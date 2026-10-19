"""What the letter decides on its own (tailor_application, verifie_redites, langue), without network.

1. The closing echo answers the greeting and agrees ("Messieurs" for two men).
2. The agricultural paragraph: a MENTION is not a SUBJECT, and "CREDIT AGRICOLE"
   contains "agricol" (91 offers wrongly kept in the first measurement).
3. The title loses the company's name.
4. The hand-written body is found by its name (the failure was SILENT).
5. verifie_redites cuts the header whatever the greeting.
6. The document's language follows the PLACE when the text is silent.
Converted from Scripts/test_lettre.py.
"""

import pytest

from jobhunter import profil
from jobhunter.documents import (
    _sans_societe,
    _slug,
    contexte_agricole,
    corps_sur_mesure,
    salutation,
)
from jobhunter.documents.relecture import corps
from jobhunter.scoring.langue import langue_offre

_AGRI = next(c for c in profil.get("lettre.contextes") if c["nom"] == "agricole")
AGRI_FR, AGRI_EN = _AGRI["fr"], _AGRI["en"]
GENERIQUE = "Madame, Monsieur"


# ── the closing echo answers the greeting ─────────────────────────────────────
@pytest.mark.parametrize(
    ("rh", "langue", "attendu"),
    [
        ("Monsieur Louis Mac Arthur et Monsieur Clément Lebrun", "fr", "Messieurs"),
        ("Madame Awa MOUSSA et Madame Mélanie GIRARD", "fr", "Mesdames"),
        ("Madame Awa MOUSSA et Monsieur Charles DE GAULLE", "fr", GENERIQUE),  # mixte
        ("Monsieur KEVIN SILVA PEREIRA", "fr", "Monsieur"),
        ("Madame Awa MOUSSA", "fr", "Madame"),
        ("", "fr", GENERIQUE),
        ("Service Recrutement", "fr", GENERIQUE),
        # English does not echo the title of address: it closes with "Yours sincerely"
        ("Monsieur Louis Mac Arthur", "en", "Sir or Madam"),
    ],
)
def test_reprise_de_cloture(rh, langue, attendu):
    assert salutation({"rh": rh}, langue)[1] == attendu


# "Yours faithfully" if the recipient is unknown, "Yours sincerely" if they are
# named; the English letter hard-coded "faithfully".
@pytest.mark.parametrize(
    ("rh", "langue", "attendu"),
    [
        ("Monsieur Louis Mac Arthur", "en", True),
        ("", "en", False),
        ("https://www.linkedin.com/search/results/people/?q=rh", "fr", False),
    ],
    ids=["nom connu", "champ vide", "URL LinkedIn"],
)
def test_nomme(rh, langue, attendu):
    assert salutation({"rh": rh}, langue)[2] is attendu


# ── the agricultural paragraph ─────────────────────────────────────────────────────
def agri(role="", texte="", societe="", langue="fr"):
    offre = dict(company=societe, role=role, offer_text=texte, missions="", profil="")
    return contexte_agricole(offre, langue)


TROIS_OCCURRENCES = (
    "Le fonds investit dans des terres agricoles et des pratiques agricoles "
    "régénératrices, avec un volet forestier."
)
CREDIT_AGRICOLE = (
    "Crédit Agricole CIB recherche un analyste. Le Crédit Agricole est un groupe "
    "bancaire. Crédit Agricole S.A. emploie…"
)

AGRI = [
    # the title is sovereign
    ("Analyste Investissement - Capital Naturel", "", "", "fr", AGRI_FR),
    ("Investment Analyst - Natural Capital", "", "", "en", AGRI_EN),
    ("Analyste Agroalimentaire", "", "", "fr", AGRI_FR),
    ("Specialist - Regenerative Agriculture", "", "", "fr", AGRI_FR),
    ("Analyste Risques Engagements", "", "", "fr", ""),
    # a mention is not a subject
    (
        "Contrôleur de gestion",
        "Nos clients vont de l'agroalimentaire à l'aéronautique.",
        "",
        "fr",
        "",
    ),
    ("Contrôleur de gestion", "Secteurs : agroalimentaire, forestier, aéronautique.", "", "fr", ""),
    ("Analyste financier", TROIS_OCCURRENCES, "", "fr", AGRI_FR),
    # « CREDIT AGRICOLE » contient « agricol »
    ("Analyste risque de liquidité H/F", CREDIT_AGRICOLE, "Crédit Agricole CIB", "fr", ""),
    (
        "Analyste Risques",
        "CREDIT AGRICOLE SA, credit agricole, Credit-Agricole",
        "CREDIT AGRICOLE SA",
        "fr",
        "",
    ),
    ("Analyste risques engagements - marché agricole", "", "Crédit Mutuel", "fr", AGRI_FR),
]


@pytest.mark.parametrize(("role", "texte", "societe", "langue", "attendu"), AGRI)
def test_paragraphe_agricole(role, texte, societe, langue, attendu):
    assert agri(role, texte, societe, langue) == attendu


