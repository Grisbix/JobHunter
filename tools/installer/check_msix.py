#!/usr/bin/env python3
"""Checks a release's JobHunter.msix against the author's signature, before the Store.

    python tools/installer/check_msix.py 3.88.0 JobHunter.msix signature.json

Why: the CI sends the release's JobHunter.msix to the Microsoft Store (store.yml). The
installer and the sources were checked by each installation against `signature.json`
(ADR 0012); the Store's package was not in it, so whoever could replace a release's
file reached every Store user with nothing but Microsoft's certification in the way
(audit 2026-11-15). Since 3.88 the signed manifest carries the package's fingerprint.

What it does not cover: a repository whose code is rewritten can rewrite this check and
the public key with it. The signature protects a release's files, not the workflow.

Exit code: 0 the package is the signed one, or the manifest names none (signed by a
tool older than 3.88: said as a warning); 1 no valid signature, or another package.
Only `jobhunter.signature` is imported: standard library, nothing to install.
"""

import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(RACINE / "src"))

from jobhunter import signature as sig  # noqa: E402


def controler(version: str, msix: Path, signature: Path) -> tuple[int, str]:
    """(exit code, sentence) for this package and this `signature.json`."""
    try:
        m = sig.ouvrir(signature.read_bytes(), version)
        if sig.controler_msix(m, msix.read_bytes()):
            return 0, f"{msix.name} est le paquet signé de la {version}."
    except OSError as e:
        return 1, f"fichier illisible : {e}"
    except sig.SignatureInvalide as e:
        return 1, f"refusé : {e}"
    return 0, (
        f"::warning::la signature de la {version} ne nomme pas de paquet MSIX "
        "(signée par un outil d'avant la 3.88) : envoyé sans contrôle."
    )


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 3:
        print(__doc__.split("\n")[2].strip())
        return 2
    code, phrase = controler(args[0].lstrip("v"), Path(args[1]), Path(args[2]))
    print(phrase)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
