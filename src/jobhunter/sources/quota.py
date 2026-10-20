"""Calls to the keyed APIs, counted for the day across every profile.

The API keys are shared by all the profiles (root.dossier_cles(), ADR 0013): each new
profile multiplies the calls made with the same key. The counter lives next to the keys,
so every profile — and every process — counts in the same place, and a daily ceiling stops
a source before the provider does (an exhausted key is refused for the rest of the day,
for every profile).

Ceilings: `quotas_api` in the main profile's sources_config.json, {"adzuna": 250, …};
otherwise PLAFONDS. None = counted, never stopped.
"""

import json
import time
from pathlib import Path

from jobhunter import root as _racine
from jobhunter.storage import lock as _verrou

FICHIER = "_api_quota.json"
# Adzuna's free access: 250 calls a day. Jooble and France Travail publish no daily
# figure for these keys: counted only.
PLAFONDS: dict[str, int | None] = {"adzuna": 250, "jooble": None, "francetravail": None}


def _fichier() -> Path:
    return _racine.dossier_cles() / FICHIER


def plafond(nom: str) -> int | None:
    """The daily ceiling of `nom`: sources_config.json's quotas_api, otherwise PLAFONDS."""
    try:
        cfg = json.loads((_racine.dossier_cles() / "sources_config.json").read_text("utf-8"))
        v = (cfg.get("quotas_api") or {}).get(nom, PLAFONDS.get(nom))
    except (OSError, ValueError, AttributeError):
        v = PLAFONDS.get(nom)
    return int(v) if isinstance(v, int | float) and v > 0 else None


def _lire(f: Path) -> dict[str, dict[str, int]]:
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return d if isinstance(d, dict) else {}


def usage(nom: str, jour: str | None = None) -> int:
    """Calls made today with `nom`'s key, all profiles together."""
    return int(_lire(_fichier()).get(jour or time.strftime("%Y-%m-%d"), {}).get(nom, 0))


def reserver(nom: str) -> bool:
    """Counts one call to `nom`; False (nothing counted) if today's ceiling is reached.

    Under a lock: two profiles' collections running at once count without losing a call.
    If the counter cannot be written (read-only folder), the call is allowed: the
    counter protects the quota, it must never stop a collection by itself.
    """
    f = _fichier()
    jour = time.strftime("%Y-%m-%d")
    if not f.parent.is_dir() or not _verrou.prendre_verrou(f, attente=10, bavard=False):
        return True
    try:
        d = _lire(f)
        d = {jour: d.get(jour, {})}  # yesterday's counts are of no use
        n = int(d[jour].get(nom, 0))
        cap = plafond(nom)
        if cap is not None and n >= cap:
            return False
        d[jour][nom] = n + 1
        tmp = f.with_name(f.name + ".tmp")
        tmp.write_text(json.dumps(d), encoding="utf-8")
        tmp.replace(f)
        return True
    except OSError:
        return True
    finally:
        _verrou.rendre_verrou(f)
