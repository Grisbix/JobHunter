"""Le paquet jobhunter.documents (phase 3.5) : facades et noms conserves.

- tailor_application EST jobhunter.documents ; message_offre et cv_auto sont ses modules ;
- les noms de l'ancien fichier unique restent lisibles (tailor_cv, titre_poste, to_pdf...) ;
- le message court se charge sans tailor_application.
"""

import json
import os
import subprocess
import sys

import pytest
from conftest import EXEMPLE, SRC

import cv_auto
import jobhunter.documents as paquet
import message_offre
import tailor_application
from jobhunter.documents import commun, cv, lettre, llm, message, rendu
from jobhunter.documents import cv_auto as cv_auto_paquet


@pytest.mark.parametrize(
    ("facade", "module"),
    [(tailor_application, paquet), (message_offre, message), (cv_auto, cv_auto_paquet)],
    ids=["tailor_application", "message_offre", "cv_auto"],
)
def test_facade_est_le_module_du_paquet(facade, module):
    assert facade is module


@pytest.mark.parametrize(
    ("nom", "module"),
    [
        ("tailor_cv", cv),
        ("cv_une_page", cv),
        ("tailor_letter", lettre),
        ("salutation", lettre),
        ("titre_poste", commun),
        ("match_skills", commun),
        ("llm_rewrite", llm),
        ("to_pdf", rendu),
        ("SOFFICE", rendu),
    ],
)
def test_les_noms_de_l_ancien_fichier_restent(nom, module):
    assert getattr(tailor_application, nom) is getattr(module, nom)


def test_une_affectation_va_au_proprietaire(monkeypatch):
    monkeypatch.setattr(tailor_application, "SOFFICE", [])
    assert rendu.SOFFICE == []
    assert rendu.to_pdf(None) is None  # aucun LibreOffice : pas de PDF, pas d'erreur


def test_le_message_se_charge_sans_tailor_application():
    env = {**os.environ, "PYTHONPATH": str(SRC), "PROFIL_JOBHUNTER": str(EXEMPLE)}
    code = "import jobhunter.documents.message, json, sys; print(json.dumps(sorted(sys.modules)))"
    r = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert not set(json.loads(r.stdout)) & {"tailor_application", "message_offre", "jutil"}
