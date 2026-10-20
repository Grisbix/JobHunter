#!/usr/bin/env python3
"""top_offres.py — The N offers to handle NOW, not the N best scores.

The fit alone is not enough to decide. A fit-10 offer is useless if its link opens the
company's home page, if it asks for ten years of experience, if the user already
applied to it, or if it is in Brest. This program applies the ACTIONABILITY filters
before sorting.

REJECTIONS, each drawn from a real case:
  - non-direct link: "BNP Paribas AM" at fit 10 pointed to /careers/, and
    "LinkedIn Jobs FR — Analyste ESG / Finance France" to a results page. A link that
    does not open the posting is not handled this morning.
  - duplicate: the same Credit Agricole posting appeared four times, under
    "Credit Agricole CIB" and "Credit Agricole S.A.". We keep the one best ranked by
    source.
  - already applied (suivi.json), already set aside (exclusions.json).
  - experience required > 3 years, work-study/internship contract, out of zone.
  - no description: the fit is then computed on the title alone.

Run:
  python JobHunter.pyw top_offres
  python JobHunter.pyw top_offres --n 20 --zone prioritaire
"""

import argparse
import importlib
import re
import sys
from urllib.parse import urlparse

from jobhunter import root as _racine

HERE = _racine.scripts()

sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]  # console : TextIOWrapper

from jobhunter.sources.common import contrat_du_titre, contrats_exclus
from jobhunter.sources.merge import rang_source

# Title that really talks about the target profession, and entry level.
RX_ESG = re.compile(
    r"\bESG\b|\bISR\b|\bRSE\b|\bSFDR\b|\bCSRD\b|extra.?financi"
    r"|durab|sustainab|climat(?!is)|carbone|taxonomie|impact"
    r"|transition [ée]nerg|green",
    re.I,
)
RX_JUNIOR = re.compile(
    r"junior|d[ée]butant|jeune dipl|graduate|analyste|analyst"
    r"|charg[ée]",
    re.I,
)

# Last segments that designate a section, hence a list of jobs.
_RUBRIQUES = {
    "careers",
    "career",
    "carrieres",
    "recrutement",
    "recruitment",
    "jobs",
    "job",
    "offres",
    "emplois",
    "emploi",
    "nous-rejoindre",
    "join-us",
    "home",
    "fr-fr",
}
_RX_RECHERCHE = re.compile(r"(^|&)(query|q|k|keywords?|search|recherche)=", re.I)

# The employer is the SITE itself: the row is not a posting but a
# listing page curated by hand ("LinkedIn Jobs FR — Analyste ESG / Finance
# France", link /jobs/analyste-esg-emplois). The two-segment path
# passed it off as a posting.
_BOARDS = (
    "linkedin",
    "welcome to the jungle",
    "indeed",
    "talent.com",
    "glassdoor",
    "jobijoba",
    "hellowork",
    "monster",
    "apec",
    "efinancialcareers",
    "wizbii",
    "meteojob",
    "cadremploi",
)


