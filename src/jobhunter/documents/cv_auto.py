"""jobhunter.documents.cv_auto — Retouches de CV automatiques, sans LLM, a partir d'une banque de faits.

Ancien Scripts/cv_auto.py.

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
  python JobHunter.pyw cv-auto --essai "texte d'annonce"     # faits retenus pour ce texte
  python JobHunter.pyw cv-auto --liste                       # la banque et son etat
"""

import json
import re
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

from jobhunter import journal as _journal

_log = _journal.journal(__name__)


def _chemin() -> Path:
    from jobhunter import chemins

    return chemins.ROOT / "CV" / "Faits.json"


@lru_cache(maxsize=1)
def banque() -> dict[str, Any]:
    """La banque lue une fois par processus.

    {} si absente ou illisible : sans banque, le CV sort du modele comme avant — jamais
    d'erreur bloquante.
    """
    try:
        b: dict[str, Any] = json.loads(_chemin().read_text(encoding="utf-8"))
        return b
    except (OSError, ValueError) as e:
        _log.info(f"  ! CV/Faits.json illisible ({type(e).__name__}) — CV sans faits automatiques")
        return {}


def faits_retenus(texte: str | None, b: dict[str, Any] | None = None) -> list[dict[str, Any]]:
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


def retouches(
    texte: str | None, langue: str = "fr", allege: int = 0, b: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Retouches au format de CV/Sur_mesure pour une annonce.

    `allege` : nombre de lignes d'`allegements` a retirer (0 = aucune).
    """
    b = banque() if b is None else b
    r: dict[str, list[Any]] = {"remplace": [], "ajoute_apres": [], "supprime": [], "faits": []}
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


def nb_allegements(langue: str = "fr", b: dict[str, Any] | None = None) -> int:
    """Nombre de lignes que `cv_une_page` peut retirer pour tenir sur une page.

    Args:
        langue: « fr » ou « en ».
        b: la banque de faits ; None = celle de CV/Faits.json.

    Returns:
        Le nombre d'allègements disponibles.
    """
    b = banque() if b is None else b
    return len((b.get("allegements") or {}).get(langue, []))


def main() -> int:
    """Ligne de commande : liste la banque de faits ou essaie une annonce."""
    import argparse

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]  # console : TextIOWrapper
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
