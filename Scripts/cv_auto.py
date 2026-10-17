#!/usr/bin/env python3
"""cv_auto.py — Retouches de CV automatiques, sans LLM, a partir d'une banque de faits.

POURQUOI. Le CV d'une offre sortait du modele tel quel, a l'intitule pres. Une
annonce Helexia (solaire, Espagne) recevait « Espagnol (débutant) » et aucune
mention des investissements dans les renouvelables — alors que l'utilisateur en a fait.
Le sur-mesure ecrit a la main (CV/Sur_mesure) regle le cas, mais coute une
heure et des tokens par offre ; le pipeline en prepare trente par jour.

LE PRINCIPE. `CV/Faits.json` liste des faits VALIDES par l'utilisateur, chacun avec
ses declencheurs (motifs cherches dans l'annonce) et ses retouches (memes
operations que CV/Sur_mesure). Ce module choisit les faits que l'annonce
appelle et rend les retouches. Il n'ecrit RIEN qui ne soit dans la banque :
pas d'invention possible, et le meme CV d'un jour a l'autre.

LA PAGE. Ajouter une ligne fait souvent deborder. `allegements` liste les
lignes du modele qu'on peut retirer, dans l'ordre ; tailor_application les
retire une par une tant que le PDF fait plus d'une page.

Run :
  python cv_auto.py --essai "texte d'annonce"     # faits retenus pour ce texte
  python cv_auto.py --liste                       # la banque et son etat
"""

import json
import re
import sys
from functools import lru_cache
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


def _chemin():
    import chemins

    return chemins.ROOT / "CV" / "Faits.json"


@lru_cache(maxsize=1)
def banque():
    """La banque lue une fois par processus. {} si absente ou illisible : sans
    banque, le CV sort du modele comme avant — jamais d'erreur bloquante."""
    try:
        return json.loads(_chemin().read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        print(f"  ! CV/Faits.json illisible ({type(e).__name__}) — CV sans faits automatiques")
        return {}


def faits_retenus(texte, b=None):
    """Les faits valides dont un declencheur apparait dans `texte`, par priorite."""
    b = banque() if b is None else b
    t = texte or ""
    out = []
    for f in b.get("faits", []):
        if not f.get("valide"):
            continue
        if any(re.search(d, t, re.I) for d in f.get("declencheurs", [])):
            out.append(f)
    out.sort(key=lambda f: -int(f.get("priorite", 0)))
    return out


def retouches(texte, langue="fr", allege=0, b=None):
    """Retouches au format de CV/Sur_mesure pour une annonce.

    `allege` : nombre de lignes d'`allegements` a retirer (0 = aucune)."""
    b = banque() if b is None else b
    r = {"remplace": [], "ajoute_apres": [], "supprime": [], "faits": []}
    for f in faits_retenus(texte, b):
        ops = f.get(langue) or []
        for op in ops:
            if op.get("op") == "remplace":
                r["remplace"].append([op["ancre"], op["texte"]])
            elif op.get("op") == "ajoute_apres":
                r["ajoute_apres"].append([op["ancre"], op["texte"]])
        if ops:
            r["faits"].append(f["id"])
    r["supprime"] = list((b.get("allegements") or {}).get(langue, []))[: max(0, allege)]
    return r


def nb_allegements(langue="fr", b=None):
    b = banque() if b is None else b
    return len((b.get("allegements") or {}).get(langue, []))


def main():
    import argparse

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--essai", default="", help="texte d'annonce a tester")
    ap.add_argument("--langue", default="fr")
    ap.add_argument("--liste", action="store_true")
    a = ap.parse_args()
    b = banque()
    if a.liste or not a.essai:
        for f in b.get("faits", []):
            etat = "valide " if f.get("valide") else "A VALIDER"
            print(
                f"  [{etat}] {f['id']:28} prio {f.get('priorite', 0):>2} · "
                f"{len(f.get('declencheurs', []))} declencheurs"
            )
        return 0
    r = retouches(a.essai, a.langue)
    print("faits retenus :", r["faits"] or "aucun")
    for x in r["ajoute_apres"]:
        print("  + ", x[1])
    for x in r["remplace"]:
        print("  ~ ", x[1])
    return 0


if __name__ == "__main__":
    sys.exit(main())
