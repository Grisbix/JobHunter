"""Ou vivent les donnees : la racine de l'installation, et son dossier Scripts/.

Regle du projet : JAMAIS de racine codee en dur. Les chemins ont bouge quatre fois en
deux jours, et tout ce qui codait une racine a casse en silence. On detecte donc par
MARQUEUR : la variable JOBHUNTER_RACINE si elle est posee, sinon le premier dossier,
en remontant depuis ce fichier, qui contient a la fois Scripts/ et profil/ ; sinon le
meme marqueur en remontant depuis le dossier courant (paquet installe par pip, hors du
dossier de l'utilisateur).

Les fichiers de donnees (apply_queue.json, descriptions.json, suivi.json) restent dans
Scripts/ : les y deplacer casserait les installations existantes et la mise a jour.
"""

import os
from pathlib import Path


def racine() -> Path:
    env = os.environ.get("JOBHUNTER_RACINE")
    if env:
        return Path(env).resolve()
    ici = Path.cwd().resolve()
    for d in [*Path(__file__).resolve().parents, ici, *ici.parents]:
        if (d / "Scripts").is_dir() and (d / "profil").is_dir():
            return d
    raise RuntimeError(
        "Racine de JobHunter introuvable (aucun dossier parent avec Scripts/ et profil/) : "
        "definir JOBHUNTER_RACINE."
    )


def exporter_paquet() -> None:
    """Ajoute le dossier qui contient le paquet `jobhunter` a PYTHONPATH, herite par les
    sous-processus : `python -m jobhunter.sources` y marche sans installation. Le
    chemin vient de ce fichier, jamais d'une racine codee en dur."""
    src = str(Path(__file__).resolve().parent.parent)
    deja = os.environ.get("PYTHONPATH", "")
    if src not in deja.split(os.pathsep):
        os.environ["PYTHONPATH"] = os.pathsep.join(p for p in (src, deja) if p)


def scripts() -> Path:
    """Le dossier des donnees de travail (file, descriptions, suivi)."""
    return racine() / "Scripts"
