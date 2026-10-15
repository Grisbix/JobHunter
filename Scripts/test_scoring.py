#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_scoring.py — le fit, l'expérience requise, et les pièges du scoring.

`ats_match` décide lesquelles des 6300 offres reçoivent un CV et une lettre.
C'était le seul programme du socle sans aucun test — et il tournait avec sa
règle principale MORTE : `_ESG_TITLE_RX` commençait par un caractère backspace,
donc « un intitulé explicitement ESG lève le plafond à 10 » ne s'appliquait
jamais. Le motif compilait, ne levait rien, et ne matchait aucune chaîne.

Run : python test_scoring.py
"""
import _profil_test  # noqa: F401  — les tests tournent sur le profil d'exemple
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import jutil
import ats_match
from ats_match import (fit_score, experience_years, axis_scores, densite_esg,
                       _ESG_TITLE_RX, _ESG_DENSITE_MIN)

PASS = FAIL = 0


def check(nom, obtenu, attendu):
    global PASS, FAIL
    if obtenu == attendu:
        PASS += 1
        print(f"  ✅ {nom}")
    else:
        FAIL += 1
        print(f"  ❌ {nom}\n       obtenu {obtenu!r}, attendu {attendu!r}")


def entre(nom, valeur, bas, haut):
    global PASS, FAIL
    if bas <= valeur <= haut:
        PASS += 1
        print(f"  ✅ {nom} ({valeur})")
    else:
        FAIL += 1
        print(f"  ❌ {nom} : {valeur} hors de [{bas}, {haut}]")


# Un texte long et creux, pour que la densité ESG soit calculée sur du volume.
REMPLISSAGE = ("Nous accompagnons nos clients dans leurs projets. " * 60)


print("── A. les motifs ne sont pas corrompus ──")
# LE test qui manquait. Un \b devient soit \x08 (heredoc shell), soit un
# antislash littéral : dans les deux cas le motif compile et ne matche plus rien.
vus = jutil.verifier_motifs(vars(ats_match), minimum=4)
check("tous les motifs du module sont sains", vus >= 4, True)
for nom, rx in [(n, v) for n, v in vars(ats_match).items() if isinstance(v, re.Pattern)]:
    check(f"{nom} sans backspace", "\x08" in rx.pattern, False)

print("\n── B. l'intitulé ESG lève le plafond (la règle qui était morte) ──")
for titre in ["Analyste ESG", "Sustainability Manager", "Chargé de mission RSE",
              "Analyste extra-financier", "Climate Risk Analyst", "E&S Analyst",
              "Analyste CSRD", "Responsable décarbonation"]:
    check(f"« {titre} » reconnu ESG", bool(_ESG_TITLE_RX.search(titre.lower())), True)
# Les bornes \b servent à ça : sans elles, « rse » matche « diveRSE ».
for titre in ["Diverse Talent Partner", "Sparse Data Engineer",
              "Trading Market Risk Analyst", "Client Services Consultant"]:
    check(f"« {titre} » PAS reconnu ESG", bool(_ESG_TITLE_RX.search(titre.lower())), False)

print("\n── C. une offre ESG franche score haut ──")
esg_pur = ("Analyste ESG. Missions : analyse extra-financière, reporting CSRD, "
           "taxonomie européenne, SFDR articles 8 et 9, notation ESG des émetteurs, "
           "empreinte carbone et trajectoire climat, due diligence ESG.")
f_pur, _ = fit_score(esg_pur, "Analyste ESG")
# UNE OFFRE ESG PURE DOIT SORTIR 10. Le commentaire de `_TARGET` l'affirmait
# depuis toujours, le nombre disait l'inverse : l'axe ESG saturé vaut 3.0
# (densité 1.00 × poids 3), et sur une cible de 4.0 il n'atteignait que 75 %,
# soit fit 8. Il fallait un SECOND axe pour toucher le maximum — autrement dit
# qu'une offre ESG parle aussi finance pour être jugée parfaite. Cible ramenée
# à 3.0, ce que vaut l'axe.
check("une offre ESG pure atteint le maximum", f_pur, 10)
esg_mixte = (esg_pur + " Analyse financière, modélisation financière, "
             "valorisation DCF, gestion d'actifs.")
f_mixte, _ = fit_score(esg_mixte, "Analyste ESG")
check("ESG + finance aussi", f_mixte, 10)
# Le plafond, lui, n'a pas bougé : baisser la cible n'ouvre le 10 qu'à ce qui
# était déjà plafonné à 10. Une offre sans ESG reste tenue par son plafond.
f_sans, _ = fit_score(
    "Analyse financière, modélisation financière, valorisation DCF, "
    "gestion d'actifs, contrôle de gestion, audit, gestion des risques, "
    "conseil et stratégie, Python et SQL.", "Financial Analyst")
entre("sans ESG, le plafond tient toujours", f_sans, 1, 8)

print("\n── D. le boilerplate RSE ne fait plus un poste ESG ──")
# Trois mentions noyées dans 8000 caractères : c'est le discours RSE de
# l'employeur, pas le poste. Mesuré sur ExxonMobil « Trading Market Risk
# Analyst » — 3 marqueurs dans 7940 caractères sortaient à fit 10.
noye = ("Trading Market Risk Analyst. " + REMPLISSAGE +
        " Our commitment to sustainability. " + REMPLISSAGE +
        " We reduce our carbon footprint. " + REMPLISSAGE +
        " environmental stewardship matters. " + REMPLISSAGE)
d = densite_esg(noye.lower())
check("densité ESG sous le seuil", d < _ESG_DENSITE_MIN, True)
f_noye, _ = fit_score(noye, "Trading Market Risk Analyst")
entre("intitulé non-ESG + RSE de façade", f_noye, 1, 8)

dense = ("Analyste ESG. " + "Analyse ESG, reporting CSRD, taxonomie, SFDR, "
         "empreinte carbone, climat, biodiversité, durabilité. " * 12)
check("une vraie annonce ESG reste au-dessus du seuil",
      densite_esg(dense.lower()) >= _ESG_DENSITE_MIN, True)

print("\n── E. le plafond tient, même avec le bonus junior ──")
# Le bonus était appliqué APRÈS le plafond et le franchissait : « Auditeur
# junior analyste » sortait à 10 avec un plafond calculé à 8.7.
sans_esg = ("Auditeur junior. Analyse financière, modélisation financière, "
            "valorisation DCF, audit et comptabilité, contrôle de gestion, "
            "gestion des risques, conseil et stratégie, Python et SQL.")
f_jun, _ = fit_score(sans_esg, "Auditeur junior analyste")
entre("junior sans ESG reste sous le plafond", f_jun, 1, 8)

print("\n── F. junior se lit dans l'INTITULÉ, pas dans la description ──")
# Même piège que SENIOR et NEG, déjà corrigé pour eux : un « ouvert aux
# alternants » en pied d'annonce donnait +1 à un poste qui n'a rien de junior.
corps = ("Analyse financière, modélisation financière, valorisation DCF. "
         "Ce poste est également ouvert aux alternants et aux stagiaires.")
f_faux, _ = fit_score(f"Directeur financier {corps}", "Directeur financier")
f_vrai, _ = fit_score(f"Analyste financier junior {corps}", "Analyste financier junior")
check("le mot « alternant » du corps ne donne pas le bonus", f_faux < f_vrai, True)

print("\n── G. malus de séniorité ──")
base = ("Analyse ESG, reporting CSRD, taxonomie, SFDR, empreinte carbone, "
        "notation ESG, due diligence ESG, analyse extra-financière.")
f_jr, _ = fit_score(f"Analyste ESG junior {base}", "Analyste ESG junior")
f_sr, _ = fit_score(f"Head of ESG {base}", "Head of ESG")
f_dir, _ = fit_score(f"Directeur ESG {base}", "Directeur ESG")
check("junior au-dessus de « Head of »", f_jr > f_sr, True)
check("junior au-dessus de « Directeur »", f_jr > f_dir, True)
# Un titre qui SE TERMINE par le mot échappait au malus (SENIOR est cherché en
# sous-chaîne avec un espace final).
f_fin, _ = fit_score(f"ESG Disclosure & Compliance Lead {base}",
                     "ESG Disclosure & Compliance Lead")
check("un titre finissant par « Lead » prend le malus", f_fin < f_jr, True)
# « Lead Generation » n'est pas un poste senior.
f_leadgen, _ = fit_score(f"ESG Lead Generation Analyst {base}",
                         "ESG Lead Generation Analyst")
check("« Lead Generation » n'est pas de la séniorité", f_leadgen > f_fin, True)

print("\n── H. malus de rôle hors-cible ──")
f_com, _ = fit_score(f"Commercial ESG {base}", "Commercial ESG")
check("un rôle commercial est pénalisé", f_com < f_jr, True)

print("\n── I. expérience requise ──")
check("« 10 ans d'expérience »", experience_years("10 ans d'expérience exigée"), 10)
check("« 5 years of experience »", experience_years("5 years of experience required"), 5)
# La fenêtre à gauche est large : l'exigence s'écrit « expérience … de N ans ».
check("« expérience professionnelle antérieure de 3 à 5 ans »",
      experience_years("expérience professionnelle antérieure de 3 à 5 ans"), 5)
# Les blancs sont écrasés : les fiches structurées séparent l'étiquette de sa valeur.
check("étiquette séparée par des retours chariot",
      experience_years("Niveau d'expérience \r\n \r\n \r\n Plus de 10 ans"), 10)
check("offre junior : un « 10 ans » isolé est du bruit",
      experience_years("Alternance. Société fondée il y a 10 ans."), 0)
check("au-delà de 15 ans = âge ou ancienneté, ignoré",
      experience_years("40 ans d'expérience de notre société"), 0)
check("aucune exigence", experience_years("Poste ouvert à tous profils"), 0)

print("\n── J. le malus expérience écrase le fit ──")
f0, y0 = fit_score(f"Analyste ESG {base}", "Analyste ESG")
f10, y10 = fit_score(f"Analyste ESG {base} 10 ans d'expérience exigée", "Analyste ESG")
check("10 ans exigés sont détectés", y10, 10)
check("10 ans exigés font chuter le fit", f10 <= f0 - 4, True)
f3, _ = fit_score(f"Analyste ESG {base} 3 ans d'expérience exigée", "Analyste ESG")
check("3 ans coûtent moins que 10", f3 > f10, True)

print("\n── K. bornes et robustesse ──")
for texte, titre in [("", ""), (None, None), ("x", "x"), ("   ", "   ")]:
    f, y = fit_score(texte, titre)
    entre(f"fit borné sur {texte!r}", f, 1, 10)
    check(f"expérience nulle sur {texte!r}", y, 0)
check("les compétences génériques seules ne suffisent pas",
      fit_score("Excel, Anglais, Communication", "Assistant administratif")[0] <= 3, True)

print("\n── L. l'axe ESG est le seul atténué par la densité ──")
ax = axis_scores(("Analyse financière, modélisation financière, valorisation DCF, "
                  "audit et comptabilité. " + REMPLISSAGE).lower())
check("l'axe finance n'est pas touché par la densité", ax["finance"] > 0.5, True)

print("\n── M. qui lève le plafond : ESG-finance oui, HSE et technique non ──")
# Mesure du 2026-09-23 : une dizaine d'offres HSE à fit 10 sur 25 tirées au
# hasard. Même description riche en ESG pour tous : seul l'intitulé change.
for titre, maxi in [("Chargé de Sécurité, Santé et Environnement H/F", 6),
                    ("Chargé de Mission HSE F/H", 6),
                    ("Sustainability (EHS) Engineer", 6),
                    ("Ingénieur QHSE H/F", 6),
                    ("Environmental Health & Safety Specialist", 6)]:
    check(f"« {titre} » ne sort pas au-dessus de {maxi}",
          fit_score(f"{titre} {esg_pur}", titre)[0] <= maxi, True)
# La garde technique retire la levée par l'INTITULÉ, pas celle par la
# description : un poste d'ingénieur décrit en SFDR et taxonomie a vraiment du
# fond ESG. Sur un texte où l'ESG n'est qu'une mention, l'intitulé technique
# ne doit rien apporter de plus qu'un intitulé neutre.
# LE TEXTE EST FIXE, SEUL L'INTITULÉ VARIE. Mettre l'intitulé dans le texte
# mélangeait deux effets : « Sustainability » y nourrit l'axe ESG de la
# description, ce qui n'a rien à voir avec la levée du plafond par le titre.
mention = ("Missions : analyse financière, modélisation financière, valorisation "
           "DCF, analyse sectorielle, suivi du bilan carbone du site.")
neutre = fit_score(mention, "Chargé de mission")[0]
for titre in ["Analyste climat", "Sustainability Analyst"]:
    check(f"« {titre} » lève bien le plafond", fit_score(mention, titre)[0] > neutre, True)
for titre in ["Ingénieur Climatologue F/H", "Technicien études génie climatique F/H",
              "Sustainability Engineer"]:
    check(f"« {titre} » n'apporte rien de plus qu'un intitulé neutre",
          fit_score(mention, titre)[0] <= neutre, True)
for titre in ["Analyste ESG", "Responsable RSE et HSE", "ESG Data Engineer",
              "Associate, Investment Stewardship", "Analyste ISR",
              "Ingénieur financier ESG"]:
    check(f"« {titre} » garde son 10", fit_score(f"{titre} {esg_pur}", titre)[0], 10)
# Un mot isolé ne déclenche pas le veto : ce sont des postes de finance.
for titre in ["Chargé d'Investissements en Venture Santé",
              "Operational Risk Management IT & Sécurité"]:
    check(f"« {titre} » échappe au veto HSE", ats_match._titre_hse(titre.lower()), False)

print("\n── N. métiers hors cible : le vocabulaire vert ne les porte plus à 10 ──")
# Mesure du 2026-09-24 sur les 665 offres à fit >= 9. Même description riche
# en ESG pour tous : seul l'intitulé change.
for titre in ["Research Assistant/Associate (Centre for Sustainable Medicine)",
              "Assistant Professor (Nature-based Climate Solutions)",
              "Doctoral student in energy and environmental systems analysis",
              "Chef(fe) de Projet Batiment Durable",
              "Gestionnaire administratif·ve de l'alliance européenne EU GREEN",
              "Procurement Risk, Sustainability & Programs Specialist",
              "Supply Chain Sustainability and Compliance Analyst",
              "Graduate Environmental Scientist (Dublin)",
              "Athlete Welfare and Sustainability Coordinator",
              "Engineer (m/w/d) Sustainability & Product Compliance",
              "Ingénieur Santé Environnement et Risque Industriel"]:
    check(f"« {titre} » ne sort pas au-dessus de 6",
          fit_score(f"{titre} {esg_pur}", titre)[0] <= 6, True)
# Ce qui DOIT rester dans la cible.
for titre in ["ESG Research Analyst", "Sustainable Procurement ESG Analyst",
              "Research Analyst - Sustainable Investing", "ESG Data Scientist",
              "Portfolio Construction Analyst - ESG", "Ingénieurs auditeur financier ESG"]:
    check(f"« {titre} » garde son 10", fit_score(f"{titre} {esg_pur}", titre)[0], 10)
for titre in ["Research Analyst", "Data-Scientist", "Ingénieurs auditeur financier"]:
    check(f"« {titre} » n'est pas hors cible", ats_match._titre_hors_cible(titre.lower()), False)
# Analyste financier classique (2026-10-07) : 8 sans ESG, plus le repli a 6.
fin = ("Missions : analyse financière, modélisation Excel, valorisation DCF, "
       "analyse de bilan, comptabilité IFRS, M&A, corporate finance.")
for titre in ["Analyste financier junior", "Financial Analyst", "Investment Analyst",
              "Contrôleur de gestion junior", "Credit Analyst"]:
    check(f"« {titre} » sans ESG dépasse l'ancien plafond de 6",
          fit_score(f"{titre} {fin}", titre)[0] >= 7, True)
check("l'ESG reste devant la finance",
      fit_score(f"Analyste ESG {esg_pur}", "Analyste ESG")[0]
      > fit_score("Financial Analyst Missions : budget, reporting mensuel.",
                  "Financial Analyst")[0], True)
check("« Data Engineer » ne profite pas de la règle finance",
      fit_score(f"Data Engineer {fin}", "Data Engineer")[0] <= 7, True)
# L'IA reste la cible secondaire : un ingénieur IA garde son plafond de 8.
ia = ("Missions : LLM, agents IA, RAG, intelligence artificielle générative, "
      "machine learning, Python, déploiement de modèles.")
check("« AI Engineer » garde le plafond IA de 8",
      fit_score(f"AI Engineer {ia}", "AI Engineer")[0] >= 7, True)

# fit_fin (2026-10-09) : departage les ex aequo sans deplacer aucun fit entier.
from ats_match import fit_detail   # noqa: E402
_TEXTES = [
    ("Analyste ESG", f"Analyste ESG {esg_pur}"),
    ("Financial Analyst", f"Financial Analyst {fin}"),
    ("AI Engineer", f"AI Engineer {ia}"),
    ("Data Engineer", f"Data Engineer {fin}"),
    ("Head of ESG", "Head of ESG 10 years of experience required"),
    ("Office Manager", "Office Manager accueil courrier"),
]
_ecarts = [(t, f, ff) for t, x in _TEXTES for f, _y, ff in [fit_detail(x, t)] if round(ff) != f]
check("l'arrondi de fit_fin rend toujours le fit entier", _ecarts, [])
check("fit_detail et fit_score s'accordent",
      all(fit_detail(x, t)[:2] == fit_score(x, t) for t, x in _TEXTES), True)
_dense = fit_detail(f"Analyste ESG {esg_pur}", "Analyste ESG")
_maigre = fit_detail(f"Analyste ESG {esg_pur} " + "Le groupe et ses metiers. " * 60, "Analyste ESG")   # ESG noye
check("a fit egal, la densite ESG passe devant",
      _dense[0] == _maigre[0] and _dense[2] > _maigre[2], True)

print("\n── H. langue : annonce illisible ou langue exigée non parlée ──")
# Profil d'exemple : français, anglais, allemand. Une offre en néerlandais sortait à 10.
_nl = ("Wij zoeken een ESG analist voor ons team. Je bent verantwoordelijk voor de "
       "rapportage van het fonds, de SFDR en de CSRD. Wij bieden een uitdagende functie "
       "bij een duurzame organisatie en jij werkt nauw samen met onze collega's. ") * 4
check("annonce rédigée en néerlandais : plafond 2", fit_score(_nl, "ESG Analist")[0] <= 2, True)
_exige = f"ESG Analyst {esg_pur} Fluent in English and Dutch is required."
check("néerlandais exigé : plafond 4", fit_score(_exige, "ESG Analyst")[0] <= 4, True)
_plus = f"ESG Analyst {esg_pur} Fluent English required; Dutch is a plus."
check("néerlandais « a plus » : rien ne change", fit_score(_plus, "ESG Analyst")[0], 10)
for txt, attendu in [
        ("Fluency in Dutch and/or French, with a good command of English.", ""),
        ("Fluent in English + French and/or Dutch (speaking all three is an asset)", ""),
        ("communication skills, in English and preferable in Dutch too, and others", ""),
        ("Strong presence in Chinese markets and fluency in English, Chinese markets", ""),
        ("Fluent in German and English, both written and spoken.", ""),
        ("Fluent in English and Swedish or Finnish.", "swedish"),
        ("Maîtrise du néerlandais exigée pour ce poste.", "néerlandais"),
        ("Profil Nederlandstalig met kennis van Engels.", "nederlands")]:
    check(f"langue exigée : {txt[:45]}…", ats_match.langue_exigee(txt), attendu)
for code, txt in [("fr", "Nous recherchons pour notre équipe un analyste. Vous travaillerez avec les gérants sur le reporting des fonds et la CSRD dans une équipe. " * 3),
                  ("de", "Wir suchen für unser Team eine Analystin. Sie arbeiten mit der Berichterstattung und das Reporting ist auf eine Stelle zu besetzen. " * 3)]:
    check(f"annonce en {code} : pas de plafond de langue", ats_match.plafond_langue(txt)[0], 10.0)

print(f"\n=== BILAN : {PASS} ✅  /  {FAIL} ❌  ({PASS}/{PASS + FAIL}) ===")
if __name__ == "__main__":
    sys.exit(1 if FAIL else 0)
