"""The double-click launchers, in launchers/ since 2.24, work from the folder above.

Each one `cd`s to the JobHunter folder first: Mon_CV/, profil/, .venv and JobHunter.pyw
are found there, not in launchers/. A real run of lancer.bat (Windows) or lancer.sh
(macOS/Linux) in a copy: with a CV in Mon_CV and no profile, it must call
`JobHunter.pyw profile <the CV>` from the root — a stand-in JobHunter.pyw writes down
what it received. Nothing is installed, nothing opens.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parent.parent
LANCEURS = RACINE / "launchers"
NOMS = ("install", "start", "update", "schedule")


def test_plus_de_lanceur_a_la_racine():
    restes = [p.name for p in RACINE.iterdir() if p.suffix in (".bat", ".sh")]
    assert restes == []


@pytest.mark.parametrize("nom", NOMS)
def test_chaque_lanceur_part_du_dossier_parent(nom):
    bat = (LANCEURS / f"{nom}.bat").read_text(encoding="utf-8")
    sh = (LANCEURS / f"{nom}.sh").read_text(encoding="utf-8")
    assert 'cd /d "%~dp0.."' in bat
    assert 'cd "$(dirname "$0")/.."' in sh


def test_lancer_cree_le_profil_depuis_la_racine(tmp_path):
    shutil.copytree(LANCEURS, tmp_path / "launchers")
    (tmp_path / "Mon_CV").mkdir()
    (tmp_path / "Mon_CV" / "cv.docx").write_bytes(b"x")
    # Stand-in for the program: notes its arguments and its folder, then fails, so
    # that the launcher stops before opening the app.
    (tmp_path / "JobHunter.pyw").write_text(
        "import os, sys\n"
        "open('appel.txt', 'w', encoding='utf-8').write(os.getcwd() + '|' + '|'.join(sys.argv[1:]))\n"
        "sys.exit(1)\n",
        encoding="utf-8",
    )
    if sys.platform == "win32":
        cmd = ["cmd", "/c", str(tmp_path / "launchers" / "start.bat")]
    else:
        if not shutil.which("bash"):
            pytest.skip("bash absent")
        cmd = ["bash", str(tmp_path / "launchers" / "start.sh")]
    # The launcher calls `python`/`python3`: the folder of this interpreter goes first.
    if sys.platform == "win32":
        systeme = os.environ.get("SYSTEMROOT", r"C:\Windows")
        env = {"PATH": f"{Path(sys.executable).parent};{systeme}\\System32", "SYSTEMROOT": systeme}
    else:
        env = {"PATH": f"{Path(sys.executable).parent}:/usr/bin:/bin"}
    subprocess.run(
        cmd,
        cwd=tmp_path / "launchers",
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        timeout=60,
    )
    appel = (tmp_path / "appel.txt").read_text(encoding="utf-8").split("|")
    assert Path(appel[0]).resolve() == tmp_path.resolve()
    assert appel[1] == "profile"
    assert Path(appel[2]).name == "cv.docx"
