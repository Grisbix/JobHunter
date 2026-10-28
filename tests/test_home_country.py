"""A profile outside France: the home country read in the CV, and places measured from it.

Measured on 2026-10-28 with a fictitious nurse's CV from Columbus, Ohio: the first
launch proposed Île-de-France as the priority zone, took « Columbus, Ohio, United
States » for the job, added French to the languages spoken, missed the phone number
and asked whether letters should agree « diplômé » or « diplômée ».
"""

import pytest

from jobhunter import lazy
from jobhunter.programs import first_launch as fl
from jobhunter.scoring import zones

CV_OHIO = """Jordan Sample
Columbus, Ohio, United States
jordan.sample@example.com · (614) 555-0100

PROFESSIONAL SUMMARY
Registered nurse with 4 years of experience in emergency and intensive care.

EXPERIENCE
Registered Nurse (RN) — Riverside Hospital, Columbus, OH — 2022–present
Triage of 30 patients per shift.

SKILLS
BLS, ACLS, triage
LANGUAGES
English (native), Spanish (conversational)
"""


@pytest.fixture
def maison():
    """The home country and the sectors, as a profile would give them.

    Set as computed lazy values, then forgotten: monkeypatch would put back a value it
    computed itself on reading, and the next tests would keep it.
    """

    def poser(pays, prio=(), sec=()):
        zones.PAYS_MAISON = pays
        zones.SECTEURS_PRIORITAIRES = [zones._secteur(x) for x in prio]
        zones.SECTEURS_SECONDAIRES = [zones._secteur(x) for x in sec]

    yield poser
    for nom in ("PAYS_MAISON", "SECTEURS_PRIORITAIRES", "SECTEURS_SECONDAIRES"):
        vars(zones).pop(nom, None)
    lazy.oublier()


def test_lieu_et_pays_lus_dans_l_en_tete():
    ident = fl.identite_du_cv(CV_OHIO)
    assert (ident["ville"], ident["region"], ident["pays"]) == ("Columbus", "Ohio", "us")
    assert ident["telephone"] == "(614) 555-0100"
    assert fl.lieu_du_cv(["Austin, TX 78701"]) == ("Austin", "Texas", "us")
    assert fl.lieu_du_cv(["Lyon, France"])[2] == "fr"


def test_un_lieu_ou_un_titre_de_section_n_est_pas_un_metier():
    lignes = [l.strip() for l in CV_OHIO.splitlines() if l.strip()]
    assert fl.titre_du_cv(lignes, fl.identite_du_cv(CV_OHIO)) == "Registered Nurse"


def test_cv_francais_inchange():
    cv = "Camille MARTIN\nChargée de communication\ncamille@exemple.fr · Toulouse\n"
    ident = fl.identite_du_cv(cv)
    assert (ident["ville"], ident["pays"]) == ("Toulouse", "fr")


def test_profil_americain_sans_france():
    ident = fl.identite_du_cv(CV_OHIO)
    rep = {
        "identite": ident,
        "competences": fl.competences_du_cv(CV_OHIO),
        "metiers": ["Registered Nurse"],
        "annees": 4,
        "genre": "m",
        "prioritaires": [],
        "secondaires": [],
    }
    p = fl.construire(CV_OHIO, "CV_Jordan_Sample.docx", rep)
    assert p["pays"] == "us"
    assert "fr" not in p["langues_parlees"]
    assert p["langues_parlees"][0] == "en"


def test_zones_vues_de_l_ohio(maison):
    columbus = {"cle": "columbus", "libelle": "Columbus", "lieux": ["Columbus"]}
    ohio = {"cle": "ohio", "libelle": "Ohio", "lieux": ["Ohio", "OH"]}
    maison("us", [columbus], [ohio])
    assert zones.zone_lieu("Columbus, OH") == zones.PRIORITAIRE
    assert zones.zone_lieu("Dayton, Ohio") == zones.SECONDAIRE
    assert zones.zone_lieu("Austin, TX") == zones.AILLEURS
    assert zones.zone_lieu("Paris, France") == zones.INTERNATIONAL
    assert zones.zone_lieu("Lyon") == zones.INTERNATIONAL
    assert zones.zone_lieu("Springfield") == zones.INCONNU
    # Its own sectors are at home, not in France.
    assert zones.pays_lieu("Columbus, Ohio, United States") == "États-Unis"


def test_zones_vues_de_france_inchangees(maison):
    maison("fr")
    assert zones.zone_lieu("Angers, Maine-et-Loire") == zones.AILLEURS  # not Maine, USA
    assert zones.zone_lieu("Dayton, Ohio") == zones.INTERNATIONAL
    assert zones.pays_lieu("Dayton, Ohio") == "États-Unis"
