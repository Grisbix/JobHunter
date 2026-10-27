"""The offers of the companies already seen, on their career sites (sources.company_sites)."""

import json

import pytest

from jobhunter.sources import INCIDENTS, common, feeds
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

VIDE = {"demandes": {}, "flux": {}}


@pytest.fixture
def registre(tmp_path, monkeypatch):
    """A queue in tmp_path, no followed feed, no pause, no quota."""
    q = tmp_path / "q.json"
    monkeypatch.setattr(common, "QUEUE", q)
    monkeypatch.setattr(cs, "_suivis", lambda: (set(), set()))
    monkeypatch.setattr(cs.time, "sleep", lambda s: None)
    monkeypatch.setattr(cs, "_quota_atteint", lambda n: False)
    monkeypatch.setattr(common, "contrats_exclus", lambda: [])
    monkeypatch.setattr(cs, "_pages_par_entreprise", lambda: {})
    monkeypatch.setattr(cs, "annuaire_workday", lambda: {})
    monkeypatch.setattr(feeds, "suspendre_morts", lambda *a, **k: {})
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
    assert list(etat["demandes"]) == ["mirova"]
    assert etat["demandes"]["mirova"] == {
        "le": cs.date.today().isoformat(),
        "offres": 1,
        "vides": 0,
    }


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
    assert json.loads(cs.chemin_etat().read_text(encoding="utf-8")) == VIDE
    monkeypatch.setattr(cs, "_quota_atteint", lambda n: True)
    appels = reseau(monkeypatch, [])
    assert cs.scan_company_sites() == [] and appels == []
    assert json.loads(cs.chemin_etat().read_text(encoding="utf-8")) == VIDE


def test_une_erreur_compte_un_incident(registre, monkeypatch):
    companies.noter(registre, [{"entreprise": "Delta", "source": "apec"}], "2026-10-20")

    def casse(*a, **k):
        raise TimeoutError

    monkeypatch.setattr(common, "_get_borne", casse)
    assert cs.scan_company_sites() == []
    assert INCIDENTS["sites-carrieres"]["TimeoutError"] == 1


def test_ancien_etat_et_delai_double(registre):
    cs.chemin_etat().write_text('{"alpha": "2026-10-01"}', encoding="utf-8")
    assert cs.lire_etat() == {"demandes": {"alpha": {"le": "2026-10-01"}}, "flux": {}}
    assert [cs.delai(v) for v in (0, 1, 2, 3, 9)] == [7, 14, 28, 56, 56]
    reg = {"alpha": {"nom": "Alpha"}, "beta": {"nom": "Beta"}}
    etat = {
        "alpha": {"le": "2026-10-15", "vides": 1},  # 12 days < 14: not yet
        "beta": {"le": "2026-10-15", "vides": 0},  # 12 days ≥ 7: again
    }
    assert [e["_cle"] for e in cs.a_demander(reg, etat, "2026-10-27")] == ["beta"]


def test_freehire_apprend_l_outil_puis_le_lit(registre, monkeypatch):
    companies.noter(registre, [{"entreprise": "Mirova", "source": "apec"}], "2026-10-20")
    postes = {
        "data": {
            "jobs": [
                {"title": "Boulanger", "url": "https://boards.greenhouse.io/mirova/jobs/7"},
            ]
        }
    }
    reseau(monkeypatch, [R(200, RECHERCHE), R(200, postes), R(200, {})])
    assert cs.scan_company_sites() == []  # the title does not pass, the tool is learned
    etat = cs.lire_etat()
    assert etat["flux"]["mirova"]["outil"] == "greenhouse"
    assert etat["flux"]["mirova"]["cle"] == "mirova"
    assert etat["demandes"]["mirova"]["vides"] == 1

    lus = []
    from jobhunter.sources import ats

    monkeypatch.setattr(ats, "fetch_ats", lambda o, c: lus.append((o, c)) or [{"poste": "x"}])
    etat["demandes"] = {}
    cs.ecrire_json(cs.chemin_etat(), etat)
    appels = reseau(monkeypatch, [])
    offres = cs.scan_company_sites()
    assert lus == [("greenhouse", "mirova")] and appels == []
    assert offres[0]["source"] == "sites-carrieres:greenhouse"


def test_comptes_possibles():
    assert cs.comptes_possibles("Société Générale") == ["societegenerale", "societe-generale"]
    assert cs.comptes_possibles("Mirova") == ["mirova"]
    assert cs.comptes_possibles("AXA") == []  # too short: anyone's


