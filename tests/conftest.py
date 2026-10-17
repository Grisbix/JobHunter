"""Socle commun des tests pytest.

Le moteur lit le profil AU CHARGEMENT de ses modules : le profil d'exemple doit
etre fixe avant le premier import, donc ici, au niveau du module (pytest charge
conftest.py avant les fichiers de test). Les tests ne lisent jamais
profil/profil.json.
"""

import os
import sys
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parent.parent
SCRIPTS = RACINE / "Scripts"
EXEMPLE = RACINE / "profil" / "exemple_finance_esg.json"

os.environ["PROFIL_JOBHUNTER"] = str(EXEMPLE)
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


class Reponse:
    """Reponse HTTP minimale, au contrat de ce que lit le moteur."""

    def __init__(self, corps="", statut=200, entetes=None):
        import json

        self.text = corps if isinstance(corps, str) else json.dumps(corps)
        self.status_code = statut
        self.headers = entetes or {}

    def json(self):
        import json

        return json.loads(self.text)


class FauxReseau:
    """Remplace job_sources._get_borne / _post_borne.

    `routes` : {motif d'URL: Reponse | corps} — premier motif contenu dans l'URL.
    `sequence(...)` : reponses rendues dans l'ordre, la derniere ensuite pour toujours.
    Toutes les URL demandees sont gardees dans `appels`.
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
    """Aucun appel reseau reel : job_sources passe par la doublure."""
    import job_sources

    f = FauxReseau()
    monkeypatch.setattr(job_sources, "_get_borne", f)
    monkeypatch.setattr(job_sources, "_post_borne", f)
    job_sources.INCIDENTS.clear()
    yield f
    job_sources.INCIDENTS.clear()


class Horloge:
    """Temps simule : `dormir` avance l'horloge au lieu d'attendre."""

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
    import job_sources

    h = Horloge()
    monkeypatch.setattr(job_sources, "_horloge", h)
    monkeypatch.setattr(job_sources, "_dormir", h.dormir)
    return h


@pytest.fixture
def file_temporaire(tmp_path, monkeypatch):
    """apply_queue.json (et descriptions.json) jetables : queue_io y ecrit."""
    import queue_io

    chemin = tmp_path / "apply_queue.json"
    monkeypatch.setattr(queue_io, "CHEMIN", chemin)
    monkeypatch.setattr(queue_io, "DESCRIPTIONS", tmp_path / "descriptions.json")
    return chemin


@pytest.fixture
def suivi_temporaire(tmp_path, monkeypatch):
    """suivi.json jetable."""
    import suivi_io

    chemin = tmp_path / "suivi.json"
    monkeypatch.setattr(suivi_io, "CHEMIN", chemin)
    return chemin
