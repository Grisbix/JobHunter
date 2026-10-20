#!/usr/bin/env python3
"""test_live_nav.py — REAL test (read-only): navigates real career sites, runs the
recognition (detect_ats, segment_page, cookies, goto_careers, find_offer) and reports
whether the program adapts. NO login, NO submit. Headless.
Run: python JobHunter.pyw test_live_nav
"""

import sys
import time

from jobhunter import racine as _racine
from jobhunter.programmes import _profil_exemple  # noqa: F401  — at the top: example profile

sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]  # console : TextIOWrapper
from playwright.sync_api import sync_playwright

from jobhunter import navigation as w
from jobhunter.navigation.navigateur import lancer as _lancer

ENG = "playwright"


def _sample_sites(per_cat=5):
    """Samples real URLs from apply_queue.json, N per automatic url_type."""
    import collections
    import json

    q = json.loads((_racine.scripts() / "apply_queue.json").read_text(encoding="utf-8"))
    cats = ("ATS_DIRECT", "CAREERS_PORTAL", "HOMEPAGE", "BOARD_DIRECT")
    seen = collections.defaultdict(list)
    urls_used = set()
    out = []
    for o in q:
        ut = o.get("url_type")
        u = o.get("url") or ""
        if ut in cats and u.startswith("http") and u not in urls_used and len(seen[ut]) < per_cat:
            seen[ut].append(1)
            urls_used.add(u)
            out.append((f"{ut[:9]}·{(o.get('entreprise') or '?')[:16]}", u))
    return out


def _all_sites():
    """ALL the unique domains of the queue (except HARD_BOARD = LinkedIn/Indeed, personal ban).
    1 representative URL per (domain, url_type)."""
    import json
    from urllib.parse import urlparse

    q = json.loads((_racine.scripts() / "apply_queue.json").read_text(encoding="utf-8"))
    doms = {}
    for o in q:
        u = o.get("url") or ""
        if not u.startswith("http"):
            continue
        ut = o.get("url_type", "?")
        if ut == "HARD_BOARD":
            continue
        k = (urlparse(u).netloc, ut)
        if k not in doms:
            doms[k] = (f"{ut[:9]}·{(o.get('entreprise') or '?')[:16]}", u)
    return sorted(doms.values())


if "--all" in sys.argv:
    _A = _all_sites()
    # --all [chunk] [nchunks]: split to stay under the timeout
    _args = [a for a in sys.argv[1:] if a.isdigit()]
    if len(_args) >= 2:
        ck, nck = int(_args[0]), int(_args[1])
        SITES = _A[ck::nck]
    else:
        SITES = _A
elif len(sys.argv) > 1 and sys.argv[1].isdigit():
    SITES = _sample_sites(per_cat=int(sys.argv[1]))
else:
    SITES = _sample_sites(per_cat=6)
EXTERNES = [  # sites outside the queue → proves the generalisation
    ("EXT·Decathlon", "https://joinus.decathlon.fr/fr/annonces"),
    ("EXT·Veolia", "https://jobs.veolia.com/fr"),
    ("EXT·Ubisoft", "https://www.ubisoft.com/en-us/company/careers"),
    ("EXT·Ledger", "https://jobs.lever.co/ledger"),
    ("EXT·Alan", "https://jobs.alan.com"),
    ("EXT·Qonto", "https://qonto.com/en/careers"),
    ("EXT·GitLab", "https://boards.greenhouse.io/gitlab"),
    ("EXT·OVHcloud", "https://careers.ovhcloud.com/"),
]
if "--ext" in sys.argv or (len(sys.argv) > 1 and "--all" not in sys.argv):
    SITES = SITES + EXTERNES


def test_site(page, name, url, role="analyste esg"):
    r = {
        "name": name,
        "goto": "?",
        "cookies": "?",
        "ats": "?",
        "kind": "?",
        "offers": 0,
        "captcha": False,
        "reached": "?",
        "note": "",
    }
    g = w.robust_goto(page, url, tries=2)
    r["goto"] = "ok" if g.get("ok") else g.get("note", "KO")[:22]
    if not g.get("ok"):
        return r
    try:
        page.wait_for_load_state("networkidle", timeout=6000)
    except Exception:
        pass
    time.sleep(1.5)  # lets the JS render (React/Vue offer cards)
    try:
        ck = w.dismiss_cookies(page)
        r["cookies"] = ck.get("done", "?")
    except Exception:
        r["cookies"] = "err"
    try:
        r["ats"] = w.detect_ats(page).get("name", "?")
    except Exception:
        pass
    try:
        seg = w.segment_page(page)
        r["kind"] = seg.get("byRole") and max(seg["byRole"], key=seg["byRole"].get) or "?"
        r["offers"] = seg.get("offers", 0)
        r["captcha"] = seg.get("overlays", {}).get("captcha", False)
    except Exception:
        pass
    if r["captcha"]:
        r["reached"] = "CAPTCHA"
        return r
    # offer search (read-only: detect→search→drill, without submitting)
    try:
        info = w.analyze(page)
        if info.get("kind") in ("apply_form", "apply_cta", "register", "login"):
            r["reached"] = info["kind"]
        else:
            fo = w.find_offer(page, role, max_tries=1)
            r["reached"] = fo.get("kind", "?")
            r["note"] = "via " + fo.get("via", "?")
    except Exception as e:
        r["reached"] = "err:" + type(e).__name__
    return r


def main():
    print(f"=== TEST NAV RÉEL ({ENG}, read-only, headless) ===\n")
    rows = []
    with sync_playwright() as p:
        b = _lancer(p.chromium, headless=True)
        ctx = b.new_context(locale="fr-FR")
        page = ctx.new_page()
        page.set_default_timeout(15000)
        for name, url in SITES:
            try:
                r = test_site(page, name, url)
            except Exception as e:
                r = {
                    "name": name,
                    "goto": "EXC",
                    "note": type(e).__name__,
                    "cookies": "-",
                    "ats": "-",
                    "kind": "-",
                    "offers": 0,
                    "captcha": False,
                    "reached": "-",
                }
            rows.append(r)
            print(
                f"{name:22} goto={r['goto']:6} cookie={str(r['cookies'])[:12]:12} "
                f"ats={r['ats']:14} top-role={str(r['kind'])[:10]:10} offres={r['offers']:3} "
                f"captcha={'Y' if r['captcha'] else '.'} → {r['reached']} {r['note']}"
            )
        b.close()
    ok = sum(1 for r in rows if r["goto"] == "ok")
    reached = sum(
        1
        for r in rows
        if r["reached"] in ("apply_form", "apply_cta", "register", "login", "offer_list")
    )
    cap = sum(1 for r in rows if r["captcha"])
    print(
        f"\n=== BILAN : {ok}/{len(rows)} chargés · {reached} form/offre atteint · {cap} captcha ==="
    )


if __name__ == "__main__":
    main()
