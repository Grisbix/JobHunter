"""The offers the user has opened in the window, and when.

`_ouvertes.json` of the active profile's data folder: {"entreprise|poste": "YYYY-MM-DD"}.
The daily triage shows only the offers never opened, and the archiving of old offers
spares every offer opened once (3.80). A lost file costs a triage shown again, nothing
more: it is a convenience, not a record like applications.json.
"""

import json
from datetime import date
from pathlib import Path

from jobhunter import root
from jobhunter.storage import atomic as _atomique

FICHIER = "_ouvertes.json"


def _chemin(chemin: Path | None = None) -> Path:
    return chemin if chemin is not None else root.scripts() / FICHIER


def lire(chemin: Path | None = None) -> dict[str, str]:
    """{oid: date of the first opening}; empty when absent or unreadable."""
    try:
        d = json.loads(_chemin(chemin).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {str(k): str(v) for k, v in d.items()} if isinstance(d, dict) else {}


def noter(oids: str | list[str], chemin: Path | None = None) -> bool:
    """Records the first opening of these offers; True if the file changed."""
    p = _chemin(chemin)
    d = lire(p)
    nouveaux = [o for o in ([oids] if isinstance(oids, str) else oids) if o and o not in d]
    if not nouveaux:
        return False
    jour = date.today().isoformat()
    d.update(dict.fromkeys(nouveaux, jour))
    try:
        # A writer's own temporary file: the window serves each page call on its own
        # thread, and two openings at once shared one « .tmp » before.
        _atomique.ecrire_json(p, d, indent=None)
    except OSError:
        return False
    return True
