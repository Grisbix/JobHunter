#!/usr/bin/env python3
"""recheck_dead.py — Detects the SOFT-404s rendered in JS (HTTP 200 page but body
"404 / offre pourvue / expirée / no longer accepting") that the static check
(link_check through requests) misses — anti-bot or React content.

Opens each URL in a real browser, runs web_nav's `dead` detector (analyze →
kind=='dead'), and writes link_status into apply_queue.json:
  - MORT     : navigation impossible (goto fails)
  - EXPIREE  : live page but dead-offer message / 0 offers
  - OK       : offer present

Run:
  python JobHunter.pyw recheck_dead --status ANTI-BOT,OK --limit 60      # targets the suspects
  python JobHunter.pyw recheck_dead --canal auto                          # auto offers
  python JobHunter.pyw recheck_dead --dry                                 # shows without writing
"""

import argparse
import datetime
import importlib
import re
import sys
import time

from jobhunter import root as _racine
from jobhunter.navigation.browser import lancer as _lancer

# line_buffering: otherwise nothing comes out when the output is redirected (background run = blind)
sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)  # type: ignore[union-attr]  # console : TextIOWrapper

HERE = _racine.scripts()
QUEUE = HERE / "apply_queue.json"
UA_H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


# ── QUICK LinkedIn route: the guest API says whether the offer is closed ──────
# In a browser, a LinkedIn offer returns kind=login (login wall) and
# therefore passes for live, whatever happens: the recheck proved NOTHING on
# LinkedIn, which is nevertheless most of the queue. The guest API, on the other hand,
# adds the CSS class `closed-job` + "No longer accepting applications" when
# the job is closed. Checked on controls: 7 offers/8 declared dead the day
# before by the browser carry the marker, none of the live ones.
# Bonus: ~0.3 s per link with httpx versus ~7 s in a browser.
# Two formats coexist: /jobs/view/<id> (links pasted by hand) and
# /jobs/view/<title>-at-<company>-<id> (links from the guest search, i.e.
# almost the whole queue). Matching only the first missed 1001
# LinkedIn offers out of 1001.
_LI_ID_RX = re.compile(r"/jobs/view/(?:[^/?#]*?-)?(\d{6,})(?:[/?#]|$)")
_LI_CLOSED_RX = re.compile(r"closed-job|no longer accepting applications", re.I)


def linkedin_fast(url):
    """(link_status, note) for a LinkedIn offer URL, without a browser.
    Returns None if the URL is not a LinkedIn offer or if the check fails, to hand
    over to the browser route."""
    m = _LI_ID_RX.search(url or "")
    if not m:
        return None
    import httpx

    try:
        r = httpx.get(
            f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{m.group(1)}",
            timeout=15,
            headers=UA_H,
            follow_redirects=True,
        )
    except Exception:
        return None
    if r.status_code == 404:
        return "EXPIREE", "guest 404 (offre retiree)"
    if r.status_code != 200 or len(r.text) < 400:
        return None  # indetermine -> navigateur
    if _LI_CLOSED_RX.search(r.text):
        return "EXPIREE", "guest: no longer accepting"
    return "OK", "guest: offre ouverte"


def classify(page, url):
    """Retour (link_status, note). Utilise robust_goto + analyze (détecteur dead partagé)."""
    from jobhunter.navigation import analyze, dismiss_cookies, robust_goto

    g = robust_goto(page, url, tries=2)
    if not g.get("ok"):
        return "MORT", g.get("note", "goto_fail")
    try:
        dismiss_cookies(page)
    except Exception:
        pass
    time.sleep(1.0)
    a = analyze(page)
    if a.get("captcha") or a.get("blocked"):
        return None, "captcha/blocked (indéterminé)"  # None = do not change
    if a.get("dead") or a.get("kind") == "dead":
        return "EXPIREE", "soft-404 (page morte / 0 offre)"
    return "OK", "vivante (kind=%s)" % a.get("kind", "?")


