"""JobHunter installed without Python: the compiled application (PyInstaller) and its interpreter.

The Windows installer (`JobHunterSetup.exe`, tools/installer/) puts two executables
in the same folder, compiled from this package:

- `JobHunter.exe`, without a console: the application;
- `jobhunter-cli.exe`, with a console: everything the application launches as a
  subprocess. The app calls its programs with `[PY, "-m", module, ...]`; here PY is
  this executable, which understands `-m module` like `python -m module`. A console
  is necessary: the first launch asks its questions at the keyboard, and an
  executable without a console has no standard output to read for the app's log.

The user's data never lives in the program's folder (replaced at each update): it goes
into `Documents/JobHunter`, or into `JOBHUNTER_RACINE` if the variable is set. At first
launch, this folder receives the shipped skeleton: example profiles, source settings,
folder for the CV. A file already present is never overwritten.

Decision: docs/adr/0011-standalone-application.md
"""

import os
import runpy
import shutil
import sys
from collections.abc import Sequence
from pathlib import Path

CONSOLE = "jobhunter-cli.exe"
SQUELETTE = "squelette"  # folder shipped next to the compiled code


def est_gele() -> bool:
    """Vrai dans l'application compilée (PyInstaller), faux sous Python."""
    return bool(getattr(sys, "frozen", False))


def interpreteur() -> str:
    """The executable that runs `-m module` in a console.

    Compiled: `jobhunter-cli.exe`, next to the current executable. Under Python: the
    running `python.exe`, never `pythonw.exe` (no console nor standard output).
    """
    exe = Path(sys.executable or "python")
    if est_gele():
        return str(exe.with_name(CONSOLE))
    if exe.name.lower() == "pythonw.exe":
        return str(exe.with_name("python.exe"))
    return str(exe)


def dossier_donnees() -> Path:
    """Where the installed application's data lives.

    `JOBHUNTER_RACINE` if it is set, otherwise the user's `Documents/JobHunter`.
    """
    env = os.environ.get("JOBHUNTER_RACINE")
    if env:
        return Path(env)
    return Path.home() / "Documents" / "JobHunter"


def preparer_donnees(dest: Path, squelette: Path) -> list[Path]:
    """Copies into `dest` the skeleton files that are missing there.

    Args:
        dest: the data folder.
        squelette: the shipped skeleton (profil/, Scripts/, Mon_CV/…).

    Returns:
        The files copied; a file already present is never replaced.
    """
    copies: list[Path] = []
    # In the layout of the folder: a 2.x installation keeps its names until it is
    # migrated (jobhunter.programs.migrate, at the application's start).
    from jobhunter import root as _racine

    for d in ("Scripts", "profil", "Mon_CV", "CV", "Lettres"):
        (dest / _racine.nom(d, dest)).mkdir(parents=True, exist_ok=True)
    if not squelette.is_dir():
        return copies
    for src in sorted(squelette.rglob("*")):
        if not src.is_file():
            continue
        cible = dest / src.relative_to(squelette)
        if cible.exists():
            continue
        cible.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, cible)
        copies.append(cible)
    return copies


def aiguiller(argv: Sequence[str]) -> int:
    """What the executable does depending on its arguments, like `python` or `JobHunter.pyw`.

    - `-m module args…`: runs the module like `python -m`;
    - `-c code`: executes the code (update checks);
    - `command args…`: a `jobhunter` command (collecte, documents…);
    - nothing: the application.

    Returns:
        The exit code.
    """
    args = list(argv)
    if len(args) >= 2 and args[0] == "-m":
        sys.argv = [args[1], *args[2:]]
        try:
            runpy.run_module(args[1], run_name="__main__", alter_sys=True)
        except SystemExit as e:
            return e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
        return 0
    if len(args) >= 2 and args[0] == "-c":
        sys.argv = ["-c", *args[2:]]
        # Like `python -c`: the caller is the application itself (update).
        exec(compile(args[1], "<-c>", "exec"), {"__name__": "__main__"})  # noqa: S102  # nosec B102
        return 0
    if args:
        from jobhunter.cli import main as commande

        return commande(args)
    # By its name, like `jobhunter app`: the engine does not import the interface.
    # jobhunter.app.__main__ ensures the profile, then opens the window.
    runpy.run_module("jobhunter.app", run_name="__main__", alter_sys=True)
    return 0


def main() -> int:
    """Point d'entrée des deux exécutables compilés."""
    for flux in (sys.stdout, sys.stderr):
        if flux is not None and hasattr(flux, "reconfigure"):
            flux.reconfigure(encoding="utf-8", errors="replace")
    dest = dossier_donnees()
    preparer_donnees(dest, Path(getattr(sys, "_MEIPASS", ".")) / SQUELETTE)
    os.environ["JOBHUNTER_RACINE"] = str(dest)
    if len(sys.argv) == 1:
        # The application starts from the data folder, as from a cloned folder.
        # A subprocess keeps the folder its caller chose (cwd=Scripts/…).
        os.chdir(dest)
    return aiguiller(sys.argv[1:])
