"""Test one API access: one minimal request, no offer imported, nothing secret shown.

"The key is saved" is not "the access works": a key can be mistyped, revoked, or out of
quota for the day. `tester(nom)` makes ONE request — the smallest the provider allows —
and sorts the answer:

- `ok`: the service answered with data;
- `absente`: no key saved;
- `refusee`: the provider refused the key (401/403, or France Travail's token refused);
- `quota`: rate or daily limit reached (429, or our shared counter, sources.quota);
- `panne`: the service answered with an error (5xx, unexpected status);
- `reseau`: no answer (offline, timeout, DNS).

The request counts in the day's quota like any other. Only the exception's TYPE is ever
shown: an httpx message contains the URL, and Adzuna's URL carries the key.
"""

import json
from dataclasses import dataclass

from jobhunter.sources import common as _commun
from jobhunter.sources import quota as _quota

SOURCES = ("adzuna", "jooble", "usajobs", "francetravail")


@dataclass(frozen=True)
class Resultat:
    """What one test found: its state, and a short detail (HTTP code, exception type)."""

    etat: str  # ok, absente, refusee, quota, panne, reseau
    detail: str = ""


def _classer(code: int) -> Resultat:
    if code in (200, 206, 204):
        return Resultat("ok", f"HTTP {code}")
    if code in (401, 403):
        return Resultat("refusee", f"HTTP {code}")
    if code == 429:
        return Resultat("quota", "HTTP 429")
    return Resultat("panne", f"HTTP {code}")


def _cle(nom: str, *champs: str) -> tuple[str, ...] | None:
    from jobhunter import root as _racine

    try:
        d = json.loads((_racine.dossier_cles() / f"{nom}.json").read_text(encoding="utf-8"))
        valeurs = tuple(str(d[c]).strip() for c in champs)
    except (OSError, ValueError, KeyError, TypeError):
        return None
    return valeurs if all(valeurs) else None


def tester(nom: str) -> Resultat:
    """One minimal request to `nom` (adzuna, jooble, francetravail), sorted."""
    import httpx

    from jobhunter.sources import aggregators as _agreg
    from jobhunter.sources import countries as _pays
    from jobhunter.sources import francetravail as _ft

    champs = {"adzuna": ("app_id", "app_key"), "jooble": ("key",), "usajobs": ("email", "key")}
    if nom == "francetravail":
        cle = _cle(nom, "client_id", "client_secret")
    elif nom in champs:
        cle = _cle(nom, *champs[nom])
    else:
        raise ValueError(f"source sans clé : {nom}")
    if cle is None:
        return Resultat("absente")
    if not _quota.reserver(nom):
        return Resultat("quota", "quota du jour (tous profils)")
    try:
        if nom == "adzuna":
            r = _commun._get_borne(
                httpx,
                _agreg.ADZUNA_API.format(
                    pays=_pays.maison() if _pays.maison() in _agreg.ADZUNA_COUVERTS else "gb"
                ),
                timeout=20,
                headers=_commun.UA,
                params={
                    "app_id": cle[0],
                    "app_key": cle[1],
                    "what": "analyst",
                    "results_per_page": 1,
                },
            )
            return _classer(r.status_code)
        if nom == "jooble":
            r = _commun._post_borne(
                httpx,
                _agreg.JOOBLE_API.format(cle=cle[0]),
                timeout=20,
                headers={**_commun.UA, "Content-Type": "application/json"},
                json={
                    "keywords": "analyst",
                    "location": _pays.nom(),
                    "page": "1",
                    "ResultOnPage": 1,
                },
            )
            return _classer(r.status_code)
        if nom == "usajobs":
            r = _commun._get_borne(
                httpx,
                _agreg.USAJOBS_API,
                timeout=20,
                headers={
                    "Host": "data.usajobs.gov",
                    "User-Agent": cle[0],
                    "Authorization-Key": cle[1],
                },
                params={"Keyword": "analyst", "ResultsPerPage": 1},
            )
            return _classer(r.status_code)
        jeton = _ft._ft_token()
        if not jeton:
            return Resultat("refusee", "jeton refusé")
        r = _commun._get_borne(
            httpx,
            _ft.FT_SEARCH,
            timeout=20,
            headers={
                **_commun.UA,
                "Authorization": f"Bearer {jeton}",
                "Accept": "application/json",
            },
            params={"motsCles": "analyste", "range": "0-0"},
        )
        return _classer(r.status_code)
    except Exception as e:  # network: only the type, never the message (it holds the URL)
        return Resultat("reseau", type(e).__name__)
