"""Entry of a collection API key, in a small window of the application.

Part of jobhunter.app. The key goes into the file the source really reads
(jobhunter.cles_api). Secret fields are masked; no value already stored is read back
or displayed again: a field left empty keeps it.
"""

import webbrowser
from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from jobhunter import cles_api
from jobhunter.app import theme as _theme
from jobhunter.app.commun import SCRIPTS
from jobhunter.app.langue import t as _t
from jobhunter.app.theme import ACC, ACC_H, ACC_TX, BG, BTN, BTN_H, CB, CE, CF, CL, MUT, TX, TX_BAD


def saisir_cle(app: Any, nom: str, apres: Callable[[], None]) -> None:
    """Opens the entry window for the `nom` key (francetravail, adzuna, jooble).

    Args:
        app: the application (for the parent window and the log).
        nom: the source.
        apres: called back after a successful save (refreshes the panel).
    """
    cle = cles_api.CLES[nom]
    deja = cles_api.presente(SCRIPTS, nom)
    win = ctk.CTkToplevel(app.root)
    win.title(f"{_t('Clé')} {cle.libelle}")
    win.configure(fg_color=BG)
    win.resizable(False, False)
    win.transient(app.root)

    CL(win, text=f"{_t('Clé')} {cle.libelle}", bg=BG, fg=TX, font=(_theme.FONT_UI, 16)).pack(
        anchor="w", padx=22, pady=(18, 2)
    )
    aide = _t("Enregistrée dans Scripts/{f}, sur ce PC seulement (ignoré par git).").format(
        f=cle.fichier
    )
    if deja:
        aide += " " + _t("Une clé est déjà posée : un champ laissé vide la garde.")
    CL(win, text=aide, bg=BG, fg=MUT, anchor="w", justify="left", wraplength=440).pack(
        fill="x", padx=22, pady=(0, 10)
    )

    grille = CF(win, bg=BG)
    grille.pack(fill="x", padx=22)
    champs: dict[str, Any] = {}
    for i, champ in enumerate(cle.champs):
        CL(grille, text=champ, bg=BG, fg=TX, anchor="w").grid(row=i, column=0, sticky="w", pady=4)
        e = CE(grille, width=46)
        if champ in cle.secrets:
            e.configure(show="•")
        e.grid(row=i, column=1, sticky="ew", padx=(12, 0), pady=4)
        champs[champ] = e
    grille.columnconfigure(1, weight=1)

    voir = ctk.BooleanVar(value=False)

    def basculer() -> None:
        for champ in cle.secrets:
            champs[champ].configure(show="" if voir.get() else "•")

    ctk.CTkCheckBox(
        win, text=_t("Afficher la saisie"), variable=voir, command=basculer, text_color=MUT
    ).pack(anchor="w", padx=22, pady=(6, 0))

    retour = CL(win, text="", bg=BG, fg=TX_BAD, anchor="w", justify="left", wraplength=440)
    retour.pack(fill="x", padx=22, pady=(6, 0))

    def fermer() -> None:
        for e in champs.values():
            e.delete(0, "end")
        win.destroy()

    def enregistrer() -> None:
        valeurs = {k: e.get() for k, e in champs.items()}
        try:
            chemin = cles_api.enregistrer(SCRIPTS, nom, valeurs)
        except (OSError, ValueError) as ex:
            retour.configure(text=f"✗ {ex}")
            return
        fermer()
        app._log(
            f"✓ {_t('Clé')} {cle.libelle} → Scripts/{chemin.name}. "
            + _t("Elle sert dès la prochaine collecte ; « Collecter cette source » l'essaie.")
            + "\n"
        )
        apres()

    bas = CF(win, bg=BG)
    bas.pack(fill="x", padx=22, pady=(10, 18))
    CB(
        bas,
        text="Enregistrer",
        command=enregistrer,
        bg=ACC,
        fg=ACC_TX,
        activebackground=ACC_H,
        relief="flat",
        cursor="hand2",
    ).pack(side="left")
    CB(
        bas,
        text="Obtenir une clé",
        command=lambda: webbrowser.open(cle.obtenir),
        bg=BTN,
        fg=TX,
        activebackground=BTN_H,
        relief="flat",
        cursor="hand2",
    ).pack(side="left", padx=12)
    CB(
        bas,
        text="Annuler",
        command=fermer,
        bg=BTN,
        fg=TX,
        activebackground=BTN_H,
        relief="flat",
        cursor="hand2",
    ).pack(side="right")

    win.protocol("WM_DELETE_WINDOW", fermer)
    win.bind("<Return>", lambda e: enregistrer())
    win.bind("<Escape>", lambda e: fermer())
    win.after(50, lambda: (win.grab_set(), champs[cle.champs[0]].focus_set()))
