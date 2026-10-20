#!/usr/bin/env python3
"""test_acces_sites.py — Measures WHICH sites of the queue can be opened.

Answers "which ones can you open". For each distinct domain, opens a representative
URL, sets aside the cookie banner (refusal first), and classifies the result:
  OK        readable page
  MUR LOGIN login form (solved by logging in once)
  BLOQUE    anti-bot / captcha — NOT bypassable, and we do not try to bypass it
  ERREUR    navigation impossible

The cookie detail says whether the refusal worked (cmp-reject / reject) or whether the
code had to ACCEPT for lack of a refusal button (accept-fallback): those cases are the
only ones where consent is given, so it is best to know them.

Run:
  python JobHunter.pyw test_acces_sites                 # CAREER sites (excluding job boards)
  python JobHunter.pyw test_acces_sites --boards        # job boards only
  python JobHunter.pyw test_acces_sites --all --limit 0 # everything, no cap
  python JobHunter.pyw test_acces_sites --json out.json
"""

import argparse
import collections
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

from jobhunter import root as _racine
from jobhunter.programs import (
    _example_profile as _profil_exemple,  # noqa: F401  — at the top: example profile
)

sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)  # type: ignore[union-attr]  # console : TextIOWrapper

HERE = _racine.scripts()
QUEUE = HERE / "apply_queue.json"
PROFIL = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "apply_runner_chrome"

BOARDS = (
    "linkedin",
    "indeed",
    "welcometothejungle",
    "talent.com",
    "glassdoor",
    "lever.co",
    "ashbyhq",
    "greenhouse",
    "smartrecruiters",
    "recruitee",
    "wizbii",
    "businessfrance",
    "frenchsif",
    "apec",
    "hellowork",
    "monster",
    "jobteaser",
    "efinancialcareers",
    "meteojob",
)
# OFFER URL: we want the domain's home/career page, not a posting
_OFFRE_RX = re.compile(r"/jobs?/view|[?&]jk=|/o/|/job-offers?/|/offres/\d+", re.I)


def cibles(mode, limit):
    q = json.loads(QUEUE.read_text(encoding="utf-8"))
    vus = {}
    for o in q:
        u = str(o.get("url") or "")
        if not u.startswith("http") or _OFFRE_RX.search(u):
            continue
        h = urlparse(u).netloc.replace("www.", "")
        est_board = any(b in h for b in BOARDS)
        if mode == "carrieres" and est_board:
            continue
        if mode == "boards" and not est_board:
            continue
        vus.setdefault(h, u)
    items = list(vus.items())
    return items[:limit] if limit else items


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--boards", action="store_true", help="job boards au lieu des sites carriere")
    ap.add_argument("--all", action="store_true", help="les deux")
    ap.add_argument("--limit", type=int, default=25, help="0 = sans plafond")
    ap.add_argument("--json", help="ecrit le detail dans ce fichier")
    a = ap.parse_args()
    mode = "tous" if a.all else ("boards" if a.boards else "carrieres")

    lots = cibles(mode, a.limit)
    if not lots:
        print("Aucun site cible.")
        return 1

    from jobhunter.navigation import analyze, dismiss_cookies, get_sync_playwright

    sp, eng = get_sync_playwright("auto")
    print(f"moteur={eng} · mode={mode} · {len(lots)} domaine(s)\n")
    print(f"{'SITE':<34}{'ETAT':<12}{'COOKIES':<18}KIND")

    res, stats, ck_stats = [], collections.Counter(), collections.Counter()
    PROFIL.mkdir(parents=True, exist_ok=True)
    with sp() as p:

        def lance():
            c = p.chromium.launch_persistent_context(
                user_data_dir=str(PROFIL),
                channel="chrome",
                headless=True,
                args=["--no-first-run", "--no-default-browser-check"],
                no_viewport=True,
                timeout=90000,
            )
            return c, (c.pages[0] if c.pages else c.new_page())

        ctx, page = lance()
        for i, (h, u) in enumerate(lots):
            ck, kind = {"done": "-"}, "?"
            try:
                page.goto(u, timeout=30000, wait_until="domcontentloaded")
                ck = dismiss_cookies(page) or {"done": "none"}
                page.wait_for_timeout(600)
                x = analyze(page)
                kind = str(x.get("kind") or "?")
                etat = (
                    "BLOQUE"
                    if (x.get("blocked") or x.get("captcha"))
                    else "MUR LOGIN"
                    if kind == "login"
                    else "OK"
                )
            except Exception as e:
                etat, kind = "ERREUR", type(e).__name__
                # Dead browser: without a restart, ALL the rest of the batch scrolls by in
                # error (28 sites out of 106 during the first pass, including sites
                # we knew were answering).
                if "Closed" in kind or "Closed" in str(e) or "crash" in str(e).lower():
                    try:
                        ctx.close()
                    except Exception:
                        pass
                    try:
                        ctx, page = lance()
                        kind += " (navigateur relance)"
                    except Exception:
                        print("  ✖ relance impossible — arret")
                        break
            # Recycled tab: avoids memory drift on long batches.
            if (i + 1) % 30 == 0:
                try:
                    vieux = page
                    page = ctx.new_page()
                    vieux.close()
                except Exception:
                    pass
            stats[etat] += 1
            ck_stats[str(ck.get("done"))] += 1
            res.append({"site": h, "url": u, "etat": etat, "cookies": ck.get("done"), "kind": kind})
            print(f"  {h[:32]:<34}{etat:<12}{str(ck.get('done'))[:16]:<18}{kind}")
        try:
            ctx.close()
        except Exception:
            pass

    tot = len(res)
    print(f"\nBILAN : {dict(stats)}   ({100 * stats['OK'] // max(1, tot)} % ouvrables)")
    print(f"COOKIES : {dict(ck_stats)}")
    acc = [r["site"] for r in res if r["cookies"] == "accept-fallback"]
    if acc:
        print(f"\n⚠ {len(acc)} site(s) sans bouton « refuser » — cookies ACCEPTES par defaut :")
        print("  " + ", ".join(acc))
    if a.json:
        Path(a.json).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"\n-> {a.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
