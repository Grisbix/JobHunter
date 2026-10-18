#!/usr/bin/env python3
"""reclasse_domaines.py — Recalcule le `domaine` de chaque offre.

POURQUOI. Le classificateur retombait sur « ESG_Finance_Durable » par DEFAUT :
2151 offres sur 2818 portaient ce domaine sans qu'aucun mot-cle ESG figure dans
leur intitule — « Analyste DSI », « Financial Controller », « Business
Analyst ». Elles recevaient donc le CV ESG, et depuis que la lettre choisit son
paragraphe de parcours par domaine, une lettre qui s'ouvre sur la finance
durable. Devant une compagnie petroliere qui cherche un analyste economique,
ca parle a cote.

Le defaut est desormais « Finance », neutre. Ce programme applique la
correction aux offres deja en file.

Le domaine pilote deux choses : la VARIANTE de CV et le paragraphe de parcours
de la lettre. Les documents deja generes ne sont PAS refaits ici — ils le
seront a la prochaine regeneration, ou a la demande.

Run :
  python reclasse_domaines.py --dry
  python reclasse_domaines.py
"""

import argparse
import collections
import sys

from jobhunter import racine as _racine

HERE = _racine.scripts()

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from jobhunter.programmes.scrape_jobs import classify_domaine


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()

    from jobhunter.stockage import file as queue_io

    if a.dry:
        q = queue_io.charger(descriptions=False)
        chg = [(o, classify_domaine(o.get("poste") or "")) for o in q]
        chg = [(o, d) for o, d in chg if d != (o.get("domaine") or "")]
        print(f"{len(chg)} offre(s) changeraient de domaine\n")
        c = collections.Counter((o.get("domaine") or "vide", d) for o, d in chg)
        for (av, ap_), n in c.most_common(12):
            print(f"  {n:5}  {av:22} -> {ap_}")
        print("\nExemples a fit >= 8 :")
        for o, d in sorted(chg, key=lambda x: -(x[0].get("fit") or 0))[:10]:
            print(
                f"  fit {o.get('fit')}  {(o.get('domaine') or ''):22} -> {d:22} "
                f"{(o.get('poste') or '')[:40]}"
            )
        print("\n[DRY] rien n'a ete ecrit.")
        return 0

    try:
        with queue_io.transaction(descriptions=False) as q:
            n = 0
            for o in q:
                d = classify_domaine(o.get("poste") or "")
                if d != (o.get("domaine") or ""):
                    o["domaine"] = d
                    n += 1
            print(f"{n} domaine(s) corrige(s).")
            print(
                "Les CV et lettres deja generes gardent l'ancienne variante "
                "jusqu'a leur prochaine regeneration."
            )
    except queue_io.VerrouIndisponible as e:
        print(f"! {e}")
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
