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


def assurer_profil() -> None:
    """Guarantees a profile before opening the application.

    Without a profile, offers to pick one's CV, then runs the profile creation in a
    console (guided first launch); the application then starts normally.
    """
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
            _dep = _rac.racine() / "Mon_CV"
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
