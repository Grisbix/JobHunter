"""First launch: without a profile, pick one's CV and answer a few questions, all in windows.

The CV is read here (jobhunter.cv_text); a form prefilled from it asks what the
console used to ask at the keyboard (first_launch.propositions); the profile is then
written by first_launch, given every answer as an option, in a process without a
console. Before 3.27.2 the questions were asked in a console window, which closed by
itself on an error: an unreadable CV ended in "the profile was not created" with no
reason shown.

Former start of JobHunter.pyw (phase 3.7). It ran at IMPORT of the .pyw; it is now a
function, called by the launcher BEFORE loading jobhunter.app (which reads the profile
as soon as it loads) -- hence this module outside the app package.
"""

import os
import sys
import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Any

from jobhunter import cv_text as _cv_text
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


# ── The new interface's look (web/static/style.css), in customtkinter ────────
# The installed application has no web view (pywebview is an extra), and these
# windows run before any profile exists: they repeat the web interface's palette —
# warm background, pale panel, white fields, dark main button, brown ticks.
# tests/test_cv_text.py checks the colours taken from style.css stay equal.
FOND = "#E3DFDD"  # --fond-rgb: the window
PANNEAU = "#F6F4F3"  # the frosted panel (--verre-fort over the background), opaque
FILET = "#FFFFFF"  # --filet: the panel's light edge
SURFACE = "#FFFFFF"  # --surface: fields and secondary buttons
PISTE = "#EAE6E3"  # --piste over the panel: drop zone, ticked lists
BORD_CHAMP = "#CFC6C1"  # a field's outline, visible on white
ENCRE = "#1C1917"  # --encre
TEXTE_DOUX = "#6F6763"  # --texte-doux
SOMBRE = "#151312"  # --sombre: the main button (.bouton.plein)
SOMBRE_H = "#2A2421"
SOMBRE_TX = "#F4EFEC"
SURVOL = "#EFEAE7"  # a secondary button under the mouse
BRUN = "#5C3C2E"  # --brun: ticks and radio buttons
BRUN_H = "#7A5242"
C1B = "#E39A6C"  # --c1b: the logo
TERRE = "#B96D49"  # --terre: the close button under the mouse
BARRE = "#FCFBFA"  # the white bar on top of the window
FEU = "#F3F0EE"  # its round-cornered buttons
BAD = "#A33A2B"
RAD_BOUTON = 12
RAD_CHAMP = 10
RAD_PANNEAU = 18
ICONE = Path(__file__).parent / "app" / "assets" / "jobhunter.ico"


def _police(taille: int = 13, gras: bool = False) -> Any:
    """The web interface's font: Inter when installed, Segoe UI otherwise."""
    import tkinter.font as tkf

    import customtkinter as ctk

    familles = set(tkf.families())
    nom = next(
        (
            n
            for n in ("Inter Display", "Inter", "Segoe UI Variable Display", "Segoe UI")
            if n in familles
        ),
        "TkDefaultFont",
    )
    return ctk.CTkFont(nom, taille, "bold" if gras else "normal")


def fenetre_accueil() -> Any:
    """The hidden root of the welcome windows: frameless, rounded, with the white bar.

    As the web interface's window: no Windows title bar, rounded corners (Windows 11),
    and a white bar on top carrying the brand, "reduce" and "close"; drag it to move.
    """
    import customtkinter as ctk

    ctk.set_appearance_mode("light")
    r = ctk.CTk(fg_color=FOND)
    r.title("JobHunter")
    try:
        if sys.platform == "win32":
            r.iconbitmap(default=str(ICONE))
        image = tk.PhotoImage(file=str(ICONE.with_suffix(".png")))
        r.iconphoto(True, image)
        r._icone = image  # Tk only holds a name
    except (tk.TclError, OSError):
        pass
    r._fermer = lambda: None
    r._sans_cadre = _sans_cadre(r)
    _barre(r)
    r.withdraw()
    return r


# Win32: a frameless window that keeps its taskbar button, with rounded corners.
_GWL_EXSTYLE = -20
_WS_EX_TOOLWINDOW = 0x00000080
_WS_EX_APPWINDOW = 0x00040000
_DWMWA_WINDOW_CORNER_PREFERENCE = 33
_DWMWCP_ROUND = 2
_SW_MINIMIZE = 6


