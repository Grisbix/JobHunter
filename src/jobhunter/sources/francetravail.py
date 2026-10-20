"""France Travail : API officielle (identifiants requis).

Partie de jobhunter.sources (ancien Scripts/job_sources.py, phase 3.4).
"""

import time
from typing import Any

from jobhunter import log as _journal
from jobhunter.sources import common as _commun
from jobhunter.sources.common import HERE, UA, _mk, title_ok

_log = _journal.journal(__name__)


# ═══════════════ 7. France Travail — API OFFICIELLE (identifiants requis) ═══════
# Formerly Pole emploi: the biggest deposit of offers in France, public API, free,
# legal. Covers very broadly what Indeed aggregates, without any workaround.
#
# ⚠ CREDENTIALS TO BE CREATED BY THE USER (I do not create accounts):
#   1. https://francetravail.io  ->  create an account, then an application
#   2. subscribe to the "Offres d'emploi v2" API
#   3. copy client_id / client_secret into Scripts/francetravail.json:
#        {"client_id": "...", "client_secret": "..."}
#      (file ignored by git: it contains a secret)
# Without this file, the source disables itself silently.
FT_CFG = HERE / "francetravail.json"

FT_TOKEN_URL = (
    "https://entreprise.francetravail.fr/connexion/oauth2/access_token?realm=%2Fpartenaire"
)

FT_SEARCH = "https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search"


def _ft_token() -> str | None:
    import json as _json

    import httpx

    if not FT_CFG.exists():
        return None
    try:
        c = _json.loads(FT_CFG.read_text(encoding="utf-8"))
        r = _commun._post_borne(
            httpx,
            FT_TOKEN_URL,
            timeout=20,
            data={
                "grant_type": "client_credentials",
                "client_id": c["client_id"],
                "client_secret": c["client_secret"],
                "scope": "api_offresdemploiv2 o2dsoffre",
            },
        )
        if r.status_code != 200:
            _log.info(f"  ✗ France Travail token http {r.status_code} — verifie les identifiants")
            return None
        jeton: str | None = r.json().get("access_token")
        return jeton
    except Exception as e:
        _log.info(f"  ✗ France Travail token {type(e).__name__}")
        return None


def fetch_france_travail(par_mot: int = 50) -> list[dict[str, Any]]:
    """The France Travail offers (official API), by keyword.

    Args:
        par_mot: maximum number of offers per keyword.

    Returns:
        The offers; [] without a token (credentials missing or refused).
    """
    import httpx

    tok = _ft_token()
    if not tok:
        return []
    H = {**UA, "Authorization": f"Bearer {tok}", "Accept": "application/json"}
    out, seen = [], set()
    for kw in _commun.KEYWORDS:
        try:
            r = _commun._get_borne(
                httpx,
                FT_SEARCH,
                timeout=25,
                headers=H,
                params={"motsCles": kw, "range": f"0-{par_mot - 1}"},
            )
            # 204 = no result, 206 = partial result (pagination): both OK
            if r.status_code not in (200, 206):
                continue
            res = r.json().get("resultats") or []
        except Exception:
            continue
        got = 0
        for j in res:
            u = (j.get("origineOffre") or {}).get(
                "urlOrigine"
            ) or f"https://candidat.francetravail.fr/offres/recherche/detail/{j.get('id')}"
            if u in seen:
                continue
            titre = str(j.get("intitule") or "").strip()
            if not title_ok(titre):
                continue
            seen.add(u)
            lieu = str((j.get("lieuTravail") or {}).get("libelle") or "")
            desc = str(j.get("description") or "")
            out.append(
                _mk(
                    titre,
                    u,
                    str((j.get("entreprise") or {}).get("nom") or "France Travail"),
                    lieu,
                    str(j.get("dateCreation") or "")[:10],
                    f"francetravail:{kw}",
                    desc,
                )
            )
            got += 1
        if got:
            _log.info(f"  ✓ france-travail «{kw}» → {got} offres")
        time.sleep(0.3)
    return out


def scan_france_travail() -> list[dict[str, Any]]:
    """France Travail collection; reports when the credentials are not configured.

    Returns:
        The offers.
    """
    o = fetch_france_travail()
    if not o and not FT_CFG.exists():
        _log.info(
            "  · France Travail ignore (Scripts/francetravail.json absent — voir le commentaire)"
        )
    else:
        _log.info(f"  ✓ France Travail → {len(o)} offres")
    return o
