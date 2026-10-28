"""JobHunter's shortcut in the Start menu (and on the desktop), for an installation from
source or with pip.

Run with pythonw.exe, the window showed Python's logo once pinned to the taskbar: the
window has its own identity (Grisbix.JobHunter), and with no shortcut carrying it,
Windows pins the program behind it, pythonw.exe (the user, 2026-10-28: « un logo qui
soit partout le même, pas un logo Python »). This shortcut has JobHunter's icon and the
window's identity, so the taskbar, the pin and the Start menu all show JobHunter.

The installer (JobHunterSetup.exe) makes its own shortcuts: nothing to do there.

    jobhunter shortcut            the Start menu
    jobhunter shortcut --bureau   the desktop too
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

AUMID = "Grisbix.JobHunter"
ICONE = Path(__file__).resolve().parents[1] / "app" / "assets" / "jobhunter.ico"

# The shortcut by WScript.Shell, then the window's identity (System.AppUserModel.ID)
# through its property store: WScript.Shell cannot set it. Values come by environment
# variables, never pasted into the script.
_PS = r"""
$ErrorActionPreference = "Stop"
$s = (New-Object -ComObject WScript.Shell).CreateShortcut($env:JH_LIEN)
$s.TargetPath = $env:JH_CIBLE
$s.Arguments = $env:JH_ARGS
$s.WorkingDirectory = $env:JH_DOSSIER
$s.IconLocation = "$env:JH_ICONE,0"
$s.Description = "JobHunter"
$s.Save()
Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public static class JhLien {
  [StructLayout(LayoutKind.Sequential)] public struct PK { public Guid fmtid; public uint pid; }
  [StructLayout(LayoutKind.Explicit)] public struct PV { [FieldOffset(0)] public ushort vt; [FieldOffset(8)] public IntPtr p; }
  [ComImport, Guid("886D8EEB-8CF2-4446-8D02-CDBA1DBDCF99"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
  public interface IPropertyStore {
    int GetCount(out uint c); int GetAt(uint i, out PK k); int GetValue(ref PK k, out PV v);
    int SetValue(ref PK k, ref PV v); int Commit();
  }
  [DllImport("shell32.dll", CharSet = CharSet.Unicode, PreserveSig = false)]
  static extern void SHGetPropertyStoreFromParsingName(string path, IntPtr pbc, int flags,
    ref Guid iid, [MarshalAs(UnmanagedType.Interface)] out IPropertyStore ps);
  public static void Poser(string chemin, string id) {
    Guid iid = typeof(IPropertyStore).GUID;
    IPropertyStore ps;
    SHGetPropertyStoreFromParsingName(chemin, IntPtr.Zero, 2, ref iid, out ps);
    PK k = new PK { fmtid = new Guid("9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3"), pid = 5 };
    PV v = new PV { vt = 31, p = Marshal.StringToCoTaskMemUni(id) };
    try { Marshal.ThrowExceptionForHR(ps.SetValue(ref k, ref v)); Marshal.ThrowExceptionForHR(ps.Commit()); }
    finally { Marshal.FreeCoTaskMem(v.p); Marshal.ReleaseComObject(ps); }
  }
}
"@
[JhLien]::Poser($env:JH_LIEN, $env:JH_AUMID)
"""


def cible() -> tuple[Path, str, Path]:
    """What the shortcut starts: pythonw.exe (no console), JobHunter.pyw if the data
    folder has one, else the installed package; and the folder it starts in."""
    from jobhunter import root

    py = Path(sys.executable)
    pyw = py.with_name("pythonw.exe")
    exe = pyw if pyw.is_file() else py
    dossier = root.racine()
    lanceur = dossier / "JobHunter.pyw"
    args = f'"{lanceur}"' if lanceur.is_file() else "-m jobhunter app"
    return exe, args, dossier


def dossiers(bureau: bool) -> list[Path]:
    """The Start menu's Programs folder, and the desktop if asked."""
    appdata = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    sortie = [appdata / "Microsoft" / "Windows" / "Start Menu" / "Programs"]
    if bureau:
        sortie.append(Path(os.environ.get("USERPROFILE", Path.home())) / "Desktop")
    return sortie


def existe() -> bool:
    """The Start menu shortcut is there (ours, or the installer's: same folder, same name)."""
    return (dossiers(False)[0] / "JobHunter.lnk").is_file()


def assurer() -> None:
    """Makes the Start menu shortcut once, when missing, for a source or pip installation.

    Called at the window's opening, in the background: an installation from before 3.59
    gets it without running anything. Silent on failure: cosmetic only.
    """
    if sys.platform != "win32" or existe():
        return
    from jobhunter import frozen

    if frozen.est_gele():
        return
    try:
        creer(dossiers(False)[0] / "JobHunter.lnk", *cible())
    except (OSError, subprocess.SubprocessError):
        pass


def creer(lien: Path, exe: Path, args: str, dossier: Path) -> None:
    """Writes `lien` (.lnk); raises CalledProcessError when PowerShell fails."""
    env = dict(
        os.environ,
        JH_LIEN=str(lien),
        JH_CIBLE=str(exe),
        JH_ARGS=args,
        JH_DOSSIER=str(dossier),
        JH_ICONE=str(ICONE),
        JH_AUMID=AUMID,
    )
    subprocess.run(  # nosec B603 B607 : fixed script, values by environment
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", _PS],
        env=env,
        check=True,
        capture_output=True,
        text=True,
        timeout=120,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    p = argparse.ArgumentParser(prog="jobhunter shortcut", description=__doc__.split("\n\n")[0])
    p.add_argument("--bureau", action="store_true", help="aussi sur le bureau")
    a = p.parse_args(argv)
    if sys.platform != "win32":
        print("Raccourci : Windows seulement.")
        return 0
    from jobhunter import frozen

    if frozen.est_gele():
        print("L'installateur a déjà fait le raccourci de JobHunter.")
        return 0
    exe, args, dossier = cible()
    code = 0
    for d in dossiers(a.bureau):
        lien = d / "JobHunter.lnk"
        try:
            d.mkdir(parents=True, exist_ok=True)
            creer(lien, exe, args, dossier)
            print(f"Raccourci : {lien}")
        except (OSError, subprocess.SubprocessError) as e:
            detail = getattr(e, "stderr", "") or str(e)
            print(f"Raccourci impossible ({lien}) : {detail.strip()[:200]}")
            code = 1
    return code


if __name__ == "__main__":
    sys.exit(main())
