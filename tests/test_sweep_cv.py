"""tools/sweep_cv.py on one CV per layout: a profile from any CV stays usable.

The full sweep (45 jobs) is run by hand: `python tools/sweep_cv.py`. Here, four of
them — Word, two columns, Canva-like PDF, English — so that a change of first_launch
or of the catalogue that breaks a new user's profile fails the suite.
"""

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

OUTIL = Path(__file__).resolve().parent.parent / "tools" / "sweep_cv.py"


@pytest.mark.parametrize("seul", ["Infirmière", "Aide-soignant", "Pharmacienne", "Software"])
def test_un_cv_par_mise_en_page(seul, tmp_path):
    r = subprocess.run(
        [sys.executable, str(OUTIL), "--garder", str(tmp_path), "--seul", seul],
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert r.returncode == 0, r.stdout + r.stderr


def test_le_balayage_couvre_chaque_mise_en_page():
    spec = importlib.util.spec_from_file_location("sweep_cv", OUTIL)
    sw = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sw)
    assert len(sw.METIERS) >= 40
    assert {"Infirmière", "Aide-soignant", "Pharmacienne"} <= {m[0] for m in sw.METIERS[:3]}
