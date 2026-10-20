"""Interface language: French (source) or English.

Part of jobhunter.app (step F5). The French text written in the code stays the
reference; in English, `t()` replaces it with its translation from the catalogue
(`textes_en.EN`), and leaves it as is if there is none. The buttons and labels of
`theme` all go through `t()`: translating a text means adding it to the catalogue,
without touching the place where it is displayed.

The choice lives in `Scripts/_interface.json` (`{"langue": "en"}`), or in the
`JOBHUNTER_LANGUE` variable. It applies to the interface only: the tracking statuses,
the letters and the profile keep their language.
"""

import json
import os
import re
from pathlib import Path
from typing import overload

from jobhunter import racine as _racine
from jobhunter.app.textes_en import EN, JOURNAL_EN, SORTIE_EN

LANGUES = ("fr", "en")
FICHIER = "_interface.json"


def _fichier() -> Path | None:
    try:
        return _racine.scripts() / FICHIER
    except RuntimeError:
        return None


def lire() -> str:
    """The chosen language: "fr" or "en" (French by default)."""
    env = os.environ.get("JOBHUNTER_LANGUE", "").lower()
    if env in LANGUES:
        return env
    f = _fichier()
    try:
        v = json.loads(f.read_text(encoding="utf-8")).get("langue") if f else None
    except (OSError, ValueError, AttributeError):
        v = None
    return v if v in LANGUES else "fr"


def choisir(langue: str) -> None:
    """Saves the interface language; it applies at the next start."""
    if langue not in LANGUES:
        raise ValueError(langue)
    f = _fichier()
    if f is None:
        return
    f.write_text(json.dumps({"langue": langue}), encoding="utf-8")


LANGUE = lire()


@overload
def t(texte: str) -> str: ...
@overload
def t(texte: object) -> object: ...
def t(texte: object) -> object:
    """The text in the interface language; any other object, as is."""
    if LANGUE == "fr" or not isinstance(texte, str):
        return texte
    return EN.get(texte, texte)


def _modele(cle: str) -> "re.Pattern[str]":
    """« ↶ annulé ({a} offre(s)). » → motif qui capture chaque `{x}`."""
    morceaux = re.split(r"\{(\w+)\}", cle)
    motif = "".join(re.escape(m) if i % 2 == 0 else f"(?P<{m}>.*?)" for i, m in enumerate(morceaux))
    return re.compile(motif)


# The app's messages, then the output of the programs it launches.
_LIGNES = {**JOURNAL_EN, **SORTIE_EN}
_MODELES = [(_modele(k), v) for k, v in _LIGNES.items() if "{" in k]


def _ligne(texte: str) -> str:
    """A log line (without edge spaces) in English, or as is."""
    if texte in _LIGNES:
        return _LIGNES[texte]
    for motif, cible in _MODELES:
        m = motif.fullmatch(texte)
        if m:
            return cible.format(**m.groupdict())
    return texte


def journal(texte: str) -> str:
    """The app's log text, line by line, in the interface language.

    Each line known to `JOURNAL_EN` (without its edge spaces) is translated,
    including those carrying a number or a name (`{a}` templates), and the summaries
    of the launched programs (`SORTIE_EN`); the other lines stay as they are.
    """
    if LANGUE == "fr":
        return texte
    sortie = []
    for ligne in texte.splitlines(keepends=True):
        corps = ligne.rstrip("\r\n")
        fin = ligne[len(corps) :]
        coeur = corps.strip()
        if coeur:
            debut = corps[: len(corps) - len(corps.lstrip())]
            corps = debut + _ligne(coeur)
        sortie.append(corps + fin)
    return "".join(sortie)
