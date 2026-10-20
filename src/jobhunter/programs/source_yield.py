#!/usr/bin/env python3
"""rendement_sources.py — What each collection source brought back, and why.

Reads the log `Scripts/_rendement.jsonl` (one line per collection, written by
`jobhunter.sources`) and summarises it per source over the last days: collections,
offers brought back, new, relevant (fit >= 8), time spent, and the verdicts —
"refusé" and "limité" say that an empty collection does NOT mean "nothing new".

Read-only. A source refused at every collection is flagged: removing it from --all is
decided by hand (Talent and Indeed were on 03/10 on this kind of finding).

Run:
  python JobHunter.pyw yield              # last 14 days
  python JobHunter.pyw yield --jours 30
  python JobHunter.pyw yield --execution 20261021-080012-a3f9   # one run (run_id)
"""

import argparse
import datetime
import sys

from jobhunter import root as _racine
from jobhunter.sources import source_yield as R


def main(argv=None):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="rendement de chaque source (lecture seule)")
    ap.add_argument("--jours", type=int, default=14, help="période, en jours (défaut 14)")
    ap.add_argument("--execution", help="ce qu'a ramené une exécution (son identifiant)")
    a = ap.parse_args(argv)

    chemin = _racine.dans(_racine.scripts(), "_rendement.jsonl")
    if a.execution:
        return execution(chemin, a.execution)
    depuis = (datetime.date.today() - datetime.timedelta(days=a.jours)).isoformat()
    total = R.bilan(R.lire_journal(chemin), depuis)
    if not total:
        print(f"Aucune collecte mesurée depuis le {depuis} ({chemin.name} absent ou vide).")
        print("Le journal se remplit à chaque collecte, à partir de JobHunter 2.4.")
        return 0
    print(f"Rendement des sources depuis le {depuis}\n")
    print(
        f"  {'source':<14}{'coll.':>6}{'ramenées':>10}{'nouv.':>7}{'pert.':>7}{'pert./h':>9}  verdicts"
    )
    for nom, t in sorted(total.items(), key=lambda kv: (-kv[1]["pertinentes"], kv[0])):
        heures = t["duree"] / 3600
        par_h = f"{t['pertinentes'] / heures:.1f}" if heures > 0.01 else "—"
        verdicts = ", ".join(f"{v} {n}" for v, n in t["verdicts"].most_common())
        print(
            f"  {nom:<14}{t['collectes']:>6}{t['ramenees']:>10}{t['nouvelles']:>7}"
            f"{t['pertinentes']:>7}{par_h:>9}  {verdicts}"
        )
    toujours_refusees = [
        n for n, t in total.items() if t["verdicts"].get(R.REFUSE, 0) == t["collectes"]
    ]
    if toujours_refusees:
        print(
            "\nRefusées à CHAQUE collecte : "
            + ", ".join(sorted(toujours_refusees))
            + " — inutile d'insister (pas de contournement) ; les retirer de --all se décide à la main."
        )
    return 0


def execution(chemin, ident: str) -> int:
    """What one run brought back: its yield lines and the offers of the queue it found."""
    lignes = [x for x in R.lire_journal(chemin) if x.get("execution") == ident]
    from jobhunter.storage import queue as queue_io

    trouvees = [o for o in queue_io.charger(descriptions=False) if o.get("execution") == ident]
    if not lignes and not trouvees:
        print(f"Exécution {ident} : inconnue (identifiants écrits à partir de JobHunter 3.10).")
        return 1
    print(f"Exécution {ident}\n")
    for x in lignes:
        for nom, m in sorted((x.get("sources") or {}).items()):
            print(
                f"  {x.get('le', '')[11:16]}  {nom:<14}{m.get('ramenees', 0):>6} ramenées"
                f"{m.get('nouvelles', 0):>6} nouvelles  {m.get('verdict', '')}"
            )
    print(f"\n{len(trouvees)} offre(s) de la file trouvée(s) par cette exécution.")
    for o in sorted(trouvees, key=lambda o: -(o.get("fit") or 0))[:15]:
        print(f"  fit {o.get('fit', '?'):>2}  {o.get('entreprise', '')} — {o.get('poste', '')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
