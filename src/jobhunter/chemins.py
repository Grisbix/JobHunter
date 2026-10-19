"""jobhunter.chemins — The only place that decides where the generated documents live.

Former Scripts/chemins.py.

STATE SINCE 20/09/2026: the whole project lives in C:/Recherche_emploi, out of
OneDrive, and the documents are in the project tree. `chemins.json` does not
exist, so the resolution falls back to the root. This module no longer MOVES
anything; it keeps the indirection.

WHY KEEP IT. Eleven programs built `ROOT / "CV" / "Par_offre"` each on their
own, plus three in the app. Moving that folder out of OneDrive took eleven
consistent changes. Next time — a disk filling up, a shared folder, a second
PC — it will be one line.

    1. Scripts/chemins.json, if it exists   -> what it says
    2. otherwise the project root
    3. the folder is created when needed

The settings file is NOT tracked by git: what it describes is true of a machine,
not of a project. On a second PC without this file, everything works from the
root.

WHAT CAN BE MOVED AND WHAT CANNOT. Par_offre is an OUTPUT: 16,093 files that
`regenere_docs.py` rebuilds from the queue and the templates. Modeles, Relances
and Messages are hand-written INPUTS, 1.5 MB in total, that nothing regenerates —
they stay anchored to the root.

    from chemins import CV_PAR_OFFRE, LT_PAR_OFFRE
"""

import json
import sys
from pathlib import Path
from typing import Any

from jobhunter import paresseux as _paresseux
from jobhunter import racine as _racine

_ici = sys.modules[__name__]
# Values taken from the profile: computed on first read, not at import
# (jobhunter.paresseux). In this module, they are read through `_ici.NAME`.
_PARESSEUX: _paresseux.Fabriques = {}


def __getattr__(nom: str) -> Any:
    return _paresseux.lire(_ici, _PARESSEUX, nom)


HERE = _racine.scripts()
ROOT = HERE.parent

# Reglage de machine. Absent = comportement historique.
CONFIG = HERE / "chemins.json"


def _base() -> Path:
    """Root of the generated documents. Never raises: failing that, the project root."""
    try:
        cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
        p = (cfg.get("documents") or "").strip()
        if p:
            return Path(p)
    except (FileNotFoundError, ValueError, OSError):
        pass
    return ROOT


_PARESSEUX["BASE"] = lambda: _base()

# ── Genere, volumineux, deplacable ──────────────────────────────────────────
_PARESSEUX["CV_PAR_OFFRE"] = lambda: _ici.BASE / "CV" / "Par_offre"
_PARESSEUX["LT_PAR_OFFRE"] = lambda: _ici.BASE / "Lettres" / "Par_offre"

# ── Hand-written, tiny, STAYS in OneDrive ────────────────────────────────────
# Anchored on ROOT and not on BASE: moving the templates would save nothing
# and would take them out of the backup. The opposite of what we want.
CV_MODELES = ROOT / "CV" / "Modèles"
LT_RELANCES = ROOT / "Lettres" / "Relances"
LT_MESSAGES = ROOT / "Lettres" / "Messages"

# Letter bodies written by hand for ONE offer. The generic template serves
# 5374 postings and cannot say anything specific about any of them; when an offer
# deserves to be worked on — a direct send to two named recruiters, for
# example — the body is written here and `tailor_letter` uses it instead of
# its own. The header, the date, the subject, the salutation and the closing stay
# generated: they are the ones that know how to name the recipient and agree the
# reprise.
#
# INPUT, hence anchored on ROOT and never touched by regenere_docs.py.
LT_SUR_MESURE = ROOT / "Lettres" / "Sur_mesure"

# CV touch-ups for ONE offer: same principle as the letter. Without this folder,
# a touch-up was made in CV/Par_offre — an OUTPUT, which regenere_docs.py
# rebuilds entirely: it disappeared at the next regeneration.
CV_SUR_MESURE = ROOT / "CV" / "Sur_mesure"


def preparer() -> tuple[Path, Path]:
    """Creates the output folders. Called by the programs that write."""
    for d in (_ici.CV_PAR_OFFRE, _ici.LT_PAR_OFFRE):
        d.mkdir(parents=True, exist_ok=True)
    return _ici.CV_PAR_OFFRE, _ici.LT_PAR_OFFRE


if __name__ == "__main__":
    import sys

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]  # console : TextIOWrapper
    etat = f"chemins.json → {_ici.BASE}" if CONFIG.exists() else "defaut : la racine du projet"
    print(f"source du reglage : {etat}")
    for nom, p in (
        ("CV/Par_offre", _ici.CV_PAR_OFFRE),
        ("Lettres/Par_offre", _ici.LT_PAR_OFFRE),
        ("CV/Modeles", CV_MODELES),
        ("Lettres/Relances", LT_RELANCES),
        ("Lettres/Messages", LT_MESSAGES),
        ("Lettres/Sur_mesure", LT_SUR_MESURE),
        ("CV/Sur_mesure", CV_SUR_MESURE),
    ):
        n = len(list(p.glob("*"))) if p.exists() else 0
        print(f"  {nom:20} {'✓' if p.exists() else '✗'} {n:6} fichiers  {p}")
