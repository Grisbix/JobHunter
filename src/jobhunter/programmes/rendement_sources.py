#!/usr/bin/env python3
"""rendement_sources.py — Ce que chaque source de collecte a rapporté, et pourquoi.

Lit le journal `Scripts/_rendement.jsonl` (une ligne par collecte, écrite par
`jobhunter.sources`) et en fait le bilan par source sur les derniers jours : collectes,
offres ramenées, nouvelles, pertinentes (fit >= 8), temps passé, et les verdicts —
« refusé » et « limité » disent qu'une collecte vide ne veut PAS dire « rien de neuf ».

Lecture seule. Une source refusée à chaque collecte se signale : la retirer de --all
se décide à la main (Talent et Indeed l'ont été le 03/10 sur ce genre de constat).

Run :
  python JobHunter.pyw rendement              # 14 derniers jours
  python JobHunter.pyw rendement --jours 30
"""

import argparse
import datetime
import sys

from jobhunter import racine as _racine
from jobhunter.sources import rendement as R


def main(argv=None):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="rendement de chaque source (lecture seule)")
    ap.add_argument("--jours", type=int, default=14, help="période, en jours (défaut 14)")
    a = ap.parse_args(argv)

    chemin = _racine.scripts() / "_rendement.jsonl"
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


if __name__ == "__main__":
    sys.exit(main())
