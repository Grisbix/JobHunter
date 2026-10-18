"""Journaux du moteur : `logging`, un format commun, un fichier par execution.

    _log = journal.journal(__name__)
    _log.info("LinkedIn : %d offres", n)

Tout le moteur ecrit sous le logger `jobhunter`. Sa console affiche le message seul,
sur la sortie standard du moment : ce que les programmes affichaient par `print`
s'affiche a l'identique, et le pipeline, qui capture la sortie de chaque etape, le
garde dans son journal comme avant.

`JOBHUNTER_JOURNAL=<fichier>` ajoute un fichier horodate (niveau, module) : le
pipeline le pose pour avoir un fichier par execution. `configurer()` fait la meme
chose depuis le code.

Rien n'est ouvert a l'import : le fichier l'est au premier message.
"""

import logging
import os
import sys
from pathlib import Path
from typing import TextIO

RACINE = "jobhunter"
FORMAT_FICHIER = "%(asctime)s %(levelname)-7s %(name)s : %(message)s"


class _Console(logging.StreamHandler[TextIO]):
    """La sortie standard DU MOMENT : un test (capsys) ou une redirection la remplace."""

    def __init__(self) -> None:
        super().__init__(sys.stdout)

    @property
    def stream(self) -> TextIO:
        return sys.stdout

    @stream.setter
    def stream(self, _valeur: TextIO) -> None:
        pass


def _installer() -> logging.Logger:
    racine = logging.getLogger(RACINE)
    if not any(isinstance(h, _Console) for h in racine.handlers):
        racine.addHandler(_Console())
        racine.setLevel(logging.INFO)
        racine.propagate = False
        fichier = os.environ.get("JOBHUNTER_JOURNAL")
        if fichier:
            configurer(fichier=Path(fichier))
    return racine


def journal(nom: str) -> logging.Logger:
    """Le logger d'un module du moteur (`journal(__name__)`)."""
    _installer()
    return logging.getLogger(nom if nom.startswith(RACINE) else f"{RACINE}.{nom}")


def configurer(niveau: int | None = None, fichier: Path | None = None) -> None:
    """Regle le niveau, et ajoute un fichier horodate (ouvert au premier message)."""
    racine = _installer()
    if niveau is not None:
        racine.setLevel(niveau)
    if fichier is not None and not any(
        isinstance(h, logging.FileHandler) and Path(h.baseFilename) == Path(fichier).resolve()
        for h in racine.handlers
    ):
        h = logging.FileHandler(fichier, encoding="utf-8", delay=True)
        h.setFormatter(logging.Formatter(FORMAT_FICHIER))
        racine.addHandler(h)
