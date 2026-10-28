"""EURES: the official job portal of the European Union.

Part of jobhunter.sources (formerly Scripts/job_sources.py, phase 3.4).
"""

import re
import time
from typing import Any

from jobhunter import log as _journal
from jobhunter.sources import common as _commun
from jobhunter.sources import keywords as _mots
from jobhunter.sources.common import INCIDENTS, UA, _mk, _strip_html, contrat_du_titre, title_ok
from jobhunter.sources.efc import _RX_EFC_ESG, _RX_EFC_SENIOR, _est_graduate

_log = _journal.journal(__name__)


# ═══════════════ 9. EURES — the OFFICIAL job portal of the European Union ═══
# WHY. 96 % of the foreign offers in the queue came from the LinkedIn
# "Worldwide" search alone, capped at 12 pages per keyword and drowned under the
# Indian and American volume. EURES aggregates the public employment services of the
# 30 EEA countries, description included, in JSON.
#
# WHAT IS ALLOWED (checked on 2026-09-24). europa.eu's robots.txt closes
# neither /eures/api/ nor /eures/portal/, and declares `crawl-delay: 10`, respected here.
# The API is the one the public portal calls itself, without authentication.
#
# TRAP: the search is BROAD. "ESG analyst" returns 255,000 results over one
# week: the keyword is searched in the description, and the "ESG" of
# German industrial purchasing come up. The BEST_MATCH ranking puts the good ones
# first; so we only read one page per keyword, and the title must pass
# eFC's profession filter (analyst, risk, ESG… and not senior).
EURES_URL = "https://europa.eu/eures/api/jv-searchengine/public/jv-search/search"

EURES_FICHE = "https://europa.eu/eures/portal/jv-se/jv-details/{}?lang=en"

EURES_DELAI = 10  # europa.eu crawl-delay — do not lower

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

# EURES country codes -> English name, which zones.py recognises.
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

# In German, "ESG" is also safety glass (Einscheiben-
# Sicherheitsglas) : « Produktionsmitarbeiter ESG-Herstellung » remontait.
_RX_EURES_VERRE = re.compile(r"\bESG-?(?:fertigung|herstellung|glas)|einscheiben", re.I)

# Off-target professions that "sustainability" brings up at EURES — purchasing,
# engineering, sales, HSE, management — measured on 2026-09-24. fit_score rates them
# 9 or 10 (the word is enough to lift the ESG cap): so they must be
# set aside HERE, a filter on the fit would not catch them.
_RX_EURES_HORS = re.compile(
    r"procurement|einkauf|beschaffung|engineer|ingenieur|vertrieb|\bsales\b"
    r"|leiter|leitung|\blead\b|\bhse\b|\bqhse\b|athlete|bioeng|produktion"
    r"|circular economy",
    re.I,
)

# Employer hidden by the advertiser: we do not invent it.
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


def _parle_de(titre: str, mots: list[str]) -> bool:
    """The title holds the first word of one of the searched phrases (« moniteur » de ski)."""
    t = titre.lower()
    return any(
        re.search(r"\b" + re.escape(m.split()[0].lower()) + r"\b", t) for m in mots if m.split()
    )


def _eures_offre(j: Any, _EX: Any, mots: list[str] | None = None) -> dict[str, Any] | None:
    """One EURES posting -> offer, or None if the title does not fit.

    Args:
        j: the posting.
        _EX: the contract types set aside.
        mots: the words searched, when they are the profile's: the title must then
            name one of them, instead of ESG or sustainability.
    """
    titre = __import__("html").unescape(str(j.get("title") or "")).strip()
    # STRICT FILTER, measured on 2026-09-24. With eFC's profession filter alone,
    # 55 of the 61 offers kept were generic German "Data Analyst" or "Business
    # Analyst" jobs, rated 1 or 2: the keyword is searched
    # in the DESCRIPTION. So we require the TITLE to talk about ESG or
    # sustainability, or to be a graduate programme.
    if not titre or not title_ok(titre) or _RX_EFC_SENIOR.search(titre):
        return None
    if mots:
        if not _parle_de(titre, mots):
            return None
    elif not (_RX_EFC_ESG.search(titre) or _est_graduate(titre)) or _RX_EURES_VERRE.search(titre):
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
    """EURES offers of the last week, one page per keyword by default."""
    import httpx

    _EX = _commun.contrats_exclus()
    offers, vus = [], set()
    n_req = 0
    with httpx.Client(follow_redirects=True) as client:
        cherches = mots or _mots.mots("eures", EURES_MOTS, len(EURES_MOTS))
        # The strict ESG title filter belongs to the module's own words (measured 2026-09-24).
        du_profil = [m.lower() for m in cherches] != [m.lower() for m in EURES_MOTS]
        for mot in cherches:
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
                    o = _eures_offre(j, _EX, cherches if du_profil else None)
                    if o:
                        offers.append(o)
                        garde += 1
                _log.info(f"    « {mot} » p{page} : {len(jvs)} lues, {garde} retenues")
                if len(jvs) < par_page:
                    break
    _log.info(f"  ✓ EURES → {len(offers)} offres (avec description)")
    return offers
