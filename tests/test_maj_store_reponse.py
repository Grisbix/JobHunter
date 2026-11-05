"""3.83: the Store package asks the Store, and a failure says why (the user, 2026-11-05:
« le Store n'a pas pu l'installer (pas de réponse) »)."""

import subprocess

import pytest

from jobhunter import frozen, store_update
from jobhunter.programs import update
from jobhunter.web import api


def _sortie(monkeypatch, texte, code=0):
    monkeypatch.setattr(
        store_update.subprocess,
        "run",
        lambda cmd, **k: subprocess.CompletedProcess(cmd, code, texte, "trace PowerShell"),
    )


def test_le_script_ecrit_son_erreur():
    assert "trap {" in store_update.SCRIPT and '"ERREUR 0x{0:X8} {1}"' in store_update.SCRIPT


def test_erreur_du_store_rendue(monkeypatch):
    _sortie(monkeypatch, "ERREUR 0x803F6101 Exception de HRESULT : 0x803F6101\n", code=1)
    assert store_update.installer() == "erreur 0x803F6101 Exception de HRESULT : 0x803F6101"
    erreur = "erreur 0x803F6101 Exception de HRESULT : 0x803F6101"
    assert store_update.verifier() == (None, erreur, "")
    assert store_update.mises_a_jour() is None


def test_verifier(monkeypatch):
    _sortie(monkeypatch, "MAJ 0\n")
    assert store_update.verifier() == (0, "", "")
    _sortie(monkeypatch, "MAJ 2\nVERSION 3.82.0\nVERSION 3.9.0\n")
    assert store_update.verifier() == (2, "", "3.82.0")
    _sortie(monkeypatch, "", code=1)
    assert store_update.verifier() == (None, "pas de réponse", "")


def test_echec_dit_l_erreur(monkeypatch, capsys):
    monkeypatch.setattr(update, "nouvelle_version", lambda **k: "9.9.9")
    monkeypatch.setattr(update._gele, "paquet_msix", lambda: True)
    monkeypatch.setattr(update._gele, "msix_du_store", lambda: True)
    monkeypatch.setattr(update, "file_libre", lambda garder=True: True)
    monkeypatch.setattr(store_update, "installer", lambda: "erreur 0x803F6101 x")
    monkeypatch.setattr("webbrowser.open", lambda u: None)
    assert update.maj_application(False) == 1
    assert "(erreur 0x803F6101 x)" in capsys.readouterr().out


@pytest.fixture
def store(monkeypatch):
    monkeypatch.setattr(api, "_version_installee", lambda: "3.81.0")
    monkeypatch.setattr(api, "_derniere_version", lambda: "3.82.0")
    monkeypatch.setattr(frozen, "paquet_msix", lambda: True)
    monkeypatch.setattr(frozen, "msix_du_store", lambda: True)
    monkeypatch.setattr(api, "_signee", lambda v: True)

    def reponse(n, erreur="", version=""):
        monkeypatch.setattr(store_update, "verifier", lambda: (n, erreur, version))
        return api.Api.mise_a_jour(None)  # type: ignore[arg-type]

    return reponse


def test_pas_encore_dans_le_store(store):
    v = store(0)
    assert not v["nouvelle"] and v["attente"] == "3.82.0" and not v["erreur"]


def test_dans_le_store(store):
    v = store(1)
    assert v["nouvelle"] and not v["attente"]


def test_la_version_du_store_pas_celle_de_github(store):
    v = store(1, version="3.81.5")
    assert v["nouvelle"] and v["derniere"] == "3.81.5"


def test_store_muet_rien_propose(store):
    v = store(None, "erreur 0x803F6101 x")
    assert not v["nouvelle"] and v["erreur"] == "erreur 0x803F6101 x"
    assert api.Api.annonce_maj(type("A", (), {"mise_a_jour": lambda s: v})()) is None


def test_fenetre_dit_l_attente_et_l_erreur():
    from pathlib import Path

    from jobhunter.web.texts import TEXTES

    js = (Path(api.__file__).parent / "static" / "app.js").read_text(encoding="utf-8")
    assert "v.erreur" in js and "arrive dans le Microsoft Store" in js
    for cle in (
        "Le Microsoft Store ne répond pas ({x}) : réessaie plus tard.",
        "La {v} arrive dans le Microsoft Store après sa vérification par Microsoft (quelques heures à quelques jours).",
    ):
        assert cle in TEXTES
