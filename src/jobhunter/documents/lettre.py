"""Lettre de motivation par offre : salutation, contexte, corps, competences.

Partie de jobhunter.documents (ancien Scripts/tailor_application.py, phase 3.5)."""

import importlib
import re
import sys
from pathlib import Path
from typing import Any

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt

from jobhunter import chemins
from jobhunter import paresseux as _paresseux
from jobhunter import profil as _P
from jobhunter.documents.commun import (
    _de,
    _slug,
    company_value,
    match_skills,
    minuscule_titre,
    titre_poste,
)
from jobhunter.scoring.lexique import cv_variant_key

_ici = sys.modules[__name__]
# Valeurs tirees du profil : calculees a la premiere lecture, pas a l'import
# (jobhunter.paresseux). Dans ce module, on les lit par `_ici.NOM`.
_PARESSEUX: _paresseux.Fabriques = {}


def __getattr__(nom: str) -> Any:
    return _paresseux.lire(_ici, _PARESSEUX, nom)


_PARESSEUX["LT_OUT"] = lambda: importlib.import_module("jobhunter.documents.commun").LT_OUT


_PARESSEUX["PROFILE"] = lambda: importlib.import_module("jobhunter.documents.commun").PROFILE


_PARESSEUX["SKILL_INTERNES"] = lambda: (
    importlib.import_module("jobhunter.documents.commun").SKILL_INTERNES
)


_PARESSEUX["_COMP"] = lambda: importlib.import_module("jobhunter.scoring.lexique")._COMP


_PARESSEUX["_DOMAINES"] = lambda: importlib.import_module("jobhunter.scoring.lexique")._DOMAINES


_PARESSEUX["SKILL_LEX"] = lambda: importlib.import_module("jobhunter.scoring.lexique").SKILL_LEX


def _citable(t: str | None, langue: str) -> bool:
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
        from jobhunter.scoring.langue import langue_offre

        # langue_offre exige 120 caracteres pour se prononcer ; en dessous il
        # repond « fr » par defaut, ce qui ferait taire toute citation courte
        # dans une lettre anglaise. On ne tranche donc que sur un texte assez
        # long pour etre juge.
        if len(t) < 120:
            return True
        return langue_offre("", t) == langue
    except Exception:
        return True


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
_PARESSEUX["SOCLE_FR"] = lambda: ({d["cle"]: d.get("parcours_fr") or "" for d in _ici._DOMAINES})


_PARESSEUX["SOCLE_EN"] = lambda: ({d["cle"]: d.get("parcours_en") or "" for d in _ici._DOMAINES})


def socle(cle: str, langue: str = "fr") -> str:
    """Paragraphe de parcours du domaine `cle`, ou celui du premier domaine
    qui en a un : une lettre sans parcours ne dit rien du candidat."""
    table = _ici.SOCLE_EN if langue == "en" else _ici.SOCLE_FR
    if table.get(cle):
        return str(table[cle])
    return next((v for v in table.values() if v), "")


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
_PARESSEUX["_CONTEXTES"] = lambda: _P.get("lettre.contextes", []) or []


def _contexte_applicable(ctx: dict[str, Any], offer: dict[str, Any]) -> bool:
    if cv_variant_key(offer.get("domaine")) in (ctx.get("sauf_domaines") or []):
        return False
    rx = _P.motif(ctx.get("mots"))
    if rx is None:
        return False
    ign = _P.motif(ctx.get("ignorer"))

    def net(t: str | None) -> str:
        return ign.sub(" ", t or "") if ign else (t or "")

    role = net(str(offer.get("role") or ""))
    if rx.search(role):
        return True
    texte = net(
        " ".join(
            str(offer.get(k) or "") for k in ("company", "role", "offer_text", "missions", "profil")
        )
    )
    if len(rx.findall(texte)) < int(ctx.get("occurrences_min") or 1):
        return False
    if ctx.get("densite_coeur"):
        # Import differe : ats_match importe ce module.
        from jobhunter.scoring.fit import _ESG_DENSITE_LONG, _ESG_DENSITE_MIN, densite_esg

        if len(texte) >= _ESG_DENSITE_LONG and densite_esg(texte) < _ESG_DENSITE_MIN:
            return False
    return True


def contexte(
    offer: dict[str, Any], langue: str = "fr", position: str | None = None
) -> tuple[str, str]:
    """(position, texte) du contexte a ajouter, ou ("", "").
    position : "socle" (ajoute au parcours) ou "paragraphe" (paragraphe a part).

    `position` restreint la recherche a une seule position. Sans elle, le
    PREMIER contexte applicable masquait les autres : une offre a la fois
    agricole (paragraphe) et durable (socle) perdait la phrase durable du
    message, que le code d'origine ajoutait independamment (Ortec, 15/10)."""
    for ctx in _ici._CONTEXTES:
        if position and (ctx.get("position") or "paragraphe") != position:
            continue
        if _contexte_applicable(ctx, offer):
            t = ctx.get("en" if langue == "en" else "fr") or ""
            if t:
                return ctx.get("position") or "paragraphe", t
    return "", ""


