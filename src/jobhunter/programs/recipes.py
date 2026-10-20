"""jobhunter recipes — replays the cleanup recipes on the queue (preview by default).

    jobhunter recipes                 # what would change, nothing written
    jobhunter recipes --appliquer     # writes it, under the queue's lock

The recipes live in `_recettes.json` (data folder) and are edited in the application:
Maintenance → « Recettes de nettoyage… ». See jobhunter.cleanup_recipes. An offer you
applied to is never renamed; a rename that would create a duplicate is skipped.
"""

import argparse
import sys

from jobhunter import cleanup_recipes as R
from jobhunter import root as _racine
from jobhunter.storage import applications as suivi_io
from jobhunter.storage import queue as queue_io

OCCUPE = 3


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]  # console : TextIOWrapper
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--appliquer", action="store_true", help="écrire les changements")
    a = ap.parse_args(argv)
    recettes = R.lire(_racine.dans(_racine.scripts(), R.FICHIER))
    if not recettes:
        print("Aucune recette (Maintenance → « Recettes de nettoyage… » pour en écrire).")
        return 0
    if erreurs := R.valider(recettes):
        print("! Recettes refusées :\n  " + "\n  ".join(erreurs))
        return 1
    candidatures = set(suivi_io.charger())
    chg = R.apercu(queue_io.charger(descriptions=False), recettes, candidatures)
    gardes = [c for c in chg if not c.ecarte]
    for c in chg[:60]:
        marque = f"  (non : {c.ecarte})" if c.ecarte else ""
        print(f"  {c.champ:<13} {c.avant} → {c.apres}{marque}")
    if len(chg) > 60:
        print(f"  … et {len(chg) - 60} autre(s)")
    print(f"\n{len(gardes)} changement(s), {len(chg) - len(gardes)} écarté(s).")
    if not a.appliquer or not gardes:
        if gardes:
            print("Rien n'est écrit : relance avec --appliquer.")
        return 0
    try:
        with queue_io.transaction(descriptions=False, attente=30) as file_:
            # Recomputed on the queue read under the lock: what changed since is respected.
            n = R.appliquer(file_, R.apercu(file_, recettes, candidatures))
    except queue_io.VerrouIndisponible:
        print("La file est occupée par un autre programme : rien n'a été écrit.")
        return OCCUPE
    print(f"Écrit : {n} changement(s). `jobhunter restore` remet la file d'avant si besoin.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
