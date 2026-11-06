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


# ── 3.85: a test release first, then the same tag becomes the release ──────


def _github(m, monkeypatch, *, release=None, tag_commit="abc", branche_commit="abc"):
    import json
    import subprocess

    faits = []

    def run(*cmd, capture=False):
        faits.append(cmd)
        if cmd[:3] == ("gh", "pr", "view"):
            return json.dumps({"headRefName": "v3.85.0", "state": "OPEN"})
        if cmd[:3] == ("gh", "pr", "checks"):
            return json.dumps([{"name": "tests", "state": "SUCCESS"}])
        if cmd[:2] == ("git", "rev-list"):
            return tag_commit
        if cmd[:2] == ("git", "rev-parse"):
            return branche_commit
        return ""

    def vue(cmd, **kw):
        if release is None:
            return subprocess.CompletedProcess(cmd, 1, "", "release not found")
        return subprocess.CompletedProcess(cmd, 0, json.dumps({"isPrerelease": release}), "")

    monkeypatch.setattr(m, "_run", run)
    monkeypatch.setattr(m, "_notes", lambda v: "- notes")
    monkeypatch.setattr(m.subprocess, "run", vue)
    monkeypatch.setattr(m, "_notes_fichier", lambda notes: _Fichier())
    return faits


class _Fichier:
    def unlink(self):
        pass

    def __str__(self):
        return "notes.md"


def test_beta_publie_la_branche_en_pre_release_sans_fusionner(monkeypatch):
    m = _outil()
    faits = _github(m, monkeypatch)
    assert m.beta(200) == 0
    cree = next(c for c in faits if c[:3] == ("gh", "release", "create"))
    assert "--prerelease" in cree and cree[cree.index("--target") + 1] == "v3.85.0"
    assert not any("refs/heads/main" in " ".join(c) for c in faits)  # main untouched


def test_beta_refuse_un_numero_deja_publie(monkeypatch):
    m = _outil()
    _github(m, monkeypatch, release=True)
    import pytest

    with pytest.raises(SystemExit):
        m.beta(200)


def test_publier_promeut_la_version_de_test(monkeypatch):
    m = _outil()
    faits = _github(m, monkeypatch, release=True)
    m.publier(200)
    edit = next(c for c in faits if c[:3] == ("gh", "release", "edit"))
    assert "--prerelease=false" in edit and "--latest" in edit
    assert not any(c[:3] == ("gh", "release", "create") for c in faits)


def test_publier_refuse_si_la_branche_a_change_depuis_le_test(monkeypatch):
    import pytest

    m = _outil()
    faits = _github(m, monkeypatch, release=True, tag_commit="abc", branche_commit="def")
    with pytest.raises(SystemExit, match="a changé"):
        m.publier(200)
    assert not any("refs/heads/main" in " ".join(c) for c in faits)


def test_notes_hors_de_git_pour_un_worktree():
    # 3.84.1: in a worktree .git is a file; publier stopped after pushing main.
    f = _outil()._notes_fichier("- notes")
    try:
        assert f.read_text(encoding="utf-8") == "- notes\n" and ".git" not in f.parts
    finally:
        f.unlink()
