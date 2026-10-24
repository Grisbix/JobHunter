"""First launch: without a profile, offer to pick one's CV (no terminal needed).

Former start of JobHunter.pyw (phase 3.7). It ran at IMPORT of the .pyw; it is now a
function, called by the launcher BEFORE loading jobhunter.app (which reads the profile
as soon as it loads) -- hence this module outside the app package.
"""

import sys
import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Any

from jobhunter import frozen as _gele
from jobhunter import profile as _profil
from jobhunter import root as _rac

EXTENSIONS_CV = (".docx", ".pdf")


# ── Drag-and-drop (tkinterdnd2), shared with the application (app.cv_drop) ────
def chemins_deposes(tk_: Any, data: str) -> list[Path]:
    """The dropped files: Tk gives one string, braces around names with spaces."""
    return [Path(p) for p in tk_.splitlist(data)]


def choisir_cv(chemins: list[Path]) -> Path | None:
    """The first dropped file that is a CV (.docx or .pdf, present on disk)."""
    return next((p for p in chemins if p.suffix.lower() in EXTENSIONS_CV and p.is_file()), None)


def activer_depot(fenetre: Any, rappel: Callable[[list[Path]], None]) -> bool:
    """Makes a window accept dropped files. False without tkinterdnd2 (nothing changes).

    tkinterdnd2 ships the tkdnd extension for Windows, macOS and Linux.
    """
    try:
        from tkinterdnd2 import DND_FILES, TkinterDnD

        TkinterDnD._require(fenetre)
        # The window gains the methods of tkinterdnd2's mixin: a customtkinter CTk
        # cannot inherit from it at creation, its class is extended here.
        if not isinstance(fenetre, TkinterDnD.DnDWrapper):
            fenetre.__class__ = type(
                fenetre.__class__.__name__, (fenetre.__class__, TkinterDnD.DnDWrapper), {}
            )
        fenetre.drop_target_register(DND_FILES)

        def deposer(ev: Any) -> Any:
            rappel(chemins_deposes(fenetre.tk, ev.data))
            return ev.action

        fenetre.dnd_bind("<<Drop>>", deposer)
        return True
    except Exception:  # library missing, or this Tk cannot load tkdnd
        return False


def demander_cv(fenetre: tk.Tk) -> str:
    """The welcome window: drop the CV on it, or choose it. "" = later."""
    choix = {"cv": ""}
    fenetre.title("JobHunter — bienvenue")
    cadre = tk.Frame(fenetre, padx=28, pady=22)
    cadre.pack()
    tk.Label(
        cadre,
        text="Aucun profil pour l'instant.\n\nDonne ton CV (.docx de préférence, ou .pdf) : "
        "JobHunter le lit\net te pose quelques questions dans une fenêtre de commande.",
        justify="left",
    ).pack(anchor="w")
    zone = tk.Label(cadre, text="Dépose ton CV ici", relief="groove", padx=60, pady=34)
    zone.pack(fill="x", pady=14)

    def fin(p: str) -> None:
        choix["cv"] = p
        fenetre.quit()

    def choisir() -> None:
        dep = _rac.dossier("Mon_CV")
        p = filedialog.askopenfilename(
            parent=fenetre,
            title="Ton CV",
            initialdir=str(dep if dep.is_dir() else Path.home()),
            filetypes=[("CV", "*.docx *.pdf"), ("Word", "*.docx"), ("PDF", "*.pdf")],
        )
        if p:
            fin(p)

    def depot(chemins: list[Path]) -> None:
        cv = choisir_cv(chemins)
        if cv is None:
            zone.configure(text="Ce n'est pas un CV .docx ou .pdf : dépose-en un autre.")
        else:
            fin(str(cv))

    if not activer_depot(fenetre, depot):
        zone.configure(text="Choisis ton CV avec le bouton ci-dessous.")
    boutons = tk.Frame(cadre)
    boutons.pack(fill="x")
    tk.Button(boutons, text="Choisir mon CV…", command=choisir).pack(side="left")
    tk.Button(boutons, text="Plus tard", command=lambda: fin("")).pack(side="right")
    fenetre.protocol("WM_DELETE_WINDOW", lambda: fin(""))
    fenetre.deiconify()
    fenetre.mainloop()
    cadre.destroy()
    fenetre.withdraw()
    return choix["cv"]


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

        _r = tk.Tk()
        _r.withdraw()
        _cv = demander_cv(_r)
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
            f"Profil créé : {_profil.FICHIER.parent.name}/{_profil.FICHIER.name}.\n\n"
            "Ensuite, dans JobHunter :\n"
            "· « Ma recherche » : tes mots-clés, les intitulés gardés, tes villes ;\n"
            "· « Profil » : tes compétences ;\n"
            "· « Actualiser les offres » : la première collecte.\n\n"
            "Si tu as Claude Code (facultatif) : /configure-profile dans ce dossier "
            "complète tout, lettres comprises.",
        )
        _r.destroy()
