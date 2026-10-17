"""La formule d'appel nominative du message (message_offre.appel), sans reseau.

Le champ `rh` porte une URL dans 413 offres sur 416 : un code qui le prendrait
pour un nom ecrirait « Bonjour https://www.linkedin.com/search... ».
Converti depuis Scripts/test_appel.py.
"""

import pytest

from message_offre import _nom_propre, _patronyme, appel, nom_dans_offre


def a(rh, langue="fr", ton="sobre"):
    return appel({"rh": rh}, langue, ton)


GENERIQUE_FR, GENERIQUE_EN = "Madame, Monsieur,", "Dear Sir or Madam,"

APPELS = [
    # les trois noms reels de la file
    ("Monsieur KEVIN SILVA PEREIRA", "fr", "sobre", "Monsieur Silva Pereira,"),
    ("Monsieur KEVIN SILVA PEREIRA", "en", "sobre", "Dear Mr Silva Pereira,"),
    ("Madame Awa MOUSSA", "fr", "sobre", "Madame Moussa,"),  # les capitales = le patronyme
    ("Madame Mélanie GIRARD", "fr", "sobre", "Madame Girard,"),
    # particules : nobiliaires en bas, articles en haut (« De Gaulle » est une faute,
    # « Le Pen » non)
    ("Monsieur JEAN-PIERRE DE LA TOUR", "fr", "sobre", "Monsieur de La Tour,"),
    ("Monsieur CHARLES DE GAULLE", "fr", "sobre", "Monsieur de Gaulle,"),
    ("Madame Marine LE PEN", "fr", "sobre", "Madame Le Pen,"),
    ("Mrs Sarah VAN DEN BERG", "fr", "sobre", "Madame van den Berg,"),
    ("M. Joao DOS SANTOS", "fr", "sobre", "Monsieur dos Santos,"),
    ("Mr PATRICK O'BRIEN", "en", "sobre", "Dear Mr O'Brien,"),
    # ce qui N'EST PAS une personne (le cas le plus frequent)
    ("https://www.linkedin.com/search/results/people/?keywords=RH", "fr", "sobre", GENERIQUE_FR),
    ("https://www.linkedin.com/search/results/people/?keywords=RH", "en", "sobre", GENERIQUE_EN),
    ("", "fr", "sobre", GENERIQUE_FR),
    ("Service Recrutement", "en", "sobre", GENERIQUE_EN),
    ("Talent Acquisition Team", "en", "sobre", GENERIQUE_EN),
    ("Direction des Ressources Humaines", "en", "sobre", GENERIQUE_EN),
    ("recrutement@societe.fr", "en", "sobre", GENERIQUE_EN),
    # le genre ne se devine pas d'un prenom ; l'anglais s'adresse au nom complet
    ("Kevin Silva Pereira", "fr", "sobre", GENERIQUE_FR),
    ("Kevin Silva Pereira", "en", "sobre", "Dear Kevin Silva Pereira,"),
    # le ton detendu garde sa forme
    ("", "fr", "detente", "Bonjour,"),
    ("Monsieur KEVIN SILVA PEREIRA", "fr", "detente", "Monsieur Silva Pereira,"),
    # plusieurs destinataires dans le meme champ (Mirova : « a Louis Mac Arthur et
    # Clement Lebrun » etait pris pour UN patronyme)
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
    # un morceau muet est ECARTE, pas propage (« Monsieur Et Marie Dupont »)
    ("Monsieur Jean et Marie Dupont", "fr", "sobre", "Monsieur Jean,"),
    ("Monsieur Louis Mac Arthur / Service Recrutement", "fr", "sobre", "Monsieur Mac Arthur,"),
    ("Service Recrutement et Direction RH", "fr", "sobre", GENERIQUE_FR),
    # l'URL se teste AVANT la decoupe : ses barres obliques sont un separateur
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


# ── nom absent de l'annonce : pas nomme (2026-10-07) ───────────────────────────
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
        ("Madame X", "Madame, Monsieur", ""),  # la civilite seule ne compte pas
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
