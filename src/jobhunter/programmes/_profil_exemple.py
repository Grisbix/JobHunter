"""Importe EN TETE des programmes de test en direct (test_live_nav, test_acces_sites) :
ils tournent sur le profil d'EXEMPLE (profil/exemple_finance_esg.json), jamais sur le
profil reel. Ancien Scripts/_profil_test.py."""

import os

from jobhunter import racine as _racine

os.environ["PROFIL_JOBHUNTER"] = str(_racine.racine() / "profil" / "exemple_finance_esg.json")
