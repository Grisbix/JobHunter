#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tailor_application.py — Adapte CV + lettre a CHAQUE offre.

Fonctions d'adaptation CV+lettre (appelées par generate_docs.py / add_offer.py),
matche le texte de l'offre contre un lexique ESG-finance REEL (pas le persona tech),
puis :
  - CV  : copie la variante ATS choisie, injecte le titre du poste + une ligne
          "Competences ciblees : <skills matches>" -> CV/Par_offre/
  - Lettre : genere une lettre .docx dont l'intro/corps reference les missions
          reelles de l'offre + les competences matchees -> Lettres/Par_offre/

CLI : generate_docs.py (lots depuis la queue) / add_offer.py (1 offre).
"""
import argparse
import os
import re
import sys
import json
import shutil
import subprocess
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

ROOT = Path(__file__).resolve().parent.parent
# Les sorties volumineuses vivent la ou chemins.py les place — hors de OneDrive
# quand Scripts/chemins.json le dit. Les MODELES, eux, restent dans le depot.
sys.path.insert(0, str(ROOT / "Scripts"))   # importable depuis n'importe ou
import chemins
CV_ATS = chemins.CV_MODELES
CV_OUT, LT_OUT = chemins.preparer()

# ---- Profil candidat : tout vient de profil/profil.json (voir profil.py) ----
import profil as _P
_ID = _P.identite()
PROFILE = dict(nom=_ID["nom"], ville=_ID["ville"], email=_ID["email"], tel=_ID["tel"])

# Un domaine du profil = une variante de CV + un paragraphe de parcours.
# Le DERNIER domaine est le repli.
_DOMAINES = _P.domaines()
CV_VARIANT = {d["cle"]: d.get("cv") or "" for d in _DOMAINES}
CV_VARIANT_EN = {d["cle"]: d.get("cv_en") or "" for d in _DOMAINES}


def cv_variant_key(domaine):
    """Cle de domaine du profil pour un champ `domaine` d'offre.

    Accepte la cle elle-meme, son libelle (« Finance »), ou un texte libre lu
    avec les mots d'intitule des domaines ; sinon le domaine de repli."""
    d = (domaine or "").strip()
    bas = d.lower()
    for x in _DOMAINES:
        if bas in (x["cle"].lower(), str(x.get("libelle", "")).lower()):
            return x["cle"]
    for x in _DOMAINES[:-1]:
        if _P.cherche(_P.motif(x.get("mots_titre")), d):
            return x["cle"]
    return _DOMAINES[-1]["cle"]


# ---- Lexique de competences (libelle -> synonymes a chercher dans l'offre) ----
_COMP = _P.get("competences", {}) or {}
SKILL_LEX = {lab: list(v.get("synonymes") or []) for lab, v in _COMP.items()}
# accroche valeur par entreprise : profil, lettre.valeurs_entreprises_fr/en
COMPANY_VALUE = dict(_P.get("lettre.valeurs_entreprises_fr", {}) or {})

# Mots qui gardent leur majuscule dans un intitule de poste : noms propres
# residuels. La regle generale est qu'un intitule francais est un NOM COMMUN
# (« contrôleur de gestion », pas « Contrôleur de Gestion »), mais les annonces
# capitalisent chaque mot a l'anglaise et on recopiait tel quel.
_PROPRES = {"france", "paris", "europe", "afrique", "asie", "amerique", "amérique",
            "allemagne", "espagne", "italie", "belgique", "suisse", "luxembourg",
            "benelux", "emea", "monde"}

# Les sigles qui gardent leurs capitales meme dans un intitule hurle. Liste
# EXPLICITE : aucune regle de longueur ne separe « ESG » de « DES ».
_SIGLES = {"ESG", "RSE", "ISR", "SFDR", "CSRD", "CSDDD", "GRI", "TCFD", "SASB",
           "PAI", "DCF", "LBO", "M&A", "IFRS", "EBITDA", "KPI", "ERP", "SAP",
           "IT", "SI", "DSI", "BI", "SQL", "VBA", "IA", "AI", "ML", "LLM",
           "RH", "QHSE", "HSE", "RGPD", "AMF", "ACPR", "BFR", "FP&A", "PME",
           "ETI", "ONG", "SRI", "UX", "UI", "API", "CRM", "PMO", "MOA", "MOE"}


def minuscule_titre(t):
    """« Contrôleur de Gestion Financier » -> « contrôleur de gestion financier ».

    Un sigle reste intact (« Analyste RSE-ESG » garde RSE-ESG), un nom propre
    connu aussi. Tout le reste passe en bas de casse : en francais un intitule
    de poste est un nom commun.

    MAIS une annonce peut etre ecrite ENTIEREMENT en capitales — « CORPORATE
    FINANCE », « GESTIONNAIRE DES RISQUES ». Prendre chaque mot pour un sigle
    laissait alors l'objet de la lettre hurler. Quand la majorite des mots
    longs sont en capitales, c'est une annonce qui crie, pas une suite de
    sigles : on abaisse TOUT, et on ne releve que les sigles reconnus.

    La longueur ne suffit pas a distinguer un sigle : « DES » fait trois
    lettres et reste un article, d'ou « gestionnaire DES risques ».
    """
    mots = (t or "").split(" ")
    longs = [m.strip(",.;:()[]") for m in mots if len(m.strip(",.;:()[]")) > 4]
    crie = bool(longs) and sum(1 for m in longs if m.upper() == m) > len(longs) / 2

    sortie = []
    for m in mots:
        nu = m.strip(",.;:()[]")
        if not nu:
            sortie.append(m)
        elif nu.lower() in _PROPRES:
            # Un nom propre garde sa majuscule, mais pas TOUTES ses capitales :
            # « CHARGE DE MISSION RSE FRANCE » donnait « … RSE FRANCE ».
            sortie.append(m.capitalize() if crie else m)
        elif crie:
            sortie.append(m if nu.upper() in _SIGLES else m.lower())
        elif nu.upper() == nu and any(c.isalpha() for c in nu):
            sortie.append(m)                     # sigle : RSE, M&A, IT, SAP
        else:
            sortie.append(m.lower())
    return " ".join(sortie)


def _de(mot, apostrophe="'"):
    """Élision : 'de Amundi' -> \"d'Amundi\".

    'h' et 'y' EXCLUS : « de Hollande » et « de Yann » sont corrects, pas « d'Hollande ».

    `apostrophe` : le gabarit de CV est écrit avec l'apostrophe TYPOGRAPHIQUE
    (« d’une expertise », « d’un mémoire »). Y injecter une apostrophe droite
    donnait, dans la même phrase : « d’un poste d'Analyste RSE-ESG ». Deux
    apostrophes différentes à six mots d'intervalle, sur un CV.
    """
    mot = (mot or "").strip()
    if mot[:1].lower() in "aàâäeéèêëiîïoôöuùûü":
        return "d" + apostrophe + mot
    return "de " + mot


# ── Nettoyage de l'intitulé de poste ────────────────────────────────────────
# Le titre brut d'une annonce n'est PAS un intitulé de poste : il porte la mention
# de genre, le type de contrat, la ville, la référence interne… Écrit tel quel dans
# « Objet : Candidature au poste de … », il donne des lettres illisibles.
# Les \b sont INDISPENSABLES : sans eux, « DAF - Finance » matche « F - F »
# (le F final de DAF, le tiret, le F initial de Finance) et le nettoyage produit
# « DA inance ». Le motif ne doit accepter que des lettres ISOLEES.
RX_GENRE = re.compile(r"[(\[]?\s*\b[HFMWX]\b(?:\s*[/|.-]\s*\b[HFMWXD]\b){1,2}\s*[)\]]?", re.I)
# Le marqueur de genre COLLE, sans separateur : « CORPORATE FINANCE HF ».
# RX_GENRE exige un separateur (H/F, H-F, H.F) et laissait donc passer celui-ci,
# si bien que l'objet annoncait un poste de « corporate finance hf ». Ancre en
# FIN de chaine seulement : ailleurs, « HF » peut vouloir dire haute frequence.
RX_GENRE_COLLE = re.compile(r"\s*[(\[]?\s*\b(?:HF|FH|MW|FM|MF)\b\s*[)\]]?\s*$", re.I)
RX_CONTRAT = re.compile(
    r"\b(CDI|CDD|VIE|V\.I\.E|int[ée]rim|freelance|temps\s+plein|temps\s+partiel|"
    r"full[\s-]?time|part[\s-]?time|permanent|remote|t[ée]l[ée]travail|hybride|"
    r"\d+\s*mois|\d+\s*months|\d+\s*ans)\b", re.I)
