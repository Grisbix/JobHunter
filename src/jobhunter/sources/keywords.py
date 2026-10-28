"""The words a source searches with: the user's, not a list written for one profession.

The user, 2026-10-28: « ce serait bien qu'on automatise tout ça plutôt que de rajouter
à chaque fois un domaine qui m'intéresse ». freehire, EURES, the Bundesagentur and the
Workday feeds each searched a list of ESG / finance words written in their module: a
seasonal worker in the mountains, or anyone outside that field, got nothing from them.

Their words now come, in this order, from:

1. `mots_sources.<source>` in sources_config.json — a hand-tuned list for one source;
2. the profile's collection keywords (`collecte.mots_cles`), the first `n` of them,
   once each — what LinkedIn and the boards already search;
3. the module's own list, for an installation whose profile has no keyword yet.
"""

import json
from collections.abc import Sequence

from jobhunter.sources import common as _commun


def _sur_mesure(source: str) -> list[str]:
    try:
        cfg = json.loads(_commun.SOURCES_CFG.read_text(encoding="utf-8"))
    except (OSError, ValueError, AttributeError):
        return []
    v = (cfg.get("mots_sources") or {}).get(source) if isinstance(cfg, dict) else None
    return [str(m).strip() for m in v if str(m).strip()] if isinstance(v, list) else []


def du_profil(n: int) -> list[str]:
    """The profile's first `n` collection keywords, once each whatever their case."""
    vus, sortie = set(), []
    for m in _commun.KEYWORDS or []:
        m = " ".join(str(m).split())
        if m and m.lower() not in vus:
            vus.add(m.lower())
            sortie.append(m)
    return sortie[:n]


def mots(source: str, defaut: Sequence[str], n: int) -> list[str]:
    """The words `source` searches with (see the module's docstring for the order).

    Args:
        source: its key in `mots_sources` (« freehire », « eures »…).
        defaut: the module's own list, used when the profile has no keyword.
        n: at most this many words from the profile — each one is a request or more.
    """
    return _sur_mesure(source) or du_profil(n) or list(defaut)
