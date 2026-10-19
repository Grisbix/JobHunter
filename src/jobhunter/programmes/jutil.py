#!/usr/bin/env python3
"""jutil.py — shared utilities: ATOMIC writing, lock, paths, text.

A crash/kill in the middle of a write never corrupts apply_queue.json.

This module also exists to host the helpers that each program rewrote on its own.
It is not aesthetics: the copies DIVERGE, and that divergence has already produced
real bugs — a case-sensitive comparison on one side and insensitive on the other, an
accent normalisation present here and missing there, two `file:///` decodings of which
one forgot the `file://` form.
"""

from pathlib import Path

# The lock lives in jobhunter.stockage.verrou; these names stay the usual ones.
# Chemins <-> URL file:/// : jobhunter.liens (phase 3.7), noms inchanges.
from jobhunter.liens import chemin_de, existe, url_de  # noqa: E402, F401
from jobhunter.stockage import atomique as _atomique  # noqa: E402
from jobhunter.stockage.verrou import (  # noqa: E402, F401
    _TENUS,
    _fverrou,
    _pid_vivant,
    garder,
    prendre_verrou,
    rendre_verrou,
    tenu,
)
from jobhunter.texte import cle, sans_accent, verifier_motifs  # noqa: E402, F401


def jwrite(path, obj, _brut=False):
    """Atomic write: we write next to it, then switch in one go.

    TWO GUARDS, each for an observed failure.

    1. The QUEUE must never take the descriptions back inline. They live in
       descriptions.json since the separation; queue_io.charger() re-injects them
       in memory for the work, and queue_io.sauver() moves them out before writing.
       Eleven programs call jwrite(QUEUE, ...) directly: each of them put the texts
       back into the file, and the queue had grown back from 2.9 MB to 15.9 MB
       without anything reporting the regression. Rather than counting on eleven
       callers to think of it, we redirect here.

    2. os.replace fails with PermissionError on Windows when OneDrive, an antivirus
       or the app still holds a handle on the file. The failure is transient: we
       retry a few times before giving up.
    """
    path = Path(path)
    # _brut: queue_io has ALREADY done the separation and hands control back to us for
    # the write. Without this flag, its own write went through the guard again and
    # called itself forever (RecursionError) as soon as the path was not the
    # canonical file — a test file, for example.
    if (
        not _brut
        and path.name == "apply_queue.json"
        and isinstance(obj, list)
        and any(isinstance(x, dict) and (x.get("description") or "").strip() for x in obj)
    ):
        from jobhunter.stockage import file

        return file.sauver(obj, path)
    _atomique.ecrire_json(path, obj)
