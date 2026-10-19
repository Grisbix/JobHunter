#!/usr/bin/env python3
"""mise_a_jour.py — Updates JobHunter from GitHub, without touching your data.

    python JobHunter.pyw maj            # updates if a more recent version exists
    python JobHunter.pyw maj --verifier # says whether there is an update, and what it brings
    python JobHunter.pyw maj --forcer   # reinstalls even at an equal version
    python JobHunter.pyw maj --annuler  # goes back to the version before the last update

Three paths:
  - folder cloned with git  -> `git pull --rebase --autostash`;
  - unzipped folder         -> downloads the ZIP (the main branch, or the tag of the
                               announced version once releases are signed, ADR 0012)
                               and replaces the program's files, one by one;
  - installed application   -> downloads, checks and opens the next installer.

In the first two cases, the update:
  1. displays what is new (CHANGELOG.md) between your version and the new one;
  2. installs, then CHECKS that the program loads (compilation of all the scripts,
     import of the core modules on the example profile);
  3. if the check fails, goes back by itself to the previous version;
  4. reports the new profile settings that yours does not have yet.

WHAT IS NEVER TOUCHED: your profile, your CV (Mon_CV, CV), your letters, the queue of
offers, the application tracking, the API keys — everything git ignores. These files
are not in the ZIP, and a guard refuses them anyway.

A PROGRAM FILE THAT YOU MODIFIED is kept as is; the new version is put next to it, as
`.nouveau`, and the summary tells you. "Modified" = different from what the installed
version contained: the fingerprint comes from the manifest (`.maj_manifeste.json`,
written by the installer then by each update) or, failing that, from the official ZIP
of your version (tag `v<version>`).

A FILE REMOVED from the program is deleted if it was not modified (copied into the
backup), kept otherwise. A file you created is never touched: only the files of an
official version can be removed.

Each file replaced or removed is first copied into `_sauvegarde_maj/<date>/`, with a
log: `--annuler` uses it.
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
from jobhunter import signature as _sig
from jobhunter.reseau import exiger_http

# line_buffering: our lines interleave in the right order with the output of git and
# pip, and are displayed as they come in the application's log.
sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)  # type: ignore[union-attr]  # console : TextIOWrapper

RACINE = _racine.racine()
DEPOT = "Grisbix/JobHunter"
ZIP_URL = f"https://github.com/{DEPOT}/archive/refs/heads/main.zip"
PAGE_VERSIONS = f"https://github.com/{DEPOT}/releases/latest"
TAG_URL = f"https://github.com/{DEPOT}/archive/refs/tags/v{{}}.zip"
VERSION_URL = f"https://raw.githubusercontent.com/{DEPOT}/main/VERSION"
# Files attached to the release v<version>: the signature and the installer.
ASSET_URL = f"https://github.com/{DEPOT}/releases/download/v{{}}/{{}}"
SETUP = "JobHunterSetup.exe"
MANIFESTE = RACINE / ".maj_manifeste.json"
SAUVEGARDES = RACINE / "_sauvegarde_maj"
DERNIERE_VERIF = RACINE / ".maj_derniere_verif"
GIT_AVANT = RACINE / ".maj_git_avant"
JOURNAL = "_journal.json"
EXEMPLE = "profil/exemple_finance_esg.json"

# User data: never written, even if a ZIP contained it.
# .venv: the Python environment created by installer.bat (2.17); out of the manifest,
# otherwise an update would remove from it the files missing from the new version.
PROTEGES_PREFIXES = (
    "profil/profil",
    "Mon_CV/",
    "CV/",
    "Lettres/",
    "_sauvegarde_maj/",
    ".git/",
    ".venv/",
)
PROTEGES_NOMS = {
    "Scripts/apply_queue.json",
    "Scripts/descriptions.json",
    "Scripts/suivi.json",
    "Scripts/adzuna.json",
    "Scripts/francetravail.json",
    "Scripts/gmail_client.json",
    "Scripts/gmail_token.json",
    "Scripts/jooble.json",
    "Scripts/apply_runner_done.json",
    "Scripts/chemins.json",
}
# Written by premier_lancement: presumed modified when no reference exists.
REECRITS_AU_PREMIER_LANCEMENT = {"Scripts/sources_config.json"}
# Never "modified by the user": a VERSION kept as is would freeze the installed
# version and the update would come up again at every launch.
TOUJOURS_REMPLACES = {"VERSION", "CHANGELOG.md"}
# Modules loaded by the post-update check: the core of sorting and documents.
# The check is the one of the INSTALLED version (controler_nouveau): this list therefore
# always describes the tree that contains it.
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
    # the application itself (without opening a window): an update that breaks it
    # would be cancelled instead of leaving a double-click without effect.
    "jobhunter.app",
)


def _sha(b):
    return hashlib.sha256(b).hexdigest()


def protege(rel):
    if rel in PROTEGES_NOMS or rel.startswith(PROTEGES_PREFIXES):
        return True
    return rel.startswith("profil/") and not Path(rel).name.startswith("exemple_")


def version_locale():
    # Installed application: the version shipped with the program, not a file of the
    # user's data.
    base = Path(getattr(sys, "_MEIPASS", RACINE)) if _gele.est_gele() else RACINE
    p = base / "VERSION"
    return p.read_text(encoding="utf-8").strip() if p.exists() else "0"


def _cle_version(v):
    return tuple(int(x) if x.isdigit() else 0 for x in v.strip().split("."))


def _get(url, timeout):
    req = urllib.request.Request(exiger_http(url), headers={"User-Agent": "JobHunter-mise-a-jour"})
    with urllib.request.urlopen(req, timeout=timeout) as r:  # nosec B310 : scheme checked by exiger_http
        return r.read()


def nouvelle_version(timeout=5, intervalle_h=24):
    """Version disponible si elle est plus recente que l'installee, sinon None.

    Pour l'application, au demarrage : un seul petit fichier (VERSION), au plus
    une fois par jour, et toute erreur (hors ligne, GitHub lent) vaut « rien de
    neuf » — une verification ne doit jamais gener le lancement."""
    # Without a VERSION file, it is not a published installation (development
    # copy, repository that syncs the engine): nothing to announce.
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
    """The "## x.y.z" sections of the CHANGELOG more recent than `depuis` (and at most
    `jusqua`), in file order (the most recent first)."""
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
    """Settings present in the example profile and missing from yours. A key whose
    parent is missing is only cited once (the parent)."""
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
            f"Pour les régler : demande à Claude « /configure-profile », ou copie-les "
            f"depuis {EXEMPLE} dans profil/profil.json."
        )


# ── Post-update check ────────────────────────────────────────────────────────


def controler():
    """True if the installed program loads. Compiles each script, then imports the
    core modules in a fresh process, on the example profile (the check does not
    depend on your profile and does not read it)."""
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
    """2.0 moved the programs into the package: a collection scheduled BEFORE targets
    Scripts/pipeline_quotidien.py, which no longer exists, and would fail every morning
    silently. We say so (read-only: the task is not changed)."""
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
    """The check of the version just installed, by ITS own code.

    This process is the old version: its list of modules and its way of loading them
    describe the old tree. A version that moves files (2.0: the Scripts/ facades
    removed) would be wrongly cancelled. So we run the check of the new tree, through a
    stable entry: `python -m jobhunter maj --controler`."""
    if not (RACINE / "src" / "jobhunter" / "cli.py").exists():
        return controler()  # tree from before 1.12: no single entry
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


def installer_dependances(changes_requirements):
    """Installs the new version's dependencies, BEFORE its check.

    Before 19/10/2026, the installation came after the check and its return code was
    ignored: a new dependency required at import made the update be cancelled before
    it had been installed, and a failed pip ended with "JobHunter est à jour" (audit of
    19/10/2026). Rolling back does not uninstall an added dependency: harmless, the old
    version does not import it.

    Returns:
        False if pip failed; the caller then goes back to the previous version.
    """
    if not changes_requirements:
        return True
    print("\nLes dépendances ont changé : installation…")
    r = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-q", "-r", str(RACINE / "requirements.txt")]
    )
    if r.returncode:
        print(f"\n! L'installation des dépendances a échoué (pip, code {r.returncode}).")
        return False
    return True


def apres():
    """Le message de fin, une fois la nouvelle version installée ET contrôlée."""
    signaler_reglages()
    print(f"\nJobHunter est à jour (version {version_locale()}). Relance l'application.")
    return 0


# ── Chemin ZIP ──────────────────────────────────────────────────────────────


def telecharger(url=ZIP_URL, timeout=120):
    print(f"Téléchargement de {url} …")
    return _get(url, timeout)


def fichiers_a_installer():
    """The files of the proposed version, checked by the author's signature.

    Without a public key in this version (`signature.CLE_PUBLIQUE` empty), nothing is
    signed: we take the ZIP of main, as before 2.18, and say so. With a key, we take the
    ZIP of the announced version's tag, and each of its files must have the fingerprint
    that the signed manifest gives it.

    Raises:
        signature.SignatureInvalide: version refused (nothing was written).
    """
    if not _sig.CLE_PUBLIQUE:
        print("(Versions non signées : la clé de l'auteur n'est pas encore publiée.)")
        return fichiers_du_zip(telecharger())
    distante = _get(VERSION_URL, 30)[:64].decode("utf-8").strip()
    nouveaux = fichiers_du_zip(telecharger(TAG_URL.format(distante)))
    m = _sig.ouvrir(_get(ASSET_URL.format(distante, _sig.FICHIER), 60), distante)
    _sig.controler_fichiers(m, nouveaux)
    print(f"Signature de l'auteur vérifiée : {len(nouveaux)} fichiers de la {distante}.")
    return nouveaux


def maj_application(verifier_seulement):
    """Installed application: downloads the new installer, checks it, opens it.

    With a public key, the installer must have the fingerprint of the signed manifest.
    Without one, we at least check the fingerprint published next to it
    (`JobHunterSetup.exe.sha256`), which protects against a damaged download, not
    against a booby-trapped release. The installer opens normally: it is the user who
    moves it forward; it closes JobHunter (CloseApplications) and keeps the data
    (Documents/JobHunter).
    """
    v = nouvelle_version(intervalle_h=0)
    print(
        f"Version installée : {version_locale()}"
        + (f" · disponible : {v}" if v else " · c'est la plus récente.")
    )
    if not v or verifier_seulement:
        return 0
    try:
        print(f"Téléchargement de {SETUP} {v} …")
        exe = _get(ASSET_URL.format(v, SETUP), 900)
        if _sig.CLE_PUBLIQUE:
            m = _sig.ouvrir(_get(ASSET_URL.format(v, _sig.FICHIER), 60), v)
            _sig.controler_setup(m, exe)
            print("Signature de l'auteur vérifiée.")
        else:
            publiee = _get(ASSET_URL.format(v, SETUP + ".sha256"), 60).decode().split()[0]
            if publiee.lower() != hashlib.sha256(exe).hexdigest():
                raise _sig.SignatureInvalide(f"{SETUP} ne correspond pas à son empreinte publiée")
            print("(Version non signée : empreinte publiée vérifiée.)")
    except _sig.SignatureInvalide as e:
        print(f"! Mise à jour refusée : {e}. Rien n'a été installé.")
        return 1
    except Exception as e:
        print(f"! Téléchargement impossible ({type(e).__name__}) : la page des versions s'ouvre.")
        import webbrowser

        webbrowser.open(PAGE_VERSIONS)
        return 1
    import tempfile

    chemin = Path(tempfile.gettempdir()) / f"JobHunterSetup-{v}.exe"
    chemin.write_bytes(exe)
    print("L'installateur s'ouvre : suis ses étapes. Tes données sont gardées.")
    subprocess.Popen([str(chemin)], close_fds=True)  # nosec B603 : file checked above
    return 0


def chemin_sur(rel):
    """A ZIP path that stays inside the program's folder.

    Refuses absolute paths, drives ("C:"), climbing up ("..") and backslashes: a
    booby-trapped ZIP must never write outside RACINE.
    """
    if not rel or "\\" in rel or rel.startswith("/") or ":" in rel:
        return False
    return ".." not in rel.split("/")


def fichiers_du_zip(data):
    """{relative path: content}; the ZIP's root folder (JobHunter-main/) is removed."""
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
    """Fingerprint of the installation as unzipped, BEFORE the user modifies anything
    (called by installer.bat / installer.sh).

    Without it, the reference is the ZIP of the v<version> tag: exact for those who
    took a release, wrong for those who took the ZIP of main between two releases (its
    files differ from the tag and would look modified). Does nothing if there is
    already a manifest, a git repository or no VERSION."""
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
    """Fingerprints of the installed version's files: the manifest if it exists,
    otherwise the official ZIP of that version (GitHub tag). {} if not found: we then
    fall back on the old rule (nothing is presumed modified, nothing is removed)."""
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
    """Decides file by file, without writing anything.

    nouveaux  : {rel: content} of the new version
    locaux    : {rel: fingerprint} of the files present on disk
    reference : {rel: fingerprint} of the installed version ({} if unknown)
    Returns {"remplacer", "ajouter", "garder", "retirer", "garder_retire", "refuser"}."""
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
            pass  # modified by the user, unchanged upstream: nothing to propose
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
    """Undoes a ZIP update according to its log."""
    for rel in journal.get("remplaces", []) + journal.get("retires", []):
        src = sauvegarde / rel
        if src.exists():
            (RACINE / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, RACINE / rel)
    installes = journal.get("manifeste_apres", {})
    for rel in journal.get("ajoutes", []):
        p = RACINE / rel
        # a file added then modified by the user stays in place
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
        nouveaux = fichiers_a_installer()
    except _sig.SignatureInvalide as e:
        print(f"! Mise à jour refusée : {e}. Rien n'a été modifié.")
        return 1
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

    # The manifest afterwards: what the new version installed. A kept file
    # (modified) keeps the reference fingerprint: it stays "modified" afterwards.
    manifeste = dict(reference)
    for rel in plan["retirer"] + plan["garder_retire"]:
        manifeste.pop(rel, None)
    for rel in plan["remplacer"] + plan["ajouter"] + plan["identiques"]:
        manifeste[rel] = _sha(nouveaux[rel])

    # Log written BEFORE any write: a failure in the middle (disk full,
    # locked file) is undone like a failed check.
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

    deps = "requirements.txt" in plan["remplacer"] + plan["ajouter"]
    if not installer_dependances(deps) or not controler_nouveau():
        print("\nRetour automatique à la version d'avant…")
        _restaurer(sauvegarde, journal)
        print(
            f"Version {version_locale()} rétablie. Signale le problème : "
            f"https://github.com/{DEPOT}/issues"
        )
        return 1
    afficher_nouveautes(changelog, locale, distante)
    return apres()


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
        # History of the public repository rewritten: a pull would replay everything in conflict.
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
        GIT_AVANT.unlink(missing_ok=True)  # nothing installed: nothing to cancel
        print((getattr(r, "stderr", "") or "").strip())
        print(
            "\n! La mise à jour git a échoué (voir le message ci-dessus). Tes fichiers n'ont "
            "pas été perdus : `git status` montre où en est le dossier."
        )
        return 1
    changes = _git("diff", "--name-only", avant, "HEAD").stdout.split()
    if not installer_dependances("requirements.txt" in changes) or not controler_nouveau():
        print("\nRetour automatique à la version d'avant…")
        _git("reset", "--keep", avant)
        print(
            f"Version {version_locale()} rétablie. Signale le problème : "
            f"https://github.com/{DEPOT}/issues"
        )
        return 1
    afficher_nouveautes(changelog, locale, distante)
    return apres()


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
        # Installed application: no files to replace one by one, the new
        # version is a new installer, which keeps the data (Documents/JobHunter).
        return maj_application(args.verifier)
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
        # Development copy, or repository that receives the engine by copy: there is
        # no published version to compare, and a `git pull` would make no sense.
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
