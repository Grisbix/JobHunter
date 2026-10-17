"""Scripts/queue_io.py — FACADE : le code vit dans jobhunter.stockage.file (phase 3 du plan).

`import queue_io` rend le module jobhunter.stockage.file LUI-MEME (alias dans sys.modules), pas une
copie de ses noms : un `monkeypatch.setattr(queue_io, "CHEMIN", ...)` agit donc sur le
code reel. Lance directement (`python Scripts/queue_io.py`), il execute ce module comme
programme. A retirer quand plus aucun programme n'importera `queue_io`.
"""

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

if __name__ == "__main__":
    # Remplacer sys.modules["__main__"] en cours d'execution ne ferait rien, sans erreur.
    import runpy

    runpy.run_module("jobhunter.stockage.file", run_name="__main__")
else:
    from jobhunter.stockage import file as _module

    sys.modules[__name__] = _module
