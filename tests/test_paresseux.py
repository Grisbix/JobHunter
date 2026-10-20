"""Values taken from the profile: computed on first read, and an injected profile
applies everywhere (phase 4 of the plan)."""

import copy
import os
import subprocess
import sys

import pytest
from conftest import EXEMPLE, SRC

from jobhunter import lazy as paresseux
from jobhunter import profile as profil
from jobhunter.scoring import fit
from jobhunter.sources import common as commun


@pytest.fixture
def profil_injecte():
    """The example profile, copied and modifiable; the file comes back at the end."""
    donnees = copy.deepcopy(profil.charger())
    yield donnees
    profil.recharger()


def test_valeur_calculee_puis_gardee_dans_le_module():
    profil.recharger()  # a previous test may have replaced KEYWORDS (sources_config)
    mots = commun.KEYWORDS
    assert mots == list(profil.get("collecte.mots_cles", []))
    assert vars(commun)["KEYWORDS"] is mots


def test_nom_inconnu_leve_attribute_error():
    with pytest.raises(AttributeError, match="PAS_UN_NOM"):
        commun.PAS_UN_NOM  # noqa: B018


def test_profil_injecte_vaut_partout(profil_injecte):
    profil_injecte["collecte"]["mots_cles"] = ["mot injecte"]
    profil_injecte["scoring"]["plafond_veto"] = 1.5
    profil.utiliser(profil_injecte)
    assert commun.KEYWORDS == ["mot injecte"]
    assert fit._PLAFOND_VETO == 1.5


def test_recharger_revient_au_fichier(profil_injecte):
    profil_injecte["collecte"]["mots_cles"] = ["mot injecte"]
    profil.utiliser(profil_injecte)
    assert commun.KEYWORDS == ["mot injecte"]
    profil.recharger()
    assert commun.KEYWORDS == list(profil.get("collecte.mots_cles", []))


def test_un_monkeypatch_remplace_la_valeur(monkeypatch):
    monkeypatch.setattr(commun, "KEYWORDS", ["remplace"])
    assert commun.KEYWORDS == ["remplace"]


def test_oublier_refait_la_valeur():
    avant = commun._DOMAIN_RX
    paresseux.oublier()
    assert "_DOMAIN_RX" not in vars(commun)
    assert commun._DOMAIN_RX.pattern == avant.pattern


def test_un_module_lance_comme_programme_lit_ses_valeurs_paresseuses():
    # Run as `__main__`, the module must find its values through `_ici` (before 2.0,
    # a facade run by runpy without alter_sys made it fail).
    env = {**os.environ, "PROFIL_JOBHUNTER": str(EXEMPLE), "PYTHONPATH": str(SRC)}
    r = subprocess.run(
        [sys.executable, "-m", "jobhunter.paths"],
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert r.returncode == 0, r.stderr
    assert "CV/Par_offre" in r.stdout
