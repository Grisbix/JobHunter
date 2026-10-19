"""Package facade: a large old module that was split keeps ONE namespace.

`installer(paquet, sous_modules)` makes the package a module that sees ALL the names of
its submodules, like the old single file (`job_sources.title_ok`,
`tailor_application.tailor_cv`). An assignment (`pkg.NAME = ...`, a monkeypatch)
goes to the submodules that bind the name; the others read it through
`_proprietaire.NAME`, never by copy. Without this routing, a test that replaces
`_get_borne` would let the collection go out on the real network.

The `Scripts/*.py` facades left in 2.0; this one stays for `sources`, `documents`,
`navigation` and `app`, whose programs and tests still read names through the package
(`jobhunter.sources.title_ok`). Removing it would require pointing each caller to the
submodule that carries the name.

Decision: docs/adr/0001-facade-aliases.md
"""

import importlib
import sys
import types
from collections.abc import Sequence
from typing import Any


def installer(paquet: str, sous_modules: Sequence[str]) -> list[types.ModuleType]:
    """Loads `sous_modules` of `paquet` and makes the package their facade. Returns the modules."""
    modules = [importlib.import_module(f"{paquet}.{m}") for m in sous_modules]
    # The original bindings: `unittest.mock.patch` exits through a `delattr` on the
    # facade (the name is not in ITS dict); we then put the original value back instead
    # of erasing the submodule's function.
    origine = {m: dict(vars(m)) for m in modules}
    noms_sous_modules = set(sous_modules)

    def paresseux(m: types.ModuleType) -> dict[str, Any]:
        """Factories of values computed on first read (jobhunter.paresseux)."""
        fabriques: dict[str, Any] = vars(m).get("_PARESSEUX", {})
        return fabriques

    def tenants(nom: str) -> list[types.ModuleType]:
        """Submodules where `nom` is bound. The owner (the one that DEFINES it) first."""
        t = [m for m in modules if nom in vars(m) or nom in origine[m] or nom in paresseux(m)]
        t.sort(key=lambda m: getattr(origine[m].get(nom), "__module__", None) != m.__name__)
        return t

    class _Facade(types.ModuleType):
        def __getattr__(self, nom: str) -> Any:
            for m in modules:
                if nom in vars(m):
                    return vars(m)[nom]
                if nom in paresseux(m):
                    return getattr(m, nom)
            raise AttributeError(f"module {self.__name__!r} has no attribute {nom!r}")

        def __setattr__(self, nom: str, valeur: Any) -> None:
            t = [] if nom.startswith("__") or nom in noms_sous_modules else tenants(nom)
            if not t:
                super().__setattr__(nom, valeur)
                return
            # All the submodules that bind the name: the owner, and those that
            # imported it as is — a replacement must apply wherever it is read.
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
