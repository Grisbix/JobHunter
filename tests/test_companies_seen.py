"""Every company a collection has seen (storage.companies), on synthetic data."""

import json

import pytest

from jobhunter import sources as J
from jobhunter.sources import common
from jobhunter.storage import atomic as atomique
from jobhunter.storage import companies
from jobhunter.web.api import Api


@pytest.fixture
def file_de_fusion(tmp_path, monkeypatch, suivi_temporaire):
    q = tmp_path / "q.json"
    monkeypatch.setattr(J, "QUEUE", q)
    monkeypatch.setattr(common, "QUEUE", q)
    monkeypatch.setattr(J, "REJETS_TRI", tmp_path / "rej.json")
    return q


def test_noter_une_entreprise_une_fois_sans_casse(tmp_path):
    q = tmp_path / "q.json"
    companies.noter(
        q, [{"entreprise": "Alpha  Conseil", "source": "linkedin-search:esg"}], "2026-10-01"
    )
    reg = companies.noter(
        q,
        [
            {"entreprise": "alpha conseil", "source": "workday:alpha"},
            {"entreprise": "", "source": "x"},
        ],
        "2026-10-05",
    )
    assert list(reg) == ["alpha conseil"]
    e = reg["alpha conseil"]
    assert (e["nom"], e["premiere_vue"], e["derniere_vue"]) == (
        "Alpha  Conseil",
        "2026-10-01",
        "2026-10-05",
    )
    assert e["sites"] == ["linkedin", "workday"]
    assert companies.charger(q) == reg


def test_le_lien_d_une_offre_donne_le_flux(tmp_path):
    q = tmp_path / "q.json"
    reg = companies.noter(
        q,
        [
            {"entreprise": "Beta", "url": "https://www.linkedin.com/jobs/view/1"},
            {"entreprise": "Beta", "url": "https://boards.greenhouse.io/betaco/jobs/42"},
        ],
    )
    assert reg["beta"]["flux"]["outil"] == "greenhouse"
    assert reg["beta"]["flux"]["cle"] == "betaco"


def test_la_fusion_note_aussi_les_offres_ecartees(file_de_fusion):
    atomique.ecrire_json(
        file_de_fusion, [{"entreprise": "Déjà", "poste": "Analyste ESG", "statut": "Scan x"}]
    )
    loin = J._mk("Analyste ESG", "https://example.org/1", "Lointaine", location="Tokyo, Japan")
    J.merge_into_queue([loin], dry=False)
    reg = json.loads(companies.chemin(file_de_fusion).read_text(encoding="utf-8"))
    assert {"lointaine", "déjà"} <= set(reg)  # out of zone, and the queue the first time


def test_fusion_a_blanc_n_ecrit_rien(file_de_fusion):
    atomique.ecrire_json(file_de_fusion, [])
    J.merge_into_queue([J._mk("Analyste", "https://example.org/2", "Gamma")], dry=True)
    assert not companies.chemin(file_de_fusion).exists()


def test_ecran_entreprises_vues(file_de_fusion, monkeypatch):
    companies.noter(
        file_de_fusion,
        [
            {"entreprise": "Alpha", "url": "https://boards.greenhouse.io/alphaco/jobs/1"},
            {"entreprise": "Partie", "source": "apec"},
        ],
    )
    api = Api()
    api._file = lambda: [{"entreprise": "Alpha", "poste": "Analyste", "fit": 9}]
    api._flux = lambda: []
    lignes = {x["nom"]: x for x in api.entreprises_vues()["lignes"]}
    assert lignes["Alpha"]["offres"] == 1 and lignes["Alpha"]["fit"] == 9
    assert lignes["Alpha"]["url_flux"] and not lignes["Alpha"]["suivie"]
    assert lignes["Partie"]["offres"] == 0 and lignes["Partie"]["sites"] == ["APEC"]
