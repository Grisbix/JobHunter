#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_lettre.py — Ce que la lettre decide seule (sans reseau).

Quatre choses que `tailor_application` tranche, et qu'aucune autre suite ne
couvre :

  1. LA REPRISE DE CLOTURE. « Monsieur Mac Arthur, » en tete et « agreer,
     Madame, Monsieur » en pied est la faute qui trahit le gabarit : la
     cloture doit repondre a l'appel, et s'accorder — « Messieurs » a deux
     hommes.

  2. LE PARAGRAPHE AGRICOLE. Le fonds Atlantic Agri et l'association
     Terres Solidaires valent devant un fonds de capital naturel et n'ont rien
     a faire devant un poste de controle de gestion. Le garde-fou est le meme
     que celui de la phrase durable : une MENTION ne vaut pas un SUJET.

     Le piege paye ici : « CREDIT AGRICOLE » contient « agricol ». Premiere
     mesure du motif, 91 offres retenues sur 5374 — et la liste etait faite de
     Credit Agricole Alpes Provence, du Morbihan, d'Aquitaine, Brie Picardie,
     CIB. Apres effacement de la marque : 49 offres, toutes agricoles.

  3. LE TITRE SANS LA SOCIETE. « Analyste Investissement - Capital Naturel -
     Mirova » donnait un objet « … - capital naturel - mirova », le nom propre
     passe en minuscules par `minuscule_titre`.

  4. LE CORPS ECRIT A LA MAIN. `Lettres/Sur_mesure/<entreprise>__<poste>.txt`
     remplace le corps du gabarit. La recherche du fichier echouait EN SILENCE
     quand la cle et le nom ne slugifiaient pas pareil : la lettre generique
     partait a sa place, sans un message.