def main():
    # Inter-process lock: this program rewrites the ENTIRE queue. If
    # another one does it at the same time (scheduled task vs app), the last one
    # to write erases the other's work.
    if not importlib.import_module("jobhunter.programs.util").garder(QUEUE):
        return 3
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--status", default="ANTI-BOT,OK", help="link_status à revérifier (CSV). Déf: ANTI-BOT,OK"
    )
    ap.add_argument("--canal", default=None, choices=["auto", "manuel", "linkedin", "all"])
    ap.add_argument("--limit", type=int, default=80)
    ap.add_argument("--dry", action="store_true")
    ap.add_argument(
        "--no-fast",
        action="store_true",
        help="desactive la voie rapide LinkedIn (tout en navigateur)",
    )
    ap.add_argument(
        "--every", type=int, default=25, help="sauvegarde tous les N liens (checkpoint)"
    )
    ap.add_argument(
        "--fresh-days",
        type=int,
        default=7,
        help="ignore les offres déjà vérifiées depuis moins de N jours (reprise par lots)",
    )
    ap.add_argument(
        "--recycle", type=int, default=40, help="recrée l'onglet tous les N liens (fuite mémoire)"
    )
    a = ap.parse_args()

    q = importlib.import_module("jobhunter.storage.queue").charger(QUEUE, descriptions=False)
    want = {s.strip().upper() for s in a.status.split(",") if s.strip()}
    today = datetime.date.today()
    targets = []
    for x in q:
        if not str(x.get("url") or "").startswith("http"):
            continue
        # resume: skips what was checked recently (allows running in batches)
        chk = str(x.get("ls_check") or "")
        if chk and a.fresh_days > 0:
            try:
                if (today - datetime.date.fromisoformat(chk)).days < a.fresh_days:
                    continue
            except Exception:
                pass
        if a.canal == "linkedin":
            if "linkedin.com" not in x["url"]:
                continue
        elif a.canal and a.canal != "all" and x.get("canal") != a.canal:
            continue
        if want and (x.get("link_status") or "OK").upper() not in want:
            continue
        targets.append(x)  # no cut here: we sort BEFORE capping
    if not targets:
        print("Aucune offre à revérifier (filtre trop strict ?).")
        return
    # LinkedIn first: quick httpx route, reliable and ~20x faster. Otherwise the
    # career pages (often "indéterminé") go first and a browser
    # incident prevents reaching the bulk of the batch.
    if not a.no_fast:
        targets.sort(key=lambda x: 0 if _LI_ID_RX.search(str(x.get("url") or "")) else 1)
    # The cap applies AFTER the sort: otherwise it cuts at the head of the queue, where
    # career pages dominate, and the LinkedIn offers are never reached.
    targets = targets[: a.limit]
    print(f"{len(targets)} offre(s) à revérifier en navigateur (status={sorted(want)})…")

    from playwright.sync_api import sync_playwright

    eng = "playwright"
    counts = {}
    with sync_playwright() as p:

        def launch():
            """Fresh (ctx, page). Called again if the browser dies during a batch."""
            b = _lancer(p.chromium, headless=True)
            pg = b.new_page()
            c = pg.context  # kept: pg.context is unusable after pg.close()
            try:
                from jobhunter.navigation import block_resources

                block_resources(c, images=False)
            except Exception:
                pass
            return c, pg

        ctx, page = launch()
        t0 = time.time()
        dead_run = 0  # consecutive failures
        for i, x in enumerate(targets, 1):
            url = x["url"]
            # LinkedIn first: httpx is enough and really decides (the browser
            # hits the login wall and answers "vivante" whatever happens).
            fast = linkedin_fast(url) if not a.no_fast else None
            if fast:
                new, note = fast
            else:
                try:
                    new, note = classify(page, url)
                except Exception as e:  # a link that blows up does not kill the batch
                    new, note = None, f"erreur: {type(e).__name__}"
                    # dead browser -> restart it, otherwise everything else scrolls by in error
                    if "TargetClosed" in type(e).__name__ or "Closed" in str(e):
                        try:
                            ctx.close()
                        except Exception:
                            pass
                        try:
                            ctx, page = launch()
                            note += " (navigateur relancé)"
                        except Exception as e2:
                            print(f"  ✖ relance navigateur impossible : {e2}")
                            break
            old = x.get("link_status")
            # ls_check ONLY if the check really succeeded: otherwise the resume
            # would skip offers never checked.
            if not a.dry and new:
                x["ls_check"] = today.isoformat()
            # Safeguard: only counts HARD FAILURES (exception, dead browser).
            # A "captcha/blocked" is a normal UNDETERMINED result on career
            # pages — counting it stopped the batch at the 15th protected page, before
            # even reaching the LinkedIn offers.
            dead_run = dead_run + 1 if str(note).startswith("erreur:") else 0
            if dead_run >= 15:
                print(f"  ✖ {dead_run} échecs d'affilée — arrêt (relance plus tard, reprise auto)")
                break
            if new and new != old:
                counts[f"{old}→{new}"] = counts.get(f"{old}→{new}", 0) + 1
                if not a.dry:
                    x["link_status"] = new
                flag = "✏️" if not a.dry else "·"
                print(
                    f"  [{i}/{len(targets)}] {flag} {new:8} {x.get('entreprise', '')[:28]:28} — {note}"
                )
            else:
                print(
                    f"  [{i}/{len(targets)}] = {old or 'OK':8} {x.get('entreprise', '')[:28]:28} — {note}"
                )
            # checkpoint: never lose the batch if it crashes/is cut
            if not a.dry and a.every > 0 and i % a.every == 0:
                importlib.import_module("jobhunter.programs.util").jwrite(QUEUE, q)
                rate = (time.time() - t0) / i
                print(
                    f"  ── checkpoint {i}/{len(targets)} — {rate:.1f}s/lien, "
                    f"reste ~{rate * (len(targets) - i) / 60:.0f} min"
                )
            # recycled tab: otherwise memory swells (2.7 GB observed on a batch of 1452)
            if a.recycle > 0 and i % a.recycle == 0:
                try:
                    # CRITICAL ORDER: open the new page BEFORE closing the old one.
                    # Closing the last page of the context stops the browser (TargetClosedError).
                    old_page = page
                    page = ctx.new_page()
                    old_page.close()
                except Exception:
                    pass
        try:
            ctx.close()
        except Exception:
            pass

    if not a.dry:
        importlib.import_module("jobhunter.programs.util").jwrite(QUEUE, q)
    print(f"\n=== {'[DRY] ' if a.dry else ''}changements: {counts or 'aucun'} ===")


if __name__ == "__main__":
    sys.exit(main())
