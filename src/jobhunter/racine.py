"""Ou vivent les donnees : la racine de l'installation, et son dossier Scripts/.

Regle du projet : JAMAIS de racine codee en dur. Les chemins ont bouge quatre fois en
deux jours, et tout ce qui codait une racine a casse en silence. On detecte donc par
MARQUEUR : la variable JOBHUNTER_RACINE si elle est posee, sinon le premier dossier,
en remontant depuis ce fichier, qui contient a la fois Scripts/ et profil/.

Les fichiers de donnees (apply_queue.json, descriptions.json, suivi.json) restent dans
Scripts/ : les y deplacer casserait les installations existantes et la mise a jour.
"""

import os
from pathlib import Path


def racine() -> Path:
    env = os.environ.get("JOBHUNTER_RACINE")
    if env:
        return Path(env).resolve()
    for d in Path(__file__).resolve().parents:
        if (d / "Scripts").is_dir() and (d / "profil").is_dir():
            return d
    raise RuntimeError(
        "Racine de JobHunter introuvable (aucun dossier parent avec Scripts/ et profil/) : "
        "definir JOBHUNTER_RACINE."
    )


def scripts() -> Path:
    """Le dossier des donnees de travail (file, descriptions, suivi)."""
    return racine() / "Scripts"
