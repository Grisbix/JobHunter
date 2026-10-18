"""Retrouver une offre LinkedIn sur le site de l'employeur (site_final), sans reseau.

Intitule strict, identite de l'employeur en mots entiers, quand resonder un flux,
lecture Workday, comptes ATS de demonstration (« coquilles »).
Converti depuis Scripts/test_site_final.py.
"""

import datetime

import pytest

from jobhunter.programmes import site_final as S

J = datetime.date(2026, 10, 7)


# ── intitules : memes mots, l'ordre et le genre/contrat varient ────────────────
@pytest.mark.parametrize(
    ("a", "b", "attendu"),
    [
        ("Analyste ESG (H/F)", "Analyste ESG", True),
        ("ESG Analyst", "Analyst ESG", True),
        ("Junior Energy Consultant", "Energy Consultant", False),
        ("(H/F)", "(H/F)", False),
    ],
    ids=["genre", "ordre", "junior", "vide"],
)
def test_meme_titre(a, b, attendu):
    assert S.meme_titre(a, b) is attendu


@pytest.mark.parametrize(
    ("nom", "tenant", "attendu"),
    [
        ("Accenture in India", "accenture", ["accenture"]),
        ("Lombard Odier", "lombardodier", ["lombard", "odier"]),
        ("Lombard Odier", "lombard-odier", ["lombard", "odier"]),
        ("ERM", "accenture", []),
    ],
    ids=["1 mot", "2 mots", "tiret", "etranger"],
)
def test_mots_du_tenant(nom, tenant, attendu):
    assert S.mots_du_tenant(nom, tenant) == attendu


# ── identite : la vitrine doit nommer l'entreprise en mots entiers ─────────────
@pytest.mark.parametrize(
    ("nom", "tenant", "texte", "attendu"),
    [
        ("ERM", "erm", "at erm, sustainability is", True),
        ("ERM", "erm", "long term growth", False),  # « erm » dans « term »
        ("Lombard Odier", "lombardodier", "about lombard odier", True),
        ("Lombard Odier", "lombardodier", "lombardodier group", False),
        ("Accenture", "accenture", "8140 asol - gurugram non stpi company", False),
    ],
    ids=["nomme", "dans un mot", "deux mots", "deux mots colles", "entite juridique"],
)
def test_meme_employeur(nom, tenant, texte, attendu):
    assert S.meme_employeur(nom, tenant, texte) is attendu


# ── quand resonder : un flux trouve ne se resonde pas, une absence apres 30 j ──
@pytest.mark.parametrize(
    ("etat", "attendu"),
    [
        (None, (True, True)),
        ({"date": "2026-10-05", "flux": [["lever", "x"]]}, (False, True)),
        ({"date": "2026-10-05", "flux": [], "wd_date": "2026-10-05"}, (False, False)),
        ({"date": "2026-09-01", "flux": [], "wd_date": "2026-09-01"}, (True, True)),
        (
            {"date": "2026-09-01", "flux": [["workday", "a.wd3/b"]], "wd_date": "2026-09-01"},
            (True, False),
        ),
        ({"date": "?", "flux": []}, (True, True)),
    ],
    ids=[
        "jamais vu",
        "ATS trouve, Workday jamais",
        "rien recent",
        "rien perime",
        "Workday trouve",
        "date illisible",
    ],
)
def test_a_resonder(etat, attendu):
    assert S.a_resonder(etat, J) == attendu


# ── sonder : garde ce qui est trouve, ne resonde que ce qui est du ─────────────
@pytest.fixture
def appels(monkeypatch):
    vus = []
    monkeypatch.setattr(S, "flux_de", lambda e, c: vus.append(("ats", e)) or [["greenhouse", "g"]])
    monkeypatch.setattr(
        S, "flux_workday", lambda e: vus.append(("wd", e)) or [["workday", "t.wd3/Site"]]
    )
    return vus


def test_sonder_neuf(appels):
    x = S.sonder("A", None, [], J)
    assert (x["flux"], x["date"], x["wd_date"], len(appels)) == (
        [["greenhouse", "g"], ["workday", "t.wd3/Site"]],
        "2026-10-07",
        "2026-10-07",
        2,
    )


def test_sonder_workday_seul(appels):
    x = S.sonder("B", {"date": "2026-10-01", "flux": [["lever", "l"]]}, [], J)
    assert (x["flux"], x["date"], appels) == (
        [["lever", "l"], ["workday", "t.wd3/Site"]],
        "2026-10-01",
        [("wd", "B")],
    )


def test_sonder_workday_cure(appels):
    x = S.sonder("C", None, [("workday", "c.wd1/C_Careers")], J)
    assert (x["flux"][-1], appels) == (["workday", "c.wd1/C_Careers"], [("ats", "C")])


def test_flux_cure_ajoute_sans_resonder(appels):
    cures = [
        ("workday", "pwc.wd3/Global_Experienced_Careers"),
        ("workday", "pwc.wd3/Global_Campus_Careers"),
    ]
    x = S.sonder(
        "PwC France", {"date": "2026-10-07", "flux": [], "wd_date": "2026-10-07"}, cures, J
    )
    assert (x["flux"], appels) == ([list(c) for c in cures], [])


# ── lire_workday : URL publique = hote/site + externalPath ─────────────────────
class _R:
    status_code = 200

    def json(self):
        return {
            "jobPostings": [
                {
                    "title": "ESG Analyst",
                    "externalPath": "/job/Paris/ESG_R1",
                    "locationsText": "Paris",
                },
                {"title": "", "externalPath": "/x"},
            ]
        }


@pytest.fixture
def workday(monkeypatch):
    monkeypatch.setattr(S, "_wd_jobs", lambda *a, **k: _R())


def test_lire_workday(workday):
    assert S.lire_workday("erm.wd3/erm_Careers", "esg") == [
        ("ESG Analyst", "https://erm.wd3.myworkdayjobs.com/erm_Careers/job/Paris/ESG_R1", "Paris")
    ]


def test_lire_flux_workday(workday):
    assert S.lire_flux("workday", "erm.wd3/erm_Careers", "esg")[0][0] == "ESG Analyst"


def test_reseau_en_panne(monkeypatch):
    monkeypatch.setattr(S, "_wd_jobs", lambda *a, **k: None)
    assert S.lire_workday("erm.wd3/erm_Careers", "esg") is None


# ── coquille : compte ATS de demonstration (google.recruitee.com, 2026-10-07) ──
@pytest.mark.parametrize(
    ("offres", "attendu"),
    [
        ([("Senior Marketer (Sample)", "u", "London")], True),
        ([("Senior Marketer (Sample)", "u", ""), ("sales executive", "v", "")], True),
        ([("ESG Analyst", "v", "")], False),
        ([], False),
    ],
    ids=["que des modeles", "modele a cote d'une offre saisie", "vraies offres", "flux vide"],
)
def test_coquille(offres, attendu):
    assert S.coquille(offres) is attendu
