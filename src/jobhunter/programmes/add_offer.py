#!/usr/bin/env python3
"""add_offer.py — COLLE UN LIEN d'offre → analyse la page (titre, entreprise,
description), score (fit/ATS), ajoute à apply_queue.json, puis génère CV + lettre.

Run : python JobHunter.pyw ajouter --url "https://…"           # analyse + queue + docs
      python JobHunter.pyw ajouter --url "https://…" --no-docs # sans CV/lettre
"""

import argparse
import importlib
import re
import sys
import time
from urllib.parse import urlparse

from jobhunter import racine as _racine

sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]  # console : TextIOWrapper

HERE = _racine.scripts()
QUEUE = HERE / "apply_queue.json"

# titre + entreprise depuis la page (og: meta > h1 > <title>)
_META_JS = r"""
() => {
  const q=s=>document.querySelector(s);
  const og=p=>{const m=q(`meta[property="og:${p}"],meta[name="og:${p}"]`);return m?m.content:''};
  const h1=q('h1')?q('h1').innerText.trim():'';
  return {ogTitle:og('title'), ogSite:og('site_name'), h1:h1,
          title:(document.title||'').trim()};
}"""


def analyze_url(url):
    """Ouvre la page (headless TURBO) → {titre, entreprise, description}."""
    from jobhunter.navigation import (
        block_resources,
        dismiss_cookies,
        get_sync_playwright,
        robust_goto,
    )
    from jobhunter.programmes.scrape_desc import _DESC_JS, _EXPAND_JS, CAP

    spw, eng = get_sync_playwright("auto")
    out = {"titre": "", "entreprise": "", "description": ""}
    with spw() as p:
        b = p.chromium.launch(headless=True)
        pg = b.new_page()
        block_resources(pg.context, images=False)
        g = robust_goto(pg, url, tries=2)
        if not g.get("ok"):
            b.close()
            return None, f"page inaccessible ({g.get('note', '')})"
        try:
            dismiss_cookies(pg)
        except Exception:
            pass
        time.sleep(1.2)
        for _ in range(2):
            try:
                if not pg.evaluate(_EXPAND_JS):
                    break
                time.sleep(0.7)
            except Exception:
                break
        try:
            m = pg.evaluate(_META_JS)
        except Exception:
            m = {}
        try:
            d = pg.evaluate(_DESC_JS, CAP)
            out["description"] = (d or {}).get("text", "").strip()
        except Exception:
            pass
        b.close()
    import html as _html

    # titre : og:title > h1 > <title> — nettoie entités + « | Site »
    t = _html.unescape((m.get("ogTitle") or m.get("h1") or m.get("title") or "").strip())
    t = re.split(r"\s*[|•]\s*", t)[0].strip()
    ent = _html.unescape((m.get("ogSite") or "").strip())
    # LinkedIn : « ENTREPRISE hiring POSTE in VILLE » → sépare
    mm = re.match(r"^(.{2,50}?)\s+hiring\s+(.+?)(?:\s+in\s+.{2,60})?$", t, re.I)
    if mm:
        ent, t = mm.group(1).strip(), mm.group(2).strip()
    # boards : og:site_name = nom du site, pas l'employeur
    if not ent or ent.lower() in (
        "linkedin",
        "indeed",
        "welcome to the jungle",
        "glassdoor",
        "hellowork",
        "apec",
    ):
        mm = re.search(r"(?:chez|at)\s+([A-Z][\w&' .-]{2,40})", t)
        ent = (
            mm.group(1).strip()
            if mm
            else urlparse(url).netloc.replace("www.", "").split(".")[0].title()
        )
    out["titre"] = t[:120] or "Offre sans titre"
    out["entreprise"] = ent[:60]
    if len(out["description"]) < 120:
        out["description"] = ""
    return out, "ok"


def add_to_queue(url, meta):
    from jobhunter.programmes.scrape_jobs import classify_domaine
    from jobhunter.sources import _mk, merge_into_queue

    o = _mk(
        meta["titre"],
        url,
        meta["entreprise"],
        source="ajout manuel",
        description=meta.get("description", ""),
    )
    o["domaine"] = classify_domaine(meta["titre"])
    r = merge_into_queue([o], dry=False)
    return r


def make_docs(url):
    """Génère CV + lettre pour la ligne queue de cette URL, met à jour les liens."""
    from jobhunter.stockage import file as queue_io

    # QUEUE explicite : les tests remplacent cette constante par un fichier
    # jetable. Sans elle, charger() lirait la vraie file.
    q = queue_io.charger(QUEUE)  # descriptions reinjectees depuis descriptions.json
    x = next((v for v in q if v.get("url") == url), None)
    if not x:
        return "offre introuvable en queue"
    from jobhunter.documents import cv_une_page, tailor_letter, to_pdf

    offer = dict(
        company=x["entreprise"],
        role=x["poste"],
        offer_text=f"{x['poste']} {x.get('description', '')}",
        missions=(x.get("description") or "")[:400],
        profil="",
        domaine=x.get("domaine", ""),
        rh=x.get("rh"),
    )
    from urllib.parse import quote as _q

    def _url_of(p):
        return "file:///" + _q(str(p).replace("\\", "/"), safe="/:")

    try:
        cv, pdf = cv_une_page(offer)
        if cv:
            x["cv"] = _url_of(pdf or cv)
            x["cv_variant"] = None
    except Exception as e:
        print(f"  ! cv: {type(e).__name__}")
    try:
        lt = tailor_letter(offer)
        if lt:
            pdf = to_pdf(lt)
            x["lettre"] = _url_of(pdf or lt)
    except Exception as e:
        print(f"  ! lettre: {type(e).__name__}")
    importlib.import_module("jobhunter.programmes.jutil").jwrite(QUEUE, q)
    return "docs générés"


def main():
    # Verrou inter-processus : ce programme reecrit la queue ENTIERE. Si un
    # autre le fait en meme temps (tache planifiee vs app), le dernier qui
    # ecrit efface le travail de l'autre.
    if not importlib.import_module("jobhunter.programmes.jutil").garder(QUEUE):
        return 3
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--no-docs", action="store_true")
    a = ap.parse_args()
    url = a.url.strip()
    if not url.startswith("http"):
        print("URL invalide.")
        return 1
    print(f"🔎 analyse {url[:80]}…")
    meta, note = analyze_url(url)
    if meta is None:
        print(f"✗ {note}")
        return 1
    print(f"  poste      : {meta['titre']}")
    print(f"  entreprise : {meta['entreprise']}")
    print(f"  description: {len(meta['description'])} car.")
    r = add_to_queue(url, meta)
    print(
        f"  queue      : +{r['added']} ({r['total']} total)"
        + (" — déjà présente (mise à jour desc)" if not r["added"] else "")
    )
    if not a.no_docs:
        print("  " + make_docs(url))
    print("✅ terminé — recharge l'app pour voir l'offre.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
