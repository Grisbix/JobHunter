"""Finding companies to follow: Workday career sites, and checking a feed before following it.

The user, 2026-10-27, after reading freehire (github.com/strelov1/freehire): its
470,000 companies come from code, not from hand. Two of its ideas fit JobHunter:

- **Workday career sites from Common Crawl.** Workday publishes no directory of its
  tenants, and a site's address (`totalenergies.wd3.myworkdayjobs.com/TotalEnergies`)
  does not follow from the company's name; but Common Crawl, the public monthly crawl
  of the web, has seen them. Its index answers `*.myworkdayjobs.com`; each address
  gives (tenant, data centre, site). The result is the user's own directory,
  `workday_directory.json` next to the queue, searched by name like the bundled
  Lever / Ashby / Greenhouse ones. It is never shipped in the package: Common Crawl's
  licence is not transferable, so every installation builds its own.
- **A feed is followed only if it answers.** Before a company seen in a collection is
  followed, one request to its tool's public API counts its open offers; none → not
  followed (freehire's harvest keeps a board only if its API returns jobs).

Polite by design: the project names itself in the User-Agent, one request at a time
with a pause, and the Common Crawl index — often overloaded, `503`/`504` — is waited
for a few times, then left for the next run, which resumes where this one stopped
(the pages already read are kept in the directory file).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from jobhunter import log as _journal
from jobhunter.sources import common as _commun
from jobhunter.storage.atomic import ecrire_json

_log = _journal.journal(__name__)

UA = {"User-Agent": "Grisbix/JobHunter (+https://github.com/Grisbix/JobHunter)"}
COLLINFO = "https://index.commoncrawl.org/collinfo.json"
MOTIF = "*.myworkdayjobs.com"
NOM_ANNUAIRE = "workday_directory.json"
INSTANTANES = 2  # snapshots a few months apart overlap heavily (freehire measured it)
PAUSE = 2.0
ATTENTES = (30, 60, 120)  # an overloaded index: wait, then leave it for the next run

_RX_SITE = re.compile(
    r"//([a-z0-9-]+)\.(wd\d+)\.myworkdayjobs\.com/(?:[a-z]{2}-[A-Z]{2}/)?([A-Za-z0-9_-]+)", re.I
)
# Path segments that are Workday's own pages, not a career site.
_PAS_UN_SITE = {"wday", "login", "assets", "robots", "favicon", "static", "sitemap", "api"}


def chemin_annuaire() -> Path:
    """The user's Workday directory, next to the queue."""
    return Path(_commun.QUEUE).parent / NOM_ANNUAIRE


def sites_workday(lignes: Iterable[str]) -> set[tuple[str, str, str]]:
    """(tenant, data centre, site) of every Workday career site in Common Crawl's lines.

    Args:
        lignes: the index's answer, one JSON object per line (`{"url": ...}`); a line
            that is not one is skipped.
    """
    sortie = set()
    for ligne in lignes:
        try:
            url = str(json.loads(ligne).get("url") or "")
        except (ValueError, AttributeError):
            continue
        m = _RX_SITE.search(url)
        if m and m.group(3).lower() not in _PAS_UN_SITE:
            sortie.add((m.group(1).lower(), m.group(2).lower(), m.group(3)))
    return sortie


