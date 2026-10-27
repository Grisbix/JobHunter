"""freehire: an open job search engine over companies' own career pages (public API).

freehire.me (github.com/strelov1/freehire, MIT) reads some 124 ATS platforms and
aggregators — Workday, Teamtailor, SmartRecruiters, Oracle… — for 470,000 companies,
and links every posting to the company's own page. Its API is public and keyless
for personal, non-commercial use (freehire.me/terms#data-licence), which is what a
job seeker running JobHunter is; its robots.txt points bots to it rather than to
the pages. The user, 2026-10-27: 864 French ESG / finance postings sampled, 847 not
in the queue.

Limits, from its OpenAPI (freehire.me/openapi.yaml): 120 requests a minute and 2,000
a day per address without a key, `429` with `Retry-After` beyond. One keyword is one
or two requests; the daily ceiling is shared by all profiles (sources.quota).
The descriptions are the index's preview: `desc_partielle`, as for Adzuna.
"""

import json
import re
import time
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from jobhunter import log as _journal
from jobhunter.sources import common as _commun
from jobhunter.sources.aggregators import (
    AGREG_PAUSE,
    _agreg_offre,
    _Garde,
    _quota_atteint,
)
from jobhunter.sources.common import INCIDENTS

_log = _journal.journal(__name__)

API = "https://freehire.me/api/v1/jobs/search"
# freehire asks callers to name their project, to warn them before a limit changes.
UA = {"User-Agent": "Grisbix/JobHunter (+https://github.com/Grisbix/JobHunter)"}
PAR_PAGE = 50  # the API's maximum
PAGES = 3
JOURS = 30
# Its own words, the telling one first. Its search requires the first words and drops
# the last ones when too few postings match: « analyste ESG » brought back every
# « analyste ». Quotes do not help (« "analyste ESG" » found 1 posting, 2026-10-27).
MOTS = (
    "ESG",
    "RSE",
    "ISR",
    "CSRD",
    "SFDR",
    "sustainability",
    "durable",
    "extra-financier",
    "climate",
    "climat",
    "carbone",
    "impact investing",
    "responsible investment",
    "crédit analyste",
    "private equity analyste",
    "financier analyste",
)


def pays() -> list[str]:
    """The countries searched: `freehire_pays` in sources_config.json, all if absent or empty.

    The user, 2026-10-27: « ne te limite pas à la France ». The countries the profile
    excludes (`pays_exclus`) are still set aside by the merge, like every source's.
    """
    try:
        cfg = json.loads(_commun.SOURCES_CFG.read_text(encoding="utf-8"))
    except (OSError, ValueError, AttributeError):
        return []
    v = cfg.get("freehire_pays") if isinstance(cfg, dict) else None
    return (
        [str(c).lower() for c in v if re.fullmatch(r"[A-Za-z]{2}", str(c))]
        if isinstance(v, list)
        else []
    )


def lien_d_origine(url: str) -> str:
    """The company's own link, without the `utm_source=freehire.me` freehire adds."""
    p = urlsplit(url)
    reste = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True) if k != "utm_source"]
    return urlunsplit(p._replace(query=urlencode(reste)))


def _entreprise(nom: str | None) -> str:
    """Some companies are only known by their careers host: « x.wd3.myworkdayjobs.com/ »."""
    return str(nom or "").strip().rstrip("/")


def scan_freehire() -> list[dict[str, Any]]:
    """The collection keywords, posted in the last 30 days, in every country by default.

    Returns:
        The offers, with the company's own links.
    """
    import httpx

    _EX = _commun.contrats_exclus()
    garde, out, vus = _Garde("freehire"), [], set()
    faites = 0
    les_pays = pays()
    for mot in MOTS:
        for page in range(PAGES):
            if garde.fini or _quota_atteint("freehire"):
                break
            if faites:
                time.sleep(AGREG_PAUSE)
            faites += 1
            try:
                r = _commun._get_borne(
                    httpx,
                    API,
                    timeout=25,
                    headers=UA,
                    params={
                        "q": mot,
                        **({"countries": les_pays} if les_pays else {}),
                        "posted_within_days": JOURS,
                        "limit": PAR_PAGE,
                        "offset": page * PAR_PAGE,
                    },
                )
            except Exception as e:
                INCIDENTS["freehire"][type(e).__name__] += 1
                break
            if not garde.reponse(r):
                break
            try:
                res = r.json().get("data") or []
            except ValueError:
                break
            for j in res:
                u = lien_d_origine(str(j.get("url") or ""))
                if not u or u in vus:
                    continue
                vus.add(u)
                o = _agreg_offre(
                    j.get("title"),
                    u,
                    _entreprise(j.get("company")),
                    j.get("location"),
                    j.get("posted_at") or j.get("created_at"),
                    f"freehire:{j.get('source') or ''}",
                    j.get("description"),
                    None,
                    _EX,
                )
                if o:
                    out.append(o)
            if len(res) < PAR_PAGE:
                break
    _log.info(f"  ✓ freehire → {len(out)} offres sur {faites} requetes (liens des entreprises)")
    return out
