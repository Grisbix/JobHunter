"""The tour after the first profile: its first scan's command, and its texts.

Synthetic keys only, in a temporary folder: no real key file is read or written.
"""

import importlib

from jobhunter import api_keys, welcome_tour


def test_scan_sans_cle_prend_les_sources_rapides(tmp_path):
    commande = welcome_tour.commande_scan(tmp_path)
    assert commande[1:4] == ["-m", "jobhunter", "collect"]
    assert commande[4:] == welcome_tour.SCAN_DE_BASE
    assert not set(welcome_tour.SCAN_CLES.values()) & set(commande)


def test_scan_ajoute_chaque_api_dont_la_cle_est_posee(tmp_path):
    cle = api_keys.CLES["francetravail"]
    api_keys.enregistrer(tmp_path, "francetravail", {c: "factice" for c in cle.champs})
    commande = welcome_tour.commande_scan(tmp_path)
    assert "--ft" in commande
    assert "--adzuna" not in commande and "--jooble" not in commande


def test_chaque_cle_a_son_apport_et_son_option():
    assert set(welcome_tour.SCAN_CLES) == set(api_keys.CLES)
    assert set(welcome_tour.APPORT) >= set(api_keys.CLES)


def test_le_module_se_charge():
    assert importlib.reload(welcome_tour).visite
