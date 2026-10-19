#!/usr/bin/env python3
"""mise_a_jour.py — Met JobHunter a jour depuis GitHub, sans toucher a tes donnees.

    python JobHunter.pyw maj            # met a jour si une version plus recente existe
    python JobHunter.pyw maj --verifier # dit s'il y a une mise a jour, et ce qu'elle apporte
    python JobHunter.pyw maj --forcer   # reinstalle meme a version egale
    python JobHunter.pyw maj --annuler  # revient a la version d'avant la derniere mise a jour

Deux chemins :
  - dossier clone avec git -> `git pull --rebase --autostash` ;
  - dossier dezippe        -> telecharge le ZIP de la branche main et remplace
                              les fichiers du programme, un par un.

Dans les deux cas, la mise a jour :
  1. affiche les nouveautes (CHANGELOG.md) entre ta version et la nouvelle ;
  2. installe, puis CONTROLE que le programme se charge (compilation de tous les
     scripts, import des modules centraux sur le profil d'exemple) ;
  3. si le controle echoue, revient d'elle-meme a la version d'avant ;
  4. signale les nouveaux reglages du profil que le tien n'a pas encore.

CE QUI N'EST JAMAIS TOUCHE : ton profil, ton CV (Mon_CV, CV), tes lettres, la
file d'offres, le suivi des candidatures, les cles d'API — tout ce que git
ignore. Ces fichiers ne sont pas dans le ZIP, et une garde les refuse quand meme.

UN FICHIER DU PROGRAMME QUE TU AS MODIFIE est garde tel quel ; la nouvelle
version est posee a cote, en `.nouveau`, et le bilan te le signale. « Modifie »
= different de ce que la version installee contenait : l'empreinte vient du
manifeste (`.maj_manifeste.json`, ecrit par l'installeur puis par chaque mise a
jour) ou, a defaut, du ZIP officiel de ta version (etiquette `v<version>`).

UN FICHIER RETIRE du programme est enleve s'il n'a pas ete modifie (copie dans
la sauvegarde), garde sinon. Un fichier que tu as cree n'est jamais touche :
seuls les fichiers d'une version officielle peuvent etre retires.

Chaque fichier remplace ou retire est d'abord copie dans
`_sauvegarde_maj/<date>/`, avec un journal : `--annuler` s'en sert.
"""

import argparse
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

from jobhunter import gele as _gele
from jobhunter import racine as _racine
from jobhunter.reseau import exiger_http

# line_buffering : nos lignes s'intercalent dans le bon ordre avec la sortie de git et
# pip, et s'affichent au fil de l'eau dans le journal de l'application.
sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)  # type: ignore[union-attr]  # console : TextIOWrapper

RACINE = _racine.racine()
DEPOT = "Grisbix/JobHunter"
ZIP_URL = f"https://github.com/{DEPOT}/archive/refs/heads/main.zip"
PAGE_VERSIONS = f"https://github.com/{DEPOT}/releases/latest"
TAG_URL = f"https://github.com/{DEPOT}/archive/refs/tags/v{{}}.zip"
VERSION_URL = f"https://raw.githubusercontent.com/{DEPOT}/main/VERSION"
MANIFESTE = RACINE / ".maj_manifeste.json"
SAUVEGARDES = RACINE / "_sauvegarde_maj"
DERNIERE_VERIF = RACINE / ".maj_derniere_verif"
GIT_AVANT = RACINE / ".maj_git_avant"
JOURNAL = "_journal.json"
EXEMPLE = "profil/exemple_finance_esg.json"

