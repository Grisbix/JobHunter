"""Module values computed on first read, not at import (phase 4 of the plan).

The constants taken from the profile (filter patterns, scoring axes, letter texts) and
from `Scripts/chemins.json` were computed at load time: importing
`jobhunter.sources.linkedin` read the profile. They are now declared as factories in
the `_PARESSEUX` dictionary of their module, and the module's `__getattr__` (PEP 562)
computes them on the first read of `module.NAME`, then stores them in the module: the
following reads, a `monkeypatch.setattr` or a facade see them as before.

In the module itself, the code reads these names through `_ici.NAME` (`_ici` = the
module): a bare global name does not go through `__getattr__` and would raise
`NameError`.

`oublier()` erases the values already computed; `profil.utiliser()` uses it so that an
injected profile applies everywhere.

Decision: docs/adr/0007-valeurs-du-profil-paresseuses.md
"""

import types
from collections.abc import Callable
from typing import Any

Fabriques = dict[str, Callable[[], Any]]

# Modules of which at least one value was computed: what `oublier` must empty.
_CALCULES: dict[str, tuple[types.ModuleType, Fabriques]] = {}


def lire(module: types.ModuleType, fabriques: Fabriques, nom: str) -> Any:
    """Body of a module's `__getattr__`: computes `nom`, keeps it, returns it."""
    fabrique = fabriques.get(nom)
    if fabrique is None:
        raise AttributeError(f"module {module.__name__!r} has no attribute {nom!r}")
    valeur = fabrique()
    setattr(module, nom, valeur)
    _CALCULES[module.__name__] = (module, fabriques)
    return valeur


def oublier() -> None:
    """Erases the computed values: the next read recomputes them."""
    for module, fabriques in _CALCULES.values():
        for nom in fabriques:
            vars(module).pop(nom, None)
    _CALCULES.clear()
