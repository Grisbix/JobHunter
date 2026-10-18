"""Scripts/profil.py — FACADE : le code vit dans jobhunter.profil (phase 3 du plan).

`import profil` rend le module jobhunter.profil LUI-MEME (alias dans sys.modules) :
`profil.FICHIER = ...` (premier_lancement) agit donc sur le code reel. Lance
directement, il execute le module du paquet. A retirer en fin de phase 3.
"""

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

if __name__ == "__main__":
    # Remplacer sys.modules["__main__"] en cours d'execution ne ferait rien, sans erreur.
    import runpy

    runpy.run_module("jobhunter.profil", run_name="__main__", alter_sys=True)
else:
    from jobhunter import profil as _module

    sys.modules[__name__] = _module
