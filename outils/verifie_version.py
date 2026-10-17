"""VERSION (lu par la mise a jour) et pyproject.toml doivent porter la meme version.

Deux sources de version, c'est une de trop : la phase 6 du plan n'en gardera
qu'une. D'ici la, ce controle tourne en CI et avant chaque commit.
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
