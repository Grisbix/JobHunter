"""Aucune donnée personnelle dans le dépôt public (outils/donnees_perso.py)."""

import importlib.util
import pathlib
import subprocess

import pytest

RACINE = pathlib.Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "donnees_perso", RACINE / "outils" / "donnees_perso.py"
)
assert _spec and _spec.loader
dp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dp)


def test_aucun_fichier_suivi_n_est_une_donnee_perso():
    suivis = subprocess.run(
        ["git", "ls-files"], cwd=RACINE, capture_output=True, text=True, encoding="utf-8"
    ).stdout.splitlines()
    if not suivis:
        pytest.skip("pas un dépôt git (archive)")
    assert dp.fautifs(suivis) == []


@pytest.mark.parametrize(
    "chemin",
    [
        "profil/profil.json",
        "profil/profil.json.bak",
        "Scripts/apply_queue.json",
        "Scripts/suivi.json",
        "Scripts/descriptions.json",
        "Scripts/adzuna.json",
        "Scripts/jooble.json",
        "Scripts/_rendement.jsonl",
        "Scripts/_preuves/2026-10-19_x.png",
        "Scripts/.ats_password",
        "Personnel/.env",
        "Lettres/Relances/Relance_J7_X.txt",
        "CV/Sur_mesure/x.docx",
        "Mon_CV/mon_CV.docx",
        "docs/mon_cv.pdf",
        "outils/apply_profile.json",
    ],
)
def test_refuse(chemin):
    assert dp.fautifs([chemin]) == [chemin]


@pytest.mark.parametrize(
    "chemin",
    [
        "profil/exemple_finance_esg.json",
        "profil/exemple_Faits.json",
        "Scripts/sources_config.json",
        "Mon_CV/LISEZ-MOI.txt",
        "docs/screenshots/offers.png",
        "src/jobhunter/stockage/suivi.py",
        "tests/reponses/lever.json",
    ],
)
def test_accepte(chemin):
    assert dp.fautifs([chemin]) == []
