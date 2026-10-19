"""Chaque entrée du menu Maintenance lance un programme qui existe.

« Tests live » lançait `test_web_nav.py`, retiré en 2.0 : le bouton échouait en silence
jusqu'au 19/10/2026.
"""

import importlib.util

from jobhunter.app.commun import MAINT


def test_chaque_commande_existe():
    absents = []
    for _groupe, entrees in MAINT:
        for nom, cmd in entrees:
            if not isinstance(cmd, list):
                continue  # action de l'app (« maj », « langue ») ou construite à la volée
            assert "-m" in cmd, f"{nom} : lancer un module du paquet, pas un fichier"
            module = cmd[cmd.index("-m") + 1]
            if importlib.util.find_spec(module) is None:
                absents.append((nom, module))
    assert absents == []
