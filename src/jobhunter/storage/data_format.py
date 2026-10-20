"""The version of the data's FORMAT, so an older JobHunter never writes over a newer one.

Installed side by side, restored from an old installer, or a second computer late by a
version: an older program reads the queue or the tracking file, understands part of it,
and writes back what it understood — losing what a newer version added. Each data folder
says which format wrote it (`_format.json`); a program that only knows an older format
refuses to WRITE there, and says why. Reading stays allowed.

FORMAT goes up only for a change an older version would damage (a field renamed, a
structure changed) — not for a new optional field, which older versions keep as is
(the queue's offers are dicts written back whole).
"""

import json
from pathlib import Path

from jobhunter.storage import atomic as atomique

FORMAT = 1
FICHIER = "_format.json"


class FormatPlusRecent(RuntimeError):
    """The data was written by a newer JobHunter: this one must not write over it."""


def lire(dossier: Path) -> int | None:
    """The format recorded in `dossier`, None if none is."""
    try:
        v = json.loads((dossier / FICHIER).read_text(encoding="utf-8")).get("format")
    except (OSError, ValueError, AttributeError):
        return None
    return v if isinstance(v, int) else None


def verifier_ecriture(dossier: Path) -> None:
    """Before writing data in `dossier`: refuse a newer format, record ours if none.

    Raises:
        FormatPlusRecent: the folder holds data of a newer format; nothing must be written.
    """
    v = lire(dossier)
    if v is not None and v > FORMAT:
        raise FormatPlusRecent(
            f"les données de {dossier} viennent d'une version plus récente de JobHunter "
            f"(format {v}, celle-ci connaît le {FORMAT}) : rien n'a été écrit. "
            f"Mets JobHunter à jour (Maintenance → Mettre à jour JobHunter)."
        )
    if v is None and dossier.is_dir():
        try:
            from importlib.metadata import version

            par = version("jobhunter")
        except Exception:  # running from the source code, not installed
            par = "?"
        try:
            atomique.ecrire_json(dossier / FICHIER, {"format": FORMAT, "par": par})
        except OSError:
            pass  # a read-only folder: the write that follows will say so
