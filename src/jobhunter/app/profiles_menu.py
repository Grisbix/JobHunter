"""Several profiles in the application: switch, create from a CV, restart on the chosen one.

A profile is a workspace of its own (jobhunter.profiles): its queue, its applications,
its CVs and letters. The paths are fixed when the modules load, so changing profile
restarts the application on the new one. Creating a profile runs the usual guided first
launch (jobhunter.welcome: the questions in a window) inside the new workspace.
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
from jobhunter.app.theme import TX

if TYPE_CHECKING:
    from jobhunter.app._app_type import AppTypee


def nom_affiche(p: _profils.Profil) -> str:
    """The name shown for a profile ("Principal" translated for the main one)."""
    return _t(p.nom) if not p.slug and p.nom == "Principal" else p.nom


def nom_actif() -> str:
    """The active profile's name, even when it is the only one ("" if unreadable)."""
    try:
        profils = _profils.liste()
    except RuntimeError:
        return ""
    s = _profils.actif()
    return next((nom_affiche(p) for p in profils if p.slug == s), "")


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
        ligne,
        text=_t("Annuler"),
        fg_color="transparent",
        border_width=1,
        text_color=TX,
        command=lambda: fin(None),
    ).pack(side="left", padx=4)
    f.protocol("WM_DELETE_WINDOW", lambda: fin(None))
    f.after(50, f.grab_set)
    parent.wait_window(f)
    return choix["i"]


# The drop-down list at the top left: the profiles, then two actions.
_NOUVEAU = "Nouveau profil…"
_GERER = "Gérer les profils…"


class ProfilsMixin:
    """The Profiles menu and the creation of a profile."""

    def _maj_menu_profils(self: "AppTypee") -> None:
        """Fills the top-left list from the profiles on disk; shows the open one.

        The open one is the profile this window runs on: after "no" to the restart,
        the list still names it, not the one chosen for the next start.
        """
        w = getattr(self, "_nom_profil_lbl", None)
        if w is None:
            return
        try:
            profils = _profils.liste()
        except RuntimeError:
            profils = []
        ouvert = getattr(self, "_profil_ouvert", None)
        if ouvert is None:
            ouvert = self._profil_ouvert = _profils.actif()
        self._profils_par_nom = {
            ("● " if p.slug == ouvert else "○ ") + nom_affiche(p): p.slug for p in profils
        }
        valeurs = [*self._profils_par_nom, _t(_NOUVEAU), _t(_GERER)]
        w.configure(values=valeurs)
        courant = next((n for n, s in self._profils_par_nom.items() if s == ouvert), "")
        w.set(courant or "● " + _t("Principal"))

    def _choix_profil(self: "AppTypee", valeur: str) -> None:
        """A choice in the top-left list: open that profile, or one of the two actions."""
        self._maj_menu_profils()  # back to the open profile until a restart says otherwise
        if valeur == _t(_NOUVEAU):
            self._nouveau_profil()
        elif valeur == _t(_GERER):
            self._profil_panel("Profils")
            self._nav_actif("profil")
        elif (s := self._profils_par_nom.get(valeur)) is not None:
            self._changer_profil(s)

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
        actif = next((p for p in _profils.liste() if p.slug == _profils.actif()), None)
        if actif is not None:
            nom = nom_affiche(actif)
            menu.add_command(
                label=_t("Renommer « {nom} »…").format(nom=nom), command=self._renommer_profil
            )
            if actif.slug:  # the main profile is the installation's folder
                menu.add_command(
                    label=_t("Archiver « {nom} »…").format(nom=nom),
                    command=self._archiver_profil,
                )
        x, y = self.root.winfo_pointerxy()
        try:
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()

    def _renommer_profil(self: "AppTypee") -> None:
        """A new displayed name for the active profile (its folder does not move)."""
        s = _profils.actif()
        nom = ctk.CTkInputDialog(text=_t("Nouveau nom du profil"), title="JobHunter").get_input()
        if not nom or not nom.strip():
            return
        _profils.renommer(s, nom)
        self._log(_t("Profil renommé : {nom}").format(nom=" ".join(nom.split())) + "\n")
        self._maj_menu_profils()

    def _archiver_profil(self: "AppTypee") -> None:
        """Moves the active profile to profiles/_archives/ (nothing deleted), back to main."""
        s = _profils.actif()
        if not s or not messagebox.askyesno(
            "JobHunter",
            _t(
                "Archiver ce profil ? Son dossier est rangé dans profiles/_archives (rien "
                "n'est supprimé) et JobHunter redémarre sur le profil principal."
            ),
            parent=self.root,
        ):
            return
        try:
            _profils.archiver(s)
        except RuntimeError:
            messagebox.showwarning(
                "JobHunter",
                _t("Une collecte tourne pour ce profil : réessaie quand elle aura fini."),
                parent=self.root,
            )
            return
        self._relancer()

    def _changer_profil(self: "AppTypee", slug: str) -> None:
        """Opens another profile at once: the window restarts on its data.

        The paths are fixed at start-up, so a new process is the only way every panel
        reads the new profile's folder. Refused while a task runs: it writes the open
        profile's queue, and its output would be cut.
        """
        if slug == getattr(self, "_profil_ouvert", _profils.actif()):
            return
        if getattr(self, "proc", None) and self.proc.poll() is None:
            messagebox.showinfo(
                "JobHunter",
                _t(
                    "Une tâche tourne sur ce profil : attends qu'elle finisse (ou « Arrêter »), "
                    "puis change de profil."
                ),
                parent=self.root,
            )
            return
        _profils.activer(slug)
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
            cmd = [sys.executable, "-m", "jobhunter.launch"]
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
            "Nouveau profil « {nom} » : vérifie et complète ce que JobHunter a lu dans le CV."
        )
        self._log(consigne.format(nom=nom.strip()) + "\n")
        env = {
            **os.environ,
            "JOBHUNTER_RACINE": str(racine),
            _profils.ENV_PRINCIPALE: str(_profils.principale()),
        }

        def tache() -> None:
            subprocess.run(  # nosec B603 : our own program, arguments built here
                [PY, "-m", "jobhunter.welcome", str(cv)],
                cwd=str(racine),
                env=env,
                # Its own windows; no console (PY is a console program).
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
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
        self._maj_menu_profils()  # the new profile appears in the top-left list
        if messagebox.askyesno(
            "JobHunter",
            _t("Profil créé. L'ouvrir maintenant ? (JobHunter redémarre)"),
            parent=self.root,
        ):
            _profils.activer(racine.name)
            self._relancer()