# Donnees de l'utilisateur : jamais ecrites, meme si un ZIP les contenait.
PROTEGES_PREFIXES = ("profil/profil", "Mon_CV/", "CV/", "Lettres/", "_sauvegarde_maj/", ".git/")
PROTEGES_NOMS = {
    "Scripts/apply_queue.json",
    "Scripts/descriptions.json",
    "Scripts/suivi.json",
    "Scripts/adzuna.json",
    "Scripts/jooble.json",
    "Scripts/apply_runner_done.json",
    "Scripts/chemins.json",
}
# Ecrits par premier_lancement : presumes modifies quand aucune reference n'existe.
REECRITS_AU_PREMIER_LANCEMENT = {"Scripts/sources_config.json"}
# Jamais « modifies par l'utilisateur » : un VERSION garde tel quel figerait la version
# installee et la mise a jour se representerait a chaque lancement.
TOUJOURS_REMPLACES = {"VERSION", "CHANGELOG.md"}
# Modules charges par le controle d'apres mise a jour : le coeur du tri et des documents.
# Le controle est celui de la version INSTALLEE (controler_nouveau) : cette liste decrit
# donc toujours l'arbre qui la contient.
MODULES_CENTRAUX = (
    "jobhunter.profil",
    "jobhunter.programmes.jutil",
    "jobhunter.stockage.file",
    "jobhunter.stockage.suivi",
    "jobhunter.scoring.fit",
    "jobhunter.scoring.tri",
    "jobhunter.documents",
    "jobhunter.sources",
    "jobhunter.navigation",
    "jobhunter.programmes.mise_a_jour",
    # l'application elle-meme (sans ouvrir de fenetre) : une mise a jour qui la casse
    # serait annulee au lieu de laisser un double-clic sans effet.
    "jobhunter.app",
)


def _sha(b):
    return hashlib.sha256(b).hexdigest()


def protege(rel):
    if rel in PROTEGES_NOMS or rel.startswith(PROTEGES_PREFIXES):
        return True
    return rel.startswith("profil/") and not Path(rel).name.startswith("exemple_")


def version_locale():
    # Application installée : la version livrée avec le programme, pas un fichier des
    # données de l'utilisateur.
    base = Path(getattr(sys, "_MEIPASS", RACINE)) if _gele.est_gele() else RACINE
    p = base / "VERSION"
    return p.read_text(encoding="utf-8").strip() if p.exists() else "0"


def _cle_version(v):
    return tuple(int(x) if x.isdigit() else 0 for x in v.strip().split("."))


def _get(url, timeout):
    req = urllib.request.Request(exiger_http(url), headers={"User-Agent": "JobHunter-mise-a-jour"})
    with urllib.request.urlopen(req, timeout=timeout) as r:  # nosec B310 : schéma vérifié par exiger_http
        return r.read()


def nouvelle_version(timeout=5, intervalle_h=24):
    """Version disponible si elle est plus recente que l'installee, sinon None.

    Pour l'application, au demarrage : un seul petit fichier (VERSION), au plus
    une fois par jour, et toute erreur (hors ligne, GitHub lent) vaut « rien de
    neuf » — une verification ne doit jamais gener le lancement."""
    # Sans fichier VERSION, ce n'est pas une installation publiee (copie de
    # developpement, depot qui synchronise le moteur) : rien a annoncer.
    if not _gele.est_gele() and not (RACINE / "VERSION").exists():
        return None
    try:
        if (
            DERNIERE_VERIF.exists()
            and time.time() - DERNIERE_VERIF.stat().st_mtime < intervalle_h * 3600
        ):
            return None
        DERNIERE_VERIF.write_text(time.strftime("%Y-%m-%d %H:%M"), encoding="utf-8")
        distante = _get(VERSION_URL, timeout)[:64].decode("utf-8").strip()
        return distante if _cle_version(distante) > _cle_version(version_locale()) else None
    except Exception:
        return None


# ── Nouveautes ──────────────────────────────────────────────────────────────


