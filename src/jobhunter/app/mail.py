"""The "Statuts depuis mes courriels" window (G4): read, suggest, validate one by one.

Part of jobhunter.app. The emails come from an export (.mbox, folder of .eml files) or
from the Gmail API, read-only (jobhunter.mail). Reading runs off the window's
thread; each suggestion is applied with one click ("Appliquer") or set aside
("Ignorer"). Nothing is written without that click.
"""

import threading
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any

import customtkinter as ctk

from jobhunter import root as _racine
from jobhunter.app import theme as _theme
from jobhunter.app.language import t as _t
from jobhunter.app.theme import ACC, ACC_H, ACC_TX, BG, BTN, BTN_H, CB, CF, CL, MUT, TX
from jobhunter.mail import reading as lecture
from jobhunter.mail import statuses as statuts
from jobhunter.programs import mail_statuses as statuts_mail
from jobhunter.storage import applications as suivi_io


def ouvrir(app: Any) -> None:
    """Choose the email source, then show the suggestions."""
    win = ctk.CTkToplevel(app.root)
    win.title(_t("Statuts depuis mes courriels"))
    win.configure(fg_color=BG)
    win.geometry("860x560")
    win.transient(app.root)
    CL(win, text=_t("Statuts depuis mes courriels"), bg=BG, fg=TX, font=(_theme.FONT_UI, 16)).pack(
        anchor="w", padx=22, pady=(16, 2)
    )
    info = CL(
        win,
        text=_t(
            "Lecture seule : les courriels sont lus et classés (refus, entretien, accusé de "
            "réception), jamais modifiés. Chaque statut proposé attend ton accord."
        ),
        bg=BG,
        fg=MUT,
        anchor="w",
        justify="left",
        wraplength=800,
    )
    info.pack(fill="x", padx=22)
    sources = CF(win, bg=BG)
    sources.pack(fill="x", padx=22, pady=10)
    tv = ttk.Treeview(win, columns=("le", "oid", "chg", "raison"), show="headings", height=14)
    for k, lbl, wd in (
        ("le", "Date", 90),
        ("oid", "Candidature", 330),
        ("chg", "Statut", 170),
        ("raison", "Formule trouvée", 220),
    ):
        tv.heading(k, text=_t(lbl))
        tv.column(k, width=wd, anchor="w", stretch=(k == "oid"))
    tv.pack(fill="both", expand=True, padx=22)
    props: dict[str, statuts.Proposition] = {}

    def montrer(liste: list[statuts.Proposition], lus: int) -> None:
        tv.delete(*tv.get_children())
        props.clear()
        for p in liste:
            iid = tv.insert(
                "", "end", values=(p.le, p.oid, f"{p.actuel or '—'} → {p.propose}", p.raison)
            )
            props[iid] = p
        info.configure(
            text=_t("{a} courriel(s) lus, {b} statut(s) à proposer.")
            .replace("{a}", str(lus))
            .replace("{b}", str(len(liste)))
        )
        kids = tv.get_children()
        if kids:
            tv.selection_set(kids[0])
            tv.focus_set()

    def lire(source: Any) -> None:
        info.configure(text=_t("Lecture des courriels…"))

        def fil() -> None:
            try:
                tous = list(source())
                liste = statuts.propositions(tous, suivi_io.charger())
                win.after(0, lambda: montrer(liste, len(tous)))
            except ImportError:
                msg = _t('Lecture Gmail : installe d\'abord pip install "jobhunter[gmail]".')
                win.after(0, lambda: info.configure(text=msg))
            except Exception as e:  # noqa: BLE001 — displayed, never swallowed
                erreur = f"! {type(e).__name__}: {e}"
                win.after(0, lambda: info.configure(text=erreur))

        threading.Thread(target=fil, daemon=True).start()

    def mbox() -> None:
        f = filedialog.askopenfilename(
            parent=win, filetypes=[("mbox", "*.mbox"), ("*", "*.*")], title=_t("Fichier .mbox")
        )
        if f:
            lire(lambda: lecture.depuis_mbox(Path(f)))

    def eml() -> None:
        d = filedialog.askdirectory(parent=win, title=_t("Dossier de fichiers .eml"))
        if d:
            lire(lambda: lecture.depuis_eml(Path(d)))

    def gmail() -> None:
        lire(lambda: lecture.depuis_gmail(_racine.dossier_cles()))

    for texte, cmd in (
        ("Fichier .mbox…", mbox),
        ("Dossier .eml…", eml),
        ("Gmail (lecture seule)", gmail),
    ):
        CB(
            sources,
            text=texte,
            command=cmd,
            bg=BTN,
            fg=TX,
            activebackground=BTN_H,
            relief="flat",
            cursor="hand2",
        ).pack(side="left", padx=(0, 8))

    def choisie() -> tuple[str, statuts.Proposition] | None:
        sel = tv.selection()
        return (sel[0], props[sel[0]]) if sel and sel[0] in props else None

    def suivante(iid: str) -> None:
        nxt = tv.next(iid) or tv.prev(iid)
        tv.delete(iid)
        props.pop(iid, None)
        if nxt:
            tv.selection_set(nxt)
            tv.focus(nxt)

    def appliquer() -> None:
        c = choisie()
        if not c:
            return
        iid, p = c
        try:
            ecrit = statuts_mail.appliquer(p, attente=3)
        except suivi_io.VerrouIndisponible:
            messagebox.showwarning(
                "JobHunter", _t("Suivi occupé : réessaie dans un instant."), parent=win
            )
            return
        if not ecrit:
            messagebox.showinfo(
                "JobHunter", _t("Le suivi a changé entre-temps : rien écrit."), parent=win
            )
        app.q.put(("reload", None))
        suivante(iid)

    def ignorer() -> None:
        c = choisie()
        if c:
            suivante(c[0])

    bas = CF(win, bg=BG)
    bas.pack(fill="x", padx=22, pady=12)
    CB(
        bas,
        text="Appliquer",
        command=appliquer,
        bg=ACC,
        fg=ACC_TX,
        activebackground=ACC_H,
        relief="flat",
        cursor="hand2",
    ).pack(side="left")
    CB(
        bas, text="Ignorer", command=ignorer, bg=BTN, fg=TX, activebackground=BTN_H, relief="flat"
    ).pack(side="left", padx=8)
    CB(
        bas,
        text="Fermer",
        command=win.destroy,
        bg=BTN,
        fg=TX,
        activebackground=BTN_H,
        relief="flat",
    ).pack(side="right")
    tv.bind("<Return>", lambda e: appliquer())
    tv.bind("<Delete>", lambda e: ignorer())
    win.bind("<Escape>", lambda e: win.destroy())
