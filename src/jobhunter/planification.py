"""La collecte chaque matin : la tâche planifiée Windows, créée depuis l'application.

`planifier.bat` ne sert qu'à l'installation depuis le code source. L'application
installée (sans Python) n'avait rien : il fallait cliquer « Actualiser les offres »
chaque jour. Ce module crée la MÊME tâche (même nom, donc l'une remplace l'autre), avec
la bonne commande dans les deux cas :

- application installée : `jobhunter-cli.exe pipeline` (les données sont dans
  `Documents/JobHunter`, que l'exécutable retrouve seul) ;
- code source : `python.exe JobHunter.pyw pipeline`, comme `planifier.bat`.

Rien n'est créé sans un clic de l'utilisateur ; `schtasks` agit pour son compte seul,
sans droits d'administrateur. Hors Windows : `planifier.sh` (cron).
"""

import re
import subprocess  # nosec B404 : schtasks, arguments construits ici
import sys
from pathlib import Path

from jobhunter import gele as _gele
from jobhunter import racine as _racine

TACHE = "JobHunter - collecte quotidienne"  # le nom de planifier.bat
_RX_HEURE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def disponible() -> bool:
    """Vrai sous Windows, où `schtasks` existe."""
    return sys.platform == "win32"


def commande() -> str:
    """La ligne que la tâche exécute (`/TR` de schtasks).

    Raises:
        FileNotFoundError: code source sans `JobHunter.pyw` à la racine des données.
    """
    if _gele.est_gele():
        return f'"{_gele.interpreteur()}" pipeline'
    lanceur = _racine.racine() / "JobHunter.pyw"
    if not lanceur.exists():
        raise FileNotFoundError(f"{lanceur} introuvable : lance planifier.bat depuis le code.")
    return f'"{_gele.interpreteur()}" "{lanceur}" pipeline'


def _schtasks(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # nosec B603 B607 : schtasks, arguments fixes ou validés
        ["schtasks", *args], capture_output=True, text=True, timeout=30
    )


def planifiee() -> bool:
    """Vrai si la tâche existe déjà (créée ici ou par planifier.bat)."""
    if not disponible():
        return False
    try:
        return _schtasks("/Query", "/TN", TACHE).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def creer(heure: str = "08:00") -> tuple[bool, str]:
    """Crée (ou remplace) la tâche quotidienne. Rend (réussi, message pour l'utilisateur)."""
    if not disponible():
        return False, "Hors Windows : lance ./planifier.sh depuis le dossier de JobHunter."
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
    """Retire la tâche. Rend (réussi, message pour l'utilisateur)."""
    if not disponible():
        return False, "Hors Windows : ./planifier.sh supprimer."
    r = _schtasks("/Delete", "/TN", TACHE, "/F")
    if r.returncode != 0:
        return False, f"La tâche n'a pas pu être retirée : {(r.stderr or r.stdout).strip()}"
    return True, "Collecte quotidienne retirée."
