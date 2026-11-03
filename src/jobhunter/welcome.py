"""First launch: what happens before a profile exists, without any window of its own.

The web window shows the welcome when there is no profile (jobhunter.web.onboarding,
3.78): the data of a previous JobHunter folder to take back, or the CV, read here
(jobhunter.cv_text), then a form prefilled from it (first_launch.propositions). The
profile is written by first_launch, given every answer as an option, in a process
without a console, and a failure says why in the window.

Until 3.77 these steps were customtkinter windows opened by the launcher before the
web window (and a tour of three more windows after it): two looks, two toolkits, and
the only reason customtkinter and tkinterdnd2 were still dependencies.
"""

import os
import sys
from pathlib import Path
from typing import Any

from jobhunter import frozen as _gele
from jobhunter import profile as _profil
from jobhunter import root as _rac

EXTENSIONS_CV = (".docx", ".pdf")
PEU_DE_TEXTE = 200  # below, first_launch writes nothing unless the jobs are given
ICONE = Path(__file__).parent / "assets" / "jobhunter.ico"


def choisir_cv(chemins: list[Path]) -> Path | None:
    """The first file that is a CV (.docx or .pdf, present on disk)."""
    return next((p for p in chemins if p.suffix.lower() in EXTENSIONS_CV and p.is_file()), None)


def migrer_si_besoin() -> str:
    """A published installation still in the 2.x layout takes the 3.0 names, once.

    Here and not in the update: the update may be run from the OLD application, which
    keeps running (and writing to Scripts/) until it is restarted. The launcher calls
    it before the window, when no other process of JobHunter has these files open.
    Returns the sentence to show ("" when nothing was to do).
    """
    from jobhunter.programs import migrate as _migration

    r = _rac.racine()
    if not (_migration.automatique(r) and _migration.a_migrer(r)):
        return ""
    code = _migration.migrer(r, bavard=False)
    if code == 0:
        _profil.recharger(_profil.chemin_par_defaut())
        return (
            "Tes dossiers ont pris leurs noms de la version 3 : data, profile, My_CV, "
            "Letters (CV/By_offer, CV/Templates…). Rien n'est perdu ; une sauvegarde "
            "_backup_migration_….zip est dans le dossier de JobHunter."
        )
    if code == 1:
        return (
            "!Le passage aux noms de dossiers de la version 3 n'a pas pu se faire : "
            "tout est resté comme avant et JobHunter marche comme d'habitude. "
            "Il sera retenté au prochain démarrage."
        )
    return ""


def reprendre(source: Path) -> str:
    """Copies a previous folder's data here (previous_data). "" once its profile reads.

    Otherwise the reason, to show; the previous folder never changes.
    """
    from jobhunter import previous_data

    try:
        previous_data.reprendre(source, _rac.racine())
    except OSError as e:
        return f"Copie impossible depuis {source} : {e}"
    migrer_si_besoin()  # a 2.x folder takes the 3.0 names
    try:
        _profil.recharger(_profil.chemin_par_defaut())
        _profil.charger()
    except _profil.ProfilAbsent:
        return f"Aucun profil lisible dans {source}."
    return ""


def arguments_profil(cv: str, rep: dict[str, Any]) -> list[str]:
    """first_launch's command-line answers for the form's answers `rep`."""
    args = [cv, "--auto"]
    for champ in ("prenom", "nom", "email", "telephone", "ville", "metiers"):
        args += [f"--{champ}", str(rep.get(champ) or "").strip()]
    args += ["--annees", str(int(rep.get("annees") or 0))]
    args += ["--genre", "f" if rep.get("genre") == "f" else "m"]
    # The sectors ticked, then the cities typed.
    villes = [v.strip() for v in str(rep.get("villes") or "").split(",") if v.strip()]
    prio = [*(rep.get("prioritaires") or []), *villes]
    if prio:
        args += ["--prioritaires", ",".join(dict.fromkeys(prio))]
    args += ["--etranger", "o" if rep.get("etranger") else "n"]
    if rep.get("etranger") and str(rep.get("pays_etrangers") or "").strip():
        args += ["--pays-etrangers", str(rep["pays_etrangers"]).strip()]
    args += ["--secondaires", ",".join(rep.get("secondaires") or [])]
    args += ["--entreprises", "o" if rep.get("entreprises") else "n"]
    args += ["--word", "o" if rep.get("word") else "n"]
    if str(rep.get("parcours") or "").strip():
        args += ["--parcours", str(rep["parcours"]).strip()]
    return args


def ouvrir(chemin: Path) -> None:
    """Opens a file in its usual application (Word, LibreOffice…)."""
    if sys.platform == "win32":
        os.startfile(chemin)  # type: ignore[attr-defined,unused-ignore]  # Windows only
    else:
        import subprocess

        subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", str(chemin)])  # nosec B603


def creer_profil(cv: str, rep: dict[str, Any]) -> tuple[bool, str]:
    """Runs first_launch with the answers, without a console. (created?, its output)."""
    import subprocess

    # pythonw has no standard output: python.exe, or jobhunter-cli.exe once installed.
    _rac.exporter_paquet()
    commande = [str(_gele.interpreteur()), "-m", "jobhunter.programs.first_launch"]
    try:
        r = subprocess.run(  # nosec B603 : our own program, arguments from our form
            commande + arguments_profil(cv, rep),
            cwd=str(_rac.racine()),
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=600,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        sortie = (r.stdout or "") + (r.stderr or "")
    except (OSError, subprocess.TimeoutExpired) as e:
        return False, f"{type(e).__name__} : {e}"
    try:
        _profil.recharger(_profil.chemin_par_defaut())
        _profil.charger()
    except _profil.ProfilAbsent:
        return False, sortie
    return True, sortie


def a_un_profil() -> bool:
    """True when the data folder has a readable profile."""
    try:
        _profil.charger()
    except _profil.ProfilAbsent:
        return False
    return True
