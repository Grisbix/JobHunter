"""jobhunter.documents.message — The SHORT message that forms ask for.

Formerly Scripts/message_offre.py.

WHY. Business France, LinkedIn Easy Apply and many ATS ask, IN ADDITION to the CV
and the letter, for a free message of a few lines. Pasting the whole letter into
this field does not work: it is too long, and its layout (subject, salutation,
closing) makes no sense in an input box.

This message says three things, in this order, and nothing else:
  1. what I am and what I am aiming for,
  2. the precise fact that ties me to THIS mission,
  3. my availability.

It relies on the same base as the letter (SOCLE_FR / SOCLE_EN), so it tells the
same story as the attached CV — but tightened to the essentials.

The file goes next to the letter, as .txt: it is text to copy and paste, not a
document to attach.

Run:
  python JobHunter.pyw message --url https://...      # one offer
  python JobHunter.pyw message --contient Nexans
"""

import argparse
import re
import sys
from typing import Any, cast

from jobhunter import root as _racine

sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]  # console : TextIOWrapper

MSG_OUT = _racine.dossier("Lettres") / "Messages"

# All the texts come from the profile: domaines[] (hook, proof per
# domain) and the "message" section (degree, languages, facts, sources).

from jobhunter import lazy as _paresseux
from jobhunter import profile as _P

_ici = sys.modules[__name__]
# Values taken from the profile: computed on first read, not at import
# (jobhunter.lazy). In this module, they are read through `_ici.NAME`.
_PARESSEUX: _paresseux.Fabriques = {}


def __getattr__(nom: str) -> Any:
    return _paresseux.lire(_ici, _PARESSEUX, nom)


_PARESSEUX["_MSG"] = lambda: _P.get("message", {}) or {}


def _dom(cle: str, champ: str) -> str:
    return _P.domaine_par_cle(cle).get(champ) or ""


# One CV FACT per requested skill, as a BARE clause: the place and the
# context are added only once in the composition, otherwise two facts from the
# same internship repeat the employer's name in the same sentence. Each fact
# carries its SOURCE (an experience, a thesis, a personal project…), introduced
# once through `message.sources`. The order of the sources is the order of PRIORITY.
_PARESSEUX["FAITS_FR"] = lambda: (
    {
        lab: (v.get("source", ""), v.get("fr", ""))
        for lab, v in (_ici._MSG.get("faits") or {}).items()
        if v.get("fr")
    }
)
_PARESSEUX["FAITS_EN"] = lambda: (
    {
        lab: (v.get("source", ""), v.get("en", ""))
        for lab, v in (_ici._MSG.get("faits") or {}).items()
        if v.get("en")
    }
)
_PARESSEUX["_SOURCES"] = lambda: list((_ici._MSG.get("sources") or {}).keys())
_PARESSEUX["_TETE_FR"] = lambda: (
    {k: (v or {}).get("fr", "") for k, v in (_ici._MSG.get("sources") or {}).items()}
)
_PARESSEUX["_TETE_EN"] = lambda: (
    {k: (v or {}).get("en", "") for k, v in (_ici._MSG.get("sources") or {}).items()}
)


def preuve(offre: dict[str, Any], langue: str, ton: str = "sobre") -> str:
    """The CV facts that best answer THIS posting.

    Grouped by source so as to name the internship or the thesis only once.
    Falls back on the per-domain sentence when the posting asks for nothing we can
    illustrate: a generic but true sentence is better than silence.
    """
    from jobhunter.documents.common import match_skills
    from jobhunter.scoring.lexicon import cv_variant_key

    table = _ici.FAITS_EN if langue == "en" else _ici.FAITS_FR
    tete = _ici._TETE_EN if langue == "en" else _ici._TETE_FR
    demandees = set(match_skills(f"{offre.get('poste', '')} {offre.get('description', '')}"))

    groupes: dict[str, list[str]] = {}
    for lab, (src, clause) in table.items():
        if lab not in demandees:
            continue
        # Two skills may point to the same fact (SFDR and ESG analysis):
        # it is not written twice.
        if clause not in groupes.setdefault(src, []):
            groupes[src].append(clause)
    if not groupes:
        cle = cv_variant_key(offre.get("domaine"))
        if langue == "en":
            p = _dom(cle, "preuve_en")
        else:
            p = (ton == "detente" and _dom(cle, "preuve_detente_fr")) or _dom(cle, "preuve_fr")
        # Profile without a written proof: the FIRST sentence of the background, which
        # already states a CV fact. Better than an empty paragraph.
        if not p:
            parcours = _dom(cle, "parcours_en" if langue == "en" else "parcours_fr")
            p = (parcours.split(". ")[0].rstrip(".") + ".") if parcours else ""
        return p

    lien = " and " if langue == "en" else " et "
    phrases: list[str] = []
    # Two sources at most: three make an enumeration, not a sentence.
    for src in _ici._SOURCES:
        if src not in groupes or len(phrases) >= 2:
            continue
        # ONE SINGLE fact per source. Two facts from the same internship collided:
        # "j'ai prepare des projections financieres et suivi des ecarts ET
        # construit des modeles financiers ET des projections" — two "et"
        # in a row, the verb repeated, "projections" twice. Each clause
        # already carries its own "et" where it is useful.
        p = tete[src] + groupes[src][0]
        phrases.append(p[0].upper() + p[1:])
    return ". ".join(phrases) + "."


