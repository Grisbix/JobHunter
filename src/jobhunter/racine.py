"""Where the data lives: the root of the installation, and its Scripts/ folder.

Project rule: NEVER a hard-coded root. The paths moved four times in two days, and
everything that hard-coded a root broke silently. So we detect by MARKER: the
JOBHUNTER_RACINE variable if it is set, otherwise the first folder, going up from this
file, that contains both Scripts/ and profil/; otherwise the same marker going up from
the current folder (package installed by pip, outside the user's folder).

The data files (apply_queue.json, descriptions.json, suivi.json) stay in Scripts/:
moving them would break the existing installations and the update.
"""

import os
from pathlib import Path


def racine() -> Path:
    """The data folder: the one that contains `Scripts/` and `profil/`.

    Looks for `JOBHUNTER_RACINE`, then going up from this file, then from the current
    folder. Never a hard-coded root.

    Returns:
        The absolute path of the data folder.

    Raises:
        RuntimeError: no candidate folder contains `Scripts/` and `profil/`.
    """
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
    """Adds the folder that contains the `jobhunter` package to PYTHONPATH.

    Inherited by subprocesses: `python -m jobhunter.sources` works there without
    installation. The path comes from this file, never from a hard-coded root.
    """
    src = str(Path(__file__).resolve().parent.parent)
    deja = os.environ.get("PYTHONPATH", "")
    if src not in deja.split(os.pathsep):
        os.environ["PYTHONPATH"] = os.pathsep.join(p for p in (src, deja) if p)


def scripts() -> Path:
    """The working data folder (queue, descriptions, tracking)."""
    return racine() / "Scripts"
