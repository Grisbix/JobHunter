"""The desktop's workshop windows in the web interface (jobhunter.web.workshop), synthetic data."""

import json

import pytest

from jobhunter import profile, root
from jobhunter.web.api import Api

PROFIL = {
    "scoring": {"axes": {"esg": {"poids": 1.0, "competences": []}, "data": {"poids": 2.0}}},
    "domaines": [{"cv": "CV_test.docx"}],
}


@pytest.fixture
def api(tmp_path, monkeypatch):
    f = tmp_path / "profile.json"
    f.write_text(json.dumps(PROFIL), encoding="utf-8")
    monkeypatch.setattr(profile, "FICHIER", f)
    monkeypatch.setattr(profile, "recharger", lambda *a: None)
    monkeypatch.setattr(profile, "charger", lambda: json.loads(f.read_text(encoding="utf-8")))
    monkeypatch.setattr(root, "scripts", lambda: tmp_path)
    a = Api()
    a._file = lambda: [
        {"entreprise": "PricewaterhouseCoopers", "poste": "Analyste", "fit": 9},
        {"entreprise": "PricewaterhouseCoopers", "poste": "Auditeur", "fit": 5},
    ]
    a._suivi = lambda: {"PricewaterhouseCoopers|Auditeur": {"statut": "postulé"}}
    a._composantes = []  # never the fit_components process in a test
    a.demarrees = []
    a._demarrer = lambda cle, lib, args: a.demarrees.append(args) or {"ok": True}
    return a, f


def test_poids_curseurs_du_profil(api):
    a, _ = api
    cles = [c["cle"] for c in a.poids()["curseurs"]]
    assert cles[:2] == ["axe:esg", "axe:data"]
    assert {"cible", "bonus_junior", "malus_senior"} <= set(cles)


def test_bilan_sans_rien_ecrire(api):
    a, f = api
    avant = f.read_text(encoding="utf-8")
    b = a.bilan_poids({"axe:esg": 3})
    assert b["pret"] and b["change"] and b["essai"]["n"] == 0
    assert len(b["essai"]["repartition"]) == 10
    assert f.read_text(encoding="utf-8") == avant


def test_enregistrer_poids_garde_le_profil_d_avant(api):
    a, f = api
    assert a.enregistrer_poids({"axe:esg": 1.0})["ok"] is False  # unchanged
    r = a.enregistrer_poids({"axe:esg": 3.0})
    assert r["ok"] and (f.parent / r["bak"]).exists()
    assert json.loads(f.read_text(encoding="utf-8"))["scoring"]["axes"]["esg"]["poids"] == 3.0


def test_recettes_apercu_epargne_les_candidatures(api):
    a, _ = api
    texte = "entreprise | PricewaterhouseCoopers | PwC"
    r = a.apercu_recettes(texte)
    assert r["ok"] and r["n"] == 1 and r["ecartes"] == 1
    assert not (root.scripts() / "_recettes.json").exists()  # a preview writes nothing


def test_recettes_invalides_refusees(api):
    a, _ = api
    assert a.apercu_recettes("champ_inconnu | a | b")["ok"] is False


def test_appliquer_recettes_enregistre_puis_lance(api):
    a, _ = api
    r = a.appliquer_recettes("entreprise | PricewaterhouseCoopers | PwC")
    assert r["ok"] and r["tache"]
    assert a.demarrees == [["jobhunter.programs.recipes", "--appliquer"]]
    assert "PwC" in a.recettes()["texte"]


def test_documents_lot_borne(api):
    a, _ = api
    assert a.documents_lot(0)["ok"] is False
    assert a.documents_lot("x")["ok"] is False
    assert a.documents_lot(12)["ok"]
    assert a.demarrees[-1][-2:] == ["--top", "12"]
    assert a.documents_restants() == 1  # fit 9 without documents; fit 5 not counted


def test_cv_de_base_sans_fenetre_ni_choix(api):
    a, _ = api
    assert a.choisir_cv_base()["ok"] is False
    assert a.remplacer_cv_base()["ok"] is False


def test_remplacer_cv_de_base_garde_l_ancien(api, tmp_path, monkeypatch):
    from jobhunter import paths

    a, f = api
    modeles = tmp_path / "Modeles"
    modeles.mkdir()
    (modeles / "CV_test.docx").write_bytes(b"ancien")
    neuf = tmp_path / "nouveau.pdf"
    neuf.write_bytes(b"neuf")
    monkeypatch.setattr(paths, "CV_MODELES", modeles)
    a._cv_choisi = neuf
    r = a.remplacer_cv_base()
    assert r == {"ok": True, "neuf": "CV_test.pdf"}
    assert (modeles / "CV_test.docx.bak").read_bytes() == b"ancien"
    assert json.loads(f.read_text(encoding="utf-8"))["domaines"][0]["cv"] == "CV_test.pdf"


def test_comparer_hors_liste(api, monkeypatch):
    a, _ = api
    monkeypatch.setattr(type(a), "_attente", staticmethod(lambda: []))
    assert a.a_comparer() == []
    assert a.diff_document(0)["ok"] is False
    assert a.choisir_version(3, True)["ok"] is False
