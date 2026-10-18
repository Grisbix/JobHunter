#!/usr/bin/env python3
"""setup_francetravail.py — Installe et VERIFIE les identifiants de l'API
France Travail, sans que le secret transite par ailleurs.

Le secret n'est jamais affiche, jamais journalise, jamais commite
(Scripts/francetravail.json est dans .gitignore). Il est saisi en local, ecrit
dans le fichier, puis immediatement teste contre l'API.

Ou obtenir les identifiants :
  1. https://francetravail.io  ->  creer un compte
  2. creer une application, souscrire a « Offres d'emploi v2 »
  3. relever client_id et client_secret

Run :
  python setup_francetravail.py            # saisie masquee + test
  python setup_francetravail.py --test     # teste les identifiants deja en place
"""

import argparse
import getpass
import json
import sys

from jobhunter import racine as _racine

sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

HERE = _racine.scripts()
CFG = HERE / "francetravail.json"


def test():
    """Verifie que les identifiants obtiennent un jeton ET ramenent des offres."""
    from jobhunter import sources as js

    tok = js._ft_token()
    if not tok:
        print(
            "✗ jeton refuse — identifiants invalides, ou l'application n'est pas"
            " abonnee a « Offres d'emploi v2 » sur francetravail.io"
        )
        return 1
    print(f"✓ jeton obtenu ({len(tok)} caracteres)")
    js.KEYWORDS = ["analyste esg"]
    offres = js.fetch_france_travail(par_mot=10)
    print(f"✓ API interrogee — {len(offres)} offre(s) sur le mot-cle test")
    for o in offres[:3]:
        print(f"    {o['titre'][:52]:<52} | {o['entreprise'][:22]}")
    print("\nOK. `python job_sources.py --all` inclut desormais France Travail.")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", action="store_true", help="teste les identifiants deja installes")
    a = ap.parse_args()

    if a.test:
        if not CFG.exists():
            print(f"✗ {CFG.name} absent — relance sans --test pour le creer")
            return 1
        return test()

    if CFG.exists():
        print(f"⚠ {CFG.name} existe deja. Entree vide = conserver l'existant.")

    print("Identifiants API France Travail (francetravail.io > ton application) :")
    cid = input("  client_id     : ").strip()
    # getpass : la frappe n'apparait pas a l'ecran et ne part pas dans l'historique shell
    secret = getpass.getpass("  client_secret : (saisie masquee) ").strip()

    if not cid or not secret:
        if CFG.exists():
            print("Saisie vide — fichier existant conserve.")
            return test()
        print("✗ les deux champs sont requis.")
        return 1

    CFG.write_text(
        json.dumps({"client_id": cid, "client_secret": secret}, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    print(f"✓ ecrit dans {CFG.name} (ignore par git)\n")
    return test()


if __name__ == "__main__":
    sys.exit(main())
