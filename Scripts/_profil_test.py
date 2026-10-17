"""Importe EN TETE de chaque test : les tests tournent sur le profil d'EXEMPLE
(profil/exemple_finance_esg.json), jamais sur le profil reel de l'utilisateur.
Leurs attendus decrivent ce profil-la ; le profil reel peut changer sans les
casser."""

import os
from pathlib import Path

os.environ["PROFIL_JOBHUNTER"] = str(
    Path(__file__).resolve().parent.parent / "profil" / "exemple_finance_esg.json"
)
