"""Regenerates the package's company directories.

Source: the jobsync project (github.com/Gsync/jobsync, MIT licence), at a pinned commit
so that a regeneration gives the same file. Each entry is validated (non-empty name,
job board identifier safe for a URL); a doubtful entry is dropped.

Second source: the companies career-ops tracks (github.com/career-ops-hq/career-ops, MIT
licence, `templates/portals.example.yml`), also at a pinned commit, kept when their
careers or API link gives a feed JobHunter reads (inventory.flux_depuis_url):
`career-ops.json`, [name, tool, identifier].

    uv run python tools/directories.py            # regenerates src/jobhunter/sources/directories/
    uv run python tools/directories.py --verifier # fails if the files differ
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
COMMIT_CO = "b5e4c26f21efee31559296495d794c9a9564a714"
SOURCE_CO = "https://raw.githubusercontent.com/career-ops-hq/career-ops/{commit}/templates/portals.example.yml"
DEST = Path(__file__).resolve().parent.parent / "src" / "jobhunter" / "sources" / "directories"
_RX_JETON = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")


def nettoyer(brut: object) -> list[list[str]]:
    """Keeps the valid entries, without duplicate identifiers, sorted by name.

    Args:
        brut: the jobsync JSON, a list of {"name", "token"}.

    Returns:
        [[name, identifier], ...]
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


def depuis_career_ops(portails: object) -> list[list[str]]:
    """The tracked companies whose link gives a feed, [[name, tool, identifier], ...].

    Args:
        portails: career-ops' portals.yml, read as YAML.
    """
    sys.path.insert(0, str(DEST.parents[2]))
    from jobhunter import inventory

    if not isinstance(portails, dict):
        raise ValueError("career-ops : un dictionnaire était attendu")
    vus: set[tuple[str, str]] = set()
    sortie = []
    for e in portails.get("tracked_companies") or []:
        if not isinstance(e, dict):
            continue
        nom = " ".join(str(e.get("name") or "").split())
        trouve = None
        for cle in ("api", "careers_url"):
            trouve = trouve or inventory.flux_depuis_url(str(e.get(cle) or ""))
        if not nom or len(nom) > 120 or not trouve or trouve[0] == "workday":
            continue
        outil, jeton = trouve[0], str(trouve[1])
        if not _RX_JETON.match(jeton) or (outil, jeton.lower()) in vus:
            continue
        vus.add((outil, jeton.lower()))
        sortie.append([nom, outil, jeton])
    return sorted(sortie, key=lambda x: (x[0].casefold(), x[1], x[2]))


def texte(entrees: list[list[str]]) -> str:
    """One entry per line: readable in a diff, compact."""
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
    import yaml

    with urllib.request.urlopen(SOURCE_CO.format(commit=COMMIT_CO), timeout=30) as r:  # nosec B310
        entrees = depuis_career_ops(yaml.safe_load(r.read().decode("utf-8")))
    cible, neuf = DEST / "career-ops.json", texte(entrees)
    if a.verifier:
        if not cible.exists() or cible.read_text(encoding="utf-8") != neuf:
            print(f"✗ {cible.name} diffère de career-ops@{COMMIT_CO[:7]}")
            ecarts += 1
    else:
        cible.write_bytes(neuf.encode("utf-8"))
        print(f"✓ career-ops  {len(entrees):>5} entreprises → {cible.name}")
    return 1 if ecarts else 0


if __name__ == "__main__":
    sys.exit(main())
