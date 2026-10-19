#!/usr/bin/env python3
"""JobHunter — application compacte (1 fenêtre : actions + dashboard riche intégré).
Tkinter (stdlib, aucune install). Double-clic JobHunter.pyw.
Onglet Dashboard = table filtrable + fiche détail + ÉDITION statut/note/date
(écrit direct dans Scripts/suivi.json ; bouton 🔄 Sync Excel pousse vers la feuille SUIVI).
LE dashboard de l'app = source unique d'infos (plus de HTML séparé).

Le code vit dans src/jobhunter ; ce fichier n'est que le lanceur, sans installation :
  double-clic / `python JobHunter.pyw`        l'application
  `python JobHunter.pyw <commande> ...`        = `python -m jobhunter <commande> ...`
Les .bat/.sh et la tache planifiee passent par lui. C'est le seul endroit qui ajoute
src/ au chemin d'import (installe par pip, le paquet n'en a pas besoin). Pose aussi
JOBHUNTER_RACINE sur son dossier quand celui-ci tient les donnees (Scripts/, profil/) :
un paquet installe ailleurs trouve ainsi les bonnes donnees, d'ou qu'on le lance. Decision : docs/adr/0008-programmes-dans-le-paquet.md
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
