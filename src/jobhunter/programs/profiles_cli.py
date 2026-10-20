"""`jobhunter profiles`: the profiles from a terminal (the app has the same in Maintenance).

    jobhunter profiles                       # list them, the active one marked
    jobhunter profiles use <name>            # active from the next start
    jobhunter profiles new <cv> --name "…"   # a new profile: the guided questions here
    jobhunter profiles rename <name> "new name"
    jobhunter profiles archive <name>        # moved to profiles/_archives/, never deleted

<name> is the displayed name or the short identifier shown by the list. One workspace
per profile: docs/adr/0013-one-workspace-per-profile.md.
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

from jobhunter import frozen as _gele
from jobhunter import profiles as _profils

sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]  # console : TextIOWrapper


def _profil(nom: str) -> _profils.Profil:
    p = _profils.trouver(nom)
    if p is None:
        noms = ", ".join(f"{x.nom} ({x.slug or 'principal'})" for x in _profils.liste())
        raise SystemExit(f"! Profil inconnu : {nom!r}. Profils : {noms}")
    return p


def lister() -> int:
    actif = _profils.actif()
    for p in _profils.liste():
        marque = "●" if p.slug == actif else " "
        print(f"{marque} {p.nom:<30} {p.slug or '(principal)':<20} {p.racine}")
    return 0


def utiliser(nom: str) -> int:
    p = _profil(nom)
    _profils.activer(p.slug)
    print(f"Profil actif au prochain démarrage : {p.nom}. Relance JobHunter pour l'ouvrir.")
    return 0


def nouveau(cv: str, nom: str) -> int:
    chemin = Path(cv).expanduser().resolve()
    if chemin.suffix.lower() not in (".docx", ".pdf") or not chemin.is_file():
        print(f"! CV introuvable ou pas en .docx/.pdf : {chemin}")
        return 1
    try:
        racine = _profils.creer(nom)
    except FileExistsError:
        print(f"! Un profil de ce nom existe déjà : {nom}")
        return 1
    print(f"Nouveau profil « {nom} » ({racine.name}) : quelques questions…\n")
    env = {
        **os.environ,
        "JOBHUNTER_RACINE": str(racine),
        _profils.ENV_PRINCIPALE: str(_profils.principale()),
    }
    subprocess.run(  # nosec B603 : our own program, arguments built here
        [_gele.interpreteur(), "-m", "jobhunter.programs.first_launch", str(chemin)],
        cwd=str(racine),
        env=env,
    )
    if not (racine / "profile" / "profile.json").exists():
        shutil.rmtree(racine, ignore_errors=True)  # an empty workspace, created just above
        print("\n! Questions non terminées : le profil n'a pas été créé.")
        return 1
    _profils.nommer(racine)
    print(f"\nProfil « {nom} » créé. `jobhunter profiles use {racine.name}` pour l'ouvrir.")
    return 0


def renommer(nom: str, nouveau_nom: str) -> int:
    p = _profil(nom)
    _profils.renommer(p.slug, nouveau_nom)
    print(f"« {p.nom} » s'appelle maintenant « {' '.join(nouveau_nom.split())} ».")
    return 0


def archiver(nom: str) -> int:
    p = _profil(nom)
    if not p.slug:
        print("! Le profil principal ne s'archive pas (c'est le dossier de l'installation).")
        return 1
    try:
        dest = _profils.archiver(p.slug)
    except RuntimeError as e:
        print(f"! {e} : rien n'a bougé, réessaie après la collecte.")
        return 3
    print(f"« {p.nom} » archivé dans {dest} (rien n'est supprimé).")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(prog="jobhunter profiles", description=__doc__.split("\n")[0])
    sous = ap.add_subparsers(dest="action")
    sous.add_parser("list", help="les profils, l'actif marqué ●")
    s = sous.add_parser("use", help="rendre un profil actif (au prochain démarrage)")
    s.add_argument("nom")
    s = sous.add_parser("new", help="nouveau profil depuis un CV (questions guidées)")
    s.add_argument("cv")
    s.add_argument("--name", required=True, help="le nom du profil")
    s = sous.add_parser("rename", help="changer le nom affiché d'un profil")
    s.add_argument("nom")
    s.add_argument("nouveau_nom")
    s = sous.add_parser("archive", help="ranger un profil dans profiles/_archives/")
    s.add_argument("nom")
    a = ap.parse_args()
    if a.action == "use":
        return utiliser(a.nom)
    if a.action == "new":
        return nouveau(a.cv, a.name)
    if a.action == "rename":
        return renommer(a.nom, a.nouveau_nom)
    if a.action == "archive":
        return archiver(a.nom)
    return lister()


if __name__ == "__main__":
    sys.exit(main())
