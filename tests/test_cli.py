"""The single `jobhunter <command>` command (phase 3.8): dispatch, help, errors."""

import importlib.util
import os
import subprocess
import sys

import pytest
from conftest import EXEMPLE, SRC

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
    assert importlib.util.find_spec(cli.COMMANDES[cmd][0]) is not None


@pytest.mark.parametrize("cmd", ["collecte", "tri", "documents", "dispo", "message"])
def test_l_aide_du_programme_passe(cmd):
    r = _lance(cmd, "--help")
    assert r.returncode == 0, r.stderr
    assert "usage" in r.stdout.lower()


def test_app_help_n_ouvre_pas_la_fenetre(monkeypatch, capsys):
    import runpy

    monkeypatch.setattr(runpy, "run_module", lambda *a, **k: pytest.fail("fenêtre ouverte"))
    assert cli.main(["app", "--help"]) == 0
    assert "Aucune option" in capsys.readouterr().out


# ── a program is a function: main(argv) called in this process ──────────────────────
@pytest.fixture
def programme(tmp_path, monkeypatch):
    """Writes a throwaway module `jh_essai_<n>` and returns its name."""
    monkeypatch.syspath_prepend(str(tmp_path))
    import uuid

    def ecrire(source):
        nom = f"jh_essai_{uuid.uuid4().hex[:12]}"  # a name never imported before
        (tmp_path / f"{nom}.py").write_text(source, encoding="utf-8")
        return nom

    return ecrire


def test_main_appele_avec_argv_et_son_code(programme):
    nom = programme(
        "import sys\nVU = []\ndef main(argv=None):\n    VU.append(list(argv))\n    return 7\n"
        'if __name__ == "__main__":\n    sys.exit(main())\n'
    )
    assert cli.executer(nom, ["--x", "1"]) == 7
    import importlib

    assert importlib.import_module(nom).VU == [["--x", "1"]]  # imported, not re-run


def test_main_nu_son_retour_n_est_pas_un_code(programme):
    nom = programme('def main():\n    return 5\nif __name__ == "__main__":\n    main()\n')
    assert cli.executer(nom, []) == 0


def test_bloc_main_avec_plus_tourne_en_script(programme, capsys):
    nom = programme(
        'import sys\ndef main(argv=None):\n    return 1\nif __name__ == "__main__":\n'
        '    print("script", sys.argv[1:])\n'
    )
    import sys

    sys.argv = ["jobhunter essai", "a"]
    assert cli.executer(nom, ["a"]) == 0
    assert "script ['a']" in capsys.readouterr().out


def test_message_de_sortie_affiche(programme):
    nom = programme(
        'def main(argv=None):\n    return "refus"\nif __name__ == "__main__":\n    sys.exit(main())\n'
    )
    with pytest.raises(SystemExit, match="refus"):
        cli.executer(nom, [])
