"""Bundesagentur für Arbeit: Germany's public employment service, by its search API.

The user, 2026-10-27, after reading career-ops (github.com/career-ops-hq/career-ops,
MIT): « ne te limite pas à la France ». The Jobsuche API is the one arbeitsagentur.de
itself calls; its client key, `jobboerse-jobsuche`, is the public one of that site
(documented by bund.dev), not an account. No login, no browser: one GET per keyword.
A sample on 2026-10-27: 311 « ESG » postings in 30 days (Frankfurt, Munich, Berlin…).

Since 2026-08 the API is v6 (v4 and v5 answer 404): `referenznummer`,
`stellenangebotsTitel`, `firma`, `stellenlokationen[]`. The list gives no description;
the offer page is arbeitsagentur.de's own, by its reference number. Postings in
Austria or Switzerland come through too (`land`).
"""

import time
from typing import Any
from urllib.parse import quote

from jobhunter import log as _journal
from jobhunter.sources import common as _commun
from jobhunter.sources import keywords as _mots
from jobhunter.sources.aggregators import AGREG_PAUSE, _agreg_offre, _Garde, _quota_atteint
from jobhunter.sources.common import INCIDENTS

_log = _journal.journal(__name__)

API = "https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v6/jobs"
FICHE = "https://www.arbeitsagentur.de/jobsuche/jobdetail/"
EN_TETES = {
    "User-Agent": "Grisbix/JobHunter (+https://github.com/Grisbix/JobHunter)",
    "X-API-Key": "jobboerse-jobsuche",  # the site's public client key, not a secret
    "Accept": "application/json",
}
PAR_PAGE = 100  # the API's maximum
JOURS = 30
# Used when the profile has no keyword (sources.keywords). German and English, the telling word first; the API matches titles and occupations.
MOTS = (
    "ESG",
    "Nachhaltigkeit",
    "Nachhaltigkeitsmanager",
    "Sustainability",
    "CSRD",
    "Sustainable Finance",
    "Klimarisiko",
    "Impact Investing",
    "Kreditanalyst",
    "Finanzanalyst",
    "Portfoliomanager",
    "Investment Analyst",
)
_PAYS = {"DEUTSCHLAND": "Deutschland", "OESTERREICH": "Österreich", "SCHWEIZ": "Schweiz"}


def lieu(offre: dict[str, Any]) -> str:
    """« Frankfurt am Main, Deutschland »: the first location of the posting."""
    for loc in offre.get("stellenlokationen") or []:
        a = (loc or {}).get("adresse") or {}
        land = str(a.get("land") or "")
        morceaux = [str(a.get("ort") or ""), _PAYS.get(land, land.title())]
        return ", ".join(m for m in morceaux if m)
    return ""


def scan_arbeitsagentur() -> list[dict[str, Any]]:
    """The keywords above, job offers (not training), posted in the last 30 days.

    Returns:
        The offers, each linked to its page on arbeitsagentur.de.
    """
    import httpx

    _EX = _commun.contrats_exclus()
    garde, out, vus = _Garde("arbeitsagentur"), [], set()
    for i, mot in enumerate(_mots.mots("arbeitsagentur", MOTS, len(MOTS))):
        if garde.fini or _quota_atteint("arbeitsagentur"):
            break
        if i:
            time.sleep(AGREG_PAUSE)
        try:
            r = _commun._get_borne(
                httpx,
                API,
                timeout=25,
                headers=EN_TETES,
                params={
                    "was": mot,
                    "angebotsart": 1,
                    "veroeffentlichtseit": JOURS,
                    "size": PAR_PAGE,
                    "page": 1,
                },
            )
        except Exception as e:
            INCIDENTS["arbeitsagentur"][type(e).__name__] += 1
            continue
        if not garde.reponse(r):
            continue
        try:
            res = r.json().get("ergebnisliste") or []
        except (ValueError, AttributeError):
            continue
        for j in res:
            ref = str(j.get("referenznummer") or "")
            if not ref or ref in vus:
                continue
            vus.add(ref)
            o = _agreg_offre(
                j.get("stellenangebotsTitel"),
                FICHE + quote(ref, safe=""),
                j.get("firma"),
                lieu(j),
                j.get("datumErsteVeroeffentlichung") or j.get("aenderungsdatum"),
                "arbeitsagentur",
                j.get("hauptberuf"),
                None,
                _EX,
            )
            if o:
                out.append(o)
    _log.info(f"  ✓ Arbeitsagentur → {len(out)} offres")
    return out
