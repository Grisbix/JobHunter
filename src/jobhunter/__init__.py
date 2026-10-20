"""JobHunter — the engine, as a package.

Phase 3 of the plan (docs/professionalisation-plan.md): the code of Scripts/ moved
here module by module. In 2.25 the modules took English names (`jobhunter.programmes`
→ `jobhunter.programs`, `racine` → `root`…). The French names keep working: a finder
maps each old name to the new module, so that `import jobhunter.programmes.jutil`,
`python -m jobhunter.programmes.relances` and the scripts written before 2.25 get the
SAME module object as the new name (a monkeypatch on one acts on the other).
"""

import importlib
import importlib.abc
import importlib.machinery
import importlib.util
import sys
import types

# Loaded before the finder is installed: the finder itself reads this table.
from jobhunter._old_names import ANCIENS


def _nouveau_nom(ancien: str) -> str | None:
    """'jobhunter.programmes.jutil.x' -> 'jobhunter.programs.util.x'; None if not an old name."""
    if not ancien.startswith("jobhunter."):
        return None
    parties = ancien.split(".")[1:]
    for n in range(len(parties), 0, -1):
        cle = ".".join(parties[:n])
        if cle in ANCIENS:
            return ".".join(["jobhunter", *ANCIENS[cle].split("."), *parties[n:]])
    # `from jobhunter.programmes import relances` asks for 'jobhunter.programs.relances':
    # the package already under its new name, the module under its old one.
    if len(parties) >= 2:
        for cle, neuf in ANCIENS.items():
            paquet, _, feuille = cle.rpartition(".")
            if feuille == parties[1] and ANCIENS.get(paquet, paquet) == parties[0]:
                return ".".join(["jobhunter", *neuf.split("."), *parties[2:]])
    return None


class _Alias(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    """The module of the new name, registered under the old one."""

    def find_spec(self, nom, chemin=None, cible=None):
        nouveau = _nouveau_nom(nom)
        if nouveau is None or importlib.util.find_spec(nouveau) is None:
            return None
        spec = importlib.machinery.ModuleSpec(nom, self, is_package=self.is_package(nom))
        spec.loader_state = nouveau
        return spec

    def create_module(self, spec):
        module = importlib.import_module(spec.loader_state)
        spec.loader_state = (spec.loader_state, module.__spec__)
        return module

    def exec_module(self, module: types.ModuleType) -> None:
        # Already executed under its new name. The import machinery has just set
        # `__spec__` to the alias spec: the module keeps its real one.
        alias = module.__spec__
        if alias is not None and isinstance(alias.loader_state, tuple):
            module.__spec__ = alias.loader_state[1]

    # runpy (`python -m <old name>`) asks the loader for the code of the module.
    def get_code(self, nom):
        nouveau = _nouveau_nom(nom)
        spec = importlib.util.find_spec(nouveau) if nouveau else None
        if spec is None or spec.loader is None:
            raise ImportError(nom)
        if spec.submodule_search_locations is not None:
            spec = importlib.util.find_spec(f"{nouveau}.__main__")
            if spec is None or spec.loader is None:
                raise ImportError(f"{nom}.__main__")
            return spec.loader.get_code(f"{nouveau}.__main__")
        return spec.loader.get_code(nouveau)

    def is_package(self, nom):
        nouveau = _nouveau_nom(nom)
        spec = importlib.util.find_spec(nouveau) if nouveau else None
        return bool(spec and spec.submodule_search_locations is not None)


# First in line: once `jobhunter.programmes` is the `programs` package, the ordinary
# finder would load `jobhunter.programmes.add_offer` a SECOND time from its folder.
if not any(isinstance(f, _Alias) for f in sys.meta_path):
    sys.meta_path.insert(0, _Alias())
