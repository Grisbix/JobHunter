"""Architecture rules of the package, checked on the code (phase 3 of the plan).

1. The ENGINE does not import the interface: neither tkinter, nor customtkinter, nor
   jobhunter.app. Only `jobhunter.app`, `jobhunter.welcome` (the first launch,
   which opens a file-choice window) and `jobhunter.welcome_tour` (its tour) are allowed to. An engine that pulls in Tkinter no longer
   runs in a scheduled task without a screen, nor in CI.
2. No module of the package touches sys.path: the package is imported because it is
   installed (or because `JobHunter.pyw` adds src/, the only allowed place). Eight
   insertions of Scripts/ — the DATA folder — survived 2.0 until
   2026-10-19: a .py dropped there came before the modules of the same name.

The plan said these rules were "checked in CI by import-linter", which was never
wired up; this test stands in for it, without a dependency.
"""

import ast
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parent.parent / "src" / "jobhunter"
INTERFACE = ("tkinter", "customtkinter", "jobhunter.app")
DROIT_A_L_INTERFACE = ("app", "welcome", "welcome_tour", "launch")


def modules():
    for f in sorted(SRC.rglob("*.py")):
        rel = f.relative_to(SRC)
        yield rel, ast.parse(f.read_text(encoding="utf-8"))


def imports(arbre):
    """All the imported modules, including inside functions (deferred imports)."""
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
    """The rule itself: a false negative would make the test useless."""
    assert any(touche_l_interface(nom) for _, nom in imports(ast.parse(code))) is attendu
