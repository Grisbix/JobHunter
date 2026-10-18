#!/usr/bin/env python3
"""probe_ats_queue.py — Quelles entreprises de la file exposent un flux ATS lisible ?

POURQUOI. Remonter au site de l'employeur par navigation ne marche pas : mesure
0 sur 27 (voir offres_depuis_site.py). Les API ATS, elles, rendent du JSON avec
l'URL directe de l'annonce ET sa description, sans navigateur ni anti-bot.

Ce programme part des entreprises DEJA dans la queue — pas d'une liste devinee
comme probe_ats.py — et compte les offres qui passent le filtre de pertinence
(`job_sources.title_ok`). Un flux de 1120 offres dont aucune ne correspond au
profil ne vaut rien : c'est le nombre APRES filtre qui decide.

Ne modifie RIEN. Ecrit un rapport JSON ; l'ajout dans sources_config.json reste
une decision explicite.

Run :
  python probe_ats_queue.py --fit 8          # entreprises des offres fit >= 8
  python probe_ats_queue.py --fit 0          # toutes
  python probe_ats_queue.py --json out.json
"""

import argparse
import collections
import concurrent.futures as cf
import json
import re
import sys
import unicodedata
from pathlib import Path

from jobhunter import racine as _racine

HERE = _racine.scripts()

sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

from jobhunter.programmes import probe_ats
from jobhunter.sources import rang_source, title_ok
from jobhunter.stockage import file as queue_io

# Mots qui ne font pas partie du slug d'un ATS.
BRUIT = {
    "group",
    "groupe",
    "france",
    "sa",
    "sas",
    "sarl",
    "the",
    "and",
    "co",
    "company",
    "consulting",
    "conseil",
    "partners",
    "international",
}


def variantes(nom):
    """Slugs plausibles pour une societe. Les ATS n'imposent aucune convention :
    « Credit Agricole » peut etre creditagricole, credit-agricole, ou credit."""
    n = unicodedata.normalize("NFD", (nom or "").lower())
    n = "".join(c for c in n if not unicodedata.combining(c))
    mots = [m for m in re.split(r"[^a-z0-9]+", n) if m]
    utiles = [m for m in mots if m not in BRUIT] or mots
    if not utiles:
        return []
    out = ["".join(utiles), "-".join(utiles)]
    if len(utiles) > 1:
        out.append(utiles[0])  # « alten » pour « Alten Group »
        out.append("".join(utiles[:2]))
    return [s for s in dict.fromkeys(out) if len(s) >= 3]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fit", type=int, default=8)
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--json", default=str(HERE / "_ats_candidats.json"))
    ap.add_argument(
        "--linkedin-seul",
        action="store_true",
        default=True,
        help="ne considerer que les entreprises dont l'offre vient de LinkedIn",
    )
    a = ap.parse_args()

    q = queue_io.charger(descriptions=False)
    ents = sorted(
        {
            (o.get("entreprise") or "").strip()
            for o in q
            if (o.get("fit") or 0) >= a.fit
            and (not a.linkedin_seul or rang_source(o.get("url")) == 0)
            and (o.get("entreprise") or "").strip()
        }
    )

    essais = {}  # slug -> nom de societe (le 1er qui le propose)
    for e in ents:
        for s in variantes(e):
            essais.setdefault(s, e)
    jobs = [(k, s) for s in essais for k in probe_ats.APIS]
    print(
        f"{len(ents)} entreprise(s) · {len(essais)} slug(s) · "
        f"{len(jobs)} requetes sur {len(probe_ats.APIS)} API"
    )

    trouves = []
    with cf.ThreadPoolExecutor(max_workers=a.workers) as ex:
        for n, r in enumerate(ex.map(lambda t: probe_ats.probe(*t), jobs), 1):
            if r:
                r["entreprise"] = essais[r["slug"]]
                trouves.append(r)
            if n % 400 == 0:
                print(f"  … {n}/{len(jobs)}  ({len(trouves)} flux)")

    # Combien d'offres passent VRAIMENT le filtre metier ?
    print(f"\n{len(trouves)} flux actif(s) — comptage des offres pertinentes…")
    for r in trouves:
        titres = _tous_les_titres(r["ats"], r["slug"])
        r["titres_total"] = len(titres)
        r["pertinents"] = [t for t in titres if title_ok(t)]

    trouves.sort(key=lambda r: -len(r["pertinents"]))
    utiles = [r for r in trouves if r["pertinents"]]

    print(
        f"\n=== {len(utiles)} flux avec au moins une offre pertinente "
        f"(sur {len(trouves)} flux actifs) ===\n"
    )
    total = 0
    for r in utiles:
        total += len(r["pertinents"])
        print(
            f"  {len(r['pertinents']):4} / {r['titres_total']:5} · {r['ats']:16} "
            f"{r['slug']:22} {r['entreprise'][:26]}"
        )
        for t in r["pertinents"][:3]:
            print(f"         · {t[:74]}")
    print(f"\n  {total} offre(s) pertinente(s) au total")

    if utiles:
        par_ats = collections.defaultdict(list)
        for r in utiles:
            par_ats[r["ats"]].append(r["slug"])
        print("\nA ajouter dans sources_config.json -> ats_slugs :")
        for k, v in par_ats.items():
            print(f'  "{k}": {sorted(set(v))},')

    Path(a.json).write_text(
        json.dumps(
            [{k: v for k, v in r.items() if k != "titres"} for r in trouves],
            ensure_ascii=False,
            indent=1,
        ),
        encoding="utf-8",
    )
    print(f"\n-> rapport : {Path(a.json).name}")
    return 0


def _tous_les_titres(kind, slug):
    """Tous les intitules du flux (probe_ats.titles n'en rend que 3)."""
    import httpx

    try:
        r = httpx.get(
            probe_ats.APIS[kind](slug), timeout=20, headers=probe_ats.UA, follow_redirects=True
        )
        if r.status_code != 200:
            return []
        d = r.json()
    except Exception:
        return []
    try:
        if kind == "greenhouse":
            return [j.get("title", "") for j in d.get("jobs", [])]
        if kind == "lever":
            return [j.get("text", "") for j in d]
        if kind == "ashby":
            return [j.get("title", "") for j in d.get("jobs", [])]
        if kind == "recruitee":
            return [j.get("title", "") for j in d.get("offers", [])]
        if kind == "smartrecruiters":
            return [j.get("name", "") for j in d.get("content", [])]
    except Exception:
        pass
    return []


if __name__ == "__main__":
    sys.exit(main())
