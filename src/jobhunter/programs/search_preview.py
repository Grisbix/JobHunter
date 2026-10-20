"""Which offers of the queue a title filter keeps — without collecting or changing anything.

    python -m jobhunter.programs.search_preview [--profil candidate.json]

Prints, as JSON, the identity (`entreprise|poste`) of each offer whose title the filter
keeps, and the total. With `--profil`, the filter is the one of that file: the application
writes the settings being edited to a temporary copy of the profile, runs this once with
the current profile and once with the copy, and shows what changes. Run in its own process:
the engine reads the profile once, when it loads.
"""

import argparse
import json
import os
import sys


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--profil", help="profile file to take the title filter from")
    a = ap.parse_args()
    if a.profil:
        os.environ["PROFIL_JOBHUNTER"] = a.profil  # before the engine loads the profile
    from jobhunter.sources.common import title_ok
    from jobhunter.storage import queue as queue_io

    offres = queue_io.charger(descriptions=False)
    gardees = [queue_io.oid(o) for o in offres if title_ok(str(o.get("poste") or ""))]
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]  # console : TextIOWrapper
    print(json.dumps({"total": len(offres), "gardees": gardees}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