# THE ENVIRONMENTAL ASPECT, when the employer works in it. Same rule as
# in the letter: the job's domain says the PROFESSION, not the sector of the
# company. Albioma recruits in corporate finance and produces renewable
# energy; the message said nothing about it.
#
# The sentence is chosen according to the source ALREADY used by the proof. Without that,
# a message whose proof comes from the thesis chained "Dans mon mémoire,
# j'ai…" then "Mon mémoire a porté sur…" — two sentences in a row about the same
# objet.
# Context sentence (message.phrase_contexte_fr/en), when the letter itself
# adds a context to its background. It is chosen according to the source ALREADY
# quoted by the proof, otherwise two sentences in a row talk about the same thing:
#   - the proof quotes ONE source present in the table -> that key's sentence
#   - the proof quotes several sources                   -> nothing, it is enough
#   - otherwise                                          -> the "autre" sentence
_PARESSEUX["_CONTEXTE_FR"] = lambda: dict(_ici._MSG.get("phrase_contexte_fr") or {})
_PARESSEUX["_CONTEXTE_EN"] = lambda: dict(_ici._MSG.get("phrase_contexte_en") or {})


def _phrase_durable(offre: dict[str, Any], langue: str, preuve_texte: str) -> str:
    """The context sentence, or "" if the posting does not call for it."""
    from jobhunter.documents.letter import contexte_durable

    if not contexte_durable(
        dict(
            company=offre.get("entreprise"),
            role=offre.get("poste"),
            offer_text=offre.get("description"),
            domaine=offre.get("domaine"),
        ),
        langue,
    ):
        return ""
    table = _ici._CONTEXTE_EN if langue == "en" else _ici._CONTEXTE_FR
    tete = _ici._TETE_EN if langue == "en" else _ici._TETE_FR
    citees = [
        k for k in _ici._SOURCES if tete.get(k, "").strip() and tete[k].strip() in preuve_texte
    ]
    if len(citees) > 1:
        return ""
    cle = citees[0] if citees and citees[0] in table else "autre"
    return (" " + table[cle]) if table.get(cle) else ""


def _intro_role(offre: dict[str, Any], langue: str, ton: str = "sobre") -> str:
    """The CV facts that answer the posting. Nothing else.

    A sentence used to name the daily work described by the offer:

        "Cette mission m'interesse : elle porte sur la cloture mensuelle, le
          budget et le suivi des ecarts."

    It explained to the recruiter what their own job consists of, after announcing
    that we were interested in it. It is pompous in both halves: they wrote the
    posting, they know what is in it, and interest is shown rather than declared.

    The link with the posting is not lost for all that: the facts are CHOSEN on the
    skills it asks for. At Elior, "suivi des ecarts" answers their "identifier les
    principaux ecarts" without having to point it out. Show, do not announce.

    Corollary: no more duplicate to avoid, so the `sauf` parameter of preuve()
    disappears — the best fact is no longer set aside on the grounds that the removed
    sentence already quoted it.

    Added to it, at an employer working in sustainability, is a sentence on
    sustainable investment — see _phrase_durable().
    """
    p = preuve(offre, langue, ton)
    return p + _phrase_durable(offre, langue, p)


