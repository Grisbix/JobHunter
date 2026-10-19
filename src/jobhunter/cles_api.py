"""Les clés des API officielles de collecte : où chaque source les lit, et leur saisie.

Chaque source lit SON fichier dans `Scripts/` (ignoré par git) : France Travail
`francetravail.json`, Adzuna `adzuna.json`, Jooble `jooble.json`. Avant la 2.12, la
saisie de l'application écrivait France Travail dans `api_keys.json`, qu'aucune source
ne lit : la clé était perdue sans un mot. La saisie passe désormais par ce module, qui
écrit le fichier que la source lit vraiment.

Aucune valeur n'est affichée ni journalisée. `presente()` ne dit que si les champs
existent, sans les rendre.
"""

import json
from dataclasses import dataclass
from pathlib import Path

from jobhunter.stockage import verrou as _verrou
from jobhunter.stockage.atomique import ecrire_json

ATTENTE = 10  # secondes d'attente du verrou d'un fichier de cle


@dataclass(frozen=True)
class Cle:
    """La clé d'une source : son fichier, ses champs, et où l'obtenir."""

    nom: str
    libelle: str
    fichier: str
    champs: tuple[str, ...]
    secrets: tuple[str, ...]  # champs masqués à la saisie
    obtenir: str  # page officielle où créer la clé


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
    """Vrai si le fichier de la source contient tous ses champs, non vides."""
    cle = CLES[nom]
    try:
        c = _lire(dossier / cle.fichier)
    except (OSError, ValueError):
        return False
    return all(str(c.get(k) or "").strip() for k in cle.champs)


def enregistrer(dossier: Path, nom: str, valeurs: dict[str, str]) -> Path:
    """Écrit la clé d'une source dans le fichier qu'elle lit.

    Un champ laissé vide garde la valeur déjà enregistrée : on peut changer le seul
    secret sans retaper l'identifiant. Les autres options du fichier sont gardées.

    Args:
        dossier: le dossier `Scripts/`.
        nom: `francetravail`, `adzuna` ou `jooble`.
        valeurs: champ → valeur saisie.

    Returns:
        Le fichier écrit.

    Raises:
        KeyError: source inconnue.
        ValueError: un champ manque (ni saisi ni déjà présent), ou le fichier existant
            est illisible — il est alors laissé tel quel.
    """
    cle = CLES[nom]
    chemin = dossier / cle.fichier
    # Lire, compléter, écrire sous verrou : deux saisies simultanées (l'app et
    # `jobhunter acces --set-key`) gardaient sinon chacune l'ancien fichier, et la
    # seconde effaçait le champ changé par la première (audit Codex du 19/10).
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
