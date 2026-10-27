"""Finding companies to follow (sources.discovery), on synthetic data, without network."""

import json

import pytest

from jobhunter.sources import common, directory, discovery
from jobhunter.web.api import Api


class R:
    def __init__(self, code, data=None, text=""):
        self.status_code, self._data, self.text = code, data, text

    def json(self):
        return self._data


LIGNES = [
    json.dumps(
        {"url": "https://alpha.wd3.myworkdayjobs.com/fr-FR/Alpha_Careers/job/Paris/Analyste_R1"}
    ),
    json.dumps({"url": "https://alpha.wd3.myworkdayjobs.com/Alpha_Careers/details/x"}),
    json.dumps({"url": "https://beta.wd103.myworkdayjobs.com/External"}),
    json.dumps({"url": "https://beta.wd103.myworkdayjobs.com/wday/cxs/beta/External/jobs"}),
    json.dumps({"url": "https://www.myworkdayjobs.com/"}),
    "pas du json",
]


@pytest.fixture
def ici(tmp_path, monkeypatch):
    monkeypatch.setattr(common, "QUEUE", tmp_path / "q.json")
    monkeypatch.setattr(discovery.time, "sleep", lambda s: None)
    return tmp_path


def test_sites_workday_des_lignes_de_l_index():
    assert discovery.sites_workday(LIGNES) == {
        ("alpha", "wd3", "Alpha_Careers"),
        ("beta", "wd103", "External"),
    }


def _index(pages_ko=()):
    appels = []

    def get(_httpx, url, **kw):
        p = kw.get("params") or {}
        appels.append((url, p, kw["headers"]["User-Agent"]))
        if url == discovery.COLLINFO:
            return R(200, [{"id": "CC-1", "cdx-api": "https://index.commoncrawl.org/CC-1-index"}])
        if p.get("showNumPages"):
            return R(200, {"pages": 2})
        if p.get("page") in pages_ko:
            return R(504)
        return R(200, text="\n".join(LIGNES[: 2 + 2 * p["page"]]))

    return get, appels


def test_construire_puis_reprendre(ici, monkeypatch):
    get, appels = _index(pages_ko=(1,))
    monkeypatch.setattr(discovery._commun, "_get_borne", get)
    b = discovery.construire_annuaire()
    assert b["pages"] == 1 and b["restantes"] == 1 and b["sites"] == 1
    assert all("JobHunter" in ua for *_, ua in appels)  # the project names itself
    # next run: page 0 is not asked again, page 1 now answers
    get, appels = _index()
    monkeypatch.setattr(discovery._commun, "_get_borne", get)
    b = discovery.construire_annuaire()
    assert b["pages"] == 1 and b["restantes"] == 0 and b["sites"] == 2
    assert not [p for _, p, _ in appels if p.get("page") == 0]


def test_index_injoignable_ne_change_rien(ici, monkeypatch):
    monkeypatch.setattr(discovery._commun, "_get_borne", lambda *a, **k: R(503))
    assert discovery.construire_annuaire()["restantes"] == -1
    assert not discovery.chemin_annuaire().exists()


def test_annuaire_workday_cherche_par_nom(ici):
    discovery.chemin_annuaire().write_text(
        json.dumps({"sites": [["alphagroupe", "wd3", "Careers"]]}), encoding="utf-8"
    )
    e = [x for x in directory.chercher("alphag") if x.outil == "workday"]
    assert e and e[0].jeton == "alphagroupe.wd3/Careers"
    assert directory.workday_de_jeton(e[0].jeton) == ("alphagroupe", "wd3", "Careers")
    assert directory.workday_de_jeton("x/../y") is None


def test_offres_ouvertes(monkeypatch):
    monkeypatch.setattr(discovery._commun, "_get_borne", lambda *a, **k: R(200, {"jobs": [1, 2]}))
    monkeypatch.setattr(discovery._commun, "_post_borne", lambda *a, **k: R(200, {"total": 7}))
    assert discovery.offres_ouvertes(("greenhouse", "alpha")) == 2
    assert discovery.offres_ouvertes(("workday", ("alpha", "wd3", "Careers"))) == 7
    assert discovery.offres_ouvertes(("personio", "alpha")) is None
    monkeypatch.setattr(discovery._commun, "_get_borne", lambda *a, **k: R(404))
    assert discovery.offres_ouvertes(("lever", "alpha")) == 0


def test_suivre_vues_seulement_les_flux_qui_repondent(monkeypatch):
    api = Api()
    lignes = [
        {
            "nom": "Alpha",
            "url_flux": "https://boards.greenhouse.io/alpha/jobs/1",
            "suivie": False,
            "fit": 8,
        },
        {"nom": "Vide", "url_flux": "https://jobs.lever.co/vide/1", "suivie": False, "fit": 9},
        {"nom": "Basse", "url_flux": "https://jobs.lever.co/basse/1", "suivie": False, "fit": 5},
        {"nom": "Deja", "url_flux": "https://jobs.lever.co/deja/1", "suivie": True, "fit": 9},
    ]
    monkeypatch.setattr(api, "entreprises_vues", lambda: {"lignes": lignes}, raising=False)
    cfg = {}
    ecrit = []
    monkeypatch.setattr(api, "_cfg_sources", lambda: ("f", cfg), raising=False)
    monkeypatch.setattr(api, "_defauts", lambda: {"ats_slugs": {}}, raising=False)
    import jobhunter.web.panels as panneaux

    monkeypatch.setattr(panneaux, "_ecrire_json", lambda f, c: ecrit.append(c))
    monkeypatch.setattr(discovery, "offres_ouvertes", lambda t: 0 if t[1] == "vide" else 3)
    r = api.suivre_vues(7)
    assert r["suivies"] == ["Alpha"] and r["vides"] == ["Vide"]
    assert cfg["ats_slugs"]["greenhouse"] == ["alpha"] and ecrit
