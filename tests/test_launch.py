"""jobhunter.launch: the web window first, the desktop one only when it cannot open."""

import sys
import types

import pytest

from jobhunter import launch


@pytest.fixture
def ouvertures(monkeypatch):
    """Records which window opens, without opening any."""
    vu = []
    monkeypatch.setattr("jobhunter.profiles.appliquer", lambda: None)
    monkeypatch.setattr("jobhunter.welcome.assurer_profil", lambda: vu.append("profil"))
    bureau = types.ModuleType("jobhunter.app.window")
    bureau.main = lambda: vu.append("bureau")
    monkeypatch.setitem(sys.modules, "jobhunter.app.window", bureau)
    return vu


def _web(monkeypatch, vu, effet):
    def main():
        vu.append("web")
        return effet()

    monkeypatch.setattr("jobhunter.web.__main__.main", main)


def test_la_fenetre_web_s_ouvre(monkeypatch, ouvertures):
    _web(monkeypatch, ouvertures, lambda: 0)
    assert launch.main() == 0
    assert ouvertures == ["profil", "web"]


def test_sans_pywebview_la_fenetre_de_bureau(monkeypatch, ouvertures):
    _web(monkeypatch, ouvertures, lambda: 1)
    assert launch.main() == 0
    assert ouvertures == ["profil", "web", "bureau"]


def test_une_vue_web_en_panne_ouvre_le_bureau(monkeypatch, ouvertures, capsys):
    def panne():
        raise RuntimeError("WebView2 absent")

    _web(monkeypatch, ouvertures, panne)
    assert launch.main() == 0
    assert ouvertures == ["profil", "web", "bureau"]
    assert "WebView2 absent" in capsys.readouterr().err


def test_les_commandes_app_et_bureau():
    from jobhunter import cli

    assert cli.COMMANDES["app"][0] == "jobhunter.launch"
    assert cli.COMMANDES["bureau"][0] == "jobhunter.app"
    assert cli.main(["bureau", "--help"]) == 0


def test_repli_interdit_en_ci(monkeypatch, ouvertures):
    monkeypatch.setenv("JOBHUNTER_EXIGER_WEB", "1")
    _web(monkeypatch, ouvertures, lambda: 1)
    assert launch.main() == 2
    assert "bureau" not in ouvertures
