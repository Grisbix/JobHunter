"""The profile's skills, as the "Compétences" tab of the Profil panel edits them.

A skill lives in two places of the profile:
  - `competences[<name>]`: the words searched in a posting (`synonymes`), its English
    name (`en`) and, optionally, how a letter says it (`prose_fr`, `prose_en`);
  - `scoring.axes[<axe>].competences`: the axes it counts for in the fit ("Machine
    learning / IA" counts for data and for AI). A skill in no axis is still recognised
    (CV coverage, letters) but does not raise the fit.

The tab edits both; nothing is written before "Enregistrer" (`ecrire` of
search_settings keeps the previous profile as `.bak`). A skill is never renamed here:
its name is the key the letters, the CV facts and the base skills refer to.
"""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Competence:
    """A skill of the profile, with the axes it counts for."""

    nom: str
    axes: list[str]  # [] = counted in no axis; a skill may count for two
    synonymes: list[str]
    en: str = ""
    autres: dict[str, Any] = field(default_factory=dict)  # prose_fr, prose_en… kept as is


def axes(profil: dict[str, Any]) -> list[str]:
    """The profile's axes, in its order."""
    return list(((profil.get("scoring") or {}).get("axes") or {}).keys())


def lire(profil: dict[str, Any]) -> list[Competence]:
    """The skills of a profile, in its order, each with the axes it counts for."""
    axes_de: dict[str, list[str]] = {}
    for a, v in ((profil.get("scoring") or {}).get("axes") or {}).items():
        for nom in v.get("competences") or []:
            axes_de.setdefault(nom, []).append(a)
    out = []
    for nom, v in (profil.get("competences") or {}).items():
        v = v or {}
        out.append(
            Competence(
                nom=nom,
                axes=axes_de.get(nom, []),
                synonymes=[str(x) for x in v.get("synonymes") or []],
                en=str(v.get("en") or ""),
                autres={k: x for k, x in v.items() if k not in ("synonymes", "en")},
            )
        )
    return out


def depuis_texte(texte: str) -> list[str]:
    """Synonyms typed one per line or separated by commas; blanks and repeats removed.

    A space at the edge of a line is kept: synonyms are matched as substrings, so
    "ia " finds "IA " but not "social", "git " not "digital". Stripping it widened
    the match each time a skill was saved in the app. Only the space that follows a
    comma (or precedes one) is a separator; runs of spaces become one.
    """
    vus: list[str] = []
    for ligne in texte.splitlines():
        morceaux = ligne.split(",")
        for j, morceau in enumerate(morceaux):
            if j > 0:
                morceau = morceau.lstrip()
            if j < len(morceaux) - 1:
                morceau = morceau.rstrip()
            m = re.sub(r"\s+", " ", morceau)
            if m.strip() and m.lower() not in {x.lower() for x in vus}:
                vus.append(m)
    return vus


def valider(liste: list[Competence], profil: dict[str, Any]) -> list[str]:
    """What prevents saving, in plain words. Empty = can be saved."""
    erreurs = []
    noms = [c.nom.strip() for c in liste]
    if any(not n for n in noms):
        erreurs.append("une compétence n'a pas de nom")
    doublons = sorted({n for n in noms if n and noms.count(n) > 1})
    if doublons:
        erreurs.append("nom en double : " + ", ".join(doublons))
    for c in liste:
        if c.nom.strip() and not c.synonymes:
            erreurs.append(f"« {c.nom} » : aucun mot à chercher dans les annonces")
        if inconnus := [a for a in c.axes if a not in axes(profil)]:
            erreurs.append(f"« {c.nom} » : axe inconnu ({', '.join(inconnus)})")
    gardees = set(noms)
    for n in profil.get("competences_de_base") or []:
        if n in (profil.get("competences") or {}) and n not in gardees:
            erreurs.append(
                f"« {n} » est une compétence de base du CV : elle ne peut pas être retirée"
            )
    return erreurs


def appliquer(profil: dict[str, Any], liste: list[Competence]) -> dict[str, Any]:
    """A copy of the profile carrying `liste`: skills and their axis.

    An axis keeps the order of its skills already there; new ones go at its end.
    """
    out = copy.deepcopy(profil)
    comp: dict[str, Any] = {}
    for c in liste:
        v: dict[str, Any] = {"synonymes": list(c.synonymes)}
        if c.en.strip():
            v["en"] = c.en.strip()
        v.update(c.autres)
        # A skill added in the app had no sentence form: the letter never quoted it.
        # Its name, in lower case unless it is an acronym ("consolidation", "SAP").
        if c.nom.strip() not in (profil.get("competences") or {}):
            nom = c.nom.strip()
            dit = nom if nom[:2].isupper() else nom[:1].lower() + nom[1:]
            v.setdefault("prose_fr", dit)
            v.setdefault("prose_en", v.get("en") or dit)
        comp[c.nom.strip()] = v
    out["competences"] = comp
    voulu = {c.nom.strip(): c.axes for c in liste}
    connues = set(profil.get("competences") or {})
    for a, v in ((out.get("scoring") or {}).get("axes") or {}).items():
        # A name an axis carries that was never a skill of the profile stays where it
        # is; a skill removed from the list leaves its axes.
        avant = [
            n for n in v.get("competences") or [] if a in voulu.get(n, [] if n in connues else [a])
        ]
        nouveaux = [c.nom.strip() for c in liste if a in c.axes and c.nom.strip() not in avant]
        v["competences"] = avant + nouveaux
    return out
