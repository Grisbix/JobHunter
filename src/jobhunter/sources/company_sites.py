"""The offers of the companies already seen, read on their own career sites.

The user, 2026-10-27: « un outil qui cherche les offres des sites carrière des
entreprises stockées ». The register of companies seen (storage.companies, some 5,000
names) keeps every company a collection met; this source asks each of them, a slice
per run, what it has open now:

- a company whose offer link gave its recruiting tool (Greenhouse, Workday…) is read
  by that tool's public API, as a followed feed would be — without following it;
- the others are looked up in freehire (sources.freehire), which reads 470,000
  companies' career sites: its company search, then the company's open jobs. Its
  search is fuzzy (« Mirova » answers « Mirvac »), so only a company whose name is
  the same, or the same followed by more words (« Amundi Ireland Limited »), is kept.

Followed companies are skipped (their feed is collected anyway). A company is asked
again after `DELAI` days; each run takes the `PAR_PASSE` least recently asked,
the most recently seen first. What was asked when is kept in `_company_sites.json`,
next to the queue. The freehire requests count against its daily quota.
"""

from __future__ import annotations

import json
import re
import time
import unicodedata
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from jobhunter import log as _journal
from jobhunter.sources import common as _commun
from jobhunter.sources.aggregators import AGREG_PAUSE, _agreg_offre, _Garde, _quota_atteint
from jobhunter.sources.common import INCIDENTS
from jobhunter.storage.atomic import ecrire_json

_log = _journal.journal(__name__)

NOM_ETAT = "_company_sites.json"
PAR_PASSE = 150
DELAI = 7  # days before a company is asked again
PAR_ENTREPRISE = 50  # open jobs read per company (freehire's maximum page)
ENTITES = 3  # freehire companies kept per name (« Amundi », « Amundi Ireland »…)


def chemin_etat() -> Path:
    """When each company was last asked, next to the queue."""
    return Path(_commun.QUEUE).parent / NOM_ETAT


def _plat(texte: object) -> str:
    t = unicodedata.normalize("NFKD", str(texte or "").casefold())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^\w]+", " ", t).split())


def meme_entreprise(cible: str, nom: str) -> bool:
    """« Amundi » is « AMUNDI », « Amundi Ireland Limited »; not « Mirvac » for « Mirova »."""
    a, b = _plat(cible), _plat(nom)
    return bool(a) and (b == a or b.startswith(a + " "))


def _suivis() -> tuple[set[tuple[str, str]], set[str]]:
    """The feeds followed, as (tool, key) — Workday by its tenant."""
    _commun._load_cfg()
    flux = {(o, str(s).lower()) for o, slugs in _commun.ATS_SLUGS.items() for s in slugs}
    flux |= {("workday", str(x[0]).lower()) for x in _commun.WORKDAY_FLUX}
    flux |= {(str(x[0]), str(x[1]).lower()) for x in _commun.AUTRES_FLUX}
    noms = {_plat(x[3]) for x in _commun.WORKDAY_FLUX if len(x) > 3}
    noms |= {_plat(x[2]) for x in _commun.AUTRES_FLUX if len(x) > 2}
    return flux, noms


def a_demander(
    reg: dict[str, dict[str, Any]], etat: dict[str, str], jour: str, n: int = PAR_PASSE
) -> list[dict[str, Any]]:
    """The register's companies to ask this run: not followed, not asked for `DELAI` days.

    Never asked first, then the least recently asked; on a tie, the most recently seen.
    """
    flux_suivis, noms_suivis = _suivis()
    limite = (date.fromisoformat(jour) - timedelta(days=DELAI)).isoformat()
    candidates = []
    for k, e in reg.items():
        fl = e.get("flux") or {}
        if fl:
            c = fl.get("cle")
            ident = (fl.get("outil"), str(c[0] if isinstance(c, list) else c).lower())
            if ident in flux_suivis:
                continue
        if _plat(e.get("nom") or k) in noms_suivis:
            continue
        vu = etat.get(k, "")
        if vu and vu > limite:
            continue
        candidates.append((vu, "" if not e.get("derniere_vue") else e["derniere_vue"], k, e))
    candidates.sort(key=lambda x: (x[0], _inverse(x[1])))
    return [{**e, "_cle": k} for _, _, k, e in candidates[:n]]


