"""A new download finds the data of the previous one.

Installed from source, JobHunter keeps its data in its own folder (data/, profile/,
My_CV/…). Downloading it again from GitHub and unzipping it elsewhere gave an empty
folder: the welcome asked for the CV again, as on a first day (the user, 2026-10-28,
on another computer). Before the CV, the welcome now offers the data of the previous
folder, found here: they are COPIED, the previous folder does not change.

The installer (JobHunterSetup.exe) keeps its data in Documents/JobHunter, which its
updates never touch: also a candidate, for someone moving from it to the source.
"""

import shutil
from pathlib import Path

# What is the user's, in both layouts (jobhunter.root): never the code.
DONNEES = (
    "data",
    "profile",
    "profiles",
    "My_CV",
    "CV",
    "Letters",
    "Scripts",
    "profil",
    "Mon_CV",
    "Lettres",
)
# Rebuilt by themselves, and heavy: the daily backups (seven days of the queue), the logs.
_SANS = shutil.ignore_patterns("~$*", "_backups", "_sauvegardes", "_logs")


def profil_de(d: Path) -> Path | None:
    """The profile file of the data folder `d`, in either layout; None without one."""
    for f in (d / "profile" / "profile.json", d / "profil" / "profil.json"):
        if f.is_file():
            return f
    return None


def _lieux() -> list[Path]:
    home = Path.home()
    return [home / "Documents", home / "Downloads", home / "Desktop", home]


def candidats(ici: Path, lieux: list[Path] | None = None) -> list[Path]:
    """The other JobHunter folders that hold a profile, the most recent first.

    Looked for beside `ici` and in Documents, Downloads, Desktop and the home folder:
    any folder whose name starts with "JobHunter" (JobHunter-main, JobHunter-3.58.0…),
    and the same name one level down (Windows' "Extract all" makes
    JobHunter-main/JobHunter-main).
    """
    ici = ici.resolve()
    vus: set[Path] = set()
    sortie: list[Path] = []
    for lieu in [ici.parent, *(_lieux() if lieux is None else lieux)]:
        try:
            dossiers = [d for d in lieu.iterdir() if d.name.lower().startswith("jobhunter")]
        except OSError:
            continue
        for d in dossiers:
            for c in (d, d / d.name):
                try:
                    r = c.resolve()
                except OSError:
                    continue
                if r == ici or r in vus or not r.is_dir() or profil_de(r) is None:
                    continue
                vus.add(r)
                sortie.append(r)
    return sorted(sortie, key=lambda d: _date(d), reverse=True)


def _date(d: Path) -> float:
    f = profil_de(d)
    try:
        return f.stat().st_mtime if f else 0.0
    except OSError:
        return 0.0


def reprendre(source: Path, dest: Path) -> list[str]:
    """Copies the user's folders of `source` into `dest`; returns their names.

    A file of `dest` with the same name is replaced (the new download's empty
    skeleton); `source` is only read.
    """
    copies = []
    for nom in DONNEES:
        s = source / nom
        if s.is_dir():
            shutil.copytree(s, dest / nom, dirs_exist_ok=True, ignore=_SANS)
            copies.append(nom)
    return copies
