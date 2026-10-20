"""The collection every morning: the Windows scheduled task, created from the application.

`lanceurs/planifier.bat` only serves the installation from source code. The installed
application (without Python) had nothing: one had to click "Actualiser les offres"
every day. This module creates the SAME task (same name, so one replaces the other),
with the right command in both cases:

- installed application: `jobhunter-cli.exe pipeline` (the data is in
  `Documents/JobHunter`, which the executable finds on its own);
- source code: `python.exe JobHunter.pyw pipeline`, like `lanceurs/planifier.bat`.

Nothing is created without a click from the user; `schtasks` acts for their account
only, without administrator rights. Outside Windows: `lanceurs/planifier.sh` (cron).
"""

import re
import subprocess  # nosec B404 : schtasks, arguments built here
import sys
from pathlib import Path

from jobhunter import gele as _gele
from jobhunter import racine as _racine

TACHE = "JobHunter - collecte quotidienne"  # the name in planifier.bat
_RX_HEURE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def disponible() -> bool:
    """Vrai sous Windows, où `schtasks` existe."""
    return sys.platform == "win32"


def commande() -> str:
    """The line that the task runs (schtasks' `/TR`).

    Raises:
        FileNotFoundError: source code without `JobHunter.pyw` at the data root.
    """
    if _gele.est_gele():
        return f'"{_gele.interpreteur()}" pipeline'
    lanceur = _racine.racine() / "JobHunter.pyw"
    if not lanceur.exists():
        raise FileNotFoundError(
            f"{lanceur} introuvable : lance lanceurs\\planifier.bat depuis le code."
        )
    return f'"{_gele.interpreteur()}" "{lanceur}" pipeline'


def _schtasks(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # nosec B603 B607 : schtasks, fixed or validated arguments
        ["schtasks", *args], capture_output=True, text=True, timeout=30
    )


def planifiee() -> bool:
    """True if the task already exists (created here or by planifier.bat)."""
    if not disponible():
        return False
    try:
        return _schtasks("/Query", "/TN", TACHE).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def creer(heure: str = "08:00") -> tuple[bool, str]:
    """Creates (or replaces) the daily task. Returns (success, message for the user)."""
    if not disponible():
        return False, "Hors Windows : lance ./lanceurs/planifier.sh depuis le dossier de JobHunter."
    if not _RX_HEURE.match(heure):
        return False, f"Heure invalide : « {heure} » (format 08:00)."
    try:
        cmd = commande()
    except FileNotFoundError as e:
        return False, str(e)
    r = _schtasks("/Create", "/F", "/SC", "DAILY", "/ST", heure, "/TN", TACHE, "/TR", cmd)
    if r.returncode != 0:
        return False, f"La tâche n'a pas pu être créée : {(r.stderr or r.stdout).strip()}"
    return True, (
        f"Collecte planifiée chaque jour à {heure}, si l'ordinateur est allumé. "
        f"Journaux : {Path('Scripts') / '_logs'}."
    )


def supprimer() -> tuple[bool, str]:
    """Removes the task. Returns (success, message for the user)."""
    if not disponible():
        return False, "Hors Windows : ./lanceurs/planifier.sh supprimer."
    r = _schtasks("/Delete", "/TN", TACHE, "/F")
    if r.returncode != 0:
        return False, f"La tâche n'a pas pu être retirée : {(r.stderr or r.stdout).strip()}"
    return True, "Collecte quotidienne retirée."
