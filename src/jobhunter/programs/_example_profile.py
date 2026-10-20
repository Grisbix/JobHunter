"""Imported AT THE TOP of the live test programs (test_live_nav, test_acces_sites):
they run on the EXAMPLE profile (profile/example_finance_esg.json), never on the real
profile. Formerly Scripts/_profil_test.py."""

import os

from jobhunter import root as _racine

os.environ["PROFIL_JOBHUNTER"] = str(
    _racine.dossier("profil") / _racine.nom("exemple_finance_esg.json")
)
