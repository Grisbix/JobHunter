"""The search, edited in the application: keywords, titles kept, titles set aside.

Three sections of the active profile's `profile.json`, the ones a user changes most:

- `collecte.mots_cles`: the searches run on LinkedIn, Welcome to the Jungle…;
- `filtre_titre.metier`: a title must contain one of these to be collected;
- `filtre_titre.exclus`: a title containing one of these is set aside.

An entry is a word or phrase (found anywhere in the title, case ignored) or, starting
with `re:`, a regular expression — the profile's own syntax, unchanged. `valider()` says
what is wrong before anything is written; `ecrire()` keeps the previous profile as `.bak`
and writes atomically, keeping the file's indentation and every other section as is.
"""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Reglages:
    """The editable part of the search."""

    mots_cles: list[str] = field(default_factory=list)
    garder: list[str] = field(default_factory=list)
    ecarter: list[str] = field(default_factory=list)


def _liste(v: object) -> list[str]:
    if isinstance(v, str):
        v = [v]
    return [str(x).strip() for x in (v or []) if str(x).strip()] if isinstance(v, list) else []


def lire(profil: dict[str, Any]) -> Reglages:
    """The search settings of a loaded profile."""
    ft = profil.get("filtre_titre") or {}
    return Reglages(
        mots_cles=_liste((profil.get("collecte") or {}).get("mots_cles")),
        garder=_liste(ft.get("metier")),
        ecarter=_liste(ft.get("exclus")),
    )


def depuis_texte(texte: str) -> list[str]:
    """One entry per line, empty lines and duplicates removed, order kept."""
    vus: dict[str, None] = {}
    for ligne in texte.splitlines():
        ligne = ligne.strip()
        if ligne and ligne.lower() not in {v.lower() for v in vus}:
            vus[ligne] = None
    return list(vus)


def valider(r: Reglages) -> list[str]:
    """What prevents saving, in plain words; [] if nothing."""
    erreurs = []
    if not r.mots_cles:
        erreurs.append("au moins un mot-clé de recherche")
    if not r.garder:
        erreurs.append("au moins un mot d'intitulé à garder (sinon aucune offre ne passe)")
    for nom, liste in (("à garder", r.garder), ("à écarter", r.ecarter)):
        for e in liste:
            if e.startswith("re:"):
                try:
                    re.compile(e[3:], re.I)
                except re.error as x:
                    erreurs.append(f"intitulés {nom} : motif invalide « {e[:40]} » ({x.msg})")
    return erreurs


def appliquer(profil: dict[str, Any], r: Reglages) -> dict[str, Any]:
    """A copy of `profil` with the settings in; every other key and its order kept."""
    nouveau = json.loads(json.dumps(profil))
    nouveau.setdefault("collecte", {})["mots_cles"] = list(r.mots_cles)
    ft = nouveau.setdefault("filtre_titre", {})
    ft["metier"] = list(r.garder)
    ft["exclus"] = list(r.ecarter)
    return nouveau


def _indentation(texte: str) -> int:
    for ligne in texte.splitlines()[1:]:
        if ligne.strip():
            return len(ligne) - len(ligne.lstrip(" "))
    return 1


def ecrire(fichier: Path, profil: dict[str, Any]) -> Path:
    """Writes the profile: the previous one kept as `<name>.bak`, atomic replace.

    Returns:
        The backup's path.
    """
    ancien = fichier.read_text(encoding="utf-8")
    sauvegarde = fichier.with_name(fichier.name + ".bak")
    sauvegarde.write_text(ancien, encoding="utf-8")
    tmp = fichier.with_name(fichier.name + ".tmp")
    tmp.write_text(
        json.dumps(profil, ensure_ascii=False, indent=_indentation(ancien)) + "\n",
        encoding="utf-8",
    )
    tmp.replace(fichier)
    return sauvegarde
