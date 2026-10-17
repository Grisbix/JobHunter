#!/usr/bin/env python3
"""rejets_tri.py — Les offres que tri_file a retirees, pour que la collecte ne
les reprenne pas.

POURQUOI. Le tri juge sur la DESCRIPTION (experience exigee, seniorite), que la
collecte LinkedIn n'a pas encore au moment de fusionner. Une offre retiree a
midi revenait donc le soir meme comme « nouvelle », on refaisait sa description,
et le tri la retirait encore. Mesure du 2026-10-05 : sur 1469 offres retirees par
le tri du soir, 1157 l'avaient deja ete a midi — environ 900 requetes LinkedIn
par passe pour rien, et autant de risques de limite de debit (899 bridages 429
ce soir-la).

C'est le pendant automatique de `exclusions.py`, qui memorise les refus faits a
la main. La cle est la meme : l'oid « entreprise|poste », jamais l'URL.

LE REJET EXPIRE APRES 30 JOURS. Les regles du tri changent ; une offre mal jugee
ne doit pas rester invisible indefiniment. Une offre encore en ligne un mois plus
tard repassera le tri avec les regles du jour.
"""

import datetime
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
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
    """{oid: {"m": motif, "d": date}} des rejets encore valables."""
    jour = jour or datetime.date.today()
    return {k: v for k, v in _lire(chemin or FICHIER).items() if _vivant(v, jour)}


def ajouter(rejets, chemin=None, jour=None):
    """Memorise {oid: motif}. Purge les rejets expires. Ecriture atomique.

    Un rejet deja connu garde sa date d'origine : sinon une offre retiree chaque
    jour ne verrait jamais expirer son rejet."""
    chemin = Path(chemin or FICHIER)
    jour = jour or datetime.date.today()
    d = charger(chemin, jour)
    for oid, motif in rejets.items():
        d.setdefault(oid, {"m": motif, "d": jour.isoformat()})
    tmp = chemin.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=0), encoding="utf-8")
    os.replace(tmp, chemin)
    return len(d)
