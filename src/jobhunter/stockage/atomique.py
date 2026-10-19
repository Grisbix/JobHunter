"""Atomic JSON writing: we write alongside, then switch in one go.

A crash or a kill in the middle of a write never corrupts the file: it sees
either the old version or the new one.

os.replace fails with PermissionError under Windows when OneDrive, an antivirus or
the application still holds a handle on the file. The failure is transient: we
retry a few times before giving up.
"""

import json
import os
import threading
import time
from os import PathLike
from pathlib import Path


def ecrire_json(path: str | PathLike[str], obj: object) -> None:
    """Writes `obj` as JSON atomically: temporary file then os.replace.

    A concurrent read sees the old file or the new one, never a half-written
    file. The replacement is retried if Windows refuses it for a moment.

    Args:
        path: the file to write.
        obj: what is serialised (UTF-8, indent 1).
    """
    path = Path(path)
    # A temporary file OWN to this writer: two processes writing the same file
    # at the same moment no longer steal each other's (Codex audit of 19/10). The last
    # replacement wins; the caller's lock, if one is needed, decides the order.
    tmp = path.with_name(f"{path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
    try:
        tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")
        for essai in range(6):
            try:
                os.replace(str(tmp), str(path))
                return
            except PermissionError:
                if essai == 5:
                    raise
                time.sleep(0.5 * (essai + 1))
    finally:
        tmp.unlink(missing_ok=True)
