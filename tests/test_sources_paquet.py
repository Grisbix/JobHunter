"""The jobhunter.sources package (phase 3.4): facade, routing of assignments, cycle broken.

- `job_sources` IS jobhunter.sources (alias) and sees the names of all submodules;
- an assignment on the facade goes to the owning submodule, which the others read;
- `unittest.mock.patch` comes out without erasing the submodule's name;
- the collection loads without scrape_jobs, and classify_domaine lives in the scoring.
"""

import json
import os
import subprocess
import sys
from unittest import mock

import pytest
from conftest import EXEMPLE, SRC

import jobhunter.sources as paquet
from jobhunter import sources as job_sources
from jobhunter.programs import scrape_jobs
from jobhunter.scoring import domains as domaines
from jobhunter.sources import cli, indeed, linkedin
from jobhunter.sources import common as commun


def test_facade_est_le_paquet():
    assert job_sources is paquet


@pytest.mark.parametrize(
    ("nom", "module"),
    [
        ("title_ok", commun),
        ("scan_linkedin", linkedin),
        ("INDEED_LIEUX", indeed),
        ("main", cli),
    ],
)
def test_la_facade_voit_les_noms_des_sous_modules(nom, module):
    assert getattr(job_sources, nom) is getattr(module, nom)


def test_une_affectation_va_au_proprietaire(monkeypatch):
    monkeypatch.setattr(job_sources, "KEYWORDS", ["test"])
    assert commun.KEYWORDS == ["test"]
    assert "KEYWORDS" not in vars(linkedin)  # linkedin lit _commun.KEYWORDS


def test_mock_patch_restaure_le_nom():
    origine = commun.contrats_exclus
    with mock.patch.object(job_sources, "contrats_exclus", return_value=set()):
        assert commun.contrats_exclus() == set()
    assert commun.contrats_exclus is origine
    assert "contrats_exclus" not in vars(paquet)


def test_monde_reglable_par_la_facade(monkeypatch):
    monkeypatch.setattr(job_sources, "MONDE", False)
    assert commun.MONDE is False
    assert commun.en_france("New York, NY") is False


def test_scrape_jobs_garde_les_noms_du_domaine():
    assert scrape_jobs.classify_domaine is domaines.classify_domaine
    assert scrape_jobs.matches_esg_finance is domaines.matches_esg_finance


def test_la_collecte_se_charge_sans_scrape_jobs():
    env = {**os.environ, "PYTHONPATH": str(SRC), "PROFIL_JOBHUNTER": str(EXEMPLE)}
    code = "import jobhunter.sources, json, sys; print(json.dumps(sorted(sys.modules)))"
    r = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    charges = set(json.loads(r.stdout))
    assert not charges & {"scrape_jobs", "job_sources", "tailor_application", "jutil", "queue_io"}
