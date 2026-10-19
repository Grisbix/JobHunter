"""Engine logs: `logging`, a common format, one file per run.

    _log = journal.journal(__name__)
    _log.info("LinkedIn : %d offres", n)

The whole engine writes under the `jobhunter` logger. Its console shows the message
alone, on the current standard output: what the programs displayed through `print`
is displayed identically, and the pipeline, which captures the output of each step,
keeps it in its log as before.

`JOBHUNTER_JOURNAL=<file>` adds a timestamped file (level, module): the pipeline sets
it to have one file per run. `configurer()` does the same from the code.

Nothing is opened at import: the file is opened at the first message.
"""

import logging
import os
import sys
from pathlib import Path
from typing import TextIO

RACINE = "jobhunter"
FORMAT_FICHIER = "%(asctime)s %(levelname)-7s %(name)s : %(message)s"


class _Console(logging.StreamHandler[TextIO]):
    """The CURRENT standard output: a test (capsys) or a redirection replaces it."""

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
    """The logger of an engine module (`journal(__name__)`)."""
    _installer()
    return logging.getLogger(nom if nom.startswith(RACINE) else f"{RACINE}.{nom}")


def configurer(niveau: int | None = None, fichier: Path | None = None) -> None:
    """Sets the level, and adds a timestamped file (opened at the first message)."""
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