def nouveautes(changelog, depuis, jusqua=None):
    """Sections « ## x.y.z » du CHANGELOG plus recentes que `depuis` (et au plus
    `jusqua`), dans l'ordre du fichier (la plus recente d'abord)."""
    out, garde = [], False
    for ligne in (changelog or "").splitlines():
        m = re.match(r"##\s+v?(\d+(?:\.\d+)*)", ligne)
        if m:
            v = _cle_version(m.group(1))
            garde = v > _cle_version(depuis) and (jusqua is None or v <= _cle_version(jusqua))
        elif ligne.startswith("# "):
            garde = False
        if garde:
            out.append(ligne)
    return "\n".join(out).strip()


def afficher_nouveautes(changelog, depuis, jusqua=None):
    texte = nouveautes(changelog, depuis, jusqua)
    if texte:
        print("\n── Nouveautés ──────────────────────────────────────────")
        print(texte)
        print("────────────────────────────────────────────────────────")


# ── Profil : nouveaux reglages ──────────────────────────────────────────────


def _cles(d, prefixe=""):
    """Cles d'un profil, sur deux niveaux (« scoring.plafond_second »)."""
    out = set()
    for k, v in (d or {}).items():
        if k.startswith("_"):
            continue
        out.add(prefixe + k)
        if isinstance(v, dict) and not prefixe:
            out |= _cles(v, k + ".")
    return out


def reglages_manquants(exemple, profil):
    """Reglages presents dans le profil d'exemple et absents du tien. Une cle dont
    le parent manque n'est citee qu'une fois (le parent)."""
    manque = sorted(_cles(exemple) - _cles(profil))
    return [k for k in manque if k.split(".")[0] == k or k.split(".")[0] not in manque]


def signaler_reglages():
    p_ex, p_moi = RACINE / EXEMPLE, RACINE / "profil" / "profil.json"
    if not (p_ex.exists() and p_moi.exists()):
        return
    try:
        manque = reglages_manquants(
            json.loads(p_ex.read_text(encoding="utf-8")),
            json.loads(p_moi.read_text(encoding="utf-8")),
        )
    except Exception:
        return
    if manque:
        print(
            "\nNouveaux réglages que ton profil n'a pas encore (la valeur par défaut "
            "s'applique en attendant) :"
        )
        for k in manque:
            print(f"  - {k}")
        print(
            f"Pour les régler : demande à Claude « /configurer-profil », ou copie-les "
            f"depuis {EXEMPLE} dans profil/profil.json."
        )


# ── Controle d'apres mise a jour ────────────────────────────────────────────


def controler():
    """True si le programme installe se charge. Compile chaque script, puis
    importe les modules centraux dans un processus neuf, sur le profil d'exemple
    (le controle ne depend pas de ton profil et ne le lit pas)."""
    erreurs = []
    fichiers = [
        *(RACINE / "Scripts").glob("*.py"),
        *(RACINE / "src").rglob("*.py"),
        RACINE / "JobHunter.pyw",
    ]
    for f in sorted(fichiers):
        if not f.exists():
            continue
        try:
            compile(f.read_bytes(), str(f), "exec")
        except SyntaxError as e:
            erreurs.append(f"{f.relative_to(RACINE)} : {e.msg} (ligne {e.lineno})")
    if not erreurs:
        env = {
            **os.environ,
            "PYTHONPATH": os.pathsep.join(
                x for x in (str(RACINE / "src"), os.environ.get("PYTHONPATH", "")) if x
            ),
            "PROFIL_JOBHUNTER": str(RACINE / EXEMPLE),
            "PYTHONIOENCODING": "utf-8",
            "PYTHONDONTWRITEBYTECODE": "1",
        }
        code = "import importlib\nfor m in %r: importlib.import_module(m)" % (MODULES_CENTRAUX,)
        r = subprocess.run(
            [sys.executable, "-c", code],
            cwd=RACINE / "Scripts",
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )
        if r.returncode:
            sortie = (r.stderr or r.stdout or "").strip().splitlines()
            erreurs.append(sortie[-1] if sortie else f"import : code {r.returncode}")
    if erreurs:
        print("\n! Contrôle échoué :")
        for err in erreurs[:10]:
            print(f"  - {err}")
        return False
    print("\nContrôle : tous les scripts se chargent.")
    return True


