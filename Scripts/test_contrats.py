#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_contrats.py — Deduction du type de contrat (job_sources).

Cas tires des VRAIS intitules et descriptions de apply_queue.json.

Regle de conception : un contrat FAUX est pire qu'un contrat vide, parce que la
colonne sert a filtrer ce que l'utilisateur voit. Chaque cas negatif ci-dessous est un
piege rencontre pour de bon (« Assurance vie », « early stage », « prestataire »).

Run : python test_contrats.py
"""

import _profil_test  # noqa: F401  — les tests tournent sur le profil d'exemple
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from job_sources import contrat_du_titre, contrat_de_la_description

PASS = FAIL = 0


def check(nom, obtenu, attendu):
    global PASS, FAIL
    if obtenu == attendu:
        PASS += 1
        print(f"  ✅ {nom}")
    else:
        FAIL += 1
        print(f"  ❌ {nom}\n       obtenu {obtenu!r}, attendu {attendu!r}")


print("\n── A. intitulé : acronymes français ──")
for t, a in [
    ("CDI - Analyste DSI H/F - Paris", "CDI"),
    ("Business Analyst Risque de Crédit / CDI / H/F", "CDI"),
    ("Group Environmental Transition Analyst (F/H) CDI", "CDI"),
    ("ANALYSTE RISQUES CDD - 12 mois H/F", "CDD"),
    ("CDD - Analyste Trade Compliance H/F", "CDD"),
    ("Risk Analyst - AI Trainer - Freelance - Remote", "Freelance"),
    ("Consultant en intérim management", "Interim"),
]:
    check(t[:52], contrat_du_titre(t), a)

print("\n── B. intitulé : libellés anglais ──")
check("Permanent → CDI", contrat_du_titre("Sustainability Manager - Permanent"), "CDI")
check("Fixed term → CDD", contrat_du_titre("Analyste Fixed Term - 6 mois"), "CDD")
check("Fixed Income n'est PAS un contrat", contrat_du_titre("Analyste Fixed Income"), "")
check("full-time n'est pas un contrat (rythme)", contrat_du_titre("Analyst - Full-time"), "")

print("\n── C. priorité : étudiant avant tout le reste ──")
check(
    "« Stage … (puis VIE/CDI) » → Stage",
    contrat_du_titre("Stage Analyste M&A (puis VIE/CDI)"),
    "Stage",
)
check(
    "« Alternance … CDI à la clé » → Alternance",
    contrat_du_titre("Alternance Analyste ESG - CDI à la clé"),
    "Alternance",
)
check("V.I.E seul → V.I.E", contrat_du_titre("V.I.E - Analyste Finance"), "V.I.E")

print("\n── D. faux positifs (aucun contrat ne doit sortir) ──")
for t in [
    "Analyste ESG H/F",
    "Chargé de mission développement durable",
    "Chargé de vie associative",
    "Assurance vie - Gestionnaire",
    "ANALYSTE CYCLE DE VIE HABILLEMENT",
    "Analyste Fixed Income",
]:
    check(f"{t[:46]} → vide", contrat_du_titre(t), "")

print("\n── E. description : libellé structuré ──")
socle = "Rejoignez notre equipe. " * 6
check(
    "« Type de contrat : CDI »",
    contrat_de_la_description(socle + "Type de contrat : CDI. Poste base a Paris."),
    "CDI",
)
check(
    "« Contrat : Alternance »",
    contrat_de_la_description(socle + "Contrat : Alternance de 24 mois."),
    "Alternance",
)

print("\n── F. description : pièges déjà rencontrés ──")
check(
    "« en alternance ou en poste » = expérience, pas contrat",
    contrat_de_la_description(socle + "Vous avez une experience en alternance ou en poste."),
    "",
)
check(
    "« early stage » = phase d'entreprise",
    contrat_de_la_description(socle + "Nous investissons dans des startups early stage."),
    "",
)
check(
    "« prestataire » = les clients",
    contrat_de_la_description(socle + "Vous gerez les contrats prestataires et commandes."),
    "",
)
check("description trop courte → vide", contrat_de_la_description("CDI"), "")

print("\n── G. un poste qui demande un étudiant est un stage ──")
# Phrases reelles de la file, 2026-10-04.
for phrase in [
    "Et si c'était vous ? Vous êtes étudiant en Bac +4/5, avec une spécialisation ESG.",
    "Qui êtes vous ? Étudiant(e) en dernière année d'école d'ingénieur ou Master 2.",
    "Étudiant en fin d’études ou en année de césure au sein d’une école de commerce.",
    "Vous êtes étudiant de niveau Bac +5 en École de Commerce, d'Ingénieur ou Université.",
    "Requirements: Currently pursuing a Bachelor’s or Master’s degree in Finance.",
    "Final or penultimate year student from a Tier 1 university, business or engineering school.",
    "Candidates must be enrolled at one of the following universities to be considered.",
    "Vous êtes étudiant en master, en vue de l'obtention du diplôme d'ingénieur.",
]:
    check("étudiant → Stage : " + phrase[:50], contrat_de_la_description(socle + phrase), "Stage")
check(
    "étudiant l'emporte sur un libellé CDD",
    contrat_de_la_description(socle + "Contrat : CDD. Vous êtes étudiant en master."),
    "Stage",
)
for phrase in [
    # le diplome est accepte : ce n'est pas un stage
    "We're looking for individuals currently pursuing (or already holding) a relevant master's degree.",
    "For final year students or recent graduates with a bachelor’s or master’s degree.",
    "Master's degree (Bac+5) or final-year student in Engineering or Sustainability.",
    "Bachelor's degree (or currently pursuing a degree) in Political Science.",
    "Higher education or currently studying in finance or economics.",
    "Étudiant en dernière année ou jeune diplômé d'une école de commerce.",
    # un passe demande, pas un statut
    "Erste Erfahrungen durch Praktika oder Werkstudententätigkeiten im Finanzbereich.",
    "Relevant experience through internships, working student roles, or research projects.",
    # hors sujet
    "Candidates currently pursuing certification may also be considered.",
    "Nous accompagnons les étudiants et les entreprises dans leur transition.",
]:
    check("pas un stage : " + phrase[:50], contrat_de_la_description(socle + phrase), "")
check(
    "titre « Working Student » → Stage",
    contrat_du_titre("Working Student - Supplier Sustainability (f/m/div)"),
    "Stage",
)
check(
    "titre « Werkstudent:in » → Stage",
    contrat_du_titre("Werkstudent:in AXA Asset Management"),
    "Stage",
)

print(f"\n=== BILAN : {PASS} ✅  /  {FAIL} ❌  ({PASS}/{PASS + FAIL}) ===")
# sys.exit au niveau module TERMINE l'interpreteur de qui importe ce
# fichier. Sous garde, il ne s'applique qu'a une execution directe.
if __name__ == "__main__":
    sys.exit(1 if FAIL else 0)
