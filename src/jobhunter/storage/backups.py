"""The daily backups (data/_backups/<date>/), gzip-compressed.

Seven days of plain JSON weighed 416 MB in a real data folder (60 MB a day, the
postings' text for three quarters); gzip brings a day to 16 MB, in half a second
(the user, 2026-10-28: « ce qui est trop lourd »). A file is written as
`<name>.gz`; every reader goes through `fichier` / `lire_texte` / `en_clair`, which
also take the plain files of the backups made before 3.61.

    ecrire(src, dossier)        copies `src` into `dossier`, compressed
    fichier(dossier, nom)       the backup file of `nom`, compressed or not; None
    lire_texte(chemin)          its text, compressed or not
    en_clair(chemin)            a plain path to give to a reader that wants one
    compresser(dossier)         compresses the plain JSON files left in `dossier`
"""

import contextlib
import gzip
import os
import shutil
import tempfile
from collections.abc import Iterator
from pathlib import Path

SUFFIXE = ".gz"


def ecrire(src: Path, dossier: Path) -> Path:
    """`dossier/<src name>.gz`, written atomically; the modification time is kept."""
    dest = dossier / (src.name + SUFFIXE)
    tmp = dest.with_name(dest.name + ".tmp")
    with src.open("rb") as entree, gzip.open(tmp, "wb", compresslevel=6) as sortie:
        shutil.copyfileobj(entree, sortie, 1 << 20)
    st = src.stat()
    os.utime(tmp, (st.st_atime, st.st_mtime))
    os.replace(tmp, dest)
    return dest


def fichier(dossier: Path, nom: str) -> Path | None:
    """The backup of `nom` in `dossier`: `nom.gz`, else `nom` (before 3.61); None."""
    for p in (dossier / (nom + SUFFIXE), dossier / nom):
        if p.is_file():
            return p
    return None


def lire_texte(chemin: Path) -> str:
    """The text of a backup file, compressed or not."""
    if chemin.suffix == SUFFIXE:
        with gzip.open(chemin, "rt", encoding="utf-8") as f:
            return f.read()
    return chemin.read_text(encoding="utf-8")


@contextlib.contextmanager
def en_clair(chemin: Path) -> Iterator[Path]:
    """A plain copy of a compressed backup, for a reader that takes a path; removed after."""
    if chemin.suffix != SUFFIXE:
        yield chemin
        return
    with tempfile.TemporaryDirectory(prefix="jobhunter_sauvegarde_") as d:
        clair = Path(d) / chemin.stem
        with gzip.open(chemin, "rb") as entree, clair.open("wb") as sortie:
            shutil.copyfileobj(entree, sortie, 1 << 20)
        yield clair


def compresser(dossier: Path) -> int:
    """Compresses the plain .json files of a backup folder (made before 3.61).

    The plain file is removed only once its .gz is written and reads back the same
    length. Returns how many were compressed.
    """
    n = 0
    for p in sorted(dossier.glob("*.json")):
        try:
            gz = ecrire(p, dossier)
            with gzip.open(gz, "rb") as f:
                taille = sum(len(b) for b in iter(lambda: f.read(1 << 20), b""))
            if taille != p.stat().st_size:
                gz.unlink()
                continue
            p.unlink()
            n += 1
        except OSError:
            continue
    return n
