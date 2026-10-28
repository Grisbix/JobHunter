#!/usr/bin/env python3
"""Builds the standalone application, then the Windows installer JobHunterSetup.exe.

    python tools/installer/build.py            # dist/JobHunter folder + installer
    python tools/installer/build.py --sans-iss  # the folder only (no Inno Setup)

Steps:
  1. the data skeleton (example profiles, source settings, CV folder), copied at
     first launch into Documents/JobHunter (jobhunter.frozen);
  2. PyInstaller: JobHunter.exe and jobhunter-cli.exe in dist/JobHunter/;
  3. Playwright's node.exe (88 MB) leaves the folder for dist/playwright-node-win64.zip,
     attached to the release and fetched the first time a browser starts
     (jobhunter.playwright_node): the installer loses about half its weight;
  4. check: jobhunter-cli.exe loads each program without error;
  5. Inno Setup (ISCC): dist/JobHunterSetup.exe, installed without administrator
     rights in %LOCALAPPDATA%/Programs/JobHunter.

The CI (.github/workflows/installer.yml) runs it at each release and attaches
the installer to the release. Decision: docs/adr/0011-standalone-application.md
"""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ICI = Path(__file__).resolve().parent
RACINE = ICI.parent.parent
BUILD = ICI / "build"
DIST = RACINE / "dist"
SQUELETTE = (
    "profile/example_finance_esg.json",
    "profile/example_Facts.json",
    "data/sources_config.json",
    "My_CV/README.txt",
)
NODE_ZIP = "playwright-node-win64.zip"  # same names in jobhunter.playwright_node
NODE_MANIFESTE = "jobhunter_node.json"
DEPOT = "https://github.com/Grisbix/JobHunter"


def version() -> str:
    return (RACINE / "VERSION").read_text(encoding="utf-8").strip()


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
        # collect_submodules("jobhunter") imports the package: the one in src/, never a
        # version installed elsewhere (the CI runner has none, a dev machine often
        # has an older one).
        env=dict(os.environ, PYTHONPATH=str(RACINE / "src")),
    )
    return DIST / "JobHunter"


def sortir_node(dossier: Path) -> Path | None:
    """Takes node.exe out of the application into dist/playwright-node-win64.zip.

    The zip is reproducible (fixed date, fixed compression): the same Node gives the
    same file from one version to the next, and the application keeps its copy.

    Returns:
        The zip, or None when the folder has no node.exe (already taken out).
    """
    interne = dossier / "_internal"
    node = interne / "playwright" / "driver" / "node.exe"
    if not node.is_file():
        return None
    octets = node.read_bytes()
    z = DIST / NODE_ZIP
    info = zipfile.ZipInfo("node.exe", date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    with zipfile.ZipFile(z, "w") as f:
        f.writestr(info, octets, compresslevel=9)
    manifeste = {
        "url": f"{DEPOT}/releases/download/v{version()}/{NODE_ZIP}",
        "sha256": hashlib.sha256(z.read_bytes()).hexdigest(),
        "node": hashlib.sha256(octets).hexdigest(),
    }
    (interne / NODE_MANIFESTE).write_text(json.dumps(manifeste, indent=2), encoding="utf-8")
    node.unlink()
    return z


def controler(dossier: Path) -> None:
    """Each program loads inside the compiled executable (a forgotten import breaks here)."""
    code = (
        "import importlib, pkgutil, jobhunter.programs as P\n"
        "ko = []\n"
        "for m in pkgutil.iter_modules(P.__path__):\n"
        "    if m.name.startswith('test_'): continue  # outils de dev : lisent la file\n"
        "    try: importlib.import_module('jobhunter.programs.' + m.name)\n"
        "    except SystemExit: pass\n"
        "    except Exception as e: ko.append(f'{m.name}: {type(e).__name__}: {e}')\n"
        "import jobhunter.app.window, jobhunter.sources.cli, jobhunter.launch\n"
        "import jobhunter.web.api, webview  # the application's window since 3.29\n"
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
    subprocess.run(
        [
            iscc(),
            f"/DVersion={version()}",
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
    print("Node.js à part :", sortir_node(dossier))
    controler(dossier)
    if not a.sans_iss:
        print("Installateur :", installateur())
    return 0


if __name__ == "__main__":
    sys.exit(main())
