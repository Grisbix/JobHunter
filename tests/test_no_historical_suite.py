"""Safeguard: no more "historical" suites, and no more programs in Scripts/.

The 27 standalone suites of Scripts/test_*.py (which counted their ✅/❌ and exited
with a non-zero code) have all been converted to pytest tests in tests/ (phase 2 of the
plan, 2026-10-18). A new Scripts/test_*.py would be run by nobody: the
tests are written in tests/. Only the two suites that really go out
on the web and must not run mechanically remain. Since 2.0, the programs
live in jobhunter.programs; Scripts/ only keeps the data.
"""

from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
PROGRAMMES = RACINE / "src" / "jobhunter" / "programs"
EN_LIGNE = {"test_live_nav", "test_site_access"}


def test_aucune_suite_historique():
    assert {p.stem for p in PROGRAMMES.glob("test_*.py")} == EN_LIGNE


def test_scripts_ne_garde_que_les_donnees():
    assert list((RACINE / "Scripts").glob("*.py")) == []