def _hwnd(fenetre: Any) -> int:
    return int(fenetre.wm_frame(), 16)


def _sans_cadre(fenetre: Any) -> bool:
    """Removes the system frame on Windows; False elsewhere or on failure (frame kept)."""
    if sys.platform != "win32":
        return False
    try:
        import ctypes

        fenetre.overrideredirect(True)
        fenetre.update_idletasks()
        hwnd = _hwnd(fenetre)
        u32 = ctypes.windll.user32  # type: ignore[attr-defined,unused-ignore]
        # Tk makes a frameless window a tool window, without a taskbar button.
        style = u32.GetWindowLongW(hwnd, _GWL_EXSTYLE)
        u32.SetWindowLongW(hwnd, _GWL_EXSTYLE, (style & ~_WS_EX_TOOLWINDOW) | _WS_EX_APPWINDOW)
        coin = ctypes.c_int(_DWMWCP_ROUND)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(  # type: ignore[attr-defined,unused-ignore]
            hwnd, _DWMWA_WINDOW_CORNER_PREFERENCE, ctypes.byref(coin), ctypes.sizeof(coin)
        )
        return True
    except Exception:  # noqa: BLE001 — cosmetic only: the system frame stays
        try:
            fenetre.overrideredirect(False)
        except tk.TclError:
            pass
        return False


def _barre(fenetre: Any) -> None:
    """The white bar on top: brand on the left, reduce and close on the right, draggable."""
    import customtkinter as ctk

    barre = ctk.CTkFrame(fenetre, fg_color=BARRE, corner_radius=0, height=46)
    barre.pack(side="top", fill="x")
    barre.pack_propagate(False)
    marque = ctk.CTkFrame(barre, fg_color="transparent")
    marque.pack(side="left", padx=16)
    ctk.CTkFrame(marque, width=22, height=22, corner_radius=7, fg_color=C1B).pack(side="left")
    nom = _texte(marque, "JobHunter", taille=13, gras=True)
    nom.pack(side="left", padx=9)

    def reduire() -> None:
        if getattr(fenetre, "_sans_cadre", False):
            import ctypes

            ctypes.windll.user32.ShowWindow(_hwnd(fenetre), _SW_MINIMIZE)  # type: ignore[attr-defined,unused-ignore]
        else:
            fenetre.iconify()

    feux = ctk.CTkFrame(barre, fg_color="transparent")
    feux.pack(side="right", padx=12)
    for signe, action, survol, fermer in (
        ("—", reduire, SURVOL, False),
        ("✕", lambda: fenetre._fermer(), TERRE, True),
    ):
        b = ctk.CTkButton(
            feux,
            text=signe,
            command=action,
            width=30,
            height=30,
            corner_radius=10,
            fg_color=FEU,
            hover_color=survol,
            border_width=1,
            border_color=FILET,
            text_color=ENCRE,
            font=_police(11),
        )
        b.pack(side="left", padx=(8, 0))
        if fermer:  # white cross on the warm hover, as in the web bar
            b.bind("<Enter>", lambda e, b=b: b.configure(text_color="#FFFFFF"), add="+")
            b.bind("<Leave>", lambda e, b=b: b.configure(text_color=ENCRE), add="+")

    depart = {"x": 0, "y": 0}

    def saisir(e: Any) -> None:
        depart["x"], depart["y"] = e.x_root - fenetre.winfo_x(), e.y_root - fenetre.winfo_y()

    def glisser(e: Any) -> None:
        fenetre.geometry(f"+{e.x_root - depart['x']}+{e.y_root - depart['y']}")

    for w in (barre, marque, nom):
        w.bind("<ButtonPress-1>", saisir, add="+")
        w.bind("<B1-Motion>", glisser, add="+")


def _fermeture(fenetre: Any, action: Callable[[], None]) -> None:
    """What closing does now: the bar's cross and, with a system frame, its own."""
    fenetre._fermer = action
    fenetre.protocol("WM_DELETE_WINDOW", action)