# ── The salutation, named when we know who we are talking to ──────────────────
#
# THE `rh` FIELD IS OVERLOADED, and it is the first thing to know. Measured on
# the queue of 21/09/2026, 4917 offers:
#
#     4501  vide
#      413  a LinkedIn SEARCH URL, not a person:
#           « https://www.linkedin.com/search/results/people/?keywords=... »
#        3  a real title followed by a name
#
# Writing "Bonjour https://www.linkedin.com/search..." would be worse than the
# generic formula. So this field is only used if it PARSES as a name.
#
# The three real names all come from the V.I.E detail API, the only source
# that returns `contactName`. Their number will grow as the V.I.E go
# through `add_vie.py`.
_RX_CIVILITE = re.compile(r"^\s*(monsieur|madame|mr|mrs|ms|mme|m)\.?\s+(.{2,})$", re.I)

# NOBILIARY particles: lower case even at the head of a surname. "Monsieur de
# Gaulle", never "Monsieur De Gaulle". Also valid for the Dutch and
# Ibero-Portuguese forms: "van den Berg", "dos Santos".
_PARTICULES = {
    "de",
    "du",
    "des",
    "d",
    "da",
    "das",
    "dos",
    "del",
    "della",
    "di",
    "van",
    "von",
    "der",
    "den",
    "ten",
    "ter",
    "el",
    "al",
    "bin",
    "ben",
}

# "Le" and "La" are NOT in this list: in French they carry a
# capital when they are part of the name — "Monsieur Le Pen", "Madame
# La Rochelle". Mixing them up with "de" would mangle one name in two.

# What looks like a name but designates a DEPARTMENT. Without this safeguard, a
# champ « Service Recrutement » produisait « Dear Service Recrutement, » —
# more ridiculous than the generic formula it replaces.
_RX_GUICHET = re.compile(
    r"\b(?:service|recrutement|recruitment|recruiting|talent|acquisition|"
    r"ressources?\s+humaines?|\brh\b|\bhr\b|human\s+resources|people|equipe|"
    r"[ée]quipe|team|d[ée]partement|department|direction|cellule|p[oô]le|"
    r"contact|candidature|careers?|emploi|jobs?|staffing|bureau)\b",
    re.I,
)


def _nom_propre(s: str) -> str:
    """“SILVA PEREIRA” -> "Silva Pereira".

    Handles hyphens and apostrophes: "JEAN-PIERRE" -> "Jean-Pierre", "O'BRIEN"
    -> "O'Brien".

    A name already correctly cased is NOT touched: "McDonald" and "van Gogh" would
    lose their shape going through a blind title().
    """

    def _mot(m: str, premier: bool) -> str:
        # `premier` does NOT protect the nobiliary particles: a surname
        # may start with them, and "Monsieur De Gaulle" is a mistake.
        if m.lower().rstrip(".'’") in _PARTICULES:
            return m.lower()
        if not m.isupper() and not m.islower():
            return m  # already cased by hand: we respect it
        out = []
        for morceau in re.split(r"([-'’])", m.lower()):
            out.append(morceau if morceau in "-'’" else morceau.capitalize())
        return "".join(out)

    mots = [w for w in s.split() if w]
    return " ".join(_mot(w, i == 0) for i, w in enumerate(mots))


def _patronyme(nom: str) -> str:
    """The SURNAME alone, from "Firstname SURNAME" or "FIRSTNAME SURNAME SURNAME".

    Two forms met in the Business France API:
      "Awa MOUSSA"             -> MIXED case: the capitals are the surname
      "KEVIN SILVA PEREIRA"    -> ALL in capitals: French administrative
                                     convention "Firstname SURNAME",
                                     so the first word is the first name
    """
    mots = [w for w in nom.split() if w]
    if not mots:
        return ""
    majs = [w for w in mots if w.isupper() and len(w) > 1]
    if majs and len(majs) < len(mots):
        return _nom_propre(" ".join(majs))  # casse mixte : tranche nette
    return _nom_propre(" ".join(mots[1:])) or _nom_propre(mots[0])


# A POSTING MAY NAME TWO. Mirova writes "adressez votre CV et votre
# lettre a Louis Mac Arthur et Clement Lebrun". Without splitting, `_patronyme`
# read the whole string as a single name and returned "Monsieur Mac
# Arthur et Monsieur Clement Lebrun" — the conjunction promoted to surname.
_RX_SEPARE = re.compile(r"\s+(?:et|and)\s+|\s*[&;+/]\s*", re.I)
GENERIQUES = ("Madame, Monsieur,", "Dear Sir or Madam,", "Bonjour,")


_CIVILITES = {"madame", "monsieur", "mme", "mr", "mrs", "ms", "m", "dr", "mlle", "mademoiselle"}


