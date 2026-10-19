#!/usr/bin/env python3
"""verifie_redites.py — Looks for repetitions in the generated letters.

WHY. Repetition defects are seen when reading, never when the generator writes: each
piece is correct in isolation, it is their assembly that stammers. Three examples
spotted by hand on a single letter:

    "la trésorerie et le financement, l'analyse financière, la modélisation
      financière et le contrôle de gestion, et je pratique…"   three "et"
    "l'analyse financière, la modélisation financière"         same ending
    "Ma formation correspond…, et j'y ajoute…, et une bonne…"  two "et"

Re-reading one letter by hand finds them. Re-reading 3900 letters, no. This program
counts them.

WHAT IT REPORTS:
  - a sentence carrying two "et" (or "and") or more;
  - two enumeration items ending with the same word;
  - a content word used three times or more in the body.

It corrects nothing: it returns the list, to be fixed in tailor_application.py.

Run:
  python JobHunter.pyw verifie_redites                    # 40 letters at random
  python JobHunter.pyw verifie_redites --toutes
  python JobHunter.pyw verifie_redites --fichier "Lettres/Par_offre/xxx.docx"
"""

import argparse
import collections
import random
import sys
from pathlib import Path

from jobhunter import racine as _racine

HERE = _racine.scripts()
ROOT = HERE.parent

from jobhunter import chemins

sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]  # console : TextIOWrapper

from jobhunter.documents.relecture import (  # noqa: E402  (moved in 2.13, relecture)
    defauts,
    texte,
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--toutes", action="store_true")
    ap.add_argument("--fichier")
    ap.add_argument("--echantillon", type=int, default=40)
    a = ap.parse_args()

    if a.fichier:
        cibles = [Path(a.fichier) if Path(a.fichier).is_absolute() else ROOT / a.fichier]
    else:
        toutes = sorted(chemins.LT_PAR_OFFRE.glob("*.docx"))
        toutes = [p for p in toutes if not p.name.startswith("~$")]
        cibles = toutes if a.toutes else random.sample(toutes, min(a.echantillon, len(toutes)))

    print(f"{len(cibles)} lettre(s) examinee(s)\n")
    compte = collections.Counter()
    sales = 0
    for p in cibles:
        try:
            d = defauts(texte(p))
        except Exception as e:
            print(f"  ! {p.name[:60]} : {type(e).__name__}")
            continue
        if not d:
            continue
        sales += 1
        if len(cibles) <= 5 or sales <= 6:
            print(f"── {p.name[:72]}")
            for x in d:
                print(f"     {x}")
        for x in d:
            compte[x.split(" :")[0].split(" revient")[0]] += 1

    print(f"\n{sales} lettre(s) avec au moins une redite sur {len(cibles)}")
    if compte:
        print("\nLes redites les plus frequentes :")
        for x, n in compte.most_common(10):
            print(f"  {n:4}  {x}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
