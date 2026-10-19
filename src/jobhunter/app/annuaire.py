"""Fenêtre « Annuaire » du panneau Entreprises : taper un nom, choisir, suivre.

Partie de jobhunter.app. Cherche dans les annuaires Lever, Ashby et Greenhouse du moteur
(jobhunter.sources.annuaire) ; aucune requête web. Une entreprise déjà suivie est
marquée comme telle.
"""

from collections.abc import Callable
from tkinter import ttk
from typing import Any

import customtkinter as ctk

from jobhunter.app import theme as _theme
from jobhunter.app.inventaire import NOMS_OUTILS
from jobhunter.app.langue import t as _t
from jobhunter.app.theme import ACC, ACC_H, ACC_TX, BG, BTN, BTN_H, CB, CE, CF, CL, MUT, ROW0, TX
from jobhunter.sources import annuaire


def choisir(
    app: Any,
    texte: str,
    suivis: Callable[[], set[tuple[str, str]]],
    suivre: Callable[[annuaire.Entree], None],
) -> None:
    """Ouvre la recherche dans l'annuaire, pré-remplie avec `texte`.

    Args:
        app: l'application (fenêtre parente).
        texte: le nom déjà tapé dans le panneau.
        suivis: rend les flux déjà suivis, {(outil, identifiant en minuscules)}.
        suivre: appelé avec l'entreprise choisie.
    """
    win = ctk.CTkToplevel(app.root)
    win.title(_t("Annuaire des entreprises"))
    win.configure(fg_color=BG)
    win.geometry("720x520")
    win.transient(app.root)
    CL(
        win,
        text=_t("Annuaire des entreprises"),
        bg=BG,
        fg=TX,
        font=(_theme.FONT_UI, 16),
    ).pack(anchor="w", padx=22, pady=(16, 2))
    CL(
        win,
        text=_t(
            "3 600 entreprises lues par l'API publique de Lever, Ashby ou Greenhouse. "
            "Double-clic ou Entrée : suivre."
        ),
        bg=BG,
        fg=MUT,
        anchor="w",
        justify="left",
        wraplength=660,
    ).pack(fill="x", padx=22)
    champ = CE(win, bg=ROW0, fg=TX, width=60)
    champ.pack(fill="x", padx=22, pady=(10, 6))
    champ.insert(0, texte)
    tv = ttk.Treeview(win, columns=("nom", "outil", "id", "etat"), show="headings", height=12)
    for k, lbl, wd in (
        ("nom", "Entreprise", 250),
        ("outil", "Outil", 110),
        ("id", "Identifiant", 170),
        ("etat", "", 110),
    ):
        tv.heading(k, text=_t(lbl) if lbl else "")
        tv.column(k, width=wd, anchor="w", stretch=(k == "nom"))
    tv.pack(fill="both", expand=True, padx=22)
    resultats: dict[str, annuaire.Entree] = {}

    def remplir() -> None:
        tv.delete(*tv.get_children())
        resultats.clear()
        deja = suivis()
        for i, e in enumerate(annuaire.chercher(champ.get(), limite=50)):
            suivi = (e.outil, e.jeton.lower()) in deja
            iid = tv.insert(
                "",
                "end",
                values=(
                    e.nom,
                    NOMS_OUTILS.get(e.outil, e.outil),
                    e.jeton,
                    _t("suivie") if suivi else "",
                ),
            )
            resultats[iid] = e
            if i == 0:
                tv.selection_set(iid)

    def valider() -> None:
        sel = tv.selection()
        if sel and sel[0] in resultats:
            suivre(resultats[sel[0]])
            remplir()

    champ.bind(
        "<KeyRelease>", lambda e: remplir() if e.keysym not in ("Up", "Down", "Return") else None
    )
    champ.bind("<Return>", lambda e: valider())
    champ.bind("<Down>", lambda e: tv.focus_set())
    tv.bind("<Double-1>", lambda e: valider())
    tv.bind("<Return>", lambda e: valider())
    bas = CF(win, bg=BG)
    bas.pack(fill="x", padx=22, pady=12)
    CB(
        bas,
        text="Suivre",
        command=valider,
        bg=ACC,
        fg=ACC_TX,
        activebackground=ACC_H,
        relief="flat",
        cursor="hand2",
    ).pack(side="left")
    CB(
        bas,
        text="Fermer",
        command=win.destroy,
        bg=BTN,
        fg=TX,
        activebackground=BTN_H,
        relief="flat",
        cursor="hand2",
    ).pack(side="right")
    win.bind("<Escape>", lambda e: win.destroy())
    remplir()
    win.after(50, champ.focus_set)
