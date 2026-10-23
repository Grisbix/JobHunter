"""The "Paramètres" panel: the interface language, the version and the update, the daily collection.

The language was chosen in a menu hidden under Maintenance ("Langue / Language…"), and
applied at the next start. Here it is one row of buttons, each language under its own
name; choosing one saves it for every profile (app.language) and restarts the window in
it at once — refused while a task runs, so as not to cut it.
"""

from importlib import metadata
from tkinter import messagebox
from typing import TYPE_CHECKING, Any

import customtkinter as ctk

from jobhunter.app import language as _langue
from jobhunter.app import theme as _theme
from jobhunter.app.language import t as _t
from jobhunter.app.theme import ACC, ACC_H, BTN, BTN_H, CARD, CB, CF, CL, MUT, TX, WORK

if TYPE_CHECKING:
    from jobhunter.app._app_type import AppTypee


def version() -> str:
    """The running version: the VERSION file of a source install, else the package's."""
    try:
        from jobhunter.programs import update as _maj

        v = str(_maj.version_locale())
    except Exception:  # an incomplete install must not hide the panel
        v = "0"
    if v in ("", "0"):
        try:
            v = metadata.version("jobhunter")
        except metadata.PackageNotFoundError:
            v = "?"
    return v


class ParametresMixin:
    def _parametres_panel(self: "AppTypee") -> None:
        self._hide_all()
        if "parametres" in self._panels:
            w = self._panels["parametres"]
            w._reload()
            w.pack(fill="both", expand=True)
            return
        w = CF(self.main, bg=WORK)
        self._panels["parametres"] = w

        def carte(titre: str, aide: str) -> Any:
            c = CF(w, bg=CARD)
            c.pack(fill="x", padx=28, pady=(16, 0))
            CL(c, text=titre, bg=CARD, fg=TX, font=(_theme.FONT_UI, 14, "bold"), anchor="w").pack(
                fill="x", padx=18, pady=(14, 0)
            )
            CL(c, text=aide, bg=CARD, fg=MUT, anchor="w", justify="left", wraplength=820).pack(
                fill="x", padx=18, pady=(0, 8)
            )
            return c

        # ── language ──
        c = carte(
            "Langue de l'interface",
            "La même pour tous les profils. JobHunter redémarre dans la langue choisie. "
            "Tes lettres, ton profil et tes données gardent la leur.",
        )
        codes = list(_langue.noms())
        noms = list(_langue.noms().values())
        langues = ctk.CTkSegmentedButton(
            c,
            values=noms,
            command=lambda nom: choisir(codes[noms.index(nom)]),
            selected_color=ACC,
            selected_hover_color=ACC_H,
            font=ctk.CTkFont(_theme.FONT_UI, 14),
            height=38,
        )
        langues.pack(anchor="w", padx=18, pady=(0, 16))

        def choisir(code: str) -> None:
            if code == _langue.LANGUE:
                return
            _langue.choisir(code)
            if getattr(self, "proc", None) and self.proc.poll() is None:
                messagebox.showinfo(
                    "JobHunter", _langue.message_relance(code), parent=self.root
                )  # a task runs: the language applies at the next start
                return
            self._relancer()

        # ── version and update ──
        c2 = carte(
            "Version",
            "Les mises à jour viennent de GitHub ; chacune est vérifiée avant d'être installée.",
        )
        ligne = CF(c2, bg=CARD, plat=True)
        ligne.pack(fill="x", padx=18, pady=(0, 16))
        v_lbl = CL(ligne, text="", bg=CARD, fg=TX, font=(_theme.FONT_UI, 13))
        v_lbl.pack(side="left")
        CB(
            ligne,
            text="Vérifier les mises à jour",
            command=self.mettre_a_jour,
            bg=BTN,
            fg=TX,
            activebackground=BTN_H,
            relief="flat",
            cursor="hand2",
        ).pack(side="left", padx=16)

        # ── daily collection (scheduled task; it was under the ⚙ wheel until 3.20) ──
        c3 = carte(
            "Collecte automatique",
            "Chaque jour à l'heure choisie, l'ordinateur collecte les offres de tous tes "
            "profils, même si JobHunter est fermé.",
        )
        ligne3 = CF(c3, bg=CARD, plat=True)
        ligne3.pack(fill="x", padx=18, pady=(0, 16))
        plan_lbl = CL(ligne3, text="", bg=CARD, fg=TX, font=(_theme.FONT_UI, 13))
        plan_lbl.pack(side="left")

        def planifier() -> None:
            self._planifier()
            recharger()

        CB(
            ligne3,
            text="Collecte chaque matin…",
            command=planifier,
            bg=BTN,
            fg=TX,
            activebackground=BTN_H,
            relief="flat",
            cursor="hand2",
        ).pack(side="left", padx=16)

        def recharger() -> None:
            langues.set(noms[codes.index(_langue.LANGUE)] if _langue.LANGUE in codes else noms[0])
            v_lbl.configure(text=f"JobHunter {version()}")
            from jobhunter import scheduling as _plan

            if not _plan.disponible():
                etat = _t("Planification disponible sous Windows (ailleurs : schedule.sh).")
            elif _plan.planifiee():
                etat = _t("Planifiée.")
            else:
                etat = _t("Pas planifiée.")
            plan_lbl.configure(text=etat)

        w._reload = recharger
        w._choisir = choisir  # for the tests
        recharger()
        w.pack(fill="both", expand=True)
