#!/usr/bin/env python3
"""Refuses that any personal data enter the public repository.

The repository is public; the user's working folder contains their profile, offers,
tracking, letters, CVs and API keys. `.gitignore` keeps them out, but a `git add -f`,
a renamed file or a copy in another folder would get through. This check looks at the
tracked files (or those given as arguments, for pre-commit) and fails on any path of
the "user" layer.

    python tools/personal_data.py            # all tracked files
    python tools/personal_data.py a.json b   # these files (pre-commit hook)

Run by pre-commit before each commit and by the tests (hence by the CI).
"""

import re
import subprocess
import sys

# What must never be published: user data and secrets.
INTERDITS = [
    r"^profil/(?!exemple_)[^/]+$",  # profil.json and any copy; only the examples
    r"^Scripts/(?!sources_config\.json$)[^/]+\.(json|jsonl|csv|txt|log)$",  # queue, tracking, keys…
    r"^Scripts/_",  # backups, logs, states (_logs/, _preuves/, _rendement.jsonl…)
    r"^(CV|Lettres)/",  # generated documents
    r"^Mon_CV/(?!LISEZ-MOI\.txt$)",  # the user's CV
    r"(^|/)\.env($|\.)",
    r"(^|/)(adzuna|jooble|francetravail|api_keys|mail_config|comptes|apply_profile)\.json$",
    r"(^|/)\.ats_password$",
    r"\.(docx|pdf|xlsx)$",  # personal documents; the README screenshots are .png files
]
_RX = [re.compile(m) for m in INTERDITS]


def fautifs(chemins: list[str]) -> list[str]:
    """The paths (git style, "/") that belong to the user's data."""
    return [c for c in chemins if any(rx.search(c.replace("\\", "/")) for rx in _RX)]


def main(argv: list[str]) -> int:
    chemins = (
        argv
        or subprocess.run(
            ["git", "ls-files"], capture_output=True, text=True, check=True, encoding="utf-8"
        ).stdout.splitlines()
    )
    mauvais = fautifs(chemins)
    for c in mauvais:
        print(f"donnée personnelle, ne pas publier : {c}")
    if mauvais:
        print("Retire-les du commit (git rm --cached <fichier>) : le dépôt est public.")
    return 1 if mauvais else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
