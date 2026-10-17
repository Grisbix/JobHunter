#!/usr/bin/env python3
"""scrape_desc.py — Récupère la DESCRIPTION d'une offre depuis sa page web et
l'enregistre dans apply_queue.json (champ 'description'). Réutilise le moteur
Playwright standard, sans session personnelle.

Usage :
  python scrape_desc.py --key "Entreprise|Poste"            # 1 offre (URL lue dans la queue)
  python scrape_desc.py --all --canal auto --limit 50       # lot (offres sans description)

Aucun envoi, aucune connexion tapée. Lecture seule de la page → texte."""

import argparse
import sys
import time
from pathlib import Path

# line_buffering : sinon rien ne sort quand la sortie est redirigée (run en fond = aveugle)
sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)

HERE = Path(__file__).resolve().parent
QUEUE = HERE / "apply_queue.json"

CAP = 30000  # description COMPLÈTE (pas de coupe à 8000)

# Déplie les boutons « voir plus / see more / afficher plus / lire la suite » (LinkedIn/Indeed/WTJ tronquent).
_EXPAND_JS = r"""
() => {
  const RX = /(voir plus|afficher plus|lire la suite|see more|show more|read more|plus de détails|développer)/i;
  let n = 0;
  document.querySelectorAll('button,a,[role=button],span[aria-expanded]').forEach(b => {
    const t = (b.innerText || b.getAttribute('aria-label') || '').trim();
    if (t && t.length < 40 && RX.test(t)) { try { b.click(); n++; } catch(e){} }
  });
  return n;
}"""

# Extraction du bloc description : conteneurs connus (ATS/jobboards) puis fallback <main>/body.
_DESC_JS = r"""
(CAP) => {
  const clean = s => (s||'').replace(/\r/g,'').replace(/[ \t]+\n/g,'\n').replace(/\n{3,}/g,'\n\n').trim();
  const SEL = [
    '.jobs-description__content', '.jobs-box__html-content',        // LinkedIn
    '.jobs-description-content__text', '#job-details',
    '#jobDescriptionText', '.jobsearch-JobComponent-description',   // Indeed
    '[data-testid="jobDescriptionText"]',
    '[data-testid="job-section-description"]', '[data-testid*="description"]',  // WTJ / génériques
    '.job-description', '.jobDescription', '.description__text',
    '.offer-description', '.job-details', '[class*="jobDescription"]',
    '[class*="job-description"]', '[class*="offer-body"]', '[class*="Description"]',
    'article', 'main'
  ];
  for (const s of SEL) {
    const el = document.querySelector(s);
    const t = el ? clean(el.innerText) : '';
    if (t && t.length > 120) return { text: t.slice(0, CAP), via: s };
  }
  // fallback : plus gros bloc texte de la page
  let best = '', node = null;
  document.querySelectorAll('div,section,article,main').forEach(e => {
    const t = (e.innerText || '').trim();
    if (t.length > best.length && t.length < 40000) { best = t; node = e; }
  });
  return { text: clean(best).slice(0, CAP), via: node ? (node.tagName.toLowerCase()) : 'body' };
}"""


def fetch_one(page, url):
    from web_nav import dismiss_cookies, robust_goto

    g = robust_goto(page, url, tries=2)
    if not g.get("ok"):
        return {"ok": False, "note": g.get("note", "goto_fail")}
    try:
        dismiss_cookies(page)
    except Exception:
        pass
    time.sleep(1.5)
    # déplie « voir plus » (2 passes : certains toggles apparaissent après le 1er clic)
    for _ in range(2):
        try:
            if not page.evaluate(_EXPAND_JS):
                break
            time.sleep(0.8)
        except Exception:
            break
    try:
        r = page.evaluate(_DESC_JS, CAP)
    except Exception as e:
        return {"ok": False, "note": type(e).__name__}
    txt = (r or {}).get("text", "").strip()
    via = r.get("via", "?")
    if len(txt) < 120:
        return {"ok": False, "note": "description introuvable (page JS/mur login ?)"}
    # garde anti-bot : page challenge captée à la place de la description (Indeed/Cloudflare)
    low = txt.lower()[:600]
    ANTI = (
        "vérifi",
        "verifie",
        "not a robot",
        "captcha",
        "cloudflare",
        "activez javascript",
        "enable javascript",
        "unusual traffic",
        "challenge",
    )
    if via in ("main", "body", "article") and any(a in low for a in ANTI):
        return {"ok": False, "note": "anti-bot (page challenge) — refus du site, on n'insiste pas"}
    return {"ok": True, "text": txt, "via": via}


def fetch_api(url):
    """Description par l'API publique quand l'ATS en a une, sans navigateur.

    Workday : la page d'offre est une SPA, le navigateur headless n'y lit rien
    (2026-10-08 : 0 sur ~200 fiches BlackRock / Deutsche Bank / Citi). L'API
    CXS que la page appelle elle-meme rend la fiche complete. None si l'URL
    n'est pas concernee ou si l'API ne repond pas : on retombe sur la page."""
    from urllib.parse import urlsplit

    u = urlsplit(url or "")
    if not u.netloc.endswith(".myworkdayjobs.com") or "/job/" not in u.path:
        return None
    tenant, hote = u.netloc.split(".")[:2]
    avant, chemin = u.path.split("/job/", 1)
    site = [p for p in avant.split("/") if p][-1:]  # « /en-US/Site » -> Site
    if not site:
        return None
    import httpx

    import job_sources

    d = job_sources._workday_detail(httpx, f"https://{u.netloc}", tenant, site[0], "/job/" + chemin)
    txt = (d.get("description") or "").strip()
    return {"ok": True, "text": txt[:CAP], "via": "api workday"} if len(txt) >= 120 else None