def charger_annuaire() -> dict[str, Any]:
    """{"sites": [[tenant, wd, site], ...], "pages_lues": {snapshot: [pages]}}; empty if absent."""
    try:
        d = json.loads(chemin_annuaire().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        d = {}
    if not isinstance(d, dict):
        d = {}
    d.setdefault("sites", [])
    d.setdefault("pages_lues", {})
    return d


def _get(httpx: Any, adresse: str, **params: Any) -> Any:
    """One request to the index; waits on an overloaded index, None if it stays so."""
    for attente in (*ATTENTES, None):
        try:
            r = _commun._get_borne(httpx, adresse, timeout=60, headers=UA, params=params)
        except Exception as e:
            _log.info(f"  ⚠ Common Crawl : {type(e).__name__}")
            r = None
        if r is not None and r.status_code == 200:
            return r
        if r is not None and r.status_code not in (429, 500, 502, 503, 504):
            return None  # not an overload: nothing to wait for
        if attente is None:
            return None
        _log.info(f"  … index surchargé, nouvel essai dans {attente} s")
        time.sleep(attente)
    return None


def construire_annuaire(instantanes: int = INSTANTANES) -> dict[str, int]:
    """Reads Workday's career sites from the last Common Crawl snapshots into the directory.

    Resumes: a page already read is not asked again. Each page read is saved at once.

    Returns:
        {"sites": total in the directory, "nouveaux": added by this run,
         "pages": pages read by this run, "restantes": pages left for the next run}.
    """
    import httpx

    d = charger_annuaire()
    connus = {tuple(s) for s in d["sites"]}
    avant = len(connus)
    lues = restantes = 0
    r = _get(httpx, COLLINFO)
    if r is None:
        _log.info("  ✗ Common Crawl ne répond pas : rien de changé, à relancer plus tard")
        return {"sites": avant, "nouveaux": 0, "pages": 0, "restantes": -1}
    for inst in (r.json() or [])[:instantanes]:
        nom, api = str(inst.get("id") or ""), str(inst.get("cdx-api") or "")
        if not nom or not api.startswith("https://index.commoncrawl.org/"):
            continue
        faites = set(d["pages_lues"].get(nom, []))
        time.sleep(PAUSE)
        n = _get(httpx, api, url=MOTIF, showNumPages="true")
        try:
            pages = int(n.json().get("pages") or 0) if n is not None else 0
        except (ValueError, AttributeError):
            pages = 0
        for page in range(pages):
            if page in faites:
                continue
            time.sleep(PAUSE)
            p = _get(httpx, api, url=MOTIF, output="json", fl="url", page=page)
            if p is None:
                restantes += pages - len(faites)
                break
            connus |= sites_workday(p.text.splitlines())
            faites.add(page)
            d["pages_lues"][nom] = sorted(faites)
            d["sites"] = sorted([list(s) for s in connus])
            ecrire_json(chemin_annuaire(), d)
            lues += 1
            _log.info(f"  {nom} page {page + 1}/{pages} : {len(connus)} sites")
    return {
        "sites": len(connus),
        "nouveaux": len(connus) - avant,
        "pages": lues,
        "restantes": restantes,
    }


# ── Checking a feed before following it ──────────────────────────────────────

_API_COMPTE = {
    "greenhouse": "https://boards-api.greenhouse.io/v1/boards/{}/jobs",
    "lever": "https://api.lever.co/v0/postings/{}?mode=json",
    "ashby": "https://api.ashbyhq.com/posting-api/job-board/{}",
    "recruitee": "https://{}.recruitee.com/api/offers/",
    "smartrecruiters": "https://api.smartrecruiters.com/v1/companies/{}/postings?limit=1",
}


def _compte(outil: str, data: Any) -> int:
    if outil == "lever":
        return len(data) if isinstance(data, list) else 0
    if outil == "smartrecruiters":
        return int(data.get("totalFound") or 0)
    if outil == "recruitee":
        return len(data.get("offers") or [])
    return len(data.get("jobs") or [])


def offres_ouvertes(trouve: tuple[str, Any]) -> int | None:
    """Open offers of a feed, by one request to its tool's public API.

    Args:
        trouve: what `inventory.flux_depuis_url` returns.

    Returns:
        The count (0: the feed answers but is empty, or is not this company's), or
        None when this tool cannot be checked this way (the feed is then followed as
        before, unchecked).
    """
    import httpx

    outil, cle = trouve
    try:
        if outil == "workday":
            tenant, wd, site = cle
            r = _commun._post_borne(
                httpx,
                f"https://{tenant}.{wd}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs",
                json={"appliedFacets": {}, "limit": 1, "offset": 0, "searchText": ""},
                timeout=20,
                headers={**UA, "Accept": "application/json", "Content-Type": "application/json"},
            )
            return int((r.json() or {}).get("total") or 0) if r.status_code == 200 else 0
        if outil not in _API_COMPTE:
            return None
        r = _commun._get_borne(httpx, _API_COMPTE[outil].format(cle), timeout=15, headers=UA)
        return _compte(outil, r.json()) if r.status_code == 200 else 0
    except Exception:
        return 0


def main(argv: list[str] | None = None) -> int:
    """`python -m jobhunter.sources.discovery --workday`: builds or completes the directory."""
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    ap.add_argument("--workday", action="store_true", help="annuaire Workday depuis Common Crawl")
    ap.add_argument("--instantanes", type=int, default=INSTANTANES)
    a = ap.parse_args(argv)
    if not a.workday:
        ap.print_help()
        return 0
    bilan = construire_annuaire(a.instantanes)
    print(
        f"Annuaire Workday : {bilan['sites']} sites ({bilan['nouveaux']} nouveaux, "
        f"{bilan['pages']} pages lues)"
        + (
            f" — {bilan['restantes']} pages à finir au prochain lancement"
            if bilan["restantes"] > 0
            else ""
        )
    )
    return 0 if bilan["restantes"] >= 0 else 4


if __name__ == "__main__":
    raise SystemExit(main())
