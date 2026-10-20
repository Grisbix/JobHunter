"""First launch: without a profile, offer to pick one's CV (no terminal needed).

Former start of JobHunter.pyw (phase 3.7). It ran at IMPORT of the .pyw; it is now a
function, called by the launcher BEFORE loading jobhunter.app (which reads the profile
as soon as it loads) -- hence this module outside the app package.
"""

import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

from jobhunter import frozen as _gele
from jobhunter import profile as _profil
from jobhunter import root as _rac


def _migrer_si_besoin() -> None:
    """A published installation still in the 2.x layout takes the 3.0 names, once.

    Here and not in the update: the update may be run from the OLD application, which
    keeps running (and writing to Scripts/) until it is restarted. At this point no
    other window of JobHunter is open on these files yet.
    """
    from jobhunter.programs import migrate as _migration

    r = _rac.racine()
    if not (_migration.automatique(r) and _migration.a_migrer(r)):
        return
    code = _migration.migrer(r, bavard=False)
    _r = tk.Tk()
    _r.withdraw()
    if code == 0:
        _profil.recharger(_profil.chemin_par_defaut())
        messagebox.showinfo(
            "JobHunter",
            "Tes dossiers ont pris leurs noms de la version 3 : data, profile, My_CV, "
            "Letters (CV/By_offer, CV/Templates…). Rien n'est perdu ; une sauvegarde "
            "_backup_migration_….zip est dans le dossier de JobHunter.",
        )
    elif code == 1:
        messagebox.showwarning(
            "JobHunter",
            "Le passage aux noms de dossiers de la version 3 n'a pas pu se faire : "
            "tout est resté comme avant et JobHunter marche comme d'habitude. "
            "Il sera retenté au prochain démarrage.",
        )
    _r.destroy()


def assurer_profil() -> None:
    """Guarantees a profile before opening the application.

    Without a profile, offers to pick one's CV, then runs the profile creation in a
    console (guided first launch); the application then starts normally.
    """
    _migrer_si_besoin()
    try:
        _profil.charger()
    except _profil.ProfilAbsent as _e:
        # GUIDED FIRST LAUNCH: pick one's CV here, without a terminal. The profile is
        # created in a console (first_launch asks its questions at the keyboard),
        # puis l'application demarre normalement.
        import subprocess
        from tkinter import filedialog

        _r = tk.Tk()
        _r.withdraw()
        _cv = ""
        if messagebox.askyesno(
            "JobHunter — bienvenue",
            "Aucun profil pour l'instant.\n\nChoisis ton CV (.docx de préférence, "
            "ou .pdf) : JobHunter le lit et te pose quelques questions dans une "
            "fenêtre de commande.\n\nChoisir mon CV maintenant ?",
        ):
            _dep = _rac.dossier("Mon_CV")
            _cv = filedialog.askopenfilename(
                title="Ton CV",
                initialdir=str(_dep if _dep.is_dir() else Path.home()),
                filetypes=[("CV", "*.docx *.pdf"), ("Word", "*.docx"), ("PDF", "*.pdf")],
            )
        if not _cv:
            messagebox.showinfo(
                "JobHunter",
                "Sans CV, pas de profil : relance JobHunter quand tu "
                "l'auras sous la main. (Voir README.fr.md)",
            )
            sys.exit(1)
        # pythonw has no console: first_launch needs python.exe (or
        # jobhunter-cli.exe in the installed application).
        _py = _gele.interpreteur()
        _racine = _rac.racine()
        _rac.exporter_paquet()
        subprocess.run(
            [str(_py), "-m", "jobhunter.programs.first_launch", _cv],
            cwd=str(_racine),
            creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0),
        )
        try:
            _profil.charger()
        except _profil.ProfilAbsent:
            messagebox.showerror(
                "JobHunter",
                "Le profil n'a pas été créé. Relance JobHunter, ou voir README.fr.md, section Dépannage.",
            )
            sys.exit(1)
        messagebox.showinfo(
            "JobHunter",
            "Profil créé : profil/profil.json.\n\nPour le compléter "
            "(compétences, recherches, lettres), ouvre Claude Code dans ce "
            "dossier et tape /configure-profile.",
        )
        _r.destroy()
