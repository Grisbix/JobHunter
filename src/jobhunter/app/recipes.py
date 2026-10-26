"""Recettes de nettoyage: write the normalisation rules, see their effect, then apply.

One rule per line, `champ | de | vers` (jobhunter.cleanup_recipes). « Aperçu » lists every
change on the queue in memory — nothing is written; « Appliquer » saves the recipes and
runs `jobhunter recipes --appliquer`, which writes under the queue's lock.
"""

from tkinter import messagebox, ttk
from typing import Any

import customtkinter as ctk

from jobhunter import cleanup_recipes as R
from jobhunter import root as _racine
from jobhunter.app import theme as _theme
from jobhunter.app.common import PY
from jobhunter.app.language import t as _t
from jobhunter.app.theme import BG, CF, CL, MUT, TX
from jobhunter.storage import applications as suivi_io

EXEMPLE = R.EXEMPLE


def ouvrir(app: Any) -> None:
    """The recipes editor, its preview on the queue, and the button that applies them."""
    chemin = _racine.dans(_racine.scripts(), R.FICHIER)
    win = ctk.CTkToplevel(app.root)
    win.title(_t("Recettes de nettoyage"))
    win.configure(fg_color=BG)
    win.geometry("980x620")
    win.transient(app.root)
    CL(win, text=_t("Recettes de nettoyage"), bg=BG, fg=TX, font=(_theme.FONT_UI, 16)).pack(
        anchor="w", padx=22, pady=(16, 2)
    )
    CL(
        win,
        text=_t(
            "Une règle par ligne : champ | valeur à remplacer | nouvelle valeur. Une valeur "
            "doit correspondre au champ entier (majuscules et espaces ignorés) ; « re: » "
            "introduit un motif. Rejouer les mêmes recettes ne change rien la deuxième fois. "
            "Une offre à laquelle tu as postulé n'est jamais renommée."
        ),
        bg=BG,
        fg=MUT,
        anchor="w",
        justify="left",
        wraplength=920,
    ).pack(fill="x", padx=22)
    zone = ctk.CTkTextbox(win, height=120, font=(_theme.FONT_MONO, 12))
    zone.pack(fill="x", padx=22, pady=(10, 6))
    zone.insert("1.0", R.en_texte(R.lire(chemin)) or EXEMPLE)
    etat = CL(win, text="", bg=BG, fg=MUT, anchor="w")
    etat.pack(fill="x", padx=22)
    tv = ttk.Treeview(win, columns=("champ", "avant", "apres", "note"), show="headings", height=8)
    for k, lbl, wd in (
        ("champ", "Champ", 110),
        ("avant", "Avant", 320),
        ("apres", "Après", 320),
        ("note", "Remarque", 150),
    ):
        tv.heading(k, text=_t(lbl))
        tv.column(k, width=wd, anchor="w", stretch=k in ("avant", "apres"))
    tv.tag_configure("ecarte", foreground=MUT)
    bas = CF(win, bg=BG)
    bas.pack(side="bottom", fill="x", padx=22, pady=(4, 14))  # before the list: always visible
    tv.pack(fill="both", expand=True, padx=22, pady=6)
    raisons = {"candidature": _t("candidature : gardé"), "doublon": _t("doublon : gardé")}

    def recettes() -> list[R.Recette] | None:
        r = R.depuis_texte(zone.get("1.0", "end"))
        if erreurs := R.valider(r):
            messagebox.showerror("JobHunter", "\n".join(erreurs), parent=win)
            return None
        return r

    def apercu() -> list[R.Changement]:
        r = recettes()
        if r is None:
            return []
        chg = R.apercu(list(app.offers), r, set(suivi_io.charger()))
        tv.delete(*tv.get_children())
        for c in chg[:2000]:
            tv.insert(
                "",
                "end",
                values=(_t(c.champ), c.avant, c.apres, raisons.get(c.ecarte, "")),
                tags=("ecarte",) if c.ecarte else (),
            )
        n = sum(1 for c in chg if not c.ecarte)
        etat.configure(
            text=_t("{a} changement(s), {b} écarté(s). Rien n'est écrit.").format(
                a=n, b=len(chg) - n
            )
        )
        return chg

    def appliquer() -> None:
        r = recettes()
        if r is None:
            return
        R.ecrire(chemin, r)
        if not any(not c.ecarte for c in apercu()):
            etat.configure(text=_t("Recettes enregistrées : rien à changer dans la file."))
            return
        win.destroy()
        app.run_step(
            [PY, "-m", "jobhunter.programs.recipes", "--appliquer"], _t("Recettes de nettoyage")
        )

    ctk.CTkButton(bas, text=_t("Aperçu"), command=apercu).pack(side="left")
    ctk.CTkButton(bas, text=_t("Enregistrer et appliquer"), command=appliquer).pack(
        side="left", padx=8
    )
    ctk.CTkButton(
        bas,
        text=_t("Fermer"),
        fg_color="transparent",
        border_width=1,
        text_color=TX,
        command=win.destroy,
    ).pack(side="right")
