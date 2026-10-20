"""Yield of each collection source: what it brings, and why not more.

Part of jobhunter.sources. An empty collection has opposite causes: nothing new to
take, or a refusal of entry. This module measures each source call during the
collection (duration, offers brought back, incidents that occurred during THAT call); the merge
adds the new and relevant offers. Each source gets a verdict:

refusé          refusal of entry (401, 403, 999, CAPTCHA, anti-bot challenge) and nothing brought back
limité          rate limit (429) met: the source throttled, the pass is partial
partiel         errors (timeout, network), but offers all the same
rien à prendre  no offer and no incident: a calm day
ok              offers, without incident

One line per collection goes into `Scripts/_rendement.jsonl`; `python JobHunter.pyw
rendement` sums it up over the last days.

Decision: docs/adr/0004-429-wait-403-stop.md
"""

import collections
import datetime
import json
import re
import time
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

from jobhunter.reseau import INCIDENTS

REFUSE, LIMITE, PARTIEL, VIDE, OK = "refusé", "limité", "partiel", "rien à prendre", "ok"
_RX_REFUS = re.compile(r"\b(?:401|403|999)\b|captcha|challenge|anti-?bot|bloqu", re.I)
_RX_LIMITE = re.compile(r"\b429\b")

# Measurements of the current collection: {source: {"ramenees", "duree", "incidents"}}.
MESURES: dict[str, dict[str, Any]] = {}


def instantane() -> dict[str, dict[str, int]]:
    """Copy of the collection's incidents, to compute their difference after a call."""
    return {s: {str(c): int(n) for c, n in par.items()} for s, par in INCIDENTS.items()}


def ecart(avant: dict[str, dict[str, int]]) -> dict[str, int]:
    """Incidents survenus depuis `avant`, toutes sources réunies : {« source cause »: n}."""
    sortie: dict[str, int] = {}
    for s, par in instantane().items():
        for c, n in par.items():
            d = n - avant.get(s, {}).get(c, 0)
            if d > 0:
                sortie[f"{s} {c}"] = d
    return sortie


def verdict(ramenees: int, incidents: dict[str, int]) -> str:
    """The verdict of a source for one collection (see the module header).

    Args:
        ramenees: offers returned by the source.
        incidents: {"source cause": count} that occurred during its call.

    Returns:
        REFUSE, LIMITE, PARTIEL, VIDE or OK.
    """
    causes = " ".join(incidents)
    if _RX_REFUS.search(causes) and not ramenees:
        return REFUSE
    if _RX_LIMITE.search(causes):
        return LIMITE
    if incidents:
        return PARTIEL if ramenees else REFUSE if _RX_REFUS.search(causes) else PARTIEL
    return OK if ramenees else VIDE


def mesurer(
    nom: str, fn: Callable[..., list[dict[str, Any]]], *args: Any, **kw: Any
) -> list[dict[str, Any]]:
    """Calls a source and records its yield.

    The returned offers are labelled `_passe` = `nom` so that the merge counts the
    new ones per source.

    An exception from the source propagates as before; the measurement is recorded anyway.
    """
    avant = instantane()
    debut = time.monotonic()
    offres: list[dict[str, Any]] = []
    try:
        offres = fn(*args, **kw) or []
        return offres
    finally:
        for o in offres:
            o["_passe"] = nom
        MESURES[nom] = {
            "ramenees": len(offres),
            "duree": round(time.monotonic() - debut, 1),
            "incidents": ecart(avant),
        }


def completer(uniques: Iterable[dict[str, Any]], par_source: dict[str, dict[str, int]]) -> None:
    """Adds to the measurements the unique offers (after the scan's dedup) and, from the merge, the new and the relevant ones; sets each source's verdict."""
    n_uniques = collections.Counter(str(o.get("_passe") or "") for o in uniques)
    for nom, m in MESURES.items():
        m["uniques"] = n_uniques.get(nom, 0)
        m["nouvelles"] = par_source.get(nom, {}).get("nouvelles", 0)
        m["pertinentes"] = par_source.get(nom, {}).get("pertinentes", 0)
        m["verdict"] = verdict(int(m["ramenees"]), m["incidents"])


def enregistrer(chemin: Path, quand: datetime.datetime | None = None) -> None:
    """Appends the collection to the yield log (one JSON line)."""
    if not MESURES:
        return
    ligne = {
        "le": (quand or datetime.datetime.now()).isoformat(timespec="seconds"),
        "sources": MESURES,
    }
    with open(chemin, "a", encoding="utf-8") as f:
        f.write(json.dumps(ligne, ensure_ascii=False) + "\n")


def resume() -> list[str]:
    """One line per measured source, for the end of the collection."""
    lignes = []
    for nom, m in sorted(MESURES.items()):
        lignes.append(
            f"  {nom:<14} {m.get('verdict', '?'):<15} {m['ramenees']:>5} ramenées"
            f" · {m.get('nouvelles', 0):>4} nouvelles · {m.get('pertinentes', 0):>3} pertinentes"
            f" · {m['duree']:>6.1f} s"
        )
    return lignes


def bilan(lignes: Iterable[dict[str, Any]], depuis: str = "") -> dict[str, dict[str, Any]]:
    """Sums the log per source since the date `depuis` (ISO; "" = everything).

    Returns:
        {source: {collectes, ramenees, nouvelles, pertinentes, duree, verdicts: Counter}}
    """
    total: dict[str, dict[str, Any]] = {}
    for ligne in lignes:
        if str(ligne.get("le", "")) < depuis:
            continue
        for nom, m in (ligne.get("sources") or {}).items():
            t = total.setdefault(
                nom,
                {
                    "collectes": 0,
                    "ramenees": 0,
                    "nouvelles": 0,
                    "pertinentes": 0,
                    "duree": 0.0,
                    "verdicts": collections.Counter(),
                },
            )
            t["collectes"] += 1
            for k in ("ramenees", "nouvelles", "pertinentes"):
                t[k] += int(m.get(k) or 0)
            t["duree"] += float(m.get("duree") or 0)
            t["verdicts"][str(m.get("verdict") or "?")] += 1
    return total


def lire_journal(chemin: Path) -> list[dict[str, Any]]:
    """The collections of the log; unreadable lines are skipped."""
    sortie: list[dict[str, Any]] = []
    try:
        texte = chemin.read_text(encoding="utf-8")
    except OSError:
        return sortie
    for l in texte.splitlines():
        try:
            d = json.loads(l)
        except ValueError:
            continue
        if isinstance(d, dict):
            sortie.append(d)
    return sortie