RX_BRUIT = re.compile(r"\b(nouveau|new|urgent|poste\s+\d+|r[ée]f\.?\s*\S+|"
                      r"job\s*id\s*:?\s*\d+|\d{3,}\s*days?)\b", re.I)
# « #00137324 » : aucun caractère de mot devant le #, donc un \b devant ne matcherait JAMAIS
RX_REF = re.compile(r"#\s*\d+")
RX_LIEU_FIN = re.compile(r"[\s,(-]+[A-ZÀ-Ý][\wÀ-ÿ'-]*\s*\(?\d{5}\)?\s*\)?\s*$")
RX_ADRESSE = re.compile(r"\b\d{1,4}\s+(rue|avenue|boulevard|impasse|chemin|place)\b"
                        r"|\b\d{5}\s+[A-ZÀ-Ý]", re.I)

for _n, _rx in list(globals().items()):
    # Un « \b » mangé par un heredoc devient \x08 : le motif ne matche plus jamais,
    # sans erreur. On refuse de démarrer plutôt que de générer des lettres fausses.
    if _n.startswith("RX_") and hasattr(_rx, "pattern"):
        assert "\x08" not in _rx.pattern, "motif corrompu (backspace littéral) : " + _n


def titre_poste(t, maxlen=80):
    """Intitulé lisible à partir du titre brut d'une annonce.

    Coupe au dernier séparateur AVANT maxlen, jamais au milieu d'un mot.
    Renvoie "" si ce n'est pas un intitulé de poste (adresse postale, vide) :
    l'appelant écrit alors une formule neutre plutôt qu'une phrase absurde.
    """
    t = re.sub(r"\s+", " ", (t or "").strip())
    if RX_ADRESSE.search(t):
        return ""
    t = RX_GENRE.sub(" ", t)
    t = RX_GENRE_COLLE.sub("", t)
    t = RX_CONTRAT.sub(" ", t)
    t = RX_BRUIT.sub(" ", t)
    t = RX_REF.sub(" ", t)
    # Parentheses vides ou reduites a des chiffres/ponctuation par les coupes
    # precedentes : « CDD (2.5 mois) » laissait « - (2. ) » une fois le contrat
    # et la duree retires.
    t = re.sub(r"[(\[]\s*[\d.,;:\s-]*\s*[)\]]", " ", t)
    t = re.sub(r"\s*,(\s*,)+", ",", t)
    t = RX_LIEU_FIN.sub("", t)
    # séparateurs : uniquement ceux ENTOURÉS d'espaces — « LCB-FT » et « H2-Power »
    # sont des mots, pas des séparateurs
    t = re.sub(r"\s+[-–—:|]\s+", " - ", t)
    t = re.sub(r"\s*[–—:|]\s*", " - ", t)
    t = re.sub(r"(\s*-\s*){2,}", " - ", t)
    t = re.sub(r"\s{2,}", " ", t).strip(" -,.;:|")
    if len(t) > maxlen:
        coupe = t[:maxlen]
        for sep in (" - ", ", ", " "):
            i = coupe.rfind(sep)
            if i > maxlen * 0.5:
                coupe = coupe[:i]
                break
        t = coupe.strip(" -,.;:|")
    return t

def _citable(t, langue):
    """Ce passage peut-il etre CITE dans une lettre ecrite en `langue` ?

    Une citation dans l'autre langue saute aux yeux : la lettre anglaise pour
    TotalEnergies Congo — dont l'annonce est francaise mais qui demande
    « Merci de candidater en anglais » — citait « Bac+5 ecole d'ingenieurs ou
    de commerce, specialisation economie ou finance ; connaissances en economie
    et finance d'entreprise » en plein milieu d'un paragraphe anglais.

    Mieux vaut PAS DE CITATION qu'une citation dans la mauvaise langue : la
    phrase qui la porte est facultative, elle disparait proprement.
    """
    t = (t or "").strip()
    if len(t) <= 15:
        return False
    try:
        from langue import langue_offre
        # langue_offre exige 120 caracteres pour se prononcer ; en dessous il
        # repond « fr » par defaut, ce qui ferait taire toute citation courte
        # dans une lettre anglaise. On ne tranche donc que sur un texte assez
        # long pour etre juge.
        if len(t) < 120:
            return True
        return langue_offre("", t) == langue
    except Exception:
        return True


def _coupe_mot(t, n):
    """Tronque a n caracteres SANS couper un mot, et sans laisser de ponctuation
    pendante. « …help to build a better wor » est parti dans une vraie lettre :
    une citation coupee en plein mot est plus visible qu'une citation absente."""
    t = " ".join((t or "").split())
    if len(t) <= n:
        return t.rstrip(" ,;:.-")
    coupe = t[:n]
    i = coupe.rfind(" ")
    if i > n * 0.6:
        coupe = coupe[:i]
    return coupe.rstrip(" ,;:.-") + "…"


# Paragraphe de parcours, par domaine d'offre. Memes faits, ordre et accent
# differents — la cle est celle de cv_variant_key, donc la lettre raconte le
# meme parcours que le CV joint.
# Une phrase ne porte qu'UNE conjonction. Au-dela, les propositions se collent
# bout a bout au lieu de s'enchainer, et la lettre se lit comme une liste :
#   « …valorisation par DCF ET analyse de bilan, ET labellisation
#     SFDR… » — trois « et » dans la meme phrase.
# Le deux-points et la virgule font le meme travail sans rien ajouter au bruit.
# Ni tiret cadratin ni barre oblique non plus : « risque/performance » s'ecrit
# « le risque et la performance ».
SOCLE_FR = {d["cle"]: d.get("parcours_fr") or "" for d in _DOMAINES}
SOCLE_EN = {d["cle"]: d.get("parcours_en") or "" for d in _DOMAINES}


def socle(cle, langue="fr"):
    """Paragraphe de parcours du domaine `cle`, ou celui du premier domaine
    qui en a un : une lettre sans parcours ne dit rien du candidat."""
    table = SOCLE_EN if langue == "en" else SOCLE_FR
    if table.get(cle):
        return table[cle]
    return next((v for v in table.values() if v), "")


def company_value(company):
    """Accroche connue pour cette entreprise, ou "" : quand l'entreprise est
    inconnue, la lettre ne lui prete AUCUN engagement, elle parle du poste."""
    c = (company or "").lower()
    for k, v in COMPANY_VALUE.items():
        if k in c:
            return v
    return ""


# ── PARAGRAPHES DE CONTEXTE ──────────────────────────────────────────────────
# Le profil peut declarer des faits qui ne valent que devant certaines offres
# (`lettre.contextes`) : une experience dans un secteur, un engagement associatif.
# Chacun porte ses mots declencheurs. Regles, toutes apprises sur des lettres
# reelles :
#   - l'INTITULE est souverain : un mot declencheur dans l'intitule suffit ;
#   - sinon il faut `occurrences_min` occurrences dans le texte (une MENTION
#     de passage — « nos clients vont de l'agroalimentaire a l'aeronautique » —
#     ne vaut pas un SUJET) ;
#   - `ignorer` efface des noms propres trompeurs avant de compter (« Credit
#     Agricole » contient « agricol ») ;
#   - `densite_coeur` : le texte doit aussi etre dense en vocabulaire de l'axe
#     coeur, comme le scoring l'exige (anti-boilerplate) ;
#   - `sauf_domaines` : inutile quand le parcours choisi dit deja la meme chose ;
#   - UN SEUL contexte par lettre, le premier de la liste qui s'applique :
#     le concret chasse le generique, deux paragraphes voisins se repetaient.
_CONTEXTES = _P.get("lettre.contextes", []) or []


