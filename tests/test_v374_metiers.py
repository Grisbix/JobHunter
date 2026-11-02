"""3.74: trades (one CV and one letter each), the advanced profile form, smooth profile switch.

Synthetic profile and documents only (public repository).
"""

import json
from pathlib import Path

import pytest
from docx import Document

from jobhunter import paths, profile
from jobhunter.web import api, trades

RACINE = Path(__file__).resolve().parent.parent
STATIQUE = RACINE / "src" / "jobhunter" / "web" / "static"
JS = (STATIQUE / "app.js").read_text(encoding="utf-8")
CSS = (STATIQUE / "style.css").read_text(encoding="utf-8")

PROFIL = {
    "identite": {"prenom": "Camille", "nom": "Exemple"},
    "domaines": [
        {
            "cle": "Data",
            "libelle": "Data",
            "mots_titre": ["data"],
            "cv": "CV_data.docx",
            "cv_en": "",
            "parcours_fr": "Parcours data.",
            "parcours_en": "Data background.",
            "accroche_fr": "analyste data",
            "accroche_en": "data analyst",
        },
        {"cle": "General", "libelle": "Autre", "mots_titre": [], "cv": "CV_data.docx"},
    ],
    "scoring": {"cible": 5, "strict": True},
}


@pytest.fixture
def a(monkeypatch, tmp_path):
    f = tmp_path / "profile.json"
    f.write_text(json.dumps(PROFIL), encoding="utf-8")
    monkeypatch.setattr(profile, "FICHIER", f)
    monkeypatch.setattr(profile, "recharger", lambda *x: None)
    monkeypatch.setattr(paths, "CV_MODELES", tmp_path / "Templates")
    monkeypatch.setattr(trades, "_dossier_lettres_metiers", lambda: tmp_path / "Base" / "Domaines")
    x = api.Api()
    return x


def _doc(tmp_path, nom, *paragraphes):
    d = Document()
    for p in paragraphes:
        d.add_paragraph(p)
    f = tmp_path / nom
    d.save(str(f))
    return f


def _profil(a):
    return json.loads(Path(profile.FICHIER).read_text(encoding="utf-8"))


def test_ajouter_un_metier(a, tmp_path, monkeypatch):
    cv = _doc(tmp_path, "CV_compta.docx", "Camille Exemple")
    monkeypatch.setattr(a, "_choisir", lambda quoi: cv)
    r = a.ajouter_metier("Contrôle de gestion", "contrôleur de gestion, FP&A")
    assert r["ok"] and r["cle"] == "Controle_de_gestion"
    doms = _profil(a)["domaines"]
    assert [d["cle"] for d in doms] == ["Data", "Controle_de_gestion", "General"]
    neuf = doms[1]
    assert neuf["mots_titre"] == ["contrôleur de gestion", "fp&a"]
    assert neuf["cv"] == "CV_compta.docx" and (tmp_path / "Templates" / "CV_compta.docx").exists()
    assert neuf["parcours_fr"] == "Parcours data."  # never a letter from nothing
    # a second one with the same name and file: numbered, nothing overwritten
    r2 = a.ajouter_metier("Contrôle de gestion", "audit")
    assert r2["cle"] == "Controle_de_gestion_2" and r2["cv"] == "CV_compta_2.docx"


def test_ajouter_refuse_sans_mots(a, monkeypatch):
    monkeypatch.setattr(a, "_choisir", lambda quoi: (_ for _ in ()).throw(AssertionError))
    assert not a.ajouter_metier("X", " , ")["ok"]


def test_annule(a, monkeypatch):
    monkeypatch.setattr(a, "_choisir", lambda quoi: None)
    assert a.cv_metier("Data") == {"ok": False, "annule": True}
    assert a.ajouter_metier("X", "x") == {"ok": False, "annule": True}


