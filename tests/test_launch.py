"""jobhunter.launch: the web window; when it cannot open, says why (no other window, 3.77)."""

import pytest

from jobhunter import launch


@pytest.fixture
def ouvertures(monkeypatch):
    """Records which window opens, without opening any."""
    vu = []
    monkeypatch.setattr("jobhunter.profiles.appliquer", lambda: None)
    monkeypatch.setattr("jobhunter.welcome.assurer_profil", lambda: vu.append("profil"))
    monkeypatch.setattr(launch, "_dire_pourquoi", lambda raison: vu.append(f"message: {raison}"))
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


def test_sans_pywebview_le_dit(monkeypatch, ouvertures):
    _web(monkeypatch, ouvertures, lambda: 1)
    assert launch.main() == 1
    assert ouvertures == ["profil", "web", "message: pywebview n'est pas installé"]


def test_une_vue_web_en_panne_le_dit(monkeypatch, ouvertures):
    def panne():
        raise RuntimeError("WebView2 absent")

    _web(monkeypatch, ouvertures, panne)
    assert launch.main() == 1
    assert ouvertures == ["profil", "web", "message: WebView2 absent"]


def test_plus_de_commande_bureau():
    from jobhunter import cli

    assert cli.COMMANDES["app"][0] == "jobhunter.launch"
    assert "bureau" not in cli.COMMANDES
    assert cli.module_de("bureau") is None


def test_en_ci_la_fenetre_web_est_exigee(monkeypatch, ouvertures):
    monkeypatch.setenv("JOBHUNTER_EXIGER_WEB", "1")
    _web(monkeypatch, ouvertures, lambda: 1)
    assert launch.main() == 2
    assert ouvertures == ["profil", "web"]  # no message box in CI