def _contexte_applicable(ctx, offer):
    if cv_variant_key(offer.get("domaine")) in (ctx.get("sauf_domaines") or []):
        return False
    rx = _P.motif(ctx.get("mots"))
    if rx is None:
        return False
    ign = _P.motif(ctx.get("ignorer"))

    def net(t):
        return ign.sub(" ", t or "") if ign else (t or "")
    role = net(str(offer.get("role") or ""))
    if rx.search(role):
        return True
    texte = net(" ".join(str(offer.get(k) or "") for k in
                         ("company", "role", "offer_text", "missions", "profil")))
    if len(rx.findall(texte)) < int(ctx.get("occurrences_min") or 1):
        return False
    if ctx.get("densite_coeur"):
        # Import differe : ats_match importe ce module.
        from ats_match import densite_esg, _ESG_DENSITE_MIN, _ESG_DENSITE_LONG
        if len(texte) >= _ESG_DENSITE_LONG and densite_esg(texte) < _ESG_DENSITE_MIN:
            return False
    return True


def contexte(offer, langue="fr", position=None):
    """(position, texte) du contexte a ajouter, ou ("", "").
    position : "socle" (ajoute au parcours) ou "paragraphe" (paragraphe a part).

    `position` restreint la recherche a une seule position. Sans elle, le
    PREMIER contexte applicable masquait les autres : une offre a la fois
    agricole (paragraphe) et durable (socle) perdait la phrase durable du
    message, que le code d'origine ajoutait independamment (Ortec, 15/10)."""
    for ctx in _CONTEXTES:
        if position and (ctx.get("position") or "paragraphe") != position:
            continue
        if _contexte_applicable(ctx, offer):
            t = ctx.get("en" if langue == "en" else "fr") or ""
            if t:
                return ctx.get("position") or "paragraphe", t
    return "", ""


def contexte_durable(offer, langue="fr"):
    """Compatibilite : le texte d'un contexte place dans le socle, ou ""."""
    return contexte(offer, langue, "socle")[1]


def contexte_agricole(offer, langue="fr"):
    """Compatibilite : le texte d'un contexte en paragraphe a part, ou ""."""
    return contexte(offer, langue, "paragraphe")[1]


# ── A QUI LA LETTRE S'ADRESSE ────────────────────────────────────────────────
# Jusqu'ici la lettre ouvrait sur « Madame, Monsieur, » en dur, et fermait sur
# « Je vous prie d'agreer, Madame, Monsieur ». Le message, lui, savait deja
# nommer le recruteur depuis `message_offre.appel()`. Deux documents partant
# dans la meme enveloppe, l'un nominatif et l'autre pas.
#
# UNE ANNONCE PEUT EN NOMMER DEUX. Mirova ecrit « adressez votre CV et votre
# lettre a Louis Mac Arthur et Clement Lebrun » — deux destinataires, dont
# `appel()` ne sait rien : il traite UNE personne, et ses 26 cas de test
# valent pour ce contrat-la. On ne le modifie donc pas ; on le rappelle une
# fois par nom.
#
# GARDE-FOU : la decoupe n'est retenue QUE si chaque morceau rend une formule
# nominative. Un seul fragment generique, et on retombe sur le champ entier,
# donc sur le comportement d'avant. « Monsieur Jean et Marie Dupont » ne
# produira jamais « Monsieur Jean, Madame Dupont ».
_CIV_FEM = {"madame", "mme", "mrs", "ms"}


def _reprise(civs, langue):
    """La civilite SEULE, pour la formule de cloture.

    « Je vous prie d'agreer, Monsieur Mac Arthur, Monsieur Lebrun » ne se dit
    pas : la reprise porte la civilite, jamais le patronyme. A deux hommes elle
    s'accorde au pluriel — « Messieurs ».
    """
    connus = [c for c in civs if c]
    if not connus or len(connus) != len(civs):
        return "Madame, Monsieur" if langue != "en" else "Sir or Madam"
    fem = [c in _CIV_FEM for c in connus]
    if langue == "en":
        return "Sir or Madam"          # l'anglais ferme sur « Yours sincerely »
    if all(fem):
        return "Madame" if len(connus) == 1 else "Mesdames"
    if not any(fem):
        return "Monsieur" if len(connus) == 1 else "Messieurs"
    return "Madame, Monsieur"


# ── LE CORPS ECRIT A LA MAIN ─────────────────────────────────────────────────
# Le gabarit sert 5374 annonces. Il ne peut donc rien dire de precis sur
# aucune : il nomme des competences, jamais un fonds, jamais une mission de
# l'annonce. C'est le bon compromis pour une candidature de masse et le
# mauvais pour les cinq offres de l'annee qui meritent une heure de travail.
#
# Quand `Lettres/Sur_mesure/<entreprise>__<poste>.txt` existe, ses paragraphes
# remplacent le CORPS. Tout le reste continue d'etre genere : l'en-tete, la
# date, l'objet, la formule d'appel — qui sait nommer deux destinataires — et
# la reprise de cloture accordee. On ne reecrit pas a la main ce que le code
# fait mieux.
#
# C'est une ENTREE, au meme titre que CV/Modeles : `regenere_docs.py` ne la
# touche pas, et regenerer la lettre la reprend telle quelle.
_RX_SLUG = re.compile(r"[^a-z0-9]+")


def _slug(s):
    return _RX_SLUG.sub("_", (s or "").lower()).strip("_")


def corps_sur_mesure(offer):
    """Les paragraphes ecrits a la main pour cette offre, ou [] s'il n'y en a
    pas. Le fichier se nomme `<entreprise>__<poste>.txt`, paragraphes separes
    par une ligne vide.

    La recherche est TOLERANTE a la casse et a la ponctuation : le nom de
    fichier vient d'un intitule d'annonce, ou l'on trouve des barres obliques,
    des parentheses et des majuscules aleatoires. Windows ignorant deja la
    casse, chercher a l'identique ne donnerait qu'un faux negatif silencieux.
    """
    from chemins import LT_SUR_MESURE
    if not LT_SUR_MESURE.exists():
        return []
    # Le nom cible passe par _slug EN ENTIER, comme celui du fichier. Assembler
    # deux slugs autour d'un « __ » litteral donnait « mirova__analyste… » face
    # a un fichier reduit a « mirova_analyste… » : le separateur double survit
    # d'un cote et pas de l'autre, et la lettre sur mesure ne se trouve jamais.
    vise = _slug(f"{offer.get('company')}__{offer.get('role')}")
    for f in LT_SUR_MESURE.glob("*.txt"):
        if _slug(f.stem) == vise:
            texte = f.read_text(encoding="utf-8")
            return [p.strip() for p in re.split(r"\n\s*\n", texte) if p.strip()]
    return []


def cv_sur_mesure(offer):
    """Les retouches de CV ecrites a la main pour cette offre, ou None.

    `CV/Sur_mesure/<entreprise>__<poste>.json`, meme nom tolerant que la lettre :
        {"remplace":    [["texte du modele", "texte pour cette offre"], ...],
         "ajoute_apres": [["texte d'un paragraphe du modele", "nouveau paragraphe"], ...],
         "supprime":    ["texte d'un paragraphe a retirer", ...]}

    `supprime` existe pour la page : ajouter une ligne propre a l'offre fait
    souvent passer le CV a deux pages, et la place se reprend sur ce que cette
    offre-la ne lit pas.

    Le modele reste la source : on ne retouche que ce que l'offre demande, et la
    regeneration reprend les retouches au lieu de les ecraser."""
    import json
    from chemins import CV_SUR_MESURE
    if not CV_SUR_MESURE.exists():
        return None
    vise = _slug(f"{offer.get('company')}__{offer.get('role')}")
    for f in CV_SUR_MESURE.glob("*.json"):
        if _slug(f.stem) == vise:
            return json.loads(f.read_text(encoding="utf-8"))
    return None


