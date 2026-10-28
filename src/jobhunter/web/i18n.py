"""The web window in the interface language (Réglages → Langue).

The page is written in French, like the desktop's code. app.js translates what it
shows — text, placeholders, tooltips, the output of the programs it runs — with the
catalogue built here, sent once at start (`Api.textes`):

- `jobhunter.web.texts`: the texts of this window, fr → (en, de, es);
- `jobhunter.locales.<code>`: the desktop's catalogues, for the texts both windows
  share (statuses, tools, collection states) and the programs' output (SORTIE,
  JOURNAL), with English as the fallback, as on the desktop.

A key with `{x}` holes is a template: app.js matches it against the whole text and
puts the captured values back, themselves translated when they are known texts.

The choice is the desktop's: `langue` in the main folder's `_interface.json`, or the
JOBHUNTER_LANGUE variable. It applies to the interface only: letters, messages and the
profile keep their own language.
"""

from __future__ import annotations

import importlib
import json
import os
from typing import Any

LANGUES = ("fr", "en", "de", "es")
COLONNE = {"en": 0, "de": 1, "es": 2}  # position in jobhunter.web.texts.TEXTES' tuples


def langue() -> str:
    """The chosen interface language, the system's by default (jobhunter.locales.systeme)."""
    env = os.environ.get("JOBHUNTER_LANGUE", "").lower()
    if env in LANGUES:
        return env
    from jobhunter.web.api import _fichier_reglages

    f = _fichier_reglages()
    try:
        v = json.loads(f.read_text(encoding="utf-8")).get("langue") if f else None
    except (OSError, ValueError, AttributeError):
        v = None
    if v in LANGUES:
        return str(v)
    from jobhunter.locales import systeme

    return systeme()


def _bureau(code: str) -> list[dict[str, str]]:
    """The desktop's catalogues for `code`, lowest priority first: English, then it."""
    vus: list[dict[str, str]] = []
    for c in dict.fromkeys(("en", code)):
        m = importlib.import_module(f"jobhunter.locales.{c}")
        for nom in ("SORTIE", "JOURNAL", "TEXTES"):
            vus.append(getattr(m, nom, {}))
    return vus


def catalogue(code: str) -> dict[str, Any]:
    """{"langue", "textes": {fr: text}, "modeles": [[fr, text], ...], "fit": [[fr, text], ...]}.

    "fit" holds the fit explanation's templates (scoring.fit.expliquer); French, the
    page's own language, gets an empty catalogue.
    """
    if code not in COLONNE:
        return {"langue": "fr", "textes": {}, "modeles": [], "fit": []}
    from jobhunter.web.texts import TEXTES

    tout: dict[str, str] = {}
    for cat in _bureau(code):
        tout.update(cat)
    # This window's own texts win; English fills a hole of German or Spanish.
    for fr, trad in TEXTES.items():
        tout[fr] = trad[COLONNE[code]] or trad[0]
    textes = {k: v for k, v in tout.items() if "{" not in k and v != k}
    modeles = [[k, v] for k, v in tout.items() if "{" in k]
    # The fit explanation's templates are too general for the rest: kept apart.
    fit: dict[str, str] = {}
    for c in dict.fromkeys(("en", code)):
        fit.update(importlib.import_module(f"jobhunter.locales.{c}").FIT)
    return {
        "langue": code,
        "textes": textes,
        "modeles": modeles,
        "fit": [[k, v] for k, v in fit.items()],
    }
