#!/usr/bin/env python3
"""probe_ats.py — Teste des slugs candidats sur les 5 API ATS publiques.

But : trouver quelles sociétés (boutiques AM / ESG françaises) exposent un flux
d'offres LISIBLE PAR MACHINE. Celles qui répondent peuvent être ajoutées à
ATS_SLUGS dans job_sources.py → scannées chaque jour, sans navigateur, sans
anti-bot, avec la description fournie d'office.

Ne modifie RIEN : affiche seulement ce qui répond. Sortie triée par nb d'offres.

Run :
  python probe_ats.py                        # liste candidate intégrée
  python probe_ats.py --slugs dnca,comgest   # teste des slugs precis
  python probe_ats.py --json out.json
"""

import argparse
import concurrent.futures as cf
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

HERE = Path(__file__).resolve().parent
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# Boutiques AM + acteurs ESG/climat FR. Variantes de slug : les ATS n'imposent
# aucune convention (tiret, casse, nom court…), donc on tente plusieurs formes.
CANDIDATS = [
    # ── Sociétés de gestion / AM françaises ──
    "lazard",
    "lazardfreresgestion",
    "lfde",
    "lafinancieredelechiquier",
    "amiralgestion",
    "amiral",
    "comgest",
    "carmignac",
    "dnca",
    "dncafinance",
    "tocqueville",
    "tocquevillefinance",
    "edmonddrothschild",
    "edram",
    "rothschildandco",
    "rothschildandcogroup",
    "arbevel",
    "financierearbevel",
    "montpensier",
    "montpensierfinance",
    "moneta",
    "monetaam",
    "trusteam",
    "sanso",
    "sansois",
    "inocap",
    "inocapgestion",
    "groupamaam",
    "groupama",
    "ofiinvest",
    "ofi",
    "creditmutuelam",
    "palatineam",
    "vegaim",
    "erasmusgestion",
    "clartan",
    "eiffelinvestmentgroup",
    "eiffel",
    "rgreeninvest",
    "rgreen",
    "demeter",
    "demeterpartners",
    "apicil",
    "federalfinance",
    "lbpam",
    "swisslifeam",
    "candriam",
    "pictet",
    "tikehaucapital",
    "tikehau",
    "meeschaert",
    "sycomore",
    # ── ESG / climat : data, notation, conseil ──
    "ethifinance",
    "carbone4",
    "carbon4finance",
    "icare",
    "icareconsult",
    "quantis",
    "axylia",
    "novethic",
    "deepki",
    "ecoact",
    "tennaxia",
    "impakanalytics",
    "impak",
    "sopht",
    "metron",
    "greenomy",
    "briink",
    "matter",
    "clarity-ai",
    "clarityai",
    "esgbook",
    "sustainalytics",
    "worldfavor",
    "position-green",
    "positiongreen",
    "coolset",
    "plana",
    "climatiq",
    "altruistiq",
    "emitwise",
    "normative",
    "greenly",
    "sweep",
]

APIS = {
    "greenhouse": lambda s: f"https://boards-api.greenhouse.io/v1/boards/{s}/jobs?content=true",
    "lever": lambda s: f"https://api.lever.co/v0/postings/{s}?mode=json",
    "ashby": lambda s: f"https://api.ashbyhq.com/posting-api/job-board/{s}",
    "recruitee": lambda s: f"https://{s}.recruitee.com/api/offers/",
    "smartrecruiters": lambda s: (
        f"https://api.smartrecruiters.com/v1/companies/{s}/postings?limit=100"
    ),
}


def count_jobs(kind, data):
    """Nb d'offres selon la forme de réponse propre à chaque ATS."""
    try:
        if kind == "greenhouse":
            return len(data.get("jobs", []))
        if kind == "lever":
            return len(data) if isinstance(data, list) else 0
        if kind == "ashby":
            return len(data.get("jobs", []))
        if kind == "recruitee":
            return len(data.get("offers", []))
        if kind == "smartrecruiters":
            return int(data.get("totalFound") or len(data.get("content", [])))
    except Exception:
        pass
    return 0


def titles(kind, data, n=3):
    try:
        if kind == "greenhouse":
            return [j.get("title", "") for j in data.get("jobs", [])[:n]]
        if kind == "lever":
            return [j.get("text", "") for j in data[:n]]
        if kind == "ashby":
            return [j.get("title", "") for j in data.get("jobs", [])[:n]]
        if kind == "recruitee":
            return [j.get("title", "") for j in data.get("offers", [])[:n]]
        if kind == "smartrecruiters":
            return [j.get("name", "") for j in data.get("content", [])[:n]]
    except Exception:
        pass
    return []


def probe(kind, slug):
    import httpx

    try:
        r = httpx.get(APIS[kind](slug), timeout=12, headers=UA, follow_redirects=True)
        if r.status_code != 200:
            return None
        data = r.json()
    except Exception:
        return None
    n = count_jobs(kind, data)
    if n <= 0:
        return None
    return {"ats": kind, "slug": slug, "n": n, "titres": titles(kind, data)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slugs", help="liste CSV de slugs à tester (sinon liste intégrée)")
    ap.add_argument("--json", help="écrit les résultats dans ce fichier")
    ap.add_argument("--workers", type=int, default=16)
    a = ap.parse_args()

    slugs = [s.strip() for s in a.slugs.split(",")] if a.slugs else CANDIDATS
    jobs = [(k, s) for s in slugs for k in APIS]
    print(f"{len(slugs)} slug(s) x {len(APIS)} ATS = {len(jobs)} requêtes…")

    found = []
    with cf.ThreadPoolExecutor(max_workers=a.workers) as ex:
        for r in ex.map(lambda t: probe(*t), jobs):
            if r:
                found.append(r)
                print(
                    f"  ✅ {r['ats']:<16} {r['slug']:<24} {r['n']:>3} offres | "
                    + " / ".join(t[:34] for t in r["titres"][:2])
                )

    found.sort(key=lambda r: -r["n"])
    print(f"\n=== {len(found)} flux ATS actifs sur {len(slugs)} slugs testés ===")
    if found:
        print("\nÀ ajouter dans job_sources.ATS_SLUGS :")
        par = {}
        for r in found:
            par.setdefault(r["ats"], []).append(r["slug"])
        for k, v in par.items():
            print(f'  "{k}": {v},')
    if a.json:
        Path(a.json).write_text(json.dumps(found, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"\n-> {a.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