def appliquer_cv_sur_mesure(doc, retouches):
    """Applique les retouches a un Document. Rend la liste des ancres introuvables.

    Le remplacement se fait DANS le run qui porte le texte : la ligne d'une
    experience melange un intitule gras et une date tabulee, et reecrire le
    paragraphe entier perdrait cette mise en forme. Une ancre introuvable est
    SIGNALEE, jamais ignoree : le modele a pu changer, et une retouche qui ne
    s'applique plus enverrait le CV generique sans un mot."""
    import copy
    manquees = []
    for ancien, nouveau in retouches.get("remplace", []):
        fait = False
        for p in doc.paragraphs:
            for r in p.runs:
                if ancien in r.text:
                    r.text = r.text.replace(ancien, nouveau)
                    fait = True
            if not fait and ancien in p.text:
                txt = p.text.replace(ancien, nouveau)
                for r in p.runs:
                    r.text = ""
                p.runs[0].text = txt
                fait = True
        if not fait:
            manquees.append(ancien)
    for ancre, texte in retouches.get("ajoute_apres", []):
        p = next((p for p in doc.paragraphs if ancre in p.text), None)
        if p is None:
            manquees.append(ancre)
            continue
        el = copy.deepcopy(p._p)
        p._p.addnext(el)
        from docx.text.paragraph import Paragraph
        neuf = Paragraph(el, p._parent)
        for r in neuf.runs:
            r.text = ""
        neuf.runs[0].text = texte
    for ancre in retouches.get("supprime", []):
        p = next((p for p in doc.paragraphs if ancre in p.text), None)
        if p is None:
            manquees.append(ancre)
            continue
        p._p.getparent().remove(p._p)
    return manquees


def _sans_societe(role, company):
    """Retire du titre le nom de la societe quand l'annonce l'y a colle.

    « Analyste Investissement - Capital Naturel - Mirova » donnait un objet de
    lettre « Candidature au poste d'analyste investissement - capital naturel -
    mirova » : le nom propre passe en minuscules par `minuscule_titre`, qui a
    raison de le faire pour un intitule et tort pour une marque.

    8 offres de la file sur 5374 sont dans ce cas. On ne touche QUE l'objet :
    le nom de fichier continue de deriver du titre brut, sinon les documents
    deja generes se retrouveraient orphelins.
    """
    r, c = (role or "").strip(), (company or "").strip()
    if not c:
        return r
    # Un tiret court n'est un separateur qu'ENTOURE d'espaces : « F-Gas » et
    # « LCB-FT » sont des mots. Couper dessus puis recoller par « - » donnait
    # l'objet « F - Gas & Sustainability Analyst » (Aggreko, 2026-10-04).
    coupe = re.split(r"\s+-\s+|\s*[–—|@]\s*", r)
    if len(coupe) < 2 or coupe[-1].strip().lower() != c.lower():
        return r
    while len(coupe) > 1 and coupe[-1].strip().lower() == c.lower():
        coupe.pop()
    return " - ".join(coupe).strip() or r


def salutation(offer, langue="fr"):
    """Rend (formule d'appel, reprise de cloture, nominative ?).

    LE TEXTE DE L'APPEL VIENT DE `message_offre.appel`, qui sait deja le faire
    et dont 26 cas de test le verifient — decoupe des destinataires multiples
    comprise. Ce qu'on ajoute ici est propre a la LETTRE : la reprise de
    cloture, que le message n'a pas.
    """
    from message_offre import appel, nom_dans_offre, _RX_CIVILITE, _RX_SEPARE, GENERIQUES
    rh = (offer.get("rh") or "").strip()
    # Un destinataire que l'annonce ne nomme pas n'est pas nomme (2026-10-07).
    if offer.get("offer_text") is not None:
        rh = nom_dans_offre(rh, offer.get("offer_text"))
    texte = appel({"rh": rh}, langue)
    if texte in GENERIQUES:
        return texte, ("Sir or Madam" if langue == "en" else "Madame, Monsieur"), False

    # Les civilites effectivement retenues, dans l'ordre, pour accorder la
    # reprise. On relit les morceaux plutot que la formule produite : « Madame
    # Moussa » et « Monsieur de Gaulle » s'y distinguent sans avoir a redecouper
    # du texte deja mis en forme.
    morceaux = [x.strip() for x in _RX_SEPARE.split(rh) if x.strip()] or [rh]
    civs = []
    for x in morceaux:
        if appel({"rh": x}, langue) in GENERIQUES and len(morceaux) > 1:
            continue                       # morceau ecarte par `appel`
        g = _RX_CIVILITE.match(x)
        civs.append(g.group(1).lower() if g else "")
    return texte, _reprise(civs, langue), True

# Libelles de competences en ANGLAIS. La lettre anglaise les cite en toutes
# lettres ; les laisser en francais trahit la generation automatique plus
# surement qu'une faute de style. Les sigles reglementaires (SFDR, CSRD, GRI,
# TCFD, PAI) ne se traduisent PAS : ce sont les memes textes europeens.
SKILL_EN = {lab: v.get("en") or lab for lab, v in _COMP.items()}


_SKILL_EN_NORM = None


def skills_en(labels):
    """Libelles traduits. La recherche ignore les ACCENTS : les cles de SKILL_EN
    sont ecrites sans eux, les libelles reels en portent (« Analyse financiere »
    contre « Analyse financiere »). Comparer tels quels ne trouvait rien et la
    lettre anglaise restait farcie de francais.

    Un libelle inconnu est RENDU TEL QUEL plutot que supprime : mieux vaut un
    mot francais visible qu'une competence disparue."""
    global _SKILL_EN_NORM
    if _SKILL_EN_NORM is None:
        from jutil import sans_accent
        _SKILL_EN_NORM = {sans_accent(k).lower(): v for k, v in SKILL_EN.items()}
    from jutil import sans_accent
    return [_SKILL_EN_NORM.get(sans_accent(x).lower(), x) for x in labels]


def company_value_en(company):
    """Accroche anglaise connue, ou "" (meme regle que company_value)."""
    c = (company or "").lower()
    for k, v in COMPANY_VALUE_EN.items():
        if k in c:
            return v
    return ""


COMPANY_VALUE_EN = dict(_P.get("lettre.valeurs_entreprises_en", {}) or {})


# ---- moteur match keyword ----
# Les sigles COURTS doivent matcher le mot ENTIER. En sous-chaîne ils partaient en
# vrille : 'ges' (gaz à effet de serre) matchait « GEStion », 'gri' « aGRIcole »,
# 'pai' « PAIement », 'var' « VARiable ». Ici l'enjeu dépasse le scoring : ces
# libellés sont IMPRIMÉS sur le CV envoyé au recruteur.
_SHORT = 4
_RX_SKILL = {lab: [re.compile(r"\b" + re.escape(n.strip()) + r"\b")
                   for n in ns if len(n.strip()) <= _SHORT]
             for lab, ns in SKILL_LEX.items()}
_SUB_SKILL = {lab: [n for n in ns if len(n.strip()) > _SHORT]
              for lab, ns in SKILL_LEX.items()}

def has_skill(label, t):
    """Le libellé est-il présent dans le texte (déjà en minuscules) ?"""
    return (any(n in t for n in _SUB_SKILL[label])
            or any(r.search(t) for r in _RX_SKILL[label]))

# Libelles qui servent au SCORING mais ne s'ecrivent pas dans une lettre : ce
# sont des noms de categorie internes, pas des competences. « Durabilité / ESG
# (généraliste) » s'est retrouve tel quel, parentheses comprises, dans une
# lettre anglaise envoyee a EY Geneve — au milieu de SFDR et GRI/TCFD, il
# signalait le systeme qui l'avait ecrite.
SKILL_INTERNES = {lab for lab, v in _COMP.items() if v.get("interne")}


# Les libelles de competence tels qu'ils s'ecrivent DANS UNE PHRASE. Sur le CV
# ce sont des etiquettes de rubrique, ou « Trésorerie / financement » et les
# capitales initiales sont normales. Recopies dans la lettre, ils donnaient :
#
#   « je me suis familiarisé avec Analyse financière, Modélisation financière,
#     Trésorerie / financement, Contrôle de gestion. »
#
# Quatre majuscules parasites et une barre oblique au milieu d'une phrase. Ca
# se lit comme un export de base de donnees, pas comme une lettre. L'article
# est inclus parce qu'il depend du mot (le, la, l', les) et qu'aucune regle
# simple ne le devine.
SKILL_PROSE_FR = {lab: v["prose_fr"] for lab, v in _COMP.items() if v.get("prose_fr")}
SKILL_PROSE_EN = {lab: v["prose_en"] for lab, v in _COMP.items() if v.get("prose_en")}


