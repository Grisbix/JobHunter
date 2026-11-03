"""Update of the pip-installed package (3.80): the pipeline's lock, the load check
after pip, the way back to the old version, --annuler."""

import subprocess
import sys
import time
from types import SimpleNamespace

import pytest

from jobhunter.programs import update
from jobhunter.storage import lock


def test_maj_attend_le_pipeline_entre_ses_etapes(tmp_path, monkeypatch):
    """3.80: the pipeline gives the queue back between its steps; its own lock
    (storage.lock.PIPELINE) keeps the update out until it ends."""
    donnees = tmp_path / "data"
    donnees.mkdir()
    monkeypatch.setattr(update._profils, "liste", lambda r: [SimpleNamespace(racine=tmp_path)])
    # Another process holds the pipeline's lock, as daily_pipeline does for its run.
    code = (
        "import sys, time; from jobhunter.storage import lock; "
        f"lock.prendre_verrou(r'{donnees / lock.PIPELINE}'); print('pris', flush=True); time.sleep(60)"
    )
    p = subprocess.Popen([sys.executable, "-c", code], stdout=subprocess.PIPE, text=True)
    try:
        assert p.stdout.readline().strip() == "pris"
        monkeypatch.setattr(
            update._verrou, "prendre_verrou", _sans_attente(update._verrou.prendre_verrou)
        )
        assert update.file_libre(garder=False) is False
    finally:
        p.kill()
        p.wait()
    time.sleep(0.2)
    assert update.file_libre(garder=False) is True  # its owner dead: free again


def _sans_attente(prendre):
    return lambda chemin, attente=0, **k: prendre(chemin, attente=0, **k)


@pytest.fixture
def maj_pip(tmp_path, monkeypatch):
    """The pip package's update with the network, pip and the lock replaced."""
    etat = {"installee": "3.78.0", "charge": True, "installs": []}
    monkeypatch.setattr(update, "PAQUET_AVANT", tmp_path / ".maj_paquet_avant")
    monkeypatch.setattr(update, "version_paquet", lambda: etat["installee"])
    monkeypatch.setattr(update, "version_proposee", lambda t: "3.79.0")
    monkeypatch.setattr(update, "file_libre", lambda garder=True: True)
    monkeypatch.setattr(
        update, "paquet_charge", lambda: etat["charge"] or etat["installee"] == "3.78.0"
    )

    def installer(version, locale):
        etat["installs"].append(version)
        etat["installee"] = version
        return 0

    monkeypatch.setattr(update, "installer_paquet", installer)
    return update, etat


def test_maj_pip_installe_et_note_la_version_d_avant(maj_pip):
    update, etat = maj_pip
    assert update.maj_paquet(False) == 0
    assert etat["installs"] == ["3.79.0"]
    assert update.PAQUET_AVANT.read_text(encoding="utf-8") == "3.78.0"


def test_maj_pip_qui_ne_se_charge_pas_revient_a_l_ancienne(maj_pip):
    update, etat = maj_pip
    etat["charge"] = False
    assert update.maj_paquet(False) == 1
    assert etat["installs"] == ["3.79.0", "3.78.0"] and etat["installee"] == "3.78.0"


def test_annuler_pip_remet_la_version_d_avant(maj_pip):
    update, etat = maj_pip
    assert update.annuler_paquet() == 1  # nothing to undo yet
    update.maj_paquet(False)
    assert update.annuler_paquet() == 0
    assert etat["installee"] == "3.78.0" and not update.PAQUET_AVANT.exists()


def test_main_annuler_va_au_paquet_pip(monkeypatch):
    monkeypatch.setattr(update, "paquet_pip", lambda: True)
    monkeypatch.setattr(update, "annuler_paquet", lambda: 42)
    assert update.main(["--annuler"]) == 42
