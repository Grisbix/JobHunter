"""Rendement de chaque source de collecte : ce qu'elle rapporte, et pourquoi pas plus.

Partie de jobhunter.sources. Une collecte vide a des causes opposées : rien de neuf à
prendre, ou un refus d'entrée. Ce module mesure chaque appel de source pendant la
collecte (durée, offres ramenées, incidents survenus pendant CET appel) ; la fusion y
ajoute les offres nouvelles et pertinentes. Chaque source reçoit un verdict :

refusé          refus d'entrée (401, 403, 999, CAPTCHA, défi anti-bot) et rien ramené
limité          limite de débit (429) rencontrée : la source a bridé, la passe est partielle
partiel         des erreurs (délai, réseau), mais des offres quand même
rien à prendre  aucune offre et aucun incident : une journée calme
ok              des offres, sans incident

Une ligne par collecte va dans `Scripts/_rendement.jsonl` ; `python JobHunter.pyw
rendement` en fait le bilan sur les derniers jours.

Decision : docs/adr/0004-429-attendre-403-arreter.md
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

# Mesures de la collecte en cours : {source: {"ramenees", "duree", "incidents"}}.
MESURES: dict[str, dict[str, Any]] = {}


def instantane() -> dict[str, dict[str, int]]:
    """Copie des incidents de la collecte, pour en calculer l'écart après un appel."""
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
    """Le verdict d'une source pour une collecte (voir l'en-tête du module).

    Args:
        ramenees: offres rendues par la source.
        incidents: {« source cause »: nombre} survenus pendant son appel.

    Returns:
        REFUSE, LIMITE, PARTIEL, VIDE ou OK.
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
    """Appelle une source et note son rendement. Les offres rendues sont étiquetées
    `_passe` = `nom` pour que la fusion compte les nouvelles par source.

    Une exception de la source remonte comme avant ; la mesure est notée quand même.
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
    """Ajoute aux mesures les offres uniques (après dédoublonnage du scan) et, depuis la
    fusion, les nouvelles et les pertinentes ; pose le verdict de chaque source."""
    n_uniques = collections.Counter(str(o.get("_passe") or "") for o in uniques)
    for nom, m in MESURES.items():
        m["uniques"] = n_uniques.get(nom, 0)
        m["nouvelles"] = par_source.get(nom, {}).get("nouvelles", 0)
        m["pertinentes"] = par_source.get(nom, {}).get("pertinentes", 0)
        m["verdict"] = verdict(int(m["ramenees"]), m["incidents"])


def enregistrer(chemin: Path, quand: datetime.datetime | None = None) -> None:
    """Ajoute la collecte au journal de rendement (une ligne JSON)."""
    if not MESURES:
        return
    ligne = {
        "le": (quand or datetime.datetime.now()).isoformat(timespec="seconds"),
        "sources": MESURES,
    }
    with open(chemin, "a", encoding="utf-8") as f:
        f.write(json.dumps(ligne, ensure_ascii=False) + "\n")


def resume() -> list[str]:
    """Une ligne par source mesurée, pour la fin de la collecte."""
    lignes = []
    for nom, m in sorted(MESURES.items()):
        lignes.append(
            f"  {nom:<14} {m.get('verdict', '?'):<15} {m['ramenees']:>5} ramenées"
            f" · {m.get('nouvelles', 0):>4} nouvelles · {m.get('pertinentes', 0):>3} pertinentes"
            f" · {m['duree']:>6.1f} s"
        )
    return lignes


def bilan(lignes: Iterable[dict[str, Any]], depuis: str = "") -> dict[str, dict[str, Any]]:
    """Cumule le journal par source depuis la date `depuis` (ISO ; "" = tout).

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
    """Les collectes du journal ; les lignes illisibles sont sautées."""
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
