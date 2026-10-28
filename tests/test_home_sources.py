"""The sources follow the profile's home country (`pays`): which ones run, where they search.

Measured on 2026-10-28 with a fictitious nurse's profile in Columbus, Ohio: the
collection queried France Travail, the V.I.E and Welcome to the Jungle, LinkedIn and
Jooble in France, and Adzuna in France and seven European countries.
"""

import json

import pytest
from conftest import Reponse

from jobhunter import lazy
from jobhunter.scoring import zones
from jobhunter.sources import aggregators as A
from jobhunter.sources import common as C
from jobhunter.sources import countries as P
from jobhunter.sources import keywords
from jobhunter.sources import linkedin as L


@pytest.fixture
def maison():
    """The home country, as a profile's `pays` would give it; forgotten afterwards."""

    def poser(pays):
        zones.PAYS_MAISON = pays

    yield poser
    vars(zones).pop("PAYS_MAISON", None)
    lazy.oublier()


def test_sources_d_un_profil_en_france(maison, monkeypatch):
    maison("fr")
    monkeypatch.setattr(P, "parle", lambda l: l in ("fr", "de"))
    assert P.source_du_pays("francetravail") and P.source_du_pays("vie")
    assert P.source_du_pays("eures") and P.source_du_pays("arbeitsagentur")
    assert not P.source_du_pays("usajobs")
    assert P.source_du_pays("linkedin") and P.source_du_pays("adzuna")


def test_sources_d_un_profil_dans_l_ohio(maison, monkeypatch):
    maison("us")
    monkeypatch.setattr(P, "parle", lambda l: l in ("en", "es"))
    for nom in ("francetravail", "vie", "wtj", "makesense", "eures", "arbeitsagentur"):
        assert not P.source_du_pays(nom), nom
    assert P.source_du_pays("usajobs") and P.source_du_pays("freehire")
    assert P.nom() == "United States"


def test_linkedin_cherche_le_pays_puis_le_monde(maison):
    maison("us")
    assert L.lieux_par_defaut() == {"United States": 3, "Worldwide": 12}
    maison("fr")
    assert L.lieux_par_defaut() == L.LIEUX_MONDE  # unchanged in France


def test_adzuna_le_pays_et_les_mots_du_profil(maison, monkeypatch):
    monkeypatch.setattr(keywords, "du_profil", lambda n: ["registered nurse", "rn"][:n])
    monkeypatch.setattr(keywords, "_sur_mesure", lambda s: [])
    monkeypatch.setattr(C, "SOURCES_CFG", C.SOURCES_CFG.parent / "absent.json")
    maison("us")
    assert A._adzuna_requetes() == [("us", "registered nurse"), ("us", "rn")]
    maison("fr")
    req = A._adzuna_requetes()
    assert req[:2] == [("fr", "registered nurse"), ("fr", "rn")]
    assert {p for p, _ in req[2:]} == set(A.ADZUNA_PAYS)  # abroad, as before


def test_hors_de_france_seulement_son_pays(maison, monkeypatch):
    monkeypatch.setattr(C, "MONDE", False)
    maison("us")
    assert C.en_france("Columbus, OH") and C.en_france("")
    assert not C.en_france("Paris, France")
    maison("fr")
    assert C.en_france("Paris") and not C.en_france("Reston, VA")


def test_usajobs(tmp_path, monkeypatch):
    cle = tmp_path / "usajobs.json"
    cle.write_text(json.dumps({"email": "jordan@example.com", "key": "K"}), encoding="utf-8")
    monkeypatch.setattr(A, "USAJOBS_CFG", cle)
    monkeypatch.setattr(A, "AGREG_PAUSE", 0)
    monkeypatch.setattr(keywords, "mots", lambda s, d, n: ["nurse"])
    vus = []
    item = {
        "MatchedObjectDescriptor": {
            "PositionTitle": "Nurse (Clinical)",
            "PositionURI": "https://www.usajobs.gov/job/1",
            "OrganizationName": "Veterans Health Administration",
            "PositionLocationDisplay": "Columbus, Ohio",
            "PublicationStartDate": "2026-10-20T00:00:00",
            "UserArea": {"Details": {"JobSummary": "Patient care."}},
        }
    }

    def get(_m, url, **kw):
        vus.append(kw)
        return Reponse({"SearchResult": {"SearchResultItems": [item]}})

    monkeypatch.setattr(C, "_get_borne", get)
    monkeypatch.setattr(A, "title_ok", lambda t: True)
    offres = A.scan_usajobs()
    assert [o["url"] for o in offres] == ["https://www.usajobs.gov/job/1"]
    assert offres[0]["entreprise"] == "Veterans Health Administration"
    assert vus[0]["headers"]["User-Agent"] == "jordan@example.com"  # the API's rule
    assert vus[0]["headers"]["Authorization-Key"] == "K"
    assert vus[0]["params"]["Keyword"] == "nurse"


def test_usajobs_sans_cle(tmp_path, monkeypatch):
    monkeypatch.setattr(A, "USAJOBS_CFG", tmp_path / "absent.json")
    assert A.scan_usajobs() == []