# ── the title loses the company's name ─────────────────────────────────────────
@pytest.mark.parametrize(
    ("titre", "societe", "attendu"),
    [
        (
            "Analyste Investissement - Capital Naturel - Mirova",
            "Mirova",
            "Analyste Investissement - Capital Naturel",
        ),
        ("Fraud & Risk Specialist (H/F) @Chargemap", "Chargemap", "Fraud & Risk Specialist (H/F)"),
        (
            "Analyst, Investment Operations | PGIM Ireland",
            "PGIM Ireland",
            "Analyst, Investment Operations",
        ),
        ("Data Scientist - tiktok", "TikTok", "Data Scientist"),
        ("Analyste ESG / Impact ESG", "Mirova", "Analyste ESG / Impact ESG"),
        ("Mirova", "Mirova", "Mirova"),  # a title reduced to the name does not become empty
        ("Analyste - Mirova", "", "Analyste - Mirova"),
        # a hyphen in a word is not a separator ("F - Gas" at Aggreko)
        (
            "F-Gas & Sustainability Analyst (H/F)",
            "AGGREKO FRANCE",
            "F-Gas & Sustainability Analyst (H/F)",
        ),
        ("Analyste LCB-FT - Mirova", "Mirova", "Analyste LCB-FT"),
    ],
)
def test_sans_societe(titre, societe, attendu):
    assert _sans_societe(titre, societe) == attendu


# ── the hand-written body is found by its name ───────────────────────────
# The key must go through _slug ENTIRELY, like the file name: two slugs
# around a literal "__" never found the file, without error.
def cle(societe, poste):
    return _slug(f"{societe}__{poste}")


def test_cle_vaut_le_nom_de_fichier():
    poste = "Analyste Investissement - Capital Naturel - Mirova"
    assert cle("Mirova", poste) == _slug(f"Mirova__{poste}")


def test_ponctuation_et_casse_sans_effet():
    assert cle("MIROVA (Natixis)", "Analyste ESG / Impact") == _slug(
        "mirova-natixis__analyste_esg_impact"
    )


def test_accents_deux_orthographes_distinctes():
    assert cle("Société X", "Chargé d'études") != cle("Societe X", "Charge d'etudes")


def test_sans_fichier_le_gabarit_reprend_la_main():
    offre = dict(company="Entreprise Inexistante 4242", role="Poste Imaginaire")
    assert corps_sur_mesure(offre) == []


# ── verifie_redites cuts the header, whatever the greeting ────────────────
EN_TETE = (
    "Camille Exemple\ncamille.exemple@example.com\n+33 6 00 00 00 00\n"
    "Le 21 septembre 2026\nObjet : Candidature au poste d'analyste\n"
)


@pytest.mark.parametrize(
    "appel",
    [
        "Madame, Monsieur,",
        "Dear Sir or Madam,",
        "Monsieur Mac Arthur,",
        "Monsieur Mac Arthur, Monsieur Lebrun,",
        "Madame Moussa, Madame Girard,",
        "Dear Mr Mac Arthur and Mr Lebrun,",
        "Bonjour,",
    ],
)
def test_en_tete_coupe(appel):
    assert corps(EN_TETE + appel + "\nLe corps commence ici.").strip() == "Le corps commence ici."


def test_formule_inconnue_on_ne_perd_pas_le_corps():
    # better too much text than an empty body, which would let any repetition through
    assert "Le corps commence ici." in corps(EN_TETE + "Salut,\nLe corps commence ici.")


# ── the language follows the PLACE when the text is silent ─────────────────────────────
# 1,809 foreign offers out of 1,814 were classified "fr" (2026-09-22).
@pytest.mark.parametrize(
    ("titre", "lieu", "attendu"),
    [
        ("Sustainability Analyst", "Stockholm, Sweden", "en"),
        ("(Junior) Consultant ESG Assurance", "Frankfurt, Germany", "en"),
        ("Analista de Sostenibilidad", "Madrid, Spain", "en"),
        ("ESG Analyst", "Singapore", "en"),
        ("Analyste ESG", "Paris, France", "fr"),
        ("Analyste ESG", "Bordeaux · Nouvelle-Aquitaine", "fr"),
        ("ESG Analyst", "Luxembourg", "fr"),
        ("Analyste ESG", "Grenoble (38) · Auvergne-Rhône-Alpes", "fr"),
        ("Gestionnaire des risques", "33700 Mérignac · Nouvelle-Aquitaine", "fr"),
        # Switzerland does not have a single working language: the place decides
        ("ESG Analyst", "Geneva, Switzerland", "fr"),
        ("ESG Analyst", "Zurich, Switzerland", "en"),
        ("ESG Analyst", "Basel, Switzerland", "en"),
        ("ESG Analyst", "", "fr"),  # without a place, French gets the benefit of the doubt
    ],
)
def test_langue_par_le_lieu(titre, lieu, attendu):
    assert langue_offre(titre, "", lieu) == attendu


def test_texte_long_tranche_seul():
    texte = (
        "We are looking for the analyst who will be in charge of the reporting and of "
        "the data, with a strong interest in the regulation and in all of our climate "
        "work, and you will be part of a team that is growing fast in our group. "
    )
    assert langue_offre("Analyste", texte, "Paris, France") == "en"
