"""Proposer un statut de candidature à partir d'un courriel. Fonctions pures, sans réseau.

Partie de jobhunter.courriels. Deux questions par courriel :

1. **Quelle candidature ?** Celle du suivi dont l'entreprise apparaît dans l'expéditeur
   (nom affiché ou domaine) ou dans le sujet. Une entreprise nommée seulement dans le
   corps ne suffit que si l'intitulé du poste y est aussi : les lettres d'information
   citent beaucoup d'entreprises. Deux candidatures dans la même entreprise : celle dont
   l'intitulé apparaît, sinon aucune (on ne devine pas).
2. **Quel statut ?** Refus, entretien ou accusé de réception, d'après des formules en
   français, anglais et allemand. Le refus passe en premier : une lettre de refus
   remercie souvent pour la candidature.

Un statut n'avance que vers l'aval : un accusé de réception ne fait passer « à postuler »
qu'à « postulé » ; un entretien ne revient jamais à « postulé » ; rien ne remplace un
refus. Le résultat est une liste de `Proposition`, que l'utilisateur valide une à une.
"""

import re
import unicodedata
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from jobhunter.courriels.lecture import Courriel

REFUS, ENTRETIEN, POSTULE = "refus", "entretien", "postulé"

# Rang de chaque statut dans la vie d'une candidature : on ne propose que d'avancer.
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

# Mots qui ne désignent pas une entreprise : formes juridiques, « groupe », pays…
_VIDES = {
    "sa", "sas", "sasu", "sarl", "se", "ag", "gmbh", "kg", "ltd", "llc", "inc", "plc", "bv",
    "nv", "spa", "group", "groupe", "france", "paris", "europe", "international", "the",
    "and", "et", "de", "des", "du", "la", "le", "les", "company", "co", "holding", "partners",
}  # fmt: skip


@dataclass(frozen=True)
class Proposition:
    """Un statut suggéré par un courriel, à valider."""

    oid: str  # « entreprise|poste »
    actuel: str
    propose: str
    raison: str  # la formule trouvée
    de: str
    sujet: str
    le: str


def _plat(t: str) -> str:
    t = unicodedata.normalize("NFKD", t.casefold()).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def mots_entreprise(entreprise: str) -> list[str]:
    """Les mots qui reconnaissent l'entreprise : « BNP Paribas SA » → [bnp, paribas]."""
    return [m for m in _plat(entreprise).split() if m not in _VIDES and len(m) >= 3]


def _nomme(mots: list[str], texte_plat: str, colle: str = "") -> bool:
    """Tous les mots de l'entreprise dans le texte (ou colles dans un domaine)."""
    if not mots:
        return False
    tokens = f" {texte_plat} "
    if all(f" {m} " in tokens for m in mots):
        return True
    return bool(colle) and "".join(mots) in colle


def statut_suggere(c: Courriel) -> tuple[str, str] | None:
    """(statut, formule trouvée) d'après le sujet et le corps ; None si rien de clair."""
    texte = f"{c.sujet}\n{c.corps}"
    for statut, rx in _RX:
        m = rx.search(texte)
        if m:
            return statut, m.group(0)
    return None


def candidature(c: Courriel, suivi: Mapping[str, Mapping[str, Any]]) -> str | None:
    """L'identité (« entreprise|poste ») de la candidature que le courriel concerne."""
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
        return None  # aucune, ou plusieurs entreprises : on ne devine pas
    oids = next(iter(par_entreprise.values()))
    if len(oids) == 1:
        return oids[0]
    texte = f"{sujet_plat} {corps_plat}"
    cites = [o for o in oids if _plat(o.partition("|")[2]) in texte]
    return cites[0] if len(cites) == 1 else None


def propositions(
    courriels: Iterable[Courriel], suivi: Mapping[str, Mapping[str, Any]]
) -> list[Proposition]:
    """Les statuts que les courriels suggèrent, un par candidature (le plus avancé)."""
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
            continue  # statut inconnu (« mauvaise »…) ou pas d'avancée
        p = Proposition(oid, actuel, statut, raison, c.de, c.sujet, c.le)
        deja = meilleures.get(oid)
        if not deja or (_RANG[statut], c.le) > (_RANG[deja.propose], deja.le):
            meilleures[oid] = p
    return sorted(meilleures.values(), key=lambda p: (p.le, p.oid), reverse=True)
