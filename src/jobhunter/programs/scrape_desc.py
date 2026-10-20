#!/usr/bin/env python3
"""scrape_desc.py — Fetches an offer's DESCRIPTION from its web page and
records it in apply_queue.json ('description' field). Reuses the standard
Playwright engine, without a personal session.

Usage:
  python JobHunter.pyw scrape_desc --key "Entreprise|Poste"            # 1 offer (URL read in the queue)
  python JobHunter.pyw scrape_desc --all --canal auto --limit 50       # batch (offers without description)

No sending, no login typed. Read-only of the page → text."""

import argparse
import importlib
import sys
import time

from jobhunter import root as _racine
from jobhunter.navigation.browser import lancer as _lancer

# line_buffering: otherwise nothing comes out when the output is redirected (background run = blind)
sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)  # type: ignore[union-attr]  # console : TextIOWrapper

HERE = _racine.scripts()
QUEUE = HERE / "apply_queue.json"

CAP = 30000  # FULL description (no cut at 8000)

# Unfolds the "voir plus / see more / afficher plus / lire la suite" buttons (LinkedIn/Indeed/WTJ truncate).
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

# Extraction of the description block: known containers (ATS/job boards) then fallback <main>/body.
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
    from jobhunter.navigation import dismiss_cookies, robust_goto

    g = robust_goto(page, url, tries=2)
    if not g.get("ok"):
        return {"ok": False, "note": g.get("note", "goto_fail")}
    try:
        dismiss_cookies(page)
    except Exception:
        pass
    time.sleep(1.5)
    # unfolds "voir plus" (2 passes: some toggles appear after the 1st click)
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
    # anti-bot guard: challenge page caught instead of the description (Indeed/Cloudflare)
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
    """Description through the public API when the ATS has one, without a browser.

    Workday: the offer page is a SPA, the headless browser reads nothing there
    (2026-10-08: 0 out of ~200 BlackRock / Deutsche Bank / Citi postings). The CXS
    API that the page calls itself returns the full posting. None if the URL is not
    concerned or if the API does not answer: we fall back on the page."""
    from urllib.parse import urlsplit

    u = urlsplit(url or "")
    if not u.netloc.endswith(".myworkdayjobs.com") or "/job/" not in u.path:
        return None
    tenant, hote = u.netloc.split(".")[:2]
    avant, chemin = u.path.split("/job/", 1)
    site = [p for p in avant.split("/") if p][-1:]  # "/en-US/Site" -> Site
    if not site:
        return None
    import httpx

    from jobhunter import sources as job_sources

    d = job_sources._workday_detail(httpx, f"https://{u.netloc}", tenant, site[0], "/job/" + chemin)
    txt = (d.get("description") or "").strip()
    return {"ok": True, "text": txt[:CAP], "via": "api workday"} if len(txt) >= 120 else None


def save(q, key, text):
    for x in q:
        if f"{x.get('entreprise', '')}|{x.get('poste', '')}" == key:
            x["description"] = text
            break
    importlib.import_module("jobhunter.programs.util").jwrite(QUEUE, q)


def main():
    # Inter-process lock: this program rewrites the ENTIRE queue. If
    # another one does it at the same time (scheduled task vs app), the last one
    # to write erases the other's work.
    if not importlib.import_module("jobhunter.programs.util").garder(QUEUE):
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

    from jobhunter.storage import queue as queue_io

    # Explicit QUEUE: the tests replace this constant with a throwaway
    # file. Without it, charger() would read the real queue.
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
                ok += 1  # x is the object of q
            if i % 25 == 0 or i == len(targets):
                importlib.import_module("jobhunter.programs.util").jwrite(
                    QUEUE, q
                )  # in batches: the queue is heavy
                print(f"   ── {i}/{len(targets)} — {ok} ok")
            time.sleep(0.3)
        print(f"\n=== {ok}/{len(targets)} descriptions enregistrées (API) ===")
        return

    from playwright.sync_api import sync_playwright

    eng = "playwright"
    ok = 0
    with sync_playwright() as p:

        def launch():
            """Fresh (ctx, page). Called again if the browser dies during a batch."""
            b = _lancer(p.chromium, headless=True)
            pg = b.new_page()
            c = pg.context  # kept: pg.context is unusable after pg.close()
            # TURBO: no need for images/fonts to read the text → 2-5× faster
            try:
                from jobhunter.navigation import block_resources

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
            except Exception as e:  # a link that blows up does not kill the batch
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
                save(q, key, r["text"])  # immediate save: nothing is lost
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
            # recycled tab (memory leak). New page BEFORE closing the old one:
            # closing the last page of the context stops the browser.
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
