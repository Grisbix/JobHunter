"""Premier lancement : sans profil, proposer de choisir son CV (aucun terminal requis).

Ancien debut de JobHunter.pyw (phase 3.7). S'executait a l'IMPORT du .pyw ; c'est
maintenant une fonction, appelee par le lanceur AVANT de charger jobhunter.app (qui lit
le profil des son chargement) -- d'ou ce module hors du paquet app.
"""

import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

from jobhunter import profil as _profil
from jobhunter import racine as _rac


def assurer_profil() -> None:
    """Garantit un profil avant d'ouvrir l'application.

    Sans profil, propose de choisir son CV, puis lance la création du profil dans une
    console (premier lancement guidé) ; l'application démarre ensuite normalement.
    """
    try:
        _profil.charger()
    except _profil.ProfilAbsent as _e:
        # PREMIER LANCEMENT GUIDE : choisir son CV ici, sans terminal. Le profil se
        # cree dans une console (premier_lancement pose ses questions au clavier),
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
                "l'auras sous la main. (Voir README.md)",
            )
            sys.exit(1)
        # pythonw n'a pas de console : premier_lancement a besoin de python.exe.
        _py = Path(sys.executable)
        _py = _py.with_name("python.exe") if _py.name.lower() == "pythonw.exe" else _py
        _racine = _rac.racine()
        _rac.exporter_paquet()
        subprocess.run(
            [str(_py), "-m", "jobhunter.programmes.premier_lancement", _cv],
            cwd=str(_racine),
            creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0),
        )
        try:
            _profil.charger()
        except _profil.ProfilAbsent:
            messagebox.showerror(
                "JobHunter",
                "Le profil n'a pas été créé. Lance lancer.bat ou voir README.md, section Dépannage.",
            )
            sys.exit(1)
        messagebox.showinfo(
            "JobHunter",
            "Profil créé : profil/profil.json.\n\nPour le compléter "
            "(compétences, recherches, lettres), ouvre Claude Code dans ce "
            "dossier et tape /configurer-profil.",
        )
        _r.destroy()
