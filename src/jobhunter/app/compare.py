"""Documents à comparer: a retouched CV or letter, and the newer version generated beside it.

Since 3.7, regenerating never overwrites a document retouched by hand: the new version
waits in `_a_comparer/` (documents.generated). This window lists them, shows the
paragraphs that differ (removed in red, added in green), and lets the user choose. The
version not chosen is set aside in `_a_comparer/_anciennes/`, never deleted.
"""

import os
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any

import customtkinter as ctk

from jobhunter import paths as _chemins
from jobhunter.app import theme as _theme
from jobhunter.app.language import t as _t
from jobhunter.app.theme import BG, CF, CL, MUT, TX
from jobhunter.documents import generated as _generes


def dossiers() -> list[Any]:
    """Where the generated documents live: CV and letters by offer."""
    return [_chemins.CV_PAR_OFFRE, _chemins.LT_PAR_OFFRE]


def nombre() -> int:
    """How many new versions are waiting (0 if the folders cannot be read)."""
    try:
        return len(_generes.en_attente(dossiers()))
    except OSError:
        return 0


def ouvrir(app: Any) -> None:
    """The list of documents waiting, the differences of the selected one, the choice."""
    win = ctk.CTkToplevel(app.root)
    win.title(_t("Documents à comparer"))
    win.configure(fg_color=BG)
    win.geometry("980x640")
    win.transient(app.root)
    CL(win, text=_t("Documents à comparer"), bg=BG, fg=TX, font=(_theme.FONT_UI, 16)).pack(
        anchor="w", padx=22, pady=(16, 2)
    )
    info = CL(
        win,
        text=_t(
            "Tu as retouché ces documents à la main ; une version plus récente a été générée "
            "à côté. Rouge : seulement dans ta version. Vert : seulement dans la nouvelle. "
            "La version que tu ne gardes pas est mise de côté dans _a_comparer/_anciennes/, "
            "jamais supprimée."
        ),
        bg=BG,
        fg=MUT,
        anchor="w",
        justify="left",
        wraplength=920,
    )
    info.pack(fill="x", padx=22)
    tv = ttk.Treeview(win, columns=("doc", "ecart"), show="headings", height=6)
    tv.heading("doc", text=_t("Document"))
    tv.heading("ecart", text=_t("Paragraphes différents"))
    tv.column("doc", width=700, anchor="w", stretch=True)
    tv.column("ecart", width=160, anchor="center")
    tv.pack(fill="x", padx=22, pady=(10, 6))
    texte = tk.Text(win, wrap="word", height=18, relief="flat", font=(_theme.FONT_UI, 11))
    texte.tag_configure("-", background="#fde2e2", foreground="#8a1c1c")
    texte.tag_configure("+", background="#dcf5e3", foreground="#145c2c")
    texte.tag_configure("=", foreground="#6b7280")
    bas = CF(win, bg=BG)
    bas.pack(side="bottom", fill="x", padx=22, pady=12)  # before the text: always visible
    texte.pack(fill="both", expand=True, padx=22)
    attente: dict[str, _generes.EnAttente] = {}

    def remplir() -> None:
        tv.delete(*tv.get_children())
        attente.clear()
        for e in _generes.en_attente(dossiers()):
            try:
                n = str(_generes.ecart(e.actuel, e.nouveau))
            except Exception:  # open in Word, damaged: shown, not compared
                n = "?"
            iid = tv.insert("", "end", values=(os.path.relpath(e.actuel, _chemins.BASE), n))
            attente[iid] = e
        texte.delete("1.0", "end")
        if not attente:
            texte.insert("end", _t("Aucun document en attente de comparaison."), "=")
        else:
            tv.selection_set(next(iter(attente)))

    def montrer(_ev: object = None) -> None:
        sel = tv.selection()
        texte.delete("1.0", "end")
        if not sel or sel[0] not in attente:
            return
        e = attente[sel[0]]
        try:
            lignes = _generes.comparer(e.actuel, e.nouveau)
        except Exception as x:
            texte.insert("end", _t("Lecture impossible : {a}").format(a=type(x).__name__), "-")
            return
        for genre, p in lignes:
            if genre == "=" and not p.strip():
                continue
            texte.insert("end", {"-": "− ", "+": "+ ", "=": "  "}[genre] + p + "\n", genre)

    def choisir(prendre: bool) -> None:
        sel = tv.selection()
        if not sel or sel[0] not in attente:
            return
        e = attente[sel[0]]
        try:
            ou = _generes.prendre_nouvelle(e) if prendre else _generes.garder_mienne(e)
        except OSError as x:
            # the document is open in Word: nothing moved
            messagebox.showerror(
                "JobHunter",
                _t(
                    "Impossible pour l'instant ({a}) : le document est-il ouvert dans Word ?"
                ).format(a=type(x).__name__),
                parent=win,
            )
            return
        app.status.configure(text=_t("Version mise de côté : {a}").format(a=ou.name))
        remplir()

    tv.bind("<<TreeviewSelect>>", montrer)
    ctk.CTkButton(bas, text=_t("Prendre la nouvelle version"), command=lambda: choisir(True)).pack(
        side="left"
    )
    ctk.CTkButton(
        bas,
        text=_t("Garder ma version"),
        fg_color="transparent",
        border_width=1,
        text_color=TX,
        command=lambda: choisir(False),
    ).pack(side="left", padx=8)
    ctk.CTkButton(
        bas,
        text=_t("Fermer"),
        fg_color="transparent",
        border_width=1,
        text_color=TX,
        command=win.destroy,
    ).pack(side="right")
    remplir()
    montrer()
