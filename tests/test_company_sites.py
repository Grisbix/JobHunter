"""The offers of the companies already seen, on their career sites (sources.company_sites)."""

import json

import pytest

from jobhunter.sources import INCIDENTS, common
from jobhunter.sources import company_sites as cs
from jobhunter.storage import companies


class R:
    def __init__(self, code, data=None):
        self.status_code, self._d = code, data or {}

    def json(self):
        return self._d


RECHERCHE = {
    "data": [
        {"slug": "mirvac", "name": "Mirvac", "job_count": 40},
        {"slug": "mirova", "name": "MIROVA", "job_count": 2},
        {"slug": "mirova-uk", "name": "Mirova UK Limited", "job_count": 1},
        {"slug": "mirova-vide", "name": "Mirova Asia", "job_count": 0},
    ]
}
POSTES = {
    "data": {
        "jobs": [
            {
                "title": "Analyste ESG",
                "url": "https://mirova.example/jobs/1?utm_source=freehire.me",
                "location": "Paris",
                "posted_at": "2026-10-20T08:00:00Z",
                "source": "teamtailor",
            }
        ]
    }
}


@pytest.fixture
def registre(tmp_path, monkeypatch):
    """A queue in tmp_path, no followed feed, no pause, no quota."""
    q = tmp_path / "q.json"
    monkeypatch.setattr(common, "QUEUE", q)
    monkeypatch.setattr(cs, "_suivis", lambda: (set(), set()))
    monkeypatch.setattr(cs.time, "sleep", lambda s: None)
    monkeypatch.setattr(cs, "_quota_atteint", lambda n: False)
    monkeypatch.setattr(common, "contrats_exclus", lambda: [])
    INCIDENTS.clear()
    yield q
    INCIDENTS.clear()


def reseau(monkeypatch, reponses):
    it, appels = iter(reponses), []

    def appel(_envoi, url, **kw):
        appels.append(url)
        return next(it, R(200, {}))

    monkeypatch.setattr(common, "_get_borne", appel)
    return appels


def test_meme_entreprise():
    assert cs.meme_entreprise("Mirova", "MIROVA")
    assert cs.meme_entreprise("Amundi", "Amundi Ireland Limited")
    assert cs.meme_entreprise("Société Générale", "societe generale")
    assert not cs.meme_entreprise("Mirova", "Mirvac")
    assert not cs.meme_entreprise("Axa", "Axalta")
    assert not cs.meme_entreprise("", "Alpha")


def test_a_demander_ordre_et_delai(monkeypatch):
    reg = {
        "ancienne": {"nom": "Ancienne", "derniere_vue": "2026-09-01"},
        "recente": {"nom": "Recente", "derniere_vue": "2026-10-20"},
        "demandee": {"nom": "Demandee", "derniere_vue": "2026-10-25"},
        "il y a longtemps": {"nom": "Il y a longtemps", "derniere_vue": "2026-10-26"},
        "suivie": {"nom": "Suivie", "flux": {"outil": "greenhouse", "cle": "suivie"}},
        "par son nom": {"nom": "Par son nom"},
    }
    monkeypatch.setattr(cs, "_suivis", lambda: ({("greenhouse", "suivie")}, {"par son nom"}))
    etat = {"demandee": "2026-10-25", "il y a longtemps": "2026-10-01"}
    lot = cs.a_demander(reg, etat, "2026-10-27")
    # never asked first, most recently seen first; then the least recently asked
    assert [e["_cle"] for e in lot] == ["recente", "ancienne", "il y a longtemps"]
    assert [e["_cle"] for e in cs.a_demander(reg, etat, "2026-10-27", 1)] == ["recente"]


def test_par_freehire_nom_exact_et_etat(registre, monkeypatch):
    companies.noter(registre, [{"entreprise": "Mirova", "source": "apec"}], "2026-10-20")
    appels = reseau(monkeypatch, [R(200, RECHERCHE), R(200, POSTES), R(200, {})])
    offres = cs.scan_company_sites()
    assert appels[0].endswith("/api/v1/companies")
    assert [u.rsplit("/", 1)[1] for u in appels[1:]] == ["mirova", "mirova-uk"]  # not Mirvac
    assert len(offres) == 1
    assert offres[0]["url"] == "https://mirova.example/jobs/1"
    assert offres[0]["source"] == "sites-carrieres:teamtailor"
    etat = json.loads(cs.chemin_etat().read_text(encoding="utf-8"))
    assert list(etat) == ["mirova"]


def test_par_son_outil_sans_freehire(registre, monkeypatch):
    companies.noter(
        registre,
        [{"entreprise": "Beta", "url": "https://boards.greenhouse.io/betaco/jobs/42"}],
        "2026-10-20",
    )
    lus = []

    def fetch_ats(outil, cle):
        lus.append((outil, cle))
        return [{"poste": "Analyste ESG", "source": "greenhouse:betaco"}]

    from jobhunter.sources import ats

    monkeypatch.setattr(ats, "fetch_ats", fetch_ats)
    appels = reseau(monkeypatch, [])
    offres = cs.scan_company_sites()
    assert lus == [("greenhouse", "betaco")] and appels == []
    assert offres[0]["source"] == "sites-carrieres:greenhouse"


def test_refus_ou_quota_laisse_a_redemander(registre, monkeypatch):
    companies.noter(registre, [{"entreprise": "Gamma", "source": "apec"}], "2026-10-20")
    reseau(monkeypatch, [R(429), R(429), R(429)])
    assert cs.scan_company_sites() == []
    assert json.loads(cs.chemin_etat().read_text(encoding="utf-8")) == {}
    monkeypatch.setattr(cs, "_quota_atteint", lambda n: True)
    appels = reseau(monkeypatch, [])
    assert cs.scan_company_sites() == [] and appels == []
    assert json.loads(cs.chemin_etat().read_text(encoding="utf-8")) == {}


def test_une_erreur_compte_un_incident(registre, monkeypatch):
    companies.noter(registre, [{"entreprise": "Delta", "source": "apec"}], "2026-10-20")

    def casse(*a, **k):
        raise TimeoutError

    monkeypatch.setattr(common, "_get_borne", casse)
    assert cs.scan_company_sites() == []
    assert INCIDENTS["sites-carrieres"]["TimeoutError"] == 1
