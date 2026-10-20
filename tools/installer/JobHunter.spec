# -*- mode: python ; coding: utf-8 -*-
# Standalone application: two executables in the same folder, no Python on the machine.
#   JobHunter.exe      the application, without a console
#   jobhunter-cli.exe  the programs launched by the application (console)
# Build: python tools/installer/build.py   (docs : ADR 0011)
import os

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

ICI = SPECPATH
RACINE = os.path.dirname(os.path.dirname(ICI))
SQUELETTE = os.path.join(ICI, "build", "squelette")

cachees = collect_submodules("jobhunter")  # dispatched by name (-m module, jobhunter <command>)
donnees = (
    collect_data_files("customtkinter")
    + collect_data_files("docx")
    + collect_data_files("jobhunter", includes=["sources/directories/*"])
    + [
        (SQUELETTE, "squelette"),
        (os.path.join(RACINE, "VERSION"), "."),
        (os.path.join(RACINE, "CHANGELOG.md"), "."),
    ]
)

a = Analysis(
    [os.path.join(ICI, "launcher.py")],
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
