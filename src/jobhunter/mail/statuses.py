"""Suggest an application status from an email. Pure functions, no network.

Part of jobhunter.mail. Two questions per email:

1. **Which application?** The tracked one whose company appears in the sender
   (display name or domain) or in the subject. A company named only in the body
   is enough only if the job title is there too: newsletters mention many
   companies. Two applications at the same company: the one whose title appears,
   otherwise none (we do not guess).
2. **Which status?** Rejection, interview or acknowledgement, from phrases in
   French, English and German. Rejection comes first: a rejection letter often
   thanks you for applying.

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

_MOTIFS = (
    (
        REFUS,
        r"ne (?:pas |plus )?(?:pouvons|pourrons) (?:pas )?donner (?:une )?suite|pas (?:été )?retenue?"
        r"|ne correspond(?:ait)? pas|regrett(?:ons|ons de vous informer)|avons (?:décidé|choisi) de "
        r"(?:poursuivre|retenir) (?:avec )?d.autres|d.autres candidat|issue défavorable"
        r"|unfortunately|not (?:to )?(?:move|moving) forward|move forward with other"
        r"|not been successful|unsuccessful|will not be (?:progressing|proceeding)|regret to inform"
        r"|not (?:been )?selected|decided to pursue other|other candidates"
        r"|leider|absage|nicht (?:weiter )?berücksichtig|anderen? (?:Bewerber|Kandidat)",
    ),
    (
        ENTRETIEN,
        r"entretien|échange (?:téléphonique|visio)|vous rencontrer|vos disponibilités"
        r"|prochaine étape du processus|vous convier"
        r"|interview|schedule (?:a|an) (?:call|meeting|chat)|your availability|next step"
        r"|invite you to|phone screen"
        r"|vorstellungsgespräch|kennenlernen|terminvorschlag",
    ),
    (
        POSTULE,
        r"bien reçu votre candidature|accusé de réception|avons bien reçu|merci (?:pour|de) votre "
        r"candidature|confirmons la réception"
        r"|thank you for (?:applying|your application)|(?:we have |we've )?received your application"
        r"|application (?:has been )?received|thanks for applying"
        r"|eingang ihrer bewerbung|vielen dank für ihre bewerbung|bewerbung erhalten",
    ),
)
_RX = tuple((statut, re.compile(m, re.I)) for statut, m in _MOTIFS)

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
    """The words that recognise the company: "BNP Paribas SA" → [bnp, paribas]."""
    return [m for m in _plat(entreprise).split() if m not in _VIDES and len(m) >= 3]


def _nomme(mots: list[str], texte_plat: str, colle: str = "") -> bool:
    """All the company's words in the text (or glued together in a domain)."""
    if not mots:
        return False
    tokens = f" {texte_plat} "
    if all(f" {m} " in tokens for m in mots):
        return True
    return bool(colle) and "".join(mots) in colle


def statut_suggere(c: Courriel) -> tuple[str, str] | None:
    """(status, phrase found) from the subject and the body; None if nothing clear."""
    texte = f"{c.sujet}\n{c.corps}"
    for statut, rx in _RX:
        m = rx.search(texte)
        if m:
            return statut, m.group(0)
    return None


def candidature(c: Courriel, suivi: Mapping[str, Mapping[str, Any]]) -> str | None:
    """The identity ("entreprise|poste") of the application the email is about."""
    de_plat = _plat(c.de)
    domaine = re.sub(r"[^a-z0-9]", "", c.de.rpartition("@")[2].casefold())
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
