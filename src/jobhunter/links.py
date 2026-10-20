"""Document paths <-> file:/// URLs (from Scripts/jutil.py, phase 3.7).

A single implementation: the six previous copies diverged (case, accents, forgotten
`file://`). jutil re-exports them.
"""

import re
from os import PathLike
from pathlib import Path
from urllib.parse import quote, unquote

_LECTEUR = re.compile(r"^/*[A-Za-z]:(?:/|$)")


# ── Chemins ↔ URL file:/// ───────────────────────────────────────────────────
def chemin_de(u: str | PathLike[str] | None) -> Path | None:
    """`file:///…` URL (or bare path) → Path. None if empty.

    Handles `file:///` AND `file://`: three of the six previous copies only handled
    the first form and returned a path starting with "/", hence not found.

    A drive letter loses the slash before it (`file:///C:/x` → `C:/x`); a macOS/Linux
    path keeps its root (`file:///Users/x` → `/Users/x`, not the relative `Users/x`).
    `file:////Users/x`, what `url_de` wrote on a Mac before 2.23.1, reads the same.
    """
    if not u:
        return None
    s = str(u)
    if s.startswith("file://"):
        s = unquote(s[len("file://") :])
        if _LECTEUR.match(s):
            s = s.lstrip("/")
        elif s.startswith("/"):
            s = "/" + s.lstrip("/")
        return Path(s)
    return Path(unquote(s))


def url_de(p: str | PathLike[str]) -> str:
    """Path → URL `file:///…`, séparateurs Windows convertis.

    `C:/x` → `file:///C:/x`; `/Users/x` → `file:///Users/x` (three slashes, not four).
    """
    s = str(p).replace("\\", "/")
    return ("file://" if s.startswith("/") else "file:///") + quote(s, safe="/:")


def existe(u: str | PathLike[str] | None) -> bool:
    """Is the document designated by this URL/path on the disk?"""
    p = chemin_de(u)
    try:
        return bool(p and p.exists())
    except OSError:  # path invalid for the OS (too long, forbidden characters)
        return False
