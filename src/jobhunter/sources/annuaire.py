"""Annuaires d'entreprises Lever, Ashby et Greenhouse : d'un nom à un flux à suivre.

Partie de jobhunter.sources. Pour suivre une entreprise par l'API publique de son outil
de recrutement, il faut l'identifiant de son tableau d'offres (`jobs.lever.co/<id>`).
Le panneau Entreprises le trouve ici à partir du nom tapé, sans aller sur le web.

Données : `annuaires/*.json`, 3 600 entreprises reprises de jobsync (licence MIT,
`annuaires/LICENSE-jobsync.txt`), régénérées par `outils/annuaires.py`. La région Lever
(lever.co ou eu.lever.co) se résout à la collecte (sources.ats).
"""

import functools
import json
import unicodedata
from dataclasses import dataclass
from importlib import resources

OUTILS = ("lever", "ashby", "greenhouse")


@dataclass(frozen=True)
class Entree:
    """Une entreprise de l'annuaire."""

    nom: str
    outil: str  # « lever », « ashby » ou « greenhouse »
    jeton: str  # l'identifiant du tableau d'offres


def _plat(texte: str) -> str:
    """Minuscules, sans accents ni ponctuation : « L'Oréal » → « loreal »."""
    t = unicodedata.normalize("NFKD", texte.casefold())
    return "".join(c for c in t if c.isalnum())


@functools.cache
def entrees() -> tuple[Entree, ...]:
    """Toutes les entreprises des trois annuaires (lues une fois)."""
    sortie: list[Entree] = []
    for outil in OUTILS:
        brut = (
            resources.files(__package__)
            .joinpath("annuaires", f"{outil}.json")
            .read_text(encoding="utf-8")
        )
        sortie.extend(Entree(nom, outil, jeton) for nom, jeton in json.loads(brut))
    return tuple(sortie)


def chercher(texte: str, limite: int = 30) -> list[Entree]:
    """Les entreprises dont le nom (ou l'identifiant) correspond à `texte`.

    Ordre : nom exact, puis nom qui commence par le texte, puis un mot du nom qui
    commence par lui, puis le texte dans un mot ; à égalité, par nom.

    Args:
        texte: ce que l'utilisateur a tapé ; moins de 2 caractères utiles → [].
        limite: nombre maximal de résultats.
    """
    q = _plat(texte)
    if len(q) < 2:
        return []
    classees = []
    for e in entrees():
        nom, jeton = _plat(e.nom), _plat(e.jeton)
        mots = [_plat(m) for m in e.nom.split()]
        if q in (nom, jeton):
            rang = 0
        elif nom.startswith(q) or jeton.startswith(q):
            rang = 1
        elif any(m.startswith(q) for m in mots):
            rang = 2
        elif any(q in m for m in mots):
            rang = 3
        else:
            continue
        classees.append((rang, e.nom.casefold(), e.outil, e))
    classees.sort(key=lambda x: x[:3])
    return [e for *_, e in classees[:limite]]
