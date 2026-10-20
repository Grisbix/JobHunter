"""The jobhunter.app package (phase 3.7): App assembled from mixins, minimal launcher.

- App inherits from each mixin and keeps all its methods (none lost or doubled);
- the settings rebound by the theme (fonts, spacings) are read through the module;
- JobHunter.pyw only launches: it compiles and does not import the app at import time.
"""

import ast
import os
import subprocess
import sys

from conftest import EXEMPLE, RACINE, SRC

os.environ["JOBHUNTER_SANS_FOND"] = "1"
import jobhunter.app as app  # noqa: E402
from jobhunter.app import theme
from jobhunter.app import window as fenetre  # noqa: E402

MIXINS = [
    "TableauMixin",
    "DonneesMixin",
    "FicheMixin",
    "ActionsMixin",
    "PanneauxMixin",
    "DetailMixin",
    "ExecutionMixin",
]


def test_app_herite_des_mixins():
    noms = [c.__name__ for c in fenetre.App.__mro__]
    assert all(m in noms for m in MIXINS)


def test_aucune_methode_en_double():
    vues = {}
    for c in fenetre.App.__mro__[:-1]:
        for nom, v in vars(c).items():
            if callable(v) and not nom.startswith("__"):
                assert nom not in vues, f"{nom} dans {vues.get(nom)} et {c.__name__}"
                vues[nom] = c.__name__
    assert len(vues) >= 105


def test_facade():
    assert app.App is fenetre.App
    assert app.CF is theme.CF


def test_reglage_du_theme_lu_par_le_module(monkeypatch):
    monkeypatch.setattr(app, "GAP", 99)
    assert theme.GAP == 99


def test_lanceur_minimal():
    texte = (RACINE / "JobHunter.pyw").read_text(encoding="utf-8")
    ast.parse(texte)
    assert len(texte.splitlines()) < 40


def test_lanceur_importable_sans_ouvrir_de_fenetre():
    env = {**os.environ, "PYTHONPATH": str(SRC), "PROFIL_JOBHUNTER": str(EXEMPLE)}
    code = (
        "import importlib.machinery as m, importlib.util as u, sys;"
        f"l = m.SourceFileLoader('lanceur', r'{RACINE / 'JobHunter.pyw'}');"
        "mod = u.module_from_spec(u.spec_from_loader('lanceur', l)); l.exec_module(mod);"
        "print('jobhunter.app.window' in sys.modules)"
    )
    r = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "False"
