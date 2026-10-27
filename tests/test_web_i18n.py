"""The web window's translation catalogue (jobhunter.web.i18n, jobhunter.web.texts)."""

import ast
import re
from pathlib import Path

import pytest

from jobhunter.web import i18n
from jobhunter.web.texts import TEXTES

TROU = re.compile(r"\{(\w*)\}")


def test_francais_catalogue_vide():
    assert i18n.catalogue("fr") == {"langue": "fr", "textes": {}, "modeles": [], "fit": []}
    assert i18n.catalogue("xx")["langue"] == "fr"


@pytest.mark.parametrize("code", ["en", "de", "es"])
def test_catalogue_par_langue(code):
    c = i18n.catalogue(code)
    assert c["langue"] == code
    assert c["textes"]["Offres"] == TEXTES["Offres"][i18n.COLONNE[code]]
    assert all("{" not in k for k in c["textes"])
    assert all("{" in fr for fr, _ in c["modeles"])
    assert c["fit"]
    # The desktop's texts are there too (statuses, programs' output).
    assert len(c["textes"]) > len([k for k in TEXTES if "{" not in k])


def test_les_textes_de_la_fenetre_priment_sur_ceux_du_bureau(monkeypatch):
    import jobhunter.locales.en as en

    monkeypatch.setitem(en.TEXTES, "Offres", "Ads")
    assert i18n.catalogue("en")["textes"]["Offres"] == "Offers"


def test_traduction_vide_retombe_sur_l_anglais(monkeypatch):
    import jobhunter.web.texts as texts

    monkeypatch.setitem(texts.TEXTES, "Essai à part", ("Separate test", "", ""))
    assert i18n.catalogue("de")["textes"]["Essai à part"] == "Separate test"


def test_cles_sans_espace_au_bord_ni_doublon():
    assert all(k == k.strip() for k in TEXTES)
    src = Path(i18n.__file__).with_name("texts.py").read_text(encoding="utf-8")
    dico = next(n.value for n in ast.walk(ast.parse(src)) if isinstance(n, ast.AnnAssign))
    assert isinstance(dico, ast.Dict)
    cles = [k.value for k in dico.keys if isinstance(k, ast.Constant)]
    assert len(cles) == len(set(cles))


@pytest.mark.parametrize("fr", [k for k in TEXTES if "{" in k])
def test_modeles_memes_trous(fr):
    attendus = set(TROU.findall(fr))
    for trad in TEXTES[fr]:
        # {s} is French's plural ending: a language may pluralise otherwise.
        assert set(TROU.findall(trad)) in (attendus, attendus - {"s"}), trad


def test_trois_traductions_non_vides():
    assert all(len(t) == 3 and all(t) for t in TEXTES.values())


def test_langue_choisie(monkeypatch):
    from jobhunter.web.api import Api

    monkeypatch.setenv("JOBHUNTER_LANGUE", "de")
    assert i18n.langue() == "de"
    assert Api().textes()["textes"]["Offres"] == "Angebote"
    monkeypatch.setenv("JOBHUNTER_LANGUE", "klingon")
    monkeypatch.setattr("jobhunter.web.api._fichier_reglages", lambda: None)
    assert i18n.langue() == "fr"
