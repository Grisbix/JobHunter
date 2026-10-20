"""The message's named greeting (message_offre.appel), without network.

The `rh` field carries a URL in 413 offers out of 416: code that took it
for a name would write "Bonjour https://www.linkedin.com/search...".
Converted from Scripts/test_message_greeting.py.
"""

import pytest

from jobhunter.documents.message import _nom_propre, _patronyme, appel, nom_dans_offre


def a(rh, langue="fr", ton="sobre"):
    return appel({"rh": rh}, langue, ton)


GENERIQUE_FR, GENERIQUE_EN = "Madame, Monsieur,", "Dear Sir or Madam,"

APPELS = [
    # the three real names of the queue
    ("Monsieur KEVIN SILVA PEREIRA", "fr", "sobre", "Monsieur Silva Pereira,"),
    ("Monsieur KEVIN SILVA PEREIRA", "en", "sobre", "Dear Mr Silva Pereira,"),
    ("Madame Awa MOUSSA", "fr", "sobre", "Madame Moussa,"),  # capitals = the surname
    ("Madame Mélanie GIRARD", "fr", "sobre", "Madame Girard,"),
    # particles: nobiliary ones lowercase, articles capitalised ("De Gaulle" is a mistake,
    # "Le Pen" is not)
    ("Monsieur JEAN-PIERRE DE LA TOUR", "fr", "sobre", "Monsieur de La Tour,"),
    ("Monsieur CHARLES DE GAULLE", "fr", "sobre", "Monsieur de Gaulle,"),
    ("Madame Marine LE PEN", "fr", "sobre", "Madame Le Pen,"),
    ("Mrs Sarah VAN DEN BERG", "fr", "sobre", "Madame van den Berg,"),
    ("M. Joao DOS SANTOS", "fr", "sobre", "Monsieur dos Santos,"),
    ("Mr PATRICK O'BRIEN", "en", "sobre", "Dear Mr O'Brien,"),
    # what is NOT a person (the most frequent case)
    ("https://www.linkedin.com/search/results/people/?keywords=RH", "fr", "sobre", GENERIQUE_FR),
    ("https://www.linkedin.com/search/results/people/?keywords=RH", "en", "sobre", GENERIQUE_EN),
    ("", "fr", "sobre", GENERIQUE_FR),
    ("Service Recrutement", "en", "sobre", GENERIQUE_EN),
    ("Talent Acquisition Team", "en", "sobre", GENERIQUE_EN),
    ("Direction des Ressources Humaines", "en", "sobre", GENERIQUE_EN),
    ("recrutement@societe.fr", "en", "sobre", GENERIQUE_EN),
    # gender cannot be guessed from a first name; English addresses the full name
    ("Kevin Silva Pereira", "fr", "sobre", GENERIQUE_FR),
    ("Kevin Silva Pereira", "en", "sobre", "Dear Kevin Silva Pereira,"),
    # the relaxed tone keeps its form
    ("", "fr", "detente", "Bonjour,"),
    ("Monsieur KEVIN SILVA PEREIRA", "fr", "detente", "Monsieur Silva Pereira,"),
    # several recipients in the same field (Mirova: "a Louis Mac Arthur et
    # Clement Lebrun" was taken for ONE surname)
    (
        "Monsieur Louis Mac Arthur et Monsieur Clément Lebrun",
        "fr",
        "sobre",
        "Monsieur Mac Arthur, Monsieur Lebrun,",
    ),
    (
        "Monsieur Louis Mac Arthur et Monsieur Clément Lebrun",
        "en",
        "sobre",
        "Dear Mr Mac Arthur and Mr Lebrun,",
    ),
    ("Madame Awa MOUSSA et Madame Mélanie GIRARD", "fr", "sobre", "Madame Moussa, Madame Girard,"),
    (
        "Madame Awa MOUSSA et Monsieur Charles DE GAULLE",
        "fr",
        "sobre",
        "Madame Moussa, Monsieur de Gaulle,",
    ),
    (
        "Monsieur Charles DE GAULLE & Madame Marine LE PEN",
        "fr",
        "sobre",
        "Monsieur de Gaulle, Madame Le Pen,",
    ),
    # a silent chunk is DROPPED, not propagated ("Monsieur Et Marie Dupont")
    ("Monsieur Jean et Marie Dupont", "fr", "sobre", "Monsieur Jean,"),
    ("Monsieur Louis Mac Arthur / Service Recrutement", "fr", "sobre", "Monsieur Mac Arthur,"),
    ("Service Recrutement et Direction RH", "fr", "sobre", GENERIQUE_FR),
    # the URL is tested BEFORE splitting: its slashes are a separator
    ("https://www.linkedin.com/search/results/people/?keywords=RH", "fr", "sobre", GENERIQUE_FR),
]


@pytest.mark.parametrize(("rh", "langue", "ton", "attendu"), APPELS)
def test_appel(rh, langue, ton, attendu):
    assert a(rh, langue, ton) == attendu


@pytest.mark.parametrize(
    ("nom", "attendu"),
    [("GARCIA-LOPEZ", "Garcia-Lopez"), ("McDonald", "McDonald")],
    ids=["trait d'union", "casse posee a la main respectee"],
)
def test_nom_propre(nom, attendu):
    assert _nom_propre(nom) == attendu


@pytest.mark.parametrize(
    ("brut", "attendu"),
    [("KEVIN SILVA PEREIRA", "Silva Pereira"), ("Awa MOUSSA", "Moussa"), ("MOUSSA", "Moussa")],
    ids=["tout capitales", "casse mixte", "un seul mot"],
)
def test_patronyme(brut, attendu):
    assert _patronyme(brut) == attendu


# ── name absent from the posting: not named (2026-10-07) ───────────────────────────
@pytest.mark.parametrize(
    ("rh", "texte", "attendu"),
    [
        ("Madame Maria LOPEZ", "VIE Sustainability PMO", ""),
        (
            "Madame Audrey Durand",
            "Contact : Audrey DURAND, chargée de recrutement",
            "Madame Audrey Durand",
        ),
        ("Monsieur Hélène Dupré", "écrire à M. Dupre", "Monsieur Hélène Dupré"),  # accents
        ("Madame X", "Madame, Monsieur", ""),  # the title of address alone does not count
    ],
)
def test_nom_dans_offre(rh, texte, attendu):
    assert nom_dans_offre(rh, texte) == attendu


def test_offre_sans_le_nom_generique():
    offre = {"rh": "Madame Maria LOPEZ", "poste": "PMO", "description": "Budapest"}
    assert appel(offre) == GENERIQUE_FR


def test_offre_qui_nomme_nominatif():
    offre = {"rh": "Madame Maria Lopez", "poste": "PMO", "description": "Contact : Maria Lopez"}
    assert appel(offre) == "Madame Lopez,"
