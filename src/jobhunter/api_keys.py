"""The keys of the official collection APIs: where each source reads them, and their entry.

Each source reads ITS file in `Scripts/` (ignored by git): France Travail
`francetravail.json`, Adzuna `adzuna.json`, Jooble `jooble.json`. Before 2.12, the
application's entry wrote France Travail into `api_keys.json`, which no source reads:
the key was lost without a word. The entry now goes through this module, which writes
the file the source really reads.

No value is displayed or logged. `presente()` only says whether the fields exist,
without returning them.
"""

import json
from dataclasses import dataclass
from pathlib import Path

from jobhunter.storage import lock as _verrou
from jobhunter.storage.atomic import ecrire_json

ATTENTE = 10  # seconds of waiting for the lock of a key file


@dataclass(frozen=True)
class Cle:
    """A source's key: its file, its fields, and where to get it."""

    nom: str
    libelle: str
    fichier: str
    champs: tuple[str, ...]
    secrets: tuple[str, ...]  # fields masked during entry
    obtenir: str  # official page where the key is created


CLES = {
    c.nom: c
    for c in (
        Cle(
            "francetravail",
            "France Travail",
            "francetravail.json",
            ("client_id", "client_secret"),
            ("client_secret",),
            "https://francetravail.io",
        ),
        Cle(
            "adzuna",
            "Adzuna",
            "adzuna.json",
            ("app_id", "app_key"),
            ("app_key",),
            "https://developer.adzuna.com",
        ),
        Cle("jooble", "Jooble", "jooble.json", ("key",), ("key",), "https://jooble.org/api/about"),
        Cle(
            "usajobs",
            "USAJOBS",
            "usajobs.json",
            ("email", "key"),
            ("key",),
            "https://developer.usajobs.gov/apirequest/",
        ),
    )
}


def _lire(chemin: Path) -> dict[str, object]:
    if not chemin.exists():
        return {}
    ancien = json.loads(chemin.read_text(encoding="utf-8"))
    if not isinstance(ancien, dict):
        raise ValueError(f"{chemin.name} : contenu inattendu ; fichier conservé.")
    return ancien


def presente(dossier: Path, nom: str) -> bool:
    """True if the source's file contains all its fields, not empty."""
    cle = CLES[nom]
    try:
        c = _lire(dossier / cle.fichier)
    except (OSError, ValueError):
        return False
    return all(str(c.get(k) or "").strip() for k in cle.champs)


def enregistrer(dossier: Path, nom: str, valeurs: dict[str, str]) -> Path:
    """Writes a source's key into the file it reads.

    A field left empty keeps the value already stored: one can change the secret
    alone without retyping the identifier. The file's other options are kept.

    Args:
        dossier: the `Scripts/` folder.
        nom: `francetravail`, `adzuna` or `jooble`.
        valeurs: field → value entered.

    Returns:
        The file written.

    Raises:
        KeyError: unknown source.
        ValueError: a field is missing (neither entered nor already present), or the
            existing file is unreadable — it is then left as is.
    """
    cle = CLES[nom]
    chemin = dossier / cle.fichier
    # Read, complete, write under lock: two simultaneous entries (the app and
    # `jobhunter acces --set-key`) otherwise each kept the old file, and the
    # second erased the field changed by the first (Codex audit of 19/10).
    a_nous = not _verrou.tenu(chemin)
    if not _verrou.prendre_verrou(chemin, attente=ATTENTE, bavard=False):
        raise ValueError(f"{chemin.name} est en cours d'écriture ; réessaie dans un instant.")
    try:
        try:
            ancien = _lire(chemin)
        except json.JSONDecodeError as e:
            raise ValueError(f"{chemin.name} illisible ; fichier conservé.") from e
        for k in cle.champs:
            v = str(valeurs.get(k) or "").strip()
            if v:
                ancien[k] = v
        manquants = [k for k in cle.champs if not str(ancien.get(k) or "").strip()]
        if manquants:
            raise ValueError(f"Champ(s) obligatoire(s) : {', '.join(manquants)}.")
        ecrire_json(chemin, ancien)
    finally:
        if a_nous:
            _verrou.rendre_verrou(chemin)
    return chemin
