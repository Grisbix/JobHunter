"""Calls to the shared API keys, counted for the day across profiles (sources.quota)."""

import json
from types import SimpleNamespace

import pytest

from jobhunter import root
from jobhunter.sources import aggregators as A
from jobhunter.sources import quota as Q


@pytest.fixture
def cles(tmp_path, monkeypatch):
    d = tmp_path / "data"
    d.mkdir()
    monkeypatch.setattr(root, "dossier_cles", lambda: d)
    monkeypatch.setattr(Q, "_fichier", lambda: d / Q.FICHIER)
    return d


def test_compte_et_s_arrete_au_plafond(cles):
    (cles / "sources_config.json").write_text(json.dumps({"quotas_api": {"adzuna": 2}}))
    assert Q.plafond("adzuna") == 2
    assert Q.reserver("adzuna") and Q.reserver("adzuna")
    assert not Q.reserver("adzuna")
    assert Q.usage("adzuna") == 2


def test_sans_plafond_compte_seulement(cles):
    for _ in range(5):
        assert Q.reserver("jooble")
    assert Q.usage("jooble") == 5 and Q.plafond("jooble") is None


def test_le_compteur_repart_chaque_jour(cles):
    (cles / Q.FICHIER).write_text(json.dumps({"2020-01-01": {"adzuna": 999}}))
    assert Q.reserver("adzuna") and Q.usage("adzuna") == 1
    assert "2020-01-01" not in json.loads((cles / Q.FICHIER).read_text())


def test_compteur_illisible_n_arrete_pas_la_collecte(cles):
    (cles / Q.FICHIER).write_text("{abîmé")
    assert Q.reserver("adzuna")


def test_adzuna_s_arrete_au_quota(cles, monkeypatch):
    (cles / "adzuna.json").write_text(json.dumps({"app_id": "x", "app_key": "y"}))
    (cles / "sources_config.json").write_text(json.dumps({"quotas_api": {"adzuna": 3}}))
    monkeypatch.setattr(A, "ADZUNA_CFG", cles / "adzuna.json")
    monkeypatch.setattr(A, "AGREG_PAUSE", 0)
    appels = []

    def get(_httpx, url, **kw):
        appels.append(url)
        return SimpleNamespace(status_code=200, json=lambda: {"results": []})

    monkeypatch.setattr(A._commun, "_get_borne", get)
    A.INCIDENTS["adzuna"].clear()
    A.scan_adzuna()
    assert len(appels) == 3
    assert A.INCIDENTS["adzuna"]["quota du jour"] == 1
