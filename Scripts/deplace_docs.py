#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""deplace_docs.py — Sort les documents generes de OneDrive, sans rien casser.

CE QU'IL DEPLACE, et seulement cela :
    CV/Par_offre        409 Mo   8073 fichiers
    Lettres/Par_offre   351 Mo   8020 fichiers

CE QU'IL LAISSE dans OneDrive, volontairement :
    CV/Modeles          1,1 Mo   les cinq CV sources, ecrits a la main
    Lettres/Relances    420 Ko
    Lettres/Messages     24 Ko
Ces trois-la ne se regenerent pas. Ils sont minuscules et meritent le nuage.

TROIS CHOSES BOUGENT, dans cet ordre, et l'ordre compte :

  1. GIT. Les 16 091 fichiers sont SUIVIS. Les deplacer sans prevenir git
     produirait 16 091 suppressions au prochain `git status`, et un
     `git checkout .` malheureux les recopierait dans OneDrive. On les sort
     donc de l'index (`git rm --cached`, le disque n'est pas touche) et on les
     ajoute a .gitignore. Le depot ne les suivra plus : ce sont des artefacts,
     `regenere_docs.py` les reconstruit.

  2. LES FICHIERS. Meme volume (C:), donc un renommage de dossier : instantane,
     aucune recopie. Si le renommage echoue — dossier ouvert, fichier verrouille
     par Word ou par la synchronisation — on bascule sur une copie fichier par
     fichier et on ne supprime la source qu'une fois tout arrive.

  3. LES LIENS DE LA FILE. 1774 offres portent un `cv` et un `lettre` en
     `file:///C:/Users/l'utilisateur/OneDrive/...`. Ils sont reecrits vers la
     nouvelle racine, sous verrou, via queue_io.

CE QUI N'EST PAS SAUVEGARDE APRES COUP. Hors de OneDrive, ces 760 Mo ne sont
plus repliques dans le nuage. C'est assume : ce sont des sorties de generation,
reconstructibles par `python regenere_docs.py --cv`. Les entrees — modeles,
file, suivi — restent, elles, synchronisees.

Run :
  python deplace_docs.py                      # inspection, rien n'est ecrit
  python deplace_docs.py --executer
  python deplace_docs.py --executer --vers "D:/Recherche_emploi_documents"
  python deplace_docs.py --retour             # revient dans OneDrive
"""
import argparse
import json
import os
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

import chemins
import jutil

# Les deux seuls dossiers concernes, sous la forme (relatif, cle de la file).
LOTS = [(Path("CV") / "Par_offre", "cv"),
        (Path("Lettres") / "Par_offre", "lettre")]

IGNORE = ["", "# ── documents generes (deplaces hors de OneDrive) ──",
          "# 760 Mo de CV et de lettres reconstructibles par regenere_docs.py.",
          "# Suivis jusqu'au 20/09/2026 ; .git pesait alors 960 Mo a lui seul.",
          "CV/Par_offre/", "Lettres/Par_offre/", "Scripts/chemins.json"]


def _taille(d):
    """(nombre de fichiers, octets). 0, 0 si le dossier n'existe pas."""
    if not d.exists():
        return 0, 0
    n = o = 0
    for p in d.rglob("*"):
        if p.is_file():
            n += 1
            o += p.stat().st_size
    return n, o


def _mo(o):
    return f"{o / 1024 / 1024:.0f} Mo"


