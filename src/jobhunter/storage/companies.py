"""Every company a collection has seen, kept after its offers leave the queue.

The user, 2026-10-27: each collection must note the company somewhere, to find its
offers again. The queue forgets a company once its offers close or are set aside;
this register does not. One entry per company (name compared without case or extra
spaces): first and last day seen, the sites its offers came from, and — when one of
its offer links is an ATS read by API (Greenhouse, Workday…) — that feed, so that the
company can be followed in one click.

Written by the merge, under the queue's lock, next to the queue: `companies_seen.json`.
A failure here never stops a merge (the queue is what matters).
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

from jobhunter.storage.atomic import ecrire_json

NOM_FICHIER = "companies_seen.json"


def cle(nom: object) -> str:
    """The company's identity in the register: « BNP  Paribas » = « bnp paribas »."""
    return re.sub(r"\s+", " ", str(nom or "")).strip().casefold()


def site(source: object) -> str:
    """« linkedin-search:analyste isr » → « linkedin »."""
    return str(source or "").partition(":")[0].removesuffix("-search").strip()


def chemin(queue: Path) -> Path:
    """The register, next to the queue."""
    return Path(queue).parent / NOM_FICHIER


def charger(queue: Path) -> dict[str, dict[str, Any]]:
    """The register; empty if absent or unreadable."""
    try:
        d = json.loads(chemin(queue).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return d if isinstance(d, dict) else {}


def _flux(url: str) -> dict[str, Any] | None:
    from jobhunter import inventory

    trouve = inventory.flux_depuis_url(url)
    if not trouve:
        return None
    outil, ident = trouve
    return {"outil": outil, "cle": list(ident) if isinstance(ident, tuple) else ident, "url": url}


def noter(
    queue: Path, vues: list[dict[str, Any]], jour: str | None = None
) -> dict[str, dict[str, Any]]:
    """Adds the companies of `vues` (offers just collected, or the queue) to the register."""
    jour = jour or time.strftime("%Y-%m-%d")
    reg = charger(queue)
    for o in vues:
        nom = str(o.get("entreprise") or "").strip()
        k = cle(nom)
        if not k or k in ("—", "-", "n/a", "inconnu", "confidentiel"):
            continue
        e = reg.setdefault(k, {"nom": nom, "premiere_vue": jour, "sites": []})
        e["derniere_vue"] = max(str(e.get("derniere_vue") or ""), jour)
        s = site(o.get("source"))
        if s and s not in e["sites"]:
            e["sites"] = sorted([*e["sites"], s])
        url = str(o.get("url") or "")
        if url and not e.get("flux"):
            f = _flux(url)
            if f:
                e["flux"] = f
    ecrire_json(chemin(queue), reg)
    return reg
