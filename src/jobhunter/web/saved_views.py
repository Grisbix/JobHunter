"""Saved views of the web offers screen, and the columns it shows.

The web page's counterpart of app.views: a view keeps the screen's filters and sort
under a name; the visible columns are remembered on their own. They live in
`_vues_web.json` of the active profile's data folder, apart from the desktop's
`_vues.json`: the two tables filter differently (the desktop by column values), and
the desktop rewrites its file with its own keys only.
"""

import json
from pathlib import Path
from typing import Any

from jobhunter import root

FICHIER = "_vues_web.json"

# The filters a view may keep, with their type (anything else is dropped).
FILTRES: dict[str, type] = {
    "texte": str,
    "statut": str,
    "zone": str,
    "domaine": str,
    "contrat": str,
    "pays": str,
    "region": str,
    "fit_min": float,
    "tri": str,
}

# Optional columns of the offers table; the offer itself is always shown.
COLONNES = (
    "lieu",
    "zone",
    "date",
    "suivi",
    "domaine",
    "contrat",
    "pays",
    "region",
    "publiee",
    "trouvee",
    "verifiee",
    "signal",
)
PAR_DEFAUT = ["lieu", "zone", "date", "suivi"]


def _chemin(chemin: Path | None = None) -> Path:
    return chemin if chemin is not None else root.scripts() / FICHIER


def lire(chemin: Path | None = None) -> dict[str, Any]:
    """{"vues": {name: filters}, "colonnes": [...]}; defaults when absent or unreadable."""
    try:
        d = json.loads(_chemin(chemin).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        d = {}
    if not isinstance(d, dict):
        d = {}
    vues = d.get("vues")
    if not isinstance(vues, dict):
        vues = {}
    return {
        "vues": {str(n): filtres(v) for n, v in vues.items()},
        "colonnes": colonnes(d.get("colonnes")) or list(PAR_DEFAUT),
    }


def _ecrire(d: dict[str, Any], chemin: Path | None = None) -> None:
    p = _chemin(chemin)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(p)


def filtres(v: Any) -> dict[str, Any]:
    """Only the known filters, with their type; a bad value is dropped."""
    out: dict[str, Any] = {}
    for cle, genre in FILTRES.items():
        if not isinstance(v, dict) or cle not in v:
            continue
        try:
            out[cle] = genre(v[cle] or (0 if genre is float else ""))
        except (TypeError, ValueError):
            continue
    return out


def colonnes(cols: Any) -> list[str] | None:
    """Known columns in the table's order; None if unusable."""
    if not isinstance(cols, list):
        return None
    garde = [c for c in COLONNES if c in cols]
    return garde or None


def enregistrer(nom: str, vue: Any, chemin: Path | None = None) -> bool:
    """Keeps the filters `vue` under `nom` (same name: replaced); False if no name."""
    nom = str(nom or "").strip()
    if not nom:
        return False
    d = lire(chemin)
    d["vues"][nom] = filtres(vue)
    _ecrire(d, chemin)
    return True


def supprimer(nom: str, chemin: Path | None = None) -> bool:
    """Forgets the view `nom`; False if there is none."""
    d = lire(chemin)
    if d["vues"].pop(nom, None) is None:
        return False
    _ecrire(d, chemin)
    return True


def memoriser_colonnes(cols: Any, chemin: Path | None = None) -> bool:
    """Remembers the visible columns; False if none is known."""
    garde = colonnes(cols)
    if garde is None:
        return False
    d = lire(chemin)
    d["colonnes"] = garde
    _ecrire(d, chemin)
    return True
