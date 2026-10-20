"""Each followed company's feed: last attempt, last success, offers, incident; suspended or not.

The yield log (source_yield) says how a whole SOURCE did ("ats", "workday"). A company
whose career API moved, or that has closed its page, disappeared in that total: Workday
brought 2,375 offers, and nobody saw that one tenant had answered 404 for three weeks.

Per feed (`<tool>:<key>`, the key of app.inventory.Flux), `_flux_etat.json` keeps:

    {"workday:pwc": {"tentative": "2026-10-21T08:03", "succes": "2026-10-21T08:03",
                     "offres": 41, "incident": "", "incident_le": ""}}

A refused or failed feed keeps its last SUCCESS: a page that refuses us is not a closed
page. Suspending a feed (`flux_suspendus` in sources_config.json) stops its future
collections without removing it from the list, and without touching the offers or the
applications already there.
"""

import datetime
import json
from pathlib import Path
from typing import Any

from jobhunter.network import INCIDENTS

FICHIER = "_flux_etat.json"
CLE_CONFIG = "flux_suspendus"

MESURES: dict[str, dict[str, Any]] = {}


def cle(outil: str, cle_flux: str) -> str:
    """'workday:pwc' — a feed's identity; for variants 'a|b', the first one."""
    return f"{outil}:{str(cle_flux).split('|')[0]}"


def suspendus(cfg: dict[str, Any] | None = None) -> set[str]:
    """The suspended feeds (sources_config.json; the loaded configuration by default)."""
    if cfg is None:
        from jobhunter.sources import common as _commun

        try:
            cfg = json.loads(_commun.SOURCES_CFG.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            cfg = {}
        if not isinstance(cfg, dict):
            cfg = {}
    return {str(x) for x in (cfg.get(CLE_CONFIG) or []) if x}


def suspendre(cfg: dict[str, Any], ident: str, oui: bool = True) -> None:
    """Suspends (or resumes) a feed in the configuration `cfg`, modified in place."""
    s = [x for x in cfg.get(CLE_CONFIG) or [] if x != ident]
    if oui:
        s.append(ident)
    cfg[CLE_CONFIG] = sorted(s)


def instantane(prefixe: str) -> dict[str, int]:
    """The incidents counted so far under INCIDENTS[prefixe], to compare after a fetch."""
    return {str(k): int(n) for k, n in INCIDENTS.get(prefixe, {}).items()}


def nouveaux(prefixe: str, avant: dict[str, int]) -> str:
    """The incidents added since `avant`: 'HTTP 404 ×2, ReadTimeout' ('' if none)."""
    out = []
    for k, n in instantane(prefixe).items():
        d = n - avant.get(k, 0)
        if d > 0:
            out.append(f"{k} ×{d}" if d > 1 else k)
    return ", ".join(out)


def noter(ident: str, offres: int, incident: str = "") -> None:
    """Records this collection's result for one feed (written by enregistrer())."""
    MESURES[ident] = {"offres": int(offres), "incident": incident}


def _maintenant() -> str:
    return datetime.datetime.now().isoformat(timespec="minutes")


def lire(chemin: Path) -> dict[str, dict[str, Any]]:
    """The feeds' state; {} if the file is absent or unreadable."""
    try:
        d = json.loads(chemin.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return d if isinstance(d, dict) else {}


def enregistrer(chemin: Path, quand: str | None = None) -> None:
    """Merges this collection's results into `_flux_etat.json` (atomic write)."""
    if not MESURES:
        return
    le = quand or _maintenant()
    etat = lire(chemin)
    for ident, m in MESURES.items():
        e = dict(etat.get(ident) or {})
        e["tentative"] = le
        if m["incident"]:
            e["incident"], e["incident_le"] = m["incident"], le
        else:
            e["succes"], e["offres"], e["incident"] = le, m["offres"], ""
        etat[ident] = e
    tmp = chemin.with_name(chemin.name + ".tmp")
    tmp.write_text(json.dumps(etat, ensure_ascii=False, indent=0), encoding="utf-8")
    tmp.replace(chemin)