def test_cv_et_lettre_d_un_metier(a, tmp_path, monkeypatch):
    cv = _doc(tmp_path, "nouveau.docx", "x")
    monkeypatch.setattr(a, "_choisir", lambda quoi: cv)
    assert a.cv_metier("Data")["ok"]
    assert _profil(a)["domaines"][0]["cv"] == "nouveau.docx"
    assert _profil(a)["domaines"][1]["cv"] == "CV_data.docx"  # the other keeps its own
    lettre = _doc(tmp_path, "lettre.docx", "Madame, Monsieur,", "Mon parcours.", "Cordialement")
    monkeypatch.setattr(a, "_choisir", lambda quoi: lettre)
    monkeypatch.setattr(
        "jobhunter.own_letter.parcours_de_lettre",
        lambda f: "Diplômé d'un master, j'ai analysé des données.",
    )
    r = a.lettre_metier("Data")
    assert r["ok"] and r["parcours"]
    d = _profil(a)["domaines"][0]
    assert d["lettre"] == "lettre.docx" and d["parcours_fr"].startswith("Diplômé")
    m = a.metiers()["metiers"][0]
    assert m["lettre_chemin"] and m["cv_chemin"]


def test_inconnu_et_dernier(a):
    assert not a.retirer_metier("Rien")["ok"]
    assert not a.retirer_metier("Data")["ok"]  # at least one trade stays
    assert not a.renommer_metier("Data", "Data", "")["ok"]
    assert a.renommer_metier("General", "Le reste", "")["ok"]


# --- advanced profile --------------------------------------------------------------------


def test_meme_forme():
    assert trades.meme_forme(PROFIL, json.loads(json.dumps(PROFIL))) == ""
    p = json.loads(json.dumps(PROFIL))
    p["scoring"]["cible"] = 4.5
    p["domaines"][0]["mots_titre"] = ["data", "bi"]
    assert trades.meme_forme(PROFIL, p) == ""
    p["scoring"]["cible"] = "cinq"
    assert "nombre" in trades.meme_forme(PROFIL, p)
    p = json.loads(json.dumps(PROFIL))
    p["nouvelle"] = 1
    assert "rubriques" in trades.meme_forme(PROFIL, p)
    p = json.loads(json.dumps(PROFIL))
    p["scoring"]["strict"] = 1
    assert "oui ou non" in trades.meme_forme(PROFIL, p)


def test_enregistrer_profil_avance(a):
    p = a.profil_avance()["profil"]
    p["scoring"]["cible"] = 6
    assert a.enregistrer_profil_avance(p)["ok"]
    assert _profil(a)["scoring"]["cible"] == 6
    p["scoring"] = []
    r = a.enregistrer_profil_avance(p)
    assert not r["ok"] and "Rien n'est écrit" in r["erreur"]
    assert _profil(a)["scoring"]["cible"] == 6


# --- interface and switch -------------------------------------------------------------------


def test_interface():
    assert "async function carteMetiers()" in JS and "async function profilAvance()" in JS
    assert 'bouton("Profil avancé", "doc", profilAvance)' in JS
    assert 'carte("Domaines visés"' not in JS
    assert "return [lettre];" in JS
    assert "body.relais::after" in CSS


def test_tache_domaines():
    assert api.TACHES["domaines"][1] == ["jobhunter.programs.reclassify_domains"]
    import importlib

    assert importlib.import_module("jobhunter.programs.reclassify_domains").main


def test_relais_ferme_quand_la_nouvelle_est_prete(monkeypatch, tmp_path):
    import threading

    lances = []
    monkeypatch.setattr(api.subprocess, "Popen", lambda cmd, **k: lances.append(k["env"]))
    monkeypatch.setattr("jobhunter.profiles.principale", lambda: tmp_path)
    monkeypatch.setattr("tempfile.gettempdir", lambda: str(tmp_path))
    ferme = threading.Event()

    class Fenetre:
        def evaluate_js(self, js):
            self.js = js

        def destroy(self):
            ferme.set()

    a = api.Api()
    a._fenetre = Fenetre()
    a._plein = lambda: False
    a._relancer()
    env = lances[0]
    assert env["JH_PLEIN"] == "0" and "relais" in a._fenetre.js
    assert not ferme.wait(0.5)  # still open: the new one is not drawn yet
    Path(env["JH_RELAIS"]).write_text("pret")
    assert ferme.wait(3)
