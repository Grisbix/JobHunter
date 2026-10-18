"""Le paquet jobhunter.navigation (phase 3.6) : facades, noms conserves, sous-modules autonomes.

- web_nav EST jobhunter.navigation, site_strategies EST navigation.strategies ;
- les noms de l'ancien fichier unique restent lisibles (dismiss_cookies, fill_application...) ;
- chaque sous-module se charge seul : le decoupage n'a laisse aucun cycle d'import.
"""

import os
import subprocess
import sys

import pytest
from conftest import EXEMPLE, SRC

import jobhunter.navigation as paquet
import site_strategies
import web_nav
from jobhunter.navigation import carrieres, formulaires, navigateur, page, segment, strategies

SOUS_MODULES = [
    "page",
    "etapes",
    "carrieres",
    "formulaires",
    "llm",
    "compte",
    "segment",
    "linkedin",
    "navigateur",
    "otp",
    "categories",
    "strategies",
]


def test_facades():
    assert web_nav is paquet
    assert site_strategies is strategies


@pytest.mark.parametrize(
    ("nom", "module"),
    [
        ("COOKIE_JS", page),
        ("dismiss_cookies", page),
        ("goto_careers", carrieres),
        ("homepage_fallback", carrieres),
        ("fill_application", formulaires),
        ("detect_ats", segment),
        ("robust_goto", navigateur),
        ("get_sync_playwright", navigateur),
    ],
)
def test_les_noms_de_l_ancien_fichier_restent(nom, module):
    assert getattr(web_nav, nom) is getattr(module, nom)


def test_aucune_furtivite():
    assert web_nav.apply_stealth(None) is False
    assert web_nav.available_engines() in ([], ["playwright"])


@pytest.mark.parametrize("module", SOUS_MODULES)
def test_chaque_sous_module_se_charge_seul(module):
    env = {**os.environ, "PYTHONPATH": str(SRC), "PROFIL_JOBHUNTER": str(EXEMPLE)}
    code = f"import importlib; importlib.import_module('jobhunter.navigation.{module}')"
    r = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
