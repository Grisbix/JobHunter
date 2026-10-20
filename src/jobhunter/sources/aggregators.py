"""Adzuna and Jooble: official APIs (key required).

Part of jobhunter.sources (formerly Scripts/job_sources.py, phase 3.4).
"""

import time
from pathlib import Path
from typing import Any

from jobhunter import log as _journal
from jobhunter import root as _racine
from jobhunter.sources import common as _commun
from jobhunter.sources.common import (
    INCIDENTS,
    UA,
    _mk,
    _strip_html,
    contrat_du_titre,
    title_ok,
)

_log = _journal.journal(__name__)


# ═══════════════ 8. Adzuna and Jooble — aggregators, official APIs (key required) ═══
# WHY. Indeed refuses everything since 24/09 (403 at the first request) and
# APEC has been behind DataDome since 02/10. Adzuna and Jooble aggregate the
# same pools — and many small sites — through an official API, with
# a free key. They are not new sources: they are LEGITIMATE ways of
# access to what Indeed no longer lets us see.
#
# ⚠ KEYS TO BE CREATED BY THE USER (I do not create accounts):
#   Adzuna : https://developer.adzuna.com -> Scripts/adzuna.json
#            {"app_id": "...", "app_key": "..."}
#   Jooble : https://jooble.org/api/about -> Scripts/jooble.json
#            {"key": "..."}
# Files ignored by git. Without them, the source deactivates itself and says so.
#
# THE KEY IS NEVER DISPLAYED. Adzuna carries it in the URL, Jooble in the
# path: an httpx exception message contains the URL. So we only print
# the TYPE of the exception, never its text.
#
# LIMITS. Descriptions = excerpts (desc_partielle: a better source replaces
# them at merge). Links = the aggregator's redirect pages, which the
# URL promotion replaces when the real site arrives through another source.
ADZUNA_CFG = _racine.dossier_cles() / "adzuna.json"

JOOBLE_CFG = _racine.dossier_cles() / "jooble.json"

ADZUNA_API = "https://api.adzuna.com/v1/api/jobs/{pays}/search/1"

JOOBLE_API = "https://jooble.org/api/{cle}"

# Few words, chosen: Adzuna's free quota is counted in calls per day,
# and one keyword x one country = one call. 12 + 6 x 7 = 54 calls per pass.
AGREG_MOTS_FR = [
    "analyste ESG",
    "finance durable",
    "investissement responsable",
    "ISR",
    "analyste financier junior",
    "analyste crédit",
    "risque climatique",
    "reporting extra-financier",
    "CSRD",
    "SFDR",
    "analyste private equity",
    "transition énergétique analyste",
]

AGREG_MOTS_EN = [
    "ESG analyst",
    "sustainable finance",
    "sustainability analyst",
    "responsible investment",
    "climate risk analyst",
    "graduate finance",
]

ADZUNA_PAYS = ("gb", "es", "de", "nl", "be", "ch", "it")

AGREG_PAUSE = 1.0

AGREG_ABANDON = 3  # refus d'entree d'affilee (cle refusee, blocage)

AGREG_REPOS_429 = 60  # a rate limit is waited out; twice at most


def _cle(chemin: Path, *champs: str) -> tuple[str, ...] | None:
    """The fields of the key file, or None. Never raises, displays nothing of the key."""
    import json as _json

    if not chemin.exists():
        return None
    try:
        c = _json.loads(chemin.read_text(encoding="utf-8"))
        return tuple(str(c[k]) for k in champs)
    except Exception as e:
        _log.info(
            f"  ✗ {chemin.name} illisible ({type(e).__name__}) — attendu : {', '.join(champs)}"
        )
        return None


class _Garde:
    """Counts a source's refusals: 429 -> pause then resume, refused entry -> stop."""

    def __init__(self, nom: str) -> None:
        self.nom, self.refus, self.repos, self.fini = nom, 0, 0, False

    def reponse(self, r: Any) -> bool:
        """True if the response is usable. Handles pauses and giving up."""
        if r.status_code == 429:
            INCIDENTS[self.nom]["HTTP 429"] += 1
            if self.repos >= 2:
                _log.info(f"  ⏸ {self.nom} : limite de debit persistante — arret de la source")
                self.fini = True
                return False
            self.repos += 1
            _log.warning(f"  ⏸ {self.nom} : limite de debit (429) — pause {AGREG_REPOS_429} s")
            time.sleep(AGREG_REPOS_429)
            return False
        if r.status_code in (401, 403):
            INCIDENTS[self.nom][f"HTTP {r.status_code}"] += 1
            self.refus += 1
            if self.refus >= AGREG_ABANDON:
                _log.warning(
                    f"  ⏸ {self.nom} : {self.refus} refus d'affilee (HTTP {r.status_code}) — "
                    f"cle refusee ou acces bloque, arret de la source"
                )
                self.fini = True
            return False
        if r.status_code != 200:
            INCIDENTS[self.nom][f"HTTP {r.status_code}"] += 1
            return False
        self.refus = 0
        return True


