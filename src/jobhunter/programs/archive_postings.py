#!/usr/bin/env python3
"""archive_postings.py — Keeps a copy of the posting of every application.

For each offer of the tracking marked postulé, relancé, entretien, refus or à
postuler, writes the posting's copy (PDF + .txt) to Letters/Postings if it has none
yet. Nothing is fetched from the web: the text is the queue's. Never rewrites a copy:
it is the version applied to. See jobhunter.postings.

Run:
  python JobHunter.pyw postings          # write the missing copies
  python JobHunter.pyw postings --dry    # list them only
"""

import argparse
import sys

from jobhunter import postings
from jobhunter.storage import applications as suivi_io
from jobhunter.storage import queue as queue_io


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[1])
    ap.add_argument("--dry", action="store_true", help="lister sans rien écrire")
    a = ap.parse_args(argv)
    suivi = suivi_io.charger()
    todo = postings.a_archiver(queue_io.charger(), suivi, queue_io.oid)
    faites, courtes = 0, 0
    for o in todo:
        if a.dry:
            print(f"  à garder : {queue_io.oid(o)[:80]}")
            continue
        p = postings.archiver(o)
        if p is None:
            courtes += 1
        else:
            faites += 1
            print(f"  ✓ {p.name}")
    print(
        f"{faites} annonce(s) gardée(s) dans {postings.dossier().name}/"
        + (f", {courtes} trop courte(s) pour l'instant" if courtes else "")
        + (f" — {len(todo)} à garder (--dry)" if a.dry else "")
    )
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    sys.exit(main())
