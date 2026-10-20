"""Several profiles in the application: switch, create from a CV, restart on the chosen one.

A profile is a workspace of its own (jobhunter.profiles): its queue, its applications,
its CVs and letters. The paths are fixed when the modules load, so changing profile
restarts the application on the new one. Creating a profile runs the usual guided first
launch (questions in a console) inside the new workspace.
"""

import functools
import os
import shutil
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import TYPE_CHECKING

import customtkinter as ctk

from jobhunter import frozen as _gele
from jobhunter import profiles as _profils
from jobhunter.app.common import PY
from jobhunter.app.language import t as _t

if TYPE_CHECKING:
    from jobhunter.app._app_type import AppTypee


def nom_affiche(p: _profils.Profil) -> str:
    """The name shown for a profile ("Principal" translated for the main one)."""
    return _t(p.nom) if not p.slug and p.nom == "Principal" else p.nom


def profil_affiche() -> str:
    """The active profile's name for the sidebar, "" while there is only one profile."""
    try:
        profils = _profils.liste()
    except RuntimeError:
        return ""
    if len(profils) < 2:
        return ""
    s = _profils.actif()
    return next((nom_affiche(p) for p in profils if p.slug == s), "")


def choisir(parent: tk.Misc, titre: str, texte: str, boutons: list[str]) -> int | None:
    """A small modal window with one button per choice. The index chosen, or None."""
    choix: dict[str, int | None] = {"i": None}
    f = ctk.CTkToplevel(parent)
    f.title(titre)
    f.transient(parent)
    ctk.CTkLabel(f, text=texte, justify="left", wraplength=420).pack(padx=22, pady=(18, 12))
    ligne = ctk.CTkFrame(f, fg_color="transparent")
    ligne.pack(padx=18, pady=(0, 16))

    def fin(i: int | None) -> None:
        choix["i"] = i
        f.destroy()

    for i, b in enumerate(boutons):
        ctk.CTkButton(ligne, text=b, command=functools.partial(fin, i)).pack(side="left", padx=4)
    ctk.CTkButton(
        ligne, text=_t("Annuler"), fg_color="transparent", border_width=1, command=lambda: fin(None)
    ).pack(side="left", padx=4)
    f.protocol("WM_DELETE_WINDOW", lambda: fin(None))
    f.after(50, f.grab_set)
    parent.wait_window(f)
    return choix["i"]


class ProfilsMixin:
    """The Profiles menu and the creation of a profile."""

    def _menu_profils(self: "AppTypee") -> None:
        """Menu of the profiles (the active one ticked), then "Nouveau profil…"."""
        menu = tk.Menu(self.root, tearoff=0)
        self._profil_var = tk.StringVar(self.root, _profils.actif())
        for p in _profils.liste():
            menu.add_radiobutton(
                label=nom_affiche(p),
                value=p.slug,
                variable=self._profil_var,
                command=functools.partial(self._changer_profil, p.slug),
            )
        menu.add_separator()
        menu.add_command(label=_t("Nouveau profil…"), command=self._nouveau_profil)
        x, y = self.root.winfo_pointerxy()
        try:
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()

    def _changer_profil(self: "AppTypee", slug: str) -> None:
        if slug == _profils.actif():
            return
        _profils.activer(slug)
        if messagebox.askyesno(
            "JobHunter",
            _t("Profil changé : JobHunter doit redémarrer pour l'ouvrir. Redémarrer maintenant ?"),
            parent=self.root,
        ):
            self._relancer()

    def _relancer(self: "AppTypee") -> None:
        """Starts JobHunter again on the active profile, then closes this window."""
        principale = _profils.principale()
        env = {k: v for k, v in os.environ.items() if k != _profils.ENV_PRINCIPALE}
        env["JOBHUNTER_RACINE"] = str(principale)
        if _gele.est_gele():
            cmd = [sys.executable]
        elif (principale / "JobHunter.pyw").exists():
            cmd = [sys.executable, str(principale / "JobHunter.pyw")]
        else:
            cmd = [sys.executable, "-m", "jobhunter.app"]
        subprocess.Popen(cmd, cwd=str(principale), env=env)  # nosec B603 : our own program
        self.root.destroy()

    def _nouveau_profil(self: "AppTypee", cv: Path | None = None) -> None:
        """A new profile from a CV: its workspace, then the guided first launch in it."""
        if cv is None:
            p = filedialog.askopenfilename(
                parent=self.root,
                title=_t("Le CV du nouveau profil"),
                filetypes=[("CV", "*.docx *.pdf"), ("Word", "*.docx"), ("PDF", "*.pdf")],
            )
            if not p:
                return
            cv = Path(p)
        nom = ctk.CTkInputDialog(
            text=_t("Nom du nouveau profil (par exemple : Chargée RSE à Lyon)"), title="JobHunter"
        ).get_input()
        if not nom or not nom.strip():
            return
        try:
            racine = _profils.creer(nom.strip())
        except FileExistsError:
            messagebox.showerror(
                "JobHunter", _t("Un profil de ce nom existe déjà."), parent=self.root
            )
            return
        consigne = _t(
            "Nouveau profil « {nom} » : réponds aux questions dans la fenêtre de commande."
        )
        self._log(consigne.format(nom=nom.strip()) + "\n")
        env = {
            **os.environ,
            "JOBHUNTER_RACINE": str(racine),
            _profils.ENV_PRINCIPALE: str(_profils.principale()),
        }

        def tache() -> None:
            subprocess.run(  # nosec B603 : our own program, arguments built here
                [PY, "-m", "jobhunter.programs.first_launch", str(cv)],
                cwd=str(racine),
                env=env,
                creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0),
            )
            self.root.after(0, functools.partial(self._profil_cree, racine))

        threading.Thread(target=tache, daemon=True).start()

    def _profil_cree(self: "AppTypee", racine: Path) -> None:
        if not (racine / "profile" / "profile.json").exists():
            # The questions were not answered: the empty workspace goes away.
            shutil.rmtree(racine, ignore_errors=True)
            messagebox.showwarning(
                "JobHunter",
                _t("Le profil n'a pas été créé (les questions n'ont pas été terminées)."),
                parent=self.root,
            )
            return
        _profils.nommer(racine)
        if messagebox.askyesno(
            "JobHunter",
            _t("Profil créé. L'ouvrir maintenant ? (JobHunter redémarre)"),
            parent=self.root,
        ):
            _profils.activer(racine.name)
            self._relancer()
