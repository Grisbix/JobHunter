#!/usr/bin/env python3
"""controle_dossiers.py — Are the folders (CV + letter) ready to go?

Goes through the offers that have a folder and checks the FINAL FILES (see
jobhunter.documents.checks): document present, readable PDF with text, one page,
profile contact details present, no forgotten template. Read-only: nothing is
changed, neither the queue nor the documents.

Applications already in the tracking are ignored: their folder has gone.

Run:
  python JobHunter.pyw check              # all the offers with a folder
  python JobHunter.pyw check --fit 8      # only fit >= 8
"""

import argparse
import collections
import sys

from jobhunter.documents.checks import controler_dossier
from jobhunter.profile import identite
from jobhunter.storage import applications as suivi_io
from jobhunter.storage import queue as queue_io


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
