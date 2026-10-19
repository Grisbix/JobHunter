#!/usr/bin/env python3
"""controle_dossiers.py — Les dossiers (CV + lettre) sont-ils prêts à partir ?

Passe en revue les offres qui ont un dossier et contrôle les FICHIERS FINAUX (voir
jobhunter.documents.controle) : pièce présente, PDF lisible avec du texte, une page,
coordonnées du profil présentes, aucun gabarit oublié. Lecture seule : rien n'est
modifié, ni la file ni les documents.

Les candidatures déjà dans le suivi sont ignorées : leur dossier est parti.

Run :
  python JobHunter.pyw controle              # toutes les offres à dossier
  python JobHunter.pyw controle --fit 8      # seulement fit >= 8
"""

import argparse
import collections
import sys

from jobhunter.documents.controle import controler_dossier
from jobhunter.profil import identite
from jobhunter.stockage import file as queue_io
from jobhunter.stockage import suivi as suivi_io


def main(argv=None):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="contrôle les dossiers avant envoi (lecture seule)")
    ap.add_argument("--fit", type=int, default=0, help="seulement les offres de fit >= N")
    a = ap.parse_args(argv)

    suivi = suivi_io.charger()
    ident = identite()
    offres = [
        o
        for o in queue_io.charger(descriptions=False)
        if (o.get("cv") or o.get("lettre"))
        and queue_io.oid(o) not in suivi
        and int(o.get("fit") or 0) >= a.fit
    ]
    offres.sort(key=lambda o: -(o.get("fit_fin") or o.get("fit") or 0))
    types = collections.Counter()
    a_revoir = 0
    for o in offres:
        problemes = controler_dossier(o, ident)
        if not problemes:
            continue
        a_revoir += 1
        print(f"✗ [{o.get('fit')}] {o.get('entreprise', '')} — {o.get('poste', '')}")
        for p in problemes:
            print(f"    {p}")
            types[p.split(" : ")[0]] += 1
    print(
        f"\n{len(offres)} dossier(s) contrôlé(s) : {len(offres) - a_revoir} prêt(s), {a_revoir} à revoir"
    )
    for t, n in types.most_common():
        print(f"  {n:4}  {t}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
