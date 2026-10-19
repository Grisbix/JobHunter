"""Each entry of the Maintenance menu launches a program that exists.

"Tests live" launched `test_web_nav.py`, removed in 2.0: the button failed silently
until 19/10/2026.
"""

import importlib.util

from jobhunter.app.commun import MAINT


def test_chaque_commande_existe():
    absents = []
    for _groupe, entrees in MAINT:
        for nom, cmd in entrees:
            if not isinstance(cmd, list):
                continue  # app action ("maj", "langue") or built on the fly
            assert "-m" in cmd, f"{nom} : lancer un module du paquet, pas un fichier"
            module = cmd[cmd.index("-m") + 1]
            if importlib.util.find_spec(module) is None:
                absents.append((nom, module))
    assert absents == []
