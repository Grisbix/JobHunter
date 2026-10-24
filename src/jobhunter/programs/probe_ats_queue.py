#!/usr/bin/env python3
"""probe_ats_queue.py — Which companies of the queue expose a readable ATS feed?

WHY. Going up to the employer's site through navigation does not work: measured 0 out
of 27 (measurement of the old offres_depuis_site, removed in 2.7). The ATS APIs, on
the other hand, return JSON with the posting's direct URL AND its description, without
a browser or anti-bot.

This program starts from the companies ALREADY in the queue — not from a guessed list
like probe_ats.py — and counts the offers that pass the relevance filter
(`job_sources.title_ok`). A feed of 1120 offers none of which matches the profile is
worth nothing: it is the number AFTER the filter that decides.

Changes NOTHING. Writes a JSON report; adding to sources_config.json stays an
explicit decision.

Run:
  python JobHunter.pyw probe_ats_queue --fit 8          # companies of the offers with fit >= 8
  python JobHunter.pyw probe_ats_queue --fit 0          # all of them
  python JobHunter.pyw probe_ats_queue --json out.json
"""

import argparse
import collections
import concurrent.futures as cf
import json
import re
import sys
import unicodedata
from pathlib import Path

from jobhunter import root as _racine

HERE = _racine.scripts()

sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)  # type: ignore[union-attr]  # console : TextIOWrapper

from jobhunter.programs import probe_ats
from jobhunter.sources.common import title_ok
from jobhunter.sources.merge import rang_source
from jobhunter.storage import queue as queue_io

# Words that are not part of an ATS slug.
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
    """Plausible slugs for a company. The ATS impose no convention:
    "Credit Agricole" can be creditagricole, credit-agricole, or credit."""
    n = unicodedata.normalize("NFD", (nom or "").lower())
    n = "".join(c for c in n if not unicodedata.combining(c))
    mots = [m for m in re.split(r"[^a-z0-9]+", n) if m]
    utiles = [m for m in mots if m not in BRUIT] or mots
    if not utiles:
        return []
    out = ["".join(utiles), "-".join(utiles)]
    if len(utiles) > 1:
        out.append(utiles[0])  # "alten" for "Alten Group"
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
    ap.add_argument(
        "--ajouter",
        action="store_true",
        help="suivre les flux CONFIRMES (sources_config.json) ; les autres restent au rapport",
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

    essais = {}  # slug -> company name (the 1st that proposes it)
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

    # How many offers REALLY pass the profession filter?
    print(f"\n{len(trouves)} flux actif(s) — comptage des offres pertinentes…")
    vus = titres_par_entreprise(q)
    for r in trouves:
        titres = _tous_les_titres(r["ats"], r["slug"])
        r["titres_total"] = len(titres)
        r["pertinents"] = [t for t in titres if title_ok(t)]
        r["confirme"] = confirme(titres, vus.get(r["entreprise"], set()))

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
            f"{r['slug']:22} {r['entreprise'][:26]}" + ("  ✓ confirmé" if r["confirme"] else "")
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

    if a.ajouter:
        ajouter([r for r in utiles if r["confirme"]])

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


def titres_par_entreprise(q):
    """{company: its offer titles in the queue, normalised}."""
    vus = collections.defaultdict(set)
    for o in q:
        if o.get("entreprise") and o.get("poste"):
            vus[o["entreprise"].strip()].add(_norme(o["poste"]))
    return vus


def _norme(titre):
    return re.sub(r"\s+", " ", (titre or "").strip().lower())


def confirme(titres_flux, titres_vus):
    """Is the feed really this company's? One of its offers seen in the queue is in it.

    A slug guessed from the name can belong to another company: "aura" is not
    AURA-AERO, "blue" is not Blue Origin (measured 2026-10-24, aerospace profile).
    """
    return bool(titres_vus & {_norme(t) for t in titres_flux})


def ajouter(confirmes):
    """Follows the confirmed feeds: added to sources_config.json, read at the next collection.

    Every API probed here (probe_ats.APIS) is read from `ats_slugs`. A missing
    `ats_slugs` means "the shipped lists": it is seeded with them before adding.
    """
    from jobhunter.sources import common as _src

    if not confirmes:
        print("\nAucun flux confirmé : rien d'ajouté.")
        return
    cfg_p = HERE / "sources_config.json"
    try:
        cfg = json.loads(cfg_p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        cfg = {}
    if "ats_slugs" not in cfg:
        cfg["ats_slugs"] = {k: list(v) for k, v in _src.ATS_SLUGS.items()}
    print()
    for r in confirmes:
        slugs = cfg["ats_slugs"].setdefault(r["ats"], [])
        if any(str(x).lower() == r["slug"].lower() for x in slugs):
            print(f"déjà suivi : {r['ats']} {r['slug']} ({r['entreprise']})")
            continue
        slugs.append(r["slug"])
        print(f"＋ flux {r['ats']} {r['slug']} — lu dès la prochaine collecte ({r['entreprise']})")
    tmp = cfg_p.with_name(cfg_p.name + ".tmp")
    tmp.write_text(json.dumps(cfg, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(cfg_p)


def _tous_les_titres(kind, slug):
    """All the titles of the feed (probe_ats.titles only returns 3)."""
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
