"""The jobhunter.navigation package (phase 3.6): facades, names kept, standalone submodules.

- web_nav IS jobhunter.navigation, site_strategies IS navigation.strategies;
- the names of the old single file remain readable (dismiss_cookies, fill_application...);
- each submodule loads alone: the split left no import cycle.
"""

import os
import subprocess
import sys

import pytest
from conftest import EXEMPLE, SRC

import jobhunter.navigation as paquet
from jobhunter import navigation as web_nav
from jobhunter.navigation import carrieres, formulaires, navigateur, page, segment, strategies
from jobhunter.navigation import strategies as site_strategies

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
