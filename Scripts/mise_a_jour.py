#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mise_a_jour.py — Met JobHunter a jour depuis GitHub, sans toucher a tes donnees.

    python Scripts/mise_a_jour.py            # met a jour si une version plus recente existe
    python Scripts/mise_a_jour.py --verifier # dit seulement s'il y a une mise a jour
    python Scripts/mise_a_jour.py --forcer   # reinstalle meme a version egale

Deux chemins :
  - dossier clone avec git -> `git pull --rebase --autostash` ;
  - dossier dezippe        -> telecharge le ZIP de la branche main et remplace
                              les fichiers du programme, un par un.

CE QUI N'EST JAMAIS TOUCHE : ton profil, ton CV (Mon_CV, CV), tes lettres, la
file d'offres, le suivi des candidatures, les cles d'API — tout ce que git
ignore. Ces fichiers ne sont pas dans le ZIP, et une garde les refuse quand meme.

UN FICHIER DU PROGRAMME QUE TU AS MODIFIE est garde tel quel ; la nouvelle
version est posee a cote, en `.nouveau`, et le bilan te le signale. « Modifie »
= different de ce que la derniere mise a jour avait installe (`.maj_manifeste.json`).
Sans ce manifeste (premiere mise a jour), seuls les fichiers que le premier
lancement reecrit (`Scripts/sources_config.json`) sont presumes modifies.

