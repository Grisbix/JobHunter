# -*- mode: python ; coding: utf-8 -*-
# Application autonome : deux exécutables dans un même dossier, sans Python sur la machine.
#   JobHunter.exe      l'application, sans console
#   jobhunter-cli.exe  les programmes lancés par l'application (console)
# Construction : python outils/installateur/construire.py   (docs : ADR 0011)
import os

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

ICI = SPECPATH
RACINE = os.path.dirname(os.path.dirname(ICI))
SQUELETTE = os.path.join(ICI, "build", "squelette")

cachees = collect_submodules("jobhunter")  # aiguillés par nom (-m module, jobhunter <commande>)
donnees = (
    collect_data_files("customtkinter")
    + collect_data_files("docx")
    + collect_data_files("jobhunter", includes=["sources/annuaires/*"])
    + [
        (SQUELETTE, "squelette"),
        (os.path.join(RACINE, "VERSION"), "."),
        (os.path.join(RACINE, "CHANGELOG.md"), "."),
    ]
)

a = Analysis(
    [os.path.join(ICI, "lanceur.py")],
    pathex=[os.path.join(RACINE, "src")],
    datas=donnees,
    hiddenimports=cachees,
    excludes=["pytest", "mypy", "ruff", "IPython", "matplotlib", "numpy", "pandas"],
    noarchive=False,
)
pyz = PYZ(a.pure)

app = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="JobHunter",
    console=False,
    icon=None,
)
cli = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="jobhunter-cli",
    console=True,
    icon=None,
)
COLLECT(app, cli, a.binaries, a.datas, name="JobHunter")
