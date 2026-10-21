"""The collection every morning: the Windows scheduled task, created from the application.

`launchers/schedule.bat` only serves the installation from source code. The installed
application (without Python) had nothing: one had to click "Actualiser les offres"
every day. This module creates the SAME task (same name, so one replaces the other),
with the right command in both cases:

- installed application: `jobhunter-cli.exe pipeline` (the data is in
  `Documents/JobHunter`, which the executable finds on its own);
- source code: `python.exe JobHunter.pyw pipeline`, like `launchers/schedule.bat`.

Nothing is created without a click from the user; `schtasks` acts for their account
only, without administrator rights. Outside Windows: `launchers/schedule.sh` (cron).
"""

import os
import re
import subprocess  # nosec B404 : schtasks, arguments built here
import sys
import tempfile
import time
from pathlib import Path
from xml.sax.saxutils import escape

from jobhunter import frozen as _gele
from jobhunter import profiles as _profils
from jobhunter import root as _racine

TACHE = "JobHunter - collecte quotidienne"  # the name in schedule.bat
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
    lanceur = _profils.principale() / "JobHunter.pyw"  # the task runs every profile
    if not lanceur.exists():
        raise FileNotFoundError(
            f"{lanceur} introuvable : lance launchers\\schedule.bat depuis le code."
        )
    return f'"{_gele.interpreteur()}" "{lanceur}" pipeline'


def _schtasks(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # nosec B603 B607 : schtasks, fixed or validated arguments
        ["schtasks", *args], capture_output=True, text=True, timeout=30
    )


def planifiee() -> bool:
    """True if the task already exists (created here or by schedule.bat)."""
    if not disponible():
        return False
    try:
        return _schtasks("/Query", "/TN", TACHE).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def xml_tache(commande: str, heure: str) -> str:
    """The task's definition, for `schtasks /Create /XML`.

    - StartWhenAvailable: a morning missed is caught up as soon as the computer is on.
    - Not stopped nor skipped on battery; at most 8 hours; one run at a time.
    - NO working directory. On 21 October 2026 the author's task still started in a
      data folder renamed by the migration: Windows refused to launch it (0x8007010B)
      and the morning collection silently did not happen. The command finds its data
      by itself (JobHunter.pyw, the installed executable).
    - The user's own account, only while they are logged on, no elevation.
    """
    m = re.match(r'^"([^"]+)"\s*(.*)$', commande)
    exe, args = (m.group(1), m.group(2)) if m else (commande, "")
    debut = time.strftime("%Y-%m-%d")
    return f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>JobHunter : collecte quotidienne des offres.</Description>
  </RegistrationInfo>
  <Triggers>
    <CalendarTrigger>
      <StartBoundary>{debut}T{heure}:00</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByDay><DaysInterval>1</DaysInterval></ScheduleByDay>
    </CalendarTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <ExecutionTimeLimit>PT8H</ExecutionTimeLimit>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{escape(exe)}</Command>
      <Arguments>{escape(args)}</Arguments>
    </Exec>
  </Actions>
</Task>
"""


def creer(heure: str = "08:00") -> tuple[bool, str]:
    """Creates (or replaces) the daily task. Returns (success, message for the user)."""
    if not disponible():
        return False, "Hors Windows : lance ./launchers/schedule.sh depuis le dossier de JobHunter."
    if not _RX_HEURE.match(heure):
        return False, f"Heure invalide : « {heure} » (format 08:00)."
    try:
        cmd = commande()
    except FileNotFoundError as e:
        return False, str(e)
    # Through an XML definition: `/SC DAILY` alone leaves Windows' defaults, under which
    # a morning missed (computer off or asleep at 08:00) is simply skipped, and a laptop
    # on battery does not start the collection at all.
    f = Path(tempfile.gettempdir()) / f"jobhunter_tache_{os.getpid()}.xml"
    try:
        f.write_text(xml_tache(cmd, heure), encoding="utf-16")
        r = _schtasks("/Create", "/F", "/TN", TACHE, "/XML", str(f))
    finally:
        f.unlink(missing_ok=True)
    if r.returncode != 0:
        return False, f"La tâche n'a pas pu être créée : {(r.stderr or r.stdout).strip()}"
    return True, (
        f"Collecte planifiée chaque jour à {heure} ; si l'ordinateur était éteint, "
        "elle se fait dès qu'il est rallumé. "
        f"Journaux : {Path(_racine.nom('Scripts')) / '_logs'}."
    )


def supprimer() -> tuple[bool, str]:
    """Removes the task. Returns (success, message for the user)."""
    if not disponible():
        return False, "Hors Windows : ./launchers/schedule.sh supprimer."
    r = _schtasks("/Delete", "/TN", TACHE, "/F")
    if r.returncode != 0:
        return False, f"La tâche n'a pas pu être retirée : {(r.stderr or r.stdout).strip()}"
    return True, "Collecte quotidienne retirée."
