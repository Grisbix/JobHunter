"""Chaque `module.nom` qu'un programme utilise sur un autre module du projet existe.

POURQUOI. Pendant la phase 3, `ruff --fix` a supprime de job_sources un import juge
inutile (`_client_partage`) : il n'etait pas utilise DANS job_sources, mais
audit_dispo appelle `job_sources._client_partage()`. Rien ne cassait au chargement ;
l'erreur ne serait sortie qu'a l'execution de l'audit. Ce test relit le code
(AST) de Scripts/, src/ et JobHunter.pyw, repere chaque acces `alias.nom` sur un
module du projet importe, et verifie que le nom existe vraiment.
"""

import ast
import importlib

import pytest
from conftest import RACINE

SCRIPTS = RACINE / "Scripts"
PROJET = {p.stem for p in SCRIPTS.glob("*.py")}
FICHIERS = sorted(
    [*SCRIPTS.glob("*.py"), *(RACINE / "src").rglob("*.py"), RACINE / "JobHunter.pyw"]
)
HORS_LIGNE = {"test_live_nav", "test_acces_sites"}  # sortent sur le web : on ne les importe pas


def acces(fichier):
    """{(module, nom)} des acces `alias.nom` sur des modules du projet."""
    arbre = ast.parse(fichier.read_text(encoding="utf-8"))
    alias = {}
    for n in ast.walk(arbre):
        if isinstance(n, ast.Import):
            for a in n.names:
                if a.name in PROJET:
                    alias[a.asname or a.name] = a.name
        elif isinstance(n, ast.ImportFrom) and n.module == "jobhunter" and n.level == 0:
            for a in n.names:
                alias[a.asname or a.name] = f"jobhunter.{a.name}"
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
