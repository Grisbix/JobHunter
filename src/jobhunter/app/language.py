"""Interface language: French (source), English, German, Spanish.

Part of jobhunter.app (step F5). The French text written in the code stays the
reference; in another language, `t()` replaces it with its translation from that
language's catalogue (`texts_<code>.py`), then from the English one, and leaves it
in French if neither has it. The buttons and labels of `theme` all go through `t()`:
translating a text means adding it to the catalogues, without touching the place
where it is displayed.

A language is a module `jobhunter.app.texts_<code>` with `NOM` (its own name, as
shown in the language menu), `RELANCER` (the restart message, in that language) and
three catalogues: `TEXTES` (buttons, labels), `JOURNAL` (the app's log lines) and
`SORTIE` (the reports of the programs it launches). Adding a language = adding its
module and its code to `LANGUES`; the list is explicit because the installed
application (PyInstaller) cannot list a package's modules.

The choice lives in the main folder's `data/_interface.json` (`{"langue": "de"}`), the
same for every profile, or in the `JOBHUNTER_LANGUE` variable. It applies to the
interface only: the letters and the profile keep their language; the tracking statuses
and contract types are stored in French and translated where they are shown.
"""

import importlib
import json
import os
import re
from pathlib import Path
from types import ModuleType
from typing import overload

from jobhunter import root as _racine

LANGUES = ("fr", "en", "de", "es")
NOM_FR = "Français"
RELANCER_FR = "Relance JobHunter pour retrouver l'interface en français."
FICHIER = "_interface.json"  # 2.x name: see root.nom()


def module(code: str) -> ModuleType | None:
    """The catalogue module of a language; None for French, the source."""
    if code == "fr":
        return None
    return importlib.import_module(f"jobhunter.app.texts_{code}")


def noms() -> dict[str, str]:
    """{code: the language's own name}, in menu order."""
    return {c: NOM_FR if c == "fr" else str(module(c).NOM) for c in LANGUES}  # type: ignore[union-attr]  # module() is None only for "fr"


def message_relance(code: str) -> str:
    """The restart message, in the language just chosen."""
    m = module(code)
    return RELANCER_FR if m is None else str(m.RELANCER)


def _fichier() -> Path | None:
    """The choice, in the MAIN folder's data: one language for every profile (3.19).

    It lived in each profile's data folder: opening another profile switched the
    interface back to French.
    """
    try:
        from jobhunter import profiles as _profils

        p = _profils.principale()
        return p / _racine.nom("Scripts", p) / FICHIER
    except RuntimeError:
        return None


def _ancien_fichier() -> Path | None:
    """Where the choice lived before 3.19: the open profile's data folder."""
    try:
        return _racine.scripts() / FICHIER
    except RuntimeError:
        return None


def lire() -> str:
    """The chosen language, one of LANGUES (French by default)."""
    env = os.environ.get("JOBHUNTER_LANGUE", "").lower()
    if env in LANGUES:
        return env
    for f in (_fichier(), _ancien_fichier()):
        try:
            v = json.loads(f.read_text(encoding="utf-8")).get("langue") if f else None
        except (OSError, ValueError, AttributeError):
            v = None
        if v in LANGUES:
            return str(v)
    return "fr"


def choisir(langue: str) -> None:
    """Saves the interface language; it applies at the next start."""
    if langue not in LANGUES:
        raise ValueError(langue)
    f = _fichier()
    if f is None:
        return
    f.parent.mkdir(parents=True, exist_ok=True)
    # The file holds other settings too (the web interface's): keep them.
    try:
        tout = json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        tout = {}
    if not isinstance(tout, dict):
        tout = {}
    tout["langue"] = langue
    f.write_text(json.dumps(tout, ensure_ascii=False), encoding="utf-8")


LANGUE = lire()


def _catalogues(nom: str) -> list[dict[str, str]]:
    """The `nom` catalogues to look into, in order: the language's, then English."""
    vus = []
    for code in dict.fromkeys((LANGUE, "en")):
        m = module(code)
        if m is not None:
            vus.append(getattr(m, nom, {}))
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


_JOURNAL = ("JOURNAL", "SORTIE")


def _lignes(
    noms: tuple[str, ...] = _JOURNAL,
) -> tuple[dict[str, str], list[tuple["re.Pattern[str]", str]]]:
    """The lines of the `noms` catalogues (by default the app's messages, then the
    programs' output) and their templates."""
    _textes()  # resets the cache if the language changed
    cle = "lignes:" + ",".join(noms)
    if cle not in _CACHE:
        lignes: dict[str, str] = {}
        # English first, then the language: the language's own lines win.
        for nom in noms:
            for cat in reversed(_catalogues(nom)):
                lignes.update(cat)
        _CACHE[cle] = (lignes, [(_modele(k), v) for k, v in lignes.items() if "{" in k])
    return _CACHE[cle]  # type: ignore[return-value]  # filled just above


def explication(texte: str) -> str:
    """A line of the fit explanation (scoring.fit.expliquer) in the interface language.

    Its own catalogue (`FIT`): its templates are too general for the log's lines.
    The skills and words found stay as the profile names them.
    """
    if LANGUE == "fr":
        return texte
    return _ligne(texte, ("FIT",))


def _ligne(texte: str, noms: tuple[str, ...] = _JOURNAL) -> str:
    """A log line (without edge spaces) in the interface language, or as is."""
    lignes, modeles = _lignes(noms)
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
