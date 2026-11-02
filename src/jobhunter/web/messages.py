"""The window's error messages: a sentence, never a Python exception's name.

The page showed « PermissionError: [Errno 13] … » when Word held a CV open; the user
reads a sentence that says what to do (audit of the interface, 2026-11-02).
"""

from __future__ import annotations


def echec(e: BaseException) -> str:
    """What went wrong with a file or a value, said to the user."""
    if isinstance(e, PermissionError):
        return "Le fichier est ouvert dans un autre programme (Word ?) : ferme-le puis réessaie."
    if isinstance(e, FileNotFoundError):
        return "Fichier introuvable : il a peut-être été déplacé ou supprimé."
    if isinstance(e, OSError):
        return f"Le disque a refusé l'écriture : {e.strerror or e}."
    detail = str(e).strip()
    return f"Échec : {detail}" if detail else "Échec."
