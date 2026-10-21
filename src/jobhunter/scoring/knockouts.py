"""Knock-out conditions a posting states: what makes an application void whatever the fit.

The fit measures how well the job matches the profile; it cannot see that the posting
requires a driving licence, a nationality, the right to work in a country, or a
security clearance. Such an offer still got a CV and a letter. These conditions are
FLAGGED (« Signal » column, the offer's card), never used to remove or re-score: a
regex can misread, and the user decides.

The experience asked for and the languages required are not here: the fit already
caps them (scoring.fit), and the sorting removes the first above `EXP_MAX`.

Profile, section `eliminatoires` (all optional):

    "eliminatoires": {
        "permis": true,                  # I hold a driving licence: no flag for it
        "habilitation": false,           # no security clearance
        "droit_de_travail": ["FR", "EU"],# where I may work without a visa
        "ignorer": ["visa"]              # labels never to flag
    }

`droit_de_travail` zones: FR, EU, UK, US, CA, AU, CH; "visa" is the posting saying
it will not sponsor one. Without the section, everything found is flagged.
Each rule skips a mention softened by "a plus", "souhaité", "preferred"...
"""

import re
import unicodedata
from collections.abc import Mapping
from typing import Any

from jobhunter import profile as _P

# A requirement softened nearby is not a knock-out ("permis B apprécié").
_RX_MOU = re.compile(
    r"\b(?:souhait\w*|apprecie\w*|un plus|serait un plus|atout|idealement|de preference|"
    r"a plus|is a plus|preferred|desirable|nice to have|an advantage|ideally|"
    r"may\s+be\s+required|if\s+needed|wunschenswert|von vorteil|idealerweise)\b"
)

_PERMIS = [
    r"\bpermis\s+(?:de\s+conduire|b)\b[^.;\n]{0,40}?\b(?:obligatoire|exige|requis|indispensable|"
    r"necessaire|imperatif)",
    r"\btitulaire\s+du\s+permis\s+(?:b|de\s+conduire)\b",
    r"\bvehicule(?:\s+personnel)?\s+(?:obligatoire|exige|indispensable)",
    r"\bdriv(?:er'?s|ing)\s+licen[cs]e\b[^.;\n]{0,40}?\b(?:required|mandatory|essential|"
    r"is\s+a\s+must)",
    r"\bmust\s+(?:hold|have|possess)\s+a\s+(?:valid\s+|full\s+|clean\s+)*"
    r"driv(?:er'?s|ing)\s+licen[cs]e",
    r"\bfuhrerschein\b[^.;\n]{0,40}?\b(?:erforderlich|zwingend|vorausgesetzt|notwendig|pflicht)",
]

_PAYS = {
    "us": "US",
    "u.s.": "US",
    "united states": "US",
    "usa": "US",
    "uk": "UK",
    "united kingdom": "UK",
    "british": "UK",
    "canada": "CA",
    "canadian": "CA",
    "australia": "AU",
    "australian": "AU",
    "switzerland": "CH",
    "swiss": "CH",
    "eu": "EU",
    "european union": "EU",
}
_NOMS_PAYS = r"u\.s\.|us|usa|united states|uk|united kingdom|british|canada|canadian|australia|australian|switzerland|swiss|eu|european union"

# (pattern, zone or None = the zone is the captured country)
_DROIT: list[tuple[str, str | None]] = [
    (
        r"\bnationalite\s+francaise\b[^.;\n]{0,30}?\b(?:obligatoire|exigee|requise|indispensable)",
        "FR",
    ),
    (
        r"\b(?:etre\s+de\s+)?nationalite\s+(?:europeenne|d'un\s+(?:etat|pays)\s+(?:membre\s+)?de\s+l'(?:union\s+europeenne|ue))",
        "EU",
    ),
    (r"\bressortissant\w*\s+(?:d'un\s+etat\s+membre\s+)?de\s+l'(?:union\s+europeenne|ue)\b", "EU"),
    (
        rf"\b({_NOMS_PAYS})\s+citizen(?:ship)?\b[^.;\n]{{0,25}}?\b(?:required|only|is\s+a\s+must|mandatory)",
        None,
    ),
    (rf"\bmust\s+(?:be|hold)\s+(?:a\s+)?({_NOMS_PAYS})\s+(?:citizen|national|passport)", None),
    (
        rf"\b(?:must|need\s+to|required\s+to)\s+(?:be\s+)?(?:legally\s+)?(?:authori[sz]ed|eligible|"
        rf"entitled|permitted)\s+to\s+work\s+in\s+(?:the\s+)?({_NOMS_PAYS})\b",
        None,
    ),
    (rf"\b(?:full\s+|existing\s+)?right\s+to\s+work\s+in\s+(?:the\s+)?({_NOMS_PAYS})\b", None),
    (
        r"\b(?:no|not\s+(?:able\s+to\s+)?(?:offer|provide|sponsor)|unable\s+to\s+(?:offer|provide|sponsor)|"
        r"cannot\s+(?:offer|provide|sponsor)|will\s+not\s+(?:offer|provide|sponsor)|does\s+not\s+(?:offer|provide|sponsor)"
        r"|without(?:\s+the\s+need\s+for)?)\s+(?:visa\s+|work\s+permit\s+)?(?:sponsorship|sponsor)\b",
        "visa",
    ),
    (r"\bkein\w*\s+(?:visum|arbeitserlaubnis)\b", "visa"),
]

