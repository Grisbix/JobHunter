"""Common base of the pytest tests.

The example profile is set here, before the first import of the engine (pytest loads
conftest.py before the test files): `jobhunter.profile` reads the
PROFIL_JOBHUNTER variable when it loads. The tests never read profil/profil.json.
"""

import os
import sys
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parent.parent
SCRIPTS = RACINE / "Scripts"
SRC = RACINE / "src"
EXEMPLE = RACINE / "profile" / "example_finance_esg.json"

os.environ["PROFIL_JOBHUNTER"] = str(EXEMPLE)
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
if str(SRC) not in sys.path:  # without installation (pip install -e .), the package is there
    sys.path.insert(0, str(SRC))


class Reponse:
    """Minimal HTTP response, matching what the engine reads."""

    def __init__(self, corps="", statut=200, entetes=None):
        import json

        self.text = corps if isinstance(corps, str) else json.dumps(corps)
        self.status_code = statut
        self.headers = entetes or {}

    def json(self):
        import json

        return json.loads(self.text)


class FauxReseau:
    """Replaces job_sources._get_borne / _post_borne.

    `routes`: {URL pattern: Reponse | body} — first pattern contained in the URL.
    `sequence(...)`: responses returned in order, the last one then forever.
    All the URLs requested are kept in `appels`.
    """

    def __init__(self):
        self.appels = []
        self._routes = {}
        self._suite = None

    def routes(self, table, statut=200):
        self._routes = {
            m: c if isinstance(c, Reponse) else Reponse(c, statut) for m, c in table.items()
        }
        self._suite = None
        return self

    def sequence(self, *reponses):
        self._suite = list(reponses)
        return self

    def __call__(self, _client, url, **_kw):
        self.appels.append(url)
        if self._suite is not None:
            return self._suite.pop(0) if len(self._suite) > 1 else self._suite[0]
        for motif, rep in self._routes.items():
            if motif in url:
                return rep
        return Reponse("", 404)


@pytest.fixture
def faux_reseau(monkeypatch):
    """No real network call: job_sources goes through the double."""
    from jobhunter import sources as job_sources

    f = FauxReseau()
    monkeypatch.setattr(job_sources, "_get_borne", f)
    monkeypatch.setattr(job_sources, "_post_borne", f)
    job_sources.INCIDENTS.clear()
    yield f
    job_sources.INCIDENTS.clear()


class Horloge:
    """Simulated time: `dormir` advances the clock instead of waiting."""

    def __init__(self):
        self.t = 0.0
        self.pauses = []

    def __call__(self):
        return self.t

    def dormir(self, s):
        self.pauses.append(s)
        self.t += s


@pytest.fixture
def horloge(monkeypatch):
    from jobhunter import sources as job_sources

    h = Horloge()
    monkeypatch.setattr(job_sources, "_horloge", h)
    monkeypatch.setattr(job_sources, "_dormir", h.dormir)
    return h


@pytest.fixture
def file_temporaire(tmp_path, monkeypatch):
    """Throwaway apply_queue.json (and descriptions.json): queue_io writes there."""
    from jobhunter.storage import queue as queue_io

    chemin = tmp_path / "apply_queue.json"
    monkeypatch.setattr(queue_io, "CHEMIN", chemin)
    monkeypatch.setattr(queue_io, "DESCRIPTIONS", tmp_path / "descriptions.json")
    return chemin


@pytest.fixture
def suivi_temporaire(tmp_path, monkeypatch):
    """suivi.json jetable."""
    from jobhunter.storage import applications as suivi_io

    chemin = tmp_path / "suivi.json"
    monkeypatch.setattr(suivi_io, "CHEMIN", chemin)
    return chemin


@pytest.fixture(scope="session")
def navigateur():
    """A single Chromium (headless) for the whole test session."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        yield b
        b.close()


@pytest.fixture
def page(navigateur):
    """A new page per test: no state passes from one test to another."""
    pg = navigateur.new_page()
    yield pg
    pg.close()


@pytest.fixture(scope="session")
def fenetre_tk():
    """A single Tk window for the whole session, transparent but displayed.

    Creating then destroying several Tk roots in one process makes Tcl
    initialisation fail under Windows after a few of them ("Can't find a usable
    init.tcl"), with Python 3.12 as with 3.14. Keyboard focus only exists on
    a displayed window: hence zero opacity rather than withdraw().
    """
    import customtkinter as ctk

    r = ctk.CTk()
    r.attributes("-alpha", 0.0)
    r.geometry("300x300+0+0")
    yield r
    r.destroy()


@pytest.fixture
def racine_tk(fenetre_tk):
    """La fenêtre de session, vidée après chaque test."""
    yield fenetre_tk
    for w in fenetre_tk.winfo_children():
        w.destroy()


@pytest.fixture(autouse=True)
def _compteur_api_jetable(tmp_path_factory, monkeypatch):
    """The shared API call counter (sources.quota) in a throwaway folder, for every test.

    Otherwise each collection test counts its fake calls in the repository's data folder,
    and after a few runs the daily ceiling stops the sources the next tests expect.
    """
    from jobhunter.sources import quota

    d = tmp_path_factory.mktemp("cles")
    monkeypatch.setattr(quota, "_fichier", lambda: d / quota.FICHIER)