def _enumere(items, langue="fr"):
    """« a, b et c ». Une enumeration se termine par une conjonction, pas par
    une virgule : sans elle, la phrase se lit comme une liste a puces mise bout
    a bout.

    Un element peut CONTENIR la conjonction (« la trésorerie et le financement »,
    « Python et SQL »). Place en dernier, il donnait deux « et » de suite :
    « …, la trésorerie et le financement et le contrôle de gestion ». Ces
    elements passent donc devant, la ou la conjonction ne se telescope pas.
    """
    items = [i for i in items if i]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    lien = " and " if langue == "en" else " et "
    # Un element porteur de conjonction passe EN DERNIER, et le sien sert de
    # conjonction finale. Le mettre devant en ajoutait une seconde :
    #   « la trésorerie et le financement, l'analyse financière ET le contrôle »
    # alors qu'en le placant a la fin, une seule suffit :
    #   « l'analyse financière, le contrôle de gestion, la trésorerie et le
    #     financement »
    porteurs = [i for i in items if lien in i]
    if porteurs:
        autres = [i for i in items if lien not in i]
        return ", ".join(autres + porteurs[:1])
    return ", ".join(items[:-1]) + lien + items[-1]


def competences_en_prose(skills, langue="fr", n=4):
    """Les competences retenues, ecrites pour tenir dans une phrase.

    Deux filtres contre la redite, tous deux constates sur une sortie reelle :

    1. Pas deux elements qui finissent par le MEME mot. « l'analyse financière,
       la modélisation financière » sonne comme un begaiement, et le second
       n'ajoute presque rien au premier.
    2. UN SEUL element porteur de « et ». « la trésorerie et le financement,
       l'analyse financière et le contrôle de gestion » : deux conjonctions
       pour trois idees, alors que l'enumeration n'en demande qu'une.
    """
    table = SKILL_PROSE_EN if langue == "en" else SKILL_PROSE_FR
    lien = " and " if langue == "en" else " et "
    vus, fins, sortie = set(), set(), []
    for s in skills:
        p = table.get(s)
        if not p or p in vus:
            continue
        fin = p.rsplit(" ", 1)[-1].lower()
        if fin in fins:
            continue
        if lien in p and any(lien in q for q in sortie):
            continue
        vus.add(p)
        fins.add(fin)
        sortie.append(p)
        if len(sortie) >= n:
            break
    return _enumere(sortie, langue)


# Competences qui ne sont pas des termes TECHNIQUES : les citer dans cette
# enumeration donnait « forecast, audit, excel, anglais » — et l'anglais est
# deja annonce deux lignes plus bas, avec son score au TOEIC.
_NON_TECHNIQUE = {lab for lab, v in _COMP.items() if v.get("technique") is False}

# Faux amis : mots francais du lexique qui existent aussi en anglais avec un
# tout autre sens. « assurance » (le secteur) s'est retrouve cite comme terme
# technique dans une lettre anglaise a TotalEnergies, ou l'annonce disait
# seulement « provide assurance ». Un mot francais trouve dans un texte anglais
# ne prouve rien.
_FAUX_AMIS_EN = {"assurance", "avocat", "location", "actuel", "formation",
                 "experience", "notice", "large", "librairie", "cave"}

# COMMENT CHAQUE TERME S'ECRIT DANS LA LANGUE DE LA LETTRE.
#
# Les mots-cles du lexique sont ceux qu'on CHERCHE dans l'annonce : ils sont
# donc dans les deux langues, en vrac. Imprimes tels quels, ils donnaient
# « je pratique ce que décrit votre annonce : forecast, Excel » — un mot
# anglais au milieu d'une lettre francaise, ce qui ne passe pas.
#
# Chaque entree dit la forme FR et la forme EN. `None` = ne pas ecrire dans
# cette langue-la. Un terme absent de la table n'est pas imprime : mieux vaut
# une enumeration plus courte qu'un anglicisme de trop.
_TERMES = {k: tuple(v) for k, v in (_P.get("termes", {}) or {}).items()}


def mots_techniques(offer_text, n=6, langue="fr"):
    """Les termes techniques que l'ANNONCE emploie et que le CV couvre.

    Les libelles de competence sont notre vocabulaire ; ceci est le LEUR. Un
    ATS cherche les mots de l'annonce, et un lecteur humain reconnait les
    siens : citer « clôture mensuelle » parce qu'ils l'ont ecrit vaut mieux que
    de nommer « le contrôle de gestion » et d'esperer qu'il fasse le lien.

    On ne retient qu'un terme deja couvert par une competence du CV : reprendre
    un mot de l'annonce qu'on ne sait pas justifier serait du remplissage.

    Le terme est ECRIT dans la langue de la lettre, via _TERMES. Les mots-cles
    du lexique servent a CHERCHER, ils sont donc dans les deux langues en
    vrac : imprimes bruts, ils donnaient « je pratique ce que décrit votre
    annonce : forecast, Excel » au milieu d'une lettre francaise. Un terme
    absent de _TERMES n'est pas imprime — une enumeration plus courte vaut
    mieux qu'un anglicisme de trop.
    """
    t = (offer_text or "").lower()
    i = 0 if langue != "en" else 1
    trouves = []
    for lab, mots in SKILL_LEX.items():
        if lab in SKILL_INTERNES or lab in _NON_TECHNIQUE:
            continue
        for m in mots:
            m = m.lower()
            if langue == "en" and m in _FAUX_AMIS_EN:
                continue
            # Bornes de mot : sans elles « rse » se trouve dans « transverse »
            # et « esg » dans n'importe quel identifiant. C'est la faute qui
            # revient le plus souvent dans ce projet.
            if len(m) >= 3 and re.search(r"\b" + re.escape(m) + r"\b", t):
                forme = _TERMES.get(m, (None, None))[i]
                if forme and forme not in trouves:
                    trouves.append(forme)
                break
    return trouves[:n]


def match_skills(offer_text, max_n=8):
    t = (offer_text or "").lower()
    hits = []
    for label in SKILL_LEX:
        if label in SKILL_INTERNES:
            continue
        if has_skill(label, t):
            hits.append(label)
    # socle neutre (pas de biais ESG) si offre pauvre en texte
    if len(hits) < 3:
        for base in (_P.get("competences_de_base", []) or []):
            if base not in hits:
                hits.append(base)
    return hits[:max_n]

