"""tri_file's removal reasons: quant, data engineering, heavy tooling, duplicates,
non-offers, student; and the tracker's protection. Converted from Scripts/test_tri_file.py.
"""

import pytest

from jobhunter.programs import duplicates as D
from jobhunter.scoring import sorting as T


def m(titre, desc="", **kw):
    # A default offer link: without it, every row would be "sans lien".
    kw.setdefault("url", "https://www.linkedin.com/jobs/view/1")
    return T.motif({"poste": titre, "description": desc, **kw}, set())


LOURD = "Stack : Kubernetes, Terraform, CI/CD, PyTorch, LangChain, AWS."

MOTIFS = [
    # quant: removed, even with ESG in the title
    ("Analyste Climate Finance / Green Bonds / ESG Quant", "", "metier:quant"),
    ("Quantitative Risk Analyst", "", "metier:quant"),
    ("Analyste Quantitatif Risques (F/H)", "", "metier:quant"),
    ("Quant Research Analyst", "", "metier:quant"),
    ("Quantitative Structurer", "", "metier:quant"),
    ("Consultant Junior – Analyste Finance Quantitative", "", "metier:quant"),
    ("Quantity Surveyor ESG", "", None),
    ("Restructuring Analyst ESG", "", None),
    ("Analyste ESG", "", None),
    # ingenierie data : retiree, meme ESG
    ("ESG Data Engineer", "", "metier:ingenierie_data"),
    ("Data Engineer & Analyst – Climate Risk", "", "metier:ingenierie_data"),
    ("Ingénieur Data Climat (H/F)", "", "metier:ingenierie_data"),
    ("Analytics Engineer Sustainability", "", "metier:ingenierie_data"),
    ("Data Analyst ESG", "", None),
    # AI engineer kept, except heavy tooling
    ("AI Engineer", "Python, LLM, agents, prompts.", None),
    ("AI Engineer", LOURD, "outils_techniques"),
    (
        "Sustainability Data & AI Solutions Analyst",
        "FastAPI, PostgreSQL, CI/CD, AWS",
        "outils_techniques",
    ),
    ("AI Analyst", "Databricks, Snowflake, Azure", None),  # 3 families: below the threshold
    # student asked for: removed, even as a V.I.E; a degree accepted: kept
    (
        "Finance Leadership Development Program",
        "Are you a fresh graduate or final-year student in Finance?",
        None,
    ),
    (
        "Consultant(e) junior – CDI",
        "Tu étais étudiant(e) en école de commerce, à la recherche d'un premier poste.",
        None,
    ),
]


@pytest.mark.parametrize(("titre", "desc", "attendu"), MOTIFS, ids=[t for t, _, _ in MOTIFS])
def test_motif(titre, desc, attendu):
    assert m(titre, desc) == attendu


def test_vie_pour_etudiant_retire():
    desc = "Profile Final or penultimate year student from a Tier 1 university."
    assert m("VIE - ESG & Sustainable Finance Analyst", desc, contrat="V.I.E") == "etudiant"


@pytest.mark.parametrize(
    ("texte", "attendu"),
    [
        ("AWS, GCP ou Azure", {"cloud"}),  # a single family
        ("Python, SQL, Excel, VBA, Power BI, Tableau, git", set()),  # outils d'analyste
        ("JavaScript", {"javascript"}),  # not Java
        ("git, GitHub, Python, Excel, Power BI, PowerPoint, VBA, Power Automate", set()),
        ("Maîtrise du langage C", {"c"}),
        ("Python, C, Rust", {"c", "rust"}),
        ("C/C++", {"c"}),
        ("C'est un poste ESG, catégorie C.", set()),  # "C'est" is not the language
        (".NET, voir www.acme.net", {"dotnet"}),  # a .net domain is not
        ("messages SWIFT et paiements", set()),  # SWIFT bancaire
    ],
)
def test_outils_techniques(texte, attendu):
    assert T.outils_techniques(texte) == attendu


# ── the tracker always protects ──────────────────────────────────────────────────
@pytest.mark.parametrize(
    ("offre", "suivi"),
    [
        ({"entreprise": "BNP", "poste": "ESG Quant", "description": LOURD}, {"BNP|ESG Quant"}),
        (
            {
                "entreprise": "Euronext",
                "poste": "VIE ESG",
                "url": "https://www.linkedin.com/jobs/view/1",
                "description": "Final year student wanted.",
            },
            {"Euronext|VIE ESG"},
        ),
        ({"entreprise": "Covéa", "poste": "Analyste ESG", "url": ""}, {"Covéa|Analyste ESG"}),
    ],
    ids=["quant outille", "etudiant", "sans lien"],
)
def test_offre_suivie_jamais_retiree(offre, suivi):
    assert T.motif(offre, suivi) is None


