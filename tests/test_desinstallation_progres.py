"""The window that shows the uninstall (or the erasing) once the application is closed.

The user, 2026-11-06: « ce serait bien d'avoir un message de désinstallation, une barre
de pourcentage ». The window used to vanish and nothing said what happened after.
"""

import os
import re
import subprocess
import sys

import pytest

from jobhunter.web import api, i18n
from jobhunter.web.texts import TEXTES

_TEXTES_CORBEILLE = dict(
    TITRE="Effacement des données",
    DONNEES="Données envoyées à la Corbeille…",
    FINI="Données à la Corbeille : restaurables tant qu'elle n'est pas vidée.",
    ECHEC="L'effacement a échoué :",
)


def _utilises(script: str) -> set[str]:
    return set(re.findall(r"\$env:(JH_T_[A-Z]+)", script))


@pytest.mark.parametrize("script", [api._CORBEILLE, api._DESINSTALLER])
def test_une_fenetre_avec_barre_et_pourcentage(script):
    assert "System.Windows.Forms.ProgressBar" in script and '"$($B.Value) %"' in script
    assert script.index("Etape 5") < script.index("Wait-Process")  # shown before waiting


def test_chaque_texte_du_script_est_fourni(installee_desinstaller):
    env = installee_desinstaller
    assert _utilises(api._DESINSTALLER) <= set(env)
    assert all(env[k] for k in _utilises(api._DESINSTALLER))


def test_textes_traduits(monkeypatch):
    monkeypatch.setenv("JOBHUNTER_LANGUE", "en")
    t = api._textes_progres(TITRE="Désinstallation de JobHunter")
    assert t["JH_T_TITRE"] == "Uninstalling JobHunter" and t["JH_T_FERMER"] == "Close"
    monkeypatch.setenv("JOBHUNTER_LANGUE", "fr")
    assert api._textes_progres(TITRE="Désinstallation de JobHunter")["JH_T_TITRE"] == (
        "Désinstallation de JobHunter"
    )


def test_tous_les_textes_ont_leur_traduction():
    for fr in (
        "Fermeture de JobHunter…",
        "Retrait de l'application…",
        "JobHunter est désinstallé.",
        *_TEXTES_CORBEILLE.values(),
        "La désinstallation a échoué :",
    ):
        assert fr in TEXTES or fr in i18n.catalogue("en")["textes"], fr


@pytest.fixture
def installee_desinstaller(monkeypatch, tmp_path):
    from jobhunter import frozen, profiles, scheduling
    from jobhunter.programs import update

    donnees = tmp_path / "Documents" / "JobHunter"
    donnees.mkdir(parents=True)
    monkeypatch.setattr(frozen, "est_gele", lambda: True)
    monkeypatch.setattr(frozen, "famille_msix", lambda: "")
    monkeypatch.setattr(profiles, "principale", lambda: donnees)
    monkeypatch.setattr(api, "_dossier_effacable", lambda: donnees)
    monkeypatch.setattr(update, "file_libre", lambda garder=True: True)
    monkeypatch.setattr(scheduling, "disponible", lambda: False)
    (tmp_path / "unins000.exe").write_bytes(b"")
    monkeypatch.setattr(api.sys, "executable", str(tmp_path / "JobHunter.exe"))
    vu = {}
    monkeypatch.setattr(api.subprocess, "Popen", lambda cmd, **kw: vu.update(kw["env"]))
    a = api.Api.__new__(api.Api)
    a._fenetre = None
    assert a.desinstaller()["ok"]
    assert vu["JH_ICONE"] == str(tmp_path / "JobHunter.exe")
    return vu


_WIN = pytest.mark.skipif(sys.platform != "win32", reason="Windows PowerShell")


@_WIN
@pytest.mark.parametrize("script", [api._CORBEILLE, api._DESINSTALLER])
def test_le_script_se_lit_sans_erreur(script, tmp_path):
    f = tmp_path / "s.ps1"
    f.write_text(script, encoding="utf-8-sig")
    code = (
        "$e = $null; [void][System.Management.Automation.Language.Parser]::ParseFile("
        f"'{f}', [ref]$null, [ref]$e); if ($e) {{ $e | Out-String; exit 1 }}"
    )
    r = subprocess.run(
        ["powershell", "-NoProfile", "-Command", code], capture_output=True, text=True
    )
    assert r.returncode == 0, r.stdout + r.stderr


@_WIN
def test_l_effacement_tourne_sans_fenetre(tmp_path):
    """Without a desktop (here JH_SANS_FENETRE) the steps run all the same."""
    dossier = tmp_path / "JobHunter"
    (dossier / "data").mkdir(parents=True)
    (dossier / "data" / "temoin.txt").write_text("x", encoding="utf-8")
    env = dict(
        os.environ,
        JH_PID="0",
        JH_DOSSIER=str(dossier),
        JH_SANS_FENETRE="1",
        **{f"JH_T_{k}": v for k, v in _TEXTES_CORBEILLE.items()},
    )
    r = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", api._CORBEILLE],
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert r.returncode == 0, r.stderr
    assert not dossier.exists()
