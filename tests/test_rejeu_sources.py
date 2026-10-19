"""The sources reread REAL recorded responses, without network (outils/rejeu.py).

Each recording in tests/reponses/ contains the public response of a source
(cleaned) and the offers it gave on the day it was taken. The replay must
find exactly the same ones: a parser change that loses an offer, adds
one or changes a description is seen here. A site that changes ITS response, on the other hand, shows
at the next collection (`jobhunter rendement` verdicts); we then re-record.
"""

import importlib.util
import json
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("rejeu", RACINE / "outils" / "rejeu.py")
rejeu = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rejeu)

CASSETTES = sorted(rejeu.CASSETTES.glob("*.json"))


def charger(chemin):
    return json.loads(chemin.read_text(encoding="utf-8"))


def test_des_enregistrements_existent():
    assert {c.stem for c in CASSETTES} == set(rejeu.SCENARIOS)


@pytest.mark.parametrize("chemin", CASSETTES, ids=[c.stem for c in CASSETTES])
def test_rejeu_redonne_les_memes_offres(chemin):
    cassette = charger(chemin)
    assert cassette["attendu"], "un enregistrement sans offre ne prouverait rien"
    assert rejeu.empreinte(rejeu.rejouer(cassette)) == cassette["attendu"]


@pytest.mark.parametrize("chemin", CASSETTES, ids=[c.stem for c in CASSETTES])
def test_rien_de_prive_dans_l_enregistrement(chemin):
    """Ni en-tête de requête, ni cookie : seulement code, type, adresse et corps."""
    for e in charger(chemin)["echanges"]:
        assert set(e) == {"cle", "statut", "type", "url", "corps"}
        assert "set-cookie" not in e["type"].lower()


def test_echange_manquant_fait_echouer():
    cassette = charger(rejeu.CASSETTES / "linkedin.json")
    cassette["echanges"] = []
    with pytest.raises(rejeu.EchangeManquant):
        rejeu.rejouer(cassette)


def test_parseur_casse_se_voit(monkeypatch):
    """Si le parseur perd un champ, le rejeu le dit : le test n'est pas décoratif."""
    from jobhunter.sources import fir

    cassette = charger(rejeu.CASSETTES / "fir.json")
    vrai_mk = fir._mk
    monkeypatch.setattr(
        fir, "_mk", lambda titre, url, *a, **k: vrai_mk(titre.upper(), url, *a, **k)
    )
    assert rejeu.empreinte(rejeu.rejouer(cassette)) != cassette["attendu"]