def _carte(fenetre: Any) -> Any:
    """The panel under the bar."""
    import customtkinter as ctk

    carte = ctk.CTkFrame(
        fenetre,
        fg_color=PANNEAU,
        corner_radius=RAD_PANNEAU,
        border_width=1,
        border_color=FILET,
    )
    carte.pack(fill="both", expand=True, padx=18, pady=(14, 18))
    return carte


def _bouton(parent: Any, texte: str, commande: Any, principal: bool = False) -> Any:
    import customtkinter as ctk

    return ctk.CTkButton(
        parent,
        text=texte,
        command=commande,
        corner_radius=RAD_BOUTON,
        height=40,
        font=_police(13, principal),
        fg_color=SOMBRE if principal else SURFACE,
        hover_color=SOMBRE_H if principal else SURVOL,
        text_color=SOMBRE_TX if principal else ENCRE,
        border_width=0 if principal else 1,
        border_color=BORD_CHAMP,
    )


def _texte(
    parent: Any,
    texte: str,
    couleur: str = ENCRE,
    taille: int = 13,
    gras: bool = False,
    largeur: int = 0,
) -> Any:
    import customtkinter as ctk

    return ctk.CTkLabel(
        parent,
        text=texte,
        text_color=couleur,
        font=_police(taille, gras),
        justify="left",
        anchor="w",
        wraplength=largeur,
    )


