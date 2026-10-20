#!/usr/bin/env python3
"""setup_francetravail.py — Installs and CHECKS the France Travail API credentials,
without the secret going anywhere else.

The secret is never displayed, never logged, never committed
(Scripts/francetravail.json is in .gitignore). It is entered locally, written to the
file, then immediately tested against the API.

Where to get the credentials:
  1. https://francetravail.io  ->  create an account
  2. create an application, subscribe to "Offres d'emploi v2"
  3. note client_id and client_secret

Run:
  python JobHunter.pyw setup_francetravail            # masked entry + test
  python JobHunter.pyw setup_francetravail --test     # tests the credentials already in place
"""

import argparse
import getpass
import json
import sys

from jobhunter import root as _racine

sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)  # type: ignore[union-attr]  # console : TextIOWrapper

HERE = _racine.scripts()
CFG = _racine.dossier_cles() / "francetravail.json"


def test():
    """Checks that the credentials get a token AND bring back offers."""
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
    print("\nOK. `python JobHunter.pyw collect --all` inclut desormais France Travail.")
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
    # getpass: typing does not appear on screen and does not go into the shell history
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
