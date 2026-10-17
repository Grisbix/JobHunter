#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify_links.py — Detecte les liens qui n'aboutissent plus chez la bonne societe.

Un lien peut etre VIVANT et pourtant trompeur : axa-im.com/about-us/careers
repond HTTP 200 mais apres une redirection 301 vers bnpparibas-am.com — AXA
Investment Managers ayant ete rachete par BNP Paribas. On clique AXA, on
atterrit chez BNP. recheck_dead ne voit rien : la page repond.

Ce programme suit les redirections et signale celles qui CHANGENT DE DOMAINE.
Avec --fix, l'URL est remplacee par sa destination reelle et l'ancienne gardee
dans `url_avant_redir`.

Ne touche pas aux job boards (LinkedIn, Indeed, WTJ...) : leurs URL ne portent
pas le nom de la societe, une redirection y est normale.

Run :
  python verify_links.py                 # rapport seul
  python verify_links.py --fix           # met a jour les URL redirigees
  python verify_links.py --limit 50
"""

import sys, json, argparse, concurrent.futures as cf
from pathlib import Path
from urllib.parse import urlparse

sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

HERE = Path(__file__).resolve().parent
QUEUE = HERE / "apply_queue.json"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

BOARDS = (
    "linkedin",
    "indeed",
    "welcometothejungle",
    "talent.com",
    "glassdoor",
    "wizbii",
    "businessfrance",
    "apec.fr",
    "hellowork",
    "monster",
    "jobteaser",
    "meteojob",
    "efinancialcareers",
    "linkfinance",
    "jobijoba",
    "engagement-jeunes",
    "frenchsif",
    "lever.co",
    "greenhouse.io",
    "ashbyhq",
    "recruitee",
    "smartrecruiters",
    "myworkdayjobs",
    "talent-soft",
    "icims",
    "taleo",
    "successfactors",
    "teamtailor",
    "workable",
    "missionhandicap",
)


def racine(host):
    """Domaine enregistrable approximatif."""
    h = (host or "").lower().replace("www.", "")
    p = [x for x in h.split(".") if x]
    if len(p) >= 3 and p[-2] in ("co", "com", "org", "gov", "ac"):
        return ".".join(p[-3:])
    return ".".join(p[-2:])


def suivre(o):
    import httpx

    u = str(o.get("url") or "")
    try:
        r = httpx.get(u, timeout=20, headers=UA, follow_redirects=True)
    except Exception as e:
        return o, u, type(e).__name__, False
    fin = str(r.url)
    change = racine(urlparse(fin).netloc) != racine(urlparse(u).netloc)
    return o, fin, r.status_code, change


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fix", action="store_true", help="remplace l'URL par sa destination")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()

    if a.fix and not __import__("jutil").garder(QUEUE):  # TODO queue_io
        return 3
    q = __import__("queue_io").charger(QUEUE, descriptions=False)
    cibles = [
        o
        for o in q
        if str(o.get("url") or "").startswith("http")
        and not any(b in urlparse(o["url"]).netloc.lower() for b in BOARDS)
    ]
    if a.limit:
        cibles = cibles[: a.limit]
    print(f"{len(cibles)} lien(s) hors job boards a suivre\n")

    change = mort = 0
    with cf.ThreadPoolExecutor(max_workers=a.workers) as ex:
        for o, fin, code, chg in ex.map(suivre, cibles):
            if not isinstance(code, int):
                mort += 1
                print(f"  ERREUR   {str(o.get('entreprise'))[:24]:<26}{code}")
                continue
            if chg:
                change += 1
                print(
                    f"  REDIRIGE {str(o.get('entreprise'))[:24]:<26}"
                    f"{racine(urlparse(o['url']).netloc):<26} -> {racine(urlparse(fin).netloc)}"
                )
                if a.fix:
                    o.setdefault("url_avant_redir", o["url"])
                    o["url"] = fin

    if a.fix:
        __import__("jutil").jwrite(QUEUE, q)
    print(
        f"\nBILAN : {change} lien(s) changeant de domaine · {mort} injoignable(s)"
        + ("  — queue mise a jour" if a.fix else "  (rapport seul, --fix pour corriger)")
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
