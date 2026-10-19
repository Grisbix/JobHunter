"""Règles d'architecture du paquet, vérifiées sur le code (phase 3 du plan).

1. Le MOTEUR n'importe pas l'interface : ni tkinter, ni customtkinter, ni
   jobhunter.app. Seuls `jobhunter.app` et `jobhunter.accueil` (le premier lancement,
   qui ouvre une fenêtre de choix de fichier) y ont droit. Un moteur qui tire Tkinter ne
   tourne plus dans une tâche planifiée sans écran, ni en CI.
2. Aucun module du paquet ne touche à sys.path : le paquet s'importe parce qu'il est
   installé (ou parce que `JobHunter.pyw` ajoute src/, seul endroit autorisé). Huit
   insertions de Scripts/ — le dossier des DONNÉES — ont survécu à la 2.0 jusqu'au
   2026-10-19 : un .py déposé là passait avant les modules du même nom.

Le plan disait ces règles « vérifiées en CI par import-linter », qui n'a jamais été
branché ; ce test en tient lieu, sans dépendance.
"""

import ast
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parent.parent / "src" / "jobhunter"
INTERFACE = ("tkinter", "customtkinter", "jobhunter.app")
DROIT_A_L_INTERFACE = ("app", "accueil")


def modules():
    for f in sorted(SRC.rglob("*.py")):
        rel = f.relative_to(SRC)
        yield rel, ast.parse(f.read_text(encoding="utf-8"))


def imports(arbre):
    """Tous les modules importés, y compris dans les fonctions (imports différés)."""
    for n in ast.walk(arbre):
        if isinstance(n, ast.Import):
            for a in n.names:
                yield n.lineno, a.name
        elif isinstance(n, ast.ImportFrom) and n.level == 0 and n.module:
            yield n.lineno, n.module
            if n.module == "jobhunter":
                for a in n.names:
                    yield n.lineno, f"jobhunter.{a.name}"


def touche_l_interface(nom):
    return any(nom == i or nom.startswith(i + ".") for i in INTERFACE)


def test_le_moteur_n_importe_pas_l_interface():
    fautes = [
        f"{rel}:{ligne} importe {nom}"
        for rel, arbre in modules()
        if rel.parts[0].removesuffix(".py") not in DROIT_A_L_INTERFACE
        for ligne, nom in imports(arbre)
        if touche_l_interface(nom)
    ]
    assert fautes == []


def test_aucun_module_ne_touche_a_sys_path():
    fautes = []
    for rel, arbre in modules():
        for n in ast.walk(arbre):
            if (
                isinstance(n, ast.Attribute)
                and n.attr == "path"
                and isinstance(n.value, ast.Name)
                and n.value.id == "sys"
            ):
                fautes.append(f"{rel}:{n.lineno}")
    assert fautes == []


@pytest.mark.parametrize(
    ("code", "attendu"),
    [
        ("import tkinter", True),
        ("from tkinter import messagebox", True),
        ("import customtkinter as ctk", True),
        ("from jobhunter.app import commun", True),
        ("from jobhunter import app", True),
        ("from jobhunter import profil", False),
        ("import tkinterx", False),
    ],
)
def test_la_regle_voit_ce_qu_elle_doit_voir(code, attendu):
    """La règle elle-même : un faux négatif rendrait le test inutile."""
    assert any(touche_l_interface(nom) for _, nom in imports(ast.parse(code))) is attendu
