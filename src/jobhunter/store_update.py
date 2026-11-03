"""Updates of the Microsoft Store package, installed from inside the application.

WHY. The Store installs its updates on its own schedule, days later, and the button
« Mettre à jour » only opened the Store's page, where the user had to click again (the
user, 2026-11-02: « mises à jour directement dans l'app, pas besoin de cliquer dans la
mise à jour de Microsoft »).

HOW. Windows' own API for that, `Windows.Services.Store.StoreContext`: it asks the
Store which updates exist for this package, then downloads and installs them without
any window (`TrySilentDownloadAndInstallStorePackageUpdatesAsync`, Windows 10 2004 and
later). It is reached through Windows PowerShell, which can call WinRT types: no new
dependency in the package. A process started by the packaged application runs with
its identity, so the Store answers for JobHunter.

The installation closes JobHunter. `RegisterApplicationRestart` (called at start-up by
the window, web/__main__.py) makes Windows start it again once the update is in.

Nothing here touches GitHub: the version comes from the Store, which received it from
the author's submission.
"""

import subprocess

# One PowerShell script, two actions: "verifier" prints the number of updates, "installer"
# downloads and installs them and prints the final state (Completed, …). WinRT's
# asynchronous operations are awaited through System.WindowsRuntimeSystemExtensions.AsTask.
SCRIPT = r"""
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$m = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object { $_.Name -eq 'AsTask' -and $_.IsGenericMethod }
function Attendre1($op, [Type]$t) {
  $f = $m | Where-Object { $_.GetParameters().Count -eq 1 -and $_.GetGenericArguments().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' } | Select-Object -First 1
  $task = $f.MakeGenericMethod($t).Invoke($null, @($op)); [void]$task.Wait(-1); $task.Result
}
function Attendre2($op, [Type]$t, [Type]$p) {
  $f = $m | Where-Object { $_.GetParameters().Count -eq 1 -and $_.GetGenericArguments().Count -eq 2 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperationWithProgress`2' } | Select-Object -First 1
  $task = $f.MakeGenericMethod($t, $p).Invoke($null, @($op)); [void]$task.Wait(-1); $task.Result
}
$null = [Windows.Services.Store.StoreContext, Windows.Services.Store, ContentType = WindowsRuntime]
$ctx = [Windows.Services.Store.StoreContext]::GetDefault()
$liste = [System.Collections.Generic.IReadOnlyList[Windows.Services.Store.StorePackageUpdate]]
$maj = Attendre1 ($ctx.GetAppAndOptionalStorePackageUpdatesAsync()) $liste
if ($env:JH_ACTION -eq 'verifier') { "MAJ " + $maj.Count; exit 0 }
if ($maj.Count -eq 0) { "ETAT Aucune"; exit 0 }
$r = Attendre2 ($ctx.TrySilentDownloadAndInstallStorePackageUpdatesAsync($maj)) ([Windows.Services.Store.StorePackageUpdateResult]) ([Windows.Services.Store.StorePackageUpdateStatus])
"ETAT " + $r.OverallState
"""


def _lancer(action: str, delai: int) -> str:
    """Runs the script; its output, or "" when PowerShell or the Store did not answer."""
    import os

    try:
        r = subprocess.run(  # nosec B603 B607 : fixed script, the action by environment
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", SCRIPT],
            capture_output=True,
            text=True,
            encoding="oem",
            errors="replace",
            timeout=delai,
            env=dict(os.environ, JH_ACTION=action),
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return r.stdout if r.returncode == 0 else ""


def mises_a_jour(delai: int = 60) -> int | None:
    """The number of updates the Store has for this package; None if it did not say."""
    for ligne in _lancer("verifier", delai).splitlines():
        if ligne.startswith("MAJ "):
            try:
                return int(ligne[4:])
            except ValueError:
                return None
    return None


def installer(delai: int = 1800) -> str:
    """Downloads and installs the Store's updates, without a window.

    Returns the final state ("Completed", "Aucune" when nothing was waiting, …), "" if
    the Store did not answer. When it completes, Windows closes JobHunter to replace
    it: this call may never return.
    """
    for ligne in _lancer("installer", delai).splitlines():
        if ligne.startswith("ETAT "):
            return ligne[5:].strip()
    return ""


def redemarrer_apres_maj() -> None:
    """Asks Windows to start JobHunter again after an update of its package.

    Flags: not after a crash (1), a hang (2) nor a reboot (8): only after an update.
    """
    import sys

    if sys.platform != "win32":
        return
    import ctypes

    try:
        ctypes.windll.kernel32.RegisterApplicationRestart(None, 1 | 2 | 8)  # type: ignore[attr-defined,unused-ignore]
    except (AttributeError, OSError):
        pass
