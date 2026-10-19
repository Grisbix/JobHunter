"""Valeurs de module calculees a la premiere lecture, pas a l'import (phase 4 du plan).

Les constantes tirees du profil (motifs du filtre, axes du scoring, textes de lettre)
et de `Scripts/chemins.json` etaient calculees au chargement : importer
`jobhunter.sources.linkedin` lisait le profil. Elles sont maintenant declarees comme
fabriques dans le dictionnaire `_PARESSEUX` de leur module, et le `__getattr__` de
module (PEP 562) les calcule a la premiere lecture de `module.NOM`, puis les range dans
le module : les lectures suivantes, un `monkeypatch.setattr` ou une facade les voient
comme avant.

Dans le module lui-meme, le code lit ces noms par `_ici.NOM` (`_ici` = le module) : un
nom global nu ne passe pas par `__getattr__` et leverait `NameError`.

`oublier()` efface les valeurs deja calculees ; `profil.utiliser()` s'en sert pour
qu'un profil injecte vaille partout.

Decision : docs/adr/0007-valeurs-du-profil-paresseuses.md
"""

import types
from collections.abc import Callable
from typing import Any

Fabriques = dict[str, Callable[[], Any]]

# Modules dont au moins une valeur a ete calculee : ce que `oublier` doit vider.
_CALCULES: dict[str, tuple[types.ModuleType, Fabriques]] = {}


def lire(module: types.ModuleType, fabriques: Fabriques, nom: str) -> Any:
    """Corps du `__getattr__` d'un module : calcule `nom`, le garde, le rend."""
    fabrique = fabriques.get(nom)
    if fabrique is None:
        raise AttributeError(f"module {module.__name__!r} has no attribute {nom!r}")
    valeur = fabrique()
    setattr(module, nom, valeur)
    _CALCULES[module.__name__] = (module, fabriques)
    return valeur


def oublier() -> None:
    """Efface les valeurs calculees : la prochaine lecture les refait."""
    for module, fabriques in _CALCULES.values():
        for nom in fabriques:
            vars(module).pop(nom, None)
    _CALCULES.clear()