def _inverse(jour: str) -> str:
    """Sorts dates newest first inside an ascending sort."""
    return "".join(chr(0x10FFFF - ord(c)) for c in jour)


def _par_flux(e: dict[str, Any]) -> list[dict[str, Any]] | None:
    """The company's offers by its tool's API; None if its tool cannot be read here."""
    from jobhunter.inventory import AUTRES_OUTILS
    from jobhunter.sources import ats as _ats
    from jobhunter.sources import workday as _workday

    fl = e.get("flux") or {}
    outil, cle = fl.get("outil"), fl.get("cle")
    nom = str(e.get("nom") or "")
    if outil == "workday" and isinstance(cle, list) and len(cle) == 3:
        return _workday.fetch_workday(cle[0], cle[1], cle[2], nom)
    if outil in AUTRES_OUTILS and isinstance(cle, str):
        return _ats.fetch_autre(outil, cle, nom)
    if outil and isinstance(cle, str):
        return _ats.fetch_ats(outil, cle)
    return None


def _par_freehire(
    httpx: Any, e: dict[str, Any], garde: Any, ex: Any
) -> list[dict[str, Any]] | None:
    """The company's open jobs in freehire, under its exact name; None if not asked."""
    from jobhunter.sources import freehire as _fh

    nom = str(e.get("nom") or "")
    if garde.fini or _quota_atteint("freehire"):
        return None
    r = _commun._get_borne(
        httpx,
        _fh.API.replace("/jobs/search", "/companies"),
        timeout=25,
        headers=_fh.UA,
        params={"q": nom, "limit": 10},
    )
    if not garde.reponse(r):
        return None
    slugs = [
        str(c.get("slug"))
        for c in (r.json() or {}).get("data") or []
        if c.get("slug") and c.get("job_count") and meme_entreprise(nom, str(c.get("name") or ""))
    ][:ENTITES]
    out = []
    for slug in slugs:
        if garde.fini or _quota_atteint("freehire"):
            break
        time.sleep(AGREG_PAUSE)
        r = _commun._get_borne(
            httpx,
            _fh.API.replace("/jobs/search", f"/companies/{slug}"),
            timeout=25,
            headers=_fh.UA,
            params={"limit": PAR_ENTREPRISE},
        )
        if not garde.reponse(r):
            continue
        for j in ((r.json() or {}).get("data") or {}).get("jobs") or []:
            o = _agreg_offre(
                j.get("title"),
                _fh.lien_d_origine(str(j.get("url") or "")),
                nom,
                j.get("location"),
                j.get("posted_at") or j.get("created_at"),
                f"sites-carrieres:{j.get('source') or 'freehire'}",
                j.get("description"),
                None,
                ex,
            )
            if o:
                out.append(o)
    return out


def scan_company_sites(n: int = PAR_PASSE) -> list[dict[str, Any]]:
    """Asks `n` companies of the register what they have open now.

    Returns:
        Their offers that pass the title filter.
    """
    import httpx

    from jobhunter.storage import companies

    jour = date.today().isoformat()
    reg = companies.charger(_commun.QUEUE)
    try:
        etat = json.loads(chemin_etat().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        etat = {}
    if not isinstance(etat, dict):
        etat = {}
    lot = a_demander(reg, etat, jour, n)
    ex = _commun.contrats_exclus()
    garde = _Garde("freehire")
    out: list[dict[str, Any]] = []
    par_api = par_fh = 0
    for i, e in enumerate(lot):
        if i:
            time.sleep(AGREG_PAUSE)
        try:
            offres = _par_flux(e)
            if offres is None:
                offres = _par_freehire(httpx, e, garde, ex)
                if offres is None:
                    continue  # not asked (quota, refusal): asked again next run
                par_fh += 1
            else:
                for o in offres:
                    o["source"] = f"sites-carrieres:{(e.get('flux') or {}).get('outil', '')}"
                par_api += 1
        except Exception as x:
            INCIDENTS["sites-carrieres"][type(x).__name__] += 1
            continue
        out.extend(offres)
        etat[e["_cle"]] = jour
    ecrire_json(chemin_etat(), etat)
    _log.info(
        f"  ✓ sites carrières → {len(out)} offres ({par_api} entreprises par leur outil, "
        f"{par_fh} par freehire, {sum(k not in etat for k in reg)} jamais demandées)"
    )
    return out