Chaque fichier remplace est d'abord copie dans `_sauvegarde_maj/<date>/` :
la mise a jour se defait en recopiant ce dossier.
"""
import argparse
import hashlib
import io
import json
import shutil
import subprocess
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RACINE = Path(__file__).resolve().parent.parent
DEPOT = "Grisbix/JobHunter"
ZIP_URL = f"https://github.com/{DEPOT}/archive/refs/heads/main.zip"
MANIFESTE = RACINE / ".maj_manifeste.json"
SAUVEGARDES = RACINE / "_sauvegarde_maj"

# Donnees de l'utilisateur : jamais ecrites, meme si un ZIP les contenait.
PROTEGES_PREFIXES = ("profil/profil", "Mon_CV/", "CV/", "Lettres/", "_sauvegarde_maj/", ".git/")
PROTEGES_NOMS = {"Scripts/apply_queue.json", "Scripts/descriptions.json", "Scripts/suivi.json",
                 "Scripts/adzuna.json", "Scripts/jooble.json", "Scripts/apply_runner_done.json",
                 "Scripts/chemins.json"}
# Ecrits par premier_lancement : presumes modifies quand il n'y a pas de manifeste.
REECRITS_AU_PREMIER_LANCEMENT = {"Scripts/sources_config.json"}


def _sha(b):
    return hashlib.sha256(b).hexdigest()


def protege(rel):
    if rel in PROTEGES_NOMS or rel.startswith(PROTEGES_PREFIXES):
        return True
    return rel.startswith("profil/") and not Path(rel).name.startswith("exemple_")


def version_locale():
    p = RACINE / "VERSION"
    return p.read_text(encoding="utf-8").strip() if p.exists() else "0"


def _cle_version(v):
    return tuple(int(x) if x.isdigit() else 0 for x in v.strip().split("."))


VERSION_URL = f"https://raw.githubusercontent.com/{DEPOT}/main/VERSION"
DERNIERE_VERIF = RACINE / ".maj_derniere_verif"


def nouvelle_version(timeout=5, intervalle_h=24):
    """Version disponible si elle est plus recente que l'installee, sinon None.

    Pour l'application, au demarrage : un seul petit fichier (VERSION), au plus
    une fois par jour, et toute erreur (hors ligne, GitHub lent) vaut « rien de
    neuf » — une verification ne doit jamais gener le lancement."""
    # Sans fichier VERSION, ce n'est pas une installation publiee (copie de
    # developpement, depot qui synchronise le moteur) : rien a annoncer.
    if not (RACINE / "VERSION").exists():
        return None
    try:
        if DERNIERE_VERIF.exists() and time.time() - DERNIERE_VERIF.stat().st_mtime < intervalle_h * 3600:
            return None
        DERNIERE_VERIF.write_text(time.strftime("%Y-%m-%d %H:%M"), encoding="utf-8")
        req = urllib.request.Request(VERSION_URL, headers={"User-Agent": "JobHunter-mise-a-jour"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            distante = r.read(64).decode("utf-8").strip()
        return distante if _cle_version(distante) > _cle_version(version_locale()) else None
    except Exception:
        return None


def telecharger():
    print(f"Téléchargement de {ZIP_URL} …")
    req = urllib.request.Request(ZIP_URL, headers={"User-Agent": "JobHunter-mise-a-jour"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def fichiers_du_zip(data):
    """{chemin relatif: contenu} ; le dossier racine du ZIP (JobHunter-main/) est retire."""
    out = {}
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for info in z.infolist():
            if info.is_dir():
                continue
            rel = info.filename.split("/", 1)[1] if "/" in info.filename else ""
            if rel:
                out[rel] = z.read(info)
    return out


def par_git(args):
    print("Dossier git détecté : git pull.")
    if args.verifier:
        subprocess.run(["git", "fetch", "--quiet"], cwd=RACINE)
        r = subprocess.run(["git", "rev-list", "--count", "HEAD..@{u}"], cwd=RACINE,
                           capture_output=True, text=True)
        n = (r.stdout or "0").strip()
        print(f"{n} mise(s) à jour disponible(s)." if n != "0" else "Déjà à jour.")
        return 0
    def tete():
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=RACINE,
                              capture_output=True, text=True).stdout.strip()
    avant = tete()
    r = subprocess.run(["git", "pull", "--rebase", "--autostash"], cwd=RACINE)
    if r.returncode:
        print("\n! git pull a échoué (voir le message ci-dessus). Tes fichiers n'ont pas été "
              "perdus : `git status` montre où en est le dossier.")
        return 1
    changes = subprocess.run(["git", "diff", "--name-only", avant, tete()], cwd=RACINE,
                             capture_output=True, text=True).stdout.split()
    return apres(changes_requirements="requirements.txt" in changes)


def par_zip(args):
    locale = version_locale()
    try:
        nouveaux = fichiers_du_zip(telecharger())
    except Exception as e:
        print(f"! Téléchargement impossible : {type(e).__name__}: {e}")
        return 1
    distante = (nouveaux.get("VERSION") or b"0").decode("utf-8").strip()
    print(f"Version installée : {locale} · version disponible : {distante}")
    if args.verifier:
        print("Mise à jour disponible." if _cle_version(distante) > _cle_version(locale)
              else "Déjà à jour.")
        return 0
    if _cle_version(distante) <= _cle_version(locale) and not args.forcer:
        print("Déjà à jour.")
        return 0

    manifeste = {}
    if MANIFESTE.exists():
        try:
            manifeste = json.loads(MANIFESTE.read_text(encoding="utf-8"))
        except Exception:
            manifeste = {}
    sauvegarde = SAUVEGARDES / time.strftime("%Y-%m-%d_%H%M%S")
    remplaces, ajoutes, gardes, refuses = [], [], [], []
    req_change = False
    nouveau_manifeste = dict(manifeste)

    for rel, contenu in sorted(nouveaux.items()):
        if protege(rel):
            refuses.append(rel)
            continue
        dest = RACINE / rel
        h_new = _sha(contenu)
        if dest.exists():
            actuel = dest.read_bytes()
            h_loc = _sha(actuel)
            if h_loc == h_new:
                nouveau_manifeste[rel] = h_new
                continue
            installe = manifeste.get(rel)
            modifie = (h_loc != installe) if installe else (rel in REECRITS_AU_PREMIER_LANCEMENT)
            if modifie:
                Path(str(dest) + ".nouveau").write_bytes(contenu)
                gardes.append(rel)
                continue            # le manifeste garde l'ancienne empreinte : toujours « modifie »
            (sauvegarde / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(dest, sauvegarde / rel)
            dest.write_bytes(contenu)
            remplaces.append(rel)
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(contenu)
            ajoutes.append(rel)
        nouveau_manifeste[rel] = h_new
        req_change = req_change or rel == "requirements.txt"

    MANIFESTE.write_text(json.dumps(nouveau_manifeste, indent=1, sort_keys=True), encoding="utf-8")
    print(f"\n{len(remplaces)} fichier(s) mis à jour, {len(ajoutes)} ajouté(s).")
    if remplaces:
        print(f"Anciennes versions copiées dans {sauvegarde.relative_to(RACINE)}")
    if gardes:
        print("\nFichiers que TU as modifiés, gardés tels quels (la nouvelle version est à côté, "
              "en .nouveau — compare et fusionne si tu veux) :")
        for rel in gardes:
            print(f"  - {rel}")
    if refuses:
        print(f"\n{len(refuses)} fichier(s) de données ignorés (jamais remplacés).")
    return apres(changes_requirements=req_change)


def apres(changes_requirements):
    if changes_requirements:
        print("\nLes dépendances ont changé : installation…")
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r",
                        str(RACINE / "requirements.txt")])
    print(f"\nJobHunter est à jour (version {version_locale()}). Relance l'application.")
    return 0


def main():
    ap = argparse.ArgumentParser(description="Met JobHunter à jour depuis GitHub.")
    ap.add_argument("--verifier", action="store_true", help="dire seulement s'il y a une mise à jour")
    ap.add_argument("--forcer", action="store_true", help="réinstaller même à version égale")
    args = ap.parse_args()
    if (RACINE / ".git").exists() and shutil.which("git"):
        return par_git(args)
    return par_zip(args)


if __name__ == "__main__":
    sys.exit(main())
