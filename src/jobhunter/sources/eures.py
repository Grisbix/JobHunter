"""EURES : le portail d'emploi officiel de l'Union europeenne.

Partie de jobhunter.sources (ancien Scripts/job_sources.py, phase 3.4).
"""

import re
import time
from typing import Any

from jobhunter import journal as _journal
from jobhunter.sources import commun as _commun
from jobhunter.sources.commun import INCIDENTS, UA, _mk, _strip_html, contrat_du_titre, title_ok
from jobhunter.sources.efc import _RX_EFC_ESG, _RX_EFC_SENIOR, _est_graduate

_log = _journal.journal(__name__)


# ═══════════════ 9. EURES — le portail d'emploi OFFICIEL de l'Union europeenne ═══
# POURQUOI. 96 % des offres etrangeres de la file venaient de la seule recherche
# LinkedIn « Worldwide », plafonnee a 12 pages par mot-cle et noyee sous le
# volume indien et americain. EURES agrege les services publics de l'emploi des
# 30 pays de l'EEE, description comprise, en JSON.
#
# CE QUI EST AUTORISE (verifie le 2026-09-24). robots.txt de europa.eu ne ferme
# ni /eures/api/ ni /eures/portal/, et declare `crawl-delay: 10`, respecte ici.
# L'API est celle que le portail public appelle lui-meme, sans authentification.
#
# PIEGE : la recherche est LARGE. « ESG analyst » rend 255 000 resultats sur une
# semaine : le mot-cle est cherche dans la description, et les « ESG » des
# achats industriels allemands remontent. Le classement BEST_MATCH met les bons
# en tete ; on ne lit donc qu'une page par mot-cle, et l'intitule doit passer
# le filtre metier d'eFC (analyste, risque, ESG… et pas senior).
EURES_URL = "https://europa.eu/eures/api/jv-searchengine/public/jv-search/search"

EURES_FICHE = "https://europa.eu/eures/portal/jv-se/jv-details/{}?lang=en"

EURES_DELAI = 10  # crawl-delay de europa.eu — ne pas baisser

EURES_MOTS = [
    "ESG analyst",
    "sustainable finance",
    "sustainability analyst",
    "climate risk analyst",
    "green bonds",
    "impact investing",
    "responsible investment",
    "graduate programme sustainability",
]

# Codes pays EURES -> nom anglais, que zones.py reconnait.
_EURES_PAYS = {
    "AT": "Austria",
    "BE": "Belgium",
    "BG": "Bulgaria",
    "HR": "Croatia",
    "CY": "Cyprus",
    "CZ": "Czech Republic",
    "DK": "Denmark",
    "EE": "Estonia",
    "FI": "Finland",
    "FR": "France",
    "DE": "Germany",
    "GR": "Greece",
    "EL": "Greece",
    "HU": "Hungary",
    "IS": "Iceland",
    "IE": "Ireland",
    "IT": "Italy",
    "LV": "Latvia",
    "LI": "Liechtenstein",
    "LT": "Lithuania",
    "LU": "Luxembourg",
    "MT": "Malta",
    "NL": "Netherlands",
    "NO": "Norway",
    "PL": "Poland",
    "PT": "Portugal",
    "RO": "Romania",
    "SK": "Slovakia",
    "SI": "Slovenia",
    "ES": "Spain",
    "SE": "Sweden",
    "CH": "Switzerland",
}

# En allemand, « ESG » est aussi le verre de securite (Einscheiben-
# Sicherheitsglas) : « Produktionsmitarbeiter ESG-Herstellung » remontait.
_RX_EURES_VERRE = re.compile(r"\bESG-?(?:fertigung|herstellung|glas)|einscheiben", re.I)

# Metiers hors cible que « sustainability » fait remonter chez EURES — achats,
# ingenierie, commerce, HSE, direction — mesures le 2026-09-24. fit_score les
# note 9 ou 10 (le mot suffit a lever le plafond ESG) : il faut donc les
# ecarter ICI, un filtre sur le fit ne les retiendrait pas.
_RX_EURES_HORS = re.compile(
    r"procurement|einkauf|beschaffung|engineer|ingenieur|vertrieb|\bsales\b"
    r"|leiter|leitung|\blead\b|\bhse\b|\bqhse\b|athlete|bioeng|produktion"
    r"|circular economy",
    re.I,
)