def lien_direct(url):
    """Does the link open THE POSTING, and not a list?"""
    u = str(url or "")
    if not u.startswith("http"):
        return False
    d = urlparse(u)
    if _RX_RECHERCHE.search(d.query or ""):
        return False
    seg = [c for c in (d.path or "").split("/") if c]
    if not seg:  # domain root = home page
        return False
    if seg[-1].lower().strip("-_") in _RUBRIQUES:
        return False
    # A posting carries an identifier: a deep path, or a number.
    return len(seg) >= 2 or any(c.isdigit() for c in "".join(seg))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--zone", default="", help="prioritaire | secondaire")
    ap.add_argument("--fit-min", type=int, default=9)
    a = ap.parse_args()

    from jobhunter.storage import queue as queue_io

    q = queue_io.charger()
    try:
        suivi = importlib.import_module("jobhunter.storage.applications").charger(
            _racine.dans(HERE, "suivi.json")
        )
    except Exception:
        suivi = {}
    try:
        from jobhunter.programs import exclusions

        exc = exclusions.charger()
    except Exception:
        exc = {}
    _EX = contrats_exclus()
    zones_ok = {a.zone} if a.zone else {"prioritaire", "secondaire"}

    rejets = {
        "zone": 0,
        "experience": 0,
        "contrat": 0,
        "deja": 0,
        "lien": 0,
        "docs": 0,
        "sans description": 0,
        "fit": 0,
    }
    gardees = []
    for o in q:
        if o.get("zone") not in zones_ok:
            rejets["zone"] += 1
            continue
        if (o.get("exp_requise") or 0) > 3:
            rejets["experience"] += 1
            continue
        c = (o.get("contrat") or "").strip()
        if c in _EX or contrat_du_titre(o.get("poste") or "") in _EX:
            rejets["contrat"] += 1
            continue
        cle = f"{o.get('entreprise', '')}|{o.get('poste', '')}"
        # The "mauvaise" status is the user's judgement on the offer. Without this
        # test, an offer they have just set aside in the app would come back at the top
        # of the ranking at the next call — and they would set it aside again, forever.
        if (suivi.get(cle) or {}).get("s") == "mauvaise":
            rejets["jugee mauvaise"] = rejets.get("jugee mauvaise", 0) + 1
            continue
        if cle in suivi or cle in exc:
            rejets["deja"] += 1
            continue
        if not lien_direct(o.get("url")):
            rejets["lien"] += 1
            continue
        if any(b in (o.get("entreprise") or "").lower() for b in _BOARDS):
            rejets["employeur = site d'offres"] = rejets.get("employeur = site d'offres", 0) + 1
            continue
        if not (o.get("cv") and o.get("lettre")):
            rejets["docs"] += 1
            continue
        if not (o.get("description") or "").strip():
            rejets["sans description"] += 1
            continue
        if (o.get("fit") or 0) < a.fit_min:
            rejets["fit"] += 1
            continue
        gardees.append(o)

    # DEDUPLICATION. The same posting comes back under several company names
    # ("Credit Agricole CIB" and "Credit Agricole S.A."). The normalised title
    # is enough to bring them together; we keep the best-ranked link.
    par_poste = {}
    for o in gardees:
        k = re.sub(r"[^a-z0-9]+", " ", (o.get("poste") or "").lower()).strip()
        autre = par_poste.get(k)
        if autre is None or rang_source(o.get("url")) > rang_source(autre.get("url")):
            par_poste[k] = o
    uniques = list(par_poste.values())

    def note(o):
        t = o.get("poste") or ""
        s = (o.get("fit_fin") or o.get("fit") or 0) * 10  # fit_fin : decimal, departage
        if RX_ESG.search(t):
            s += 30  # ESG in the TITLE, not only in the text
        if RX_JUNIOR.search(t):
            s += 12
        if o.get("zone") == "prioritaire":
            s += 8
        s += rang_source(o.get("url")) * 2  # lien employeur > agregateur
        # The FIRST priority sector of the profile goes before the others.
        _sz = importlib.import_module("jobhunter.scoring.zones").sous_zone(
            o.get("localisation") or ""
        )
        if _sz and _sz == (
            importlib.import_module("jobhunter.scoring.zones").SECTEURS_PRIORITAIRES or [{}]
        )[0].get("cle"):
            s += 15
        return s

    uniques.sort(key=lambda o: -note(o))
    print(f"{len(q)} offres → {len(gardees)} actionnables → {len(uniques)} apres dedoublonnage\n")
    print("écartées : " + " · ".join(f"{v} {k}" for k, v in rejets.items() if v) + "\n")
    for i, o in enumerate(uniques[: a.n], 1):
        print(
            f"{i:2}. {(o.get('entreprise') or '')[:34]}  —  fit {o.get('fit')}"
            f"{' · ' + str(o['exp_requise']) + ' ans demandés' if o.get('exp_requise') else ''}"
        )
        print(f"    {(o.get('poste') or '')[:72]}")
        print(f"    {(o.get('localisation') or '')[:36]} · {o.get('contrat') or 'non précisé'}")
        print(f"    {o.get('url')}")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
