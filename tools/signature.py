"""Sign a published version of JobHunter, with the author's private key.

    uv run python tools/signature.py cle              # once: creates the key pair
    uv run python tools/signature.py signer 2.18.0    # after the release CI
    uv run python tools/signature.py signer 2.18.0 --publier   # and attaches it to the release

`cle` creates the private key in `~/.jobhunter/cle_signature`, OUTSIDE the repository,
and writes the public key into `src/jobhunter/signature.py` (to commit, and to publish
in a release). The private key is never displayed. **Back it up** (USB key, password
manager): if lost, no version can be signed any more, and every installation will have
to be redone by hand with the new public key.

`approuver` is what a scheduled task runs every hour, without a console: for each
release published since the last signed one, whose installer the CI has built, a window
asks « Signer JobHunter X.Y.Z ? » with its date and commit. Yes signs and publishes it;
No is remembered and never asked again. Signing stays an act of the author on purpose:
signing whatever appears on GitHub automatically would also sign what an attacker who
took the GitHub account published, which is exactly what the signature is for (ADR 0012).

`signer` downloads what the installations will download — the ZIP of the
`v<version>` tag and the `JobHunterSetup.exe` attached by the CI —, builds the manifest,
signs it and writes `signature.json`. `--publier` attaches it to the release
(`gh release upload`). Run it **after** the release's "installer" workflow has
finished: without the installer, the installed application would refuse the update.
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE / "src"))

if sys.stdout is None:
    # pythonw (the hourly `approuver` task): no console. Redirected BEFORE importing
    # the engine, whose update module reconfigures sys.stdout when imported.
    _log = Path.home() / ".jobhunter" / "signature.log"
    _log.parent.mkdir(parents=True, exist_ok=True)
    sys.stdout = sys.stderr = _log.open("a", encoding="utf-8")
    print(f"===== {__import__('time').strftime('%Y-%m-%d %H:%M')}", flush=True)

from jobhunter import signature as sig  # noqa: E402
from jobhunter.network import exiger_http  # noqa: E402
from jobhunter.programs import update as maj  # noqa: E402

CLE_PRIVEE = Path(
    os.environ.get("JOBHUNTER_CLE_SIGNATURE", Path.home() / ".jobhunter" / "cle_signature")
)
MODULE = RACINE / "src" / "jobhunter" / "signature.py"


REFUSEES = CLE_PRIVEE.parent / "versions_refusees.txt"
# gh launched from pythonw (the hourly task) would flash a console window each time.
_SANS_FENETRE = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _gh(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # nosec B603 B607 : gh, arguments built here
        ["gh", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=check,
        creationflags=_SANS_FENETRE,
    )


def _get(url: str) -> bytes:
    req = urllib.request.Request(exiger_http(url), headers={"User-Agent": "JobHunter-signature"})
    with urllib.request.urlopen(req, timeout=600) as r:  # nosec B310 : scheme checked
        return bytes(r.read())


def creer_cle() -> int:
    if CLE_PRIVEE.exists():
        print(f"Une clé existe déjà ({CLE_PRIVEE}) : rien n'est remplacé.")
        return 1
    import secrets

    secret = secrets.token_bytes(32)
    CLE_PRIVEE.parent.mkdir(parents=True, exist_ok=True)
    CLE_PRIVEE.write_text(secret.hex() + "\n", encoding="ascii")
    publique = sig.publique(secret).hex()
    texte = MODULE.read_text(encoding="utf-8")
    ligne = 'CLE_PUBLIQUE = ""'
    if ligne not in texte:
        print("! CLE_PUBLIQUE déjà posée dans signature.py : vérifie-la à la main.")
        return 1
    MODULE.write_text(texte.replace(ligne, f'CLE_PUBLIQUE = "{publique}"', 1), encoding="utf-8")
    print(f"Clé privée : {CLE_PRIVEE} (jamais affichée — sauvegarde ce fichier).")
    print(f"Clé publique : {publique}, écrite dans src/jobhunter/signature.py.")
    print("Commite-la et publie une version : les suivantes devront être signées.")
    return 0


def signer(version: str, publier: bool) -> int:
    if not CLE_PRIVEE.exists():
        print(f"Pas de clé privée ({CLE_PRIVEE}) : lance d'abord « cle ».")
        return 1
    secret = bytes.fromhex(CLE_PRIVEE.read_text(encoding="ascii").strip())
    if sig.publique(secret).hex() != sig.CLE_PUBLIQUE:
        print("! Cette clé privée ne correspond pas à CLE_PUBLIQUE du dépôt : rien n'est signé.")
        return 1
    print(f"Téléchargement de la {version} (ZIP de l'étiquette, installateur) …")
    fichiers = maj.fichiers_du_zip(_get(maj.TAG_URL.format(version)))
    setup = _get(maj.ASSET_URL.format(version, maj.SETUP))
    publiee = _get(maj.ASSET_URL.format(version, maj.SETUP + ".sha256")).decode().split()[0]
    if publiee.lower() != hashlib.sha256(setup).hexdigest():
        print(
            "! L'installateur ne correspond pas à l'empreinte publiée par la CI : rien n'est signé."
        )
        return 1
    if (fichiers.get("VERSION") or b"").decode().strip() != version:
        print("! Le VERSION de l'étiquette n'est pas cette version : rien n'est signé.")
        return 1
    contenu = sig.emballer(secret, sig.manifeste(version, fichiers, setup))
    m = sig.ouvrir(contenu, version)  # read back as each installation will
    sig.controler_fichiers(m, fichiers)
    sig.controler_setup(m, setup)
    sortie = RACINE / "dist" / sig.FICHIER
    sortie.parent.mkdir(exist_ok=True)
    sortie.write_bytes(contenu)
    print(f"{sig.FICHIER} écrit : {len(fichiers)} fichiers et l'installateur ({sortie}).")
    if publier:
        _gh("release", "upload", f"v{version}", str(sortie), "--clobber", "-R", maj.DEPOT)
        print(f"Attaché à la release v{version}.")
        # The real-update test waited for this signature (installations that carry the
        # key refuse an unsigned version): run it now.
        r = _gh("workflow", "run", "update-transition.yml", "-R", maj.DEPOT, check=False)
        if r.returncode == 0:
            print("Test de mise à jour réelle relancé (workflow update-transition).")
    else:
        print(f"Pour l'attacher : gh release upload v{version} {sortie} --clobber")
    return 0


def en_attente() -> list[dict[str, str]]:
    """Releases published since the last signed one, installer built, not refused.

    Newest first. Older unsigned releases (before the key existed) are not asked for:
    the search stops at the first release that carries a signature.
    """
    rels = json.loads(_gh("api", f"repos/{maj.DEPOT}/releases?per_page=10").stdout)
    refusees = set(REFUSEES.read_text(encoding="utf-8").split()) if REFUSEES.exists() else set()
    attente = []
    for r in rels:
        if r.get("draft") or r.get("prerelease"):
            continue
        noms = {a["name"] for a in r.get("assets", [])}
        if sig.FICHIER in noms:
            break
        version = str(r["tag_name"]).lstrip("v")
        if maj.SETUP + ".sha256" not in noms or version in refusees:
            continue  # the installer CI has not finished yet / the author said no
        c = json.loads(_gh("api", f"repos/{maj.DEPOT}/commits/{r['tag_name']}").stdout)
        attente.append(
            {
                "version": version,
                "date": str(r.get("published_at", ""))[:16].replace("T", " "),
                "commit": str(c["commit"]["message"]).splitlines()[0],
            }
        )
    return attente


def approuver(demander: object = None) -> int:
    """One window per release waiting for the author's signature; yes signs it."""
    attente = en_attente()
    if not attente:
        return 0
    if demander is None:
        import tkinter as tk
        from tkinter import messagebox

        racine = tk.Tk()
        racine.withdraw()
        racine.attributes("-topmost", True)

        def demander(titre: str, question: str) -> bool:
            return bool(messagebox.askyesno(titre, question, parent=racine))

    rc = 0
    for r in reversed(attente):  # oldest first
        question = (
            f"JobHunter {r['version']} a été publiée le {r['date']} (UTC).\n\n"
            f"Commit : {r['commit']}\n\n"
            "Signer cette version ? Réponds oui seulement si c'est une version que tu "
            "as demandée : une version inattendue peut venir d'un compte GitHub piraté."
        )
        if demander("Signer une version de JobHunter", question):  # type: ignore[operator]
            print(f"{r['version']} : signature approuvée.")
            rc = max(rc, signer(r["version"], True))
        else:
            print(f"{r['version']} : refusée, ne sera plus proposée.")
            REFUSEES.parent.mkdir(parents=True, exist_ok=True)
            with REFUSEES.open("a", encoding="utf-8") as f:
                f.write(r["version"] + "\n")
    return rc


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sous = ap.add_subparsers(dest="action", required=True)
    sous.add_parser("cle", help="créer la paire de clés (une seule fois)")
    s = sous.add_parser("signer", help="signer une version publiée")
    s.add_argument("version")
    s.add_argument("--publier", action="store_true", help="attacher signature.json à la release")
    sous.add_parser("approuver", help="proposer de signer les versions en attente (tâche horaire)")
    a = ap.parse_args()
    if a.action == "cle":
        return creer_cle()
    if a.action == "approuver":
        return approuver()
    return signer(a.version, a.publier)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
