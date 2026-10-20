"""Every panel of the window, opened as the user opens it, with no console.

The app is launched by pythonw (JobHunter.pyw, the installed shortcut): no console,
`sys.stdout` and `sys.stderr` are None. A panel that fails there shows nothing and
says nothing. Importing the modules without a console is already tested
(test_sources_sans_console.py); here each sidebar button is clicked, and the panel
must be displayed with no internal failure — then again with its files damaged
(unreadable JSON, unreadable log, queue that cannot be read): the panel still opens
and the next button still works.

Idea of the GitHub sweep of 20/10 (Thonny, Textual: test what the user sees, not only
the import).
"""

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

os.environ["JOBHUNTER_SANS_FOND"] = "1"
os.environ.pop("JOBHUNTER_ACTION", None)
import jobhunter.app as ui  # noqa: E402
from jobhunter.app import common as _commun  # noqa: E402
from jobhunter.app import language as _langue  # noqa: E402
from jobhunter.app import panels as _panneaux  # noqa: E402
from jobhunter.sources import common as _sources_commun  # noqa: E402

BOUTONS = ["offres", "cv", "entreprises", "sites", "stats", "acces"]
# The frame each button shows (None: the CV viewer, held in app.viewer).
CADRES = {
    "offres": "dash",
    "cv": None,
    "entreprises": "companies",
    "sites": "sources",
    "stats": "stats",
    "acces": "acces",
}
OFFRE = {
    "entreprise": "Test",
    "poste": "Analyste ESG",
    "fit": 8,
    "statut": "Scan 2026-10-01",
    "url": "https://example.invalid/offre",
    "source": "greenhouse:test",
}


def _cadre(app, cle):
    nom = CADRES[cle]
    if nom is None:
        return app.viewer
    return app.dash if nom == "dash" else app._panels[nom]


@pytest.fixture
def sans_console(monkeypatch):
    """pythonw: no standard streams at all."""
    monkeypatch.setattr(sys, "stdout", None)
    monkeypatch.setattr(sys, "stderr", None)


def _ouvrir(racine, dossier: Path, charger_file):
    """The App on a throwaway data folder; returns (app, recorded failures)."""
    pannes: list[str] = []
    patches = [
        patch.object(ui.queue_io, "charger", charger_file),
        patch.object(ui.suivi_io, "charger", return_value={}),
        patch.object(ui, "SUIVI", dossier / "suivi.json"),
        patch.object(ui, "COMPTES", dossier / "comptes.json"),
        patch.object(ui, "PROFILE", dossier / "profil.json"),
        patch.object(_commun, "SUIVI", dossier / "suivi.json"),
        patch.object(_panneaux, "SCRIPTS", dossier),
        patch.object(_panneaux, "QUEUE", dossier / "apply_queue.json"),
        patch.object(_sources_commun, "SOURCES_CFG", dossier / "sources_config.json"),
        patch.object(ui.App, "JOURNAL", dossier / "_logs" / "app_erreurs.log"),
        patch.object(
            ui.App,
            "_journal_panne",
            lambda self, contexte, exc=None: pannes.append(f"{contexte}: {exc!r}"),
        ),
    ]
    for p in patches:
        p.start()
    racine.withdraw()
    with patch.object(racine, "state"):
        app = ui.App(racine)
    racine.geometry("1080x680")
    racine.deiconify()
    racine.update()
    return app, pannes, patches


def _parcourir(app, racine, pannes):
    """Clicks each sidebar button in turn; each panel must be displayed."""
    for cle in [*BOUTONS, "offres"]:
        app._nav[cle].invoke()
        racine.update()
        cadre = _cadre(app, cle)
        assert cadre is not None and cadre.winfo_ismapped(), f"panneau {cle} non affiché"
        assert not pannes, f"panne interne en ouvrant {cle} : {pannes}"


def _fermer(racine, patches):
    racine.withdraw()
    for p in reversed(patches):
        p.stop()


@pytest.mark.parametrize("code", _langue.LANGUES)
def test_chaque_panneau_s_affiche_sans_console(
    racine_tk, tmp_path, sans_console, code, monkeypatch
):
    """In each interface language: a translation that breaks a panel shows up here."""
    monkeypatch.setattr(_langue, "LANGUE", code)
    app, pannes, patches = _ouvrir(racine_tk, tmp_path, lambda *a, **k: [dict(OFFRE)])
    try:
        _parcourir(app, racine_tk, pannes)
    finally:
        _fermer(racine_tk, patches)


def _abimer(dossier: Path):
    """Every file a panel reads, damaged as a crash mid-write would leave it."""
    for nom in ("comptes.json", "sources_config.json", "suivi.json", "adzuna.json"):
        (dossier / nom).write_text('{"tronque": ', encoding="utf-8")
    (dossier / "_rendement.jsonl").write_bytes(b'{"source": "linkedin", "offres": \xff\xfe\n')
    (dossier / "unique_domains.txt").write_bytes(b"mirova.com\nbpi\xe9france.fr\n")
    (dossier / "_logs").mkdir()


def test_fichiers_abimes_le_panneau_s_ouvre_et_la_suite_marche(racine_tk, tmp_path, sans_console):
    _abimer(tmp_path)
    appels = {"n": 0}

    def charger(*a, **k):
        # the first read (window start) works; later rereads from a panel fail
        appels["n"] += 1
        if appels["n"] > 1:
            raise OSError("apply_queue.json illisible (test)")
        return [dict(OFFRE)]

    app, pannes, patches = _ouvrir(racine_tk, tmp_path, charger)
    try:
        _parcourir(app, racine_tk, pannes)
        # A second round: panels already built are reloaded, not rebuilt.
        _parcourir(app, racine_tk, pannes)
    finally:
        _fermer(racine_tk, patches)