_ADZUNA_CONTRAT = {"permanent": "CDI", "contract": "CDD"}


def _agreg_offre(
    titre: str,
    url: str,
    entreprise: str | None,
    lieu: str | None,
    date: str,
    source: str,
    extrait: str | None,
    contrat: str | None,
    _EX: Any,
) -> dict[str, Any] | None:
    titre = (titre or "").strip()
    if not titre or not url or not title_ok(titre):
        return None
    ctr = contrat_du_titre(titre) or contrat or ""
    if ctr and ctr in _EX:
        return None
    o = _mk(
        titre,
        url,
        entreprise or source.split(":")[0].title(),
        lieu or "",
        str(date or "")[:10],
        source,
        _strip_html(extrait or ""),
    )
    o["desc_partielle"] = True
    if ctr:
        o["contrat"] = ctr
    return o


def scan_adzuna() -> list[dict[str, Any]]:
    """Adzuna collection (official API, France and seven countries).

    Returns:
        The offers; [] if the key (Scripts/adzuna.json) is missing.
    """
    import httpx

    cle = _cle(ADZUNA_CFG, "app_id", "app_key")
    if not cle:
        _log.info("  · Adzuna ignore (Scripts/adzuna.json absent — voir le commentaire)")
        return []
    app_id, app_key = cle
    _EX = _commun.contrats_exclus()
    garde, out, vus = _Garde("adzuna"), [], set()
    requetes = [("fr", m) for m in AGREG_MOTS_FR] + [
        (p, m) for p in ADZUNA_PAYS for m in AGREG_MOTS_EN
    ]
    faites = 0
    for pays, mot in requetes:
        if garde.fini:
            break
        if faites:
            time.sleep(AGREG_PAUSE)
        faites += 1
        try:
            r = _commun._get_borne(
                httpx,
                ADZUNA_API.format(pays=pays),
                timeout=25,
                headers=UA,
                params={
                    "app_id": app_id,
                    "app_key": app_key,
                    "what": mot,
                    "results_per_page": 50,
                    "max_days_old": 30,
                    "content-type": "application/json",
                },
            )
        except Exception as e:
            INCIDENTS["adzuna"][type(e).__name__] += 1
            continue
        if not garde.reponse(r):
            continue
        try:
            res = r.json().get("results") or []
        except ValueError:
            continue
        for j in res:
            u = j.get("redirect_url") or ""
            if not u or u in vus:
                continue
            vus.add(u)
            o = _agreg_offre(
                j.get("title"),
                u,
                (j.get("company") or {}).get("display_name"),
                (j.get("location") or {}).get("display_name"),
                j.get("created"),
                f"adzuna:{pays}",
                j.get("description"),
                _ADZUNA_CONTRAT.get(j.get("contract_type") or ""),
                _EX,
            )
            if o:
                out.append(o)
    _log.info(f"  ✓ Adzuna → {len(out)} offres sur {faites} requetes (extraits, liens Adzuna)")
    return out


def scan_jooble() -> list[dict[str, Any]]:
    """Jooble collection (official API).

    Returns:
        The offers; [] if the key (Scripts/jooble.json) is missing.
    """
    import httpx

    cle = _cle(JOOBLE_CFG, "key")
    if not cle:
        _log.info("  · Jooble ignore (Scripts/jooble.json absent — voir le commentaire)")
        return []
    _EX = _commun.contrats_exclus()
    garde, out, vus = _Garde("jooble"), [], set()
    faites = 0
    for mot in AGREG_MOTS_FR:
        if garde.fini:
            break
        if faites:
            time.sleep(AGREG_PAUSE)
        faites += 1
        try:
            r = _commun._post_borne(
                httpx,
                JOOBLE_API.format(cle=cle[0]),
                timeout=25,
                headers={**UA, "Content-Type": "application/json"},
                json={"keywords": mot, "location": "France", "page": "1"},
            )
        except Exception as e:
            INCIDENTS["jooble"][type(e).__name__] += 1
            continue
        if not garde.reponse(r):
            continue
        try:
            res = r.json().get("jobs") or []
        except ValueError:
            continue
        for j in res:
            u = j.get("link") or ""
            if not u or u in vus:
                continue
            vus.add(u)
            typ = str(j.get("type") or "")
            ctr = "CDI" if "CDI" in typ else "CDD" if "CDD" in typ else ""
            o = _agreg_offre(
                j.get("title"),
                u,
                j.get("company"),
                j.get("location"),
                j.get("updated"),
                "jooble",
                j.get("snippet"),
                ctr,
                _EX,
            )
            if o:
                out.append(o)
    _log.info(f"  ✓ Jooble → {len(out)} offres sur {faites} requetes (extraits, liens Jooble)")
    return out
