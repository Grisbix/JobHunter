"""Suggest an application status from an email. Pure functions, no network.

Part of jobhunter.mail. Two questions per email:

1. **Which application?** The tracked one whose company appears in the sender
   (display name or domain) or in the subject. A company named only in the body
   is enough only if the job title is there too: newsletters mention many
   companies. Two applications at the same company: the one whose title appears,
   otherwise none (we do not guess).
2. **Which status?** Rejection, interview or acknowledgement, from phrases in
   French, English and German. Rejection comes first: a rejection letter often
   thanks you for applying. Each status has STRONG phrases, enough on their own,
   and WEAK ones, too common elsewhere: "Unfortunately we need to reschedule your
   interview" is no rejection, and an acknowledgement that promises "next steps"
   is no interview. Two distinct weak rejection phrases make a rejection; a weak
   interview phrase counts only in a message that is not an acknowledgement.
   (Tiers taken from career-ops' invite-match, after its false rejections.)

A status only moves forward: an acknowledgement only takes "à postuler" to
"postulé"; an interview never goes back to "postulé"; nothing replaces a
rejection. The result is a list of `Proposition`, which the user validates one by one.
"""

import re
import unicodedata
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from jobhunter.mail.reading import Courriel

REFUS, ENTRETIEN, POSTULE = "refus", "entretien", "postulé"

# Rank of each status in the life of an application: we only suggest moving forward.
_RANG = {
    "": 0,
    "à postuler": 0,
    "à vérifier": 0,
    POSTULE: 1,
    "relancé": 1,
    ENTRETIEN: 2,
    REFUS: 3,
}


def _rx(*motifs: str) -> tuple[re.Pattern[str], ...]:
    return tuple(re.compile(m, re.I) for m in motifs)


# A rejection on its own: these sentences have no other use.
_REFUS_FORT = _rx(
    r"(?:pas|plus) (?:pouvoir )?donner (?:une )?suite"
    r"|ne (?:pouvons|pourrons) (?:pas |plus )?donner (?:une )?suite",
    r"pas (?:été )?retenue?",
    r"avons (?:décidé|choisi) de (?:poursuivre|retenir) (?:avec )?d.autres",
    r"issue défavorable",
    r"decided not to move forward|not (?:to )?move forward with (?:your|you)"
    r"|not moving forward with your|move forward with other",
    r"decided to pursue other|pursu(?:e|ing) other candidates|candidates whose (?:profile|experience|qualifications)",
    r"not (?:been )?selected (?:for this|to advance)|will not be progressing your application",
    r"\babsage\b|nicht (?:weiter )?berücksichtig|für (?:einen )?anderen? (?:Bewerber|Kandidat)",
)
# Rejection words that also open reschedules, delays and unrelated bad news.
_REFUS_FAIBLE = _rx(
    r"unfortunately|malheureusement|leider",
    r"regrettons|regret to inform",
    r"ne correspond(?:ait)? pas",
    r"d.autres candidat|other candidates",
    r"(?:was|has) not (?:been )?successful|unsuccessful",
    r"not (?:been )?selected(?! yet)",  # "a candidate has not been selected yet" is a delay
    r"will not be (?:progressing|proceeding)",
)
_ENTRETIEN_FORT = _rx(
    r"échange (?:téléphonique|visio)|vous rencontrer|vos disponibilités|vous convier",
    r"invite you to|schedule (?:a|an) (?:call|meeting|chat|interview)|your availability"
    r"|phone screen",
    r"vorstellungsgespräch|terminvorschlag",
)
# "interview" and "next steps" are also in every acknowledgement.
_ENTRETIEN_FAIBLE = _rx(r"entretien|interview|next step|prochaine étape|kennenlernen")
_ACCUSE = _rx(
    r"bien reçu votre candidature|accusé de réception|avons bien reçu|merci (?:pour|de) votre "
    r"candidature|confirmons la réception"
    r"|thank you for (?:applying|your application)|(?:we have |we've )?received your application"
    r"|application (?:has been )?received|thanks for applying"
    r"|eingang ihrer bewerbung|vielen dank für ihre bewerbung|bewerbung erhalten",
)


def _trouves(motifs: tuple[re.Pattern[str], ...], texte: str) -> list[str]:
    """The phrase each pattern finds, one per pattern that matches."""
    return [m.group(0) for rx in motifs if (m := rx.search(texte))]


# Words that do not designate a company: legal forms, "groupe", countries…
_VIDES = {
    "sa", "sas", "sasu", "sarl", "se", "ag", "gmbh", "kg", "ltd", "llc", "inc", "plc", "bv",
    "nv", "spa", "group", "groupe", "france", "paris", "europe", "international", "the",
    "and", "et", "de", "des", "du", "la", "le", "les", "company", "co", "holding", "partners",
}  # fmt: skip