def signaler_tache_ancienne():
    """La 2.0 a range les programmes dans le paquet : une collecte planifiee AVANT vise
    Scripts/pipeline_quotidien.py, qui n'existe plus, et echouerait chaque matin sans
    bruit. On le dit (lecture seule : la tache n'est pas modifiee)."""
    if sys.platform == "win32":
        r = subprocess.run(
            ["schtasks", "/Query", "/TN", "JobHunter - collecte quotidienne", "/XML"],
            capture_output=True,
            text=True,
            errors="replace",
        )
        lanceur = "planifier.bat"
    else:
        r = subprocess.run(["crontab", "-l"], capture_output=True, text=True, errors="replace")
        lanceur = "./planifier.sh"
    if r.returncode == 0 and "pipeline_quotidien.py" in (r.stdout or ""):
        print(
            f"\n! La collecte planifiee lance encore l'ancien Scripts/pipeline_quotidien.py, "
            f"qui n'existe plus. Relance {lanceur} pour la remettre a jour."
        )
        return True
    return False


def controler_nouveau():
    """Le controle de la version qu'on vient d'installer, par SON propre code.

    Ce processus est l'ancienne version : sa liste de modules et sa facon de les
    charger decrivent l'ancien arbre. Une version qui deplace des fichiers (2.0 : les
    facades de Scripts/ retirees) serait annulee a tort. On lance donc le controle du
    nouvel arbre, par une entree stable : `python -m jobhunter maj --controler`."""
    if not (RACINE / "src" / "jobhunter" / "cli.py").exists():
        return controler()  # arbre d'avant la 1.12 : pas d'entree unique
    env = {
        **os.environ,
        "PYTHONPATH": os.pathsep.join(
            x for x in (str(RACINE / "src"), os.environ.get("PYTHONPATH", "")) if x
        ),
        "PYTHONIOENCODING": "utf-8",
    }
    r = subprocess.run(
        [sys.executable, "-m", "jobhunter", "maj", "--controler"],
        cwd=RACINE,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
    )
    print((r.stdout or "").rstrip())
    if r.returncode and r.stderr:
        print(r.stderr.strip().splitlines()[-1])
    return r.returncode == 0


def apres(changes_requirements):
    if changes_requirements:
        print("\nLes dépendances ont changé : installation…")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-q", "-r", str(RACINE / "requirements.txt")]
        )
    signaler_reglages()
    print(f"\nJobHunter est à jour (version {version_locale()}). Relance l'application.")
    return 0


# ── Chemin ZIP ──────────────────────────────────────────────────────────────


def telecharger(url=ZIP_URL, timeout=120):
    print(f"Téléchargement de {url} …")
    return _get(url, timeout)


def chemin_sur(rel):
    """Un chemin de ZIP qui reste dans le dossier du programme.

    Refuse les chemins absolus, les lecteurs (« C: »), les remontées (« .. ») et les
    barres inverses : un ZIP piégé ne doit jamais écrire hors de RACINE.
    """
    if not rel or "\\" in rel or rel.startswith("/") or ":" in rel:
        return False
    return ".." not in rel.split("/")


def fichiers_du_zip(data):
    """{chemin relatif: contenu} ; le dossier racine du ZIP (JobHunter-main/) est retire."""
    out = {}
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for info in z.infolist():
            if info.is_dir():
                continue
            rel = info.filename.split("/", 1)[1] if "/" in info.filename else ""
            if rel and chemin_sur(rel):
                out[rel] = z.read(info)
    return out


