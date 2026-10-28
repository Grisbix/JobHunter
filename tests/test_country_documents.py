"""Letters and contracts in the offer's country's format.

Measured on 2026-10-28: an English letter for an offer in Columbus, Ohio opened with
« Dear Sir or Madam » and closed with « Yours faithfully », the British forms; a
« Part-time » or « (Contract) » posting had no contract type.
"""

import pytest

from jobhunter import lazy
from jobhunter.documents import letter
from jobhunter.documents.common import nord_americain
from jobhunter.documents.message import appel
from jobhunter.scoring import zones
from jobhunter.sources.common import contrat_de_la_description, contrat_du_titre

OFFRE = {
    "company": "Riverside Hospital",
    "role": "Registered Nurse",
    "offer_text": "Registered Nurse: patient care, triage, BLS.",
    "missions": "",
    "profil": "",
    "domaine": "",
}


@pytest.fixture
def maison():
    def poser(pays):
        zones.PAYS_MAISON = pays

    yield poser
    vars(zones).pop("PAYS_MAISON", None)
    lazy.oublier()


@pytest.fixture
def lettre(monkeypatch, tmp_path):
    textes = []
    monkeypatch.setattr(
        letter._generes,
        "enregistrer",
        lambda doc, out: textes.append([p.text for p in doc.paragraphs]),
    )
    monkeypatch.setattr(letter, "LT_OUT", tmp_path, raising=False)

    def ecrire(lieu):
        letter.tailor_letter(dict(OFFRE, lieu=lieu), nom="essai", langue="en")
        return textes[-1]

    return ecrire


def test_nord_americain(maison):
    maison("fr")
    assert nord_americain("Columbus, OH") and nord_americain("Toronto, Ontario, Canada")
    assert not nord_americain("London, United Kingdom") and not nord_americain("")
    maison("us")
    assert nord_americain("")  # unknown place: the profile's country


def test_lettre_americaine(maison, lettre):
    maison("fr")
    lignes = lettre("Columbus, OH")
    assert "Dear Hiring Manager," in lignes
    assert "Sincerely," in lignes and "Yours faithfully," not in lignes
    date = next(l for l in lignes if l[:1].isalpha() and l.split()[0] in letter_mois())
    assert date.split()[1].rstrip(",").isdigit()  # « October 28, 2026 »


def test_lettre_britannique(maison, lettre):
    maison("fr")
    lignes = lettre("London, United Kingdom")
    assert "Dear Sir or Madam," in lignes and "Yours faithfully," in lignes
    assert any(
        l.split()[:1] and l.split()[0].isdigit() and l.split()[1] in letter_mois()
        for l in lignes
        if l.split()
    )


def letter_mois():
    return {
        "January", "February", "March", "April", "May", "June", "July", "August",
        "September", "October", "November", "December",
    }  # fmt: skip


def test_message_americain(maison):
    maison("fr")
    assert appel({"rh": "", "localisation": "Austin, TX"}, "en") == "Dear Hiring Manager,"
    assert appel({"rh": "", "localisation": "Dublin, Ireland"}, "en") == "Dear Sir or Madam,"
    assert appel({"rh": "", "localisation": "Austin, TX"}, "fr") == "Madame, Monsieur,"


@pytest.mark.parametrize(
    "titre, attendu",
    [
        ("Part-time Registered Nurse", "Temps partiel"),
        ("Infirmier à temps partiel", "Temps partiel"),
        ("Data Analyst (Contract)", "CDD"),
        ("Contract Manager", ""),  # a job, not a contract
        ("Seasonal Ski Instructor", "Saisonnier"),
    ],
)
def test_contrat_du_titre(titre, attendu):
    assert contrat_du_titre(titre) == attendu


@pytest.mark.parametrize(
    "texte, attendu",
    [
        ("Job Type: Part-time. Pay: $30 per hour.", "Temps partiel"),
        ("Employment type: Internship (summer).", "Stage"),
        ("Job type: Temporary, 6 months.", "CDD"),
        ("Position type: Permanent.", "CDI"),
        ("Type de contrat : CDI.", "CDI"),
    ],
)
def test_contrat_de_la_description(texte, attendu):
    assert contrat_de_la_description("Description du poste. " * 4 + texte) == attendu
