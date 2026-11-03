"""Test one API access: one minimal request, sorted, nothing secret shown (sources.connexion)."""

import json
from types import SimpleNamespace

import pytest

from jobhunter import root
from jobhunter.sources import common as C
from jobhunter.sources import connexion as X
from jobhunter.sources import francetravail as FT
from jobhunter.sources import quota as Q

SECRET = "CLE-SECRETE-123"


@pytest.fixture
def cles(tmp_path, monkeypatch):
    d = tmp_path / "data"
    d.mkdir()
    monkeypatch.setattr(root, "dossier_cles", lambda: d)
    monkeypatch.setattr(Q, "_fichier", lambda: d / Q.FICHIER)
    (d / "adzuna.json").write_text(json.dumps({"app_id": "id", "app_key": SECRET}))
    (d / "jooble.json").write_text(json.dumps({"key": SECRET}))
    (d / "francetravail.json").write_text(json.dumps({"client_id": "a", "client_secret": SECRET}))
    return d


def repondre(monkeypatch, code=200, erreur=None):
    def faux(_httpx, url, **kw):
        if erreur:
            raise erreur(f"GET {url}?app_key={SECRET}")
        return SimpleNamespace(status_code=code)

    monkeypatch.setattr(C, "_get_borne", faux)
    monkeypatch.setattr(C, "_post_borne", faux)


@pytest.mark.parametrize(
    ("code", "etat"),
    [(200, "ok"), (401, "refusee"), (403, "refusee"), (429, "quota"), (500, "panne")],
)
@pytest.mark.parametrize("nom", ["adzuna", "jooble"])
def test_classement(cles, monkeypatch, nom, code, etat):
    repondre(monkeypatch, code)
    assert X.tester(nom).etat == etat


def test_cle_absente(cles, monkeypatch):
    (cles / "jooble.json").unlink()
    repondre(monkeypatch, 200)
    assert X.tester("jooble").etat == "absente"


def test_reseau_sans_jamais_montrer_le_message(cles, monkeypatch):
    repondre(monkeypatch, erreur=ConnectionError)
    r = X.tester("adzuna")
    assert r.etat == "reseau" and r.detail == "ConnectionError"
    assert SECRET not in repr(r)


def test_compte_dans_le_quota_et_s_arrete(cles, monkeypatch):
    (cles / "sources_config.json").write_text(json.dumps({"quotas_api": {"adzuna": 1}}))
    repondre(monkeypatch, 200)
    assert X.tester("adzuna").etat == "ok"
    assert X.tester("adzuna").etat == "quota"


def test_france_travail_jeton_refuse(cles, monkeypatch):
    monkeypatch.setattr(FT, "_ft_token", lambda: None)
    assert X.tester("francetravail") == X.Resultat("refusee", "jeton refusé")


def test_france_travail_ok(cles, monkeypatch):
    monkeypatch.setattr(FT, "_ft_token", lambda: "jeton")
    repondre(monkeypatch, 206)
    assert X.tester("francetravail").etat == "ok"


def test_jeton_refuse_compte_comme_refus(cles, monkeypatch):
    # 20/10 -> 03/11/2026: a token answering 400 read « rien à prendre » every day.
    from jobhunter.sources import source_yield as R

    monkeypatch.setattr(FT, "FT_CFG", cles / "francetravail.json")
    repondre(monkeypatch, 400)
    C.INCIDENTS.clear()
    assert FT._ft_token() is None
    incidents = dict(C.INCIDENTS["francetravail"])
    assert incidents == {"jeton refusé HTTP 400": 1}
    assert R.verdict(0, incidents) == R.REFUSE
    C.INCIDENTS.clear()


@pytest.mark.parametrize(
    ("erreur", "conseil"),
    [("invalid_scope", "Offres d'emploi v2"), ("invalid_client", "recopie"), ("", "vérifie")],
)
def test_jeton_refuse_dit_quoi_faire(erreur, conseil):
    class R:
        def json(self):
            return {"error": erreur}

    assert conseil in FT._cause(R())
