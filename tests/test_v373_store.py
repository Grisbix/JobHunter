"""3.73: the Store package updates from inside the application (no Store window)."""

import subprocess
from pathlib import Path

import js_app

from jobhunter import store_update
from jobhunter.programs import update
from jobhunter.web import api

RACINE = Path(__file__).resolve().parent.parent
JS = js_app.source()


def _sortie(monkeypatch, texte, code=0):
    vu = {}

    def faux(cmd, **k):
        vu["env"] = k["env"]["JH_ACTION"]
        return subprocess.CompletedProcess(cmd, code, texte, "")

    monkeypatch.setattr(store_update.subprocess, "run", faux)
    return vu


def test_verifier(monkeypatch):
    vu = _sortie(monkeypatch, "MAJ 1\n")
    assert store_update.mises_a_jour() == 1 and vu["env"] == "verifier"
    _sortie(monkeypatch, "", code=1)
    assert store_update.mises_a_jour() is None


def test_installer(monkeypatch):
    vu = _sortie(monkeypatch, "ETAT Completed\n")
    assert store_update.installer() == "Completed" and vu["env"] == "installer"
    _sortie(monkeypatch, "boom", code=1)
    assert store_update.installer() == ""


def test_pas_de_powershell(monkeypatch):
    def absent(*a, **k):
        raise FileNotFoundError

    monkeypatch.setattr(store_update.subprocess, "run", absent)
    assert store_update.mises_a_jour() is None and store_update.installer() == ""


def _store(monkeypatch, etat):
    ouvert = []
    monkeypatch.setattr(update, "nouvelle_version", lambda **k: "9.9.9")
    monkeypatch.setattr(update._gele, "paquet_msix", lambda: True)
    monkeypatch.setattr(update._gele, "msix_du_store", lambda: True)
    monkeypatch.setattr(update, "file_libre", lambda garder=True: True)
    monkeypatch.setattr(store_update, "installer", lambda: etat)
    monkeypatch.setattr("webbrowser.open", ouvert.append)
    return ouvert


def test_maj_store_installee_ici(monkeypatch):
    ouvert = _store(monkeypatch, "Completed")
    assert update.maj_application(False) == 0 and not ouvert


def test_maj_store_echec_n_ouvre_rien(monkeypatch):
    ouvert = _store(monkeypatch, "")
    assert update.maj_application(False) == 1
    assert ouvert == []  # never the Store's window (the user, 2026-11-05)


def test_annonce_pour_le_store(monkeypatch):
    a = api.Api()
    monkeypatch.setattr(
        a,
        "mise_a_jour",
        lambda: {"signee": False, "store": True, "nouvelle": True, "derniere": "9"},
    )
    monkeypatch.setattr(store_update, "telecharger", lambda: "Completed")  # no PowerShell
    assert a.annonce_maj()


def test_interface_store():
    assert "se ferme pendant l'installation puis se rouvre" in JS
    assert "Le Microsoft Store l'installe de lui-même" not in JS
