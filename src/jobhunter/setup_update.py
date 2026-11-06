"""Updates of the installed application (JobHunterSetup.exe), in the background.

WHY. The update opened the installer's window and the user clicked through its steps
(the user, 2026-11-05: « la mise à jour doit se faire en background »). Desktop
applications (Chrome, VS Code) download the new version unasked, then install it when
the application restarts or closes.

HOW. At start-up the window downloads the signed release's installer and checks it
against the author's signature (programs.update), without a window. Once it is ready,
the title bar offers « Redémarrer pour mettre à jour ». Clicking it, or closing the
window, starts a hidden PowerShell that waits for JobHunter to exit, then runs the
installer with /VERYSILENT: per user (PrivilegesRequired=lowest), so no UAC prompt;
/RELANCER makes it start JobHunter again (JobHunter.iss). The data
(Documents/JobHunter) is not the installer's: it stays.

Only for the installer's copy (unins000.exe beside JobHunter.exe): the Store package
updates through the Store (store_update), a pip installation through pip.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

# Waits for the window's process, then installs; the values come by environment.
SCRIPT = r"""
try { Wait-Process -Id ([int]$env:JH_PID) -Timeout 120 -ErrorAction Stop } catch {}
$a = @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/NOCANCEL')
if ($env:JH_RELANCER -eq '1') { $a += '/RELANCER' }
Start-Process -FilePath $env:JH_SETUP -ArgumentList $a
"""


def concerne() -> bool:
    """This is the installer's copy of JobHunter: its updates can install silently."""
    from jobhunter import frozen

    if not frozen.est_gele() or frozen.paquet_msix():
        return False
    return Path(sys.executable).with_name("unins000.exe").is_file()


def chemin(version: str) -> Path:
    """Where the installer of `version` waits until it is installed."""
    return Path(tempfile.gettempdir()) / f"JobHunterSetup-{version}.exe"


def preparer(version: str) -> Path:
    """Downloads the installer of `version` and checks it; its path, ready to run.

    A copy already downloaded is checked again, never trusted as it is: the temporary
    folder is writable by any program of the user.

    Raises:
        signature.SignatureInvalide: the installer does not match the signed manifest.
        Exception: the download failed (offline, GitHub).
    """
    from jobhunter import signature
    from jobhunter.programs import update

    f = chemin(version)
    manifeste = update._signature(version)
    if f.is_file():
        try:
            signature.controler_setup(manifeste, f.read_bytes())
            return f
        except signature.SignatureInvalide:
            f.unlink(missing_ok=True)
    exe = update._get(update.ASSET_URL.format(version, update.SETUP), 900)
    signature.controler_setup(manifeste, exe)
    partiel = f.with_suffix(".partiel")
    partiel.write_bytes(exe)
    os.replace(partiel, f)
    return f


def apres_fermeture(script: str, valeurs: dict[str, str]) -> subprocess.Popen[bytes]:
    """Starts a hidden PowerShell `script` that outlives this process; values by environment.

    CREATE_NO_WINDOW only. With DETACHED_PROCESS (3.82 to 3.84) Windows PowerShell 5.1
    started, ran nothing and exited with code 0: « Désinstaller JobHunter », « Effacer mes
    données » and the update at closing did nothing at all (the user, 2026-11-06). The CI
    ran the scripts with subprocess.run, without those flags, and saw nothing.

    From the temporary folder: started from JobHunter's, it kept that folder in use and the
    uninstaller could not remove it.
    """
    return subprocess.Popen(  # nosec B603 B607 : fixed scripts, values by environment
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
        env=dict(os.environ, JH_PID=str(os.getpid()), **valeurs),
        cwd=tempfile.gettempdir(),
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def appliquer(setup: Path, version: str, relancer: bool) -> None:
    """Installs `setup` once this process has exited; JobHunter restarts if `relancer`."""
    from jobhunter.programs import update

    update.attendre_version(version, update.version_locale())
    apres_fermeture(SCRIPT, {"JH_SETUP": str(setup), "JH_RELANCER": "1" if relancer else ""})
