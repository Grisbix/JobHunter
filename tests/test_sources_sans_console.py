"""The desktop panels load the sources without console output (pythonw)."""

import os
import subprocess
import sys

import pytest
from conftest import SRC


@pytest.mark.parametrize("sortie", ["None", "io.StringIO()"])
def test_sources_sans_console(sortie):
    env = dict(os.environ, PYTHONPATH=str(SRC))
    resultat = subprocess.run(
        [sys.executable, "-c", f"import sys, io; sys.stdout={sortie}; import jobhunter.sources"],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert resultat.returncode == 0, resultat.stderr
