"""Garde-fou : plus aucune suite « historique » dans Scripts/.

Les 27 suites autonomes de Scripts/test_*.py (qui comptaient leurs ✅/❌ et sortaient
en code non nul) ont toutes ete converties en tests pytest dans tests/ (phase 2 du
plan, 2026-10-18). Un nouveau Scripts/test_*.py ne serait lance par personne : les
tests s'ecrivent dans tests/. Seules restent les deux suites qui sortent vraiment
sur le web et ne doivent pas tourner machinalement.
"""

from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "Scripts"
EN_LIGNE = {"test_live_nav", "test_acces_sites"}


def test_aucune_suite_historique_dans_scripts():
    assert {p.stem for p in SCRIPTS.glob("test_*.py")} == EN_LIGNE