# Employeur masque par l'annonceur : on ne l'invente pas.
_RX_EURES_ANONYME = re.compile(
    r"siehe beschreibung|confidential|non renseign|not specified|anonym|see description"
    r"|voir (?:la )?description|^\W*$",
    re.I,
)


def _eures_corps(mot: str, page: int, par_page: int) -> dict[str, Any]:
    return {
        "resultsPerPage": par_page,
        "page": page,
        "sortSearch": "BEST_MATCH",
        "keywords": [{"keyword": mot, "specificSearchCode": "EVERYWHERE"}],
        "publicationPeriod": "LAST_WEEK",
        "occupationUris": [],
        "skillUris": [],
        "requiredExperienceCodes": [],
        "positionScheduleCodes": [],
        "sectorCodes": [],
        "educationAndQualificationLevelCodes": [],
        "positionOfferingCodes": [],
        "locationCodes": [],
        "euresFlagCodes": [],
        "otherBenefitsCodes": [],
        "requiredLanguages": [],
        "minNumberPost": None,
        "sessionId": "jobhunter",
    }


def _eures_offre(j: Any, _EX: Any) -> dict[str, Any] | None:
    """Une annonce EURES -> offre, ou None si l'intitule ne convient pas."""
    titre = __import__("html").unescape(str(j.get("title") or "")).strip()
    # FILTRE STRICT, mesure le 2026-09-24. Avec le seul filtre metier d'eFC,
    # 55 des 61 offres retenues etaient des « Data Analyst » ou « Business
    # Analyst » allemands generiques, notees 1 ou 2 : le mot-cle est cherche
    # dans la DESCRIPTION. On exige donc que l'INTITULE parle d'ESG ou de
    # durabilite, ou qu'il s'agisse d'un programme jeunes diplomes.
    if not titre or not title_ok(titre) or _RX_EFC_SENIOR.search(titre):
        return None
    if not (_RX_EFC_ESG.search(titre) or _est_graduate(titre)) or _RX_EURES_VERRE.search(titre):
        return None
    if _RX_EURES_HORS.search(titre):
        return None
    if contrat_du_titre(titre) in _EX:
        return None
    loc = j.get("locationMap") or {}
    code = next(iter(loc), "") if isinstance(loc, dict) else ""
    lieu = _EURES_PAYS.get(code.upper(), code)
    soc = str((j.get("employer") or {}).get("name") or "").strip()
    if _RX_EURES_ANONYME.search(soc):
        soc = "Employeur non précisé (EURES)"
    date = ""
    try:
        date = time.strftime("%Y-%m-%d", time.gmtime(int(j.get("creationDate")) / 1000))
    except Exception:
        pass
    return _mk(
        titre,
        EURES_FICHE.format(j.get("id")),
        soc,
        lieu,
        date,
        "eures",
        _strip_html(str(j.get("description") or "")),
    )


def scan_eures(
    pages: int = 1, par_page: int = 50, mots: list[str] | None = None
) -> list[dict[str, Any]]:
    """Offres EURES de la derniere semaine, une page par mot-cle par defaut."""
    import httpx

    _EX = _commun.contrats_exclus()
    offers, vus = [], set()
    n_req = 0
    with httpx.Client(follow_redirects=True) as client:
        for mot in mots or EURES_MOTS:
            for page in range(1, pages + 1):
                if n_req:
                    time.sleep(EURES_DELAI)  # crawl-delay: 10
                n_req += 1
                try:
                    r = _commun._post_borne(
                        client,
                        EURES_URL,
                        json=_eures_corps(mot, page, par_page),
                        headers={
                            **UA,
                            "Content-Type": "application/json",
                            "Accept": "application/json",
                        },
                        timeout=40,
                    )
                except Exception as e:
                    INCIDENTS["eures"][type(e).__name__] += 1
                    break
                if r.status_code != 200:
                    INCIDENTS["eures"][f"HTTP {r.status_code}"] += 1
                    break
                jvs = (r.json() or {}).get("jvs") or []
                garde = 0
                for j in jvs:
                    if j.get("id") in vus:
                        continue
                    vus.add(j.get("id"))
                    o = _eures_offre(j, _EX)
                    if o:
                        offers.append(o)
                        garde += 1
                _log.info(f"    « {mot} » p{page} : {len(jvs)} lues, {garde} retenues")
                if len(jvs) < par_page:
                    break
    _log.info(f"  ✓ EURES → {len(offers)} offres (avec description)")
    return offers
