"""Facade de paquet : un ancien gros module decoupe garde UN espace de noms.

`installer(paquet, sous_modules)` fait du paquet un module qui voit TOUS les noms de
ses sous-modules, comme l'ancien fichier unique (`job_sources.title_ok`,
`tailor_application.tailor_cv`). Une affectation (`pkg.NOM = ...`, un monkeypatch)
part dans les sous-modules qui lient le nom ; les autres le lisent par
`_proprietaire.NOM`, jamais par copie. Sans ce routage, un test qui remplace
`_get_borne` laisserait la collecte sortir sur le vrai reseau.

A retirer avec les facades `Scripts/*.py` (phase 3.9) : les appelants importeront alors
le sous-module qui porte le nom.
"""

import importlib
import sys
import types
from collections.abc import Sequence
from typing import Any


def installer(paquet: str, sous_modules: Sequence[str]) -> list[types.ModuleType]:
    """Charge `sous_modules` de `paquet` et fait du paquet leur facade. Rend les modules."""
    modules = [importlib.import_module(f"{paquet}.{m}") for m in sous_modules]
    # Les liaisons d'origine : `unittest.mock.patch` sort par un `delattr` sur la
    # facade (le nom n'est pas dans SON dict) ; on remet alors la valeur d'origine au
    # lieu d'effacer la fonction du sous-module.
    origine = {m: dict(vars(m)) for m in modules}
    noms_sous_modules = set(sous_modules)

    def tenants(nom: str) -> list[types.ModuleType]:
        """Sous-modules ou `nom` est lie. Le proprietaire (celui qui le DEFINIT) en tete."""
        t = [m for m in modules if nom in vars(m) or nom in origine[m]]
        t.sort(key=lambda m: getattr(origine[m].get(nom), "__module__", None) != m.__name__)
        return t

    class _Facade(types.ModuleType):
        def __getattr__(self, nom: str) -> Any:
            for m in modules:
                if nom in vars(m):
                    return vars(m)[nom]
            raise AttributeError(f"module {self.__name__!r} has no attribute {nom!r}")

        def __setattr__(self, nom: str, valeur: Any) -> None:
            t = [] if nom.startswith("__") or nom in noms_sous_modules else tenants(nom)
            if not t:
                super().__setattr__(nom, valeur)
                return
            # Tous les sous-modules qui lient le nom : le proprietaire, et ceux qui
            # l'ont importe tel quel — un remplacement doit valoir partout ou on le lit.
            for m in t:
                setattr(m, nom, valeur)

        def __delattr__(self, nom: str) -> None:
            if nom in vars(self):
                super().__delattr__(nom)
                return
            t = tenants(nom)
            if not t:
                raise AttributeError(nom)
            for m in t:
                if nom in origine[m]:
                    setattr(m, nom, origine[m][nom])
                else:
                    delattr(m, nom)

        def __dir__(self) -> list[str]:
            return sorted(set(super().__dir__()).union(*(vars(m) for m in modules)))

    sys.modules[paquet].__class__ = _Facade
    return modules
