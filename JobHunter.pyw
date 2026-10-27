#!/usr/bin/env python3
"""JobHunter — the application. Double-click JobHunter.pyw.

The code lives in src/jobhunter; this file is only the launcher, with no installation:
  double-click / `python JobHunter.pyw`        the application
  `python JobHunter.pyw <command> ...`         = `python -m jobhunter <command> ...`
The .bat/.sh files and the scheduled task go through it. It is the only place that adds
src/ to the import path, and it sets JOBHUNTER_RACINE to its folder when that folder holds
the data (data/ and profile/, or Scripts/ and profil/ before 3.0). Decision: ADR 0008.
"""

import os
import sys
from pathlib import Path

_ICI = Path(__file__).resolve().parent
_SRC = _ICI / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
if any(
    (_ICI / a).is_dir() and (_ICI / b).is_dir()
    for a, b in (("data", "profile"), ("Scripts", "profil"))
):
    os.environ.setdefault("JOBHUNTER_RACINE", str(_ICI))

if __name__ == "__main__":
    from jobhunter.profiles import appliquer  # the active profile, before any path is built

    appliquer()
    if len(sys.argv) > 1:
        from jobhunter.cli import main as _commande

        sys.exit(_commande(sys.argv[1:]))
    from jobhunter.launch import main  # the web window, the desktop one as fallback

    sys.exit(main())
