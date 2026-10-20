"""Why an offer's score changed: its successive fits, with when, why, and under which rules.

An offer scored 6 yesterday and 9 today: did its posting gain a description, did the
profile change, or did a new engine score it differently? `poser()` sets the fit and,
only when it CHANGES, appends to the offer's `historique_fit`:

    {"date": "2026-10-20", "fit": 9, "cause": "description", "regles": "3.8.0·a1b2c3d4",
     "execution": "20261020-080012-a3f9"}

`regles` identifies the scoring rules in force: the engine's version and a fingerprint of
the profile's sections that score (domains, skills, scoring, title filter, zones…). Two
entries with different `regles` were computed under different rules. An unchanged fit
writes nothing; new offers start without history (the first change records the old
value first). At most MAX entries, the oldest go.
"""

import hashlib
import json
import time
from functools import cache
from typing import Any

from jobhunter import run_id as _execution

MAX = 10
# The profile's sections that change a score (profile.py). Identity, letters and form
# fields do not.
SECTIONS = (
    "domaines",
    "competences",
    "competences_de_base",
    "termes",
    "scoring",
    "niveau",
    "filtre_titre",
    "langues_parlees",
    "zones",
)


@cache
def regles() -> str:
    """'<engine version>·<profile fingerprint>', computed once per process."""
    try:
        from importlib.metadata import version

        moteur = version("jobhunter")
    except Exception:  # source code without installation
        moteur = "?"
    try:
        from jobhunter import profile as _profil

        p = _profil.charger()
        utile = {k: p.get(k) for k in SECTIONS}
        empreinte = hashlib.sha256(
            json.dumps(utile, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()[:8]
    except Exception:  # no profile yet
        empreinte = "?"
    return f"{moteur}·{empreinte}"


def poser(o: dict[str, Any], fit: int, exp: int, fit_fin: float, cause: str) -> None:
    """Sets the offer's fit (fit, exp_requise, fit_fin), recording a change of fit.

    Args:
        o: the offer, modified in place.
        fit: the new fit, 1 to 10 (fit_detail).
        exp: the years of experience the posting asks for.
        fit_fin: the fit with its tie-break decimals.
        cause: why it is recomputed — "description" (its text arrived or changed),
            "re-score" (recomputed with the current rules).
    """
    avant = o.get("fit")
    if isinstance(avant, int | float) and avant != fit:
        h = list(o.get("historique_fit") or [])
        if not h:  # the value it had before any history
            h.append({"date": str(o.get("process") or "?")[:10], "fit": avant, "cause": "?"})
        h.append(
            {
                "date": time.strftime("%Y-%m-%d"),
                "fit": fit,
                "cause": cause,
                "regles": regles(),
                "execution": _execution.courant(),
            }
        )
        o["historique_fit"] = h[-MAX:]
    o["fit"], o["exp_requise"], o["fit_fin"] = fit, exp, fit_fin
