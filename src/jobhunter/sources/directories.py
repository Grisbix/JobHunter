"""The large employers of the profile's country, from open directories, into the register.

The register of companies seen (storage.companies) only knew the companies a
collection had met. This adds the country's large employers, ranked by headcount, so
that the career-site pass (company_sites, morning pass 1f) asks them too:

- Wikidata, for any country: companies with a headcount (P1128) of 500 or more, their
  website (P856) and industry (P452). One public SPARQL query, by country code.
- in France, the SIRENE directory (recherche-entreprises.api.gouv.fr, public, no key):
  companies of 1,000 employees or more, by activity section.

Only the industries of the profile's job families are kept (a nurse gets hospitals,
an analyst banks and insurers); a company whose industry is unknown is kept after
them. The directories never touch the queue: they only add names to the register,
and the career-site pass then asks each company what it has open.

    python -m jobhunter companies-import            # the profile's country, 300 at most
    python -m jobhunter companies-import --n 1000 --tous-secteurs --dry
"""

from __future__ import annotations

import argparse
import sys
import time
from typing import Any

from jobhunter import network as _reseau
from jobhunter.sources import common as _commun

UA = {"User-Agent": "Grisbix/JobHunter (+https://github.com/Grisbix/JobHunter)"}
WIKIDATA = "https://query.wikidata.org/sparql"
SIRENE = "https://recherche-entreprises.api.gouv.fr/search"
PAUSE = 1.0  # seconds between two requests to the same directory

# Job family → (words of the Wikidata industries in English, SIRENE activity sections).
# A family absent here (legal, HR, sales, project) works in every industry: no filter.
SECTEURS: dict[str, tuple[tuple[str, ...], str]] = {
    "finance": (("financ", "bank", "insurance", "invest", "asset", "credit"), "K"),
    "rse": (("energy", "renewable", "environment", "sustainab", "utilit", "waste"), "DEM"),
    "conseil": (("consult", "professional services", "audit", "accounting"), "M"),
    "dev": (
        ("software", "information technology", "internet", "computer", "telecom", "video game"),
        "J",
    ),
    "data": (("software", "information technology", "internet", "computer", "telecom"), "JK"),
    "sante": (("hospital", "health", "pharma", "medical", "biotech", "care"), "Q"),
    "ingenierie": (
        ("engineering", "automotive", "aerospace", "manufactur", "industr", "chemical"),
        "CF",
    ),
    "marketing": (("advertis", "media", "retail", "consumer", "fashion", "publishing"), "GJ"),
    "logistique": (("logistic", "transport", "shipping", "freight", "postal", "rail"), "H"),
    "design": (("design", "architecture", "fashion", "media", "video game", "publishing"), "MR"),
    "enseignement": (("education", "university", "school", "research"), "P"),
}


def familles_du_profil(n: int = 2) -> list[str]:
    """The profile's `n` main job families, from its title words (first_launch's scoring)."""
    from jobhunter import profile as _P
    from jobhunter.programs.first_launch import familles_visees

    mots = [
        p
        for x in (_P.get("filtre_titre.metier", []) or [])
        if isinstance(x, str) and not x.startswith("re:")
        for p in x.replace(" + ", " / ").split(" / ")
    ]
    mots += [str(d.get("libelle") or "") for d in _P.get("domaines", []) or []]
    mots += [
        x
        for x in (_P.get("scoring.intitules_coeur", []) or [])
        if isinstance(x, str) and ":" not in x
    ]
    ordre, _ = familles_visees([m.replace("_", " ") for m in mots], {})
    return [str(f) for f in ordre[:n]]


def filtre(familles: list[str]) -> tuple[tuple[str, ...], str] | None:
    """(industry words, SIRENE sections) of the families; None = every industry."""
    if not familles or any(f not in SECTEURS for f in familles):
        return None
    mots = tuple(m for f in familles for m in SECTEURS[f][0])
    sections = "".join(dict.fromkeys("".join(SECTEURS[f][1] for f in familles)))
    return mots, sections