_HABILITATION = [
    r"\bhabilitation\s+(?:secret|confidentiel|tres\s+secret)[\s-]+defense\b",
    r"\b(?:etre\s+)?habilitable\b",
    r"\beligib\w+\s+a\s+(?:une|l')\s*habilitation\b",
    r"\b(?:active\s+|current\s+)?(?:security|sc|dv|top\s+secret|ts/sci|secret|baseline)\s+clearance\b",
    r"\beligib\w+\s+(?:for|to\s+obtain)\s+(?:a\s+)?(?:security\s+)?clearance\b",
    r"\bsicherheitsuberprufung\w*\b",
]

# Where an EU national works without a visa (EU, EEA, Switzerland), in pays_lieu's names.
LIBRE_CIRCULATION = frozenset(
    "France Allemagne Autriche Belgique Bulgarie Chypre Croatie Danemark Espagne Estonie "
    "Finlande Grèce Hongrie Irlande Italie Lettonie Lituanie Luxembourg Malte Pays-Bas "
    "Pologne Portugal Roumanie Slovaquie Slovénie Suède Tchéquie Norvège Islande "
    "Liechtenstein Suisse".split()
)

_RX_PERMIS = [re.compile(p) for p in _PERMIS]
_RX_DROIT = [(re.compile(p), z) for p, z in _DROIT]
_RX_HABILITATION = [re.compile(p) for p in _HABILITATION]


def _plat(texte: str) -> str:
    """Accents off, lower case, ASCII apostrophes, single spaces."""
    t = (texte or "").replace("’", "'").replace("‘", "'")
    t = unicodedata.normalize("NFKD", t.casefold())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"[ \t\r\f\v]+", " ", t)


def _ferme(t: str, m: re.Match[str]) -> bool:
    """A real requirement: no softening word in the match or just around it."""
    fenetre = t[max(0, m.start() - 30) : m.end() + 40]
    return not _RX_MOU.search(fenetre)


def _reglages(profil: Mapping[str, Any] | None) -> dict[str, Any]:
    if profil is not None:
        return dict(profil)
    r = _P.get("eliminatoires", {}) or {}
    return dict(r) if isinstance(r, Mapping) else {}


def trouver(
    texte: str, profil: Mapping[str, Any] | None = None, pays: str | None = None
) -> list[str]:
    """The knock-out conditions of a posting that the profile does not meet.

    Args:
        texte: the description.
        profil: the `eliminatoires` section; None = the profile's.
        pays: the offer's country (scoring.zones.pays_lieu): "no visa sponsorship" is
            moot where an EU national needs no visa, for a profile with EU or FR.

    Returns:
        Short labels, without duplicates: "permis exigé", "nationalité FR",
        "droit de travail UK", "pas de visa", "habilitation".
    """
    t = _plat(texte)
    if not t:
        return []
    r = _reglages(profil)
    ignorer = {str(x).casefold() for x in r.get("ignorer") or []}
    zones = {str(x).upper() for x in r.get("droit_de_travail") or []}
    out: list[str] = []

    def ajouter(lib: str, cle: str) -> None:
        if cle.casefold() not in ignorer and lib not in out:
            out.append(lib)

    if not r.get("permis") and any(_ferme(t, m) for rx in _RX_PERMIS for m in rx.finditer(t)):
        ajouter("permis exigé", "permis")
    for rx, zone in _RX_DROIT:
        for m in rx.finditer(t):
            if not _ferme(t, m):
                continue
            z = zone or _PAYS.get(m.group(1).strip(), m.group(1).upper())
            if z == "visa":
                libre = zones & {"EU", "FR"} and pays in LIBRE_CIRCULATION
                if "VISA" not in zones and not libre:
                    ajouter("pas de visa", "visa")
                continue
            # An EU national may work in France: FR is met by FR, EU by EU or FR.
            if z in zones or (z == "EU" and "FR" in zones):
                continue
            ajouter("nationalité FR" if zone == "FR" else f"droit de travail {z}", z)
    if not r.get("habilitation") and any(
        _ferme(t, m) for rx in _RX_HABILITATION for m in rx.finditer(t)
    ):
        ajouter("habilitation", "habilitation")
    return out
