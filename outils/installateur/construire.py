#!/usr/bin/env python3
"""Construit l'application autonome, puis l'installateur Windows JobHunterSetup.exe.

    python outils/installateur/construire.py            # dossier dist/JobHunter + installateur
    python outils/installateur/construire.py --sans-iss  # le dossier seul (pas d'Inno Setup)

Étapes :
  1. le squelette des données (profils d'exemple, réglages des sources, dossier du CV),
     copié au premier lancement dans Documents/JobHunter (jobhunter.gele) ;
  2. PyInstaller : JobHunter.exe et jobhunter-cli.exe dans dist/JobHunter/ ;
  3. contrôle : jobhunter-cli.exe charge chaque programme sans erreur ;
  4. Inno Setup (ISCC) : dist/JobHunterSetup.exe, installation sans droits
     d'administrateur dans %LOCALAPPDATA%/Programs/JobHunter.

La CI (.github/workflows/installateur.yml) le lance à chaque release et attache
l'installateur à la release. Décision : docs/adr/0011-application-autonome.md
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
RACINE = ICI.parent.parent
BUILD = ICI / "build"
DIST = RACINE / "dist"
SQUELETTE = (
    "profil/exemple_finance_esg.json",
    "profil/exemple_Faits.json",
    "Scripts/sources_config.json",
    "Mon_CV/LISEZ-MOI.txt",
)


def squelette() -> None:
    dest = BUILD / "squelette"
    shutil.rmtree(dest, ignore_errors=True)
    for rel in SQUELETTE:
        cible = dest / rel
        cible.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(RACINE / rel, cible)


def pyinstaller() -> Path:
    subprocess.run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            "--workpath",
            str(BUILD / "pyinstaller"),
            "--distpath",
            str(DIST),
            str(ICI / "JobHunter.spec"),
        ],
        check=True,
        # collect_submodules("jobhunter") importe le paquet : celui de src/, jamais une
        # version installée ailleurs (le runner de la CI n'en a pas, un poste de dev en
        # a souvent une plus ancienne).
        env=dict(os.environ, PYTHONPATH=str(RACINE / "src")),
    )
    return DIST / "JobHunter"


def controler(dossier: Path) -> None:
    """Chaque programme se charge dans l'exécutable compilé (un import oublié casse ici)."""
    code = (
        "import importlib, pkgutil, jobhunter.programmes as P\n"
        "ko = []\n"
        "for m in pkgutil.iter_modules(P.__path__):\n"
        "    if m.name.startswith('test_'): continue  # outils de dev : lisent la file\n"
        "    try: importlib.import_module('jobhunter.programmes.' + m.name)\n"
        "    except SystemExit: pass\n"
        "    except Exception as e: ko.append(f'{m.name}: {type(e).__name__}: {e}')\n"
        "import jobhunter.app.fenetre, jobhunter.sources.cli\n"
        "print('KO', ko) if ko else print('programmes charges')\n"
        "raise SystemExit(1 if ko else 0)\n"
    )
    env = dict(os.environ, JOBHUNTER_RACINE=str(BUILD / "donnees_essai"))
    subprocess.run([str(dossier / "jobhunter-cli.exe"), "-c", code], check=True, env=env)


def iscc() -> str:
    for p in (
        shutil.which("iscc"),
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
    ):
        if p and Path(p).exists():
            return p
    raise SystemExit("Inno Setup (ISCC) introuvable : https://jrsoftware.org/isdl.php")


def installateur() -> Path:
    version = (RACINE / "VERSION").read_text(encoding="utf-8").strip()
    subprocess.run(
        [
            iscc(),
            f"/DVersion={version}",
            f"/DSource={DIST / 'JobHunter'}",
            f"/O{DIST}",
            str(ICI / "JobHunter.iss"),
        ],
        check=True,
    )
    return DIST / "JobHunterSetup.exe"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--sans-iss", action="store_true", help="ne pas construire l'installateur")
    a = ap.parse_args()
    squelette()
    dossier = pyinstaller()
    controler(dossier)
    if not a.sans_iss:
        print("Installateur :", installateur())
    return 0


if __name__ == "__main__":
    sys.exit(main())
