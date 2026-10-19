"""Les clés des API de collecte vont dans le fichier que chaque source lit (cles_api)."""

import json

import pytest

from jobhunter import cles_api
from jobhunter.app import inventaire
from jobhunter.sources.agregateurs import _cle


def test_adzuna_lu_par_la_source_et_options_gardees(tmp_path):
    chemin = tmp_path / "adzuna.json"
    chemin.write_text('{"option": 7}', encoding="utf-8")
    autre = tmp_path / "api_keys.json"
    autre.write_text("inchangé", encoding="utf-8")
    cles_api.enregistrer(tmp_path, "adzuna", {"app_id": " exemple-id ", "app_key": " cle "})
    assert _cle(chemin, "app_id", "app_key") == ("exemple-id", "cle")
    assert json.loads(chemin.read_text(encoding="utf-8"))["option"] == 7
    assert autre.read_text(encoding="utf-8") == "inchangé"


def test_jooble_lu_par_la_source(tmp_path):
    cles_api.enregistrer(tmp_path, "jooble", {"key": "k"})
    assert _cle(tmp_path / "jooble.json", "key") == ("k",)


def test_france_travail_dans_son_fichier(tmp_path, monkeypatch):
    """Avant la 2.12, la saisie allait dans api_keys.json, qu'aucune source ne lit."""
    cles_api.enregistrer(tmp_path, "francetravail", {"client_id": "i", "client_secret": "s"})
    c = json.loads((tmp_path / "francetravail.json").read_text(encoding="utf-8"))
    assert c == {"client_id": "i", "client_secret": "s"}
    assert not (tmp_path / "api_keys.json").exists()


def test_champ_vide_garde_la_valeur(tmp_path):
    cles_api.enregistrer(tmp_path, "adzuna", {"app_id": "id", "app_key": "ancienne"})
    cles_api.enregistrer(tmp_path, "adzuna", {"app_id": "", "app_key": "neuve"})
    assert _cle(tmp_path / "adzuna.json", "app_id", "app_key") == ("id", "neuve")


@pytest.mark.parametrize("contenu", ["{", "[]"])
def test_fichier_illisible_conserve(tmp_path, contenu):
    chemin = tmp_path / "adzuna.json"
    chemin.write_text(contenu, encoding="utf-8")
    with pytest.raises(ValueError):
        cles_api.enregistrer(tmp_path, "adzuna", {"app_id": "id", "app_key": "cle"})
    assert chemin.read_text(encoding="utf-8") == contenu
    assert not cles_api.presente(tmp_path, "adzuna")


@pytest.mark.parametrize("valeurs", [{"app_id": "", "app_key": "cle"}, {"app_id": "id"}])
def test_champs_requis(tmp_path, valeurs):
    with pytest.raises(ValueError):
        cles_api.enregistrer(tmp_path, "adzuna", valeurs)
    assert not (tmp_path / "adzuna.json").exists()


def test_presente(tmp_path):
    assert not cles_api.presente(tmp_path, "jooble")
    (tmp_path / "jooble.json").write_text('{"key": ""}', encoding="utf-8")
    assert not cles_api.presente(tmp_path, "jooble")
    cles_api.enregistrer(tmp_path, "jooble", {"key": "k"})
    assert cles_api.presente(tmp_path, "jooble")


def test_le_panneau_connait_chaque_fichier_de_cle():
    fichiers = {f for _, _, f in inventaire.SOURCES_COLLECTE if f}
    assert fichiers == {c.fichier for c in cles_api.CLES.values()}


def test_set_key_en_ligne_de_commande(tmp_path, monkeypatch):
    from jobhunter.programmes import acces

    monkeypatch.setattr(acces, "HERE", tmp_path)
    monkeypatch.setattr("builtins.input", lambda invite="": "mon-id")
    monkeypatch.setattr(acces.getpass, "getpass", lambda invite="": "mon-secret")
    assert acces.cmd_set_key("francetravail") == 0
    c = json.loads((tmp_path / "francetravail.json").read_text(encoding="utf-8"))
    assert c == {"client_id": "mon-id", "client_secret": "mon-secret"}
    assert acces.cmd_set_key("inconnue") == 1