@dataclass(frozen=True)
class Proposition:
    """A status suggested by an email, to be validated."""

    oid: str  # « entreprise|poste »
    actuel: str
    propose: str
    raison: str  # the phrase found
    de: str
    sujet: str
    le: str


def _plat(t: str) -> str:
    t = unicodedata.normalize("NFKD", t.casefold()).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def mots_entreprise(entreprise: str) -> list[str]:
    """The words that recognise the company: "BNP Paribas SA" → [bnp, paribas].

    Words of two letters are dropped ("de", "of"…), unless they are all the name
    has: EY, HP, 3M were never recognised. They are then matched as whole words
    only (`_nomme`), so "HP" is not found inside "PHP".
    """
    mots = [m for m in _plat(entreprise).split() if m not in _VIDES]
    longs = [m for m in mots if len(m) >= 3]
    return longs or [m for m in mots if len(m) == 2]


def _nomme(mots: list[str], texte_plat: str, domaine: str = "") -> bool:
    """All the company's words in the text, or glued together in the sender's domain.

    A short glued name must be a whole label of the domain ("ey" in ey.com), not a
    piece of one: "ey" sits inside "keyrecruit.com", which is not EY.
    """
    if not mots:
        return False
    tokens = f" {texte_plat} "
    if all(f" {m} " in tokens for m in mots):
        return True
    colle = "".join(mots)
    if len(colle) < 3:
        return colle in re.split(r"[^a-z0-9]+", domaine)
    return colle in re.sub(r"[^a-z0-9]", "", domaine)


def statut_suggere(c: Courriel) -> tuple[str, str] | None:
    """(status, phrase found) from the subject and the body; None if nothing clear."""
    texte = f"{c.sujet}\n{c.corps}"
    if fort := _trouves(_REFUS_FORT, texte):
        return REFUS, fort[0]
    faibles = _trouves(_REFUS_FAIBLE, texte)
    if len(faibles) >= 2:
        return REFUS, " … ".join(faibles[:2])
    if fort := _trouves(_ENTRETIEN_FORT, texte):
        return ENTRETIEN, fort[0]
    if accuse := _trouves(_ACCUSE, texte):
        return POSTULE, accuse[0]
    if faible := _trouves(_ENTRETIEN_FAIBLE, texte):
        return ENTRETIEN, faible[0]
    return None


def candidature(c: Courriel, suivi: Mapping[str, Mapping[str, Any]]) -> str | None:
    """The identity ("entreprise|poste") of the application the email is about."""
    de_plat = _plat(c.de)
    domaine = c.de.rpartition("@")[2].casefold().strip("> ")
    sujet_plat, corps_plat = _plat(c.sujet), _plat(c.corps)
    par_entreprise: dict[str, list[str]] = {}
    for oid in suivi:
        entreprise, _, poste = oid.partition("|")
        mots = mots_entreprise(entreprise)
        en_tete = _nomme(mots, f"{de_plat} {sujet_plat}", domaine)
        poste_cite = bool(poste) and _plat(poste) in f"{sujet_plat} {corps_plat}"
        if en_tete or (_nomme(mots, corps_plat) and poste_cite):
            par_entreprise.setdefault(" ".join(mots), []).append(oid)
    if len(par_entreprise) != 1:
        return None  # none, or several companies: we do not guess
    oids = next(iter(par_entreprise.values()))
    if len(oids) == 1:
        return oids[0]
    texte = f"{sujet_plat} {corps_plat}"
    cites = [o for o in oids if _plat(o.partition("|")[2]) in texte]
    return cites[0] if len(cites) == 1 else None


def propositions(
    courriels: Iterable[Courriel], suivi: Mapping[str, Mapping[str, Any]]
) -> list[Proposition]:
    """The statuses the emails suggest, one per application (the most advanced)."""
    meilleures: dict[str, Proposition] = {}
    for c in courriels:
        trouve = statut_suggere(c)
        if not trouve:
            continue
        oid = candidature(c, suivi)
        if not oid:
            continue
        actuel = str(suivi[oid].get("s") or "")
        statut, raison = trouve
        if actuel not in _RANG or _RANG[statut] <= _RANG[actuel]:
            continue  # unknown status ("mauvaise"…) or no progress
        p = Proposition(oid, actuel, statut, raison, c.de, c.sujet, c.le)
        deja = meilleures.get(oid)
        if not deja or (_RANG[statut], c.le) > (_RANG[deja.propose], deja.le):
            meilleures[oid] = p
    return sorted(meilleures.values(), key=lambda p: (p.le, p.oid), reverse=True)
