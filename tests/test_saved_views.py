"""Saved views of the offer table and remembered columns (app/views.py), and the viewer's
"open in Word" check (app/detail.py) — without a window."""

import json

import pytest

from jobhunter.app import views as V
from jobhunter.app import window as ui
from jobhunter.app.common import COLS, SEARCH_HINT
from jobhunter.app.detail import ouvert_dans_word

CONNUES = [c[0] for c in COLS]


@pytest.fixture
def fichier(tmp_path, monkeypatch):
    f = tmp_path / V.FICHIER
    monkeypatch.setattr(V, "_chemin", lambda chemin=None: chemin or f)
    return f


# ── capture and restore ─────────────────────────────────────────────────────


def test_aller_retour():
    colsel = {"pays": ("keep", {"France", "Suisse"}), "contrat": ("excl", {"Stage"}), "fit": None}
    vue = V.capturer(colsel, ("fit", False), ["esg"], ["_chk", "poste", "fit"])
    vue = json.loads(json.dumps(vue))  # what the file gives back
    r = V.restaurer(vue, CONNUES)
    assert r["colsel"] == {"pays": ("keep", {"France", "Suisse"}), "contrat": ("excl", {"Stage"})}
    assert r["tri"] == ("fit", False)
    assert r["recherche"] == ["esg"]
    assert r["colonnes"] == ["_chk", "poste", "fit"]


def test_colonne_disparue_ignoree():
    """A view saved by an older version still opens, with what still makes sense."""
    vue = {
        "filtres": {"ancienne": ["keep", ["x"]], "pays": ["bizarre", ["y"]]},
        "tri": ["ancienne", True],
        "colonnes": ["ancienne"],
    }
    r = V.restaurer(vue, CONNUES)
    assert r["colsel"] == {}
    assert r["tri"] == (None, False)
    assert r["colonnes"] is None


def test_colonnes_dans_l_ordre_du_tableau_case_en_tete():
    assert V.colonnes_valides(["fit", "poste", "_chk", "?"], CONNUES) == ["_chk", "poste", "fit"]
    assert V.colonnes_valides("poste", CONNUES) is None


# ── the file ────────────────────────────────────────────────────────────────


def test_enregistrer_lire_supprimer(fichier):
    assert V.lire() == {"vues": {}, "colonnes": []}
    assert V.enregistrer("  ESG Paris ", {"tri": ["fit", False]})
    assert not V.enregistrer("   ", {})
    assert V.memoriser_colonnes(["_chk", "poste"])
    d = V.lire()
    assert d["vues"] == {"ESG Paris": {"tri": ["fit", False]}}
    assert d["colonnes"] == ["_chk", "poste"]  # a view and the columns live side by side
    assert V.supprimer("ESG Paris") and not V.supprimer("ESG Paris")
    assert V.lire()["colonnes"] == ["_chk", "poste"]


@pytest.mark.parametrize("contenu", ["{pas du json", "[1, 2]", '{"vues": 3, "colonnes": "x"}'])
def test_fichier_abime_vide(fichier, contenu):
    fichier.write_text(contenu, encoding="utf-8")
    assert V.lire() == {"vues": {}, "colonnes": []}
    assert V.enregistrer("a", {})  # and it can be written again
    assert list(V.lire()["vues"]) == ["a"]


# ── applied to the table ────────────────────────────────────────────────────


class Arbre:
    def __init__(self, cols):
        self.cols = tuple(cols)

    def cget(self, k):
        assert k == "displaycolumns"
        return self.cols

    def configure(self, displaycolumns):
        self.cols = tuple(displaycolumns)


class Saisie:
    def __init__(self, texte=""):
        self.texte = texte

    def get(self):
        return self.texte

    def delete(self, a, b):
        self.texte = ""

    def insert(self, i, s):
        self.texte = s


@pytest.fixture
def app(fichier):
    a = object.__new__(ui.App)
    a._visible_cols = ("_chk", "entreprise", "poste", "fit")
    a.tree = Arbre(a._visible_cols)
    a.colsel = {"zone": ("keep", {"1 · prioritaire"})}
    a._sort = (None, False)
    a._search_termes_actifs = []
    a.e_search = Saisie(SEARCH_HINT)
    a.redessins = 0
    a.root = type("Racine", (), {"after_idle": lambda self, f: None})()
    a.refresh_table = lambda: setattr(a, "redessins", a.redessins + 1)
    return a


def test_appliquer_une_vue(app):
    vue = V.capturer({"pays": ("keep", {"France"})}, ("fit", False), ["esg", "paris"], ["poste"])
    V.appliquer(app, vue)
    assert app.colsel == {"pays": ("keep", {"France"})}  # the old filter is gone
    assert app._sort == ("fit", False)
    assert app.e_search.get() == "esg paris" and app._search_termes_actifs == ["esg", "paris"]
    assert app.tree.cols == ("_chk", "poste")
    assert app._urlcol is None
    assert app.redessins == 1
    assert V.lire()["colonnes"] == ["_chk", "poste"]  # remembered for the next session


def test_vue_par_defaut(app):
    app._search_termes_actifs = ["x"]
    V.appliquer(app, {"colonnes": list(app._visible_cols)})
    assert app.colsel == {} and app._sort == (None, False)
    assert app.e_search.get() == SEARCH_HINT and app._search_termes_actifs == []
    assert app.tree.cols == app._visible_cols


def test_colonne_lien_reperee(app):
    app._montrer_colonnes(["poste", "_url"])
    assert app.tree.cols == ("_chk", "poste", "_url")
    assert app._urlcol == "#3"
    assert V.lire()["colonnes"] == []  # not remembered unless asked


def test_colonnes_inutilisables_vue_compacte(app):
    app._montrer_colonnes(["?"])
    assert app.tree.cols == app._visible_cols


# ── viewer: a document Word holds open ──────────────────────────────────────


@pytest.mark.parametrize(
    ("nom", "verrou"),
    [
        ("Lettre_Exemple_Analyste.docx", "~$ttre_Exemple_Analyste.docx"),  # long name
        ("CV1234.docx", "~$CV1234.docx"),  # short name: kept whole
        ("CV12345.docx", "~$V12345.docx"),
    ],
)
def test_ouvert_dans_word(tmp_path, nom, verrou):
    doc = tmp_path / nom
    doc.write_bytes(b"")
    assert not ouvert_dans_word(doc)
    (tmp_path / verrou).write_bytes(b"")
    assert ouvert_dans_word(doc)
