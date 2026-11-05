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

# One PowerShell script, three actions: "verifier" prints the number of updates and their
# versions (the Store's, which may be older than GitHub's latest), "telecharger" only
# downloads them (JobHunter keeps running), "installer"
# downloads and installs them and prints the final state (Completed, …). WinRT's
# asynchronous operations are awaited through System.WindowsRuntimeSystemExtensions.AsTask.
# A failure prints « ERREUR 0x… message », the innermost exception: before, PowerShell's
# error went to stderr, which was dropped, and the window said only « pas de réponse »
# (the user, 2026-11-05).
SCRIPT = r"""
$ErrorActionPreference = 'Stop'
trap {
  $e = $_.Exception; while ($e.InnerException) { $e = $e.InnerException }
  "ERREUR 0x{0:X8} {1}" -f $e.HResult, $e.Message; exit 1
}
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
if ($env:JH_ACTION -eq 'verifier') {
  "MAJ " + $maj.Count
  foreach ($u in $maj) { $v = $u.Package.Id.Version; "VERSION {0}.{1}.{2}" -f $v.Major, $v.Minor, $v.Build }
  exit 0
}
if ($maj.Count -eq 0) { "ETAT Aucune"; exit 0 }
if ($env:JH_ACTION -eq 'telecharger') {
  $r = Attendre2 ($ctx.TrySilentDownloadStorePackageUpdatesAsync($maj)) ([Windows.Services.Store.StorePackageUpdateResult]) ([Windows.Services.Store.StorePackageUpdateStatus])
  "ETAT " + $r.OverallState; exit 0
}
$r = Attendre2 ($ctx.TrySilentDownloadAndInstallStorePackageUpdatesAsync($maj)) ([Windows.Services.Store.StorePackageUpdateResult]) ([Windows.Services.Store.StorePackageUpdateStatus])
"ETAT " + $r.OverallState
"""


def _lancer(action: str, delai: int) -> str:
    """Runs the script; its output (« ERREUR … » included), "" when PowerShell did not run."""
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
    return r.stdout or ""


def _erreur(sortie: str) -> str:
    """« erreur 0x803F6101 … » from the script's output, "" when it printed none."""
    for ligne in sortie.splitlines():
        if ligne.startswith("ERREUR "):
            return "erreur " + ligne[7:].strip()
    return ""


def mises_a_jour(delai: int = 60) -> int | None:
    """The number of updates the Store has for this package; None if it did not say."""
    return verifier(delai)[0]


def verifier(delai: int = 60) -> tuple[int | None, str, str]:
    """The Store's updates: their number, why none was given, the version to install.

    The error is "" when the Store answered; the version "" when it has none.

    The Store, not GitHub: a release reaches the Store's users only once Microsoft has
    certified it, hours or days later. Before, the window offered the GitHub version
    right away and the click failed (the user, 2026-11-05).
    """
    sortie = _lancer("verifier", delai)
    lignes = sortie.splitlines()
    versions = [x[8:].strip() for x in lignes if x.startswith("VERSION ")]
    for ligne in lignes:
        if ligne.startswith("MAJ "):
            try:
                return int(ligne[4:]), "", max(versions, key=_cle, default="")
            except ValueError:
                break
    return None, _erreur(sortie) or "pas de réponse", ""


def _cle(v: str) -> tuple[int, ...]:
    return tuple(int(x) if x.isdigit() else 0 for x in v.split("."))


def telecharger(delai: int = 1800) -> str:
    """Downloads the Store's updates without installing them: JobHunter keeps running.

    The installation, quick once downloaded, waits for the window to close (the user,
    2026-11-05: « possible sans redémarrer l'app ? »). Same returns as installer().
    """
    sortie = _lancer("telecharger", delai)
    for ligne in sortie.splitlines():
        if ligne.startswith("ETAT "):
            return ligne[5:].strip()
    return _erreur(sortie)


def ne_pas_redemarrer() -> None:
    """Cancels the restart after the update: installed at closing, JobHunter stays closed."""
    import sys

    if sys.platform != "win32":
        return
    import ctypes

    try:
        ctypes.windll.kernel32.UnregisterApplicationRestart()  # type: ignore[attr-defined,unused-ignore]
    except (AttributeError, OSError):
        pass


def installer(delai: int = 1800) -> str:
    """Downloads and installs the Store's updates, without a window.

    Returns the final state ("Completed", "Aucune" when nothing was waiting, …), the
    Store's error (« erreur 0x… ») or "" if it did not answer. When it completes, Windows
    closes JobHunter to replace it: this call may never return.
    """
    sortie = _lancer("installer", delai)
    for ligne in sortie.splitlines():
        if ligne.startswith("ETAT "):
            return ligne[5:].strip()
    return _erreur(sortie)


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
