"""jobhunter.documents.cv_auto — Automatic CV touch-ups, without an LLM, from a fact bank.

Formerly Scripts/cv_auto.py.

WHY. An offer's CV came out of the template as is, apart from the title. A Helexia
posting (solar, Spain) received "Espagnol (débutant)" and no mention of investments
in renewables — although the user has done some. The tailor-made version written by
hand (CV/Sur_mesure) solves the case, but costs an hour and tokens per offer; the
pipeline prepares thirty a day.

THE PRINCIPLE. `CV/Faits.json` lists facts VALIDATED by the user, each with its
triggers (patterns searched in the posting) and its touch-ups (same operations as
CV/Sur_mesure). This module picks the facts the posting calls for and returns the
touch-ups. It writes NOTHING that is not in the bank: no invention possible, and the
same CV from one day to the next.

THE PAGE. Adding a line often overflows. `allegements` lists the template's lines
that can be removed, in order; tailor_application removes them one by one as long as
the PDF is longer than one page.

Run:
  python JobHunter.pyw cv-auto --essai "posting text"     # facts kept for this text
  python JobHunter.pyw cv-auto --liste                    # the bank and its state
"""

import json
import re
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

from jobhunter import log as _journal
from jobhunter import root as _racine

_log = _journal.journal(__name__)


def _chemin() -> Path:
    from jobhunter import paths as chemins

    return chemins.ROOT / "CV" / _racine.nom("Faits.json")


@lru_cache(maxsize=1)
def banque() -> dict[str, Any]:
    """The bank, read once per process.

    {} if missing or unreadable: without a bank, the CV comes out of the template as
    before — never a blocking error.
    """
    try:
        b: dict[str, Any] = json.loads(_chemin().read_text(encoding="utf-8"))
        return b
    except (OSError, ValueError) as e:
        _log.info(f"  ! CV/Faits.json illisible ({type(e).__name__}) — CV sans faits automatiques")
        return {}


def faits_retenus(texte: str | None, b: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """The valid facts one of whose triggers appears in `texte`, by priority."""
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
    """Touch-ups in the CV/Sur_mesure format for a posting.

    `allege`: number of `allegements` lines to remove (0 = none).
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
    """Number of lines that `cv_une_page` can remove to fit on one page.

    Args:
        langue: "fr" or "en".
        b: the fact bank; None = the one in CV/Faits.json.

    Returns:
        The number of available lightenings.
    """
    b = banque() if b is None else b
    return len((b.get("allegements") or {}).get(langue, []))


def main() -> int:
    """Command line: lists the fact bank or tries a posting."""
    import argparse

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]  # console : TextIOWrapper
    ap = argparse.ArgumentParser()
    ap.add_argument("--essai", default="", help="texte d'annonce a tester")
    ap.add_argument("--langue", default="fr")
    ap.add_argument("--liste", action="store_true")
    a = ap.parse_args()
    b = banque()
    if a.liste or not a.essai:
        if not b.get("faits"):
            print("Aucun fait dans CV/Facts.json : le CV part tel que le modele.")
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
