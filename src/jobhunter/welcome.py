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


# ── The application's look (app.theme), without loading the app package ─────
# jobhunter.app reads the profile when it loads, and these windows run before one
# exists: the few colours they use are repeated here (tests/test_cv_text.py checks
# they stay equal to app.theme's).
BG = "#E9EFF7"
CARD = "#FFFFFF"
LINE = "#D8E2EF"
LINE_SAISIE = "#74869F"
TX = "#19283F"
MUT = "#52647B"
ACC = "#325EDF"
ACC_H = "#234FC7"
BTN = "#E7EDF7"
BTN_H = "#D4E1F7"
BAD = "#AC3E49"
RAD_BTN = 6
RAD_CARD = 10
ICONE = Path(__file__).parent / "app" / "assets" / "jobhunter.ico"


def _police(taille: int = 13, gras: bool = False) -> Any:
    """The application's font (IBM Plex Sans when installed, Segoe UI otherwise)."""
    import tkinter.font as tkf

    import customtkinter as ctk

    familles = set(tkf.families())
    nom = next((n for n in ("IBM Plex Sans", "Segoe UI") if n in familles), "TkDefaultFont")
    return ctk.CTkFont(nom, taille, "bold" if gras else "normal")


def fenetre_accueil() -> Any:
    """The hidden root of the welcome windows: JobHunter's background and icon."""
    import customtkinter as ctk

    ctk.set_appearance_mode("light")
    r = ctk.CTk(fg_color=BG)
    r.title("JobHunter")
    try:
        if sys.platform == "win32":
            r.iconbitmap(default=str(ICONE))
        image = tk.PhotoImage(file=str(ICONE.with_suffix(".png")))
        r.iconphoto(True, image)
        r._icone = image  # Tk only holds a name
    except (tk.TclError, OSError):
        pass
    r.withdraw()
    return r


def _carte(fenetre: Any) -> Any:
    import customtkinter as ctk

    carte = ctk.CTkFrame(
        fenetre, fg_color=CARD, corner_radius=RAD_CARD, border_width=1, border_color=LINE
    )
    carte.pack(fill="both", expand=True, padx=20, pady=20)
    return carte


def _bouton(parent: Any, texte: str, commande: Any, principal: bool = False) -> Any:
    import customtkinter as ctk

    return ctk.CTkButton(
        parent,
        text=texte,
        command=commande,
        corner_radius=RAD_BTN,
        height=34,
        font=_police(13, True),
        fg_color=ACC if principal else BTN,
        hover_color=ACC_H if principal else BTN_H,
        text_color="#FFFFFF" if principal else TX,
    )


