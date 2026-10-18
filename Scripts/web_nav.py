#!/usr/bin/env python3
"""Scripts/web_nav.py — FACADE : le code vit dans jobhunter.navigation (phase 3 du plan).

`import web_nav` rend le module jobhunter.navigation LUI-MEME (alias dans sys.modules) : une
affectation ou un monkeypatch sur `web_nav.X` agit donc sur le code reel. Lance
directement (`python Scripts/web_nav.py ...`), il execute ce module comme programme,
avec les memes arguments. A retirer en fin de phase 3.
"""

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

if __name__ == "__main__":
    # Remplacer sys.modules["__main__"] en cours d'execution ne ferait rien, sans erreur.
    import runpy

    runpy.run_module("jobhunter.navigation", run_name="__main__", alter_sys=True)
else:
    import importlib

    sys.modules[__name__] = importlib.import_module("jobhunter.navigation")
