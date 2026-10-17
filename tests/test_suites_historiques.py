"""Les suites historiques de Scripts/, lancees par pytest.

Etape immediate de la phase 2 du plan : chaque `Scripts/test_*.py` reste un
programme autonome (il compte ses cas et sort en code non nul sur un echec) ;
pytest les lance une par une, dans un processus neuf, depuis Scripts/. Elles
seront converties en vrais tests pytest une par une, et retirees d'ici a mesure.

    pytest -q                      # toutes
    pytest -q -k scoring           # une seule
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "Scripts"

# Sans reseau, toutes. test_live_nav et test_acces_sites sortent sur le web : exclus.
SUITES = [
    "test_sources",
    "test_patterns",
    "test_scoring",
    "test_titres",
    "test_appel",
    "test_lettre",
    "test_contrats",
    "test_queue_io",
    "test_liens",
    "test_suivi",
    "test_zones",
    "test_audit_dispo",
    "test_cv_auto",
    "test_agregateurs",
    "test_glassdoor_refus",
    "test_rejets_tri",
    "test_tri_file",
    "test_site_final",
    "test_metriques_hebdo",
    "test_lecteurs_ats",
    "test_web_nav_mock",
    "test_mise_a_jour",
    "test_relances",
    "test_web_nav",
    "test_app_design",
    "test_indeed",
    "test_acces",
]


@pytest.mark.parametrize("suite", SUITES)
def test_suite(suite):
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    r = subprocess.run(
        [sys.executable, f"{suite}.py"],
        cwd=SCRIPTS,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=600,
    )
    sortie = (r.stdout + r.stderr).strip().splitlines()
    assert r.returncode == 0, "\n".join(sortie[-40:])


def test_toutes_les_suites_sont_listees():
    """Une suite ajoutee dans Scripts/ sans etre listee ici ne tournerait jamais."""
    hors_ligne = {"test_live_nav", "test_acces_sites"}
    presentes = {p.stem for p in SCRIPTS.glob("test_*.py")} - hors_ligne
    assert presentes == set(SUITES)
