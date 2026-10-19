"""Sign a published version of JobHunter, with the author's private key.

    uv run python outils/signature.py cle              # once: creates the key pair
    uv run python outils/signature.py signer 2.18.0    # after the release CI
    uv run python outils/signature.py signer 2.18.0 --publier   # and attaches it to the release

`cle` creates the private key in `~/.jobhunter/cle_signature`, OUTSIDE the repository,
and writes the public key into `src/jobhunter/signature.py` (to commit, and to publish
in a release). The private key is never displayed. **Back it up** (USB key, password
manager): if lost, no version can be signed any more, and every installation will have
to be redone by hand with the new public key.

`signer` downloads what the installations will download — the ZIP of the
`v<version>` tag and the `JobHunterSetup.exe` attached by the CI —, builds the manifest,
signs it and writes `signature.json`. `--publier` attaches it to the release
(`gh release upload`). Run it **after** the release's "installateur" workflow has
finished: without the installer, the installed application would refuse the update.
"""

import argparse
import hashlib
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE / "src"))

from jobhunter import signature as sig  # noqa: E402
from jobhunter.programmes import mise_a_jour as maj  # noqa: E402
from jobhunter.reseau import exiger_http  # noqa: E402

CLE_PRIVEE = Path(
    os.environ.get("JOBHUNTER_CLE_SIGNATURE", Path.home() / ".jobhunter" / "cle_signature")
)
MODULE = RACINE / "src" / "jobhunter" / "signature.py"


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
        subprocess.run(  # nosec B603 B607 : gh, arguments fixes
            ["gh", "release", "upload", f"v{version}", str(sortie), "--clobber"], check=True
        )
        print(f"Attaché à la release v{version}.")
    else:
        print(f"Pour l'attacher : gh release upload v{version} {sortie} --clobber")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sous = ap.add_subparsers(dest="action", required=True)
    sous.add_parser("cle", help="créer la paire de clés (une seule fois)")
    s = sous.add_parser("signer", help="signer une version publiée")
    s.add_argument("version")
    s.add_argument("--publier", action="store_true", help="attacher signature.json à la release")
    a = ap.parse_args()
    return creer_cle() if a.action == "cle" else signer(a.version, a.publier)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    sys.exit(main())