def test_deviner_verifie_le_nom(monkeypatch):
    monkeypatch.setattr(cs.time, "sleep", lambda s: None)
    from jobhunter.sources import discovery

    monkeypatch.setattr(discovery, "offres_ouvertes", lambda t: 0)
    # Greenhouse has a board « mirova », but it is another company's.
    reseau(monkeypatch, [R(200, {"name": "Mirova Cleaning Services"})])
    assert cs.deviner(None, "Mirova Natixis") is None
    reseau(
        monkeypatch,
        [R(404), R(200, {"totalFound": 3, "content": [{"company": {"name": "MIROVA"}}]})],
    )
    assert cs.deviner(None, "Mirova") == {
        "outil": "smartrecruiters",
        "cle": "mirova",
        "url": "https://careers.smartrecruiters.com/mirova",
        "par": "nom",
    }


def test_page_carriere_donne_l_outil():
    assert cs.page_de_l_entreprise("https://careers.alpha.example/job/1")
    assert not cs.page_de_l_entreprise("https://www.linkedin.com/jobs/view/1")
    assert not cs.page_de_l_entreprise("https://jobs.lever.co/alpha/1")  # already a tool
    html = (
        '<html><iframe src="https://job-boards.greenhouse.io/embed/job_board?for=alphaco">'
        '<a href="https://jobs.lever.co/alpha">x</a></html>'
    )
    trouve = cs.outil_dans_la_page(html)
    assert trouve and trouve["par"] == "page"
    assert cs.outil_dans_la_page("<html>rien</html>") is None


def test_sans_freehire_on_devine_puis_on_lit_la_page(registre, monkeypatch):
    companies.noter(registre, [{"entreprise": "Omega Partners", "source": "apec"}], "2026-10-20")
    monkeypatch.setattr(cs, "deviner", lambda *a: None)
    monkeypatch.setattr(
        cs, "_pages_par_entreprise", lambda: {"omega partners": ["https://omega.example/o/1"]}
    )
    monkeypatch.setattr(
        cs, "lire_la_page", lambda h, u: {"outil": "lever", "cle": "omega", "url": u, "par": "page"}
    )
    from jobhunter.sources import ats

    monkeypatch.setattr(ats, "fetch_ats", lambda o, c: [{"poste": "Analyste", "source": "lever"}])
    reseau(monkeypatch, [R(200, {"data": []})])  # freehire does not know it
    offres = cs.scan_company_sites()
    assert offres[0]["source"] == "sites-carrieres:lever"
    assert cs.lire_etat()["flux"]["omega partners"]["par"] == "page"


def test_flux_morts_suspendus(tmp_path):
    cfg, etat = tmp_path / "sources_config.json", tmp_path / "_flux_etat.json"
    cfg.write_text('{"flux_suspendus": []}', encoding="utf-8")
    etat.write_text(
        json.dumps(
            {
                "greenhouse:mort": {
                    "premier": "2026-01-01T08:00",
                    "tentative": "2026-10-27T08:00",
                    "succes": "2026-06-01T08:00",
                    "offres": 0,
                },
                "lever:vide": {
                    "premier": "2026-01-01T08:00",
                    "succes": "2026-10-27T08:00",
                    "brut": 0,
                    "brut_le": "2026-05-01T08:00",
                },
                "ashby:rien": {
                    "premier": "2026-01-01T08:00",
                    "succes": "2026-10-27T08:00",
                    "brut": 9,
                    "brut_le": "2026-10-27T08:00",
                    "retenues_le": "2026-03-01T08:00",
                },
                "workday:jeune": {"premier": "2026-10-20T08:00", "tentative": "2026-10-27T08:00"},
            }
        ),
        encoding="utf-8",
    )
    trouves = feeds.suspendre_morts(cfg, etat)
    assert set(trouves) == {"greenhouse:mort", "lever:vide"}  # « rien pour » is not dead
    d = json.loads(cfg.read_text(encoding="utf-8"))
    assert feeds.suspendus(d) == {"greenhouse:mort", "lever:vide"}
    assert set(d[feeds.CLE_AUTO]) == {"greenhouse:mort", "lever:vide"}
    assert b"\r\n" not in cfg.read_bytes()
    assert feeds.suspendre_morts(cfg, etat) == {}  # already suspended


def test_deviner_par_l_annuaire_workday(monkeypatch):
    monkeypatch.setattr(cs.time, "sleep", lambda s: None)
    from jobhunter.sources import discovery

    ouverts = {("workday", ("mirova", "wd3", "Careers")): 12}
    monkeypatch.setattr(discovery, "offres_ouvertes", lambda t: ouverts.get(t, 0))
    reseau(monkeypatch, [])
    annuaire = {"mirova": [("mirova", "wd3", "Interne"), ("mirova", "wd3", "Careers")]}
    trouve = cs.deviner(None, "Mirova", annuaire)
    assert trouve and trouve["cle"] == ["mirova", "wd3", "Careers"]
    assert trouve["url"] == "https://mirova.wd3.myworkdayjobs.com/Careers"
