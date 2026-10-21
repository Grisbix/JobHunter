"""Is an offer still open? Asked of its ATS's public API, before reading its page.

WHY. Workday and Ashby pages are drawn by JavaScript: the HTML a program receives is
the same empty shell, HTTP 200, whether the offer is open or withdrawn. The
availability check therefore found every one of them open — on 21/10/2026, 304
Workday offers checked "OK 200" and not a single one closed, while their API said
half were withdrawn (10 of a sample of 20, each confirmed absent from its employer's
own job list). The ATS's public JSON answers for real:

  - Workday, per offer: `/wday/cxs/{tenant}/{site}/job/{path}`. 200 = open,
    404/410 = gone, and a 403 whose JSON says `errorCode: "S22"` = withdrawn. Any
    other 403 (a firewall page, another code) proves nothing.
  - Greenhouse, per offer: `boards-api.greenhouse.io/v1/boards/{slug}/jobs/{id}`.
    200 = open, 404 = gone.
  - Ashby, per BOARD: `api.ashbyhq.com/posting-api/job-board/{org}` lists every open
    offer of the company. Listed = open, absent from a board that answered = closed.
    A 404 of the board says nothing about the offer (embed-only boards), and the
    board is read once per company and per run.

Anything else — unknown host, timeout, 429, 5xx, unreadable body — returns None, and
the caller reads the page as before. A false "closed" removes a live offer, which is
worse than checking a dead one again.

The API addresses are built from FIXED hosts and from path pieces taken out of the
offer's URL with a strict alphabet (no "..", no other host), so an offer URL cannot
steer a request elsewhere. Technique and the S22 reading: career-ops, liveness-api.mjs.
"""

import re
import threading
from collections.abc import Callable
from typing import Any

# One piece of an API path. "%" stays: Workday paths carry encoded brackets.
_PIECE = re.compile(r"^[A-Za-z0-9._%-]+$")

_WORKDAY = re.compile(
    r"^https://([A-Za-z0-9-]+)\.(wd\d+)\.myworkdayjobs\.com"
    r"(?:/[a-z]{2}-[A-Z]{2})?/([^/?#]+)/job/([^?#]+?)/?(?:[?#].*)?$"
)
_GREENHOUSE = re.compile(
    r"^https://(?:boards|job-boards)(?:\.eu)?\.greenhouse\.io/([^/?#]+)/jobs/(\d+)/?(?:[?#].*)?$"
)
_ASHBY = re.compile(
    r"^https://jobs\.ashbyhq\.com/([^/?#]+)/([0-9a-fA-F-]{36})(?:/application)?/?(?:[?#].*)?$"
)

OUVERTE, FERMEE = "OK", "FERMEE"
Verdict = tuple[str, str]  # (OUVERTE or FERMEE, reason)

_tableaux: dict[str, set[str] | None] = {}
_verrou = threading.Lock()


def _surs(*pieces: str) -> bool:
    return all(p and _PIECE.match(p) and ".." not in p for p in pieces)


def verdict_workday(statut: int, corps: Any) -> Verdict | None:
    """The Workday per-offer answer, read; None when it proves nothing."""
    if statut == 200:
        return OUVERTE, "ouverte (API Workday)"
    if statut in (404, 410):
        return FERMEE, f"API Workday {statut}"
    if (
        statut == 403
        and isinstance(corps, dict)
        and corps.get("httpStatus") == 403
        and corps.get("errorCode") == "S22"
    ):
        return FERMEE, "retiree (Workday S22)"
    return None


def _ids_ashby(corps: Any) -> set[str] | None:
    if not isinstance(corps, dict) or not isinstance(corps.get("jobs"), list):
        return None
    return {str(j.get("id", "")).lower() for j in corps["jobs"] if isinstance(j, dict)}


def _json(r: Any) -> Any:
    try:
        return r.json()
    except Exception:
        return None


def controle(url: str, get: Callable[..., Any]) -> Verdict | None:
    """Ask the offer's ATS. `get(url, **kw)` returns an httpx-like response.

    None: not an ATS we know, or no conclusive answer — read the page instead.
    """
    url = url.strip()
    entete = {"Accept": "application/json", "User-Agent": "Mozilla/5.0"}
    try:
        if m := _WORKDAY.match(url):
            tenant, shard, site, chemin = m.groups()
            if not _surs(tenant, site, *chemin.split("/")):
                return None
            r = get(
                f"https://{tenant}.{shard}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/job/{chemin}",
                headers=entete,
            )
            return verdict_workday(r.status_code, _json(r) if r.status_code == 403 else None)
        if m := _GREENHOUSE.match(url):
            slug, ident = m.groups()
            if not _surs(slug):
                return None
            r = get(
                f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs/{ident}", headers=entete
            )
            if r.status_code == 200:
                return OUVERTE, "ouverte (API Greenhouse)"
            if r.status_code in (404, 410):
                return FERMEE, f"API Greenhouse {r.status_code}"
            return None
        if m := _ASHBY.match(url):
            org, ident = m.groups()
            if not _surs(org):
                return None
            with _verrou:
                connu = org in _tableaux
                ids = _tableaux.get(org)
            if not connu:
                r = get(f"https://api.ashbyhq.com/posting-api/job-board/{org}", headers=entete)
                ids = _ids_ashby(_json(r)) if r.status_code == 200 else None
                with _verrou:
                    _tableaux[org] = ids
            if ids is None:
                return None
            if ident.lower() in ids:
                return OUVERTE, "ouverte (tableau Ashby)"
            return FERMEE, "absente du tableau Ashby"
    except Exception:
        return None
    return None


def oublier_tableaux() -> None:
    """Forget the Ashby boards read (one run = one reading per company)."""
    with _verrou:
        _tableaux.clear()
