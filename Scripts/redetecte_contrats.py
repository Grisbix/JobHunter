#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""redetecte_contrats.py — Relit le contrat de chaque offre depuis sa description.

POURQUOI. Le detecteur ne voyait pas les fiches en TABLEAU (« Type de contrat »
suivi de blancs, sans deux-points, comme sur eFinancialCareers) et tombait alors
sur le premier mot-cle venu — souvent le « CDD » d'une phrase de boilerplate :
« …et d'opportunites en alternance, VIE, CDD et CDI ». Quatre STAGES du Credit
Agricole se retrouvaient etiquetes CDD, et remontaient en tete du classement.

Le detecteur est corrige ; ce programme applique la correction aux offres deja
en file, que le scan ne repassera pas.

L'intitule reste PRIORITAIRE sur la description : « Stage - Analyste ESG » dit
ce qu'est le poste, et personne ne se trompe en ecrivant son propre titre.

Run :
  python redetecte_contrats.py --dry
  python redetecte_contrats.py
"""
import sys
import argparse
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from job_sources import contrat_de_la_description, contrat_du_titre


def contrat_correct(o):
    """Contrat le mieux fonde pour cette offre, ou None si rien de sûr."""
    par_titre = contrat_du_titre(o.get("poste") or "", o.get("source") or "")
    if par_titre:
        return par_titre
    return contrat_de_la_description(o.get("description") or "", "") or None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()

    import queue_io
    if a.dry:
        q = queue_io.charger()
        chg = []
        for o in q:
            c = contrat_correct(o)
            if c and c != (o.get("contrat") or "").strip():
                chg.append((o, c))
        print(f"{len(chg)} offre(s) changeraient de contrat\n")
        import collections
        cpt = collections.Counter((o.get("contrat") or "vide", c) for o, c in chg)
        for (avant, apres), n in cpt.most_common(12):
            print(f"  {n:5}  {avant:12} -> {apres}")
        print("\nExemples a fit >= 8 :")
        for o, c in sorted(chg, key=lambda x: -(x[0].get("fit") or 0))[:12]:
            print(f"  fit {o.get('fit')}  {(o.get('contrat') or 'vide'):10} -> {c:11} "
                  f"{(o.get('entreprise') or '')[:22]:22} {(o.get('poste') or '')[:38]}")
        print("\n[DRY] rien n'a ete ecrit.")
        return 0

    try:
        with queue_io.transaction() as q:
            n = 0
            for o in q:
                c = contrat_correct(o)
                if c and c != (o.get("contrat") or "").strip():
                    o["contrat"] = c
                    n += 1
            print(f"{n} contrat(s) corrige(s).")
    except queue_io.VerrouIndisponible as e:
        print(f"! {e}")
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