def contexte_durable(offer: dict[str, Any], langue: str = "fr") -> str:
    """Compatibilite : le texte d'un contexte place dans le socle, ou ""."""
    return contexte(offer, langue, "socle")[1]


def contexte_agricole(offer: dict[str, Any], langue: str = "fr") -> str:
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


def _reprise(civs: list[str], langue: str) -> str:
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
        return "Sir or Madam"  # l'anglais ferme sur « Yours sincerely »
    if all(fem):
        return "Madame" if len(connus) == 1 else "Mesdames"
    if not any(fem):
        return "Monsieur" if len(connus) == 1 else "Messieurs"
    return "Madame, Monsieur"


def corps_sur_mesure(offer: dict[str, Any]) -> list[str]:
    """Les paragraphes ecrits a la main pour cette offre, ou [] s'il n'y en a
    pas. Le fichier se nomme `<entreprise>__<poste>.txt`, paragraphes separes
    par une ligne vide.

    La recherche est TOLERANTE a la casse et a la ponctuation : le nom de
    fichier vient d'un intitule d'annonce, ou l'on trouve des barres obliques,
    des parentheses et des majuscules aleatoires. Windows ignorant deja la
    casse, chercher a l'identique ne donnerait qu'un faux negatif silencieux.
    """
    from jobhunter.chemins import LT_SUR_MESURE

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


def _sans_societe(role: str, company: str) -> str:
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


def salutation(offer: dict[str, Any], langue: str = "fr") -> tuple[str, str, bool]:
    """Rend (formule d'appel, reprise de cloture, nominative ?).

    LE TEXTE DE L'APPEL VIENT DE `message_offre.appel`, qui sait deja le faire
    et dont 26 cas de test le verifient — decoupe des destinataires multiples
    comprise. Ce qu'on ajoute ici est propre a la LETTRE : la reprise de
    cloture, que le message n'a pas.
    """
    from jobhunter.documents.message import (
        _RX_CIVILITE,
        _RX_SEPARE,
        GENERIQUES,
        appel,
        nom_dans_offre,
    )

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
            continue  # morceau ecarte par `appel`
        g = _RX_CIVILITE.match(x)
        civs.append(g.group(1).lower() if g else "")
    return texte, _reprise(civs, langue), True


def company_value_en(company: str | None) -> str:
    """Accroche anglaise connue, ou "" (meme regle que company_value)."""
    c = (company or "").lower()
    for k, v in _ici.COMPANY_VALUE_EN.items():
        if k in c:
            return str(v)
    return ""


_PARESSEUX["COMPANY_VALUE_EN"] = lambda: dict(_P.get("lettre.valeurs_entreprises_en", {}) or {})


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
_PARESSEUX["SKILL_PROSE_FR"] = lambda: (
    {lab: v["prose_fr"] for lab, v in _ici._COMP.items() if v.get("prose_fr")}
)


_PARESSEUX["SKILL_PROSE_EN"] = lambda: (
    {lab: v["prose_en"] for lab, v in _ici._COMP.items() if v.get("prose_en")}
)


def _enumere(items: list[str], langue: str = "fr") -> str:
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


def competences_en_prose(skills: list[str], langue: str = "fr", n: int = 4) -> str:
    """Les competences retenues, ecrites pour tenir dans une phrase.

    Deux filtres contre la redite, tous deux constates sur une sortie reelle :

    1. Pas deux elements qui finissent par le MEME mot. « l'analyse financière,
       la modélisation financière » sonne comme un begaiement, et le second
       n'ajoute presque rien au premier.
    2. UN SEUL element porteur de « et ». « la trésorerie et le financement,
       l'analyse financière et le contrôle de gestion » : deux conjonctions
       pour trois idees, alors que l'enumeration n'en demande qu'une.
    """
    table = _ici.SKILL_PROSE_EN if langue == "en" else _ici.SKILL_PROSE_FR
    lien = " and " if langue == "en" else " et "
    vus: set[str] = set()
    fins: set[str] = set()
    sortie: list[str] = []
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
_PARESSEUX["_NON_TECHNIQUE"] = lambda: (
    {lab for lab, v in _ici._COMP.items() if v.get("technique") is False}
)


