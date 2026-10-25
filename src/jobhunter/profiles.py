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
# The displayed names, {slug: name} ("" = the main one), in the main data folder: a
# name changes without rewriting anybody's profile.json.
FICHIER_NOMS = "_profile_names.json"
# Archived profiles: moved here, never deleted.
ARCHIVES = "_archives"
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


def _fichier_noms(p: Path) -> Path:
    return _racine.dans(p / _racine.nom("Scripts", p), FICHIER_NOMS)


def _noms(p: Path) -> dict[str, str]:
    try:
        d = json.loads(_fichier_noms(p).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {str(k): str(v) for k, v in d.items()} if isinstance(d, dict) else {}


def _nom_affiche(p: Path, slug_: str, r: Path, defaut: str) -> str:
    """The registered name, else the one written in the profile (3.2), else `defaut`."""
    if nom := _noms(p).get(slug_):
        return nom
    f = r / _racine.nom("profil", r) / _racine.nom("profil.json", r)
    try:
        return json.loads(f.read_text(encoding="utf-8")).get("_profil_nom") or defaut
    except (OSError, ValueError, AttributeError):
        return defaut


def liste(p: Path | None = None) -> list[Profil]:
    """The main profile, then the others in name order."""
    p = p or principale()
    profils = [Profil("", _nom_affiche(p, "", p, "Principal"), p)]
    dossier = p / DOSSIER
    if dossier.is_dir():
        for d in sorted(dossier.iterdir()):
            if d.is_dir() and _SLUG.fullmatch(d.name) and (d / "profile" / "profile.json").exists():
                profils.append(Profil(d.name, _nom_affiche(p, d.name, d, d.name), d))
    return profils


def trouver(nom: str, p: Path | None = None) -> Profil | None:
    """A profile by its slug or its displayed name (case ignored)."""
    nom = nom.strip()
    for pr in liste(p):
        if nom in (pr.slug, pr.nom) or nom.casefold() == pr.nom.casefold() or slug(nom) == pr.slug:
            return pr
        # The main one is listed "(principal)": that word still finds it once renamed.
        if not pr.slug and nom.casefold() == "principal":
            return pr
    return None


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


def nommer(r: Path, p: Path | None = None) -> None:
    """After `first_launch`: registers the name chosen at creation."""
    n = r / "profile" / "_nom.txt"
    if not ((r / "profile" / "profile.json").exists() and n.exists()):
        return
    renommer(r.name, n.read_text(encoding="utf-8"), p)
    n.unlink()


def renommer(slug_: str, nom: str, p: Path | None = None) -> None:
    """Changes a profile's displayed name; its slug, and its folder, stay.

    Raises:
        ValueError: empty name, or no such profile.
    """
    p = p or principale()
    nom = " ".join(nom.split())[:60]
    if not nom:
        raise ValueError("nom vide")
    if slug_ and not (_SLUG.fullmatch(slug_) and (p / DOSSIER / slug_).is_dir()):
        raise ValueError(f"profil inconnu : {slug_!r}")
    noms = _noms(p)
    noms[slug_] = nom
    f = _fichier_noms(p)
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_name(f.name + ".tmp")
    tmp.write_text(json.dumps(noms, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, f)


def archiver(slug_: str, p: Path | None = None) -> Path:
    """Moves a profile to `profiles/_archives/` — nothing deleted. Returns its new folder.

    The main profile cannot be archived. If the archived profile was active, the main one
    becomes active. Its name is kept in the registry, under its archive folder's name.

    Raises:
        ValueError: the main profile, or no such profile.
        RuntimeError: its queue is in use (a collection is running for it).
    """
    import time

    from jobhunter.storage import lock as _verrou

    p = p or principale()
    if not slug_ or not _SLUG.fullmatch(slug_) or not (p / DOSSIER / slug_).is_dir():
        raise ValueError(f"profil archivable inconnu : {slug_!r}")
    r = p / DOSSIER / slug_
    file = r / "data" / "apply_queue.json"
    if (r / "data").is_dir():
        # Checked, not held: the lock file lives in the folder that moves.
        if not _verrou.prendre_verrou(file, attente=5, bavard=False):
            raise RuntimeError("file du profil occupée (collecte en cours)")
        _verrou.rendre_verrou(file)
    etait_actif = actif(p) == slug_
    dest = p / DOSSIER / ARCHIVES / f"{slug_}-{time.strftime('%Y%m%d-%H%M%S')}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(r), str(dest))
    noms = _noms(p)
    if slug_ in noms:
        noms[f"{ARCHIVES}/{dest.name}"] = noms.pop(slug_)
        _fichier_noms(p).write_text(
            json.dumps(noms, ensure_ascii=False, indent=1), encoding="utf-8"
        )
    if etait_actif:
        activer("", p)
    return dest