Run : python test_lettre.py
"""
import _profil_test  # noqa: F401  — les tests tournent sur le profil d'exemple
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, __import__("pathlib").Path(__file__).resolve().parent.as_posix())

import profil as _profil   # noqa: E402
_AGRI = next(c for c in _profil.get("lettre.contextes") if c["nom"] == "agricole")
AGRI_FR, AGRI_EN = _AGRI["fr"], _AGRI["en"]
from tailor_application import (salutation, contexte_agricole,   # noqa: E402
                                _sans_societe,
                                corps_sur_mesure, _slug)

PASS = FAIL = 0


def check(nom, obtenu, attendu):
    global PASS, FAIL
    if obtenu == attendu:
        PASS += 1
        print(f"  ✅ {nom}")
    else:
        FAIL += 1
        print(f"  ❌ {nom}\n       attendu : {attendu!r}\n       obtenu  : {obtenu!r}")


def rep(rh, langue="fr"):
    """La reprise de cloture seule."""
    return salutation({"rh": rh}, langue)[1]


def nomme(rh, langue="fr"):
    return salutation({"rh": rh}, langue)[2]


print("\n── A. La reprise de cloture repond a l'appel ──")
check("deux hommes -> pluriel",
      rep("Monsieur Louis Mac Arthur et Monsieur Clément Lebrun"), "Messieurs")
check("deux femmes -> pluriel", rep("Madame Awa MOUSSA et Madame Mélanie GIRARD"),
      "Mesdames")
check("mixte -> la generique", rep("Madame Awa MOUSSA et Monsieur Charles DE GAULLE"),
      "Madame, Monsieur")
check("un seul homme", rep("Monsieur KEVIN SILVA PEREIRA"), "Monsieur")
check("une seule femme", rep("Madame Awa MOUSSA"), "Madame")
check("destinataire inconnu", rep(""), "Madame, Monsieur")
check("guichet", rep("Service Recrutement"), "Madame, Monsieur")
# L'anglais ne reprend pas la civilite : il ferme sur « Yours sincerely ».
check("anglais, nomme", rep("Monsieur Louis Mac Arthur", "en"), "Sir or Madam")

print("\n── B. Nommé ou pas — c'est ce qui choisit la cloture anglaise ──")
# « Yours faithfully » quand le destinataire est inconnu, « Yours sincerely »
# quand on l'a nomme. La lettre anglaise ecrivait « faithfully » en dur.
check("nom connu", nomme("Monsieur Louis Mac Arthur", "en"), True)
check("champ vide", nomme("", "en"), False)
check("URL LinkedIn", nomme("https://www.linkedin.com/search/results/people/?q=rh"), False)

print("\n── C. Le paragraphe agricole : l'intitule est souverain ──")
def agri(role="", texte="", societe="", langue="fr"):
    return contexte_agricole(dict(company=societe, role=role, offer_text=texte,
                                  missions="", profil=""), langue)


check("capital naturel dans l'intitule",
      agri(role="Analyste Investissement - Capital Naturel"), AGRI_FR)
check("  idem en anglais",
      agri(role="Investment Analyst - Natural Capital", langue="en"), AGRI_EN)
check("agroalimentaire dans l'intitule", agri(role="Analyste Agroalimentaire"), AGRI_FR)
check("regeneratif dans l'intitule",
      agri(role="Specialist - Regenerative Agriculture"), AGRI_FR)
check("intitule ordinaire, texte muet", agri(role="Analyste Risques Engagements"), "")

print("\n── D. Une mention ne vaut pas un sujet ──")
# Meme regle que la phrase durable : le mot lache au fil d'une enumeration de
# secteurs ne fait pas de l'annonce une offre agricole.
check("une seule mention -> rien",
      agri(role="Contrôleur de gestion",
           texte="Nos clients vont de l'agroalimentaire à l'aéronautique."), "")
check("deux mentions -> toujours rien",
      agri(role="Contrôleur de gestion",
           texte="Secteurs : agroalimentaire, forestier, aéronautique."), "")
check("trois occurrences -> le paragraphe",
      agri(role="Analyste financier",
           texte="Le fonds investit dans des terres agricoles et des pratiques "
                 "agricoles régénératrices, avec un volet forestier."), AGRI_FR)

print("\n── E. « CREDIT AGRICOLE » contient « agricol » ──")
# La famille sinGAPore / diveRSE / CLIMATisation / bp dans BPCE, recensee dans
# .claude/rules/motifs.md. 42 offres de la file tenaient a ce seul substrat.
check("la banque n'est pas une offre agricole",
      agri(role="Analyste risque de liquidité H/F", societe="Crédit Agricole CIB",
           texte="Crédit Agricole CIB recherche un analyste. Le Crédit Agricole "
                 "est un groupe bancaire. Crédit Agricole S.A. emploie…"), "")
check("  sans accent non plus",
      agri(role="Analyste Risques", societe="CREDIT AGRICOLE SA",
           texte="CREDIT AGRICOLE SA, credit agricole, Credit-Agricole"), "")
check("mais le marche agricole d'une banque, oui",
      agri(role="Analyste risques engagements - marché agricole",
           societe="Crédit Mutuel"), AGRI_FR)

print("\n── F. Le titre perd le nom de la societe ──")
check("suffixe societe", _sans_societe("Analyste Investissement - Capital Naturel - Mirova",
                                       "Mirova"), "Analyste Investissement - Capital Naturel")
check("separateur arobase", _sans_societe("Fraud & Risk Specialist (H/F) @Chargemap",
                                          "Chargemap"), "Fraud & Risk Specialist (H/F)")
check("barre verticale", _sans_societe("Analyst, Investment Operations | PGIM Ireland",
                                       "PGIM Ireland"), "Analyst, Investment Operations")
check("casse differente", _sans_societe("Data Scientist - tiktok", "TikTok"),
      "Data Scientist")
check("pas de suffixe : inchange",
      _sans_societe("Analyste ESG / Impact ESG", "Mirova"), "Analyste ESG / Impact ESG")
# Un titre qui n'est QUE le nom de la societe ne doit pas devenir vide.
check("titre reduit au nom : on ne vide pas", _sans_societe("Mirova", "Mirova"), "Mirova")
check("societe inconnue", _sans_societe("Analyste - Mirova", ""), "Analyste - Mirova")
# Un tiret dans un mot n'est pas un separateur (objet « F - Gas » chez Aggreko).
check("tiret dans un mot : intact",
      _sans_societe("F-Gas & Sustainability Analyst (H/F)", "AGGREKO FRANCE"),
      "F-Gas & Sustainability Analyst (H/F)")
check("tiret dans un mot, societe retiree",
      _sans_societe("Analyste LCB-FT - Mirova", "Mirova"), "Analyste LCB-FT")

print("\n── G. Le corps ecrit a la main se retrouve par son nom ──")
# Le fichier se nomme « <entreprise>__<poste>.txt ». La cle de recherche doit
# passer par _slug EN ENTIER, comme le nom du fichier : assembler deux slugs
# autour d'un « __ » litteral donnait « mirova__analyste… » face a un fichier
# reduit a « mirova_analyste… ». Le separateur double survivait d'un cote et
# pas de l'autre, et la lettre sur mesure n'etait jamais trouvee — sans erreur,
# la lettre generique partait a sa place.
def cle(societe, poste):
    return _slug(f"{societe}__{poste}")


check("la cle vaut le nom de fichier",
      cle("Mirova", "Analyste Investissement - Capital Naturel - Mirova"),
      _slug("Mirova__Analyste Investissement - Capital Naturel - Mirova"))
check("  ponctuation et casse sans effet",
      cle("MIROVA (Natixis)", "Analyste ESG / Impact"),
      _slug("mirova-natixis__analyste_esg_impact"))
check("accents : deux orthographes ne se confondent pas",
      cle("Société X", "Chargé d'études") == cle("Societe X", "Charge d'etudes"), False)
check("aucun fichier pour cette offre -> le gabarit reprend la main",
      corps_sur_mesure(dict(company="Entreprise Inexistante 4242",
                            role="Poste Imaginaire")), [])

print("\n── H. verifie_redites coupe l'en-tete, quelle que soit la formule ──")
# BUG CAUSE PAR LA FORMULE NOMINATIVE. `corps()` cherchait « Madame, » ou
# « Dear  » en debut de ligne : les deux seules formules que la lettre savait
# ecrire avant. Depuis qu'elle nomme le recruteur, l'en-tete n'etait plus coupe
# du tout, et le nom, le courriel, le telephone et l'objet entraient dans le
# comptage. La lettre Mirova s'est vu reprocher « 2 conjonctions » dans un bloc
# qui commencait par « Camille Exemple ».
from verifie_redites import corps   # noqa: E402

EN_TETE = ("Camille Exemple\ncamille.exemple@example.com\n+33 6 00 00 00 00\n"
           "Le 21 septembre 2026\nObjet : Candidature au poste d'analyste\n")


def coupe(appel):
    return corps(EN_TETE + appel + "\nLe corps commence ici.").strip()


for nom, appel in [("generique francaise", "Madame, Monsieur,"),
                   ("generique anglaise", "Dear Sir or Madam,"),
                   ("un homme nomme", "Monsieur Mac Arthur,"),
                   ("deux hommes nommes", "Monsieur Mac Arthur, Monsieur Lebrun,"),
                   ("deux femmes nommees", "Madame Moussa, Madame Girard,"),
                   ("anglais nominatif", "Dear Mr Mac Arthur and Mr Lebrun,"),
                   ("ton detendu", "Bonjour,")]:
    check(nom, coupe(appel), "Le corps commence ici.")
# Une lettre sans formule reconnue rend tout : mieux vaut trop de texte qu'un
# corps vide, qui ferait passer n'importe quelle redite.
check("formule inconnue : on ne perd pas le corps",
      "Le corps commence ici." in corps(EN_TETE + "Salut,\nLe corps commence ici."), True)

print("\n── I. La langue du document suit le LIEU quand le texte est muet ──")
# Mesure du 2026-09-22, apres l'elargissement a douze pays : 1 809 offres
# etrangeres sur 1 814 etaient classees « fr ». La recherche publique LinkedIn
# ne rend que le titre et le lieu, le texte reste sous les 120 caracteres qui
# permettent de trancher, et la regle retombait sur le francais. Un CV francais
# envoye a Stockholm ou a Francfort, c'est se disqualifier avant lecture.
from langue import langue_offre   # noqa: E402


def lg(titre, lieu=""):
    return langue_offre(titre, "", lieu)


check("Suede", lg("Sustainability Analyst", "Stockholm, Sweden"), "en")
check("Allemagne", lg("(Junior) Consultant ESG Assurance", "Frankfurt, Germany"), "en")
check("Espagne", lg("Analista de Sostenibilidad", "Madrid, Spain"), "en")
check("Singapour", lg("ESG Analyst", "Singapore"), "en")
check("France", lg("Analyste ESG", "Paris, France"), "fr")
check("Bordeaux sans le mot France", lg("Analyste ESG", "Bordeaux · Nouvelle-Aquitaine"), "fr")
check("Luxembourg", lg("ESG Analyst", "Luxembourg"), "fr")
# Premier essai : une liste de villes ecrite dans langue.py. Elle ratait ces
# deux-la, francaises mais sans le mot « France » ni de ville connue de la
# liste. `zones.zone_lieu` les classe correctement, et c'est lui qui decide.
check("Grenoble, sans le mot France",
      lg("Analyste ESG", "Grenoble (38) · Auvergne-Rhône-Alpes"), "fr")
check("code postal et region",
      lg("Gestionnaire des risques", "33700 Mérignac · Nouvelle-Aquitaine"), "fr")
# La Suisse n'a pas une seule langue de travail : le lieu decide, pas le pays.
check("Suisse romande", lg("ESG Analyst", "Geneva, Switzerland"), "fr")
check("  Zurich, pas romande", lg("ESG Analyst", "Zurich, Switzerland"), "en")
check("  Bâle non plus", lg("ESG Analyst", "Basel, Switzerland"), "en")
# Sans lieu, le comportement d'avant : le doute profite au francais.
check("lieu inconnu : comportement d'avant", lg("ESG Analyst", ""), "fr")
# Un texte LONG tranche tout seul, le lieu ne doit pas le contredire.
_EN = ("We are looking for the analyst who will be in charge of the reporting and of "
       "the data, with a strong interest in the regulation and in all of our climate "
       "work, and you will be part of a team that is growing fast in our group. ")
check("texte long anglais, lieu francais",
      langue_offre("Analyste", _EN, "Paris, France"), "en")

print(f"\n=== BILAN : {PASS} ✅  /  {FAIL} ❌  ({PASS}/{PASS + FAIL}) ===")
sys.exit(1 if FAIL else 0)
