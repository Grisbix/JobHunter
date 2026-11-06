"""The window's layout, checked screen by screen on a fictitious profile.

    uv run python tools/design_check.py [--out DIR] [--largeurs 1440,1000] [--vide]

Draws every screen and every Sources tab in a headless Chromium, its calls answered by
the real `jobhunter.web.api.Api` on a throwaway folder (the README screenshots' data,
tools/screenshots.py), scrolls each one top to bottom, and reports:

- **bord**: a text, button or tag less than 8 px from the edge of its card (the user,
  2026-11-05: « les écritures ne touchent pas les bords des widgets ou de l'app »);
- **coupé**: a text cut in two by the container it scrolls in, with no fade
  (`mask-image`) to say there is more.

A row scrolled under a fade is not reported: that is the fade's job. Text hidden in a
closed <details> neither, and a text cut by its own ellipsis counts by its box.

It writes one screenshot per screen and width in --out (default: a temporary folder),
to look at the empty space by eye — the other half of DESIGN.md's « Layout »: no card
stretched far past its content, no empty column beside a card. Exit code 1 when
anything is reported. tests/test_design_layout.py runs the same check in CI.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))

import screenshots  # noqa: E402  (tools/screenshots.py: the fictitious folder)

MARGE = 8  # px between a text and its card's edge, at least
ECRANS = (
    "accueil", "offres", "candidatures", "documents", "stats", "profil",
    "sources", "sources:entreprises", "sources:vues", "sources:sites", "sources:acces",
    "reglages", "tri", "relances",
)  # fmt: skip

# Run in the page: what is too close to a card's edge, or cut by its container.
MESURE = r"""
(MARGE) => {
  const CARTES = ".verre, .sombre, .carte, .colonne-k, .fiche-k, .tiroir";
  const out = [];
  const vu = new Set();
  const visible = (el) => { const s = getComputedStyle(el); return s.visibility !== "hidden" && s.display !== "none" && el.getClientRects().length; };
  const nom = (el) => (typeof el.className === "string" && el.className.trim() ? "." + el.className.trim().split(/\s+/).join(".") : el.tagName.toLowerCase());
  // the container that scrolls `el` and fades it out, if any: what passes under it is meant to
  const sousFondu = (el) => { for (let a = el.parentElement; a && a.id !== "vue"; a = a.parentElement) {
    const s = getComputedStyle(a);
    if (s.overflowY !== "visible" && s.maskImage && s.maskImage !== "none") return a; } return null; };
  function verifier(el, r, texte) {
    if (r.width < 1 || r.height < 1) return;
    if (el.closest("details:not([open])") && !el.closest("summary")) return;
    for (let a = el; a && a !== document.body; a = a.parentElement) {
      const s = getComputedStyle(a);
      if (s.textOverflow === "ellipsis" && s.overflow !== "visible") { r = a.getBoundingClientRect(); break; }
    }
    const fondu = sousFondu(el);
    if (fondu) {
      const f = fondu.getBoundingClientRect();
      if (r.bottom > f.bottom - 24 || r.top < f.top) return;  // under the fade, or scrolled away
    }
    const carte = el.closest(CARTES);
    if (carte && carte !== el) {
      const c = carte.getBoundingClientRect();
      const d = { gauche: r.left - c.left, droite: c.right - r.right, haut: r.top - c.top, bas: c.bottom - r.bottom };
      // far outside: scrolled out of a list, not drawn against the edge
      const pres = Object.entries(d).filter(([, v]) => v < MARGE && v > -4);
      if (pres.length) {
        const cle = "bord|" + nom(carte) + "|" + texte;
        if (!vu.has(cle)) { vu.add(cle); out.push({ type: "bord", ou: nom(carte), texte, ecart: pres.map(([k, v]) => `${k} ${Math.round(v)} px`).join(", ") }); }
      }
    }
    for (let a = el.parentElement; a && a.id !== "vue" && a !== document.body; a = a.parentElement) {
      const s = getComputedStyle(a);
      if (s.overflowX === "visible" && s.overflowY === "visible") continue;
      if (s.maskImage && s.maskImage !== "none") break;
      const c = a.getBoundingClientRect();
      const coupe = (r.top < c.top - 1 && r.bottom > c.top + 1) || (r.bottom > c.bottom + 1 && r.top < c.bottom - 1)
        || (r.left < c.left - 1 && r.right > c.left + 1) || (r.right > c.right + 1 && r.left < c.right - 1);
      if (coupe) {
        const cle = "coupe|" + nom(a) + "|" + texte;
        if (!vu.has(cle)) { vu.add(cle); out.push({ type: "coupé", ou: nom(a), texte }); }
      }
      break;
    }
  }
  for (const rac of [document.getElementById("vue"), document.getElementById("tiroir")]) {
    if (!rac || !visible(rac)) continue;
    const w = document.createTreeWalker(rac, NodeFilter.SHOW_TEXT);
    for (let n = w.nextNode(); n; n = w.nextNode()) {
      const t = n.textContent.trim();
      if (!t || !visible(n.parentElement)) continue;
      const rg = document.createRange(); rg.selectNodeContents(n);
      for (const r of rg.getClientRects()) verifier(n.parentElement, r, t.slice(0, 40));
    }
    for (const el of rac.querySelectorAll("button, input, select, textarea, .puce, .etiq, .compte")) {
      if (visible(el)) verifier(el, el.getBoundingClientRect(), (el.innerText || el.value || el.placeholder || el.tagName).trim().slice(0, 40));
    }
  }
  return out;
}
"""

# Stands in for pywebview, the calls answered by the Python Api (as tools/screenshots.py).
_PONT = screenshots._PONT


def dossier_fictif(racine: Path, candidatures: bool = True) -> None:
    """The README screenshots' folder; without applications, Candidatures' empty state."""
    screenshots.sandbox.preparer(racine)
    if not candidatures:
        (racine / "data" / "applications.json").write_text("{}", encoding="utf-8")


def ouvrir(navigateur, largeur: int, hauteur: int = 900):
    """A page on the web window, answered by the real Api of JOBHUNTER_RACINE's folder."""
    from jobhunter.web.__main__ import STATIC
    from jobhunter.web.api import Api

    api = Api()

    def pont(nom: str, args: list) -> object:
        return json.loads(json.dumps(getattr(api, nom)(*args), default=str))

    page = navigateur.new_page(viewport={"width": largeur, "height": hauteur})
    page.expose_function("__jh", pont)
    page.add_init_script(_PONT)
    page.goto((STATIC / "index.html").as_uri())
    page.wait_for_timeout(1500)
    page.evaluate("document.body.classList.remove('natif')")
    return page