# ---- CV : injecte titre + ligne competences ciblees ----
def tailor_cv(offer, nom=None, langue="fr", allege=0, auto=True):
    """`nom` : stem impose. Sans lui, plusieurs offres au titre voisin
    produisent le MEME fichier et s'ecrasent — voir generate_docs._noms_uniques.

    `langue` : 'en' choisit le modele anglais quand il existe. 1525 offres de la
    file sont redigees en anglais ; leur envoyer un CV francais, c'est se
    disqualifier avant lecture. Le repli sur le francais est SILENCIEUX quand le
    modele anglais manque (toutes les variantes ne sont pas encore traduites) —
    un CV francais vaut mieux que pas de CV."""
    key = cv_variant_key(offer["domaine"])
    src = CV_ATS / (CV_VARIANT.get(key) or "")
    if not CV_VARIANT.get(key):
        # Variante sans fichier : le premier CV du profil qui existe.
        src = next((CV_ATS / f for f in CV_VARIANT.values() if f and (CV_ATS / f).exists()), src)
    if langue == "en" and CV_VARIANT_EN.get(key) and (CV_ATS / CV_VARIANT_EN[key]).exists():
        src = CV_ATS / CV_VARIANT_EN[key]
    if not src.is_file():
        print(f"  ! CV variante absente: {src.name or key} (profil.json, domaines[].cv)"); return None
    from rename_docs import new_name
    if src.suffix.lower() == ".pdf":
        # CV fourni en PDF seulement : il part tel quel, sans adaptation.
        # Un modele .docx permet d'y inserer l'intitule du poste.
        out = CV_OUT / ((nom or new_name("CV", offer.get("role") or "", offer["company"])) + ".pdf")
        shutil.copyfile(src, out)
        return out
    doc = Document(str(src))
    # Le marqueur est dans le PROFIL : « je suis a la recherche d'un poste de
    # [nom du poste] ». Y coller l'intitule BRUT donnait « d'ACTUAIRE (F/H) » ou
    # « d'Adjoint Risque Clients (F/H) - CDD » : la mention de genre et le type de
    # contrat n'ont rien a faire dans une phrase ecrite a la premiere personne.
    # Sur un CV le titre entre DANS une phrase : il doit se lire, pas seulement
    # etre exact. « …a la recherche d'un poste d'Analyste RSE-ESG - Analyste
    # Credit et ESG. » ou « …a position as Consultant, Climate Change and
    # Sustainability Services Financial Services. » trainent le titre d'annonce
    # entier, tiret de separation compris. On garde le premier segment quand il
    # suffit a nommer le metier ; l'objet de la LETTRE, lui, conserve le titre
    # complet, parce qu'il doit correspondre exactement a l'annonce.
    role = titre_poste(offer.get("role") or "") or "ce poste"
    # UN TITRE TROP LONG FAIT DEBORDER LE CV SUR DEUX PAGES. Il s'insere DANS
    # une phrase du profil, qui tient sur trois lignes et n'a qu'un point de
    # marge. Mesure du 2026-09-22 sur les intitules ESG de la file : deux des
    # trois plus longs passaient le CV a deux pages, en silence.
    #
    # On ne coupe donc pas seulement sur « - » : les annonces empilent aussi
    # des virgules, des parentheses et des barres obliques. « Investment
    # Banking, Natural Resources & Energy Transition (Power/Energy) » devient
    # « Investment Banking », qui se lit et tient.
    #
    # Le seuil de 12 caracteres protege les tetes trop courtes pour nommer un
    # metier : « Stage » ou « VIE » seuls ne disent rien.
    for sep in (" - ", " – ", ", ", " (", " / ", " | "):
        tete = role.split(sep)[0].strip()
        if 12 <= len(tete) < len(role):
            role = tete
    # Dernier filet, si aucun separateur n'apparait : on coupe sur un mot.
    if len(role) > 46:
        coupe = role[:46]
        i = coupe.rfind(" ")
        role = (coupe[:i] if i > 28 else coupe).rstrip(" ,;:.-&")

    # 1) remplace le titre [nom du poste], avec l'elision de _de() (h et y exclus)
    #    Le modele anglais porte « [job title] » et ne demande AUCUNE elision :
    #    « as [job title] » se construit sans article contracte.
    for p in doc.paragraphs:
        if "[job title]" in p.text:
            txt = p.text.replace("[job title]", role)
        elif "[nom du poste]" in p.text:
            if "de [nom du poste]" in p.text:
                # Apostrophe TYPOGRAPHIQUE : le gabarit ecrit « d’un poste ».
                txt = p.text.replace("de [nom du poste]", _de(role, "’"))
            else:
                txt = p.text.replace("[nom du poste]", role)
        else:
            continue
        for r in p.runs:
            r.text = ""
        (p.runs[0] if p.runs else p.add_run("")).text = txt

    # 1 bis) Retouches ecrites a la main pour CETTE offre (CV/Sur_mesure).
    #       Sans elles, les faits automatiques de CV/Faits.json (cv_auto) :
    #       le sur-mesure, relu par l'utilisateur, l'emporte toujours.
    retouches = cv_sur_mesure(offer)
    if retouches:
        manquees = appliquer_cv_sur_mesure(doc, retouches)
        for m in manquees:
            print(f"  ! CV sur mesure : texte introuvable dans le modele : « {m[:60]} »")
    elif auto:
        import cv_auto
        r = cv_auto.retouches(offer.get("offer_text") or offer.get("role") or "",
                              langue if langue == "en" else "fr", allege)
        # Ancres manquees : NORMAL ici. Chaque variante de CV n'a pas les memes
        # lignes, et un fait vise parfois une seule d'entre elles.
        appliquer_cv_sur_mesure(doc, r)

    # 2) SUPPRIMÉ (2026-07-12) : la ligne « Compétences ciblées pour ce poste : … »
    #    trahissait un CV auto-généré auprès des recruteurs. Les skills servent toujours
    #    au scoring (fit/ATS) et à la LETTRE, mais ne sont plus injectés dans le CV.

    from rename_docs import new_name   # Prenom_Nom_CV_<Poste court>_<Entreprise>
    out = CV_OUT / ((nom or new_name("CV", role, offer["company"])) + ".docx")
    doc.save(str(out))
    return out

def _pages_pdf(pdf):
    try:
        import fitz
        with fitz.open(str(pdf)) as d:
            return d.page_count
    except Exception:
        return 1          # illisible : on ne boucle pas pour rien


def cv_une_page(offer, nom=None, langue="fr"):
    """tailor_cv + to_pdf, en garantissant UNE page. Rend (docx, pdf).

    Les faits automatiques ajoutent des lignes ; si le PDF deborde, on retire
    les `allegements` de CV/Faits.json un par un. En dernier recours, le CV
    repart du modele sans fait automatique : un CV generique d'une page vaut
    mieux qu'un CV adapte de deux. Un CV/Sur_mesure n'est jamais allege : il a
    ete relu, sa page aussi."""
    import cv_auto
    lg = langue if langue == "en" else "fr"
    essais = [(k, True) for k in range(cv_auto.nb_allegements(lg) + 1)] + [(0, False)]
    if cv_sur_mesure(offer):
        essais = [(0, True)]
    cv = pdf = None
    for allege, auto in essais:
        cv = tailor_cv(offer, nom=nom, langue=langue, allege=allege, auto=auto)
        if not cv:
            return None, None
        pdf = to_pdf(cv)
        if not pdf or _pages_pdf(pdf) <= 1:
            break
    return cv, pdf


def _enable_hyphenation(doc):
    """Active la césure automatique Word → un texte justifié sans « trous » (rivières)."""
    try:
        from docx.oxml.ns import qn
        s = doc.settings.element
        if s.find(qn("w:autoHyphenation")) is None:
            el = s.makeelement(qn("w:autoHyphenation"), {qn("w:val"): "true"})
            s.append(el)
    except Exception:
        pass


