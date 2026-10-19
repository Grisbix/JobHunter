#!/usr/bin/env python3
"""JobHunter — compact application (one window: actions + rich built-in dashboard).
Tkinter (stdlib, nothing to install). Double-click JobHunter.pyw.
Dashboard tab = filterable table + detail card + EDITING of status/note/date
(written straight into Scripts/suivi.json; the 🔄 Sync Excel button pushes to the SUIVI sheet).
THE app dashboard = single source of information (no separate HTML any more).

The code lives in src/jobhunter; this file is only the launcher, with no installation:
  double-click / `python JobHunter.pyw`        the application
  `python JobHunter.pyw <command> ...`         = `python -m jobhunter <command> ...`
The .bat/.sh files and the scheduled task go through it. It is the only place that adds
src/ to the import path (installed by pip, the package does not need it). It also sets
JOBHUNTER_RACINE to its folder when that folder holds the data (Scripts/, profil/):
a package installed elsewhere thus finds the right data, wherever it is launched from. Decision: docs/adr/0008-programs-in-the-package.md
"""

import os
import sys
from pathlib import Path

_ICI = Path(__file__).resolve().parent
_SRC = _ICI / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
if (_ICI / "Scripts").is_dir() and (_ICI / "profil").is_dir():
    os.environ.setdefault("JOBHUNTER_RACINE", str(_ICI))

if __name__ == "__main__":
    if len(sys.argv) > 1:
        from jobhunter.cli import main as _commande

        sys.exit(_commande(sys.argv[1:]))
    from jobhunter.accueil import assurer_profil

    assurer_profil()
    from jobhunter.app.fenetre import main

    main()
