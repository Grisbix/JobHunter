"""Deduction du type de contrat (job_sources), et ses faux positifs.

Converti depuis Scripts/test_contrats.py. Les phrases « etudiant » sont des
phrases reelles de la file (2026-10-04).
"""

import pytest

from job_sources import contrat_de_la_description, contrat_du_titre

PAR_TITRE = [
    # acronymes francais
    ("CDI - Analyste DSI H/F - Paris", "CDI"),
    ("Business Analyst Risque de Crédit / CDI / H/F", "CDI"),
    ("Group Environmental Transition Analyst (F/H) CDI", "CDI"),
    ("ANALYSTE RISQUES CDD - 12 mois H/F", "CDD"),
    ("CDD - Analyste Trade Compliance H/F", "CDD"),
    ("Risk Analyst - AI Trainer - Freelance - Remote", "Freelance"),
    ("Consultant en intérim management", "Interim"),
    # libelles anglais
    ("Sustainability Manager - Permanent", "CDI"),
    ("Analyste Fixed Term - 6 mois", "CDD"),
    ("Analyste Fixed Income", ""),  # Fixed Income n'est PAS un contrat
    ("Analyst - Full-time", ""),  # un rythme, pas un contrat
    # l'etudiant passe avant tout le reste
    ("Stage Analyste M&A (puis VIE/CDI)", "Stage"),
    ("Alternance Analyste ESG - CDI à la clé", "Alternance"),
    ("V.I.E - Analyste Finance", "V.I.E"),
    # faux positifs : aucun contrat ne doit sortir
    ("Analyste ESG H/F", ""),
    ("Chargé de mission développement durable", ""),
    ("Chargé de vie associative", ""),
    ("Assurance vie - Gestionnaire", ""),
    ("ANALYSTE CYCLE DE VIE HABILLEMENT", ""),
    ("Analyste Fixed Income", ""),
    # un poste etudiant est un stage
    ("Working Student - Supplier Sustainability (f/m/div)", "Stage"),
    ("Werkstudent:in AXA Asset Management", "Stage"),
]


@pytest.mark.parametrize(("titre", "attendu"), PAR_TITRE, ids=[t[:40] for t, _ in PAR_TITRE])
def test_contrat_du_titre(titre, attendu):
    assert contrat_du_titre(titre) == attendu


SOCLE = "Rejoignez notre equipe. " * 6

PAR_DESCRIPTION = [
    # libelle structure
    ("Type de contrat : CDI. Poste base a Paris.", "CDI"),
    ("Contrat : Alternance de 24 mois.", "Alternance"),
    # pieges deja rencontres
    ("Vous avez une experience en alternance ou en poste.", ""),  # experience, pas contrat
    ("Nous investissons dans des startups early stage.", ""),  # phase d'entreprise
    ("Vous gerez les contrats prestataires et commandes.", ""),  # les clients
    # un poste qui demande un etudiant est un stage
    ("Et si c'était vous ? Vous êtes étudiant en Bac +4/5, avec une spécialisation ESG.", "Stage"),
    ("Qui êtes vous ? Étudiant(e) en dernière année d'école d'ingénieur ou Master 2.", "Stage"),
    ("Étudiant en fin d’études ou en année de césure au sein d’une école de commerce.", "Stage"),
    (
        "Vous êtes étudiant de niveau Bac +5 en École de Commerce, d'Ingénieur ou Université.",
        "Stage",
    ),
    ("Requirements: Currently pursuing a Bachelor’s or Master’s degree in Finance.", "Stage"),
    (
        "Final or penultimate year student from a Tier 1 university, business or engineering "
        "school.",
        "Stage",
    ),
    ("Candidates must be enrolled at one of the following universities to be considered.", "Stage"),
    ("Vous êtes étudiant en master, en vue de l'obtention du diplôme d'ingénieur.", "Stage"),
    ("Contrat : CDD. Vous êtes étudiant en master.", "Stage"),  # l'etudiant l'emporte
    # le diplome est accepte : ce n'est pas un stage
    (
        "We're looking for individuals currently pursuing (or already holding) a relevant "
        "master's degree.",
        "",
    ),
    ("For final year students or recent graduates with a bachelor’s or master’s degree.", ""),
    ("Master's degree (Bac+5) or final-year student in Engineering or Sustainability.", ""),
    ("Bachelor's degree (or currently pursuing a degree) in Political Science.", ""),
    ("Higher education or currently studying in finance or economics.", ""),
    ("Étudiant en dernière année ou jeune diplômé d'une école de commerce.", ""),
    # un passe demande, pas un statut
    ("Erste Erfahrungen durch Praktika oder Werkstudententätigkeiten im Finanzbereich.", ""),
    ("Relevant experience through internships, working student roles, or research projects.", ""),
    # hors sujet
    ("Candidates currently pursuing certification may also be considered.", ""),
    ("Nous accompagnons les étudiants et les entreprises dans leur transition.", ""),
]


@pytest.mark.parametrize(
    ("phrase", "attendu"), PAR_DESCRIPTION, ids=[p[:40] for p, _ in PAR_DESCRIPTION]
)
def test_contrat_de_la_description(phrase, attendu):
    assert contrat_de_la_description(SOCLE + phrase) == attendu


def test_description_trop_courte():
    assert contrat_de_la_description("CDI") == ""
