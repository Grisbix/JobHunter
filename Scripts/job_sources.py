#!/usr/bin/env python3
"""Scripts/job_sources.py — FACADE : le code vit dans jobhunter.sources (phase 3 du plan).

`import job_sources` rend le module jobhunter.sources LUI-MEME (alias dans sys.modules) : une
affectation ou un monkeypatch sur `job_sources.X` agit donc sur le code reel. Lance
directement (`python Scripts/job_sources.py ...`), il execute la collecte
(jobhunter.sources.__main__), avec les memes arguments. A retirer en fin de phase 3.
"""

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

if __name__ == "__main__":
    # Remplacer sys.modules["__main__"] en cours d'execution ne ferait rien, sans erreur.
    import runpy

    runpy.run_module("jobhunter.sources", run_name="__main__")
else:
    import importlib

    sys.modules[__name__] = importlib.import_module("jobhunter.sources")
