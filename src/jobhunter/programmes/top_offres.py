#!/usr/bin/env python3
"""top_offres.py — Les N offres a traiter MAINTENANT, pas les N meilleurs scores.

Le fit seul ne suffit pas a decider. Une offre a fit 10 est inutile si son lien
ouvre la page d'accueil de l'entreprise, si elle demande dix ans d'experience,
si l'utilisateur y a deja postule, ou si elle est a Brest. Ce programme applique les
filtres d'ACTIONNABILITE avant de trier.

REJETS, chacun tire d'un cas reel :
  - lien non direct : « BNP Paribas AM » a fit 10 pointait sur /careers/, et
    « LinkedIn Jobs FR — Analyste ESG / Finance France » sur une page de
    resultats. Un lien qui n'ouvre pas l'annonce ne se traite pas ce matin.
  - doublon : la meme annonce Credit Agricole apparaissait quatre fois, sous
    « Credit Agricole CIB » et « Credit Agricole S.A. ». On garde la mieux
    classee par source.
  - deja postule (suivi.json), deja ecartee (exclusions.json).
  - experience exigee > 3 ans, contrat alternance/stage, hors zone.
  - pas de description : le fit est alors calcule sur le seul intitule.

Run :
  python JobHunter.pyw top_offres
  python JobHunter.pyw top_offres --n 20 --zone prioritaire
"""

import argparse
import importlib
import re
import sys
from urllib.parse import urlparse

from jobhunter import racine as _racine

HERE = _racine.scripts()

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from jobhunter.sources import contrat_du_titre, contrats_exclus, rang_source

# Intitule qui parle vraiment du metier vise, et niveau d'entree.
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

# Derniers segments qui designent une rubrique, donc une liste de postes.
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

# L'employeur est le SITE lui-meme : la ligne n'est pas une annonce mais une
# page de listing curee a la main (« LinkedIn Jobs FR — Analyste ESG / Finance
# France », lien /jobs/analyste-esg-emplois). Le chemin a deux segments la
# faisait passer pour une annonce.
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
    """Le lien ouvre-t-il L'ANNONCE, et pas une liste ?"""
    u = str(url or "")
    if not u.startswith("http"):
        return False
    d = urlparse(u)
    if _RX_RECHERCHE.search(d.query or ""):
        return False
    seg = [c for c in (d.path or "").split("/") if c]
    if not seg:  # racine du domaine = page d'accueil
        return False
    if seg[-1].lower().strip("-_") in _RUBRIQUES:
        return False
    # Une annonce porte un identifiant : un chemin profond, ou un nombre.
    return len(seg) >= 2 or any(c.isdigit() for c in "".join(seg))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--zone", default="", help="prioritaire | secondaire")
    ap.add_argument("--fit-min", type=int, default=9)
    a = ap.parse_args()

    from jobhunter.stockage import file as queue_io

    q = queue_io.charger()
    try:
        suivi = importlib.import_module("jobhunter.stockage.suivi").charger(HERE / "suivi.json")
    except Exception:
        suivi = {}
    try:
        from jobhunter.programmes import exclusions

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
        # Le statut « mauvaise » est le jugement de l'utilisateur sur l'offre. Sans ce
        # test, une offre qu'il vient d'ecarter dans l'app reviendrait en tete
        # du classement au prochain appel — et il la recarterait, indefiniment.
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

    # DEDUPLICATION. La meme annonce revient sous plusieurs raisons sociales
    # (« Credit Agricole CIB » et « Credit Agricole S.A. »). L'intitule normalise
    # suffit a les rapprocher ; on garde le lien le mieux classe.
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
            s += 30  # ESG dans l'INTITULE, pas seulement dans le texte
        if RX_JUNIOR.search(t):
            s += 12
        if o.get("zone") == "prioritaire":
            s += 8
        s += rang_source(o.get("url")) * 2  # lien employeur > agregateur
        # Le PREMIER secteur prioritaire du profil passe devant les autres.
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
