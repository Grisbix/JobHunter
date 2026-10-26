r"""Cleanup recipes: rules that normalise the queue's company names, places and contracts.

"PWC France", "PricewaterhouseCoopers" and "PwC" are one employer; "Paris 8e" and "Paris"
one city. A recipe says it once, and is replayed as often as needed:

    {"champ": "entreprise", "de": "PricewaterhouseCoopers", "vers": "PwC"}
    {"champ": "entreprise", "de": "re:\\s+(SAS|SA|GmbH)$", "vers": ""}
    {"champ": "localisation", "de": "re:^Paris \\d+e$", "vers": "Paris"}

`de` is a value (case and spaces ignored: the whole field must match) or, after `re:`, a
regular expression replaced wherever it matches. Only three fields can be changed
(CHAMPS). No code is ever run: a recipe is data, checked by `valider()` before use.

What makes it safe:

- `apercu()` lists every change before anything is written; `jobhunter recipes` without
  `--appliquer` only shows them;
- replaying the same recipes changes nothing the second time (each result is final);
- the company name is part of an offer's identity (`entreprise|poste`), which the
  applications file uses: an offer you applied to is never renamed, and a rename that
  would collide with another offer of the queue is skipped. Both are reported.
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

CHAMPS = ("entreprise", "localisation", "contrat")
FICHIER = "_recettes.json"

# Shown in an empty editor (the desktop's and the web's).
EXEMPLE = (
    "# champ | de | vers   (champs : entreprise, localisation, contrat ; re: = motif)\n"
    "# entreprise | PricewaterhouseCoopers | PwC\n"
    "# entreprise | re:\\s+(SAS|SA|GmbH)$ |\n"
    "# localisation | re:^Paris \\d+e$ | Paris\n"
)


@dataclass(frozen=True)
class Recette:
    """One rule: in `champ`, `de` (a value, or `re:` + a pattern) becomes `vers`."""

    champ: str
    de: str
    vers: str


@dataclass(frozen=True)
class Changement:
    """One change a recipe makes (or would make) to one offer."""

    oid: str
    champ: str
    avant: str
    apres: str
    ecarte: str = ""  # why it is not applied ("candidature", "doublon"), "" if it is


def _espaces(v: object) -> str:
    return " ".join(str(v or "").split())


def depuis_json(donnees: object) -> list[Recette]:
    """The recipes of a loaded JSON list; malformed entries are skipped."""
    out = []
    for d in donnees if isinstance(donnees, list) else []:
        if isinstance(d, dict) and d.get("champ") and d.get("de") is not None:
            out.append(Recette(str(d["champ"]), str(d["de"]), str(d.get("vers") or "")))
    return out


def lire(chemin: Path) -> list[Recette]:
    """The recipes saved in `chemin`; [] if absent or unreadable."""
    try:
        return depuis_json(json.loads(chemin.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return []


def ecrire(chemin: Path, recettes: list[Recette]) -> None:
    """Saves the recipes (atomic write)."""
    tmp = chemin.with_name(chemin.name + ".tmp")
    tmp.write_text(
        json.dumps([r.__dict__ for r in recettes], ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8",
    )
    tmp.replace(chemin)


def depuis_texte(texte: str) -> list[Recette]:
    """One recipe per line, 'champ | de | vers' (the app's editing format).

    The separator is a `|` with spaces around it: a pattern's own `(SAS|SA)` has none.
    """
    out = []
    for ligne in texte.splitlines():
        if not ligne.strip() or ligne.lstrip().startswith("#"):
            continue
        morceaux = [m.strip() for m in re.split(r"(?<!\S)\|(?!\S)", ligne.strip(), maxsplit=2)]
        morceaux += [""] * (3 - len(morceaux))
        out.append(Recette(morceaux[0], morceaux[1], morceaux[2]))
    return out


def en_texte(recettes: list[Recette]) -> str:
    """The inverse of depuis_texte()."""
    return "\n".join(f"{r.champ} | {r.de} | {r.vers}" for r in recettes)


def valider(recettes: list[Recette]) -> list[str]:
    """What prevents using the recipes, in plain words; [] if nothing."""
    erreurs = []
    for i, r in enumerate(recettes, 1):
        if r.champ not in CHAMPS:
            erreurs.append(f"ligne {i} : champ « {r.champ} » inconnu ({', '.join(CHAMPS)})")
        if not r.de.strip() or r.de.strip() == "re:":
            erreurs.append(f"ligne {i} : rien à remplacer")
        elif r.de.startswith("re:"):
            try:
                re.compile(r.de[3:], re.I)
            except re.error as x:
                erreurs.append(f"ligne {i} : motif invalide ({x.msg})")
    return erreurs


def transformer(valeur: str, champ: str, recettes: list[Recette]) -> str:
    """`valeur` after every recipe of `champ`, in order."""
    v = _espaces(valeur)
    for r in recettes:
        if r.champ != champ:
            continue
        if r.de.startswith("re:"):
            v = _espaces(re.sub(r.de[3:], r.vers, v, flags=re.I))
        elif v.casefold() == _espaces(r.de).casefold():
            v = _espaces(r.vers)
    return v


def _oid(o: Any) -> str:
    """queue_io.oid, without importing the storage (this module is pure)."""
    return f"{(o.get('entreprise') or '').strip()}|{(o.get('poste') or '').strip()}"


def apercu(offres: list[Any], recettes: list[Recette], candidatures: set[str]) -> list[Changement]:
    """Every change the recipes would make, the skipped ones with their reason."""
    existants = {_oid(o) for o in offres}
    out = []
    for o in offres:
        oid = _oid(o)
        for champ in CHAMPS:
            avant = str(o.get(champ) or "")
            if not avant.strip():
                continue
            apres = transformer(avant, champ, recettes)
            if apres == _espaces(avant) or not apres:
                continue  # nothing to do, or a rule that would empty the field
            ecarte = ""
            if champ == "entreprise":
                neuf = _oid({**o, "entreprise": apres})
                if oid in candidatures:
                    ecarte = "candidature"
                elif neuf in existants:
                    ecarte = "doublon"
            out.append(Changement(oid, champ, avant, apres, ecarte))
    return out


def appliquer(offres: list[Any], changements: list[Changement]) -> int:
    """Applies the changes not set aside to `offres` (modified in place). Returns the count."""
    par_oid: dict[str, list[Changement]] = {}
    for c in changements:
        if not c.ecarte:
            par_oid.setdefault(c.oid, []).append(c)
    n = 0
    for o in offres:
        for c in par_oid.get(_oid(o), []):
            if str(o.get(c.champ) or "") == c.avant:  # unchanged since the preview
                o[c.champ] = c.apres
                n += 1
    return n
