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
import re
from pathlib import Path
from typing import overload

from jobhunter import racine as _racine
from jobhunter.app.textes_en import EN, JOURNAL_EN

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


def _modele(cle: str) -> "re.Pattern[str]":
    """« ↶ annulé ({a} offre(s)). » → motif qui capture chaque `{x}`."""
    morceaux = re.split(r"\{(\w+)\}", cle)
    motif = "".join(re.escape(m) if i % 2 == 0 else f"(?P<{m}>.*?)" for i, m in enumerate(morceaux))
    return re.compile(motif)


_MODELES = [(_modele(k), v) for k, v in JOURNAL_EN.items() if "{" in k]


def _ligne(texte: str) -> str:
    """Une ligne du journal (sans espaces de bord) en anglais, ou telle quelle."""
    if texte in JOURNAL_EN:
        return JOURNAL_EN[texte]
    for motif, cible in _MODELES:
        m = motif.fullmatch(texte)
        if m:
            return cible.format(**m.groupdict())
    return texte


def journal(texte: str) -> str:
    """Le texte du journal de l'app, ligne à ligne, dans la langue de l'interface.

    Chaque ligne connue de `JOURNAL_EN` (sans ses espaces de bord) est traduite, y
    compris celles qui portent un nombre ou un nom (modèles à `{a}`) ; les autres, dont
    la sortie des programmes lancés, restent telles quelles.
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
