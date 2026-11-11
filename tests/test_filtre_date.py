"""Offers screen: a filter on the offer's age (the user, 2026-11-04: « il n'y a pas de
filtre sur la date de l'offre »). Publication date, else the day it was seen, else the
scan; an offer with no date is left out while the filter is on."""

from datetime import date, timedelta

import js_app

from jobhunter.web import api
from jobhunter.web.texts import TEXTES

JS = js_app.source()


def _jour(n):
    return (date.today() - timedelta(days=n)).isoformat()


OFFRES = [
    {"entreprise": "A", "poste": "hier", "statut": "scan 2026-01-01", "date_publication": _jour(1)},
    {
        "entreprise": "B",
        "poste": "il y a 10 j",
        "statut": "scan 2026-01-01",
        "date_publication": _jour(10),
    },
    {"entreprise": "C", "poste": "vue il y a 2 j", "statut": "scan 2026-01-01", "vu_le": _jour(2)},
    {"entreprise": "D", "poste": "sans date", "statut": "à voir"},
]


def _postes(jours):
    r = api.offres(OFFRES, {}, statut="toutes", tri="entreprise", jours=jours)
    return [ligne["poste"] for ligne in r["lignes"]]


def test_sans_filtre_tout_passe():
    assert _postes(0) == ["hier", "il y a 10 j", "vue il y a 2 j", "sans date"]


def test_le_filtre_garde_les_offres_recentes():
    assert _postes(3) == ["hier", "vue il y a 2 j"]
    assert _postes(14) == ["hier", "il y a 10 j", "vue il y a 2 j"]
    assert _postes(1) == ["hier"]


def test_l_ecran_a_le_filtre_traduit():
    assert 'changer("jours"' in JS
    for _, libelle in [(0, "Toutes les dates"), (1, "Dernières 24 h"), (30, "30 derniers jours")]:
        assert libelle in TEXTES
