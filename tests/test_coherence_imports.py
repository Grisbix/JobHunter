"""Each `module.name` a program uses on another module of the project exists.

WHY. During phase 3, `ruff --fix` removed from job_sources an import deemed
unused (`_client_partage`): it was not used WITHIN job_sources, but
audit_dispo calls `job_sources._client_partage()`. Nothing broke at load time;
the error would only have come out when running the audit. This test rereads the code
(AST) of src/ and JobHunter.pyw, spots each `alias.name` access on an imported
project module, and checks that the name really exists.
"""

import ast
import importlib

import pytest
from conftest import RACINE

SRC = RACINE / "src"
FICHIERS = sorted([*SRC.rglob("*.py"), RACINE / "JobHunter.pyw"])
# they go out on the web: we do not import them
HORS_LIGNE = {"jobhunter.programmes.test_live_nav", "jobhunter.programmes.test_acces_sites"}


def est_module(nom):
    """Does `nom` (dotted) designate a module or a package of src/?"""
    chemin = SRC.joinpath(*nom.split("."))
    return chemin.with_suffix(".py").exists() or (chemin / "__init__.py").exists()


def acces(fichier):
    """{(module, name)} of the `alias.name` accesses on project modules."""
    arbre = ast.parse(fichier.read_text(encoding="utf-8"))
    alias = {}
    for n in ast.walk(arbre):
        if (
            isinstance(n, ast.ImportFrom)
            and n.level == 0
            and (n.module or "").startswith("jobhunter")
        ):
            for a in n.names:
                if est_module(f"{n.module}.{a.name}"):
                    alias[a.asname or a.name] = f"{n.module}.{a.name}"
    vus = set()
    for n in ast.walk(arbre):
        if (
            isinstance(n, ast.Attribute)
            and isinstance(n.value, ast.Name)
            and n.value.id in alias
            and isinstance(n.ctx, ast.Load)
        ):
            vus.add((alias[n.value.id], n.attr))
    return vus


CAS = sorted({(f.name, m, nom) for f in FICHIERS for m, nom in acces(f) if m not in HORS_LIGNE})


def test_des_acces_sont_bien_trouves():
    assert len(CAS) > 100


@pytest.mark.parametrize(("fichier", "module", "nom"), CAS, ids=[f"{f}:{m}.{n}" for f, m, n in CAS])
def test_le_nom_existe(fichier, module, nom):
    mod = importlib.import_module(module)
    assert hasattr(mod, nom), f"{fichier} utilise {module}.{nom}, qui n'existe pas"
