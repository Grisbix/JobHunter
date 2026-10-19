"""Langue de l'interface : français (source) ou anglais.

Partie de jobhunter.app (étape F5). Le texte français écrit dans le code reste la
référence ; en anglais, `t()` le remplace par sa traduction du catalogue
(`textes_en.EN`), et le laisse tel quel s'il n'y en a pas. Les boutons et étiquettes de
`theme` passent tous par `t()` : traduire un texte, c'est l'ajouter au catalogue, sans
toucher à l'endroit où il s'affiche.

Le choix vit dans `Scripts/_interface.json` (`{"langue": "en"}`), ou dans la variable
`JOBHUNTER_LANGUE`. Il vaut pour l'interface seulement : les statuts du suivi, les lettres
et le profil gardent leur langue.
"""

import json
import os
from pathlib import Path
from typing import overload

from jobhunter import racine as _racine
from jobhunter.app.textes_en import EN

LANGUES = ("fr", "en")
FICHIER = "_interface.json"


def _fichier() -> Path | None:
    try:
        return _racine.scripts() / FICHIER
    except RuntimeError:
        return None


def lire() -> str:
    """La langue choisie : "fr" ou "en" (français à défaut)."""
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
    """Enregistre la langue de l'interface ; elle vaut au prochain démarrage."""
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
    """Le texte dans la langue de l'interface ; tout autre objet, tel quel."""
    if LANGUE == "fr" or not isinstance(texte, str):
        return texte
    return EN.get(texte, texte)
