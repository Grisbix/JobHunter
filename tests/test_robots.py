"""robots.txt: a byte-order mark no longer hides the rules; the read is bounded."""

import types

import pytest

from jobhunter import network
from jobhunter.programs import scrape_jobs as sj

REGLES = "User-agent: *\nDisallow: /jobs\n"


@pytest.mark.parametrize("texte", [REGLES, "﻿" + REGLES], ids=["sans BOM", "avec BOM"])
def test_disallow_respecte_meme_avec_bom(texte):
    rp = sj.robots_lu(200, texte)
    assert not rp.can_fetch(sj.ROBOTS_UA, "https://x.com/jobs/1")
    assert rp.can_fetch(sj.ROBOTS_UA, "https://x.com/about")


def test_codes_comme_robotparser():
    assert not sj.robots_lu(403, "").can_fetch(sj.ROBOTS_UA, "https://x.com/a")
    assert sj.robots_lu(404, "").can_fetch(sj.ROBOTS_UA, "https://x.com/a")


@pytest.fixture
def sans_cache(monkeypatch):
    monkeypatch.setattr(sj, "_ROBOTS_CACHE", {})


def test_lu_par_get_borne_une_fois_par_hote(monkeypatch, sans_cache):
    appels = []

    def get_borne(envoi, url, **kw):
        appels.append((url, kw["total"]))
        return types.SimpleNamespace(status_code=200, content=("﻿" + REGLES).encode())

    monkeypatch.setattr(network, "get_borne", get_borne)
    assert not sj.robots_autorise("https://x.com/jobs/1")
    assert sj.robots_autorise("https://x.com/about")
    assert appels == [("https://x.com/robots.txt", 30)]


def test_injoignable_vaut_permission(monkeypatch, sans_cache):
    def get_borne(envoi, url, **kw):
        raise TimeoutError("lent")

    monkeypatch.setattr(network, "get_borne", get_borne)
    assert sj.robots_autorise("https://lent.example/jobs/1")