# ---- Lettre : docx tailoree aux missions reelles ----
def tailor_letter(offer, nom=None, langue="fr"):
    """`nom` : stem impose, meme raison que tailor_cv.

    `langue` : 'en' ecrit la lettre en anglais. Les FAITS sont les memes — meme
    memoire, memes 3 000 fonds, meme stage chez Acme Finance — seule la langue
    change. Les formules de politesse, elles, ne se traduisent pas mot a mot :
    « Je vous prie d'agreer… » n'a pas d'equivalent litteral et devient
    « Yours faithfully », qui est la forme attendue quand le destinataire est
    inconnu (« Dear Sir or Madam »)."""
    company = offer["company"]; role = (offer["role"] or "ce poste").strip()
    skills = match_skills(offer["offer_text"])
    missions = (offer["missions"] or "").strip()
    profil = (offer["profil"] or "").strip()
    # A QUI on ecrit. Rend la generique quand le champ `rh` ne porte pas une
    # personne — c'est le cas de 4501 offres sur 4917, donc le cas courant.
    _appel, _reprise_civ, _nomme = salutation(offer, langue)
    # Corps ecrit a la main pour CETTE offre, s'il existe. Voir corps_sur_mesure().
    _corps = corps_sur_mesure(offer)

    doc = Document()
    style = doc.styles["Normal"]; style.font.name = "Calibri"; style.font.size = Pt(11)
    _enable_hyphenation(doc)   # césure auto : justifié SANS trous (rivières)

    def para(txt, align=WD_ALIGN_PARAGRAPH.JUSTIFY, space=6, bold=False):
        p = doc.add_paragraph(); p.alignment = align
        r = p.add_run(txt); r.bold = bold
        p.paragraph_format.space_after = Pt(space)
        return p

    # en-tete expediteur
    for line in [PROFILE["nom"], PROFILE["email"], PROFILE["tel"]]:   # pas d'adresse/ville (vie privee)
        para(line, WD_ALIGN_PARAGRAPH.LEFT, 0)
    para("")
    # date du jour a droite ; PAS de bloc destinataire : nom du recruteur inconnu
    # -> on ne met pas le nom de l'entreprise (demande l'utilisateur 2026-07-12)
    from datetime import date as _d
    _MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
             "août", "septembre", "octobre", "novembre", "décembre"]
    _MONTHS = ["January", "February", "March", "April", "May", "June", "July",
               "August", "September", "October", "November", "December"]
    _t = _d.today()
    para(f"{_MONTHS[_t.month - 1]} {_t.day}, {_t.year}" if langue == "en"
         else f"Le {_t.day} {_MOIS[_t.month - 1]} {_t.year}",
         WD_ALIGN_PARAGRAPH.RIGHT, 12)
    if langue == "en":
        _titre_en = titre_poste(_sans_societe(role, company))
        para(f"Subject: Application for the position of {_titre_en}" if _titre_en
             else "Subject: Speculative application", space=12, bold=True)
        para(_appel)
        # LE CORPS ECRIT A LA MAIN court-circuite le gabarit. Ce qui l'entoure
        # reste genere : c'est lui qui sait nommer deux destinataires et
        # accorder la cloture.
        if _corps:
            for _bloc in _corps:
                para(_bloc)
            para("Yours sincerely," if _nomme else "Yours faithfully,", space=12)
            para(PROFILE["nom"], WD_ALIGN_PARAGRAPH.LEFT, 0)
            from rename_docs import new_name
            out_sm = LT_OUT / ((nom or new_name("Lettre", role, company)) + ".docx")
            doc.save(str(out_sm))
            return out_sm
        # « caught my full attention » est le calque de « a retenu toute mon
        # attention » : personne n'écrit cela en anglais. « I read your
        # advertisement with great interest » est la formule usuelle.
        # Et comme en français, on ne prête aucun engagement à une entreprise
        # qu'on ne connaît pas : sans valeur identifiée, on parle du poste.
        _val_en = company_value_en(company)
        _connue_en = bool(_val_en)
        para(
            "I read your advertisement with great interest: "
            + (_val_en if _connue_en else "this role")
            + " matches the career path I have been building since my studies."
        )
        # Le parcours suit le DOMAINE de l'offre : ecrire « je me suis
        # specialise en finance durable » a une compagnie petroliere qui cherche
        # un analyste economique, c'est parler a cote.
        _cle = cv_variant_key(offer.get("domaine"))
        socle_en = socle(_cle, "en")
        # Meme suppression qu'en francais : on collait 220 caracteres de leur
        # annonce entre parentheses, coupes en plein milieu d'une phrase.
        # Paragraphe A PART, pas une rallonge du socle : celui-ci fait deja
        # quatre phrases, et une cinquieme sur des oliviers portugais s'y
        # perdrait. Vide pour toute offre non agricole.
        _agri_en = contexte_agricole(offer, "en")
        # LE CONCRET CHASSE LE GENERIQUE. La phrase durable dit « that work
        # covered sustainable investment: SFDR classification »; le paragraphe
        # agricole dit la meme chose en nommant les fonds et le terrain. Les
        # deux ensemble donnaient « SFDR » deux fois en quatre lignes, et
        # « fund » trois fois — releve par verifie_redites.py sur la lettre
        # Mirova. Quand l'agricole part, le generique se tait.
        _dur_en = "" if _agri_en else contexte_durable(offer, "en")
        if _dur_en:
            socle_en += " " + _dur_en
        if socle_en.strip():
            para(socle_en)
        if _agri_en:
            para(_agri_en)
        if skills:
            # Quatre competences, pas six : au-dela, l'enumeration cesse d'etre
            # une phrase et devient une liste de mots-cles.
            prose_en = competences_en_prose(skills, "en", 4)
            if prose_en:
                techs_en = [m for m in mots_techniques(
                                f"{offer.get('missions','')} {offer.get('profil','')} "
                                f"{offer.get('offer_text','')}", 12, "en")
                            if m.lower() not in prose_en.lower()][:4]
                ph = f"Along the way I became familiar with {prose_en}."
                if len(techs_en) >= 2:
                    ph += (" I also work with what your advertisement describes: "
                           + ", ".join(techs_en) + ".")
                para(ph + " These are foundations I would be glad to deepen "
                          "within your teams.")
        if (_citable(profil, "en")
                and profil.lower() not in ("non précisé", "à compléter", "nan")):
            # Le point-virgule anglais n'etait pas mieux que le francais.
            _pp_en = _P.get("lettre.phrase_profil_en", "") or ""
            if _pp_en:
                para(_pp_en)
        # « I would be VERY glad to discuss IN PERSON what I COULD bring […] at
        # your convenience » : trois attenuations dans une phrase. On demande
        # un entretien, on ne s'excuse pas de le demander.
        para("I would welcome the opportunity to discuss this role with you and am "
             "available for an interview at your convenience.")
        # « Yours faithfully » est la formule attendue quand le destinataire est
        # inconnu ; « Yours sincerely » suppose qu'on l'a nomme. La lettre sait
        # desormais lequel des deux cas s'applique.
        para("Yours sincerely," if _nomme else "Yours faithfully,", space=12)
        para(PROFILE["nom"], WD_ALIGN_PARAGRAPH.LEFT, 0)
        from rename_docs import new_name
        out_en = LT_OUT / ((nom or new_name("Lettre", role, company)) + ".docx")
        doc.save(str(out_en))
        return out_en
    # le titre BRUT de l'annonce ne va pas dans la lettre : voir titre_poste()
    # En francais un intitule de poste est un nom commun. Les annonces le
    # capitalisent a l'anglaise — « Contrôleur de Gestion Financier » — et on
    # le recopiait tel quel dans l'objet.
    _titre = minuscule_titre(titre_poste(_sans_societe(role, company)))
    para(f"Objet : Candidature au poste {_de(_titre)}" if _titre else "Objet : Candidature spontanée",
         space=12, bold=True)
    para(_appel)

    # LE CORPS ECRIT A LA MAIN, meme regle qu'en anglais.
    if _corps:
        for _bloc in _corps:
            para(_bloc)
        para(f"Je vous prie d'agréer, {_reprise_civ}, l'expression de mes "
             "salutations distinguées.", space=12)
        para(PROFILE["nom"], WD_ALIGN_PARAGRAPH.LEFT, 0)
        from rename_docs import new_name
        out_sm = LT_OUT / ((nom or new_name("Lettre", role, company)) + ".docx")
        doc.save(str(out_sm))
        return out_sm

    # INTRO. Trois corrections de formulation, toutes tirées de la relecture
    # d'une lettre réelle (Crédit Mutuel AM) :
    #
    # 1. Le titre complet était répété MOT POUR MOT juste après l'objet, deux
    #    lignes plus haut. « Votre annonce » suffit : le lecteur vient de le lire.
    # 2. « a retenu TOUTE mon attention » : le superlatif affaiblit. On garde
    #    « a retenu mon attention ».
    # 3. company_value() rendait sa phrase générique — « votre engagement en
    #    faveur de la finance durable » — pour 5831 offres sur 5907, soit 98 %.
    #    Écrite à Van Cleef & Arpels (joaillier) ou à EY, elle sonne faux et
    #    n'affirme rien. Quand l'entreprise est inconnue, on ne lui prête AUCUN
    #    engagement : on parle du poste, qu'on connaît.
    _valeur = company_value(company)
    _connue = bool(_valeur)
    _sujet = _valeur if _connue else "ce poste"
    para(
        f"Votre annonce a retenu mon attention : {_sujet} rejoint le projet "
        "professionnel que je construis depuis mes études."
    )

    # corps 1 : preuve par le parcours (faits, pas de superlatifs)
    # Meme regle qu'en anglais : le parcours suit le domaine de l'offre.
    socle_txt = socle(cv_variant_key(offer.get("domaine")), "fr")
    # LES MISSIONS NE SONT PLUS CITEES. On collait 220 caracteres de l'annonce
    # entre parentheses, coupes en plein milieu d'une phrase :
    #
    #   « Les missions que vous décrivez (Dans le cadre de son développement en
    #     Inde, notre filiale de Bangalore recherche un(e) VIE – Contrôleur de
    #     Gestion Financier. Rattaché(e) à la Direction Financière…) font écho
    #     à ces expériences. »
    #
    # Leur propre texte leur est renvoye tel quel, avec les majuscules de
    # l'annonce, les formes inclusives « un(e) », le tiret demi-cadratin et
    # trois points de suspension a la place de la fin. Ce n'est pas une
    # citation, c'est un copier-coller tronque.
    #
    # A la place : les termes techniques que l'annonce emploie ET que le CV
    # couvre. Ce sont LEURS mots, ce qui sert au filtrage ATS, et chacun est
    # justifie par une competence reelle.
    #
    # Et si l'employeur travaille dans la durabilite sans que le POSTE soit un
    # poste ESG — un analyste corporate finance chez un producteur d'energie
    # renouvelable —, la specialisation de master se dit ici. Sinon la lettre
    # a un energeticien vert n'en soufflait pas un mot.
    # Le terrain agricole, en paragraphe autonome. Meme raison qu'en anglais :
    # le socle est deja plein, et ces deux faits — le fonds Atlantic Agri,
    # Terres Solidaires — meritent d'etre lus, pas glisses en fin de phrase.
    _agri = contexte_agricole(offer, "fr")
    # LE CONCRET CHASSE LE GENERIQUE, voir la branche anglaise.
    _dur = "" if _agri else contexte_durable(offer, "fr")
    if _dur:
        socle_txt += " " + _dur
    if socle_txt.strip():          # parcours vide dans le profil : pas de paragraphe creux
        para(socle_txt)
    if _agri:
        para(_agri)

    # corps 2 : compétences amenées avec humilité (junior assumé, envie d'apprendre)
    # Les libelles bruts etaient recopies tels qu'ils figurent sur le CV, ou ce
    # sont des ETIQUETTES de rubrique : « Analyse financière, Modélisation
    # financière, Trésorerie / financement, Contrôle de gestion ». Quatre
    # majuscules parasites et une barre oblique au milieu d'une phrase.
    # SKILL_PROSE_FR donne la forme qui se dit. QUATRE competences, pas six :
    # au-dela, l'enumeration cesse d'etre une phrase.
    if skills:
        prose = competences_en_prose(skills, "fr", 4)
        if prose:
            # Les termes de l'annonce que le CV couvre, en APPOSITION apres deux
            # points. Sans article, donc sans probleme d'accord : « forecast,
            # reporting, Excel » marche pour n'importe quel mot, la ou « avec le
            # forecast et le reporting » demanderait de deviner le genre de
            # chacun. C'est aussi la forme que lit un ATS, qui cherche les mots
            # de l'annonce et non nos libelles maison.
            techs = [m for m in mots_techniques(
                        f"{offer.get('missions','')} {offer.get('profil','')} "
                        f"{offer.get('offer_text','')}", 12, "fr")
                     if m.lower() not in prose.lower()][:4]
            phrase = f"Au fil de ce parcours, je me suis {_P.accord('familiarisé', 'familiarisée')} avec {prose}."
            if len(techs) >= 2:
                phrase += " Je pratique aussi ce que décrit votre annonce : " + ", ".join(techs) + "."
            para(phrase + f" Ce sont des acquis que je serais {_P.accord('heureux', 'heureuse')} "
                          "d'approfondir au sein de vos équipes.")
    # Le profil non plus n'est plus cite : meme copier-coller tronque, suivi
    # d'un point-virgule que personne n'ecrit dans une lettre.
    if (_citable(profil, "fr")
            and profil.lower() not in ("non précisé", "à compléter", "nan")):
        _pp = _P.get("lettre.phrase_profil_fr", "") or ""
        if _pp:
            para(_pp)

    # CLOTURE. L'ancienne version empilait trois conditionnels et deux formules
    # toutes faites : « Je SERAIS TRÈS heureux de vous exposer DE VIVE VOIX ce
    # que je POURRAIS apporter […] à votre convenance ». Une phrase qui
    # s'excuse de demander un entretien ne donne pas envie de l'accorder.
    para(
        f"Je serais {_P.accord('heureux', 'heureuse')} d'échanger avec vous sur ce poste et me tiens à "
        "votre disposition pour un entretien."
    )
    # LA REPRISE DOIT REPONDRE A L'APPEL. Ecrire « Monsieur Mac Arthur, » en
    # tete et « agréer, Madame, Monsieur » en pied est la faute classique des
    # lettres a trous : la cloture trahit le gabarit que l'ouverture cachait.
    para(f"Je vous prie d'agréer, {_reprise_civ}, l'expression de mes "
         "salutations distinguées.", space=12)
    para(PROFILE["nom"], WD_ALIGN_PARAGRAPH.LEFT, 0)

    from rename_docs import new_name   # Prenom_Nom_Lettre_<Poste court>_<Entreprise>
    out = LT_OUT / ((nom or new_name("Lettre", role, company)) + ".docx")
    doc.save(str(out))
    return out

