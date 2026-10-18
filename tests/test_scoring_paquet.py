"""Le paquet jobhunter.scoring (phase 3.3) : facades, cycle casse, noms conserves.

- ats_match, langue, zones, tri_file, chemins SONT les modules du paquet (alias) ;
- le scoring se charge sans tailor_application : le cycle ats_match <-> tailor est casse ;
- les noms historiques restent importables (tailor_application.cv_variant_key,
  jutil.sans_accent...) : message_offre et les tests s'en servent.
"""

import json
import os
import subprocess
import sys

import pytest
from conftest import EXEMPLE, SRC

import ats_match
import chemins
import jutil
import langue
import tailor_application
import tri_file
import zones
from jobhunter import chemins as chemins_paquet
from jobhunter import texte
from jobhunter.scoring import fit, lexique, tri
from jobhunter.scoring import langue as langue_paquet
from jobhunter.scoring import zones as zones_paquet


@pytest.mark.parametrize(
    ("facade", "module"),
    [
        (ats_match, fit),
        (langue, langue_paquet),
        (zones, zones_paquet),
        (tri_file, tri),
        (chemins, chemins_paquet),
    ],
    ids=["ats_match", "langue", "zones", "tri_file", "chemins"],
)
def test_facade_est_le_module_du_paquet(facade, module):
    assert facade is module


def _modules_charges(code):
    env = {**os.environ, "PYTHONPATH": str(SRC), "PROFIL_JOBHUNTER": str(EXEMPLE)}
    r = subprocess.run(
        [sys.executable, "-c", code + "; import json, sys; print(json.dumps(sorted(sys.modules)))"],
        env=env,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr
    return set(json.loads(r.stdout))


def test_le_scoring_se_charge_sans_tailor_application():
    charges = _modules_charges("import jobhunter.scoring.fit, jobhunter.scoring.langue")
    assert not charges & {"tailor_application", "ats_match", "jutil", "queue_io"}


def test_le_lexique_ne_depend_que_du_profil():
    charges = {
        m for m in _modules_charges("import jobhunter.scoring.lexique") if m.startswith("jobhunter")
    }
    assert charges <= {
        "jobhunter",
        "jobhunter.racine",
        "jobhunter.profil",
        "jobhunter.scoring",
        "jobhunter.scoring.lexique",
    }


@pytest.mark.parametrize(
    "nom",
    [
        "cv_variant_key",
        "has_skill",
        "SKILL_LEX",
        "CV_VARIANT",
        "CV_VARIANT_EN",
        "_DOMAINES",
        "_COMP",
    ],
)
def test_tailor_application_garde_les_noms_du_lexique(nom):
    assert getattr(tailor_application, nom) is getattr(lexique, nom)


@pytest.mark.parametrize("nom", ["sans_accent", "cle", "verifier_motifs"])
def test_jutil_garde_les_noms_du_texte(nom):
    assert getattr(jutil, nom) is getattr(texte, nom)


def test_fit_lit_les_modeles_de_cv_par_chemins():
    assert fit.CV_ATS == chemins_paquet.CV_MODELES
