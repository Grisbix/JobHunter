"""Interface languages (jobhunter.app.language) and their catalogues."""

import importlib
import json
import pathlib
import re

import pytest

from jobhunter.app import language as langue
from jobhunter.app import texts_en as texts_en

EN = texts_en.TEXTES
AUTRES = [c for c in langue.LANGUES if c != "fr"]

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
    langue.choisir("de")
    assert langue.lire() == "de"
    with pytest.raises(ValueError):
        langue.choisir("xx")


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
        "Langue / Language…",
    ):
        assert fr in EN, fr


def test_chaque_cle_courte_existe_dans_l_app():
    """A catalogue key the app no longer displays is a dead translation.

    Long texts, written in several pieces in the code, are not checked here.
    """
    # Modules outside app/ whose sentences the app translates (they take `tr`).
    hors_app = [APP.parent / "collect_state.py"]
    source = "\n".join(
        p.read_text(encoding="utf-8")
        for p in [*APP.glob("*.py"), *hors_app]
        if not p.name.startswith("texts_")
    )
    mortes = [k for k in EN if len(k) < 60 and f'"{k}' not in source and f"'{k}" not in source]
    assert mortes == []


@pytest.mark.parametrize("code", AUTRES)
def test_catalogue_sans_doublon_de_cle(code):
    texte = (APP / f"texts_{code}.py").read_text(encoding="utf-8")
    cles = re.findall(r'^    "((?:[^"\\]|\\.)*)": ', texte, re.M)
    assert len(cles) == len(set(cles))


@pytest.mark.parametrize("code", [c for c in AUTRES if c != "en"])
@pytest.mark.parametrize("nom", ["TEXTES", "JOURNAL", "SORTIE"])
def test_chaque_langue_couvre_l_anglais(code, nom):
    """English is the reference list: every language translates all of it, nothing more.

    Same `{x}` holes on both sides: a missing hole raises KeyError at display.
    """
    ref, cat = getattr(texts_en, nom), getattr(langue.module(code), nom)
    assert [k for k in ref if k not in cat] == []
    assert [k for k in cat if k not in ref] == []
    trous = re.compile(r"\{(\w+)\}")
    assert [k for k, v in cat.items() if sorted(trous.findall(k)) != sorted(trous.findall(v))] == []


def test_noms_et_message_de_relance():
    assert langue.noms() == {"fr": "Français", "en": "English", "de": "Deutsch", "es": "Español"}
    assert "JobHunter" in langue.message_relance("de")
    assert langue.message_relance("fr").startswith("Relance")


def test_repli_sur_l_anglais(monkeypatch):
    """A text the language lacks is shown in English, then in French."""
    monkeypatch.setattr(langue, "LANGUE", "de")
    monkeypatch.setitem(texts_en.TEXTES, "Texte de test absent", "Test text")
    langue._CACHE.clear()
    assert langue.t("Mes CV") == "Meine Lebensläufe"
    assert langue.t("Texte de test absent") == "Test text"
    assert langue.t("vraiment absent") == "vraiment absent"
    langue._CACHE.clear()


def test_journal_en_allemand_et_espagnol(monkeypatch):
    monkeypatch.setattr(langue, "LANGUE", "de")
    assert langue.journal("↶ annulé (3 offre(s)).\n") == "↶ rückgängig gemacht (3 Angebot(e)).\n"
    monkeypatch.setattr(langue, "LANGUE", "es")
    assert langue.journal("Rien à annuler.\n") == "Nada que deshacer.\n"


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
    # An unknown line stays as is.
    assert langue.journal("→ [3/9] Amundi|Analyste\n") == "→ [3/9] Amundi|Analyste\n"


def test_sortie_des_programmes(monkeypatch):
    """The reports of the programs launched by the app, as they print them."""
    monkeypatch.setattr(langue, "LANGUE", "en")
    sortie = (
        "\nScan : 412 offres uniques (→ offres_scan.json)\n"
        "  francetravail  rien à prendre      0 ramenées ·    0 nouvelles ·   0 pertinentes"
        " ·    1.2 s\n"
        "Merge : +12 nouvelles, 3 enrichies (desc), 0 liens promus (LinkedIn -> vrai site), "
        "4 hors de France, 1 écartées à la main, 7 déjà rejetées par le tri, 2 pays écartés, "
        "0 bruits purgés — 12431 total\n"
        "   ── 20/150 — 18 ok — 2.4s/offre, reste ~5 min\n"
        "notifié — 3 marquée(s), historique 41\n"
        "non notifié (toast KO) — 3 marquée(s), historique 41\n"
    )
    assert langue.journal(sortie) == (
        "\nScan: 412 unique offers (→ offres_scan.json)\n"
        "  francetravail  rien à prendre      0 fetched ·    0 new ·   0 relevant ·    1.2 s\n"
        "Merge : +12 new, 3 enriched (desc), 0 links promoted (LinkedIn -> real site), "
        "4 outside France, 1 set aside by hand, 7 already rejected by sorting, 2 countries "
        "set aside, 0 noise purged — 12431 total\n"
        "   ── 20/150 — 18 ok — 2.4s/offer, ~5 min left\n"
        "notified — 3 marked, history 41\n"
        "not notified (toast failed) — 3 marked, history 41\n"
    )


def test_sortie_modeles_vivent_dans_le_paquet():
    """Each line of SORTIE is still printed somewhere in the package."""
    SORTIE_EN = texts_en.SORTIE

    source = "\n".join(
        p.read_text(encoding="utf-8")
        for p in APP.parent.rglob("*.py")
        if not p.name.startswith("texts_")
    )
    trous = re.compile(r"\{(\w+)\}")
    morts = []
    for fr, en in SORTIE_EN.items():
        assert sorted(trous.findall(fr)) == sorted(trous.findall(en)), fr
        # The code often splits these lines into several strings: we look for the start of
        # EACH fixed piece, short enough to fit in a single one.
        for morceau in trous.split(fr)[::2]:
            debut = re.sub(r"^\W+", "", morceau)[:8]
            if len(debut) >= 4 and debut not in source:
                morts.append((fr, debut))
    assert morts == []


def test_journal_modeles_coherents():
    """Same set of `{x}` on both sides, and each template still lives in the app."""
    JOURNAL_EN = texts_en.JOURNAL

    source = "\n".join(
        p.read_text(encoding="utf-8") for p in APP.glob("*.py") if not p.name.startswith("texts_")
    )
    trous = re.compile(r"\{(\w+)\}")
    morts = []
    for fr, en in JOURNAL_EN.items():
        assert sorted(trous.findall(fr)) == sorted(trous.findall(en)), fr
        # The start of the longest fixed piece must appear in the app's code (the
        # rest may be split there into several strings).
        fixe = re.sub(r"^\W+", "", max(trous.split(fr)[::2], key=len))[:18]
        if fixe not in source:
            morts.append(fr)
    assert morts == []


def test_choisir_depuis_le_menu(racine, monkeypatch):
    """The menu saves the language and says, in that language, that a restart applies it."""
    import os

    os.environ["JOBHUNTER_SANS_FOND"] = "1"
    from jobhunter.app import window as fenetre

    app = object.__new__(fenetre.App)
    app.root = None
    vus = []
    monkeypatch.setattr(fenetre.messagebox, "showinfo", lambda titre, msg, **k: vus.append(msg))
    monkeypatch.setattr(langue, "LANGUE", "fr")
    app._choisir_langue("es")
    assert langue.lire() == "es"
    assert vus == [langue.message_relance("es")]
    app._choisir_langue("fr")  # the current language: nothing to do
    assert len(vus) == 1