# ---- mode LLM : Claude API (si clé) OU Ollama local (gratuit) ----
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1:8b")

def _llm_prompt(offer):
    return (
        f"Tu es {PROFILE['nom']}. {_P.get('lettre.presentation_llm', '') or ''} "
        f"Rédige le CORPS (3 paragraphes, français, sobre, factuel, sans clichés ni superlatifs) d'une lettre de motivation "
        f"pour le poste « {offer['role']} » chez {offer['company']}.\n\n"
        f"Missions de l'offre : {offer['missions'][:600]}\n"
        f"Profil recherché : {offer['profil'][:400]}\n\n"
        "Mets en avant les recoupements réels entre son parcours et l'offre. Pas d'en-tête ni de formule "
        "de politesse (déjà gérés ailleurs). Uniquement les 3 paragraphes du corps."
    )

def _ollama_generate(prompt):
    """Appelle Ollama local (gratuit). Retourne le texte ou None si indispo."""
    import json as _json
    import urllib.request
    body = _json.dumps({"model": OLLAMA_MODEL, "prompt": prompt, "stream": False,
                        "options": {"temperature": 0.4}}).encode()
    try:
        req = urllib.request.Request(f"{OLLAMA_URL}/api/generate", data=body,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=120) as r:
            return _json.loads(r.read()).get("response", "").strip()
    except Exception as e:
        print(f"  ! Ollama indispo ({type(e).__name__}) — lance `ollama serve` + `ollama pull {OLLAMA_MODEL}`")
        return None

def llm_rewrite(offer, cv_docx, letter_docx):
    prompt = _llm_prompt(offer)
    body = None
    # 1) Claude API si clé
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        try:
            import anthropic
            msg = anthropic.Anthropic(api_key=key).messages.create(
                model="claude-sonnet-5", max_tokens=700,
                messages=[{"role": "user", "content": prompt}])
            body = msg.content[0].text.strip()
            print("  ✎ Claude API")
        except Exception as e:
            print(f"  ! Claude API échec: {type(e).__name__}")
    # 2) sinon Ollama local (gratuit)
    if not body:
        body = _ollama_generate(prompt)
        if body:
            print(f"  ✎ Ollama local ({OLLAMA_MODEL})")
    if not body:
        return False
    # reconstruit la lettre avec le corps LLM
    doc = Document()
    doc.styles["Normal"].font.name = "Calibri"; doc.styles["Normal"].font.size = Pt(11)
    for line in [PROFILE["nom"], PROFILE["email"], PROFILE["tel"], ""]:   # pas d'adresse/ville
        doc.add_paragraph(line)
    # même nettoyage + élision que tailor_letter : ce chemin LLM écrivait le titre brut
    _t = titre_poste(offer.get("role") or "")
    doc.add_paragraph(f"Objet : Candidature au poste {_de(_t)}" if _t
                      else "Objet : Candidature spontanée").runs[0].bold = True
    doc.add_paragraph("Madame, Monsieur,")
    for para in body.split("\n\n"):
        p = doc.add_paragraph(para.strip()); p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    doc.add_paragraph("Je vous prie d'agréer, Madame, Monsieur, mes salutations distinguées.")
    doc.add_paragraph(PROFILE["nom"])
    doc.save(str(letter_docx))
    return True

# ---- PDF via LibreOffice ----
SOFFICE = [r"C:\Program Files\LibreOffice\program\soffice.exe",
           r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"]
def to_pdf(docx_path):
    exe = next((s for s in SOFFICE if Path(s).exists()), None)
    if not exe:
        return None
    try:
        subprocess.run([exe, "--headless", "--convert-to", "pdf", "--outdir",
                        str(docx_path.parent), str(docx_path)],
                       check=True, capture_output=True, timeout=90)
        return docx_path.with_suffix(".pdf")
    except Exception as e:
        print(f"  ! PDF échec: {e}"); return None

# ---- lecture Excel ----
if __name__ == "__main__":
    print("Module de fonctions (tailor_cv/tailor_letter/to_pdf). CLI : generate_docs.py / add_offer.py")