def initialiser():
    """Empreinte de l'installation telle que dezippee, AVANT que l'utilisateur ne
    modifie quoi que ce soit (appele par installer.bat / installer.sh).

    Sans elle, la reference est le ZIP de l'etiquette v<version> : exact pour qui a
    pris une release, faux pour qui a pris le ZIP de main entre deux releases (ses
    fichiers different de l'etiquette et passeraient pour modifies). Ne fait rien
    s'il y a deja un manifeste, un depot git ou pas de VERSION."""
    if MANIFESTE.exists() or (RACINE / ".git").exists() or not (RACINE / "VERSION").exists():
        return False
    m = {}
    for p in RACINE.rglob("*"):
        rel = p.relative_to(RACINE).as_posix()
        if (
            not p.is_file()
            or protege(rel)
            or "__pycache__/" in rel
            or rel.endswith(".nouveau")
            or rel.startswith((".maj_", "Scripts/_logs/", "Scripts/_sauvegardes/"))
        ):
            continue
        m[rel] = _sha(p.read_bytes())
    MANIFESTE.write_text(json.dumps(m, indent=1, sort_keys=True), encoding="utf-8")
    return True


def reference_installee(version):
    """Empreintes des fichiers de la version installee : le manifeste s'il existe,
    sinon le ZIP officiel de cette version (etiquette GitHub). {} si introuvable :
    on retombe alors sur l'ancienne regle (rien n'est presume modifie, rien n'est
    retire)."""
    if MANIFESTE.exists():
        try:
            return json.loads(MANIFESTE.read_text(encoding="utf-8")), "manifeste"
        except Exception:
            pass
    try:
        data = _get(TAG_URL.format(version), 60)
        return {rel: _sha(b) for rel, b in fichiers_du_zip(data).items()}, f"v{version}"
    except Exception:
        return {}, None


def plan_zip(nouveaux, locaux, reference):
    """Decide fichier par fichier, sans rien ecrire.

    nouveaux  : {rel: contenu} de la nouvelle version
    locaux    : {rel: empreinte} des fichiers presents sur le disque
    reference : {rel: empreinte} de la version installee ({} si inconnue)
    Rend {"remplacer", "ajouter", "garder", "retirer", "garder_retire", "refuser"}."""
    plan = {
        k: []
        for k in (
            "remplacer",
            "ajouter",
            "garder",
            "retirer",
            "garder_retire",
            "refuser",
            "identiques",
        )
    }
    for rel, contenu in sorted(nouveaux.items()):
        if protege(rel):
            plan["refuser"].append(rel)
            continue
        h_loc = locaux.get(rel)
        if h_loc is None:
            plan["ajouter"].append(rel)
        elif h_loc == _sha(contenu):
            plan["identiques"].append(rel)
        elif reference.get(rel) == _sha(contenu):
            pass  # modifie chez l'utilisateur, inchange en amont : rien a proposer
        else:
            ref = reference.get(rel)
            modifie = (h_loc != ref) if ref else (rel in REECRITS_AU_PREMIER_LANCEMENT)
            modifie = modifie and rel not in TOUJOURS_REMPLACES
            plan["garder" if modifie else "remplacer"].append(rel)
    for rel, ref in sorted(reference.items()):
        if rel in nouveaux or protege(rel) or rel not in locaux:
            continue
        plan["retirer" if locaux[rel] == ref else "garder_retire"].append(rel)
    return plan


def _restaurer(sauvegarde, journal):
    """Defait une mise a jour ZIP d'apres son journal."""
    for rel in journal.get("remplaces", []) + journal.get("retires", []):
        src = sauvegarde / rel
        if src.exists():
            (RACINE / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, RACINE / rel)
    installes = journal.get("manifeste_apres", {})
    for rel in journal.get("ajoutes", []):
        p = RACINE / rel
        # un fichier ajoute puis modifie par l'utilisateur reste en place
        if p.exists() and _sha(p.read_bytes()) == installes.get(rel):
            p.unlink()
    avant = journal.get("manifeste_avant")
    if avant:
        MANIFESTE.write_text(json.dumps(avant, indent=1, sort_keys=True), encoding="utf-8")
    elif MANIFESTE.exists():
        MANIFESTE.unlink()
    journal["annule"] = time.strftime("%Y-%m-%d %H:%M")
    (sauvegarde / JOURNAL).write_text(json.dumps(journal, indent=1), encoding="utf-8")


