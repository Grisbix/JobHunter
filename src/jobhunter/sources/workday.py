"""Workday: the public API of large groups.

Part of jobhunter.sources (formerly Scripts/job_sources.py, phase 3.4).
"""

import time
from typing import Any

from jobhunter import log as _journal
from jobhunter.sources import common as _commun
from jobhunter.sources.common import INCIDENTS, UA, _mk, _strip_html, title_ok

_log = _journal.journal(__name__)


# Short on purpose. The 55 keywords of KEYWORDS would target LinkedIn, not a company
# feed where we look for a PROFESSION in an already narrow catalogue.
WORKDAY_MOTS = [
    "ESG",
    "durable",
    "sustainability",
    "finance",
    "analyste",
    "analyst",
    "climat",
    "risque",
]

WORKDAY_PAGES = 2  # pages of 20 per keyword

WORKDAY_PAUSE = 0.6

WORKDAY_DETAILS = 25  # detailed postings per feed, at most

WORKDAY_PARALLELE = (
    6  # feeds read at the same time (one tenant = one site); 42 feeds as of 2026-10-08
)


def _workday_detail(httpx: Any, base: str, tenant: str, site: str, chemin: str) -> dict[str, Any]:
    """An offer's posting: description, real date, country, working time."""
    try:
        r = _commun._post_borne(
            httpx,
            f"{base}/wday/cxs/{tenant}/{site}{chemin}",
            timeout=15,
            headers={**UA, "Accept": "application/json"},
        )
        if r.status_code != 200:
            r = _commun._get_borne(
                httpx,
                f"{base}/wday/cxs/{tenant}/{site}{chemin}",
                timeout=15,
                headers={**UA, "Accept": "application/json"},
            )
        if r.status_code != 200:
            return {}
        ji = (r.json() or {}).get("jobPostingInfo") or {}
    except Exception:
        return {}
    pays = (ji.get("country") or {}).get("descriptor") or ""
    return {
        "description": _strip_html(ji.get("jobDescription") or "")[:30000],
        "date": str(ji.get("startDate") or "")[:10],
        "location": ji.get("location") or "",
        "pays": pays,
        # "Full time" / "Part time" is a working time, not a contract:
        # we do not let it fill the `contrat` column, which is used for filtering.
        "temps": ji.get("timeType") or "",
    }


def fetch_workday(tenant: str, host: str, site: str, nom: str) -> list[dict[str, Any]]:
    """The offers of a Workday feed that pass title_ok, descriptions included."""
    import httpx

    base = f"https://{tenant}.{host}.myworkdayjobs.com"
    vus, retenues = set(), []
    try:
        for mot in WORKDAY_MOTS:
            for page in range(WORKDAY_PAGES):
                r = _commun._post_borne(
                    httpx,
                    f"{base}/wday/cxs/{tenant}/{site}/jobs",
                    json={"appliedFacets": {}, "limit": 20, "offset": page * 20, "searchText": mot},
                    timeout=20,
                    headers={
                        **UA,
                        "Accept": "application/json",
                        "Content-Type": "application/json",
                    },
                )
                if r.status_code != 200:
                    INCIDENTS[f"workday:{tenant}"][f"HTTP {r.status_code}"] += 1
                    break
                postes = (r.json() or {}).get("jobPostings") or []
                if not postes:
                    break
                for j in postes:
                    chemin = j.get("externalPath") or ""
                    if not chemin or chemin in vus:
                        continue
                    vus.add(chemin)
                    titre = (j.get("title") or "").strip()
                    if titre and title_ok(titre):
                        retenues.append((titre, chemin, j.get("locationsText") or ""))
                time.sleep(WORKDAY_PAUSE)
    except Exception as e:
        INCIDENTS[f"workday:{tenant}"][type(e).__name__] += 1

    out = []
    for titre, chemin, lieu in retenues[:WORKDAY_DETAILS]:
        d = _workday_detail(httpx, base, tenant, site, chemin)
        # The COUNTRY is served in clear by the API. It is safer than guessing
        # from a city name, and en_france() can read "France".
        lieu_final = ", ".join(x for x in (d.get("location") or lieu, d.get("pays")) if x)
        o = _mk(
            titre,
            f"{base}/{site}{chemin}",
            nom,
            lieu_final,
            d.get("date", ""),
            f"workday:{tenant}",
            d.get("description", ""),
        )
        out.append(o)
        time.sleep(WORKDAY_PAUSE)
    # Offers without a detailed posting get in anyway: the title and the link
    # are enough to make them exist, auto-enrichment will do the rest.
    for titre, chemin, lieu in retenues[WORKDAY_DETAILS:]:
        out.append(_mk(titre, f"{base}/{site}{chemin}", nom, lieu, "", f"workday:{tenant}"))
    return [o for o in out if o["titre"] and o["url"]]


def scan_workday() -> list[dict[str, Any]]:
    """The feeds in parallel, WORKDAY_PARALLELE at a time.

    Each tenant is a distinct site: the per-feed pause still holds, none is
    hit faster than before. In series, 27 feeds at ~70 s exceeded the 30
    min cap of pass 1a (2026-10-08).
    """
    import concurrent.futures as cf

    offres = []
    with cf.ThreadPoolExecutor(max_workers=WORKDAY_PARALLELE) as ex:
        futs = [(f[0], ex.submit(fetch_workday, *f)) for f in _commun.WORKDAY_FLUX]
        for tenant, fut in futs:
            got = fut.result()
            _log.info(f"  ✓ workday:{tenant} → {len(got)} offres retenues")
            offres.extend(got)
    return offres
