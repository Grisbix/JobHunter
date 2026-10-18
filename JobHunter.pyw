#!/usr/bin/env python3
"""JobHunter — application compacte (1 fenêtre : actions + dashboard riche intégré).
Tkinter (stdlib, aucune install). Double-clic JobHunter.pyw.
Onglet Dashboard = table filtrable + fiche détail + ÉDITION statut/note/date
(écrit direct dans Scripts/suivi.json ; bouton 🔄 Sync Excel pousse vers la feuille SUIVI).
LE dashboard de l'app = source unique d'infos (plus de HTML séparé).

Le code vit dans src/jobhunter/app (phase 3.7 du plan) ; ce fichier n'est que le
lanceur du double-clic.
"""

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

if __name__ == "__main__":
    from jobhunter.accueil import assurer_profil

    assurer_profil()
    from jobhunter.app.fenetre import main

    main()
