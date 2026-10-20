"""Interface language: French (source), English, German, Spanish.

Part of jobhunter.app (step F5). The French text written in the code stays the
reference; in another language, `t()` replaces it with its translation from that
language's catalogue (`textes_<code>.py`), then from the English one, and leaves it
in French if neither has it. The buttons and labels of `theme` all go through `t()`:
translating a text means adding it to the catalogues, without touching the place
where it is displayed.

A language is a module `jobhunter.app.textes_<code>` with `NOM` (its own name, as
shown in the language menu), `RELANCER` (the restart message, in that language) and
three catalogues: `TEXTES` (buttons, labels), `JOURNAL` (the app's log lines) and
`SORTIE` (the reports of the programs it launches). Adding a language = adding its
module and its code to `LANGUES`; the list is explicit because the installed
application (PyInstaller) cannot list a package's modules.

The choice lives in `Scripts/_interface.json` (`{"langue": "de"}`), or in the
`JOBHUNTER_LANGUE` variable. It applies to the interface only: the tracking statuses,
the letters and the profile keep their language.
"""

import importlib
import json
import os
import re
from pathlib import Path
from types import ModuleType
from typing import overload

from jobhunter import racine as _racine

LANGUES = ("fr", "en", "de", "es")
NOM_FR = "Français"
RELANCER_FR = "Relance JobHunter pour retrouver l'interface en français."
FICHIER = "_interface.json"


def module(code: str) -> ModuleType | None:
    """The catalogue module of a language; None for French, the source."""
    if code == "fr":
        return None
    return importlib.import_module(f"jobhunter.app.textes_{code}")


def noms() -> dict[str, str]:
    """{code: the language's own name}, in menu order."""
    return {c: NOM_FR if c == "fr" else str(module(c).NOM) for c in LANGUES}  # type: ignore[union-attr]  # module() is None only for "fr"


def message_relance(code: str) -> str:
    """The restart message, in the language just chosen."""
    m = module(code)
    return RELANCER_FR if m is None else str(m.RELANCER)


def _fichier() -> Path | None:
    try:
        return _racine.scripts() / FICHIER
    except RuntimeError:
        return None


def lire() -> str:
    """The chosen language, one of LANGUES (French by default)."""
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


def _catalogues(nom: str) -> list[dict[str, str]]:
    """The `nom` catalogues to look into, in order: the language's, then English."""
    vus = []
    for code in dict.fromkeys((LANGUE, "en")):
        m = module(code)
        if m is not None:
            vus.append(getattr(m, nom))
    return vus


def _textes() -> list[dict[str, str]]:
    if _CACHE.get("langue") != LANGUE:
        _CACHE.clear()
        _CACHE["langue"] = LANGUE
    if "textes" not in _CACHE:
        _CACHE["textes"] = _catalogues("TEXTES")
    return _CACHE["textes"]  # type: ignore[return-value]  # filled just above


# Built on first use and rebuilt if LANGUE changes (the tests switch it).
_CACHE: dict[str, object] = {}


@overload
def t(texte: str) -> str: ...
@overload
def t(texte: object) -> object: ...
def t(texte: object) -> object:
    """The text in the interface language; any other object, as is."""
    if LANGUE == "fr" or not isinstance(texte, str):
        return texte
    for cat in _textes():
        if texte in cat:
            return cat[texte]
    return texte


def _modele(cle: str) -> "re.Pattern[str]":
    """« ↶ annulé ({a} offre(s)). » → motif qui capture chaque `{x}`."""
    morceaux = re.split(r"\{(\w+)\}", cle)
    motif = "".join(re.escape(m) if i % 2 == 0 else f"(?P<{m}>.*?)" for i, m in enumerate(morceaux))
    return re.compile(motif)


def _lignes() -> tuple[dict[str, str], list[tuple["re.Pattern[str]", str]]]:
    """The log lines (the app's messages, then the programs' output) and their templates."""
    _textes()  # resets the cache if the language changed
    if "lignes" not in _CACHE:
        lignes: dict[str, str] = {}
        # English first, then the language: the language's own lines win.
        for nom in ("JOURNAL", "SORTIE"):
            for cat in reversed(_catalogues(nom)):
                lignes.update(cat)
        _CACHE["lignes"] = (lignes, [(_modele(k), v) for k, v in lignes.items() if "{" in k])
    return _CACHE["lignes"]  # type: ignore[return-value]  # filled just above


def _ligne(texte: str) -> str:
    """A log line (without edge spaces) in the interface language, or as is."""
    lignes, modeles = _lignes()
    if texte in lignes:
        return lignes[texte]
    for motif, cible in modeles:
        m = motif.fullmatch(texte)
        if m:
            return cible.format(**m.groupdict())
    return texte


def journal(texte: str) -> str:
    """The app's log text, line by line, in the interface language.

    Each line known to a `JOURNAL` catalogue (without its edge spaces) is translated,
    including those carrying a number or a name (`{a}` templates), and the summaries
    of the launched programs (`SORTIE`); the other lines stay as they are.
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