def _centrer(fenetre: Any) -> None:
    fenetre.update_idletasks()
    w, h = fenetre.winfo_reqwidth(), fenetre.winfo_reqheight()
    x = max(0, (fenetre.winfo_screenwidth() - w) // 2)
    y = max(0, (fenetre.winfo_screenheight() - h) // 3)
    fenetre.geometry(f"+{x}+{y}")


def _montrer(fenetre: Any) -> None:
    """Centres and shows the window, also once its event loop has started.

    A CTk withdrawn before its first mainloop is withdrawn again by it (customtkinter
    restores that state after colouring the title bar on Windows): measured on
    2026-10-26, the welcome window never appeared.
    """
    _centrer(fenetre)
    fenetre.deiconify()

    def devant() -> None:
        fenetre.deiconify()
        fenetre.lift()
        fenetre.focus_force()

    fenetre.after(50, devant)


def demander_cv(fenetre: Any) -> str:
    """The welcome window: drop the CV on it, or choose it. "" = later."""
    import customtkinter as ctk

    choix = {"cv": ""}
    fenetre.title("JobHunter — bienvenue")
    carte = _carte(fenetre)
    corps = ctk.CTkFrame(carte, fg_color="transparent")
    corps.pack(fill="both", expand=True, padx=26, pady=(18, 24))
    _texte(corps, "Bienvenue", taille=28, gras=True).pack(anchor="w")
    _texte(
        corps,
        "Aucun profil pour l'instant. Donne ton CV, en PDF (ou en Word) : JobHunter le "
        "lit puis te pose quelques questions.",
        couleur=TEXTE_DOUX,
        largeur=460,
    ).pack(anchor="w", pady=(6, 0))
    zone = ctk.CTkLabel(
        corps,
        text="Dépose ton CV ici\nPDF ou Word",
        fg_color=PISTE,
        corner_radius=RAD_PANNEAU - 4,
        text_color=TEXTE_DOUX,
        font=_police(14, True),
        height=130,
        wraplength=420,
    )
    zone.pack(fill="x", pady=18)

    def fin(p: str) -> None:
        choix["cv"] = p
        fenetre.quit()

    def choisir() -> None:
        dep = _rac.dossier("Mon_CV")
        p = filedialog.askopenfilename(
            parent=fenetre,
            title="Ton CV",
            initialdir=str(dep if dep.is_dir() else Path.home()),
            filetypes=[("CV", "*.pdf *.docx"), ("PDF", "*.pdf"), ("Word", "*.docx")],
        )
        if p:
            fin(p)

    def depot(chemins: list[Path]) -> None:
        cv = choisir_cv(chemins)
        if cv is None:
            zone.configure(text="Ce n'est pas un CV PDF ou Word : dépose-en un autre.")
        else:
            fin(str(cv))

    if not activer_depot(fenetre, depot):
        zone.configure(text="Choisis ton CV (PDF ou Word) avec le bouton ci-dessous.")
    boutons = ctk.CTkFrame(corps, fg_color="transparent")
    boutons.pack(fill="x")
    _bouton(boutons, "Choisir mon CV…", choisir, principal=True).pack(side="left")
    _bouton(boutons, "Plus tard", lambda: fin("")).pack(side="right")
    _fermeture(fenetre, lambda: fin(""))
    _montrer(fenetre)
    fenetre.mainloop()
    carte.destroy()
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


# ── The questions, in a window ───────────────────────────────────────────────
PEU_DE_TEXTE = 200  # below, first_launch writes nothing unless the jobs are given


def arguments_profil(cv: str, rep: dict[str, Any]) -> list[str]:
    """first_launch's command-line answers for the form's answers `rep`."""
    args = [cv, "--auto"]
    for champ in ("prenom", "nom", "email", "telephone", "ville", "metiers"):
        args += [f"--{champ}", str(rep.get(champ) or "").strip()]
    args += ["--annees", str(int(rep.get("annees") or 0))]
    args += ["--genre", "f" if rep.get("genre") == "f" else "m"]
    # The sectors ticked, then the cities typed.
    villes = [v.strip() for v in str(rep.get("villes") or "").split(",") if v.strip()]
    prio = [*(rep.get("prioritaires") or []), *villes]
    if prio:
        args += ["--prioritaires", ",".join(dict.fromkeys(prio))]
    args += ["--etranger", "o" if rep.get("etranger") else "n"]
    if rep.get("etranger") and str(rep.get("pays_etrangers") or "").strip():
        args += ["--pays-etrangers", str(rep["pays_etrangers"]).strip()]
    args += ["--secondaires", ",".join(rep.get("secondaires") or [])]
    args += ["--entreprises", "o" if rep.get("entreprises") else "n"]
    args += ["--word", "o" if rep.get("word") else "n"]
    if str(rep.get("parcours") or "").strip():
        args += ["--parcours", str(rep["parcours"]).strip()]
    return args


def _ouvrir(chemin: Path) -> None:
    """Opens a file in its usual application (Word, LibreOffice…)."""
    if sys.platform == "win32":
        os.startfile(chemin)  # type: ignore[attr-defined,unused-ignore]  # Windows only
    else:
        import subprocess

        subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", str(chemin)])  # nosec B603


def demander_reponses(fenetre: Any, cv: str, texte: str) -> dict[str, Any] | str | None:
    """The form prefilled from the CV. Its answers, "autre" for another CV, None = later."""
    import customtkinter as ctk

    from jobhunter.programs import first_launch as _premier
    from jobhunter.scoring import zones

    prop = _premier.propositions(texte)
    secteurs = list(zones.CATALOGUE)
    fenetre.title("JobHunter — ton profil")
    carte = _carte(fenetre)
    # The buttons stay at the bottom; the form scrolls when the screen is short (a
    # laptop at 150 %: about 700 points high).
    pied = ctk.CTkFrame(carte, fg_color="transparent")
    pied.pack(side="bottom", fill="x", padx=24, pady=(4, 18))
    echelle = ctk.ScalingTracker.get_window_scaling(fenetre) or 1
    hauteur = int(min(820, fenetre.winfo_screenheight() / echelle - 300))
    cadre = ctk.CTkScrollableFrame(
        carte,
        fg_color="transparent",
        width=660,
        height=hauteur,
        scrollbar_button_color=BORD_CHAMP,
        scrollbar_button_hover_color=TEXTE_DOUX,
    )
    cadre.pack(fill="both", expand=True, padx=(24, 8), pady=(20, 0))
    cadre.grid_columnconfigure(1, weight=1)
    _texte(cadre, "Ton profil", taille=28, gras=True).grid(
        row=0, column=0, columnspan=2, sticky="w"
    )
    _texte(cadre, f"CV lu : {Path(cv).name}", couleur=TEXTE_DOUX).grid(
        row=1, column=0, columnspan=2, sticky="w"
    )
    ligne = 2
    if len(texte.strip()) < PEU_DE_TEXTE:
        _texte(
            cadre,
            "Presque rien n'a pu être lu dans ce CV. "
            + (
                _cv_text.pourquoi_peu_de_texte(cv)
                or "Choisis un PDF exporté depuis Word, Canva ou Google Docs, ou le .docx."
            )
            + " Sinon, remplis au moins les métiers visés.",
            couleur=BAD,
            largeur=640,
        ).grid(row=ligne, column=0, columnspan=2, sticky="w", pady=(8, 0))
        ligne += 1
    _texte(
        cadre,
        "Vérifie et complète : rien n'est écrit tant que tu n'as pas validé.",
        couleur=TEXTE_DOUX,
    ).grid(row=ligne, column=0, columnspan=2, sticky="w", pady=(4, 12))
    ligne += 1

    def champ(valeur: str, largeur: int = 360) -> Any:
        e = ctk.CTkEntry(
            cadre,
            width=largeur,
            corner_radius=RAD_CHAMP,
            border_width=1,
            border_color=BORD_CHAMP,
            fg_color=SURFACE,
            text_color=ENCRE,
            font=_police(),
        )
        e.insert(0, valeur)
        return e

    champs: dict[str, Any] = {}
    for cle, libelle in (
        ("prenom", "Prénom"),
        ("nom", "Nom"),
        ("email", "Email"),
        ("telephone", "Téléphone"),
        ("ville", "Ville"),
        ("metiers", "Métiers visés (séparés par des virgules)"),
    ):
        _texte(cadre, libelle).grid(row=ligne, column=0, sticky="w", pady=3, padx=(0, 16))
        champs[cle] = champ(str(prop.get(cle) or ""))
        champs[cle].grid(row=ligne, column=1, sticky="we", pady=3)
        ligne += 1
    _texte(cadre, "Années d'expérience (stages compris)").grid(
        row=ligne, column=0, sticky="w", pady=3, padx=(0, 16)
    )
    annees = champ(str(prop["annees"]), largeur=70)
    annees.grid(row=ligne, column=1, sticky="w", pady=3)
    ligne += 1
    genre = tk.StringVar(value=prop["genre"])
    _texte(cadre, "Accords dans les lettres").grid(
        row=ligne, column=0, sticky="w", pady=3, padx=(0, 16)
    )
    accords = ctk.CTkFrame(cadre, fg_color="transparent")
    accords.grid(row=ligne, column=1, sticky="w", pady=3)
    for val, lib in (("m", "« diplômé »"), ("f", "« diplômée »")):
        ctk.CTkRadioButton(
            accords,
            text=lib,
            variable=genre,
            border_color=BORD_CHAMP,
            value=val,
            fg_color=BRUN,
            hover_color=BRUN_H,
            text_color=ENCRE,
            font=_police(),
        ).pack(side="left", padx=(0, 16))
    ligne += 1

    coches: dict[str, dict[str, tk.BooleanVar]] = {}
    for cle, libelle, choisis in (
        ("prioritaires", "Secteurs prioritaires", prop["prioritaires"]),
        ("secondaires", "Secteurs secondaires (facultatif)", []),
    ):
        _texte(cadre, libelle).grid(row=ligne, column=0, columnspan=2, sticky="w", pady=(12, 4))
        ligne += 1
        liste = ctk.CTkFrame(cadre, fg_color=PISTE, corner_radius=RAD_BOUTON)
        liste.grid(row=ligne, column=0, columnspan=2, sticky="we", padx=(0, 12))
        for c in range(3):
            liste.grid_columnconfigure(c, weight=1, uniform="secteur")
        coches[cle] = {}
        for i, s in enumerate(secteurs):
            v = tk.BooleanVar(value=s in choisis)
            ctk.CTkCheckBox(
                liste,
                text=str(zones.CATALOGUE[s].get("libelle") or s),
                variable=v,
                fg_color=BRUN,
                hover_color=BRUN_H,
                border_color=BORD_CHAMP,
                text_color=ENCRE,
                font=_police(12),
                corner_radius=4,
                checkbox_width=18,
                checkbox_height=18,
            ).grid(row=i // 3, column=i % 3, sticky="w", padx=8, pady=3)
            coches[cle][s] = v
        ligne += 1
    _texte(cadre, "Autres villes de préférence (facultatif, séparées par des virgules)").grid(
        row=ligne, column=0, columnspan=2, sticky="w", pady=(12, 4)
    )
    ligne += 1
    champs["villes"] = champ("", largeur=640)
    champs["villes"].grid(row=ligne, column=0, columnspan=2, sticky="we", padx=(0, 12))
    ligne += 1

    # ── Where: the home country only, or abroad too (which countries) ──
    pays_maison = zones._ISO_PAYS.get(str(prop.get("pays") or "fr"), "ton pays")
    _texte(cadre, "Où chercher").grid(row=ligne, column=0, columnspan=2, sticky="w", pady=(12, 4))
    ligne += 1
    etranger = tk.BooleanVar(value=False)
    rang_ou = ctk.CTkFrame(cadre, fg_color="transparent")
    rang_ou.grid(row=ligne, column=0, columnspan=2, sticky="w")
    ligne += 1
    lib_pays = _texte(cadre, "Pays ou régions (ex. : Suisse, Belgique, Europe, monde)")
    lib_pays.grid(row=ligne, column=0, sticky="w", pady=3, padx=(0, 16))
    pays_etrangers = champ("")
    pays_etrangers.grid(row=ligne, column=1, sticky="we", pady=3)
    ligne += 1

    def montrer_pays() -> None:
        for w in (lib_pays, pays_etrangers):
            if etranger.get():
                w.grid()
            else:
                w.grid_remove()

    for dehors, lib in ((False, f"Seulement en {pays_maison}"), (True, "Aussi à l'étranger")):
        ctk.CTkRadioButton(
            rang_ou,
            text=lib,
            variable=etranger,
            value=dehors,
            command=montrer_pays,
            border_color=BORD_CHAMP,
            fg_color=BRUN,
            hover_color=BRUN_H,
            text_color=ENCRE,
            font=_police(),
        ).pack(side="left", padx=(0, 16))
    montrer_pays()
    entreprises = tk.BooleanVar(value=bool(prop["entreprises"]))
    ctk.CTkCheckBox(
        cadre,
        text="Suivre les ~90 entreprises de finance / ESG proposées",
        variable=entreprises,
        fg_color=BRUN,
        hover_color=BRUN_H,
        border_color=BORD_CHAMP,
        text_color=ENCRE,
        font=_police(),
        corner_radius=4,
    ).grid(row=ligne, column=0, columnspan=2, sticky="w", pady=(12, 0))
    ligne += 1
    erreur = _texte(pied, "", couleur=BAD)
    erreur.pack(anchor="w")

    # ── The CV sent, and the letters' background paragraph ──
    _texte(cadre, "Ton CV et tes lettres", taille=16, gras=True).grid(
        row=ligne, column=0, columnspan=2, sticky="w", pady=(20, 4)
    )
    ligne += 1
    pdf = Path(cv).suffix.lower() == ".pdf"
    word = tk.BooleanVar(value=pdf and len(texte.strip()) >= PEU_DE_TEXTE)
    if pdf:

        def apercu() -> None:
            import tempfile

            from jobhunter import cv_word

            try:
                sortie = Path(tempfile.mkdtemp()) / "Apercu_CV.docx"
                _ouvrir(cv_word.pdf_en_docx(cv, sortie))
            except (OSError, ValueError) as e:
                erreur.configure(text=f"Version Word impossible : {e}.")

        rang = ctk.CTkFrame(cadre, fg_color="transparent")
        rang.grid(row=ligne, column=0, columnspan=2, sticky="w")
        ctk.CTkCheckBox(
            rang,
            text="Adapter mon CV à chaque offre",
            variable=word,
            fg_color=BRUN,
            hover_color=BRUN_H,
            border_color=BORD_CHAMP,
            text_color=ENCRE,
            font=_police(),
            corner_radius=4,
        ).pack(side="left")
        _bouton(rang, "Voir la version Word", apercu).pack(side="left", padx=12)
        ligne += 1
        _texte(
            cadre,
            "Un PDF ne se modifie pas : il partirait identique pour chaque offre. JobHunter "
            "en refait une version Word, plus sobre, où les compétences demandées passent en "
            "premier. Ton PDF reste à côté ; décoche pour l'envoyer tel quel.",
            couleur=TEXTE_DOUX,
            largeur=640,
        ).grid(row=ligne, column=0, columnspan=2, sticky="w", pady=(2, 8))
        ligne += 1
    _texte(cadre, "Le paragraphe de parcours de tes lettres").grid(
        row=ligne, column=0, columnspan=2, sticky="w", pady=(6, 2)
    )
    ligne += 1
    parcours = ctk.CTkTextbox(
        cadre,
        height=110,
        wrap="word",
        corner_radius=RAD_CHAMP,
        border_width=1,
        border_color=BORD_CHAMP,
        fg_color=SURFACE,
        text_color=ENCRE,
        font=_police(),
    )
    parcours.insert("1.0", str(prop.get("parcours") or ""))
    parcours.grid(row=ligne, column=0, columnspan=2, sticky="we", padx=(0, 12))
    ligne += 1

    def depuis_lettre() -> None:
        from jobhunter import own_letter

        f = filedialog.askopenfilename(
            parent=fenetre,
            title="Ta lettre de motivation",
            initialdir=str(Path(cv).parent),
            filetypes=[("Lettre", "*.pdf *.docx"), ("PDF", "*.pdf"), ("Word", "*.docx")],
        )
        if not f:
            return
        try:
            trouve = own_letter.parcours_de_lettre(f)
        except (OSError, ValueError) as e:
            source.configure(text=f"Lettre illisible : {e}.", text_color=BAD)
            return
        if not trouve:
            source.configure(
                text="Aucun paragraphe de parcours trouvé dans cette lettre : écris-le ici.",
                text_color=BAD,
            )
            return
        parcours.delete("1.0", "end")
        parcours.insert("1.0", trouve)
        source.configure(text=f"Repris de {Path(f).name}. Relis-le.", text_color=TEXTE_DOUX)

    rang_lettre = ctk.CTkFrame(cadre, fg_color="transparent")
    rang_lettre.grid(row=ligne, column=0, columnspan=2, sticky="we", pady=(6, 0))
    _bouton(rang_lettre, "Reprendre celui de ma lettre…", depuis_lettre).pack(side="left")
    source = _texte(
        rang_lettre,
        "Tiré de ton CV. Tu as déjà une lettre que tu aimes ? Reprends-en le paragraphe.",
        couleur=TEXTE_DOUX,
        largeur=380,
    )
    source.pack(side="left", padx=12)
    ligne += 1

    choix: dict[str, Any] = {"r": None}

    def valider() -> None:
        metiers = champs["metiers"].get().strip()
        if not metiers or metiers == _premier.A_COMPLETER:
            erreur.configure(text="Indique au moins un métier visé.")
            return
        try:
            n = int(annees.get() or 0)
        except ValueError:
            erreur.configure(text="Années d'expérience : un nombre.")
            return
        choix["r"] = {
            **{k: v.get() for k, v in champs.items()},
            "annees": n,
            "genre": genre.get(),
            "entreprises": entreprises.get(),
            "etranger": etranger.get(),
            "pays_etrangers": pays_etrangers.get().strip(),
            "word": word.get(),
            "parcours": parcours.get("1.0", "end").strip(),
            **{k: [s for s, v in c.items() if v.get()] for k, c in coches.items()},
        }
        fenetre.quit()

    def fin(r: str | None) -> None:
        choix["r"] = r
        fenetre.quit()

    boutons = ctk.CTkFrame(pied, fg_color="transparent")
    boutons.pack(fill="x", pady=(4, 0))
    _bouton(boutons, "Créer mon profil", valider, principal=True).pack(side="left")
    _bouton(boutons, "Choisir un autre CV…", lambda: fin("autre")).pack(side="left", padx=8)
    _bouton(boutons, "Plus tard", lambda: fin(None)).pack(side="right")
    _fermeture(fenetre, lambda: fin(None))
    _montrer(fenetre)
    fenetre.mainloop()
    carte.destroy()
    fenetre.withdraw()
    reponse: dict[str, Any] | str | None = choix["r"]
    return reponse


def _attente(fenetre: Any) -> Any:
    """The "Création du profil…" card while first_launch writes the profile."""
    carte = _carte(fenetre)
    _fermeture(fenetre, lambda: None)  # the profile is being written: no closing
    _texte(carte, "Création du profil…", taille=15, gras=True).pack(padx=48, pady=32)
    fenetre.title("JobHunter")
    _montrer(fenetre)
    fenetre.update()
    return carte


def creer_profil(cv: str, rep: dict[str, Any]) -> tuple[bool, str]:
    """Runs first_launch with the answers, without a console. (created?, its output)."""
    import os
    import subprocess

    # pythonw has no standard output: python.exe, or jobhunter-cli.exe once installed.
    _rac.exporter_paquet()
    commande = [str(_gele.interpreteur()), "-m", "jobhunter.programs.first_launch"]
    try:
        r = subprocess.run(  # nosec B603 : our own program, arguments from our form
            commande + arguments_profil(cv, rep),
            cwd=str(_rac.racine()),
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=600,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        sortie = (r.stdout or "") + (r.stderr or "")
    except (OSError, subprocess.TimeoutExpired) as e:
        return False, f"{type(e).__name__} : {e}"
    try:
        _profil.charger()
    except _profil.ProfilAbsent:
        return False, sortie
    return True, sortie


def profil_guide(fenetre: Any, cv: str = "") -> bool:
    """CV, questions and writing, until a profile exists (True) or the user gives up.

    `cv` already chosen (a new profile from the application), or "" to ask for it.
    """
    while True:
        if not cv:
            cv = demander_cv(fenetre)
            if not cv:
                return False
        try:
            from jobhunter.programs.first_launch import lire_cv

            texte = lire_cv(cv)
        except (Exception, SystemExit) as e:  # a damaged, protected or unknown file
            messagebox.showerror(
                "JobHunter",
                f"Ce fichier ne s'ouvre pas : {Path(cv).name}\n\n{e}\n\n"
                "Ferme-le s'il est ouvert ailleurs, ou exporte-le à nouveau en PDF "
                "(ou en .docx), puis choisis-le encore.",
            )
            cv = ""
            continue
        rep = demander_reponses(fenetre, cv, texte)
        if rep == "autre":
            cv = ""
            continue
        if not isinstance(rep, dict):
            return False
        attente = _attente(fenetre)
        ok, sortie = creer_profil(cv, rep)
        attente.destroy()
        fenetre.withdraw()
        if ok:
            return True
        fin = "\n".join(sortie.strip().splitlines()[-12:]) or "(aucun message)"
        messagebox.showerror(
            "JobHunter",
            f"Le profil n'a pas été créé. Ce que JobHunter a répondu :\n\n{fin}\n\n"
            "Tu peux choisir un autre CV (un PDF exporté depuis Word ou Canva, ou le .docx).",
        )
        cv = ""


def assurer_profil() -> None:
    """Guarantees a profile before opening the application.

    Without a profile: the CV (dropped or chosen), the questions in a form, then the
    profile written by first_launch, and a short tour (sites, API keys, first
    collection); the application then starts normally. Everything happens in windows,
    and a failure says why in one.
    """
    _migrer_si_besoin()
    try:
        _profil.charger()
        return
    except _profil.ProfilAbsent:
        pass
    _r = fenetre_accueil()
    if not profil_guide(_r):
        messagebox.showinfo(
            "JobHunter",
            "Pas de profil pour l'instant : relance JobHunter quand tu auras ton CV sous la main.",
        )
        sys.exit(1)
    # The sites read, the API keys and a first collection (jobhunter.welcome_tour).
    from jobhunter.welcome_tour import visite

    visite(_r)
    _r.destroy()


def main(argv: list[str] | None = None) -> int:
    """`python -m jobhunter.welcome <cv>`: a new profile's questions, in windows.

    What the application's "new profile" runs in the new workspace (JOBHUNTER_RACINE),
    without a console. 0 when the profile exists, 1 otherwise.
    """
    args = sys.argv[1:] if argv is None else argv
    r = fenetre_accueil()
    try:
        return 0 if profil_guide(r, args[0] if args else "") else 1
    finally:
        r.destroy()


if __name__ == "__main__":
    sys.exit(main())
