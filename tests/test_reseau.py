"""jobhunter.network: requests bounded in TOTAL duration and in size (phase 3.2).

Until now these functions had no direct test: the suites always replaced them
with doubles. We check their guarantees with a fake httpx stream, without
network: a server that trickles its bytes is cut at the total duration, a body
too big is refused, the returned response is complete and without double decompression.
"""

import io

import httpx
import pytest

from jobhunter import network as reseau
from jobhunter import profile as profil
from jobhunter import profile as profil_paquet
from jobhunter import sources as job_sources


class FluxLent:
    """Fake `envoi`: .stream() returns blocks, advancing a simulated clock."""

    def __init__(self, blocs, horloge, par_bloc=0.0, statut=200, entetes=None):
        self.blocs, self.horloge, self.par_bloc = blocs, horloge, par_bloc
        self.statut, self.entetes = statut, entetes or {}
        self.appels = []

    def stream(self, methode, url, **kw):
        self.appels.append((methode, url, kw))
        flux = self

        class _Rep:
            status_code = flux.statut
            headers = httpx.Headers(flux.entetes)
            request = httpx.Request(methode, url)

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def iter_bytes(self):
                for b in flux.blocs:
                    flux.horloge[0] += flux.par_bloc
                    yield b

        return _Rep()


@pytest.fixture
def horloge(monkeypatch):
    t = [0.0]
    monkeypatch.setattr(reseau.time, "time", lambda: t[0])
    return t


def test_reponse_complete(horloge):
    r = reseau.get_borne(FluxLent([b'{"a": ', b"1}"], horloge), "https://x/y")
    assert (r.status_code, r.json()) == (200, {"a": 1})


def test_coupe_a_la_duree_totale(horloge):
    """One byte every 19 s: each packet respects the timeout, not the whole."""
    lent = FluxLent([b"x"] * 100, horloge, par_bloc=19)
    with pytest.raises(httpx.TimeoutException, match="plus de 60 s"):
        reseau.get_borne(lent, "https://lent", timeout=20)


def test_duree_totale_par_defaut_trois_fois_le_delai(horloge):
    lent = FluxLent([b"x"] * 100, horloge, par_bloc=10)
    with pytest.raises(httpx.TimeoutException, match="plus de 90 s"):
        reseau.get_borne(lent, "https://lent", timeout=30)


def test_corps_trop_gros_refuse(horloge):
    with pytest.raises(httpx.TimeoutException, match="octets"):
        reseau.req_borne(
            FluxLent([b"x" * 600] * 2, horloge), "GET", "https://gros", max_octets=1000
        )


def test_pas_de_double_decompression(horloge):
    """iter_bytes has already decompressed: the response must no longer announce gzip."""
    r = reseau.get_borne(
        FluxLent(
            [b"ok"],
            horloge,
            entetes={"content-encoding": "gzip", "content-length": "999", "x-garde": "1"},
        ),
        "https://z",
    )
    assert "content-encoding" not in r.headers and r.headers["x-garde"] == "1"
    assert r.text == "ok"


def test_delai_par_defaut_vingt_secondes(horloge):
    flux = FluxLent([b"ok"], horloge)
    reseau.post_borne(flux, "https://p", json={"k": 1})
    methode, _, kw = flux.appels[0]
    assert (methode, kw["timeout"], kw["json"]) == ("POST", 20, {"k": 1})


def test_le_module_httpx_passe_par_le_client_partage(monkeypatch, horloge):
    flux = FluxLent([b"ok"], horloge)
    monkeypatch.setattr(reseau, "_CLIENT", flux)
    reseau.get_borne(httpx, "https://partage")
    assert flux.appels and flux.appels[0][1] == "https://partage"


def test_client_partage_unique(monkeypatch):
    monkeypatch.setattr(reseau, "_CLIENT", None)
    a = reseau.client_partage()
    try:
        assert reseau.client_partage() is a
    finally:
        a.close()


class LecteurLent(io.RawIOBase):
    def __init__(self, horloge, n=1000, par_bloc=1.0):
        self.horloge, self.n, self.par_bloc = horloge, n, par_bloc

    def read1(self, taille=-1):
        if not self.n:
            return b""
        self.n -= 1
        self.horloge[0] += self.par_bloc
        return b"x"


def test_lire_borne_complet(horloge):
    assert reseau.lire_borne(LecteurLent(horloge, n=5, par_bloc=0)) == b"xxxxx"


def test_lire_borne_coupe_a_la_duree(horloge):
    with pytest.raises(TimeoutError):
        reseau.lire_borne(LecteurLent(horloge), total=3)


# ── job_sources keeps its old names ─────────────────────────────────────────
def test_job_sources_reexporte_le_reseau():
    assert (
        job_sources._get_borne,
        job_sources._post_borne,
        job_sources._lire_borne,
        job_sources._client_partage,
    ) == (reseau.get_borne, reseau.post_borne, reseau.lire_borne, reseau.client_partage)


# ── profile: the facade is the package's module ─────────────────────────────────
def test_profil_est_le_module_du_paquet():
    assert profil is profil_paquet


def test_profil_lit_le_profil_d_exemple():
    assert profil.FICHIER.name == "exemple_finance_esg.json" and profil.get("langues_parlees")


def test_incidents_un_seul_compteur_porte_par_le_reseau():
    from jobhunter.sources import common as commun

    assert commun.INCIDENTS is reseau.INCIDENTS
    reseau.INCIDENTS.clear()
    try:
        reseau.INCIDENTS.noter("linkedin_http", 429)
        reseau.INCIDENTS["linkedin_http"][429] += 1
        reseau.INCIDENTS.noter("apec", "HTTP 403")
        assert commun.incidents_resume() == ["  ⚠ apec : HTTP 403×1", "  ⚠ linkedin_http : 429×2"]
    finally:
        reseau.INCIDENTS.clear()
