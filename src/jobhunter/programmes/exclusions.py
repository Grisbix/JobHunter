#!/usr/bin/env python3
"""exclusions.py — The offers the user set aside, and WHY.

TWO ROLES, and the second is the most useful.

1. Prevent the return. Deleting an offer from the queue does not kill it: the next
   scan finds it again at the source and re-adds it. Setting aside means remembering
   the refusal so that the answer holds.

2. Measure what the scoring misses. Each reason is a disagreement between the score
   and the user's judgement. "fit 10 but ten years of experience" revealed three bugs
   at once: the description that did not follow the promoted link, the carriage
   returns that hid the requirement, "EXPERT" missing from the seniority penalties.
   A refusal is a test case offered.

The key is queue_io's `oid` — "entreprise|poste" — and above all not the URL, which
changes as soon as a better-ranked duplicate promotes it.

Run:
  python JobHunter.pyw exclusions                 # report: what the scoring misses
  python JobHunter.pyw exclusions --liste
"""

import argparse
import collections
import datetime as _dt
import json
import sys

from jobhunter import racine as _racine

HERE = _racine.scripts()


FICHIER = HERE / "exclusions.json"

# Reasons offered in the app. Free text stays possible: these five are
# the ones that come back, and fixing them allows counting them.
MOTIFS = [
    "Trop d'expérience demandée",
    "Poste trop senior",
    "Pas le bon métier",
    "Lieu impossible",
    "Entreprise qui ne m'intéresse pas",
]


def charger():
    try:
        d = json.loads(FICHIER.read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except (FileNotFoundError, ValueError):
        return {}


def est_exclu(offre, table=None):
    from jobhunter.stockage import file as queue_io

    return queue_io.oid(offre) in (charger() if table is None else table)


def ajouter(offres, motif, note=""):
    """Sets offers aside. Returns the number of NEW exclusions.

    We keep fit and exp_requise AS THEY WERE at the time of the refusal: they are the
    material of the report. Without them we would know that the user said no, not
    what the score thought of it.
    """
    from jobhunter.programmes import jutil
    from jobhunter.stockage import file as queue_io

    t = charger()
    n = 0
    today = _dt.date.today().isoformat()
    for o in offres:
        k = queue_io.oid(o)
        if k in t:
            continue
        t[k] = {
            "motif": motif,
            "note": note,
            "date": today,
            "entreprise": o.get("entreprise", ""),
            "poste": o.get("poste", ""),
            "url": o.get("url", ""),
            "fit": o.get("fit"),
            "exp_requise": o.get("exp_requise"),
            "source": o.get("source", ""),
        }
        n += 1
    if n:
        jutil.jwrite(FICHIER, t)
    return n


def retirer(cles):
    """Cancels exclusions. Returns the number removed."""
    from jobhunter.programmes import jutil

    t = charger()
    n = 0
    for k in cles:
        if t.pop(k, None) is not None:
            n += 1
    if n:
        jutil.jwrite(FICHIER, t)
    return n


def _rapport():
    t = charger()
    if not t:
        print("Aucune offre ecartee pour l'instant.")
        print("\nDans l'app : coche des offres, puis « ✕ Écarter la sélection ».")
        return 0
    print(f"{len(t)} offre(s) ecartee(s)\n")
    par_motif = collections.defaultdict(list)
    for k, v in t.items():
        par_motif[v.get("motif") or "(sans motif)"].append(v)

    print("=== ce que la notation rate ===")
    for motif, lot in sorted(par_motif.items(), key=lambda x: -len(x[1])):
        fits = [v["fit"] for v in lot if isinstance(v.get("fit"), int)]
        # A refusal on a high-fit offer is a DISAGREEMENT: the score
        # recommended it. That is the one that teaches something.
        hauts = [f for f in fits if f >= 8]
        moy = f"{sum(fits) / len(fits):.1f}" if fits else "—"
        print(f"\n  {len(lot):3} × {motif}")
        print(f"       fit moyen {moy} · {len(hauts)} offre(s) etaient a fit >= 8")
        for v in sorted(lot, key=lambda v: -(v.get("fit") or 0))[:4]:
            exp = v.get("exp_requise")
            print(
                f"       fit {v.get('fit')} exp {exp}  "
                f"{(v.get('entreprise') or '')[:22]:22} {(v.get('poste') or '')[:40]}"
            )

    desaccords = [v for v in t.values() if (v.get("fit") or 0) >= 8]
    print(f"\n=== {len(desaccords)} desaccord(s) : le score disait oui, l'utilisateur dit non ===")
    if desaccords:
        print("Chacun est un cas a examiner dans ats_match.py.")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--liste", action="store_true", help="tout afficher, ligne par ligne")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if a.liste:
        t = charger()
        print(f"{len(t)} exclusion(s)")
        for k, v in sorted(t.items(), key=lambda x: -(x[1].get("fit") or 0)):
            print(
                f"  fit {v.get('fit')} exp {v.get('exp_requise')} · {v.get('motif')}"
                f"{(' — ' + v['note']) if v.get('note') else ''}\n      {k}"
            )
        return 0
    return _rapport()


if __name__ == "__main__":
    sys.exit(main())
