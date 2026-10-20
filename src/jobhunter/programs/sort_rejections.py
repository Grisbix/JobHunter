#!/usr/bin/env python3
"""rejets_tri.py — The offers that tri_file removed, so that the collection does not take
them back.

WHY. The sorting judges on the DESCRIPTION (required experience, seniority), which the
LinkedIn collection does not have yet at merge time. An offer removed at noon thus came
back the same evening as "new", its description was fetched again, and the sorting
removed it again. Measured on 2026-10-05: of 1469 offers removed by the evening
sorting, 1157 had already been removed at noon — about 900 LinkedIn requests per pass
for nothing, and as many risks of a rate limit (899 throttlings with 429 that evening).

It is the automatic counterpart of `exclusions.py`, which remembers the refusals made
by hand. The key is the same: the oid "entreprise|poste", never the URL.

THE REJECTION EXPIRES AFTER 30 DAYS. The sorting rules change; a badly judged offer
must not stay invisible forever. An offer still online a month later will go through
the sorting again with the rules of the day.
"""

import datetime
import json
import os
from pathlib import Path

from jobhunter import root as _racine

HERE = _racine.scripts()
FICHIER = HERE / "_rejets_tri.json"
DUREE_JOURS = 30


def _lire(chemin):
    try:
        d = json.loads(Path(chemin).read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def _vivant(rec, jour):
    try:
        return (jour - datetime.date.fromisoformat(rec["d"])).days < DUREE_JOURS
    except Exception:
        return False


def charger(chemin=None, jour=None):
    """{oid: {"m": reason, "d": date}} of the rejections still valid."""
    jour = jour or datetime.date.today()
    return {k: v for k, v in _lire(chemin or FICHIER).items() if _vivant(v, jour)}


def ajouter(rejets, chemin=None, jour=None):
    """Remembers {oid: reason}. Purges the expired rejections. Atomic write.

    A rejection already known keeps its original date: otherwise an offer removed
    every day would never see its rejection expire."""
    chemin = Path(chemin or FICHIER)
    jour = jour or datetime.date.today()
    d = charger(chemin, jour)
    for oid, motif in rejets.items():
        d.setdefault(oid, {"m": motif, "d": jour.isoformat()})
    tmp = chemin.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=0), encoding="utf-8")
    os.replace(tmp, chemin)
    return len(d)