def nom_dans_offre(rh: str | None, texte: str | None) -> str:
    """`rh` if one of its names (excluding the title, at least 3 letters) appears in the TEXT of the posting, "" otherwise.

    The user, 2026-10-07: we do not name a recipient the posting does not name.
    Business France passes a "contactName" (Madame Rossi at Meridiam, Madame Lopez
    at Schneider) that appears nowhere in the published text: addressing that person
    gives away that we read a technical field, not the offer.
    """
    import unicodedata

    def n(s: object) -> str:
        s = unicodedata.normalize("NFD", str(s or "").lower())
        return "".join(c for c in s if not unicodedata.combining(c))

    t = n(texte)
    mots = [m for m in re.split(r"[^a-z]+", n(rh)) if len(m) >= 3 and m not in _CIVILITES]
    if any(re.search(r"(?<![a-z])" + re.escape(m) + r"(?![a-z])", t) for m in mots):
        return rh or ""
    return ""


def appel(offre: dict[str, Any], langue: str = "fr", ton: str = "sobre") -> str:
    """The salutation.

    Named if `rh` carries a title and a name, generic otherwise. Several names
    separated by "et" are all used.

    GENDER IS NOT GUESSED FROM A FIRST NAME. Without an explicit title in the field,
    we do not choose between "Monsieur" and "Madame": in English we address the full
    name, which is perfectly fine; in French no named formula is neutral, so we keep
    the generic one.
    """
    rh = (offre.get("rh") or "").strip()
    # A complete offer (with its text): the name must appear in it.
    if "description" in offre:
        rh = nom_dans_offre(rh, f"{offre.get('poste', '')} {offre.get('description') or ''}")
    generique = (
        "Dear Sir or Madam,"
        if langue == "en"
        else "Bonjour,"
        if ton == "detente"
        else "Madame, Monsieur,"
    )
    # Neither a URL, nor a department, nor an email address: we want a PERSON.
    # URL and email address are tested BEFORE the split: a URL contains
    # slashes, which are a separator, and being chopped into ten
    # fragments leads nowhere. The DEPARTMENT, on the other hand, is tested AFTER: in
    # "Monsieur Martin / Service Recrutement" it only disqualifies the
    # second half, and rejecting the whole field lost a usable name.
    if not rh or rh.lower().startswith(("http://", "https://", "www.")) or "@" in rh:
        return generique

    # Several recipients. WE ONLY KEEP THE PIECES THAT ARE
    # PEOPLE, and we never fall back on the whole string: "Monsieur
    # Jean et Marie Dupont" would give back "Monsieur Et Marie Dupont".
    # Setting aside the silent piece also serves "Monsieur Martin / RH", whose
    # first half stays usable.
    morceaux = [x.strip() for x in _RX_SEPARE.split(rh) if x.strip()]
    if len(morceaux) > 1:
        noms = [appel({"rh": x}, langue, ton) for x in morceaux]
        noms = [n.rstrip(",") for n in noms if n not in GENERIQUES]
        if not noms:
            return generique
        if langue == "en":
            return "Dear " + " and ".join(n[len("Dear ") :] for n in noms) + ","
        return ", ".join(noms) + ","

    if _RX_GUICHET.search(rh):
        return generique

    m = _RX_CIVILITE.match(rh)
    if not m:
        # A name without a title: usable in English, not in French.
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


def message(offre: dict[str, Any], langue: str | None = None, ton: str = "sobre") -> str:
    """The text to paste into the form.

    `ton`: sobre | detente. An empty field of the profile does not leave an empty paragraph.
    """
    return re.sub(r"\n{3,}", "\n\n", _message(offre, langue, ton)).strip()


