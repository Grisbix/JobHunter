#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""message_offre.py — Le message COURT que demandent les formulaires.

POURQUOI. Business France, LinkedIn Easy Apply et beaucoup d'ATS demandent,
EN PLUS du CV et de la lettre, un message libre de quelques lignes. Coller la
lettre entiere dans ce champ ne marche pas : elle est trop longue, et sa mise
en page (objet, formule d'appel, salutations) n'a aucun sens dans une zone de
saisie.

Ce message dit trois choses, dans cet ordre, et rien d'autre :
  1. ce que je suis et ce que je vise,
  2. le fait precis qui me rattache a CETTE mission,
  3. ma disponibilite.

Il s'appuie sur le meme socle que la lettre (SOCLE_FR / SOCLE_EN), donc il
raconte le meme parcours que le CV joint — mais resserre a l'essentiel.

Le fichier va a cote de la lettre, en .txt : c'est du texte a copier-coller,
pas un document a joindre.

Run :
  python message_offre.py --url https://...      # une offre
  python message_offre.py --contient Nexans
"""
import sys
import argparse
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

MSG_OUT = HERE.parent / "Lettres" / "Messages"
MSG_OUT.mkdir(parents=True, exist_ok=True)

# Tous les textes viennent du profil : domaines[] (accroche, preuve par
# domaine) et la section « message » (diplome, langues, faits, sources).
import profil as _P
_MSG = _P.get("message", {}) or {}


def _dom(cle, champ):
    return _P.domaine_par_cle(cle).get(champ) or ""


# Un FAIT du CV par competence demandee, en proposition NUE : le lieu et le
# contexte sont ajoutes une seule fois a la composition, sinon deux faits du
# meme stage repetent le nom de l'employeur dans la meme phrase. Chaque fait
# porte sa SOURCE (une experience, un memoire, un projet perso…), introduite
# une fois par `message.sources`. L'ordre des sources est l'ordre de PRIORITE.
FAITS_FR = {lab: (v.get("source", ""), v.get("fr", "")) for lab, v in (_MSG.get("faits") or {}).items()
            if v.get("fr")}
FAITS_EN = {lab: (v.get("source", ""), v.get("en", "")) for lab, v in (_MSG.get("faits") or {}).items()
            if v.get("en")}
_SOURCES = list((_MSG.get("sources") or {}).keys())
_TETE_FR = {k: (v or {}).get("fr", "") for k, v in (_MSG.get("sources") or {}).items()}
_TETE_EN = {k: (v or {}).get("en", "") for k, v in (_MSG.get("sources") or {}).items()}


def preuve(offre, langue, ton="sobre"):
    """Les faits du CV qui repondent le mieux a CETTE annonce.

    Groupes par source pour ne nommer le stage ou le memoire qu'une fois.
    Se rabat sur la phrase par domaine quand l'annonce ne demande rien qu'on
    sache illustrer : mieux vaut une phrase generique mais vraie qu'un silence.
    """
    from tailor_application import match_skills, cv_variant_key
    table = FAITS_EN if langue == "en" else FAITS_FR
    tete = _TETE_EN if langue == "en" else _TETE_FR
    demandees = set(match_skills(f"{offre.get('poste','')} {offre.get('description','')}"))

    groupes = {}
    for lab, (src, clause) in table.items():
        if lab not in demandees:
            continue
        # Deux competences peuvent pointer le meme fait (SFDR et Analyse ESG) :
        # on ne l'ecrit pas deux fois.
        if clause not in groupes.setdefault(src, []):
            groupes[src].append(clause)
    if not groupes:
        cle = cv_variant_key(offre.get("domaine"))
        if langue == "en":
            p = _dom(cle, "preuve_en")
        else:
            p = (ton == "detente" and _dom(cle, "preuve_detente_fr")) or _dom(cle, "preuve_fr")
        # Profil sans preuve ecrite : la PREMIERE phrase du parcours, qui dit
        # deja un fait du CV. Mieux qu'un paragraphe vide.
        if not p:
            parcours = _dom(cle, "parcours_en" if langue == "en" else "parcours_fr")
            p = (parcours.split(". ")[0].rstrip(".") + ".") if parcours else ""
        return p

    lien = " and " if langue == "en" else " et "
    phrases = []
    # Deux sources au plus : trois font une enumeration, pas une phrase.
    for src in _SOURCES:
        if src not in groupes or len(phrases) >= 2:
            continue
        # UN SEUL fait par source. Deux faits du meme stage se telescopaient :
        # « j'ai prepare des projections financieres et suivi des ecarts ET
        # construit des modeles financiers ET des projections » — deux « et »
        # d'affilee, le verbe repete, « projections » deux fois. Chaque clause
        # porte deja son propre « et » la ou il est utile.
        p = tete[src] + groupes[src][0]
        phrases.append(p[0].upper() + p[1:])
    return ". ".join(phrases) + "."


# L'ASPECT ENVIRONNEMENTAL, quand l'employeur travaille dedans. Meme regle que
# dans la lettre : le domaine du poste dit le METIER, pas le secteur de la
# maison. Albioma recrute en corporate finance et produit de l'energie
# renouvelable ; le message n'en disait rien.
#
# La phrase est choisie selon la source DEJA employee par la preuve. Sans cela,
# un message dont la preuve vient du memoire enchainait « Dans mon mémoire,
# j'ai… » puis « Mon mémoire a porté sur… » — deux phrases de suite sur le meme
# objet.
# Phrase de contexte (message.phrase_contexte_fr/en), quand la lettre ajoute
# elle-meme un contexte a son parcours. Elle est choisie selon la source DEJA
# citee par la preuve, sinon deux phrases de suite parlent du meme objet :
#   - la preuve cite UNE source presente dans la table -> la phrase de cette cle
#   - la preuve cite plusieurs sources                  -> rien, elle se suffit
#   - sinon                                             -> la phrase « autre »
_CONTEXTE_FR = dict(_MSG.get("phrase_contexte_fr") or {})
_CONTEXTE_EN = dict(_MSG.get("phrase_contexte_en") or {})


def _phrase_durable(offre, langue, preuve_texte):
    """La phrase de contexte, ou "" si l'annonce n'y appelle pas."""
    from tailor_application import contexte_durable
    if not contexte_durable(dict(company=offre.get("entreprise"),
                                 role=offre.get("poste"),
                                 offer_text=offre.get("description"),
                                 domaine=offre.get("domaine")), langue):
        return ""
    table = _CONTEXTE_EN if langue == "en" else _CONTEXTE_FR
    tete = _TETE_EN if langue == "en" else _TETE_FR
    citees = [k for k in _SOURCES if tete.get(k, "").strip() and tete[k].strip() in preuve_texte]
    if len(citees) > 1:
        return ""
    cle = citees[0] if citees and citees[0] in table else "autre"
    return (" " + table[cle]) if table.get(cle) else ""


def _intro_role(offre, langue, ton="sobre"):
    """Les faits du CV qui repondent a l'annonce. Rien d'autre.

    Une phrase nommait auparavant le quotidien decrit par l'offre :

        « Cette mission m'interesse : elle porte sur la cloture mensuelle, le
          budget et le suivi des ecarts. »

    Elle expliquait au recruteur en quoi consiste son propre poste, apres avoir
    annonce qu'on s'y interessait. C'est pompeux dans les deux moities : il a
    ecrit l'annonce, il sait ce qu'il y a dedans, et l'interet se demontre au
    lieu de se declarer.

    Le lien avec l'annonce n'est pas perdu pour autant : les faits sont
    CHOISIS sur les competences qu'elle demande. Chez Elior, « suivi des
    ecarts » repond a leur « identifier les principaux ecarts » sans avoir a le
    souligner. Montrer, pas annoncer.

    Corollaire : plus de doublon a eviter, donc le parametre `sauf` de
    preuve() disparait — le meilleur fait n'est plus ecarte au motif que la
    phrase supprimee le citait deja.

    S'y ajoute, chez un employeur qui travaille dans la durabilite, une phrase
    sur l'investissement durable — voir _phrase_durable().
    """
    p = preuve(offre, langue, ton)
    return p + _phrase_durable(offre, langue, p)


# ── La formule d'appel, nominative quand on sait a qui l'on parle ───────────
#
# LE CHAMP `rh` EST SURCHARGE, et c'est la premiere chose a savoir. Mesure sur
# la file du 21/09/2026, 4917 offres :
#
#     4501  vide
#      413  une URL de RECHERCHE LinkedIn, pas une personne :
#           « https://www.linkedin.com/search/results/people/?keywords=... »
#        3  une vraie civilite suivie d'un nom
#
# Ecrire « Bonjour https://www.linkedin.com/search... » serait pire que la
# formule generique. On n'utilise donc ce champ que s'il PARSE comme un nom.
#
# Les trois vrais noms viennent tous de l'API detail des V.I.E, la seule source
# qui rende `contactName`. Leur nombre grandira a mesure que les V.I.E passent
# par `ajoute_vie.py`.
_RX_CIVILITE = re.compile(
    r"^\s*(monsieur|madame|mr|mrs|ms|mme|m)\.?\s+(.{2,})$", re.I)

# Particules NOBILIAIRES : minuscules meme en tete de patronyme. « Monsieur de
# Gaulle », jamais « Monsieur De Gaulle ». Valable aussi pour les formes
# neerlandaises et ibero-portugaises : « van den Berg », « dos Santos ».
_PARTICULES = {"de", "du", "des", "d", "da", "das", "dos", "del", "della", "di",
               "van", "von", "der", "den", "ten", "ter", "el", "al", "bin", "ben"}

# « Le » et « La » NE SONT PAS dans cette liste : en francais ils portent la
# majuscule quand ils font corps avec le nom — « Monsieur Le Pen », « Madame
# La Rochelle ». Les confondre avec « de » ecorcherait un nom sur deux.

# Ce qui ressemble a un nom mais designe un SERVICE. Sans ce garde-fou, un
# champ « Service Recrutement » produisait « Dear Service Recrutement, » —
# plus ridicule que la formule generique qu'il remplace.
_RX_GUICHET = re.compile(
    r"\b(?:service|recrutement|recruitment|recruiting|talent|acquisition|"
    r"ressources?\s+humaines?|\brh\b|\bhr\b|human\s+resources|people|equipe|"
    r"[ée]quipe|team|d[ée]partement|department|direction|cellule|p[oô]le|"
    r"contact|candidature|careers?|emploi|jobs?|staffing|bureau)\b", re.I)


def _nom_propre(s):
    """« SILVA PEREIRA » -> « Silva Pereira ». Gere traits d'union et
    apostrophes : « JEAN-PIERRE » -> « Jean-Pierre », « O'BRIEN » -> « O'Brien ».

    Un nom deja correctement casse n'est PAS retouche : « McDonald » et
    « van Gogh » perdraient leur forme a passer dans un title() aveugle.
    """
    def _mot(m, premier):
        # `premier` ne protege PAS les particules nobiliaires : un patronyme
        # peut commencer par elles, et « Monsieur De Gaulle » est une faute.
        if m.lower().rstrip(".'’") in _PARTICULES:
            return m.lower()
        if not m.isupper() and not m.islower():
            return m                       # deja casse a la main : on respecte
        out = []
        for morceau in re.split(r"([-'’])", m.lower()):
            out.append(morceau if morceau in "-'’" else morceau.capitalize())
        return "".join(out)
    mots = [w for w in s.split() if w]
    return " ".join(_mot(w, i == 0) for i, w in enumerate(mots))


def _patronyme(nom):
    """Le NOM DE FAMILLE seul, depuis « Prenom NOM » ou « PRENOM NOM NOM ».

    Deux formes rencontrees dans l'API Business France :
      « Awa MOUSSA »            -> casse MIXTE : les capitales sont le nom
      « KEVIN SILVA PEREIRA »   -> TOUT en capitales : convention
                                     administrative francaise « Prenom NOM »,
                                     donc le premier mot est le prenom
    """
    mots = [w for w in nom.split() if w]
    if not mots:
        return ""
    majs = [w for w in mots if w.isupper() and len(w) > 1]
    if majs and len(majs) < len(mots):
        return _nom_propre(" ".join(majs))          # casse mixte : tranche nette
    return _nom_propre(" ".join(mots[1:])) or _nom_propre(mots[0])


# UNE ANNONCE PEUT EN NOMMER DEUX. Mirova ecrit « adressez votre CV et votre
# lettre a Louis Mac Arthur et Clement Lebrun ». Sans decoupe, `_patronyme`
# lisait la chaine entiere comme un seul nom et rendait « Monsieur Mac
# Arthur et Monsieur Clement Lebrun » — la conjonction promue patronyme.
_RX_SEPARE = re.compile(r"\s+(?:et|and)\s+|\s*[&;+/]\s*", re.I)
GENERIQUES = ("Madame, Monsieur,", "Dear Sir or Madam,", "Bonjour,")


_CIVILITES = {"madame", "monsieur", "mme", "mr", "mrs", "ms", "m", "dr", "mlle", "mademoiselle"}


def nom_dans_offre(rh, texte):
    """`rh` si l'un de ses noms (hors civilite, 3 lettres au moins) figure dans
    le TEXTE de l'annonce, "" sinon.

    l'utilisateur, 2026-10-07 : on ne nomme pas un destinataire que l'annonce ne
    nomme pas. Business France transmet un « contactName » (Madame Rossi chez
    Meridiam, Madame Lopez chez Schneider) qui n'apparait nulle part dans le
    texte publie : s'adresser a cette personne trahit qu'on a lu un champ
    technique, pas l'offre."""
    import unicodedata

    def n(s):
        s = unicodedata.normalize("NFD", str(s or "").lower())
        return "".join(c for c in s if not unicodedata.combining(c))
    t = n(texte)
    mots = [m for m in re.split(r"[^a-z]+", n(rh)) if len(m) >= 3 and m not in _CIVILITES]
    if any(re.search(r"(?<![a-z])" + re.escape(m) + r"(?![a-z])", t) for m in mots):
        return rh
    return ""


def appel(offre, langue="fr", ton="sobre"):
    """La formule d'appel. Nominative si `rh` porte une civilite et un nom,
    generique sinon. Plusieurs noms separes par « et » sont tous repris.

    LE GENRE NE SE DEVINE PAS D'UN PRENOM. Sans civilite explicite dans le
    champ, on ne choisit pas entre « Monsieur » et « Madame » : en anglais on
    s'adresse au nom complet, ce qui se dit parfaitement ; en francais aucune
    formule nominative n'est neutre, donc on garde la generique.
    """
    rh = (offre.get("rh") or "").strip()
    # Une offre complete (avec son texte) : le nom doit y figurer.
    if "description" in offre:
        rh = nom_dans_offre(rh, f"{offre.get('poste', '')} {offre.get('description') or ''}")
    generique = ("Dear Sir or Madam," if langue == "en"
                 else "Bonjour," if ton == "detente" else "Madame, Monsieur,")
    # Ni une URL, ni un guichet, ni une adresse mail : on veut une PERSONNE.
    # URL et adresse mail se testent AVANT la decoupe : une URL contient des
    # barres obliques, qui sont un separateur, et s'y faire hacher en dix
    # fragments ne mene nulle part. Le GUICHET, lui, se teste APRES : dans
    # « Monsieur Martin / Service Recrutement » il ne disqualifie que la
    # seconde moitie, et rejeter le champ entier perdait un nom exploitable.
    if (not rh
            or rh.lower().startswith(("http://", "https://", "www."))
            or "@" in rh):
        return generique

    # Plusieurs destinataires. ON NE GARDE QUE LES MORCEAUX QUI SONT DES
    # PERSONNES, et on ne retombe jamais sur la chaine entiere : « Monsieur
    # Jean et Marie Dupont » y redonnerait « Monsieur Et Marie Dupont ».
    # Ecarter le morceau muet sert aussi « Monsieur Martin / RH », dont la
    # premiere moitie reste exploitable.
    morceaux = [x.strip() for x in _RX_SEPARE.split(rh) if x.strip()]
    if len(morceaux) > 1:
        noms = [appel({"rh": x}, langue, ton) for x in morceaux]
        noms = [n.rstrip(",") for n in noms if n not in GENERIQUES]
        if not noms:
            return generique
        if langue == "en":
            return "Dear " + " and ".join(n[len("Dear "):] for n in noms) + ","
        return ", ".join(noms) + ","

    if _RX_GUICHET.search(rh):
        return generique

    m = _RX_CIVILITE.match(rh)
    if not m:
        # Un nom sans civilite : exploitable en anglais, pas en francais.
        nom = _nom_propre(rh)
        if langue == "en" and 1 < len(nom.split()) < 6:
            return f"Dear {nom},"
        return generique

    civ, nom = m.group(1).lower(), m.group(2).strip()
    fam = _patronyme(nom)
    if not fam:
        return generique
    if langue == "en":
        titre = {"madame": "Ms", "mme": "Ms", "mrs": "Ms", "ms": "Ms"}.get(civ, "Mr")
        return f"Dear {titre} {fam},"
    titre = "Madame" if civ in ("madame", "mme", "mrs", "ms") else "Monsieur"
    return f"{titre} {fam},"


def message(offre, langue=None, ton="sobre"):
    """Le texte a coller dans le formulaire. `ton` : sobre | detente.
    Un champ vide du profil ne laisse pas de paragraphe vide."""
    return re.sub(r"\n{3,}", "\n\n", _message(offre, langue, ton)).strip()


def _message(offre, langue=None, ton="sobre"):
    """Le texte a coller dans le formulaire. `ton` : sobre | detente."""
    from tailor_application import cv_variant_key, titre_poste, minuscule_titre
    from langue import langue_offre
    lg = langue or langue_offre(offre.get("poste"), offre.get("description"),
                                offre.get("localisation"))
    cle = cv_variant_key(offre.get("domaine"))
    titre = titre_poste(offre.get("poste") or "") or ""
    # Meme regle que dans la lettre : en francais un intitule de poste est un
    # nom commun, et une annonce en capitales ne doit pas faire crier le
    # message. « je postule au poste de CORPORATE FINANCE HF chez ALBIOMA »
    # etait la citation exacte d'une annonce, recopiee sans egard.
    if lg != "en":
        titre = minuscule_titre(titre)
    # Le titre entier alourdit un message de cinq lignes : on garde le premier
    # segment, comme sur le CV.
    tete = titre.split(" - ")[0].strip()
    if 12 <= len(tete) < len(titre):
        titre = tete
    soc = (offre.get("entreprise") or "").strip()

    nom = _P.identite()["nom"]

    def lien(diplome):
        # « Je suis analyste ESG, diplômé de …, et je postule » : le diplome
        # est optionnel dans le profil, la phrase doit tenir sans lui.
        return f", {diplome}," if diplome else ""

    if lg == "en":
        dip = _MSG.get("diplome_en", "")
        return (
            f"{appel(offre, 'en')}\n\n"
            f"I am {_un(_dom(cle, 'accroche_en'))}{lien(dip)} and I am "
            f"applying for the {titre} position at {soc}.\n\n"
            + f"{_intro_role(offre, 'en')} {_MSG.get('langues_en', '')}".rstrip() + "\n\n"
            "My CV and cover letter are attached. I would be glad to discuss the role with you "
            "and am available at your convenience.\n\n"
            f"Kind regards,\n{nom}"
        )
    if ton == "detente":
        # Un parcours a l'etranger se raconte sans bravade : le fait suffit.
        dip = _MSG.get("diplome_detente_fr") or _MSG.get("diplome_fr", "")
        langues = _MSG.get("langues_detente_fr") or _MSG.get("langues_fr", "")
        return (
            f"{appel(offre, 'fr', 'detente')}\n\n"
            f"Je suis {_dom(cle, 'accroche_fr')}{lien(dip)} et je postule au poste "
            f"{_de_titre(titre)} chez {soc}.\n\n"
            f"{_intro_role(offre, 'fr', 'detente')}\n\n"
            + (f"{langues}\n\n" if langues else "")
            + "Vous trouverez mon CV et ma lettre en pièces jointes. Je serais "
            f"{_P.accord('ravi', 'ravie')} d'en discuter avec vous.\n\n"
            f"Bien à vous,\n{nom}"
        )
    dip = _MSG.get("diplome_fr", "")
    return (
        f"{appel(offre, 'fr')}\n\n"
        f"Je suis {_dom(cle, 'accroche_fr')}{lien(dip)} et je "
        f"postule au poste {_de_titre(titre)} chez {soc}.\n\n"
        + f"{_intro_role(offre, 'fr')} {_MSG.get('langues_fr', '')}".rstrip() + "\n\n"
        "Mon CV et ma lettre de motivation sont joints. Je serais "
        f"{_P.accord('heureux', 'heureuse')} d'échanger avec vous "
        "sur ce poste et me tiens à votre disposition.\n\n"
        f"Cordialement,\n{nom}"
    )


def _un(nom):
    """« a junior analyst », « an ESG analyst » : l'article suit le SON initial ;
    un sigle se lit lettre par lettre (« an ESG », « an MBA »)."""
    if not nom:
        return ""
    mot = nom.split()[0]
    sigle_voyelle = mot.isupper() and mot[0] in "AEFHILMNORSX"
    return ("an " if (mot[0].lower() in "aeiou" or sigle_voyelle) else "a ") + nom


def _de_titre(t):
    from tailor_application import _de
    return _de(t) if t else "proposé"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="", help="fragment de l'URL de l'offre")
    ap.add_argument("--contient", default="", help="fragment du nom de l'entreprise")
    # TotalEnergies Congo publie en francais mais demande « Merci de candidater
    # en anglais » : la detection lit la langue du TEXTE, pas cette consigne.
    # Sans ce drapeau, le message serait francais alors que le CV et la lettre
    # sont anglais — trois pieces, deux langues.
    ap.add_argument("--langue", choices=("fr", "en"), default=None,
                    help="forcer la langue (defaut : celle de l'annonce)")
    ap.add_argument("--ton", choices=("sobre", "detente"), default="sobre",
                    help="registre : detente = moins raide, memes faits")
    a = ap.parse_args()
    if not (a.url or a.contient):
        ap.error("donner --url ou --contient")

    import queue_io
    from rename_docs import new_name
    q = queue_io.charger()
    cibles = [o for o in q
              if (a.url and a.url in (o.get("url") or ""))
              or (a.contient and a.contient.lower() in (o.get("entreprise") or "").lower())]
    if not cibles:
        print("aucune offre ne correspond")
        return 1
    for o in cibles:
        txt = message(o, langue=a.langue, ton=a.ton)
        f = MSG_OUT / (new_name("Message", o.get("poste", ""), o.get("entreprise", "")) + ".txt")
        f.write_text(txt, encoding="utf-8")
        print(f"\n=== {o.get('entreprise')} — {(o.get('poste') or '')[:50]} ===")
        print(txt)
        print(f"\n-> {f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
