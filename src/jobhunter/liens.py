"""Document paths <-> file:/// URLs (from Scripts/jutil.py, phase 3.7).

A single implementation: the six previous copies diverged (case, accents, forgotten
`file://`). jutil re-exports them.
"""

from os import PathLike
from pathlib import Path
from urllib.parse import quote, unquote


# ── Chemins ↔ URL file:/// ───────────────────────────────────────────────────
def chemin_de(u: str | PathLike[str] | None) -> Path | None:
    """`file:///…` URL (or bare path) → Path. None if empty.

    Handles `file:///` AND `file://`: three of the six previous copies only handled
    the first form and returned a path starting with "/", hence not found.
    """
    if not u:
        return None
    s = str(u)
    for prefixe in ("file:///", "file://"):
        if s.startswith(prefixe):
            s = s[len(prefixe) :]
            break
    return Path(unquote(s))


def url_de(p: str | PathLike[str]) -> str:
    """Path → URL `file:///…`, séparateurs Windows convertis."""
    return "file:///" + quote(str(p).replace("\\", "/"), safe="/:")


def existe(u: str | PathLike[str] | None) -> bool:
    """Le document désigné par cette URL/ce chemin est-il sur le disque ?"""
    p = chemin_de(u)
    try:
        return bool(p and p.exists())
    except OSError:  # path invalid for the OS (too long, forbidden characters)
        return False