def _message(offre: dict[str, Any], langue: str | None = None, ton: str = "sobre") -> str:
    """The text to paste into the form. `ton`: sobre | detente."""
    from jobhunter.documents.common import minuscule_titre, titre_poste
    from jobhunter.scoring.language import langue_offre
    from jobhunter.scoring.lexicon import cv_variant_key

    lg = langue or langue_offre(
        offre.get("poste"), offre.get("description"), offre.get("localisation")
    )
    cle = cv_variant_key(offre.get("domaine"))
    titre = titre_poste(offre.get("poste") or "") or ""
    # Same rule as in the letter: in French a job title is a
    # common noun, and a posting in capitals must not make the message
    # shout. "je postule au poste de CORPORATE FINANCE HF chez ALBIOMA"
    # was the exact quotation of a posting, copied without regard.
    if lg != "en":
        titre = minuscule_titre(titre)
    # The whole title weighs down a five-line message: we keep the first
    # segment, as on the CV.
    tete = titre.split(" - ")[0].strip()
    if 12 <= len(tete) < len(titre):
        titre = tete
    soc = (offre.get("entreprise") or "").strip()

    nom = _P.identite()["nom"]

    def lien(diplome: str) -> str:
        # "Je suis analyste ESG, diplômé de …, et je postule": the degree
        # is optional in the profile, the sentence must stand without it.
        return f", {diplome}," if diplome else ""

    if lg == "en":
        dip = _ici._MSG.get("diplome_en", "")
        return (
            f"{appel(offre, 'en')}\n\n"
            f"I am {_un(_dom(cle, 'accroche_en'))}{lien(dip)} and I am "
            f"applying for the {titre} position at {soc}.\n\n"
            + f"{_intro_role(offre, 'en')} {_ici._MSG.get('langues_en', '')}".strip()
            + "\n\n"
            "My CV and cover letter are attached. I would be glad to discuss the role with you "
            "and am available at your convenience.\n\n"
            f"Kind regards,\n{nom}"
        )
    if ton == "detente":
        # A background abroad is told without bravado: the fact is enough.
        dip = _ici._MSG.get("diplome_detente_fr") or _ici._MSG.get("diplome_fr", "")
        langues = _ici._MSG.get("langues_detente_fr") or _ici._MSG.get("langues_fr", "")
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
    dip = _ici._MSG.get("diplome_fr", "")
    return (
        f"{appel(offre, 'fr')}\n\n"
        f"Je suis {_dom(cle, 'accroche_fr')}{lien(dip)} et je "
        f"postule au poste {_de_titre(titre)} chez {soc}.\n\n"
        + f"{_intro_role(offre, 'fr')} {_ici._MSG.get('langues_fr', '')}".strip()
        + "\n\n"
        "Mon CV et ma lettre de motivation sont joints. Je serais "
        f"{_P.accord('heureux', 'heureuse')} d'échanger avec vous "
        "sur ce poste et me tiens à votre disposition.\n\n"
        f"Cordialement,\n{nom}"
    )


def _un(nom: str) -> str:
    """Article: "a junior analyst", "an ESG analyst": the article follows the initial SOUND; an acronym is read letter by letter ("an ESG", "an MBA")."""
    if not nom:
        return ""
    mot = nom.split()[0]
    sigle_voyelle = mot.isupper() and mot[0] in "AEFHILMNORSX"
    return ("an " if (mot[0].lower() in "aeiou" or sigle_voyelle) else "a ") + nom


def _de_titre(t: str) -> str:
    from jobhunter.documents.common import _de

    return _de(t) if t else "proposé"


def main() -> int:
    """Command line: writes an offer's short message into Lettres/Messages."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="", help="fragment de l'URL de l'offre")
    ap.add_argument("--contient", default="", help="fragment du nom de l'entreprise")
    # TotalEnergies Congo publishes in French but asks "Merci de candidater
    # en anglais": the detection reads the language of the TEXT, not this instruction.
    # Without this flag, the message would be French while the CV and the letter
    # are English — three documents, two languages.
    ap.add_argument(
        "--langue",
        choices=("fr", "en"),
        default=None,
        help="forcer la langue (defaut : celle de l'annonce)",
    )
    ap.add_argument(
        "--ton",
        choices=("sobre", "detente"),
        default="sobre",
        help="registre : detente = moins raide, memes faits",
    )
    a = ap.parse_args()
    if not (a.url or a.contient):
        ap.error("donner --url ou --contient")

    from jobhunter.programs.rename_docs import new_name
    from jobhunter.storage import queue as queue_io

    q = queue_io.charger()
    cibles = [
        o
        for o in q
        if (a.url and a.url in (o.get("url") or ""))
        or (a.contient and a.contient.lower() in (o.get("entreprise") or "").lower())
    ]
    if not cibles:
        print("aucune offre ne correspond")
        return 1
    for o in cibles:
        txt = message(cast(dict[str, Any], o), langue=a.langue, ton=a.ton)
        MSG_OUT.mkdir(parents=True, exist_ok=True)  # at write time, not at import
        f = MSG_OUT / (new_name("Message", o.get("poste", ""), o.get("entreprise", "")) + ".txt")
        f.write_text(txt, encoding="utf-8")
        print(f"\n=== {o.get('entreprise')} — {(o.get('poste') or '')[:50]} ===")
        print(txt)
        print(f"\n-> {f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
