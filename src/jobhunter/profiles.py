"""Several profiles, several searches: one workspace per profile.

A profile is a complete data folder — `data/` (its queue, its applications, its logs),
`profile/profile.json`, `My_CV/`, `CV/`, `Letters/` — so two searches never mix: two
queues, two trackings, two locks. The first profile is the installation's own folder
(the MAIN root, where nothing moves); the others live in `profiles/<slug>/` inside it.

The active profile is written in the main root's data folder (`_active_profile.json`)
and applied at start-up, BEFORE any module builds its paths (they are fixed at import):
`appliquer()` points `JOBHUNTER_RACINE` to the active workspace and remembers the main
root in `JOBHUNTER_PRINCIPALE`, which child processes inherit. Changing profile in the
application therefore restarts it.

Shared between profiles, never copied: the API keys (Adzuna, Jooble, France Travail,
Gmail) — `root.dossier_cles()` reads them from the main root's data folder — and
the browser profile, which is outside the data. The morning collection runs every
profile one after the other (`jobhunter pipeline`), each with its own root and log.

Decision: docs/adr/0013-one-workspace-per-profile.md
"""

import json
import os
import re
import shutil
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from jobhunter import root as _racine

DOSSIER = "profiles"
FICHIER_ACTIF = "_active_profile.json"
ENV_PRINCIPALE = "JOBHUNTER_PRINCIPALE"
# A profile's identifier: never changes, never a path. Its displayed name can change.
_SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")


@dataclass(frozen=True)
class Profil:
    """A profile: its slug ("" for the main one), its name, its data folder."""

    slug: str
    nom: str
    racine: Path


def principale() -> Path:
    """The installation's own data folder, whichever profile is active."""
    env = os.environ.get(ENV_PRINCIPALE)
    return Path(env).resolve() if env else _racine.racine()


def slug(nom: str) -> str:
    """'Chargée RSE (Lyon)' -> 'chargee-rse-lyon'."""
    s = unicodedata.normalize("NFKD", nom).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower())[:40].strip("-") or "profil"


def _nom_affiche(r: Path, defaut: str) -> str:
    """The name written in the workspace's profile (`_profil_nom`), otherwise `defaut`."""
    f = r / _racine.nom("profil", r) / _racine.nom("profil.json", r)
    try:
        return json.loads(f.read_text(encoding="utf-8")).get("_profil_nom") or defaut
    except (OSError, ValueError, AttributeError):
        return defaut


def liste(p: Path | None = None) -> list[Profil]:
    """The main profile, then the others in name order."""
    p = p or principale()
    profils = [Profil("", _nom_affiche(p, "Principal"), p)]
    dossier = p / DOSSIER
    if dossier.is_dir():
        for d in sorted(dossier.iterdir()):
            if d.is_dir() and (d / "profile" / "profile.json").exists():
                profils.append(Profil(d.name, _nom_affiche(d, d.name), d))
    return profils


def _fichier_actif(p: Path) -> Path:
    return _racine.dans(p / _racine.nom("Scripts", p), FICHIER_ACTIF)


def actif(p: Path | None = None) -> str:
    """The slug of the active profile ("" = the main one, or an active one that vanished)."""
    p = p or principale()
    try:
        s = json.loads(_fichier_actif(p).read_text(encoding="utf-8")).get("profil") or ""
    except (OSError, ValueError, AttributeError):
        return ""
    if not isinstance(s, str) or not _SLUG.fullmatch(s):
        return ""  # a hand-edited file never points outside profiles/
    return s if (p / DOSSIER / s / "profile" / "profile.json").exists() else ""


def activer(slug_: str, p: Path | None = None) -> None:
    """Makes `slug_` the active profile from the next start ("" = the main one).

    Raises:
        ValueError: `slug_` is not a slug (a path, "..", capitals…).
    """
    if slug_ and not _SLUG.fullmatch(slug_):
        raise ValueError(f"profil invalide : {slug_!r}")
    p = p or principale()
    f = _fichier_actif(p)
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps({"profil": slug_}), encoding="utf-8")


def racine_de(slug_: str, p: Path | None = None) -> Path:
    """The data folder of a profile ("" = the main one)."""
    p = p or principale()
    return p / DOSSIER / slug_ if slug_ else p


def appliquer() -> Path:
    """At start-up: the active profile's folder becomes the data root. Idempotent.

    Must run before any module of jobhunter that builds paths at import.
    """
    if os.environ.get(ENV_PRINCIPALE):
        return _racine.racine()
    try:
        p = _racine.racine()
    except RuntimeError:
        return Path.cwd()
    os.environ[ENV_PRINCIPALE] = str(p)
    s = actif(p)
    if s:
        os.environ["JOBHUNTER_RACINE"] = str(racine_de(s, p))
    return _racine.racine()


def creer(nom: str, p: Path | None = None) -> Path:
    """The workspace of a new profile, ready for `first_launch`. Returns its folder.

    The data folders are created in the 3.0 layout. The main profile's collection
    settings (company lists) and interface language are copied as a starting point;
    the keys are not copied, they are read from the main profile.

    Raises:
        FileExistsError: a profile of that name already exists.
    """
    p = p or principale()
    s = slug(nom)
    r = p / DOSSIER / s
    if r.exists():
        raise FileExistsError(r)
    for d in ("data", "profile", "My_CV", "CV", "Letters"):
        (r / d).mkdir(parents=True)
    donnees = p / _racine.nom("Scripts", p)
    for f in ("sources_config.json", "_interface.json"):
        src = _racine.dans(donnees, f)
        if src.is_file():
            shutil.copy2(src, r / "data" / _racine.NOMS.get(f, f))
    (r / "profile" / "_nom.txt").write_text(nom, encoding="utf-8")
    return r


def nommer(r: Path) -> None:
    """After `first_launch`: writes the name chosen at creation into the profile."""
    f = r / "profile" / "profile.json"
    n = r / "profile" / "_nom.txt"
    if not (f.exists() and n.exists()):
        return
    profil = json.loads(f.read_text(encoding="utf-8"))
    profil["_profil_nom"] = n.read_text(encoding="utf-8").strip()
    f.write_text(json.dumps(profil, ensure_ascii=False, indent=1), encoding="utf-8")
    n.unlink()
