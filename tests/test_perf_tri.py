"""The three hot spots measured on the real queue on 2026-11-10 (19 528 offers).

- duplicates: language, city, title words and tokens computed once per offer, not once
  per pair (74 s -> 6.5 s);
- sorting: a word every branch of the pattern needs is looked for before the pattern
  (27 s -> 5 s);
- the offer sheet reads one posting's text, not all of them (0.9 s, 165 MB -> 0.3 ms).

Each change must give the same answers as before: the tests below say so.
"""

import json

import pytest

from jobhunter.programs import duplicates
from jobhunter.sources import common as C
from jobhunter.storage import queue as queue_io
from jobhunter.web.api import Api

# One posting per branch of _RX_OFFRE_STAGE: each must pass the word test AND the pattern.
STAGES = [
    "Nous recherchons un stagiaire pour notre equipe finance durable.",
    "Nous proposons une alternance de douze mois.",
    "Vous cherchez un premier stage en ESG ?",
    "Offre de stage au sein de la direction RSE.",
    "Stage de 6 mois a pourvoir en janvier.",
    "Stage de six mois, Paris.",
    "A 6-month internship in our ESG team.",
    "An internship of 6 months in Paris.",
    "This internship will start in January.",
    "Internship opportunity in sustainable finance.",
    "Nous recrutons un apprenti pour la rentree.",
]

# One per branch of _RX_ETUDIANT.
ETUDIANTS = [
    "Vous etes etudiant en ecole de commerce.",
    "Vous êtes actuellement étudiante en master.",
    "Etudiant en derniere annee, vous cherchez une experience.",
    "Dans le cadre de votre annee de cesure.",
    "Dans le cadre de votre année de césure.",
    "Stage de cesure a pourvoir.",
    "You are currently enrolled at a university.",
    "Currently studying finance or economics.",
    "Currently pursuing a master in finance.",
    "You are a current student in business.",
    "Currently a university student.",
    "Penultimate-year student in economics.",
    "Final year undergraduate in finance.",
    "You must be a current student.",
    "You must be enrolled for the whole period.",
    "Enrolled in a master programme.",
]


@pytest.mark.parametrize("texte", STAGES)
def test_le_mot_du_stage_ne_cache_aucune_branche(texte):
    assert C._RX_OFFRE_STAGE.search(texte), "the example no longer matches its branch"
    assert C._un_mot(texte, C._MOTS_OFFRE_STAGE)
    assert C.offre_de_stage(texte)


@pytest.mark.parametrize("texte", ETUDIANTS)
def test_le_mot_de_l_etudiant_ne_cache_aucune_branche(texte):
    assert C._RX_ETUDIANT.search(texte), "the example no longer matches its branch"
    assert C._un_mot(texte, C._MOTS_ETUDIANT)
    assert C.demande_etudiant(texte)


def test_le_mot_se_lit_sans_la_casse():
    assert C.offre_de_stage("OFFRE DE STAGE - DIRECTION RSE")
    assert C.demande_etudiant("VOUS ÊTES ÉTUDIANT EN MASTER")


@pytest.mark.parametrize("texte", ["", None, "Analyste ESG confirme, CDI, Paris."])
def test_sans_le_mot_la_reponse_est_non(texte):
    assert not C.offre_de_stage(texte)
    assert not C.demande_etudiant(texte)


def _offre(i, ville="Paris", langue="fr"):
    corps = {
        "fr": "Nous cherchons pour notre equipe une personne avec des competences ESG CSRD 2026",
        "en": "We are looking for someone with the skills of the team ESG CSRD 2026",
    }[langue]
    return {
        "entreprise": "Acme",
        "poste": f"Analyste numero {i} finance durable",
        "localisation": ville,
        "url": f"https://exemple.test/offre/{i}",
        "description": corps,
    }


def test_doublons_une_lecture_par_offre(monkeypatch):
    """Twelve offers of one company, one city: 66 pairs, and still twelve readings."""
    file = [_offre(i, langue="fr" if i % 2 else "en") for i in range(12)]
    appels = {"langue": 0, "ville": 0, "jetons": 0}

    def compte(nom):
        vraie = getattr(duplicates, nom)

        def f(o):
            appels[nom] += 1
            return vraie(o)

        return f

    for nom in appels:
        monkeypatch.setattr(duplicates, nom, compte(nom))
    duplicates.doublons(file, rang_source=lambda _u: 0, oid=lambda o: o["poste"])
    assert appels["ville"] == 12
    assert appels["langue"] <= 12
    assert appels["jetons"] <= 12


def test_doublons_meme_reponse_qu_avant():
    """A translated pair and a re-titled pair are still found; a stranger is kept."""
    a = _offre(1, langue="fr")
    b = dict(_offre(1, langue="en"), poste="Sustainable finance analyst one")
    c = dict(_offre(2), poste="Finance durable numero 2 analyste (H/F)")
    d = _offre(2)
    e = _offre(3, ville="Lyon")
    for o in (a, b):
        o["description"] += " SFDR TCFD GRI ISO 14001 SBTi 2030 CDP EFRAG"
    retires = duplicates.doublons(
        [a, b, c, d, e], rang_source=lambda _u: 0, oid=lambda o: o["poste"] + o["url"][-1]
    )
    assert len(retires) == 2
    assert e["poste"] + "3" not in retires
    assert all("_oid" not in o for o in (a, b, c, d, e))


@pytest.fixture
def file_en_base(file_temporaire):
    file_temporaire.write_text(
        json.dumps([{"entreprise": "A", "poste": "x"}, {"entreprise": "B", "poste": "y"}]),
        encoding="utf-8",
    )
    queue_io.DESCRIPTIONS.write_text(json.dumps({"A|x": "texte de A"}), encoding="utf-8")
    (file_temporaire.parent / "_format.json").write_text('{"format": 1}', encoding="utf-8")
    with queue_io.transaction() as offres:
        offres[1]["fit"] = 4
    assert queue_io.base().is_file()
    return file_temporaire


def test_une_description_par_sa_cle(file_en_base):
    assert queue_io.description("A|x") == "texte de A"
    assert queue_io.description("B|y") == ""
    assert queue_io.description("inconnue|z") == ""


def test_une_description_avant_la_base(file_temporaire):
    """The 2.x layout (one JSON file) answers too."""
    queue_io.DESCRIPTIONS.write_text(json.dumps({"A|x": "texte de A"}), encoding="utf-8")
    assert queue_io.description("A|x") == "texte de A"
    assert queue_io.description("B|y") == ""


def test_la_fiche_ne_lit_pas_toutes_les_descriptions(file_en_base, monkeypatch):
    def interdit():
        raise AssertionError("the sheet read every description")

    monkeypatch.setattr(queue_io, "_lire_descriptions", interdit)
    assert Api()._description("A|x") == "texte de A"
