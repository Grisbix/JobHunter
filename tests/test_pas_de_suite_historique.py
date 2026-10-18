"""Garde-fou : plus aucune suite « historique », et plus aucun programme dans Scripts/.

Les 27 suites autonomes de Scripts/test_*.py (qui comptaient leurs ✅/❌ et sortaient
en code non nul) ont toutes ete converties en tests pytest dans tests/ (phase 2 du
plan, 2026-10-18). Un nouveau Scripts/test_*.py ne serait lance par personne : les
tests s'ecrivent dans tests/. Seules restent les deux suites qui sortent vraiment
sur le web et ne doivent pas tourner machinalement. Depuis la 2.0, les programmes
vivent dans jobhunter.programmes ; Scripts/ ne garde que les donnees.
"""

from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
PROGRAMMES = RACINE / "src" / "jobhunter" / "programmes"
EN_LIGNE = {"test_live_nav", "test_acces_sites"}


def test_aucune_suite_historique():
    assert {p.stem for p in PROGRAMMES.glob("test_*.py")} == EN_LIGNE


def test_scripts_ne_garde_que_les_donnees():
    assert list((RACINE / "Scripts").glob("*.py")) == []
