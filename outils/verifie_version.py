"""VERSION (read by the updater) and pyproject.toml must carry the same version.

Two version sources is one too many: phase 6 of the plan will keep only one.
Until then, this check runs in CI and before each commit.
"""

import sys
import tomllib
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent


def main():
    fichier = (RACINE / "VERSION").read_text(encoding="utf-8").strip()
    with open(RACINE / "pyproject.toml", "rb") as f:
        projet = tomllib.load(f)["project"]["version"]
    if fichier != projet:
        print(f"VERSION dit {fichier}, pyproject.toml dit {projet} : aligner les deux.")
        return 1
    print(f"version {fichier} : cohérente")
    return 0


if __name__ == "__main__":
    sys.exit(main())
