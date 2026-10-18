"""Chemins de documents <-> URL file:/// (venus de Scripts/jutil.py, phase 3.7).

Une seule implementation : les six copies d'avant divergeaient (casse, accents,
`file://` oublie). jutil les re-exporte.
"""

from pathlib import Path
from urllib.parse import quote, unquote


# ── Chemins ↔ URL file:/// ───────────────────────────────────────────────────
def chemin_de(u):
    """URL `file:///…` (ou chemin nu) → Path. None si vide.

    Gere `file:///` ET `file://` : trois des six copies precedentes ne
    traitaient que la premiere forme et rendaient un chemin commencant par
    « / », donc introuvable.
    """
    if not u:
        return None
    s = str(u)
    for prefixe in ("file:///", "file://"):
        if s.startswith(prefixe):
            s = s[len(prefixe) :]
            break
    return Path(unquote(s))


def url_de(p):
    """Path → URL `file:///…`, séparateurs Windows convertis."""
    return "file:///" + quote(str(p).replace("\\", "/"), safe="/:")


def existe(u):
    """Le document désigné par cette URL/ce chemin est-il sur le disque ?"""
    p = chemin_de(u)
    try:
        return bool(p and p.exists())
    except OSError:  # chemin invalide pour l'OS (trop long, caracteres interdits)
        return False
