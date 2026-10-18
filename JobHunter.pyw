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
src/ au chemin d'import (installe par pip, le paquet n'en a pas besoin).
"""

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

if __name__ == "__main__":
    if len(sys.argv) > 1:
        from jobhunter.cli import main as _commande

        sys.exit(_commande(sys.argv[1:]))
    from jobhunter.accueil import assurer_profil

    assurer_profil()
    from jobhunter.app.fenetre import main

    main()
