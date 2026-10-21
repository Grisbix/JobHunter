"""ats_liveness: the ATS's API decides, an unclear answer leaves the page to decide."""

import types

import pytest

from jobhunter import ats_liveness as al

WD = "https://pwc.wd3.myworkdayjobs.com/fr-FR/Global_Campus_Careers/job/Neuilly-sur-Seine/Consultant_740384WD-1"
GH = "https://job-boards.greenhouse.io/acme/jobs/4012345"
AS = "https://jobs.ashbyhq.com/alan/a5973d82-d4f2-48f8-8c96-70de49f14c9b"


def rep(statut, corps=None):
    def json():
        if corps is None:
            raise ValueError("pas de JSON")
        return corps

    return types.SimpleNamespace(status_code=statut, json=json)


class Faux:
    def __init__(self, *reponses):
        self.reponses, self.urls = list(reponses), []

    def __call__(self, url, **kw):
        self.urls.append(url)
        return self.reponses.pop(0)


@pytest.fixture(autouse=True)
def tableaux_vides():
    al.oublier_tableaux()


@pytest.mark.parametrize(
    ("reponse", "attendu"),
    [
        (rep(200, {"jobPostingInfo": {}}), "OK"),
        (rep(404), "FERMEE"),
        (
            rep(403, {"httpStatus": 403, "errorCode": "S22", "message": "permission denied"}),
            "FERMEE",
        ),
        (rep(403, {"httpStatus": 403, "errorCode": "S01"}), None),  # another refusal
        (rep(403), None),  # a firewall page, not JSON
        (rep(429), None),
    ],
    ids=["ouverte", "404", "S22", "autre 403", "403 html", "429"],
)
def test_workday(reponse, attendu):
    get = Faux(reponse)
    v = al.controle(WD, get)
    assert (v[0] if v else None) == attendu
    assert get.urls == [
        "https://pwc.wd3.myworkdayjobs.com/wday/cxs/pwc/Global_Campus_Careers/job/"
        "Neuilly-sur-Seine/Consultant_740384WD-1"
    ]


def test_greenhouse():
    assert al.controle(GH, Faux(rep(200, {})))[0] == "OK"
    assert al.controle(GH, Faux(rep(404)))[0] == "FERMEE"
    assert al.controle(GH, Faux(rep(500))) is None


def test_ashby_tableau_lu_une_fois():
    tableau = {"jobs": [{"id": "A5973D82-D4F2-48F8-8C96-70DE49F14C9B"}]}
    get = Faux(rep(200, tableau))
    assert al.controle(AS, get)[0] == "OK"
    autre = "https://jobs.ashbyhq.com/alan/00000000-0000-0000-0000-000000000000"
    assert al.controle(autre, get) == ("FERMEE", "absente du tableau Ashby")
    assert len(get.urls) == 1  # one board per company and per run


def test_ashby_tableau_illisible_ne_conclut_pas():
    assert al.controle(AS, Faux(rep(404))) is None
    al.oublier_tableaux()
    assert al.controle(AS, Faux(rep(200, {"pas": "de jobs"}))) is None


@pytest.mark.parametrize(
    "url",
    [
        "https://www.linkedin.com/jobs/view/123",
        "https://evil.example/x?u=https://pwc.wd3.myworkdayjobs.com/a/job/b",
        "https://pwc.wd3.myworkdayjobs.com/site/job/../../admin",
        "http://job-boards.greenhouse.io/acme/jobs/1",  # not https
    ],
)
def test_autres_adresses_jamais_demandees(url):
    get = Faux()
    assert al.controle(url, get) is None
    assert get.urls == []


def test_erreur_reseau_laisse_la_page_decider():
    def get(url, **kw):
        raise TimeoutError

    assert al.controle(WD, get) is None
