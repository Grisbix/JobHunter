#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_tri_file.py — Motifs de retrait de tri_file : quant, ingenierie data,
trop d'outils de developpement (regles de l'utilisateur du 2026-10-05).

Intitules tires de la file reelle. Sans reseau.

Run : python test_tri_file.py
"""

import _profil_test  # noqa: F401  — les tests tournent sur le profil d'exemple
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import tri_file as T

ok = ko = 0


def check(nom, obtenu, attendu):
    global ok, ko
    if obtenu == attendu:
        ok += 1
        print(f"  ✅ {nom}")
    else:
        ko += 1
        print(f"  ❌ {nom}\n       obtenu {obtenu!r}, attendu {attendu!r}")


def m(titre, desc="", **kw):
    # Un lien d'offre par defaut : sans lui, toute ligne serait « sans lien ».
    kw.setdefault("url", "https://www.linkedin.com/jobs/view/1")
    return T.motif({"poste": titre, "description": desc, **kw}, set())


print("\n── A. quant : retire, meme avec ESG dans le titre ──")
for t in [
    "Analyste Climate Finance / Green Bonds / ESG Quant",
    "Quantitative Risk Analyst",
    "Analyste Quantitatif Risques (F/H)",
    "Quant Research Analyst",
    "Quantitative Structurer",
    "Consultant Junior – Analyste Finance Quantitative",
]:
    check(t, m(t), "metier:quant")
for t in ["Quantity Surveyor ESG", "Restructuring Analyst ESG", "Analyste ESG"]:
    check("pas quant : " + t, m(t), None)

print("\n── B. ingenierie data : retiree, meme ESG ──")
for t in [
    "ESG Data Engineer",
    "Data Engineer & Analyst – Climate Risk",
    "Ingénieur Data Climat (H/F)",
    "Analytics Engineer Sustainability",
]:
    check(t, m(t), "metier:ingenierie_data")
check("Data Analyst ESG reste", m("Data Analyst ESG"), None)

print("\n── C. AI engineer garde, sauf outillage lourd ──")
check("AI Engineer sans outillage : garde", m("AI Engineer", "Python, LLM, agents, prompts."), None)
lourd = "Stack : Kubernetes, Terraform, CI/CD, PyTorch, LangChain, AWS."
check("AI Engineer outillage lourd : retire", m("AI Engineer", lourd), "outils_techniques")
check(
    "analyste avec outillage lourd : retire aussi",
    m("Sustainability Data & AI Solutions Analyst", "FastAPI, PostgreSQL, CI/CD, AWS"),
    "outils_techniques",
)

print("\n── D. comptage des familles d'outils ──")
check("AWS, GCP et Azure = une famille", T.outils_techniques("AWS, GCP ou Azure"), {"cloud"})
check(
    "outils d'analyste non comptes",
    T.outils_techniques("Python, SQL, Excel, VBA, Power BI, Tableau, git"),
    set(),
)
check("JavaScript n'est pas Java", T.outils_techniques("JavaScript"), {"javascript"})
check(
    "tes outils ne comptent pas (git, PowerPoint, VBA…)",
    T.outils_techniques("git, GitHub, Python, Excel, Power BI, PowerPoint, VBA, Power Automate"),
    set(),
)
check("langage C compte", T.outils_techniques("Maîtrise du langage C"), {"c"})
check("C dans une liste de langages", T.outils_techniques("Python, C, Rust"), {"c", "rust"})
check("C/C++ = une seule famille", T.outils_techniques("C/C++"), {"c"})
check(
    "« C'est » n'est pas le langage C",
    T.outils_techniques("C'est un poste ESG, catégorie C."),
    set(),
)
check(
    ".NET compte, un domaine en .net non",
    T.outils_techniques(".NET, voir www.acme.net"),
    {"dotnet"},
)
check(
    "SWIFT bancaire n'est pas le langage", T.outils_techniques("messages SWIFT et paiements"), set()
)
check("3 familles : sous le seuil", m("AI Analyst", "Databricks, Snowflake, Azure"), None)

print("\n── E. le suivi protege toujours ──")
o = {"entreprise": "BNP", "poste": "ESG Quant", "description": lourd}
check("offre suivie jamais retiree", T.motif(o, {"BNP|ESG Quant"}), None)

print("\n── F. doublons ──")
import doublons as D

_oid = lambda o: f"{o['entreprise']}|{o['poste']}"
_rs = lambda u: 3 if "linkedin" not in (u or "") else 0


def dbl(*offres, proteges=frozenset()):
    return set(D.doublons(list(offres), proteges, _rs, _oid))


EN = (
    "At ABB we help industries. You will report to the EU Taxonomy lead. CSRD, LCA, EPD, "
    "ISO 14001, REACH, RoHS, 2026, 40 % of the time with the team and our partners."
)
DE = (
    "Bei ABB unterstützen wir die Industrie. Sie berichten an die EU Taxonomie. CSRD, LCA, "
    "EPD, ISO 14001, REACH, RoHS, 2026, 40 % der Zeit und wir sind für Sie da."
)
a = {
    "entreprise": "ABB",
    "poste": "Product Sustainability & EU Taxonomy Specialist (f/m/d)",
    "localisation": "Eggelsberg, Upper Austria",
    "description": EN,
    "url": "https://linkedin/1",
    "fit": 10,
}
b = {
    "entreprise": "ABB",
    "poste": "Spezialist:in Produktnachhaltigkeit & EU-Taxonomie (w/m/d)",
    "localisation": "Eggelsberg, Upper Austria",
    "description": DE,
    "url": "https://linkedin/2",
    "fit": 10,
}
check("traduction EN/DE : la version allemande part", dbl(a, b), {_oid(b)})
check("meme traduction, autre ville : deux postes", dbl(a, {**b, "localisation": "Wien"}), set())
c = {
    "entreprise": "Onepoint",
    "poste": "Consultant en Transformation Finance - F/H",
    "localisation": "Paris, Île-de-France",
    "url": "https://linkedin/3",
}
d = {
    "entreprise": "Onepoint",
    "poste": "Consultant Transformation Finance F/H",
    "localisation": "Paris - 75",
    "url": "https://onepoint.fr/jobs/9",
}
check("meme intitule aux mots vides pres : garde le site employeur", dbl(c, d), {_oid(c)})
e1 = {
    "entreprise": "Fifth Third",
    "poste": "Finance and Accounting Leadership Program: Accounting",
    "localisation": "Cincinnati",
}
e2 = {**e1, "poste": "Finance and Accounting Leadership Program: Finance"}
check("deux filieres, memes mots en ensemble : pas doublon", dbl(e1, e2), set())
z1 = {"entreprise": "EY", "poste": "【ESG服務】社會組 - 顧問", "localisation": "Taipei"}
z2 = {**z1, "poste": "【ESG服務】環境組 - 顧問"}
check("titres non latins : jamais confondus", dbl(z1, z2), set())
check("le suivi garde son offre", dbl(c, d, proteges={_oid(c)}), {_oid(d)})

print("\n── G. ce qui n'est pas une offre ──")
for u, attendu in [
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
]:
    check("url " + (u[:55] or "(vide)"), T.pas_une_offre({"url": u}), attendu)
check(
    "ligne RECHERCHE sans lien : retiree",
    m("Analyste ESG", url="", url_type="RECHERCHE"),
    "pas_une_offre:sans_lien",
)
print("\n── étudiant demandé : retiré, même en V.I.E ──")
check(
    "Euronext V.I.E pour étudiant",
    m(
        "VIE - ESG & Sustainable Finance Analyst",
        "Profile Final or penultimate year student from a Tier 1 university.",
        contrat="V.I.E",
    ),
    "etudiant",
)
check(
    "fresh graduate or final-year : gardée",
    m(
        "Finance Leadership Development Program",
        "Are you a fresh graduate or final-year student in Finance?",
    ),
    None,
)
check(
    "« Tu étais étudiant(e) » : gardée",
    m(
        "Consultant(e) junior – CDI",
        "Tu étais étudiant(e) en école de commerce, à la recherche d'un premier poste.",
    ),
    None,
)
check(
    "étudiant au suivi : gardée",
    T.motif(
        {
            "entreprise": "Euronext",
            "poste": "VIE ESG",
            "url": "https://www.linkedin.com/jobs/view/1",
            "description": "Final year student wanted.",
        },
        {"Euronext|VIE ESG"},
    ),
    None,
)

check(
    "sans lien mais au suivi : gardee",
    T.motif({"entreprise": "Covéa", "poste": "Analyste ESG", "url": ""}, {"Covéa|Analyste ESG"}),
    None,
)

print(f"\n=== BILAN : {ok} ✅  /  {ko} ❌  ({ok}/{ok + ko}) ===")
sys.exit(1 if ko else 0)
