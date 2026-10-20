"""Annuaires d'entreprises Lever, Ashby, Greenhouse (sources.annuaire, outils/annuaires.py)."""

import importlib.util
import json
import re

import pytest
from conftest import SRC

from jobhunter.app import inventaire
from jobhunter.sources import annuaire

DOSSIER = SRC / "jobhunter" / "sources" / "annuaires"
_spec = importlib.util.spec_from_file_location(
    "annuaires_outil", SRC.parent / "outils" / "annuaires.py"
)
assert _spec and _spec.loader
outil = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(outil)


def test_trois_annuaires_valides_et_attribues():
    total = 0
    for nom in annuaire.OUTILS:
        entrees = json.loads((DOSSIER / f"{nom}.json").read_text(encoding="utf-8"))
        assert len(entrees) > 500, nom
        assert outil.nettoyer([{"name": n, "token": j} for n, j in entrees]) == entrees
        total += len(entrees)
    assert total == len(annuaire.entrees()) > 3000
    licence = (DOSSIER / "LICENSE-jobsync.txt").read_text(encoding="utf-8")
    assert "MIT License" in licence and outil.COMMIT in licence


def test_chaque_outil_est_un_flux_connu():
    assert set(annuaire.OUTILS) <= set(inventaire.NOMS_OUTILS)


def test_identifiants_surs_pour_une_url():
    rx = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    assert all(rx.match(e.jeton) for e in annuaire.entrees())


def test_nettoyer_ecarte_le_douteux():
    brut = [
        {"name": "Bonne", "token": "bonne"},
        {"name": "Doublon", "token": "BONNE"},
        {"name": "", "token": "vide"},
        {"name": "Piège", "token": "../etc"},
        {"name": "Espace", "token": "a b"},
        "pas un objet",
        {"name": "  Alan   SAS ", "token": "alan"},
    ]
    assert outil.nettoyer(brut) == [["Alan SAS", "alan"], ["Bonne", "bonne"]]
    with pytest.raises(ValueError):
        outil.nettoyer({"name": "x"})


@pytest.fixture
def petit(monkeypatch):
    E = annuaire.Entree
    donnees = (
        E("L'Oréal", "lever", "loreal"),
        E("Alan", "ashby", "alan"),
        E("Alanine Labs", "greenhouse", "alaninelabs"),
        E("Super Alan", "lever", "superalan"),
        E("Catalan Bank", "ashby", "catalanbank"),
        E("Central and Co", "lever", "centralandco"),
    )
    monkeypatch.setattr(annuaire, "entrees", lambda: donnees)


def test_chercher_ordre(petit):
    noms = [e.nom for e in annuaire.chercher("alan")]
    assert noms == ["Alan", "Alanine Labs", "Super Alan", "Catalan Bank"]


def test_pas_a_cheval_sur_deux_mots(petit):
    """ "Central and" contains "alan" once the spaces are removed: not a result."""
    assert "Central and Co" not in [e.nom for e in annuaire.chercher("alan")]


def test_chercher_sans_accents_ni_ponctuation(petit):
    assert [e.jeton for e in annuaire.chercher("loreal")] == ["loreal"]
    assert [e.jeton for e in annuaire.chercher("L’oréal")] == ["loreal"]


def test_chercher_trop_court_et_limite(petit):
    assert annuaire.chercher("a") == []
    assert len(annuaire.chercher("al", limite=2)) == 2


def test_un_nom_reel_se_trouve():
    assert annuaire.chercher("15five")[0].jeton == "15five"


def test_suivre_depuis_l_annuaire_ajoute_le_flux():
    cfg: dict = {}
    msg = inventaire.ajouter_flux(cfg, {"ats_slugs": {}}, ("ashby", "alan"))
    assert cfg["ats_slugs"]["ashby"] == ["alan"]
    assert "Ashby" in msg
    assert "déjà suivi" in inventaire.ajouter_flux(cfg, {"ats_slugs": {}}, ("ashby", "Alan"))
