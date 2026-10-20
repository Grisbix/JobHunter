"""The French names of 2.24 and before keep working after the 2.25 rename.

Scripts written against the old names (`from jobhunter.programmes import jutil`),
scheduled tasks that run a program by its old file name (`jobhunter relances`,
`jobhunter metriques_hebdo`) and the old commands (`jobhunter collecte`, `maj`) must
still reach the right code — the SAME module object, so that a monkeypatch through
an old name acts on the real code.
"""

import importlib
import subprocess
import sys

import pytest
from conftest import EXEMPLE, SRC

from jobhunter import _old_names, cli


@pytest.mark.parametrize(("ancien", "nouveau"), sorted(_old_names.ANCIENS.items()))
def test_ancien_module_meme_objet(ancien, nouveau):
    assert importlib.import_module(f"jobhunter.{ancien}") is importlib.import_module(
        f"jobhunter.{nouveau}"
    )


def test_ancien_nom_garde_la_vraie_spec():
    import jobhunter.programmes.jutil as ancien

    assert ancien.__spec__.name == "jobhunter.programs.util"


def test_from_import_ancien_paquet_ancien_module():
    from jobhunter.programmes import relances
    from jobhunter.stockage import file

    assert relances.__name__ == "jobhunter.programs.follow_ups"
    assert file.__name__ == "jobhunter.storage.queue"


def test_sous_module_garde_son_nom_sous_l_ancien_paquet():
    import jobhunter.programmes.add_offer as a

    assert a.__name__ == "jobhunter.programs.add_offer"


@pytest.mark.parametrize(
    ("commande", "module"),
    [
        ("collecte", "jobhunter.sources"),
        ("collect", "jobhunter.sources"),
        ("postuler", "jobhunter.programs.apply_runner"),
        ("maj", "jobhunter.programs.update"),
        ("update", "jobhunter.programs.update"),
        ("profil", "jobhunter.programs.first_launch"),
        # Gabriel's scheduled tasks: a program by its old file name
        ("relances", "jobhunter.programs.follow_ups"),
        ("metriques_hebdo", "jobhunter.programs.weekly_metrics"),
        ("follow_ups", "jobhunter.programs.follow_ups"),
        ("probe_ats", "jobhunter.programs.probe_ats"),
    ],
)
def test_commandes_anciennes_et_nouvelles(commande, module):
    assert cli.module_de(commande) == module


def test_commande_inconnue():
    assert cli.module_de("n_existe_pas") is None


def test_python_m_ancien_nom():
    """`python -m jobhunter.programmes.<old name>` still runs the program."""
    r = subprocess.run(
        [sys.executable, "-m", "jobhunter.programmes.verifie_profil", "Analyste ESG"],
        env={
            "PYTHONPATH": str(SRC),
            "PROFIL_JOBHUNTER": str(EXEMPLE),
            "PYTHONIOENCODING": "utf-8",
            "SYSTEMROOT": __import__("os").environ.get("SYSTEMROOT", ""),
        },
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
    )
    assert r.returncode == 0, r.stderr
    assert "Analyste ESG" in r.stdout and "Profil :" in r.stdout
