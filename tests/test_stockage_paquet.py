"""Le paquet jobhunter.stockage (phase 3) : facades, independance, racine.

- `queue_io` / `suivi_io` SONT les modules du paquet (alias), pas des copies :
  sinon un monkeypatch de leur CHEMIN ne toucherait pas le code reel.
- Le stockage se charge SANS Scripts/ sur le chemin : plus de cycle jutil <-> queue_io.
- La racine se trouve par marqueur, ou par JOBHUNTER_RACINE.
"""

import json
import os
import subprocess
import sys

import pytest
from conftest import RACINE, SRC

import jutil
import queue_io
import suivi_io
from jobhunter import racine
from jobhunter.stockage import atomique, file, suivi, verrou


def test_queue_io_est_le_module_du_paquet():
    assert queue_io is file


def test_suivi_io_est_le_module_du_paquet():
    assert suivi_io is suivi


def test_jutil_reexporte_le_meme_verrou():
    assert (jutil.prendre_verrou, jutil.rendre_verrou, jutil.tenu, jutil.garder) == (
        verrou.prendre_verrou,
        verrou.rendre_verrou,
        verrou.tenu,
        verrou.garder,
    )


def test_le_stockage_se_charge_sans_scripts():
    code = (
        "import sys; from jobhunter.stockage import file, suivi; "
        "print('jutil' in sys.modules or 'queue_io' in sys.modules)"
    )
    env = {**os.environ, "PYTHONPATH": str(SRC)}
    r = subprocess.run(
        [sys.executable, "-c", code], env=env, capture_output=True, text=True, cwd=RACINE
    )
    assert (r.returncode, r.stdout.strip()) == (0, "False"), r.stderr


def test_racine_par_marqueur(monkeypatch):
    monkeypatch.delenv("JOBHUNTER_RACINE", raising=False)
    assert racine.racine() == RACINE


def test_racine_par_variable(monkeypatch, tmp_path):
    monkeypatch.setenv("JOBHUNTER_RACINE", str(tmp_path))
    assert racine.scripts() == tmp_path.resolve() / "Scripts"


def test_donnees_dans_scripts():
    assert (file.CHEMIN, suivi.CHEMIN) == (
        RACINE / "Scripts" / "apply_queue.json",
        RACINE / "Scripts" / "suivi.json",
    )


def test_ecriture_atomique(tmp_path):
    f = tmp_path / "x.json"
    atomique.ecrire_json(f, {"é": [1, 2]})
    assert f.read_text(encoding="utf-8") == '{\n "é": [\n  1,\n  2\n ]\n}'
    assert not (tmp_path / "x.json.tmp").exists()


def test_jwrite_redirige_toujours_la_file_vers_la_separation(file_temporaire):
    """Garde-fou historique : ecrire apply_queue.json en direct ne remet jamais les
    descriptions dans la file."""
    jutil.jwrite(file_temporaire, [{"entreprise": "A", "poste": "B", "description": "texte"}])
    assert "description" not in file_temporaire.read_text(encoding="utf-8")
    assert file.charger()[0]["description"] == "texte"


@pytest.mark.parametrize("module", ["jobhunter.stockage.verrou", "jobhunter.stockage.atomique"])
def test_couches_basses_sans_dependance_au_moteur(module):
    """atomique et verrou n'importent rien d'autre du projet."""
    code = (
        f"import json, sys, {module}; "
        "print(json.dumps([m for m in sys.modules if m.startswith('jobhunter')]))"
    )
    env = {**os.environ, "PYTHONPATH": str(SRC)}
    r = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True)
    charges = set(json.loads(r.stdout))
    assert charges <= {"jobhunter", "jobhunter.stockage", module}


@pytest.mark.parametrize(
    ("script", "donnee", "attendu"),
    [
        ("queue_io.py", ("apply_queue.json", '[{"entreprise": "A", "poste": "B"}]'), "1 offres"),
        ("suivi_io.py", ("suivi.json", '{"A|B": {"s": "postulé"}}'), "1 candidature(s)"),
    ],
)
def test_facade_lancee_directement_affiche_son_bilan(tmp_path, script, donnee, attendu):
    """`python Scripts/queue_io.py` affichait le nombre d'offres ; la facade ne doit pas
    le rendre muet."""
    (tmp_path / "Scripts").mkdir()
    (tmp_path / "profil").mkdir()
    (tmp_path / "Scripts" / donnee[0]).write_text(donnee[1], encoding="utf-8")
    env = {**os.environ, "JOBHUNTER_RACINE": str(tmp_path), "PYTHONIOENCODING": "utf-8"}
    r = subprocess.run(
        [sys.executable, str(RACINE / "Scripts" / script)],
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert attendu in r.stdout, r.stdout + r.stderr