def aller(page, ecran: str) -> None:
    """Draws `ecran` ("sources:vues" for a Sources tab) and waits for it to be filled."""
    nom, _, onglet = ecran.partition(":")
    avant = f"ongletSources = '{onglet or 'recherche'}';" if nom == "sources" else ""
    page.evaluate(f"(async () => {{ {avant} await aller('{nom}'); }})()")
    page.wait_for_timeout(800)
    for _ in range(40):  # some tabs say « Chargement… » while the Api reads
        if "Chargement…" not in page.evaluate("document.getElementById('vue').innerText"):
            break
        page.wait_for_timeout(250)
    page.wait_for_timeout(300)


def controler(page) -> list[dict]:
    """What the current screen shows too close to an edge, scrolling it top to bottom."""
    trouve: dict[str, dict] = {}
    hauteur = page.evaluate("document.getElementById('vue').scrollHeight")
    vue = page.evaluate("document.getElementById('vue').clientHeight")
    y = 0
    while True:
        page.evaluate(f"document.getElementById('vue').scrollTop = {y}")
        page.wait_for_timeout(100)
        for t in page.evaluate(MESURE, MARGE):
            trouve[json.dumps(t, sort_keys=True, ensure_ascii=False)] = t
        if y + vue >= hauteur:
            break
        y += max(200, vue - 200)
    page.evaluate("document.getElementById('vue').scrollTop = 0")
    return list(trouve.values())


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    a = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    a.add_argument("--out", help="screenshots and report (default: a temporary folder)")
    a.add_argument("--largeurs", default="1440,1000", help="window widths, in px")
    a.add_argument("--vide", action="store_true", help="no application (Candidatures empty)")
    args = a.parse_args()
    sortie = Path(args.out or tempfile.mkdtemp(prefix="jobhunter_design_")).resolve()
    sortie.mkdir(parents=True, exist_ok=True)
    racine = Path(tempfile.mkdtemp(prefix="jobhunter_design_dossier_"))
    os.environ.update(JOBHUNTER_RACINE=str(racine), JOBHUNTER_LANGUE="fr")
    os.environ.pop("JOBHUNTER_PRINCIPALE", None)
    rapport: dict[str, list[dict]] = {}
    try:
        dossier_fictif(racine, candidatures=not args.vide)
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            nav = p.chromium.launch()
            for largeur in (int(x) for x in args.largeurs.split(",")):
                page = ouvrir(nav, largeur)
                for ecran in ECRANS:
                    aller(page, ecran)
                    rapport[f"{ecran} à {largeur} px"] = controler(page)
                    page.screenshot(path=str(sortie / f"{ecran.replace(':', '-')}_{largeur}.png"))
                page.close()
            nav.close()
    finally:
        shutil.rmtree(racine, ignore_errors=True)
    (sortie / "rapport.json").write_text(
        json.dumps(rapport, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    n = 0
    for ecran, defauts in rapport.items():
        for d in defauts:
            n += 1
            print(f"{ecran} — {d['type']} ({d['ou']}) : « {d['texte']} » {d.get('ecart', '')}")
    print(f"{n} défaut(s). Captures et rapport : {sortie}")
    return 1 if n else 0


if __name__ == "__main__":
    sys.exit(main())