# Faux amis : mots francais du lexique qui existent aussi en anglais avec un
# tout autre sens. « assurance » (le secteur) s'est retrouve cite comme terme
# technique dans une lettre anglaise a TotalEnergies, ou l'annonce disait
# seulement « provide assurance ». Un mot francais trouve dans un texte anglais
# ne prouve rien.
_FAUX_AMIS_EN = {
    "assurance",
    "avocat",
    "location",
    "actuel",
    "formation",
    "experience",
    "notice",
    "large",
    "librairie",
    "cave",
}


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
_PARESSEUX["_TERMES"] = lambda: ({k: tuple(v) for k, v in (_P.get("termes", {}) or {}).items()})


def mots_techniques(offer_text: str | None, n: int = 6, langue: str = "fr") -> list[str]:
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
    for lab, mots in _ici.SKILL_LEX.items():
        if lab in _ici.SKILL_INTERNES or lab in _ici._NON_TECHNIQUE:
            continue
        for m in mots:
            m = m.lower()
            if langue == "en" and m in _FAUX_AMIS_EN:
                continue
            # Bornes de mot : sans elles « rse » se trouve dans « transverse »
            # et « esg » dans n'importe quel identifiant. C'est la faute qui
            # revient le plus souvent dans ce projet.
            if len(m) >= 3 and re.search(r"\b" + re.escape(m) + r"\b", t):
                forme = _ici._TERMES.get(m, (None, None))[i]
                if forme and forme not in trouves:
                    trouves.append(forme)
                break
    return trouves[:n]


