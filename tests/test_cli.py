"""La commande unique `jobhunter <commande>` (phase 3.8) : aiguillage, aide, erreurs."""

import importlib.util
import os
import subprocess
import sys

import pytest
from conftest import EXEMPLE, SCRIPTS, SRC

from jobhunter import cli


def _lance(*args):
    env = {**os.environ, "PYTHONPATH": str(SRC), "PROFIL_JOBHUNTER": str(EXEMPLE)}
    return subprocess.run(
        [sys.executable, "-m", "jobhunter", *args],
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def test_sans_argument_liste_les_commandes(capsys):
    assert cli.main([]) == 0
    sortie = capsys.readouterr().out
    assert all(c in sortie for c in cli.COMMANDES)


def test_commande_inconnue_code_2(capsys):
    assert cli.main(["envoyer-tout"]) == 2
    assert "inconnue" in capsys.readouterr().err


def test_aucune_commande_d_envoi():
    assert not {"envoyer", "submit", "auto"} & set(cli.COMMANDES)


@pytest.mark.parametrize("cmd", list(cli.COMMANDES))
def test_chaque_commande_vise_un_module_existant(cmd, monkeypatch):
    monkeypatch.syspath_prepend(str(SCRIPTS))
    assert importlib.util.find_spec(cli.COMMANDES[cmd][0]) is not None


@pytest.mark.parametrize("cmd", ["collecte", "tri", "documents", "dispo", "message"])
def test_l_aide_du_programme_passe(cmd):
    r = _lance(cmd, "--help")
    assert r.returncode == 0, r.stderr
    assert "usage" in r.stdout.lower()
