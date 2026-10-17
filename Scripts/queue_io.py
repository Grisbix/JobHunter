"""Scripts/queue_io.py — FACADE : le code vit dans jobhunter.stockage.file (phase 3 du plan).

`import queue_io` rend le module jobhunter.stockage.file LUI-MEME (alias dans sys.modules), pas une
copie de ses noms : un `monkeypatch.setattr(queue_io, "CHEMIN", ...)` agit donc sur le
code reel. A retirer quand plus aucun programme n'importera `queue_io`.
"""

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from jobhunter.stockage import file as _module  # noqa: E402

sys.modules[__name__] = _module
