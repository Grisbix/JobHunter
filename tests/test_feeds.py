"""Each followed company: last attempt, success, incident; suspended or not (sources.feeds)."""

import json

import pytest

from jobhunter.network import INCIDENTS
from jobhunter.sources import common as C
from jobhunter.sources import feeds as F


@pytest.fixture(autouse=True)
def _propre(monkeypatch):
    monkeypatch.setattr(F, "MESURES", {})


def test_cle():
    assert F.cle("workday", "pwc") == "workday:pwc"
    assert F.cle("sfrss", "a.com|b.com") == "sfrss:a.com"


def test_suspendre_et_reprendre():
    cfg: dict = {}
    F.suspendre(cfg, "greenhouse:acme")
    F.suspendre(cfg, "greenhouse:acme")  # no duplicate
    assert F.suspendus(cfg) == {"greenhouse:acme"}
    F.suspendre(cfg, "greenhouse:acme", False)
    assert F.suspendus(cfg) == set()


def test_nouveaux_incidents():
    avant = F.instantane("ats:testfeeds")
    INCIDENTS["ats:testfeeds"]["HTTP 404"] += 2
    INCIDENTS["ats:testfeeds"]["ReadTimeout"] += 1
    assert F.nouveaux("ats:testfeeds", avant) == "HTTP 404 ×2, ReadTimeout"
    assert F.nouveaux("ats:testfeeds", F.instantane("ats:testfeeds")) == ""


def test_un_echec_garde_le_dernier_succes(tmp_path):
    f = tmp_path / F.FICHIER
    F.noter("workday:pwc", 41)
    F.enregistrer(f, "2026-10-20T08:03")
    F.MESURES.clear()
    F.noter("workday:pwc", 0, "HTTP 404")
    F.enregistrer(f, "2026-10-21T08:03")
    e = F.lire(f)["workday:pwc"]
    assert e["succes"] == "2026-10-20T08:03" and e["offres"] == 41
    assert e["incident"] == "HTTP 404" and e["tentative"] == "2026-10-21T08:03"
    F.MESURES.clear()
    F.noter("workday:pwc", 39)
    F.enregistrer(f, "2026-10-22T08:03")
    assert F.lire(f)["workday:pwc"]["incident"] == ""


def test_scan_ats_saute_les_suspendus(tmp_path, monkeypatch):
    from jobhunter.sources import ats

    cfg = tmp_path / "sources_config.json"
    cfg.write_text(json.dumps({"flux_suspendus": ["greenhouse:b"]}), encoding="utf-8")
    monkeypatch.setattr(C, "SOURCES_CFG", cfg)
    monkeypatch.setattr(C, "ATS_SLUGS", {"greenhouse": ["a", "b"]})
    monkeypatch.setattr(ats, "ATS_PAUSE", 0)
    monkeypatch.setattr(ats, "scan_autres", lambda: [])
    vus = []
    monkeypatch.setattr(ats, "fetch_ats", lambda k, s: vus.append(s) or [{"titre": "x"}])
    assert len(ats.scan_ats()) == 1
    assert vus == ["a"]
    assert F.MESURES == {"greenhouse:a": {"offres": 1, "incident": ""}}
