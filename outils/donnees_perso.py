#!/usr/bin/env python3
"""Refuse qu'une donnée personnelle entre dans le dépôt public.

Le dépôt est public ; le dossier de travail de l'utilisateur, lui, contient son profil,
ses offres, son suivi, ses lettres, ses CV et ses clés d'API. `.gitignore` les écarte,
mais un `git add -f`, un fichier renommé ou une copie dans un autre dossier passeraient.
Ce contrôle regarde les fichiers suivis (ou ceux passés en arguments, pour pre-commit)
et échoue sur tout chemin de la couche « utilisateur ».

    python outils/donnees_perso.py            # tous les fichiers suivis
    python outils/donnees_perso.py a.json b   # ces fichiers (hook pre-commit)

Lancé par pre-commit avant chaque commit et par les tests (donc par la CI).
"""

import re
import subprocess
import sys

# Ce qui ne doit jamais être publié : données de l'utilisateur et secrets.
INTERDITS = [
    r"^profil/(?!exemple_)[^/]+$",  # profil.json et toute copie ; seuls les exemples
    r"^Scripts/(?!sources_config\.json$)[^/]+\.(json|jsonl|csv|txt|log)$",  # file, suivi, clés…
    r"^Scripts/_",  # sauvegardes, journaux, états (_logs/, _preuves/, _rendement.jsonl…)
    r"^(CV|Lettres)/",  # documents générés
    r"^Mon_CV/(?!LISEZ-MOI\.txt$)",  # le CV de l'utilisateur
    r"(^|/)\.env($|\.)",
    r"(^|/)(adzuna|jooble|francetravail|api_keys|mail_config|comptes|apply_profile)\.json$",
    r"(^|/)\.ats_password$",
    r"\.(docx|pdf|xlsx)$",  # documents personnels ; les captures du README sont des .png
]
_RX = [re.compile(m) for m in INTERDITS]


def fautifs(chemins: list[str]) -> list[str]:
    """Les chemins (style git, « / ») qui relèvent des données de l'utilisateur."""
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
