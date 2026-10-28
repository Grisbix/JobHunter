"""The order of the offers: the decimal fit, adjusted by what the fit cannot see.

The fit (`fit`, `fit_fin`) measures the posting against the profile, from its text.
Two things outside the text change how worth applying an offer is:

- REPOSTED again and again (programs/reposts, `republiee`): an offer taken down and
  put back three times in 90 days is often a "ghost" posting, not a vacancy;
- the CONTRACT, when the user's own choices say so: a user who applies to V.I.E.
  offers the fit scored 6 wants them higher (`jobhunter evaluation --analyse` measures it).

`rang` is the fit_fin minus a small penalty, plus a bonus per contract: it moves an
offer within its fit, rarely past a whole point. The fit displayed does not change;
the table, the folders to prepare and the notifications follow `rang`.

Profile, section `classement` (all optional):

    "classement": {
        "malus_republiee": 0.3,          # default 0.3
        "republiee_des": 3,              # from how many reposts; default 3
        "bonus_contrat": {"V.I.E": 0.5}  # by the offer's `contrat`; default none
    }
"""

from collections.abc import Mapping
from typing import Any

from jobhunter import profile as _P

MALUS_REPUBLIEE = 0.3
REPUBLIEE_DES = 3


def reglages(profil: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """The `classement` section with its defaults."""
    if profil is None:
        r = _P.get("classement", {}) or {}
        profil = r if isinstance(r, Mapping) else {}
    bonus = profil.get("bonus_contrat") or {}
    return {
        "malus_republiee": float(profil.get("malus_republiee", MALUS_REPUBLIEE)),
        "republiee_des": int(profil.get("republiee_des", REPUBLIEE_DES)),
        "bonus_contrat": {str(k): float(v) for k, v in bonus.items()}
        if isinstance(bonus, Mapping)
        else {},
    }


def fit_decimal(o: Mapping[str, Any]) -> float:
    """`fit_fin`, failing that `fit`, failing that 0."""
    for cle in ("fit_fin", "fit"):
        v = o.get(cle)
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            return float(v)
        if isinstance(v, str) and v.strip().lstrip("-").isdigit():
            return float(v)
    return 0.0


def ajustement(o: Mapping[str, Any], r: Mapping[str, Any] | None = None) -> float:
    """What the rank adds to the fit: the contract's bonus minus the repost penalty."""
    r = r or reglages()
    a = float(r["bonus_contrat"].get(str(o.get("contrat") or ""), 0.0))
    n = o.get("republiee") or 0
    if isinstance(n, int) and n >= r["republiee_des"]:
        a -= r["malus_republiee"]
    return a


def rang(o: Mapping[str, Any], r: Mapping[str, Any] | None = None) -> float:
    """The offer's place: higher first. `r` = reglages(), to pass when sorting many."""
    return fit_decimal(o) + ajustement(o, r)
