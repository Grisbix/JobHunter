"""A real update, from an older published version, on fictitious data.

    python tools/update_transition.py preparer <installation>
    python tools/update_transition.py verifier <installation> <expected version>

`preparer` writes, in an installation extracted from an older release's ZIP, what a
user has there: a queue, applications, a profile, a CV, a second profile, a fake API
key, and a program file they edited. It records the fingerprint of each. `verifier`
runs after `JobHunter.pyw update`: the expected version is installed, every piece of
user data is byte for byte the same, the edited file is still theirs.

Used by .github/workflows/update-transition.yml after each release (the previous and
the one before, to the new one); runnable by hand in a throwaway folder. Never on real
data: everything here is invented.
"""

import hashlib
import json
import sys
from pathlib import Path

EMPREINTES = ".transition_empreintes.json"
MARQUE = "\n<!-- edited by the user: must survive the update -->\n"


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _ecrire(f: Path, contenu: object) -> None:
    f.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(contenu, bytes):
        f.write_bytes(contenu)
    else:
        f.write_text(json.dumps(contenu, ensure_ascii=False, indent=1), encoding="utf-8")


def donnees(r: Path) -> list[Path]:
    """The user's files written by `preparer` (3.0 layout)."""
    offre = {
        "entreprise": "Atelier Nova",
        "poste": "ESG Analyst",
        "url": "https://jobs.example.com/1",
        "statut": "Scan 2026-10-01",
        "fit": 9,
    }
    fichiers = {
        "data/apply_queue.json": [offre],
        "data/applications.json": {"Atelier Nova|ESG Analyst": {"s": "postulé", "d": "01/10"}},
        "data/adzuna.json": {"app_id": "FICTIF", "app_key": "FICTIF"},
        "My_CV/cv_camille.docx": b"PK fictitious CV",
        "profiles/b/profile/profile.json": {"_profil_nom": "Second", "identite": {}},
        "profiles/b/data/apply_queue.json": [dict(offre, entreprise="Studio Lumen")],
        "data/_active_profile.json": {"profil": ""},
    }
    exemple = r / "profile" / "example_finance_esg.json"
    fichiers["profile/profile.json"] = json.loads(exemple.read_text(encoding="utf-8"))
    for rel, contenu in fichiers.items():
        if not (r / rel).exists():
            _ecrire(r / rel, contenu)
    return [r / rel for rel in fichiers]


def preparer(r: Path) -> int:
    if not (r / "data").is_dir():
        print(f"! {r} n'est pas une installation 3.x (pas de data/)")
        return 1
    fichiers = donnees(r)
    readme = r / "README.md"
    readme.write_text(readme.read_text(encoding="utf-8") + MARQUE, encoding="utf-8")
    empreintes = {str(f.relative_to(r)).replace("\\", "/"): _sha(f) for f in fichiers}
    (r / EMPREINTES).write_text(json.dumps(empreintes, indent=1), encoding="utf-8")
    version = (r / "VERSION").read_text(encoding="utf-8").strip()
    print(f"Installation {version} préparée : {len(empreintes)} fichiers de données fictifs.")
    return 0


def verifier(r: Path, attendue: str) -> int:
    erreurs = []
    version = (r / "VERSION").read_text(encoding="utf-8").strip()
    if version != attendue:
        erreurs.append(f"version {version} installée, {attendue} attendue")
    empreintes = json.loads((r / EMPREINTES).read_text(encoding="utf-8"))
    for rel, sha in empreintes.items():
        f = r / rel
        if not f.exists():
            erreurs.append(f"donnée perdue : {rel}")
        elif _sha(f) != sha:
            erreurs.append(f"donnée modifiée : {rel}")
    if MARQUE not in (r / "README.md").read_text(encoding="utf-8"):
        erreurs.append("README.md modifié par l'utilisateur : sa retouche a disparu")
    for e in erreurs:
        print("✗", e)
    if not erreurs:
        print(
            f"✓ {version} installée, {len(empreintes)} fichiers de données intacts, retouche gardée."
        )
    return 1 if erreurs else 0


def main(argv: list[str]) -> int:
    if len(argv) >= 2 and argv[0] == "preparer":
        return preparer(Path(argv[1]))
    if len(argv) >= 3 and argv[0] == "verifier":
        return verifier(Path(argv[1]), argv[2])
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    sys.exit(main(sys.argv[1:]))
