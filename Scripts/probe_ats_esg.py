#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""probe_ats_esg.py — Sonde les societes de GESTION et les cabinets ESG.

POURQUOI. Les flux ATS ajoutes depuis la file ont apporte du volume mais pas de
la pertinence : sur 273 offres, 5 % d'ESG et 27 % d'ingenierie tech. La cause est
une boucle — l'axe IA du scoring a fait remonter des ESN dans la file, on a sonde
CELLES-LA, et leurs flux sont pleins de postes d'ingenieur.

Ici on part d'une liste CURATED de societes de gestion, boutiques d'asset
management, cabinets de notation extra-financiere et acteurs climat. C'est la
population ou les offres ESG vivent reellement.

Chaine identique a probe_ats_queue.py : flux actif -> offres pertinentes
(title_ok) -> identite verifiee (verify_ats_slugs) -> geographie (en_france).
Ne modifie RIEN : ecrit un rapport, l'ajout reste une decision explicite.

Run :
  python probe_ats_esg.py
  python probe_ats_esg.py --json _ats_esg.json
"""

import sys
import json
import argparse
import collections
import concurrent.futures as cf
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

import probe_ats
from probe_ats_queue import variantes, _tous_les_titres
from job_sources import title_ok, en_france

# Societes de gestion, boutiques AM, notation extra-financiere, acteurs climat.
# Complete la liste de probe_ats.CANDIDATS avec des noms FR/EU du secteur.
ESG_AM = [
    # Societes de gestion et boutiques
    "mirova",
    "sycomore",
    "sycomoream",
    "lafinanciaredelechiquier",
    "lfde",
    "dnca",
    "comgest",
    "carmignac",
    "amiralgestion",
    "tocquevillefinance",
    "edmondderothschild",
    "rothschildandco",
    "lazardfreresgestion",
    "montpensierfinance",
    "monetaam",
    "trusteam",
    "sanso",
    "inocapgestion",
    "ofiinvest",
    "lbpam",
    "swisslifeam",
    "candriam",
    "tikehaucapital",
    "eiffelinvestmentgroup",
    "rgreeninvest",
    "demeter",
    "meeschaert",
    "ecofi",
    "ecofiinvestissements",
    "phitrust",
    "quaeroCapital",
    "varenne",
    "axaim",
    "bnpparibasam",
    "amundi",
    "natixis",
    "ostrum",
    "seeyond",
    # Notation extra-financiere, data ESG, conseil climat
    "ethifinance",
    "carbone4",
    "carbon4finance",
    "icare",
    "quantis",
    "axylia",
    "novethic",
    "deepki",
    "ecoact",
    "tennaxia",
    "impak",
    "greenomy",
    "briink",
    "clarityai",
    "esgbook",
    "sustainalytics",
    "worldfavor",
    "positiongreen",
    "coolset",
    "plana",
    "climatiq",
    "altruistiq",
    "emitwise",
    "normative",
    "greenly",
    "sweep",
    "watershed",
    "ecovadis",
    "carbometrix",
    "sami",
    "greenscope",
    "verteego",
    "hellocarbo",
    "aktio",
    "toovalu",
    "traace",
    # Conseil et audit a forte composante durabilite
    "utopies",
    "goodwill-management",
    "bl-evolution",
    "wavestone",
    "sia",
    "eleven",
    "kea",
    "square",
    "julhiet",
    "colombus",
    "keyrus",
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--json", default=str(HERE / "_ats_esg.json"))
    a = ap.parse_args()

    # Liste integree de probe_ats + la notre, dedupliquees.
    noms = list(dict.fromkeys(list(probe_ats.CANDIDATS) + ESG_AM))
    essais = {}
    for n in noms:
        for s in variantes(n) or [n]:
            essais.setdefault(s, n)
    jobs = [(k, s) for s in essais for k in probe_ats.APIS]
    print(f"{len(noms)} societe(s) ESG/AM · {len(essais)} slug(s) · {len(jobs)} requetes")

    trouves = []
    with cf.ThreadPoolExecutor(max_workers=a.workers) as ex:
        for n, r in enumerate(ex.map(lambda t: probe_ats.probe(*t), jobs), 1):
            if r:
                r["entreprise"] = essais[r["slug"]]
                trouves.append(r)
            if n % 300 == 0:
                print(f"  … {n}/{len(jobs)}  ({len(trouves)} flux)")

    print(f"\n{len(trouves)} flux actif(s) — comptage des offres pertinentes…")
    for r in trouves:
        titres = _tous_les_titres(r["ats"], r["slug"])
        r["titres_total"] = len(titres)
        r["pertinents"] = [t for t in titres if title_ok(t)]

    utiles = sorted([r for r in trouves if r["pertinents"]], key=lambda r: -len(r["pertinents"]))
    print(f"\n=== {len(utiles)} flux avec au moins une offre pertinente ===\n")
    for r in utiles:
        print(
            f"  {len(r['pertinents']):4} / {r['titres_total']:5} · {r['ats']:16} "
            f"{r['slug']:24} {r['entreprise'][:22]}"
        )
        for t in r["pertinents"][:3]:
            print(f"         · {t[:72]}")
    print(f"\n  {sum(len(r['pertinents']) for r in utiles)} offre(s) pertinente(s)")

    Path(a.json).write_text(json.dumps(trouves, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n-> {Path(a.json).name}")
    print("Verifier l'identite avant d'ajouter :")
    print(f"  python verify_ats_slugs.py --json {Path(a.json).name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
