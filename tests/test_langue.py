"""Langue de l'interface (jobhunter.app.langue) et catalogue anglais."""

import importlib
import json
import pathlib
import re

import pytest

from jobhunter.app import langue
from jobhunter.app.textes_en import EN

APP = pathlib.Path(langue.__file__).parent


@pytest.fixture
def racine(tmp_path, monkeypatch):
    (tmp_path / "Scripts").mkdir()
    (tmp_path / "profil").mkdir()
    monkeypatch.setenv("JOBHUNTER_RACINE", str(tmp_path))
    monkeypatch.delenv("JOBHUNTER_LANGUE", raising=False)
    return tmp_path


def test_francais_par_defaut(racine):
    assert langue.lire() == "fr"


def test_choisir_puis_lire(racine):
    langue.choisir("en")
    assert json.loads((racine / "Scripts" / "_interface.json").read_text()) == {"langue": "en"}
    assert langue.lire() == "en"
    with pytest.raises(ValueError):
        langue.choisir("de")


def test_variable_d_environnement(racine, monkeypatch):
    monkeypatch.setenv("JOBHUNTER_LANGUE", "EN")
    assert langue.lire() == "en"


def test_fichier_illisible(racine):
    (racine / "Scripts" / "_interface.json").write_text("{pas du json", encoding="utf-8")
    assert langue.lire() == "fr"


def test_t(monkeypatch):
    monkeypatch.setattr(langue, "LANGUE", "fr")
    assert langue.t("Mes CV") == "Mes CV"
    monkeypatch.setattr(langue, "LANGUE", "en")
    assert langue.t("Mes CV") == "My CVs"
    assert langue.t("texte absent du catalogue") == "texte absent du catalogue"
    assert langue.t(3) == 3


def test_navigation_et_panneaux_traduits():
    for fr in (
        "Offres",
        "Mes CV",
        "Entreprises",
        "Sites d'offres",
        "Statistiques",
        "Accès",
        "Actualiser les offres",
        "Entreprises suivies",
        "Accès aux sources",
        "Langue : English",
    ):
        assert fr in EN, fr


def test_chaque_cle_courte_existe_dans_l_app():
    """Une clé du catalogue que l'app n'affiche plus est une traduction morte.

    Les textes longs, écrits en plusieurs morceaux dans le code, ne se vérifient pas ici.
    """
    source = "\n".join(
        p.read_text(encoding="utf-8") for p in APP.glob("*.py") if p.name != "textes_en.py"
    )
    mortes = [k for k in EN if len(k) < 60 and f'"{k}' not in source and f"'{k}" not in source]
    assert mortes == []


def test_catalogue_sans_doublon_de_cle():
    texte = (APP / "textes_en.py").read_text(encoding="utf-8")
    cles = re.findall(r'^    "((?:[^"\\]|\\.)*)": ', texte, re.M)
    assert len(cles) == len(set(cles))


def test_theme_traduit(monkeypatch):
    monkeypatch.setattr(langue, "LANGUE", "en")
    theme = importlib.import_module("jobhunter.app.theme")
    vu = {}
    monkeypatch.setattr(theme.ctk, "CTkLabel", lambda parent, **kw: vu.setdefault("kw", kw))
    theme.CL(None, text="Mes CV")
    assert vu["kw"]["text"] == "My CVs"


def test_journal(monkeypatch):
    monkeypatch.setattr(langue, "LANGUE", "fr")
    assert langue.journal("Rien à annuler.\n") == "Rien à annuler.\n"
    monkeypatch.setattr(langue, "LANGUE", "en")
    assert langue.journal("Rien à annuler.\n") == "Nothing to undo.\n"
    assert langue.journal("↶ annulé (3 offre(s)).\n") == "↶ undone (3 offer(s)).\n"
    assert (
        langue.journal("x\n   Réessaie dans un instant — il se termine tout seul.\n")
        == "x\n   Try again in a moment — it finishes on its own.\n"
    )
    assert (
        langue.journal("＋ flux Ashby alan — lu par API dès la prochaine collecte (Alan)\n")
        == "＋ Ashby feed alan — read by API from the next collection (Alan)\n"
    )
    # La sortie d'un programme lancé reste telle quelle.
    assert langue.journal("Scan : 6 offres uniques\n") == "Scan : 6 offres uniques\n"


def test_journal_modeles_coherents():
    """Même jeu de `{x}` des deux côtés, et chaque modèle vit encore dans l'app."""
    from jobhunter.app.textes_en import JOURNAL_EN

    source = "\n".join(
        p.read_text(encoding="utf-8") for p in APP.glob("*.py") if p.name != "textes_en.py"
    )
    trous = re.compile(r"\{(\w+)\}")
    morts = []
    for fr, en in JOURNAL_EN.items():
        assert sorted(trous.findall(fr)) == sorted(trous.findall(en)), fr
        # Le début du plus long morceau fixe doit apparaître dans le code de l'app (le
        # reste peut y être coupé en plusieurs chaînes).
        fixe = re.sub(r"^\W+", "", max(trous.split(fr)[::2], key=len))[:18]
        if fixe not in source:
            morts.append(fr)
    assert morts == []