def _requete_wikidata(iso: str, minimum: int, maximum: int | None) -> str:
    plafond = f" && ?e < {maximum}" if maximum else ""
    return f"""
SELECT ?c ?cLabel (MAX(?e) AS ?emp) (SAMPLE(?s) AS ?site)
       (GROUP_CONCAT(DISTINCT ?iL; separator="|") AS ?ind) WHERE {{
  ?pays wdt:P297 "{iso.upper()}".
  ?c wdt:P17 ?pays; wdt:P1128 ?e.
  FILTER(?e >= {minimum}{plafond})
  OPTIONAL {{ ?c wdt:P856 ?s. }}
  OPTIONAL {{ ?c wdt:P452 ?i. ?i rdfs:label ?iL. FILTER(LANG(?iL) = "en") }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en,{iso.lower()}". }}
}}
GROUP BY ?c ?cLabel
ORDER BY DESC(?emp) LIMIT 2000
"""


def lignes_wikidata(donnees: dict[str, Any]) -> list[dict[str, Any]]:
    """The SPARQL answer as companies {nom, effectif, site_web, secteurs, source}."""
    out: list[dict[str, Any]] = []
    vus: set[str] = set()
    for b in (donnees.get("results") or {}).get("bindings") or []:
        nom = str((b.get("cLabel") or {}).get("value") or "").strip()
        # An item without a label in these languages comes back as its id (« Q123 »).
        if not nom or (nom[0] == "Q" and nom[1:].isdigit()) or nom.casefold() in vus:
            continue
        vus.add(nom.casefold())
        try:
            effectif = int(float((b.get("emp") or {}).get("value") or 0))
        except ValueError:
            effectif = 0
        secteurs = [s for s in str((b.get("ind") or {}).get("value") or "").split("|") if s]
        out.append(
            {
                "nom": nom,
                "effectif": effectif,
                "site_web": str((b.get("site") or {}).get("value") or ""),
                "secteurs": secteurs,
                "source": "wikidata",
            }
        )
    return out


# Headcount bands, largest first: one query per band stays under the service's minute
# (a single query for the United States did not, one time in two).
TRANCHES = ((20000, None), (5000, 20000), (2000, 5000), (1000, 2000), (500, 1000))


def wikidata(iso: str) -> list[dict[str, Any]]:
    """The country's companies of 500+ employees, largest first.

    Asked band by band; a band that fails (timeout) is asked once more, then skipped:
    the others still count. A refusal (403, 429) stops there.
    """
    import httpx

    out: list[dict[str, Any]] = []
    for bas, haut in TRANCHES:
        for essai in range(2):
            if out or essai:
                time.sleep(PAUSE * (5 if essai else 2))
            try:
                r = _reseau.get_borne(
                    httpx,
                    WIKIDATA,
                    params={"query": _requete_wikidata(iso, bas, haut), "format": "json"},
                    headers={**UA, "Accept": "application/sparql-results+json"},
                    timeout=70,
                    total=90,
                )
            except (httpx.HTTPError, ValueError):
                continue
            if r.status_code in (403, 429):
                return out
            if r.status_code == 200:
                try:
                    lot = lignes_wikidata(r.json())
                except ValueError:
                    continue
                vus = {e["nom"].casefold() for e in out}
                out.extend(e for e in lot if e["nom"].casefold() not in vus)
                break
    return out


def lignes_sirene(donnees: dict[str, Any]) -> list[dict[str, Any]]:
    """A SIRENE answer page as companies."""
    out = []
    for x in donnees.get("results") or []:
        nom = str(x.get("nom_raison_sociale") or x.get("nom_complet") or "").strip()
        if nom:
            out.append(
                {
                    "nom": nom,
                    "effectif": 0,
                    "site_web": "",
                    "secteurs": [str(x.get("activite_principale") or "")],
                    "source": "sirene",
                    "tranche": str(x.get("tranche_effectif_salarie") or ""),
                }
            )
    return out


