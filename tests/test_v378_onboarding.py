"""3.78: the welcome lives in the web window (jobhunter.web.onboarding), no Tk any more."""

from pathlib import Path

from jobhunter import welcome
from jobhunter.programs import first_launch
from jobhunter.web.onboarding import BienvenueApi


class _Api(BienvenueApi):
    def __init__(self):
        self.relances = []

    def _relancer(self, dans=None, cv=""):
        self.relances.append((dans, cv))


def test_bienvenue_rend_le_message_et_le_cv_une_seule_fois(monkeypatch):
    monkeypatch.setattr(welcome, "a_un_profil", lambda: False)
    monkeypatch.setattr(BienvenueApi, "_secondaire", staticmethod(lambda: ""))
    monkeypatch.setenv("JH_MIGRATION", "Dossier renommé.")
    monkeypatch.setenv("JH_CV", "C:/cv.pdf")
    b = _Api().bienvenue()
    assert b["message"] == "Dossier renommé." and b["cv"] == "C:/cv.pdf"
    assert b["reprise"] == []  # a CV already chosen: no take-back offered
    b = _Api().bienvenue()
    assert b["message"] == "" and b["cv"] == ""


def test_un_profil_sans_metier_n_est_pas_cree(monkeypatch):
    vu = []
    monkeypatch.setattr(welcome, "creer_profil", lambda cv, rep: vu.append(rep) or (True, ""))
    api = _Api()
    for metiers in ("", "  ", first_launch.A_COMPLETER):
        r = api.creer_mon_profil("cv.pdf", {"metiers": metiers})
        assert r["ok"] is False and "métier" in r["erreur"]
    r = api.creer_mon_profil("cv.pdf", {"metiers": "Analyste", "annees": "trois"})
    assert r["ok"] is False and "nombre" in r["erreur"]
    assert vu == [] and api.relances == []


def test_un_profil_cree_relance_la_fenetre(monkeypatch):
    monkeypatch.setattr(welcome, "creer_profil", lambda cv, rep: (True, ""))
    monkeypatch.setattr(BienvenueApi, "_secondaire", staticmethod(lambda: ""))
    api = _Api()
    assert api.creer_mon_profil("cv.pdf", {"metiers": "Analyste", "annees": "3"}) == {"ok": True}
    assert api.relances == [(None, "")]


def test_un_echec_montre_la_fin_de_la_sortie(monkeypatch):
    sortie = "\n".join(f"ligne {i}" for i in range(30))
    monkeypatch.setattr(welcome, "creer_profil", lambda cv, rep: (False, sortie))
    api = _Api()
    r = api.creer_mon_profil("cv.pdf", {"metiers": "Analyste"})
    assert r["ok"] is False and "ligne 29" in r["erreur"] and "ligne 5\n" not in r["erreur"]
    assert api.relances == []


def test_plus_tard_archive_un_nouveau_profil_vide(monkeypatch):
    from jobhunter import profiles

    archives = []
    monkeypatch.setattr(BienvenueApi, "_secondaire", staticmethod(lambda: "camille"))
    monkeypatch.setattr(profiles, "archiver", lambda slug: archives.append(slug))
    api = _Api()
    assert api.plus_tard() == {"ok": True}
    assert archives == ["camille"] and api.relances == [(None, "")]


def test_plus_tard_dans_le_dossier_principal_ferme_la_fenetre(monkeypatch):
    class Fenetre:
        ferme = False

        def destroy(self):
            self.ferme = True

    monkeypatch.setattr(BienvenueApi, "_secondaire", staticmethod(lambda: ""))
    api = _Api()
    api._fenetre = Fenetre()
    api.plus_tard()
    assert api._fenetre.ferme and api.relances == []


def test_un_fichier_qui_n_est_pas_un_cv_est_refuse():
    r = _Api().lire_cv(str(Path("notes.txt")))
    assert r["ok"] is False and "PDF ou Word" in r["erreur"]


def test_plus_de_tkinter_dans_l_accueil():
    import re

    src = Path(welcome.__file__).parent
    for f in (src / "welcome.py", src / "web" / "onboarding.py"):
        code = f.read_text(encoding="utf-8")
        assert not re.search(r"^\s*(from|import)\s+\w*tkinter", code, re.M), f.name
    assert not (src / "welcome_tour.py").exists()
