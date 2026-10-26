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


def demander_cv(fenetre: tk.Tk) -> str:
    """The welcome window: drop the CV on it, or choose it. "" = later."""
    choix = {"cv": ""}
    fenetre.title("JobHunter — bienvenue")
    cadre = tk.Frame(fenetre, padx=28, pady=22)
    cadre.pack()
    tk.Label(
        cadre,
        text="Aucun profil pour l'instant.\n\nDonne ton CV (.docx de préférence, ou .pdf) : "
        "JobHunter le lit\npuis te pose quelques questions.",
        justify="left",
    ).pack(anchor="w")
    zone = tk.Label(cadre, text="Dépose ton CV ici", relief="groove", padx=60, pady=34)
    zone.pack(fill="x", pady=14)

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
    boutons = tk.Frame(cadre)
    boutons.pack(fill="x")
    tk.Button(boutons, text="Choisir mon CV…", command=choisir).pack(side="left")
    tk.Button(boutons, text="Plus tard", command=lambda: fin("")).pack(side="right")
    fenetre.protocol("WM_DELETE_WINDOW", lambda: fin(""))
    fenetre.deiconify()
    fenetre.mainloop()
    cadre.destroy()
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


def demander_reponses(fenetre: tk.Tk, cv: str, texte: str) -> dict[str, Any] | str | None:
    """The form prefilled from the CV. Its answers, "autre" for another CV, None = later."""
    from jobhunter.programs import first_launch as _premier
    from jobhunter.scoring import zones

    prop = _premier.propositions(texte)
    secteurs = list(zones.CATALOGUE)
    fenetre.title("JobHunter — ton profil")
    cadre = tk.Frame(fenetre, padx=24, pady=18)
    cadre.pack(fill="both", expand=True)
    tk.Label(cadre, text=f"CV lu : {Path(cv).name}", font=("Segoe UI", 10, "bold")).grid(
        row=0, column=0, columnspan=2, sticky="w"
    )
    ligne = 1
    if len(texte.strip()) < PEU_DE_TEXTE:
        tk.Label(
            cadre,
            fg="#b3261e",
            justify="left",
            wraplength=520,
            text="Presque rien n'a pu être lu dans ce CV : il est sans doute scanné ou "
            "enregistré en image. Choisis plutôt un .docx, ou un PDF exporté depuis Word ; "
            "sinon, remplis au moins les métiers visés.",
        ).grid(row=ligne, column=0, columnspan=2, sticky="w", pady=(6, 0))
        ligne += 1
    tk.Label(
        cadre, text="Vérifie et complète : rien n'est écrit tant que tu n'as pas validé."
    ).grid(row=ligne, column=0, columnspan=2, sticky="w", pady=(6, 10))
    ligne += 1
    champs: dict[str, tk.StringVar] = {}
    for cle, libelle in (
        ("prenom", "Prénom"),
        ("nom", "Nom"),
        ("email", "Email"),
        ("telephone", "Téléphone"),
        ("ville", "Ville"),
        ("metiers", "Métiers visés (séparés par des virgules)"),
    ):
        champs[cle] = tk.StringVar(value=str(prop.get(cle) or ""))
        tk.Label(cadre, text=libelle).grid(row=ligne, column=0, sticky="w", pady=2)
        tk.Entry(cadre, textvariable=champs[cle], width=52).grid(
            row=ligne, column=1, sticky="we", pady=2
        )
        ligne += 1
    annees = tk.StringVar(value=str(prop["annees"]))
    tk.Label(cadre, text="Années d'expérience (stages compris)").grid(
        row=ligne, column=0, sticky="w"
    )
    tk.Spinbox(cadre, from_=0, to=50, textvariable=annees, width=6).grid(
        row=ligne, column=1, sticky="w"
    )
    ligne += 1
    genre = tk.StringVar(value=prop["genre"])
    tk.Label(cadre, text="Accords dans les lettres").grid(row=ligne, column=0, sticky="w")
    accords = tk.Frame(cadre)
    accords.grid(row=ligne, column=1, sticky="w")
    tk.Radiobutton(accords, text="« diplômé »", variable=genre, value="m").pack(side="left")
    tk.Radiobutton(accords, text="« diplômée »", variable=genre, value="f").pack(side="left")
    ligne += 1

    listes = {}
    for cle, libelle, choisis in (
        ("prioritaires", "Secteurs prioritaires", prop["prioritaires"]),
        ("secondaires", "Secteurs secondaires (facultatif)", []),
    ):
        tk.Label(cadre, text=libelle).grid(row=ligne, column=0, sticky="nw", pady=(6, 0))
        lb = tk.Listbox(cadre, selectmode="multiple", height=5, exportselection=False)
        for i, s in enumerate(secteurs):
            lb.insert("end", str(zones.CATALOGUE[s].get("libelle") or s))
            if s in choisis:
                lb.selection_set(i)
                lb.see(i)
        lb.grid(row=ligne, column=1, sticky="we", pady=(6, 0))
        listes[cle] = lb
        ligne += 1
    entreprises = tk.BooleanVar(value=bool(prop["entreprises"]))
    tk.Checkbutton(
        cadre, text="Suivre les ~90 entreprises de finance / ESG proposées", variable=entreprises
    ).grid(row=ligne, column=0, columnspan=2, sticky="w", pady=(8, 0))
    ligne += 1
    erreur = tk.Label(cadre, fg="#b3261e", text="")
    erreur.grid(row=ligne, column=0, columnspan=2, sticky="w")
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
            **{k: [secteurs[i] for i in lb.curselection()] for k, lb in listes.items()},  # type: ignore[no-untyped-call]
        }
        fenetre.quit()

    def fin(r: str | None) -> None:
        choix["r"] = r
        fenetre.quit()

    boutons = tk.Frame(cadre)
    boutons.grid(row=ligne, column=0, columnspan=2, sticky="we", pady=(12, 0))
    tk.Button(boutons, text="Créer mon profil", command=valider).pack(side="left")
    tk.Button(boutons, text="Choisir un autre CV…", command=lambda: fin("autre")).pack(
        side="left", padx=8
    )
    tk.Button(boutons, text="Plus tard", command=lambda: fin(None)).pack(side="right")
    fenetre.protocol("WM_DELETE_WINDOW", lambda: fin(None))
    fenetre.deiconify()
    fenetre.mainloop()
    cadre.destroy()
    fenetre.withdraw()
    reponse: dict[str, Any] | str | None = choix["r"]
    return reponse


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


def profil_guide(fenetre: tk.Tk, cv: str = "") -> bool:
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
        attente = tk.Toplevel(fenetre)
        attente.title("JobHunter")
        tk.Label(attente, text="Création du profil…", padx=40, pady=24).pack()
        attente.update()
        ok, sortie = creer_profil(cv, rep)
        attente.destroy()
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
    _r = tk.Tk()
    _r.withdraw()
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
    r = tk.Tk()
    r.withdraw()
    try:
        return 0 if profil_guide(r, args[0] if args else "") else 1
    finally:
        r.destroy()


if __name__ == "__main__":
    sys.exit(main())