def _texte(
    parent: Any,
    texte: str,
    couleur: str = TX,
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
    corps.pack(fill="both", expand=True, padx=28, pady=24)
    _texte(corps, "Bienvenue dans JobHunter", taille=20, gras=True).pack(anchor="w")
    _texte(
        corps,
        "Aucun profil pour l'instant. Donne ton CV (.docx de préférence, ou .pdf) : "
        "JobHunter le lit puis te pose quelques questions.",
        couleur=MUT,
        largeur=440,
    ).pack(anchor="w", pady=(6, 0))
    zone = ctk.CTkLabel(
        corps,
        text="Dépose ton CV ici",
        fg_color=BG,
        corner_radius=RAD_CARD,
        text_color=MUT,
        font=_police(14, True),
        height=120,
        wraplength=400,
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
    boutons = ctk.CTkFrame(corps, fg_color="transparent")
    boutons.pack(fill="x")
    _bouton(boutons, "Choisir mon CV…", choisir, principal=True).pack(side="left")
    _bouton(boutons, "Plus tard", lambda: fin("")).pack(side="right")
    fenetre.protocol("WM_DELETE_WINDOW", lambda: fin(""))
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
    if rep.get("prioritaires"):
        args += ["--prioritaires", ",".join(rep["prioritaires"])]
    args += ["--secondaires", ",".join(rep.get("secondaires") or [])]
    args += ["--entreprises", "o" if rep.get("entreprises") else "n"]
    return args


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
    hauteur = int(min(820, fenetre.winfo_screenheight() / echelle - 230))
    cadre = ctk.CTkScrollableFrame(carte, fg_color="transparent", width=660, height=hauteur)
    cadre.pack(fill="both", expand=True, padx=(24, 8), pady=(20, 0))
    cadre.grid_columnconfigure(1, weight=1)
    _texte(cadre, "Ton profil", taille=20, gras=True).grid(
        row=0, column=0, columnspan=2, sticky="w"
    )
    _texte(cadre, f"CV lu : {Path(cv).name}", couleur=MUT).grid(
        row=1, column=0, columnspan=2, sticky="w"
    )
    ligne = 2
    if len(texte.strip()) < PEU_DE_TEXTE:
        _texte(
            cadre,
            "Presque rien n'a pu être lu dans ce CV : il est sans doute scanné ou "
            "enregistré en image. Choisis plutôt un .docx, ou un PDF exporté depuis Word ; "
            "sinon, remplis au moins les métiers visés.",
            couleur=BAD,
            largeur=560,
        ).grid(row=ligne, column=0, columnspan=2, sticky="w", pady=(8, 0))
        ligne += 1
    _texte(
        cadre, "Vérifie et complète : rien n'est écrit tant que tu n'as pas validé.", couleur=MUT
    ).grid(row=ligne, column=0, columnspan=2, sticky="w", pady=(4, 12))
    ligne += 1

    def champ(valeur: str, largeur: int = 360) -> Any:
        e = ctk.CTkEntry(
            cadre,
            width=largeur,
            corner_radius=RAD_BTN,
            border_width=1,
            border_color=LINE_SAISIE,
            fg_color=CARD,
            text_color=TX,
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
            value=val,
            fg_color=ACC,
            hover_color=ACC_H,
            text_color=TX,
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
        liste = ctk.CTkFrame(cadre, fg_color=BG, corner_radius=RAD_BTN)
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
                fg_color=ACC,
                hover_color=ACC_H,
                border_color=LINE_SAISIE,
                text_color=TX,
                font=_police(12),
                corner_radius=4,
                checkbox_width=18,
                checkbox_height=18,
            ).grid(row=i // 3, column=i % 3, sticky="w", padx=8, pady=3)
            coches[cle][s] = v
        ligne += 1
    entreprises = tk.BooleanVar(value=bool(prop["entreprises"]))
    ctk.CTkCheckBox(
        cadre,
        text="Suivre les ~90 entreprises de finance / ESG proposées",
        variable=entreprises,
        fg_color=ACC,
        hover_color=ACC_H,
        border_color=LINE_SAISIE,
        text_color=TX,
        font=_police(),
        corner_radius=4,
    ).grid(row=ligne, column=0, columnspan=2, sticky="w", pady=(12, 0))
    ligne += 1
    erreur = _texte(pied, "", couleur=BAD)
    erreur.pack(anchor="w")

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
    fenetre.protocol("WM_DELETE_WINDOW", lambda: fin(None))
    _montrer(fenetre)
    fenetre.mainloop()
    carte.destroy()
    fenetre.withdraw()
    reponse: dict[str, Any] | str | None = choix["r"]
    return reponse


def _attente(fenetre: Any) -> Any:
    """The "Création du profil…" card while first_launch writes the profile."""
    carte = _carte(fenetre)
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
                "Ferme-le s'il est ouvert dans Word, ou enregistre-le à nouveau en .docx "
                "ou en PDF, puis choisis-le encore.",
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
            "Tu peux choisir un autre CV (un .docx de préférence).",
        )
        cv = ""


def assurer_profil() -> None:
    """Guarantees a profile before opening the application.

    Without a profile: the CV (dropped or chosen), the questions in a form, then the
    profile written by first_launch; the application then starts normally. Everything
    happens in windows, and a failure says why in one.
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
