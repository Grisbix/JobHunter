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
# Offers the feed served BEFORE the title filter, by feed identity (set by the fetchers
# that know it): 0 there is an empty page, not "nothing for this profile".
BRUTS: dict[str, int] = {}
MUET_JOURS = 30


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
    if ident in BRUTS:
        MESURES[ident]["brut"] = BRUTS.pop(ident)


def brut(outil: str, cle_flux: str, n: int) -> None:
    """How many offers the feed served before the title filter (see BRUTS)."""
    BRUTS[cle(outil, cle_flux)] = int(n)


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
        # Before 3.15 the state had no dates per kind of result: a feed that had
        # offers at its last success had them then.
        if "retenues_le" not in e and e.get("offres") and e.get("succes"):
            e["retenues_le"] = e["succes"]
        e.setdefault("premier", le)
        e["tentative"] = le
        if m["incident"]:
            e["incident"], e["incident_le"] = m["incident"], le
        else:
            e["succes"], e["offres"], e["incident"] = le, m["offres"], ""
            if m["offres"]:
                e["retenues_le"] = le
            if m.get("brut") is not None:
                e["brut"] = m["brut"]
                if m["brut"]:
                    e["brut_le"] = le
        etat[ident] = e
    tmp = chemin.with_name(chemin.name + ".tmp")
    tmp.write_text(json.dumps(etat, ensure_ascii=False, indent=0), encoding="utf-8")
    tmp.replace(chemin)


def _jours(depuis: str | None, maintenant: datetime.datetime) -> int | None:
    try:
        return (maintenant - datetime.datetime.fromisoformat(str(depuis))).days
    except ValueError:
        return None


def muet(
    e: dict[str, Any], maintenant: datetime.datetime | None = None, jours: int = MUET_JOURS
) -> str:
    """Why a followed company's feed brought nothing for `jours` days; '' if it did.

    A company whose career page moved (a new ATS, a renamed tenant) does not fail
    loudly: its feed answers, empty, every morning, and its offers are simply missed.
    Three cases, worst first:
      - failing: no success for `jours` days (refused, 404, timeout);
      - empty page: answers, but served no offer at all for `jours` days — the address
        has probably changed (known for the fetchers that count before the filter);
      - nothing for the profile: offers served, none kept by the title filter.
    The count starts at the first collection that recorded the feed (`premier`): a
    feed is never called silent before it has been followed for `jours` days.
    """
    maintenant = maintenant or datetime.datetime.now()
    age = _jours(e.get("premier") or e.get("tentative"), maintenant)
    if age is None or age < jours:
        return ""
    sans_succes = _jours(e.get("succes"), maintenant) if e.get("succes") else age
    if sans_succes is not None and sans_succes >= jours:
        return f"en échec depuis {sans_succes} j" if e.get("succes") else "jamais réussie"
    if "brut" in e and not e.get("brut"):
        vide = _jours(e.get("brut_le"), maintenant) if e.get("brut_le") else age
        if vide is not None and vide >= jours:
            return f"page vide depuis {vide} j"
    rien = _jours(e.get("retenues_le"), maintenant) if e.get("retenues_le") else age
    if rien is not None and rien >= jours:
        return f"rien pour ton profil depuis {rien} j"
    return ""


def muets(
    etat: dict[str, dict[str, Any]],
    suspendus: set[str] | None = None,
    maintenant: datetime.datetime | None = None,
) -> dict[str, str]:
    """{feed: reason} of the followed feeds silent for MUET_JOURS days, suspended ones aside."""
    suspendus = suspendus or set()
    out = {}
    for ident, e in etat.items():
        if ident in suspendus or not isinstance(e, dict):
            continue
        r = muet(e, maintenant)
        if r:
            out[ident] = r
    return out