def sirene(sections: str = "", limite: int = 400) -> list[dict[str, Any]]:
    """French companies of 1,000+ employees, in these activity sections ("" = all)."""
    import httpx

    out: list[dict[str, Any]] = []
    params: dict[str, Any] = {
        "tranche_effectif_salarie": "42,51,52,53",
        "etat_administratif": "A",
        "per_page": 25,
    }
    if sections:
        params["section_activite_principale"] = ",".join(sections)
    page = 1
    while len(out) < limite:
        try:
            r = _reseau.get_borne(
                httpx, SIRENE, params={**params, "page": page}, headers=UA, timeout=30, total=60
            )
        except httpx.HTTPError:
            break
        if r.status_code != 200:
            break
        d = r.json()
        lot = lignes_sirene(d)
        out.extend(lot)
        if not lot or page >= int(d.get("total_pages") or 1):
            break
        page += 1
        time.sleep(PAUSE)
    return out[:limite]


def du_secteur(
    entreprises: list[dict[str, Any]], f: tuple[tuple[str, ...], str] | None
) -> list[dict[str, Any]]:
    """The companies of the families' industries first, then those of unknown industry.

    Those of another known industry are left out; `f` None keeps them all.
    """
    if f is None:
        return list(entreprises)
    mots, _ = f
    dedans, inconnues = [], []
    for e in entreprises:
        if e["source"] == "sirene":  # already chosen by activity section
            dedans.append(e)
            continue
        s = " ".join(e.get("secteurs") or []).lower()
        if not s:
            inconnues.append(e)
        elif any(m in s for m in mots):
            dedans.append(e)
    return dedans + inconnues


def importer(n: int = 300, tous_secteurs: bool = False, dry: bool = False) -> dict[str, int]:
    """Adds the profile's country's large employers to the register.

    Returns:
        {"lus": read in the directories, "gardes": of the families' industries,
        "ajoutes": new in the register}.
    """
    from jobhunter.sources import countries
    from jobhunter.storage import companies
    from jobhunter.storage import lock as verrou

    iso = countries.maison()
    f = None if tous_secteurs else filtre(familles_du_profil())
    lus = wikidata(iso)
    if iso == "fr":
        time.sleep(PAUSE)
        lus = sirene(f[1] if f else "") + lus
    gardes = du_secteur(lus, f)[:n]
    if dry:
        reg = companies.charger(_commun.QUEUE)
        nouveaux = sum(1 for e in gardes if companies.cle(e["nom"]) not in reg)
        return {"lus": len(lus), "gardes": len(gardes), "ajoutes": nouveaux}
    if not verrou.prendre_verrou(_commun.QUEUE, attente=180):
        raise RuntimeError("la file est occupée par un autre programme — rien n'a été ajouté")
    try:
        ajoutes = companies.ajouter_annuaire(_commun.QUEUE, gardes)
    finally:
        verrou.rendre_verrou(_commun.QUEUE)
    return {"lus": len(lus), "gardes": len(gardes), "ajoutes": ajoutes}


def main() -> int:
    """The command line: `python -m jobhunter companies-import`."""
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    ap = argparse.ArgumentParser(
        description="Adds the large employers of the profile's country (Wikidata, SIRENE "
        "in France) to the register of companies the career-site pass asks."
    )
    ap.add_argument("--n", type=int, default=300, help="companies added at most (300)")
    ap.add_argument(
        "--tous-secteurs", action="store_true", help="every industry, not only the profile's"
    )
    ap.add_argument("--dry", action="store_true", help="count only, write nothing")
    a = ap.parse_args()
    from jobhunter.sources import countries

    print(f"Annuaires — {countries.nom()} · familles : {', '.join(familles_du_profil()) or '—'}")
    try:
        r = importer(a.n, a.tous_secteurs, a.dry)
    except RuntimeError as e:
        print(f"  {e}")
        return 3
    print(
        f"  {r['lus']} entreprises lues · {r['gardes']} gardées · "
        f"{r['ajoutes']} {'à ajouter' if a.dry else 'ajoutées'} au registre"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