def save(q, key, text):
    for x in q:
        if f"{x.get('entreprise', '')}|{x.get('poste', '')}" == key:
            x["description"] = text
            break
    __import__("jutil").jwrite(QUEUE, q)


def main():
    # Verrou inter-processus : ce programme reecrit la queue ENTIERE. Si un
    # autre le fait en meme temps (tache planifiee vs app), le dernier qui
    # ecrit efface le travail de l'autre.
    if not __import__("jutil").garder(QUEUE):
        return 3
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", help="Entreprise|Poste (1 offre)")
    ap.add_argument("--all", action="store_true", help="lot : offres sans description")
    ap.add_argument("--canal", default=None, choices=["auto", "manuel", "linkedin", "all"])
    ap.add_argument("--limit", type=int, default=30)
    ap.add_argument(
        "--api-seul",
        action="store_true",
        help="seulement les offres lisibles par API (Workday), sans navigateur",
    )
    ap.add_argument(
        "--source",
        default=None,
        help="prefixes de source separes par des virgules (ex. talentbrew,sitemap) : "
        "seulement ces offres — pour ne viser que des pages publiques, "
        "jamais Glassdoor/Indeed qui refusent les robots",
    )
    args = ap.parse_args()
    sources = tuple(s.strip() for s in (args.source or "").split(",") if s.strip())

    import queue_io

    # QUEUE explicite : les tests remplacent cette constante par un fichier
    # jetable. Sans elle, charger() lirait la vraie file.
    q = queue_io.charger(QUEUE)  # descriptions reinjectees depuis descriptions.json
    targets = []
    if args.key:
        targets = [x for x in q if f"{x.get('entreprise', '')}|{x.get('poste', '')}" == args.key]
    elif args.all:
        for x in q:
            if x.get("description"):
                continue
            if args.canal == "linkedin" and "linkedin.com" not in (x.get("url") or ""):
                continue
            if (
                args.canal
                and args.canal not in ("all", "linkedin")
                and x.get("canal") != args.canal
            ):
                continue
            if args.api_seul and ".myworkdayjobs.com/" not in (x.get("url") or ""):
                continue
            if sources and not (x.get("source") or "").startswith(sources):
                continue
            if str(x.get("url") or "").startswith("http"):
                targets.append(x)
            if len(targets) >= args.limit:
                break
    else:
        print("Rien à faire : --key ou --all requis.")
        return
    if not targets:
        print("Aucune offre ciblée.")
        return
    print(f"{len(targets)} offre(s) à récupérer…")

    if args.api_seul:
        ok = 0
        for i, x in enumerate(targets, 1):
            key = f"{x.get('entreprise', '')}|{x.get('poste', '')}"
            try:
                r = fetch_api(x.get("url") or "")
            except Exception:
                r = None
            if r:
                x["description"] = r["text"]
                ok += 1  # x est l'objet de q
            if i % 25 == 0 or i == len(targets):
                __import__("jutil").jwrite(QUEUE, q)  # par lots : la file pese lourd
                print(f"   ── {i}/{len(targets)} — {ok} ok")
            time.sleep(0.3)
        print(f"\n=== {ok}/{len(targets)} descriptions enregistrées (API) ===")
        return

    from playwright.sync_api import sync_playwright

    eng = "playwright"
    ok = 0
    with sync_playwright() as p:

        def launch():
            """(ctx, page) neufs. Rappelé si le navigateur meurt en cours de lot."""
            b = p.chromium.launch(headless=True)
            pg = b.new_page()
            c = pg.context  # gardé : pg.context est inutilisable après pg.close()
            # TURBO : pas besoin d'images/polices pour lire le texte → 2-5× plus rapide
            try:
                from web_nav import block_resources

                block_resources(c, images=False)
            except Exception:
                pass
            return c, pg

        ctx, page = launch()
        t0 = time.time()
        for i, x in enumerate(targets, 1):
            key = f"{x.get('entreprise', '')}|{x.get('poste', '')}"
            url = x.get("url") or ""
            print(f"→ [{i}/{len(targets)}] {key[:55]}")
            try:
                r = fetch_api(url) or fetch_one(page, url)
            except Exception as e:  # un lien qui explose ne tue pas le lot
                r = {"ok": False, "note": f"erreur: {type(e).__name__}"}
                if "TargetClosed" in type(e).__name__ or "Closed" in str(e):
                    try:
                        ctx.close()
                    except Exception:
                        pass
                    try:
                        ctx, page = launch()
                        r["note"] += " (navigateur relancé)"
                    except Exception as e2:
                        print(f"   ✖ relance navigateur impossible : {e2}")
                        break
            if r["ok"]:
                save(q, key, r["text"])  # sauvegarde immédiate : rien ne se perd
                ok += 1
                print(f"   ✅ {len(r['text'])} car. (via {r['via']})")
            else:
                print(f"   ✗ {r['note']}")
            if i % 25 == 0:
                rate = (time.time() - t0) / i
                print(
                    f"   ── {i}/{len(targets)} — {ok} ok — {rate:.1f}s/offre, "
                    f"reste ~{rate * (len(targets) - i) / 60:.0f} min"
                )
            # onglet recyclé (fuite mémoire). Nouvelle page AVANT de fermer l'ancienne :
            # fermer la dernière page du contexte arrête le navigateur.
            if i % 40 == 0:
                try:
                    old_page = page
                    page = ctx.new_page()
                    old_page.close()
                except Exception:
                    pass
        try:
            ctx.close()
        except Exception:
            pass
    print(f"\n=== {ok}/{len(targets)} descriptions enregistrées dans apply_queue.json ===")


if __name__ == "__main__":
    sys.exit(main())