def par_zip(args):
    locale = version_locale()
    try:
        nouveaux = fichiers_du_zip(telecharger())
    except Exception as e:
        print(f"! Téléchargement impossible : {type(e).__name__}: {e}")
        return 1
    distante = (nouveaux.get("VERSION") or b"0").decode("utf-8").strip()
    changelog = (nouveaux.get("CHANGELOG.md") or b"").decode("utf-8", "replace")
    print(f"Version installée : {locale} · version disponible : {distante}")
    plus_recente = _cle_version(distante) > _cle_version(locale)
    if args.verifier:
        print("Mise à jour disponible." if plus_recente else "Déjà à jour.")
        if plus_recente:
            afficher_nouveautes(changelog, locale, distante)
        return 0
    if not plus_recente and not args.forcer:
        print("Déjà à jour.")
        return 0

    reference, source = reference_installee(locale)
    if source and source != "manifeste":
        print(f"Référence de ta version : ZIP officiel {source}.")
    locaux = {}
    for rel in set(nouveaux) | set(reference):
        p = RACINE / rel
        if p.is_file():
            locaux[rel] = _sha(p.read_bytes())
    plan = plan_zip(nouveaux, locaux, reference)

    # Le manifeste d'apres : ce que la nouvelle version a installe. Un fichier garde
    # (modifie) conserve l'empreinte de reference : il reste « modifie » ensuite.
    manifeste = dict(reference)
    for rel in plan["retirer"] + plan["garder_retire"]:
        manifeste.pop(rel, None)
    for rel in plan["remplacer"] + plan["ajouter"] + plan["identiques"]:
        manifeste[rel] = _sha(nouveaux[rel])

    # Journal ecrit AVANT toute ecriture : une panne au milieu (disque plein,
    # fichier verrouille) se defait comme un controle rate.
    sauvegarde = SAUVEGARDES / time.strftime("%Y-%m-%d_%H%M%S")
    sauvegarde.mkdir(parents=True, exist_ok=True)
    journal = {
        "avant": locale,
        "apres": distante,
        "date": time.strftime("%Y-%m-%d %H:%M"),
        "remplaces": plan["remplacer"],
        "ajoutes": plan["ajouter"],
        "retires": plan["retirer"],
        "manifeste_avant": reference if source == "manifeste" else {},
        "manifeste_apres": manifeste,
    }
    (sauvegarde / JOURNAL).write_text(json.dumps(journal, indent=1), encoding="utf-8")
    try:
        for rel in plan["remplacer"] + plan["retirer"]:
            (sauvegarde / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(RACINE / rel, sauvegarde / rel)
        for rel in plan["remplacer"]:
            (RACINE / rel).write_bytes(nouveaux[rel])
        for rel in plan["ajouter"]:
            (RACINE / rel).parent.mkdir(parents=True, exist_ok=True)
            (RACINE / rel).write_bytes(nouveaux[rel])
        for rel in plan["garder"]:
            Path(str(RACINE / rel) + ".nouveau").write_bytes(nouveaux[rel])
        for rel in plan["retirer"]:
            (RACINE / rel).unlink()
    except OSError as e:
        print(f"\n! Écriture impossible ({type(e).__name__}: {e}). Retour à la version d'avant…")
        _restaurer(sauvegarde, journal)
        return 1
    MANIFESTE.write_text(json.dumps(manifeste, indent=1, sort_keys=True), encoding="utf-8")

    print(
        f"\n{len(plan['remplacer'])} fichier(s) mis à jour, {len(plan['ajouter'])} ajouté(s), "
        f"{len(plan['retirer'])} retiré(s)."
    )
    print(
        f"Anciennes versions copiées dans {sauvegarde.relative_to(RACINE)} "
        f"(--annuler pour revenir en arrière)."
    )
    if plan["garder"]:
        print(
            "\nFichiers que TU as modifiés, gardés tels quels (la nouvelle version est à côté, "
            "en .nouveau — compare et fusionne si tu veux) :"
        )
        for rel in plan["garder"]:
            print(f"  - {rel}")
    if plan["garder_retire"]:
        print("\nFichiers retirés du programme mais modifiés chez toi, laissés en place :")
        for rel in plan["garder_retire"]:
            print(f"  - {rel}")
    if plan["refuser"]:
        print(f"\n{len(plan['refuser'])} fichier(s) de données ignorés (jamais remplacés).")

    if not controler_nouveau():
        print("\nRetour automatique à la version d'avant…")
        _restaurer(sauvegarde, journal)
        print(
            f"Version {version_locale()} rétablie. Signale le problème : "
            f"https://github.com/{DEPOT}/issues"
        )
        return 1
    afficher_nouveautes(changelog, locale, distante)
    return apres(changes_requirements="requirements.txt" in plan["remplacer"] + plan["ajouter"])


def annuler_zip():
    journaux = sorted(SAUVEGARDES.glob(f"*/{JOURNAL}")) if SAUVEGARDES.exists() else []
    for j in reversed(journaux):
        journal = json.loads(j.read_text(encoding="utf-8"))
        if journal.get("annule"):
            continue
        _restaurer(j.parent, journal)
        print(
            f"Mise à jour du {journal.get('date')} annulée : retour de "
            f"{journal.get('apres')} à {journal.get('avant')}."
        )
        return 0
    print("Aucune mise à jour à annuler.")
    return 1


# ── Chemin git ──────────────────────────────────────────────────────────────


def _git(*a, **kw):
    return subprocess.run(
        ["git", *a],
        cwd=RACINE,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        **kw,
    )


def _git_fichier(ref, chemin):
    r = _git("show", f"{ref}:{chemin}")
    return r.stdout if r.returncode == 0 else ""


def par_git(args):
    print("Dossier git détecté : git pull.")
    if _git("rev-parse", "--abbrev-ref", "@{u}").returncode:
        print(
            "! Ce dossier git ne suit aucune branche distante (`git branch -u origin/main` "
            "pour la rétablir)."
        )
        return 1
    if _git("fetch", "--quiet").returncode:
        print("! git fetch a échoué (hors ligne ?).")
        return 1
    locale = version_locale()
    distante = _git_fichier("@{u}", "VERSION").strip() or locale
    changelog = _git_fichier("@{u}", "CHANGELOG.md")
    lie = _git("merge-base", "HEAD", "@{u}").returncode == 0
    n = _git("rev-list", "--count", "HEAD..@{u}").stdout.strip() or "0"
    print(f"Version installée : {locale} · version disponible : {distante}")

    if args.verifier:
        print(f"{n} changement(s) à récupérer." if n != "0" else "Déjà à jour.")
        if n != "0":
            afficher_nouveautes(changelog, locale, distante)
        return 0
    if not lie:
        # Historique du depot public reecrit : un pull rejouerait tout en conflit.
        if not args.forcer:
            print(
                "\n! L'historique du dépôt GitHub a été réécrit depuis ton installation.\n"
                "  Relance avec --forcer : ton dossier passe sur la nouvelle version, tes\n"
                "  données (ignorées par git) et tes fichiers modifiés restent en place."
            )
            return 1
        avant = _git("rev-parse", "HEAD").stdout.strip()
        GIT_AVANT.write_text(avant, encoding="utf-8")
        r = _git("reset", "--keep", "@{u}")
    else:
        if n == "0" and not args.forcer:
            print("Déjà à jour.")
            return 0
        avant = _git("rev-parse", "HEAD").stdout.strip()
        GIT_AVANT.write_text(avant, encoding="utf-8")
        r = subprocess.run(["git", "pull", "--rebase", "--autostash"], cwd=RACINE)
    if r.returncode:
        GIT_AVANT.unlink(missing_ok=True)  # rien d'installe : rien a annuler
        print((getattr(r, "stderr", "") or "").strip())
        print(
            "\n! La mise à jour git a échoué (voir le message ci-dessus). Tes fichiers n'ont "
            "pas été perdus : `git status` montre où en est le dossier."
        )
        return 1
    if not controler_nouveau():
        print("\nRetour automatique à la version d'avant…")
        _git("reset", "--keep", avant)
        print(
            f"Version {version_locale()} rétablie. Signale le problème : "
            f"https://github.com/{DEPOT}/issues"
        )
        return 1
    changes = _git("diff", "--name-only", avant, "HEAD").stdout.split()
    afficher_nouveautes(changelog, locale, distante)
    return apres(changes_requirements="requirements.txt" in changes)


def annuler_git():
    if not GIT_AVANT.exists():
        print("Aucune mise à jour à annuler.")
        return 1
    avant = GIT_AVANT.read_text(encoding="utf-8").strip()
    r = _git("reset", "--keep", avant)
    if r.returncode:
        print(f"! Retour impossible : {r.stderr.strip()}")
        return 1
    GIT_AVANT.unlink()
    print(f"Retour à la version {version_locale()} ({avant[:7]}).")
    return 0


def main():
    ap = argparse.ArgumentParser(description="Met JobHunter à jour depuis GitHub.")
    ap.add_argument(
        "--verifier",
        action="store_true",
        help="dire s'il y a une mise à jour et ce qu'elle apporte",
    )
    ap.add_argument("--forcer", action="store_true", help="réinstaller même à version égale")
    ap.add_argument(
        "--annuler",
        action="store_true",
        help="revenir à la version d'avant la dernière mise à jour",
    )
    ap.add_argument(
        "--controler",
        action="store_true",
        help="(mise a jour) verifier que cette installation se charge",
    )
    ap.add_argument(
        "--initialiser",
        action="store_true",
        help="(installeur) noter l'empreinte des fichiers tels qu'installés",
    )
    args = ap.parse_args()
    if _gele.est_gele():
        # Application installée : pas de fichiers à remplacer un par un, la nouvelle
        # version est un nouvel installateur, qui garde les données (Documents/JobHunter).
        v = nouvelle_version(intervalle_h=0)
        print(
            f"Version installée : {version_locale()}"
            + (f" · disponible : {v}" if v else " · c'est la plus récente.")
        )
        if v and not args.verifier:
            print("Télécharge JobHunterSetup.exe sur la page qui s'ouvre, puis lance-le.")
            import webbrowser

            webbrowser.open(PAGE_VERSIONS)
        return 0
    if args.controler:
        if not controler():
            return 1
        signaler_tache_ancienne()
        return 0
    if args.initialiser:
        if initialiser():
            print("Empreinte de l'installation enregistrée (.maj_manifeste.json).")
        return 0
    if not (RACINE / "VERSION").exists():
        # Copie de developpement, ou depot qui recoit le moteur par copie : il n'y a
        # pas de version publiee a comparer, et un `git pull` n'aurait pas de sens.
        print(
            "Pas de fichier VERSION : ce dossier n'est pas une installation publiée de "
            "JobHunter (copie de développement ?). Rien à mettre à jour ici."
        )
        return 1
    git = (RACINE / ".git").exists() and shutil.which("git")
    if args.annuler:
        return annuler_git() if git else annuler_zip()
    return par_git(args) if git else par_zip(args)


if __name__ == "__main__":
    sys.exit(main())
