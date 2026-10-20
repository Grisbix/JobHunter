"""Where the data lives: the root, its data folder, and the names of what is in it.

Project rule: NEVER a hard-coded root. The paths moved four times in two days, and
everything that hard-coded a root broke silently. So we detect by MARKER: the
JOBHUNTER_RACINE variable if it is set, otherwise the first folder, going up from this
file, that contains a data folder and a profile folder; otherwise the same marker going
up from the current folder (package installed by pip, outside the user's folder).

TWO LAYOUTS, both readable (3.0). The English one — `data/`, `profile/profile.json`,
`My_CV/`, `Letters/`, `CV/By_offer`, `applications.json`… — and the French one of
2.x — `Scripts/`, `profil/profil.json`, `Mon_CV/`, `Lettres/`, `CV/Par_offre`,
`suivi.json`… `jobhunter migrate` turns the second into the first. The code names every
folder and file by its 2.x name; `nom()` gives the name on disk in this root's layout.
"""

import os
from pathlib import Path

# 2.x name -> 3.0 name. Folders at the root:
DOSSIERS = {"Scripts": "data", "profil": "profile", "Mon_CV": "My_CV", "Lettres": "Letters"}
# Folders inside CV/, Lettres/ and Scripts/:
SOUS_DOSSIERS = {
    "Par_offre": "By_offer",
    "Modèles": "Templates",
    "Sur_mesure": "Tailored",
    "Relances": "Follow_ups",
    "_sauvegardes": "_backups",
    "_preuves": "_proofs",
}
# Files, wherever they are:
FICHIERS = {
    "suivi.json": "applications.json",
    "profil.json": "profile.json",
    "Faits.json": "Facts.json",
    "exemple_finance_esg.json": "example_finance_esg.json",
    "exemple_Faits.json": "example_Facts.json",
    "LISEZ-MOI.txt": "README.txt",
    "comptes.json": "accounts.json",
    "comptes_sites.json": "site_accounts.json",
    "_audit_dispo.json": "_availability_audit.json",
    "_rendement.jsonl": "_source_yield.jsonl",
    "_linkedin_etat.json": "_linkedin_state.json",
    "_site_final.json": "_final_site.json",
    "_rejets_tri.json": "_sort_rejections.json",
    "offres_scan.json": "scanned_offers.json",
    "chemins.json": "paths.json",
    "_interface.json": "_settings.json",
}
NOMS = {**DOSSIERS, **SOUS_DOSSIERS, **FICHIERS}


def _a_des_donnees(d: Path, donnees: str, profil: str, fichier_profil: str) -> bool:
    return (d / donnees / "apply_queue.json").exists() or (d / profil / fichier_profil).exists()


def anglais(d: Path) -> bool:
    """True if the root `d` is in the English layout (3.0), False if in the French one.

    Decided by where the user's data IS, not by which folders exist: the first update
    to 3.0 adds `data/` and `profile/` (shipped files) next to a French layout that
    still holds everything. Without data on either side (a new installation), the
    English folders decide.
    """
    if _a_des_donnees(d, "data", "profile", "profile.json"):
        return True
    if _a_des_donnees(d, "Scripts", "profil", "profil.json"):
        return False
    # No data yet: a 2.x skeleton stays 2.x, anything else (an empty folder) is 3.0.
    vieux = (d / "Scripts").is_dir() and (d / "profil").is_dir()
    return not vieux or ((d / "data").is_dir() and (d / "profile").is_dir())


def _marque(d: Path) -> bool:
    return ((d / "data").is_dir() and (d / "profile").is_dir()) or (
        (d / "Scripts").is_dir() and (d / "profil").is_dir()
    )


def racine() -> Path:
    """The data folder: the one that contains `data/` and `profile/`.

    In the 2.x layout: `Scripts/` and `profil/`.

    Looks for `JOBHUNTER_RACINE`, then going up from this file, then from the current
    folder. Never a hard-coded root.

    Returns:
        The absolute path of the data folder.

    Raises:
        RuntimeError: no candidate folder contains them.
    """
    env = os.environ.get("JOBHUNTER_RACINE")
    if env:
        return Path(env).resolve()
    ici = Path.cwd().resolve()
    for d in [*Path(__file__).resolve().parents, ici, *ici.parents]:
        if _marque(d):
            return d
    raise RuntimeError(
        "Racine de JobHunter introuvable (aucun dossier parent avec data/ et profile/) : "
        "definir JOBHUNTER_RACINE."
    )


def nom(ancien: str, d: Path | None = None) -> str:
    """The name on disk of a folder or file that the code names by its 2.x name.

    `nom("suivi.json")` is "applications.json" in the English layout, "suivi.json" in
    the French one. A name that did not change comes back as is.
    """
    return NOMS.get(ancien, ancien) if anglais(d or racine()) else ancien


def dans(dossier: Path, ancien: str) -> Path:
    """`dossier / <name on disk>` of a file or folder named by its 2.x name.

    The layout is read from the folder itself when its name tells it (`Scripts` or
    `Lettres`: 2.x; `data` or `Letters`: 3.0), from the root otherwise. A program, or a
    test, that points a constant to another data folder gets the names of THAT folder.
    """
    if dossier.name in DOSSIERS:
        return dossier / ancien
    neuf = NOMS.get(ancien, ancien)
    if dossier.name in DOSSIERS.values():
        return dossier / neuf
    # A folder that does not say: what is there, otherwise the root's layout.
    if (dossier / ancien).exists() and not (dossier / neuf).exists():
        return dossier / ancien
    if (dossier / neuf).exists():
        return dossier / neuf
    return dossier / nom(ancien)


def dossier_cles() -> Path:
    """Where the API keys live (Adzuna, Jooble, France Travail, Gmail).

    The data folder of the MAIN profile, shared by every profile (jobhunter.profiles),
    never copied.
    """
    env = os.environ.get("JOBHUNTER_PRINCIPALE")
    if not env:
        return scripts()
    p = Path(env).resolve()
    return p / nom("Scripts", p)


def exporter_paquet() -> None:
    """Adds the folder that contains the `jobhunter` package to PYTHONPATH.

    Inherited by subprocesses: `python -m jobhunter.sources` works there without
    installation. The path comes from this file, never from a hard-coded root.
    """
    src = str(Path(__file__).resolve().parent.parent)
    deja = os.environ.get("PYTHONPATH", "")
    if src not in deja.split(os.pathsep):
        os.environ["PYTHONPATH"] = os.pathsep.join(p for p in (src, deja) if p)


def scripts() -> Path:
    """The working data folder (queue, descriptions, tracking): `data/`, or `Scripts/`."""
    r = racine()
    return r / nom("Scripts", r)


def dossier(ancien: str) -> Path:
    """A folder at the root, named by its 2.x name: `dossier("Mon_CV")` -> `<root>/My_CV`."""
    r = racine()
    return r / nom(ancien, r)
