#!/usr/bin/env python3
"""exclusions.py — Les offres que l'utilisateur a ecartees, et POURQUOI.

DEUX ROLES, et le second est le plus utile.

1. Empecher le retour. Supprimer une offre de la file ne la tue pas : le scan
   suivant la retrouve a la source et la reajoute. Ecarter, c'est memoriser le
   refus pour que la reponse tienne.

2. Mesurer ce que la notation rate. Chaque motif est un desaccord entre le
   score et le jugement de l'utilisateur. « fit 10 mais dix ans d'experience » a
   revele trois bugs d'un coup : la description qui ne suivait pas le lien
   promu, les retours chariot qui cachaient l'exigence, « EXPERT » absent des
   malus de seniorite. Un refus est un cas de test offert.

La cle est l'`oid` de queue_io — « entreprise|poste » — et surtout pas l'URL,
qui change des qu'un doublon mieux classe la promeut.

Run :
  python exclusions.py                 # rapport : ce que la notation rate
  python exclusions.py --liste
"""

import argparse
import collections
import datetime as _dt
import json
import sys

from jobhunter import racine as _racine

HERE = _racine.scripts()


FICHIER = HERE / "exclusions.json"

# Motifs proposes dans l'app. Le texte libre reste possible : ces cinq-la sont
# ceux qui reviennent, et les figer permet de les compter.
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
    """Ecarte des offres. Rend le nombre de NOUVELLES exclusions.

    On garde fit et exp_requise TELS QU'ILS ETAIENT au moment du refus : c'est
    la matiere du rapport. Sans eux on saurait que l'utilisateur a dit non, pas ce que
    le score en pensait.
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
    """Annule des exclusions. Rend le nombre retire."""
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
        # Un refus sur une offre a fit eleve est un DESACCORD : le score la
        # recommandait. C'est celui-la qui apprend quelque chose.
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
