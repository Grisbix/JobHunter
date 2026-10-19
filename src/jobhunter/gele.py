"""JobHunter installé sans Python : l'application compilée (PyInstaller) et son interpréteur.

L'installateur Windows (`JobHunterSetup.exe`, outils/installateur/) pose deux exécutables
dans le même dossier, compilés depuis ce paquet :

- `JobHunter.exe`, sans console : l'application ;
- `jobhunter-cli.exe`, avec console : tout ce que l'application lance en sous-processus.
  L'app appelle ses programmes par `[PY, "-m", module, ...]` ; ici PY est cet exécutable,
  qui comprend `-m module` comme `python -m module`. Une console est nécessaire : le
  premier lancement pose ses questions au clavier, et un exécutable sans console n'a pas
  de sortie standard à lire pour le journal de l'app.

Les données de l'utilisateur ne vivent jamais dans le dossier du programme (remplacé à
chaque mise à jour) : elles vont dans `Documents/JobHunter`, ou dans `JOBHUNTER_RACINE`
si la variable est posée. Au premier lancement, ce dossier reçoit le squelette livré :
profils d'exemple, réglages des sources, dossier pour le CV. Un fichier déjà présent n'est
jamais écrasé.

Décision : docs/adr/0011-application-autonome.md
"""

import os
import runpy
import shutil
import sys
from collections.abc import Sequence
from pathlib import Path

CONSOLE = "jobhunter-cli.exe"
SQUELETTE = "squelette"  # dossier livré à côté du code compilé


def est_gele() -> bool:
    """Vrai dans l'application compilée (PyInstaller), faux sous Python."""
    return bool(getattr(sys, "frozen", False))


def interpreteur() -> str:
    """L'exécutable qui lance `-m module` dans une console.

    Compilé : `jobhunter-cli.exe`, à côté de l'exécutable courant. Sous Python : le
    `python.exe` qui tourne, jamais `pythonw.exe` (sans console ni sortie standard).
    """
    exe = Path(sys.executable or "python")
    if est_gele():
        return str(exe.with_name(CONSOLE))
    if exe.name.lower() == "pythonw.exe":
        return str(exe.with_name("python.exe"))
    return str(exe)


def dossier_donnees() -> Path:
    """Où vivent les données de l'application installée.

    `JOBHUNTER_RACINE` si elle est posée, sinon `Documents/JobHunter` de l'utilisateur.
    """
    env = os.environ.get("JOBHUNTER_RACINE")
    if env:
        return Path(env)
    return Path.home() / "Documents" / "JobHunter"


def preparer_donnees(dest: Path, squelette: Path) -> list[Path]:
    """Copie dans `dest` les fichiers du squelette qui y manquent.

    Args:
        dest: le dossier des données.
        squelette: le squelette livré (profil/, Scripts/, Mon_CV/…).

    Returns:
        Les fichiers copiés ; un fichier déjà présent n'est jamais remplacé.
    """
    copies: list[Path] = []
    for d in ("Scripts", "profil", "Mon_CV", "CV", "Lettres"):
        (dest / d).mkdir(parents=True, exist_ok=True)
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
    """Ce que fait l'exécutable selon ses arguments, comme `python` ou `JobHunter.pyw`.

    - `-m module args…` : lance le module comme `python -m` ;
    - `-c code` : exécute le code (contrôles de la mise à jour) ;
    - `commande args…` : une commande de `jobhunter` (collecte, documents…) ;
    - rien : l'application.

    Returns:
        Le code de sortie.
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
        # Comme `python -c` : l'appelant est l'application elle-même (mise à jour).
        exec(compile(args[1], "<-c>", "exec"), {"__name__": "__main__"})  # noqa: S102  # nosec B102
        return 0
    if args:
        from jobhunter.cli import main as commande

        return commande(args)
    # Par son nom, comme `jobhunter app` : le moteur n'importe pas l'interface.
    # jobhunter.app.__main__ assure le profil, puis ouvre la fenêtre.
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
        # L'application part du dossier des données, comme depuis un dossier cloné.
        # Un sous-processus garde le dossier que son appelant a choisi (cwd=Scripts/…).
        os.chdir(dest)
    return aiguiller(sys.argv[1:])
