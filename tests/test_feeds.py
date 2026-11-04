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


# ── in parallel: one request at a time per domain, same offers, own incidents ──
@pytest.mark.parametrize(
    ("kind", "cle", "attendu"),
    [
        ("greenhouse", "anthropic", "greenhouse"),
        ("ashby", "checkout.com", "ashby"),
        ("workable", "j", "workable"),
        ("sfrss", "careers.ey.com", "ey.com"),
        ("oracle", "estm.fa.em2.oraclecloud.com", "oraclecloud.com"),
        ("sitemap", "https://www.kbc.be/jobs/en.sitemap.xml", "kbc.be"),
        ("phenom", "jobs.bureauveritas.com/gb/en", "bureauveritas.com"),
        ("sfrss", "a.ey.com|b.ey.com", "ey.com"),
    ],
)
def test_domaine(kind, cle, attendu):
    from jobhunter.sources import ats

    assert ats.domaine(kind, cle) == attendu


def test_en_chaines_un_domaine_a_la_fois(monkeypatch):
    import threading
    import time

    from jobhunter.sources import ats

    monkeypatch.setattr(ats, "ATS_PAUSE", 0)
    en_cours: dict[str, int] = {}
    pic: dict[str, int] = {}
    verrou = threading.Lock()

    def lire(dom, n):
        with verrou:
            en_cours[dom] = en_cours.get(dom, 0) + 1
            pic[dom] = max(pic.get(dom, 0), en_cours[dom])
        time.sleep(0.01)
        with verrou:
            en_cours[dom] -= 1
        return [n]

    taches = [(d, lire, (d, i)) for i, d in enumerate(["a", "b", "a", "c", "a", "b"])]
    res = ats._en_chaines(taches)
    assert [r[0] for r in res] == [[0], [1], [2], [3], [4], [5]]
    assert pic == {"a": 1, "b": 1, "c": 1}


def test_en_chaines_incidents_par_flux(monkeypatch):
    from jobhunter.sources import ats

    monkeypatch.setattr(ats, "ATS_PAUSE", 0)

    def lire(n):
        for _ in range(n):
            ats._incident("testchaines", "HTTP 429")
        return []

    res = ats._en_chaines([("x", lire, (2,)), ("y", lire, (0,)), ("z", lire, (1,))])
    assert [r[1] for r in res] == ["HTTP 429 ×2", "", "HTTP 429"]


# ── silent feeds (3.15): a company whose page moved does not fail loudly ──────────
def _muet(e, jour="2026-11-30T08:00"):
    import datetime

    return F.muet(e, datetime.datetime.fromisoformat(jour))


def test_muet_jamais_avant_trente_jours_de_suivi():
    assert _muet({"premier": "2026-11-10T08:00", "succes": "2026-11-30T08:00", "offres": 0}) == ""


def test_muet_les_trois_cas():
    base = {"premier": "2026-09-01T08:00"}
    assert (
        _muet({**base, "succes": "2026-10-01T08:00", "incident": "HTTP 404"})
        == "en échec depuis 60 j"
    )
    assert _muet({**base, "incident": "HTTP 403"}) == "jamais réussie"
    vide = {
        **base,
        "succes": "2026-11-30T08:00",
        "offres": 0,
        "brut": 0,
        "brut_le": "2026-10-20T08:00",
    }
    assert _muet(vide) == "page vide depuis 41 j"
    rien = {
        **base,
        "succes": "2026-11-30T08:00",
        "offres": 0,
        "brut": 12,
        "brut_le": "2026-11-30T08:00",
    }
    assert _muet(rien) == "rien pour ton profil depuis 90 j"
    actif = {**rien, "retenues_le": "2026-11-20T08:00"}
    assert _muet(actif) == ""


def test_enregistrer_date_les_resultats(tmp_path):
    p = tmp_path / F.FICHIER
    p.write_text('{"ashby:x": {"succes": "2026-10-01T08:00", "offres": 3}}', encoding="utf-8")
    F.brut("ashby", "x", 0)
    F.noter("ashby:x", 0)
    F.enregistrer(p, "2026-10-02T08:00")
    e = json.loads(p.read_text(encoding="utf-8"))["ashby:x"]
    # the old success with offers dates the last offers kept; the feed is followed from now
    assert e["retenues_le"] == "2026-10-01T08:00" and e["premier"] == "2026-10-02T08:00"
    assert e["brut"] == 0 and "brut_le" not in e
    assert F.muets({"ashby:x": e}, {"ashby:x"}) == {}