def _enable_hyphenation(doc: Any) -> None:
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
def tailor_letter(offer: dict[str, Any], nom: str | None = None, langue: str = "fr") -> Path:
    """`nom` : stem impose, meme raison que tailor_cv.

    `langue` : 'en' ecrit la lettre en anglais. Les FAITS sont les memes — meme
    memoire, memes 3 000 fonds, meme stage chez Acme Finance — seule la langue
    change. Les formules de politesse, elles, ne se traduisent pas mot a mot :
    « Je vous prie d'agreer… » n'a pas d'equivalent litteral et devient
    « Yours faithfully », qui est la forme attendue quand le destinataire est
    inconnu (« Dear Sir or Madam »)."""
    chemins.preparer()  # dossiers de sortie, au moment d'ecrire
    company = offer["company"]
    role = (offer["role"] or "ce poste").strip()
    skills = match_skills(offer["offer_text"])
    missions = (offer["missions"] or "").strip()
    profil = (offer["profil"] or "").strip()
    # A QUI on ecrit. Rend la generique quand le champ `rh` ne porte pas une
    # personne — c'est le cas de 4501 offres sur 4917, donc le cas courant.
    _appel, _reprise_civ, _nomme = salutation(offer, langue)
    # Corps ecrit a la main pour CETTE offre, s'il existe. Voir corps_sur_mesure().
    _corps = corps_sur_mesure(offer)

    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(11)
    _enable_hyphenation(doc)  # césure auto : justifié SANS trous (rivières)

    def para(
        txt: str, align: Any = WD_ALIGN_PARAGRAPH.JUSTIFY, space: int = 6, bold: bool = False
    ) -> Any:
        p = doc.add_paragraph()
        p.alignment = align
        r = p.add_run(txt)
        r.bold = bold
        p.paragraph_format.space_after = Pt(space)
        return p

    # en-tete expediteur
    for line in [
        _ici.PROFILE["nom"],
        _ici.PROFILE["email"],
        _ici.PROFILE["tel"],
    ]:  # pas d'adresse/ville (vie privee)
        para(line, WD_ALIGN_PARAGRAPH.LEFT, 0)
    para("")
    # date du jour a droite ; PAS de bloc destinataire : nom du recruteur inconnu
    # -> on ne met pas le nom de l'entreprise (demande l'utilisateur 2026-07-12)
    from datetime import date as _d

    _MOIS = [
        "janvier",
        "février",
        "mars",
        "avril",
        "mai",
        "juin",
        "juillet",
        "août",
        "septembre",
        "octobre",
        "novembre",
        "décembre",
    ]
    _MONTHS = [
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ]
    _t = _d.today()
    para(
        f"{_MONTHS[_t.month - 1]} {_t.day}, {_t.year}"
        if langue == "en"
        else f"Le {_t.day} {_MOIS[_t.month - 1]} {_t.year}",
        WD_ALIGN_PARAGRAPH.RIGHT,
        12,
    )
    if langue == "en":
        _titre_en = titre_poste(_sans_societe(role, company))
        para(
            f"Subject: Application for the position of {_titre_en}"
            if _titre_en
            else "Subject: Speculative application",
            space=12,
            bold=True,
        )
        para(_appel)
        # LE CORPS ECRIT A LA MAIN court-circuite le gabarit. Ce qui l'entoure
        # reste genere : c'est lui qui sait nommer deux destinataires et
        # accorder la cloture.
        if _corps:
            for _bloc in _corps:
                para(_bloc)
            para("Yours sincerely," if _nomme else "Yours faithfully,", space=12)
            para(_ici.PROFILE["nom"], WD_ALIGN_PARAGRAPH.LEFT, 0)
            from jobhunter.programmes.rename_docs import new_name

            out_sm: Path = _ici.LT_OUT / ((nom or new_name("Lettre", role, company)) + ".docx")
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
                techs_en = [
                    m
                    for m in mots_techniques(
                        f"{offer.get('missions', '')} {offer.get('profil', '')} "
                        f"{offer.get('offer_text', '')}",
                        12,
                        "en",
                    )
                    if m.lower() not in prose_en.lower()
                ][:4]
                ph = f"Along the way I became familiar with {prose_en}."
                if len(techs_en) >= 2:
                    ph += (
                        " I also work with what your advertisement describes: "
                        + ", ".join(techs_en)
                        + "."
                    )
                para(ph + " These are foundations I would be glad to deepen within your teams.")
        if _citable(profil, "en") and profil.lower() not in ("non précisé", "à compléter", "nan"):
            # Le point-virgule anglais n'etait pas mieux que le francais.
            _pp_en = _P.get("lettre.phrase_profil_en", "") or ""
            if _pp_en:
                para(_pp_en)
        # « I would be VERY glad to discuss IN PERSON what I COULD bring […] at
        # your convenience » : trois attenuations dans une phrase. On demande
        # un entretien, on ne s'excuse pas de le demander.
        para(
            "I would welcome the opportunity to discuss this role with you and am "
            "available for an interview at your convenience."
        )
        # « Yours faithfully » est la formule attendue quand le destinataire est
        # inconnu ; « Yours sincerely » suppose qu'on l'a nomme. La lettre sait
        # desormais lequel des deux cas s'applique.
        para("Yours sincerely," if _nomme else "Yours faithfully,", space=12)
        para(_ici.PROFILE["nom"], WD_ALIGN_PARAGRAPH.LEFT, 0)
        from jobhunter.programmes.rename_docs import new_name

        out_en: Path = _ici.LT_OUT / ((nom or new_name("Lettre", role, company)) + ".docx")
        doc.save(str(out_en))
        return out_en
    # le titre BRUT de l'annonce ne va pas dans la lettre : voir titre_poste()
    # En francais un intitule de poste est un nom commun. Les annonces le
    # capitalisent a l'anglaise — « Contrôleur de Gestion Financier » — et on
    # le recopiait tel quel dans l'objet.
    _titre = minuscule_titre(titre_poste(_sans_societe(role, company)))
    para(
        f"Objet : Candidature au poste {_de(_titre)}"
        if _titre
        else "Objet : Candidature spontanée",
        space=12,
        bold=True,
    )
    para(_appel)

    # LE CORPS ECRIT A LA MAIN, meme regle qu'en anglais.
    if _corps:
        for _bloc in _corps:
            para(_bloc)
        para(
            f"Je vous prie d'agréer, {_reprise_civ}, l'expression de mes salutations distinguées.",
            space=12,
        )
        para(_ici.PROFILE["nom"], WD_ALIGN_PARAGRAPH.LEFT, 0)
        from jobhunter.programmes.rename_docs import new_name

        out_sm = _ici.LT_OUT / ((nom or new_name("Lettre", role, company)) + ".docx")
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
    if socle_txt.strip():  # parcours vide dans le profil : pas de paragraphe creux
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
            techs = [
                m
                for m in mots_techniques(
                    f"{offer.get('missions', '')} {offer.get('profil', '')} "
                    f"{offer.get('offer_text', '')}",
                    12,
                    "fr",
                )
                if m.lower() not in prose.lower()
            ][:4]
            phrase = f"Au fil de ce parcours, je me suis {_P.accord('familiarisé', 'familiarisée')} avec {prose}."
            if len(techs) >= 2:
                phrase += (
                    " Je pratique aussi ce que décrit votre annonce : " + ", ".join(techs) + "."
                )
            para(
                phrase + f" Ce sont des acquis que je serais {_P.accord('heureux', 'heureuse')} "
                "d'approfondir au sein de vos équipes."
            )
    # Le profil non plus n'est plus cite : meme copier-coller tronque, suivi
    # d'un point-virgule que personne n'ecrit dans une lettre.
    if _citable(profil, "fr") and profil.lower() not in ("non précisé", "à compléter", "nan"):
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
    para(
        f"Je vous prie d'agréer, {_reprise_civ}, l'expression de mes salutations distinguées.",
        space=12,
    )
    para(_ici.PROFILE["nom"], WD_ALIGN_PARAGRAPH.LEFT, 0)

    from jobhunter.programmes.rename_docs import (
        new_name,  # Prenom_Nom_Lettre_<Poste court>_<Entreprise>
    )

    out: Path = _ici.LT_OUT / ((nom or new_name("Lettre", role, company)) + ".docx")
    doc.save(str(out))
    return out
