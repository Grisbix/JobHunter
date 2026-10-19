#!/usr/bin/env python3
"""probe_workday.py — Finds the public Workday feeds of large groups.

Why: the career sites of these groups (careers.axa.com, allianz.com,
group.bnpparibas...) are behind an anti-bot and do not open. But their offers are
served by Workday on *.myworkdayjobs.com, which is NOT protected and exposes a public,
unauthenticated JSON API (the one their own page calls). We read the official source
instead of forcing the shop window.

Two steps, so as not to hammer:
  1. does the tenant exist?    GET https://{tenant}.{host}.myworkdayjobs.com/
  2. what is the site's name?  POST /wday/cxs/{tenant}/{site}/jobs

Changes NOTHING: displays the feeds that answer.

Run:
  python JobHunter.pyw probe_workday
  python JobHunter.pyw probe_workday --tenants axa,allianz --json out.json
"""

import argparse
import concurrent.futures as cf
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)  # type: ignore[union-attr]  # console : TextIOWrapper

UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
    "Content-Type": "application/json",
}

# Groups whose career page is blocked by anti-bot (test_acces_sites.py)
TENANTS = [
    "axa",
    "axaim",
    "axa-im",
    "axaxl",
    "allianz",
    "allianzgi",
    "allianzse",
    "bnpparibas",
    "bnp",
    "bpifrance",
    "swissre",
    "swisslife",
    "juliusbaer",
    "lombardodier",
    "cushwake",
    "cushmanwakefield",
    "greenly",
    "sweep",
    "amundi",
    "natixis",
    "societegenerale",
    "creditagricole",
    "schroders",
    "abrdn",
    "robeco",
    "generali",
    "zurich",
    "aviva",
    "legalandgeneral",
]
HOSTS = ["wd1", "wd2", "wd3", "wd5", "wd12", "wd103"]
# Workday imposes no convention for the site's name: we try the forms seen
SITES = [
    "careers",
    "Careers",
    "External",
    "external",
    "ExternalCareerSite",
    "External_Career_Site",
    "Global",
    "global",
    "jobs",
    "Jobs",
    "GlobalCareers",
    "CareerSite",
    "Professional",
    "Experienced",
]


def tenant_vivant(tenant, host):
    import httpx

    url = f"https://{tenant}.{host}.myworkdayjobs.com/"
    try:
        r = httpx.get(url, timeout=10, headers=UA, follow_redirects=True)
        return (tenant, host) if r.status_code < 500 else None
    except Exception:
        return None


def probe_site(tenant, host, site):
    import httpx

    url = f"https://{tenant}.{host}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs"
    try:
        r = httpx.post(
            url,
            timeout=12,
            headers=UA,
            follow_redirects=True,
            json={"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": ""},
        )
        if r.status_code != 200:
            return None
        d = r.json()
    except Exception:
        return None
    n = int(d.get("total") or 0)
    if n <= 0:
        return None
    return {
        "tenant": tenant,
        "host": host,
        "site": site,
        "n": n,
        "url": url,
        "titres": [p.get("title", "") for p in (d.get("jobPostings") or [])[:3]],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tenants", help="liste CSV (sinon liste integree)")
    ap.add_argument("--json", help="ecrit les resultats dans ce fichier")
    ap.add_argument("--workers", type=int, default=24)
    a = ap.parse_args()

    tenants = [t.strip() for t in a.tenants.split(",")] if a.tenants else TENANTS
    paires = [(t, h) for t in tenants for h in HOSTS]
    print(f"Etape 1 : {len(paires)} tenant/host a tester…")

    vivants = []
    with cf.ThreadPoolExecutor(max_workers=a.workers) as ex:
        for r in ex.map(lambda p: tenant_vivant(*p), paires):
            if r:
                vivants.append(r)
                print(f"  · tenant trouve : {r[0]}.{r[1]}")

    combos = [(t, h, s) for (t, h) in vivants for s in SITES]
    print(
        f"\nEtape 2 : {len(vivants)} tenant(s) x {len(SITES)} noms de site = {len(combos)} requetes…"
    )

    found = []
    with cf.ThreadPoolExecutor(max_workers=a.workers) as ex:
        for r in ex.map(lambda c: probe_site(*c), combos):
            if r:
                found.append(r)
                print(
                    f"  OK {r['tenant']}.{r['host']}/{r['site']:<22} {r['n']:>5} offres | "
                    + " / ".join(t[:34] for t in r["titres"][:2])
                )

    found.sort(key=lambda r: -r["n"])
    print(f"\n=== {len(found)} flux Workday actifs ===")
    if a.json:
        Path(a.json).write_text(json.dumps(found, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"-> {a.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