# ── doublons ───────────────────────────────────────────────────────────────────
def _oid(o):
    return f"{o['entreprise']}|{o['poste']}"


def dbl(*offres, proteges=frozenset()):
    rang = lambda u: 3 if "linkedin" not in (u or "") else 0  # noqa: E731
    return set(D.doublons(list(offres), proteges, rang, _oid))


EN = (
    "At ABB we help industries. You will report to the EU Taxonomy lead. CSRD, LCA, EPD, "
    "ISO 14001, REACH, RoHS, 2026, 40 % of the time with the team and our partners."
)
DE = (
    "Bei ABB unterstützen wir die Industrie. Sie berichten an die EU Taxonomie. CSRD, LCA, "
    "EPD, ISO 14001, REACH, RoHS, 2026, 40 % der Zeit und wir sind für Sie da."
)
ABB_EN = {
    "entreprise": "ABB",
    "poste": "Product Sustainability & EU Taxonomy Specialist (f/m/d)",
    "localisation": "Eggelsberg, Upper Austria",
    "description": EN,
    "url": "https://linkedin/1",
    "fit": 10,
}
ABB_DE = {
    "entreprise": "ABB",
    "poste": "Spezialist:in Produktnachhaltigkeit & EU-Taxonomie (w/m/d)",
    "localisation": "Eggelsberg, Upper Austria",
    "description": DE,
    "url": "https://linkedin/2",
    "fit": 10,
}
ONEPOINT_LI = {
    "entreprise": "Onepoint",
    "poste": "Consultant en Transformation Finance - F/H",
    "localisation": "Paris, Île-de-France",
    "url": "https://linkedin/3",
}
ONEPOINT_SITE = {
    "entreprise": "Onepoint",
    "poste": "Consultant Transformation Finance F/H",
    "localisation": "Paris - 75",
    "url": "https://onepoint.fr/jobs/9",
}


def test_traduction_en_de_la_version_allemande_part():
    assert dbl(ABB_EN, ABB_DE) == {_oid(ABB_DE)}


def test_meme_traduction_autre_ville_deux_postes():
    assert dbl(ABB_EN, {**ABB_DE, "localisation": "Wien"}) == set()


def test_mots_vides_pres_garde_le_site_employeur():
    assert dbl(ONEPOINT_LI, ONEPOINT_SITE) == {_oid(ONEPOINT_LI)}


def test_deux_filieres_pas_doublon():
    e1 = {
        "entreprise": "Fifth Third",
        "localisation": "Cincinnati",
        "poste": "Finance and Accounting Leadership Program: Accounting",
    }
    assert dbl(e1, {**e1, "poste": "Finance and Accounting Leadership Program: Finance"}) == set()


def test_titres_non_latins_jamais_confondus():
    z1 = {"entreprise": "EY", "poste": "【ESG服務】社會組 - 顧問", "localisation": "Taipei"}
    assert dbl(z1, {**z1, "poste": "【ESG服務】環境組 - 顧問"}) == set()


def test_le_suivi_garde_son_offre():
    assert dbl(ONEPOINT_LI, ONEPOINT_SITE, proteges={_oid(ONEPOINT_LI)}) == {_oid(ONEPOINT_SITE)}


# ── what is not an offer ─────────────────────────────────────────────────
@pytest.mark.parametrize(
    ("url", "attendu"),
    [
        ("", "pas_une_offre:sans_lien"),
        ("https://www.ecocert.com/fr-FR/home", "pas_une_offre:accueil_ou_portail"),
        ("https://careers.societegenerale.com", "pas_une_offre:accueil_ou_portail"),
        ("https://meeschaert.com/carrieres/recrutement/", "pas_une_offre:accueil_ou_portail"),
        ("https://careers.smartrecruiters.com/SycomoreAssetManagement", "pas_une_offre:portail"),
        ("https://fr.indeed.com/q-analyste-esg-junior-emplois.html", "pas_une_offre:recherche"),
        ("https://fr.linkedin.com/jobs/analyste-esg-emplois", "pas_une_offre:recherche"),
        ("https://www.linkedin.com/jobs/view/4472756804", None),
        ("https://jobs.smartrecruiters.com/scalian/744000139977123", None),
        ("https://recrutement.natixis.com/job/analyste-impact-et-esg-f", None),
        ("https://fr.indeed.com/viewjob?jk=9c0aac3268fdc4c2", None),
    ],
)
def test_pas_une_offre(url, attendu):
    assert T.pas_une_offre({"url": url}) == attendu


def test_ligne_recherche_sans_lien_retiree():
    assert m("Analyste ESG", url="", url_type="RECHERCHE") == "pas_une_offre:sans_lien"
