"""Chaque `module.nom` qu'un programme utilise sur un autre module du projet existe.

POURQUOI. Pendant la phase 3, `ruff --fix` a supprime de job_sources un import juge
inutile (`_client_partage`) : il n'etait pas utilise DANS job_sources, mais
audit_dispo appelle `job_sources._client_partage()`. Rien ne cassait au chargement ;
l'erreur ne serait sortie qu'a l'execution de l'audit. Ce test relit le code
(AST) de src/ et JobHunter.pyw, repere chaque acces `alias.nom` sur un module du
projet importe, et verifie que le nom existe vraiment.
"""

import ast
import importlib

import pytest
from conftest import RACINE

SRC = RACINE / "src"
FICHIERS = sorted([*SRC.rglob("*.py"), RACINE / "JobHunter.pyw"])
# sortent sur le web : on ne les importe pas
HORS_LIGNE = {"jobhunter.programmes.test_live_nav", "jobhunter.programmes.test_acces_sites"}


def est_module(nom):
    """`nom` (pointe) designe-t-il un module ou un paquet de src/ ?"""
    chemin = SRC.joinpath(*nom.split("."))
    return chemin.with_suffix(".py").exists() or (chemin / "__init__.py").exists()


def acces(fichier):
    """{(module, nom)} des acces `alias.nom` sur des modules du projet."""
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
