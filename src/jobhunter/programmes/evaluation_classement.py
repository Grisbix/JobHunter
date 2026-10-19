#!/usr/bin/env python3
"""evaluation_classement.py — Does the ranking put at the top the offers I judge good?

Compares the engine's score (decimal fit) with the tracking's judgements: postulé,
relancé, entretien, refus, à postuler = relevant; mauvaise, pas intéressé = useless
(see jobhunter.scoring.evaluation). Displays the AUC with its interval, the precision
of the top ones, and the offers where the ranking is most wrong. Read-only.

`--enregistrer` keeps the result as a REFERENCE (Scripts/_evaluation.json): a scoring
variant is then judged against it, in addition to the bench.

The more judgements there are, the surer the figure: marking "mauvaise" or "pas
intéressé" in the application, in passing, enriches the reference.

Run:
  python JobHunter.pyw evaluation
  python JobHunter.pyw evaluation --enregistrer
"""

import argparse
import datetime
import json
import sys

from jobhunter import racine as _racine
from jobhunter.scoring.evaluation import evaluer
from jobhunter.stockage import file as queue_io
from jobhunter.stockage import suivi as suivi_io


def main(argv=None):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="évalue le classement sur les jugements du suivi")
    ap.add_argument("--enregistrer", action="store_true", help="garde ce résultat comme référence")
    a = ap.parse_args(argv)

    r = evaluer(queue_io.charger(descriptions=False), suivi_io.charger(), queue_io.oid)
    print(
        f"Offres jugées encore en file : {r['pertinentes']} pertinentes, {r['inutiles']} inutiles"
    )
    if r["auc"] is None:
        print("Il faut au moins une offre de chaque sorte pour mesurer le classement.")
        return 0
    bas, haut = r["intervalle"]
    print(f"AUC {r['auc']:.2f}  (intervalle à 90 % : {bas:.2f} – {haut:.2f} ; 0,5 = au hasard)")
    print(f"Précision des {r['pertinentes']} premières : {r['precision']:.0%}")
    if r["pertinentes"] + r["inutiles"] < 60:
        print(
            "  ! Peu de jugements : le chiffre est incertain. Marquer « mauvaise » ou "
            "« pas intéressé » dans l'application enrichit la référence."
        )
    print("\nInutiles les MIEUX notées (le classement les surestime) :")
    for n, ent, poste in r["pires"]["inutiles_hautes"]:
        print(f"  {n:5.1f}  {ent} — {poste}")
    print("Pertinentes les MOINS bien notées (le classement les sous-estime) :")
    for n, ent, poste in r["pires"]["pertinentes_basses"]:
        print(f"  {n:5.1f}  {ent} — {poste}")

    chemin = _racine.scripts() / "_evaluation.json"
    try:
        ref = json.loads(chemin.read_text(encoding="utf-8"))
        print(
            f"\nRéférence du {ref['le']} : AUC {ref['auc']:.2f} sur "
            f"{ref['pertinentes']} + {ref['inutiles']} jugements"
            f" → écart {r['auc'] - ref['auc']:+.2f}"
        )
    except (OSError, ValueError, KeyError):
        ref = None
    if a.enregistrer:
        chemin.write_text(
            json.dumps(
                {
                    "le": datetime.date.today().isoformat(),
                    "auc": r["auc"],
                    "intervalle": r["intervalle"],
                    "precision": r["precision"],
                    "pertinentes": r["pertinentes"],
                    "inutiles": r["inutiles"],
                },
                ensure_ascii=False,
                indent=1,
            ),
            encoding="utf-8",
        )
        print(f"Référence enregistrée : {chemin.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
