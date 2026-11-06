"""A release in two commands, instead of fifteen by hand.

  python tools/release.py preparer 3.27.0     # branch v3.27.0, VERSION, pyproject, uv.lock
  (write the « ## 3.27.0 — date » section of CHANGELOG.md, commit, push, open the PR)
  python tools/release.py publier 106         # CI green → main, GitHub release, local main

  python tools/release.py beta 106            # before publier: a test release (3.85)

`beta` publishes the PR's branch as a GitHub pre-release, without merging it: the
installer CI builds and attaches it, the author signs it, and only the copies that ticked
« Recevoir les versions de test » receive it. `publier` then turns that same tag into the
release (refused if the branch moved since: a new version is a new test).

`publier` refuses while a check of the PR is not green, or when CHANGELOG.md has no
section for the version. It never signs: the signature stays the author's act
(tools/signature.py). `--installer <dossier>` then upgrades the package installed for
that data folder's interpreter, from the tag just published: the first `python` on PATH
outside this venv (which has no pip), or `--python <exe>`.
"""

import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

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


def python_hors_venv() -> str:
    """The `python` a data folder runs: the first on PATH outside the venv running this tool.

    3.84.0: `sys.executable` was the engine's venv, which has no pip, and the install
    failed after the release was published.
    """
    venv = Path(sys.prefix).resolve()
    dossiers = []
    for d in os.environ.get("PATH", "").split(os.pathsep):
        try:
            chemin = Path(d).resolve()
        except OSError:
            continue
        if d and chemin != venv and venv not in chemin.parents:
            dossiers.append(d)
    return shutil.which("python", path=os.pathsep.join(dossiers)) or ""


def _pr_prete(pr: int) -> tuple[str, str, str]:
    """(branch, version, release notes) of an open release PR whose CI is green."""
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
    return branche, version, notes


def _release_existante(version: str) -> dict[str, Any] | None:
    """{"prerelease", "commit"} of the release `v<version>`, None when there is none."""
    r = subprocess.run(
        ["gh", "release", "view", f"v{version}", "--json", "isPrerelease"],
        cwd=RACINE,
        text=True,
        capture_output=True,
        encoding="utf-8",
    )
    if r.returncode:
        return None
    commit = _run("git", "rev-list", "-n", "1", f"v{version}", capture=True)
    return {"prerelease": bool(json.loads(r.stdout)["isPrerelease"]), "commit": commit}


def _notes_fichier(notes: str) -> Path:
    """The release notes in a temporary file, for `gh release create --notes-file`.

    Not in .git/: in a worktree .git is a file, and 3.84.1's `publier` stopped there
    after pushing main, before creating the release.
    """
    fd, nom = tempfile.mkstemp(prefix="notes_release_", suffix=".md")
    os.close(fd)
    fichier = Path(nom)
    fichier.write_text(notes + "\n", encoding="utf-8")
    return fichier


def beta(pr: int) -> int:
    """The PR's branch as a GitHub pre-release: built, signed, offered to testers only."""
    branche, version, notes = _pr_prete(pr)
    _run("git", "fetch", "-q", "--tags", "origin")
    if _release_existante(version):
        sys.exit(f"v{version} existe déjà : une nouvelle version de test demande un nouveau numéro")
    fichier = _notes_fichier(notes)
    _run(
        "gh",
        "release",
        "create",
        f"v{version}",
        "--target",
        branche,
        "--prerelease",
        "--title",
        f"JobHunter {version} (test)",
        "--notes-file",
        str(fichier),
    )
    fichier.unlink()
    print(f"v{version} publiée en version de test : {DEPOT}/releases/tag/v{version}")
    print("La signature reste à faire par son auteur (tools/signature.py) ; puis publier.")
    return 0


def publier(pr: int, installer: str = "", python: str = "") -> int:
    branche, version, notes = _pr_prete(pr)
    _run("git", "fetch", "-q", "--tags", "origin")
    test = _release_existante(version)
    if test and not test["prerelease"]:
        sys.exit(f"v{version} est déjà publiée")
    if test and test["commit"] != _run("git", "rev-parse", f"origin/{branche}", capture=True):
        sys.exit(
            f"la branche {branche} a changé depuis la version de test v{version} : "
            "ce qui a été testé n'est plus ce qui serait publié. Nouveau numéro."
        )
    _run("git", "push", "origin", f"origin/{branche}:refs/heads/main")
    if test:
        # The tested tag becomes the release: same commit, installer and signature.
        _run(
            "gh",
            "release",
            "edit",
            f"v{version}",
            "--prerelease=false",
            "--latest",
            "--title",
            f"JobHunter {version}",
        )
    else:
        fichier = _notes_fichier(notes)
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
        exe = python or python_hors_venv()
        if not exe:
            sys.exit("aucun python hors du venv sur le PATH : relancer avec --python <exe>")
        cible = f"jobhunter @ git+{DEPOT}@v{version}"
        subprocess.run(
            [exe, "-m", "pip", "install", "-q", "--upgrade", cible],
            cwd=installer,
            check=True,
        )
        print(f"installée pour {installer} ({exe})")
    if not test:
        print("La signature reste à faire par son auteur (tools/signature.py).")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sous = ap.add_subparsers(dest="action", required=True)
    sous.add_parser("preparer").add_argument("version")
    sous.add_parser("beta").add_argument("pr", type=int)
    p = sous.add_parser("publier")
    p.add_argument("pr", type=int)
    p.add_argument(
        "--installer", default="", help="dossier de données dont mettre à jour le paquet"
    )
    p.add_argument("--python", default="", help="interpréteur de ce dossier (défaut : hors venv)")
    a = ap.parse_args()
    if a.action == "preparer":
        return preparer(a.version)
    if a.action == "beta":
        return beta(a.pr)
    return publier(a.pr, a.installer, a.python)


if __name__ == "__main__":
    sys.exit(main())
