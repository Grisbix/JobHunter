"""A release in two commands, instead of fifteen by hand.

  python tools/release.py preparer 3.27.0     # branch v3.27.0, VERSION, pyproject, uv.lock
  (write the « ## 3.27.0 — date » section of CHANGELOG.md, commit, push, open the PR)
  python tools/release.py publier 106         # CI green → main, GitHub release, local main

`publier` refuses while a check of the PR is not green, or when CHANGELOG.md has no
section for the version. It never signs: the signature stays the author's act
(tools/signature.py). `--installer <dossier>` then upgrades the package installed for
that data folder's interpreter, from the tag just published.
"""

import argparse
import datetime
import json
import re
import subprocess
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
DEPOT = "https://github.com/Grisbix/JobHunter"


def _run(*cmd: str, capture: bool = False) -> str:
    r = subprocess.run(cmd, cwd=RACINE, text=True, capture_output=capture, encoding="utf-8")
    if r.returncode:
        sys.exit(f"échec : {' '.join(cmd)}\n{(r.stderr or '').strip() if capture else ''}")
    return (r.stdout or "").strip() if capture else ""


def _notes(version: str) -> str:
    """The CHANGELOG section of `version`, without its title ('' if absent)."""
    texte = (RACINE / "CHANGELOG.md").read_text(encoding="utf-8")
    m = re.search(rf"^## {re.escape(version)}\b.*?$(.*?)(?=^## |\Z)", texte, re.M | re.S)
    return m.group(1).strip() if m else ""


def preparer(version: str) -> int:
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        sys.exit(f"version invalide : {version}")
    if _run("git", "status", "--porcelain", "--untracked-files=no", capture=True):
        sys.exit("des fichiers suivis sont modifiés : les commiter ou les mettre de côté d'abord")
    _run("git", "fetch", "-q", "origin")
    _run("git", "checkout", "-q", "-b", f"v{version}", "origin/main")
    (RACINE / "VERSION").write_bytes(f"{version}\n".encode())
    py = RACINE / "pyproject.toml"
    texte = py.read_text(encoding="utf-8")
    nouveau = re.sub(r'(?m)^version = "[^"]+"', f'version = "{version}"', texte, count=1)
    py.write_bytes(nouveau.encode("utf-8"))
    _run("uv", "lock", "-q")
    print(
        f"branche v{version} prête. Reste : la section « ## {version} — "
        f"{datetime.date.today()} » de CHANGELOG.md, le commit, le push et la PR."
    )
    return 0


def publier(pr: int, installer: str = "") -> int:
    info = json.loads(
        _run("gh", "pr", "view", str(pr), "--json", "headRefName,state", capture=True)
    )
    branche = info["headRefName"]
    version = branche.removeprefix("v")
    if info["state"] != "OPEN":
        sys.exit(f"PR {pr} : {info['state']}")
    checks = json.loads(_run("gh", "pr", "checks", str(pr), "--json", "name,state", capture=True))
    rouges = [c["name"] for c in checks if c["state"] not in ("SUCCESS", "SKIPPED", "NEUTRAL")]
    if not checks or rouges:
        sys.exit(f"CI pas verte : {', '.join(rouges) or 'aucun contrôle'}")
    notes = _notes(version)
    if not notes:
        sys.exit(f"CHANGELOG.md n'a pas de section {version}")
    _run("git", "fetch", "-q", "origin")
    _run("git", "push", "origin", f"origin/{branche}:refs/heads/main")
    fichier = RACINE / ".git" / "notes_release.md"
    fichier.write_text(notes + "\n", encoding="utf-8")
    _run(
        "gh",
        "release",
        "create",
        f"v{version}",
        "--target",
        "main",
        "--title",
        f"JobHunter {version}",
        "--notes-file",
        str(fichier),
    )
    fichier.unlink()
    _run("git", "checkout", "-q", "main")
    _run("git", "merge", "-q", "--ff-only", "origin/main")
    subprocess.run(["git", "branch", "-d", branche], cwd=RACINE, capture_output=True)
    print(f"v{version} publiée : {DEPOT}/releases/tag/v{version}")
    if installer:
        cible = f"jobhunter @ git+{DEPOT}@v{version}"
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-q", "--upgrade", cible],
            cwd=installer,
            check=True,
        )
        print(f"installée pour {installer}")
    print("La signature reste à faire par son auteur (tools/signature.py).")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sous = ap.add_subparsers(dest="action", required=True)
    sous.add_parser("preparer").add_argument("version")
    p = sous.add_parser("publier")
    p.add_argument("pr", type=int)
    p.add_argument(
        "--installer", default="", help="dossier de données dont mettre à jour le paquet"
    )
    a = ap.parse_args()
    return preparer(a.version) if a.action == "preparer" else publier(a.pr, a.installer)


if __name__ == "__main__":
    sys.exit(main())
