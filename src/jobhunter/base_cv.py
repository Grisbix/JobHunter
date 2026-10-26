"""The profile's base CV: which files it uses, and replacing one by a new CV.

Shared by the desktop (a CV dropped on the window, app.cv_drop) and the web interface.
No window here: tests/test_cv_drop.py calls it directly.
"""

import json
import shutil
from pathlib import Path
from typing import Any

from jobhunter.storage import atomic as _atomique


def cvs_de_base(profil: dict[str, Any]) -> list[str]:
    """The base CV file names the profile uses (`domaines[].cv`), without duplicates."""
    noms: list[str] = []
    for d in profil.get("domaines") or []:
        n = (d or {}).get("cv") if isinstance(d, dict) else None
        if n and n not in noms:
            noms.append(n)
    return noms


def remplacer_cv_de_base(cv: Path, ancien: str, modeles: Path, fichier_profil: Path) -> str:
    """Puts `cv` in place of the base CV `ancien`. Returns the new file name.

    The new file keeps the old name, with the extension of the dropped file
    (`CV_camille.docx` replaced by a PDF becomes `CV_camille.pdf`). The old file is
    kept as `<name>.bak`; when the name changes, the profile's domains that used the
    old name point to the new one (`profile.json.bak` keeps the profile as it was).
    """
    modeles.mkdir(parents=True, exist_ok=True)
    neuf = Path(ancien).stem + cv.suffix.lower()
    for nom in {ancien, neuf}:
        if (modeles / nom).exists():
            shutil.copy2(modeles / nom, modeles / (nom + ".bak"))
    shutil.copyfile(cv, modeles / neuf)
    if neuf != ancien and fichier_profil.exists():
        profil = json.loads(fichier_profil.read_text(encoding="utf-8"))
        shutil.copyfile(fichier_profil, fichier_profil.with_name(fichier_profil.name + ".bak"))
        for d in profil.get("domaines") or []:
            if isinstance(d, dict) and d.get("cv") == ancien:
                d["cv"] = neuf
        _atomique.ecrire_json(fichier_profil, profil)
    return neuf