def git(*args):
    import subprocess
    r = subprocess.run(["git", "-C", str(ROOT)] + list(args),
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def detacher_de_git():
    """Sort les deux dossiers de l'index et les ajoute a .gitignore."""
    suivis = 0
    for rel, _ in LOTS:
        code, out = git("ls-files", str(rel).replace("\\", "/"))
        n = len([l for l in out.splitlines() if l.strip()])
        suivis += n
        if n:
            code, out = git("rm", "-r", "--cached", "--quiet", str(rel).replace("\\", "/"))
            if code:
                print(f"! git rm a echoue sur {rel} : {out.strip()[:200]}")
                return False
            print(f"  git : {n} fichiers sortis de l'index ({rel})")
    gi = ROOT / ".gitignore"
    t = gi.read_text(encoding="utf-8") if gi.exists() else ""
    if "CV/Par_offre/" not in t:
        gi.write_text(t.rstrip("\n") + "\n" + "\n".join(IGNORE) + "\n", encoding="utf-8")
        print("  .gitignore : deux dossiers ajoutes")
    return True


def bouger(src, dst):
    """Renommage si possible, copie sinon. True si tout est arrive."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        print(f"! {dst} existe deja — rien n'est deplace.")
        return False
    try:
        os.rename(src, dst)                 # meme volume : instantane
        print(f"  renomme : {src.name} → {dst}")
        return True
    except OSError as e:
        print(f"  renommage impossible ({type(e).__name__}) — copie fichier par fichier")
    dst.mkdir(parents=True, exist_ok=True)
    rates = []
    for p in src.rglob("*"):
        if not p.is_file():
            continue
        cible = dst / p.relative_to(src)
        cible.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copy2(p, cible)
        except OSError as e:
            rates.append((p.name, type(e).__name__))
    if rates:
        # RIEN N'EST SUPPRIME quand une copie a echoue. Un dossier a moitie
        # copie dont on efface la source, c'est une perte seche.
        print(f"! {len(rates)} fichiers non copies — la source est CONSERVEE :")
        for nom, err in rates[:5]:
            print(f"    {nom[:60]} ({err})")
        return False
    shutil.rmtree(src, ignore_errors=True)
    print(f"  copie puis source effacee : {src.name} → {dst}")
    return True


def reecrire_liens(base_avant, base_apres):
    """Rebase les file:/// de la file. Rend le nombre de liens changes."""
    import queue_io
    a, b = str(base_avant).lower(), None
    n = 0
    with queue_io.transaction(descriptions=False) as file:
        for o in file:
            for cle in ("cv", "lettre"):
                p = jutil.chemin_de(o.get(cle))
                if p is None:
                    continue
                s = str(p)
                if s.lower().startswith(a):
                    o[cle] = jutil.url_de(base_apres / Path(s[len(str(base_avant)):].lstrip("\\/")))
                    n += 1
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vers", default=str(chemins.DEFAUT_AILLEURS))
    ap.add_argument("--executer", action="store_true")
    ap.add_argument("--retour", action="store_true", help="ramene les documents dans OneDrive")
    a = ap.parse_args()

    depart = ROOT if not a.retour else Path(a.vers)
    arrivee = Path(a.vers) if not a.retour else ROOT

    print(f"de   : {depart}")
    print(f"vers : {arrivee}\n")
    total = 0
    for rel, _ in LOTS:
        n, o = _taille(depart / rel)
        total += o
        print(f"  {str(rel):22} {n:6} fichiers  {_mo(o):>8}   {depart / rel}")
    print(f"\n  libere de OneDrive : {_mo(total)}" if not a.retour
          else f"\n  remis dans OneDrive : {_mo(total)}")

    if not a.executer:
        print("\n[INSPECTION] rien n'a ete ecrit. --executer pour deplacer.")
        return 0

    if not a.retour and not detacher_de_git():
        return 3

    for rel, _ in LOTS:
        src = depart / rel
        if not src.exists():
            print(f"  = {rel} absent de {depart} — rien a faire")
            continue
        if not bouger(src, arrivee / rel):
            print("\n! deplacement interrompu. La file n'a PAS ete modifiee.")
            return 4

    # Le reglage de machine. Ecrit APRES le deplacement : tant que les fichiers
    # ne sont pas arrives, chemins.py doit continuer de pointer sur l'ancien.
    if a.retour:
        chemins.CONFIG.unlink(missing_ok=True)
        print("  chemins.json supprime — retour au defaut OneDrive")
    else:
        chemins.CONFIG.write_text(
            json.dumps({"documents": str(arrivee).replace("\\", "/")},
                       ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"  chemins.json ecrit → {arrivee}")

    n = reecrire_liens(depart, arrivee)
    print(f"  file : {n} liens cv/lettre reecrits")
    print("\nfait.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
