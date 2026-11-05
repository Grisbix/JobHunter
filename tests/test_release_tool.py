"""tools/release.py: the package is installed with the data folder's Python, not the venv's."""

import importlib.util
import os
import sys
from pathlib import Path

OUTIL = Path(__file__).resolve().parent.parent / "tools" / "release.py"


def _outil():
    spec = importlib.util.spec_from_file_location("release_outil", OUTIL)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_installer_prend_le_python_hors_du_venv(tmp_path, monkeypatch):
    # 3.84.0: the venv's python (no pip) installed nothing after the release.
    nom = "python.exe" if sys.platform == "win32" else "python"
    venv, systeme = tmp_path / "venv", tmp_path / "systeme"
    for d in (venv / "Scripts", systeme):
        d.mkdir(parents=True)
        (d / nom).write_bytes(b"")
        (d / nom).chmod(0o755)
    monkeypatch.setattr(sys, "prefix", str(venv))
    monkeypatch.setenv("PATH", os.pathsep.join([str(venv / "Scripts"), str(systeme)]))
    trouve = _outil().python_hors_venv()
    assert Path(trouve).parent.resolve() == systeme.resolve()


def test_installer_sans_autre_python_ne_rend_rien(tmp_path, monkeypatch):
    venv = tmp_path / "venv"
    (venv / "bin").mkdir(parents=True)
    monkeypatch.setattr(sys, "prefix", str(venv))
    monkeypatch.setenv("PATH", str(venv / "bin"))
    assert _outil().python_hors_venv() == ""
