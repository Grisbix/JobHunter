"""La collecte chaque matin depuis l'application (jobhunter.planification), sans schtasks réel."""

import subprocess

import pytest

from jobhunter import planification as plan


@pytest.fixture
def schtasks(monkeypatch):
    appels = []

    def faux(*args, code=0):
        appels.append(list(args))
        return subprocess.CompletedProcess(["schtasks", *args], code, "", "")

    monkeypatch.setattr(plan, "disponible", lambda: True)
    monkeypatch.setattr(plan, "_schtasks", faux)
    return appels


def test_application_installee_lance_l_executable(monkeypatch):
    monkeypatch.setattr(plan._gele, "est_gele", lambda: True)
    monkeypatch.setattr(plan._gele, "interpreteur", lambda: r"C:\JH\jobhunter-cli.exe")
    assert plan.commande() == r'"C:\JH\jobhunter-cli.exe" pipeline'


def test_code_source_lance_jobhunter_pyw(monkeypatch, tmp_path):
    (tmp_path / "JobHunter.pyw").write_text("", encoding="utf-8")
    monkeypatch.setattr(plan._gele, "est_gele", lambda: False)
    monkeypatch.setattr(plan._racine, "racine", lambda: tmp_path)
    monkeypatch.setattr(plan._gele, "interpreteur", lambda: r"C:\Python\python.exe")
    assert plan.commande() == f'"C:\\Python\\python.exe" "{tmp_path / "JobHunter.pyw"}" pipeline'


def test_creer_tache_du_meme_nom_que_planifier_bat(schtasks, monkeypatch):
    monkeypatch.setattr(plan, "commande", lambda: '"jh.exe" pipeline')
    ok, msg = plan.creer("07:30")
    assert ok and "07:30" in msg
    a = schtasks[0]
    assert a[:2] == ["/Create", "/F"]
    assert a[a.index("/TN") + 1] == "JobHunter - collecte quotidienne"
    assert a[a.index("/ST") + 1] == "07:30"
    assert a[a.index("/TR") + 1] == '"jh.exe" pipeline'
    bat = (plan.Path(__file__).parent.parent / "planifier.bat").read_text(encoding="utf-8")
    assert f'set "TACHE={plan.TACHE}"' in bat


@pytest.mark.parametrize("heure", ["8h", "25:00", "08:60", "", "08:00 && calc"])
def test_heure_invalide_rien_cree(schtasks, heure):
    ok, msg = plan.creer(heure)
    assert not ok and "invalide" in msg
    assert schtasks == []


def test_supprimer(schtasks):
    ok, _ = plan.supprimer()
    assert ok and schtasks == [["/Delete", "/TN", plan.TACHE, "/F"]]


def test_hors_windows_rien(monkeypatch):
    monkeypatch.setattr(plan, "disponible", lambda: False)
    assert plan.creer("08:00")[0] is False
    assert plan.planifiee() is False
