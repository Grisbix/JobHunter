"""The jobhunter.scoring package (phase 3.3): facades, cycle broken, names kept.

- ats_match, langue, zones, tri_file, chemins ARE the package's modules (aliases);
- the scoring loads without tailor_application: the ats_match <-> tailor cycle is broken;
- the historical names remain importable (tailor_application.cv_variant_key,
  jutil.sans_accent...): message_offre and the tests use them.
"""

import json
import os
import subprocess
import sys

import pytest
from conftest import EXEMPLE, SRC

from jobhunter import documents as tailor_application
from jobhunter import paths as chemins
from jobhunter import paths as chemins_paquet
from jobhunter import text as texte
from jobhunter.programs import util as jutil
from jobhunter.scoring import fit, zones
from jobhunter.scoring import fit as ats_match
from jobhunter.scoring import language as langue
from jobhunter.scoring import language as langue_paquet
from jobhunter.scoring import lexicon as lexique
from jobhunter.scoring import sorting as tri
from jobhunter.scoring import sorting as tri_file
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
    charges = _modules_charges("import jobhunter.scoring.fit, jobhunter.scoring.language")
    assert not charges & {"tailor_application", "ats_match", "jutil", "queue_io"}


def test_le_lexique_ne_depend_que_du_profil():
    charges = {
        m for m in _modules_charges("import jobhunter.scoring.lexicon") if m.startswith("jobhunter")
    }
    assert charges <= {
        "jobhunter",
        "jobhunter._old_names",
        "jobhunter.root",
        "jobhunter.profile",
        "jobhunter.lazy",
        "jobhunter.scoring",
        "jobhunter.scoring.lexicon",
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
