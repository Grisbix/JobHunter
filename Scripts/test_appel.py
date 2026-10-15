#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_appel.py — La formule d'appel nominative du message (sans reseau).

POURQUOI UNE SUITE A PART. Le champ `rh` de la file est SURCHARGE. Mesure du
21/09/2026 sur 4917 offres :

    4501  vide
     413  une URL de recherche LinkedIn, pas une personne
       3  une civilite suivie d'un nom, toutes venues de l'API detail V.I.E

Un code qui prendrait ce champ pour un nom ecrirait « Bonjour
https://www.linkedin.com/search... » dans un message de candidature. Le risque
n'est donc pas theorique, il est majoritaire : 413 cas contre 3.

Run : python test_appel.py
"""
import _profil_test  # noqa: F401  — les tests tournent sur le profil d'exemple
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, __import__("pathlib").Path(__file__).resolve().parent.as_posix())

from message_offre import appel, _nom_propre, _patronyme   # noqa: E402

PASS = FAIL = 0


def check(nom, obtenu, attendu):
    global PASS, FAIL
    if obtenu == attendu:
        PASS += 1
        print(f"  ✅ {nom}")
    else:
        FAIL += 1
        print(f"  ❌ {nom}\n       attendu : {attendu!r}\n       obtenu  : {obtenu!r}")


def a(rh, langue="fr", ton="sobre"):
    return appel({"rh": rh}, langue, ton)


print("\n── A. Les trois noms reels de la file ──")
check("V.I.E CA Consumer Finance, tout en capitales",
      a("Monsieur KEVIN SILVA PEREIRA"), "Monsieur Silva Pereira,")
check("  la meme en anglais",
      a("Monsieur KEVIN SILVA PEREIRA", "en"), "Dear Mr Silva Pereira,")
check("casse mixte : les capitales sont le patronyme",
      a("Madame Awa MOUSSA"), "Madame Moussa,")
check("  accent dans le prenom, sans effet sur le nom",
      a("Madame Mélanie GIRARD"), "Madame Girard,")

print("\n── B. Particules : nobiliaires en bas, articles en haut ──")
# « Monsieur De Gaulle » est une faute ; « Monsieur Le Pen » n'en est pas une.
# Les deux familles ne se traitent donc pas pareil.
check("de + article", a("Monsieur JEAN-PIERRE DE LA TOUR"), "Monsieur de La Tour,")
check("de seul", a("Monsieur CHARLES DE GAULLE"), "Monsieur de Gaulle,")
check("« Le » garde sa majuscule", a("Madame Marine LE PEN"), "Madame Le Pen,")
check("neerlandais", a("Mrs Sarah VAN DEN BERG"), "Madame van den Berg,")
check("portugais", a("M. Joao DOS SANTOS"), "Monsieur dos Santos,")

print("\n── C. Ponctuation interne au nom ──")
check("apostrophe", a("Mr PATRICK O'BRIEN", "en"), "Dear Mr O'Brien,")
check("trait d'union dans le patronyme",
      _nom_propre("GARCIA-LOPEZ"), "Garcia-Lopez")
check("casse deja posee a la main, respectee", _nom_propre("McDonald"), "McDonald")

print("\n── D. Ce qui N'EST PAS une personne ──")
# 413 offres de la file portent une URL dans ce champ : c'est le cas le plus
# frequent, pas un cas limite.
check("URL LinkedIn -> generique",
      a("https://www.linkedin.com/search/results/people/?keywords=RH"),
      "Madame, Monsieur,")
check("  idem en anglais",
      a("https://www.linkedin.com/search/results/people/?keywords=RH", "en"),
      "Dear Sir or Madam,")
check("champ vide", a(""), "Madame, Monsieur,")
check("guichet : service", a("Service Recrutement", "en"), "Dear Sir or Madam,")
check("guichet : equipe", a("Talent Acquisition Team", "en"), "Dear Sir or Madam,")
check("guichet : direction", a("Direction des Ressources Humaines", "en"),
      "Dear Sir or Madam,")
check("adresse mail", a("recrutement@societe.fr", "en"), "Dear Sir or Madam,")

print("\n── E. Le genre ne se devine pas d'un prenom ──")
# Sans civilite explicite, aucune formule francaise n'est neutre : on garde la
# generique. L'anglais, lui, s'adresse au nom complet sans genrer.
check("nom nu, francais -> generique", a("Kevin Silva Pereira"),
      "Madame, Monsieur,")
check("nom nu, anglais -> nom complet", a("Kevin Silva Pereira", "en"),
      "Dear Kevin Silva Pereira,")

print("\n── F. Le ton detendu garde sa forme ──")
check("detente sans nom", a("", "fr", "detente"), "Bonjour,")
check("detente avec nom : la civilite prime",
      a("Monsieur KEVIN SILVA PEREIRA", "fr", "detente"),
      "Monsieur Silva Pereira,")

print("\n── G. Patronyme isole ──")
check("tout capitales : le premier mot est le prenom",
      _patronyme("KEVIN SILVA PEREIRA"), "Silva Pereira")
check("casse mixte : coupe sur les capitales",
      _patronyme("Awa MOUSSA"), "Moussa")
check("un seul mot", _patronyme("MOUSSA"), "Moussa")

print("\n── H. Plusieurs destinataires dans le meme champ ──")
# Mirova (offre 246087 mise a part, celle-ci vient d'Indeed) ecrit en clair
# « adressez votre CV et votre lettre a Louis Mac Arthur et Clement Lebrun ».
# Sans decoupe, `_patronyme` avalait la conjonction et rendait
# « Monsieur Mac Arthur et Monsieur Clement Lebrun » comme UN patronyme.
check("deux hommes",
      a("Monsieur Louis Mac Arthur et Monsieur Clément Lebrun"),
      "Monsieur Mac Arthur, Monsieur Lebrun,")
check("  les memes en anglais",
      a("Monsieur Louis Mac Arthur et Monsieur Clément Lebrun", "en"),
      "Dear Mr Mac Arthur and Mr Lebrun,")
check("deux femmes", a("Madame Awa MOUSSA et Madame Mélanie GIRARD"),
      "Madame Moussa, Madame Girard,")
check("mixte, la particule tient", a("Madame Awa MOUSSA et Monsieur Charles DE GAULLE"),
      "Madame Moussa, Monsieur de Gaulle,")
check("separateur esperluette", a("Monsieur Charles DE GAULLE & Madame Marine LE PEN"),
      "Monsieur de Gaulle, Madame Le Pen,")
# Un morceau muet est ECARTE, pas propage : le repli sur la chaine entiere
# rendait « Monsieur Et Marie Dupont », une conjonction promue patronyme.
check("le morceau qui ne parse pas est ecarte",
      a("Monsieur Jean et Marie Dupont"), "Monsieur Jean,")
check("le guichet ne disqualifie que sa moitie",
      a("Monsieur Louis Mac Arthur / Service Recrutement"),
      "Monsieur Mac Arthur,")
check("deux guichets : generique", a("Service Recrutement et Direction RH"),
      "Madame, Monsieur,")
# L'URL se teste AVANT la decoupe : ses barres obliques sont un separateur.
check("l'URL n'est pas hachee en morceaux",
      a("https://www.linkedin.com/search/results/people/?keywords=RH"),
      "Madame, Monsieur,")

print("\n── nom absent de l'annonce : pas nommé (2026-10-07) ──")
from message_offre import nom_dans_offre   # noqa: E402
check("nom absent du texte", nom_dans_offre("Madame Maria LOPEZ", "VIE Sustainability PMO"), "")
check("nom cité dans le texte", nom_dans_offre("Madame Audrey Durand",
      "Contact : Audrey DURAND, chargée de recrutement"), "Madame Audrey Durand")
check("accents ignorés", nom_dans_offre("Monsieur Hélène Dupré", "écrire à M. Dupre"),
      "Monsieur Hélène Dupré")
check("la civilité seule ne compte pas", nom_dans_offre("Madame X", "Madame, Monsieur"), "")
check("appel d'une offre sans le nom → générique",
      appel({"rh": "Madame Maria LOPEZ", "poste": "PMO", "description": "Budapest"}),
      "Madame, Monsieur,")
check("appel d'une offre qui nomme → nominatif",
      appel({"rh": "Madame Maria Lopez", "poste": "PMO",
             "description": "Contact : Maria Lopez"}), "Madame Lopez,")

print(f"\n=== BILAN : {PASS} ✅  /  {FAIL} ❌  ({PASS}/{PASS + FAIL}) ===")
sys.exit(1 if FAIL else 0)
