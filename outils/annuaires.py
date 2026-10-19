"""Régénère les annuaires d'entreprises Lever, Ashby et Greenhouse du paquet.

Source : le projet jobsync (github.com/Gsync/jobsync, licence MIT), à un commit épinglé
pour qu'une régénération donne le même fichier. Chaque entrée est validée (nom non vide,
identifiant de tableau d'offres sûr pour une URL) ; une entrée douteuse est écartée.

    uv run python outils/annuaires.py            # régénère src/jobhunter/sources/annuaires/
    uv run python outils/annuaires.py --verifier # échoue si les fichiers diffèrent
"""

import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path

COMMIT = "2bd2284879d2037883cbd21ee3283cf27138a671"
OUTILS = ("lever", "ashby", "greenhouse")
SOURCE = "https://raw.githubusercontent.com/Gsync/jobsync/{commit}/src/lib/scraper/{outil}/companies.json"
DEST = Path(__file__).resolve().parent.parent / "src" / "jobhunter" / "sources" / "annuaires"
_RX_JETON = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")


def nettoyer(brut: object) -> list[list[str]]:
    """Garde les entrées valides, sans doublon d'identifiant, triées par nom.

    Args:
        brut: le JSON de jobsync, une liste de {"name", "token"}.

    Returns:
        [[nom, identifiant], ...]
    """
    if not isinstance(brut, list):
        raise ValueError("annuaire : une liste était attendue")
    vus: set[str] = set()
    sortie = []
    for e in brut:
        if not isinstance(e, dict):
            continue
        nom = " ".join(str(e.get("name") or "").split())
        jeton = str(e.get("token") or "").strip()
        if not nom or len(nom) > 120 or not _RX_JETON.match(jeton) or jeton.lower() in vus:
            continue
        vus.add(jeton.lower())
        sortie.append([nom, jeton])
    return sorted(sortie, key=lambda x: (x[0].casefold(), x[1]))


def texte(entrees: list[list[str]]) -> str:
    """Une entrée par ligne : lisible dans un diff, compact."""
    lignes = ",\n".join(json.dumps(e, ensure_ascii=False) for e in entrees)
    return "[\n" + lignes + "\n]\n"


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--verifier", action="store_true")
    a = ap.parse_args()
    ecarts = 0
    for outil in OUTILS:
        url = SOURCE.format(commit=COMMIT, outil=outil)
        with urllib.request.urlopen(url, timeout=30) as r:  # nosec B310  (https fixe)
            entrees = nettoyer(json.loads(r.read().decode("utf-8")))
        cible = DEST / f"{outil}.json"
        neuf = texte(entrees)
        if a.verifier:
            if not cible.exists() or cible.read_text(encoding="utf-8") != neuf:
                print(f"✗ {cible.name} diffère de jobsync@{COMMIT[:7]}")
                ecarts += 1
            continue
        cible.parent.mkdir(parents=True, exist_ok=True)
        cible.write_bytes(neuf.encode("utf-8"))
        print(f"✓ {outil:<11} {len(entrees):>5} entreprises → {cible.name}")
    return 1 if ecarts else 0


if __name__ == "__main__":
    sys.exit(main())
