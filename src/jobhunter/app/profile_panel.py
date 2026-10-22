"""The "Profil" panel: the profiles, the fit of the active one, its skills.

Three tabs:
  - Profils: every profile, the active one marked; open (JobHunter restarts on it),
    rename, archive (nothing is deleted); a CV dropped on this tab, or chosen, creates
    a new profile (profiles_menu._nouveau_profil: workspace + guided first launch);
  - Fit: the weights of the fit, with their effect on the queue (fit_panel);
  - Compétences: the active profile's skills, the words searched for each in the
    postings and the axes they count for (jobhunter.skills_settings).
Fit and skills belong to the ACTIVE profile: another profile is edited by opening it.
Nothing is written before "Enregistrer"; the previous profile is kept as `.bak`.
"""

import json
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from typing import TYPE_CHECKING, Any

import customtkinter as ctk

from jobhunter import profile as _profil
from jobhunter import profiles as _profils
from jobhunter import search_settings as _reglages
from jobhunter import skills_settings as _comp
from jobhunter.app import theme as _theme
from jobhunter.app.common import PY
from jobhunter.app.language import t as _t
from jobhunter.app.profiles_menu import nom_affiche
from jobhunter.app.theme import (
    ACC,
    ACC_H,
    ACC_TX,
    BG,
    BTN,
    BTN_H,
    CARD,
    CB,
    CF,
    CL,
    DEL,
    LINE,
    MUT,
    TX,
    WORK,
)

if TYPE_CHECKING:
    from jobhunter.app._app_type import AppTypee

ONGLETS = ("Profils", "Fit", "Compétences")


def _boutons(parent: Any, specs: tuple[tuple[str, Any, bool], ...]) -> None:
    for texte, cmd, principal in specs:
        CB(
            parent,
            text=texte,
            command=cmd,
            bg=ACC if principal else BTN,
            fg=ACC_TX if principal else TX,
            activebackground=ACC_H if principal else BTN_H,
            relief="flat",
            cursor="hand2",
        ).pack(side="left", padx=(0, 12))


def _proposer_rescore(app: "AppTypee") -> None:
    if messagebox.askyesno(
        "JobHunter",
        _t(
            "Recalculer maintenant le fit enregistré de chaque offre de ta file ? "
            "Le tableau et le tri l'utilisent."
        ),
        parent=app.root,
    ):
        app.run_step([PY, "-m", "jobhunter.programs.rescore_ats"], _t("Recalculer le fit"))


class ProfilPanneauMixin:
    def _profil_panel(self: "AppTypee", onglet: str | None = None) -> None:
        self._hide_all()
        if "profil" not in self._panels:
            self._construire_profil()
        w = self._panels["profil"]
        w.pack(fill="both", expand=True)
        w._montrer(onglet or w._onglet)

    def _construire_profil(self: "AppTypee") -> None:
        w = CF(self.main, bg=WORK)
        self._panels["profil"] = w
        top = CF(w, bg=BG)
        top.pack(fill="x")
        CB(
            top,
            text="Offres",
            command=self._show_dash,
            bg=BTN,
            fg=MUT,
            relief="flat",
            cursor="hand2",
            font=(_theme.FONT_UI, 13),
        ).pack(side="left", padx=12, pady=(2, 0))
        CL(top, text="Profil", bg=BG, fg=TX, font=(_theme.FONT_UI, 16)).pack(side="left", padx=28)
        actif_lbl = CL(top, text="", bg=BG, fg=MUT)
        actif_lbl.pack(side="left")
        choix = ctk.CTkSegmentedButton(
            w,
            values=[_t(o) for o in ONGLETS],
            command=lambda v: montrer(ONGLETS[[_t(o) for o in ONGLETS].index(v)]),
            selected_color=ACC,
            selected_hover_color=ACC_H,
            font=ctk.CTkFont(_theme.FONT_UI, 13),
        )
        choix.pack(anchor="w", padx=28, pady=(12, 4))
        contenu = CF(w, bg=WORK, plat=True)
        contenu.pack(fill="both", expand=True)
        onglets: dict[str, Any] = {}
        w._onglet = "Profils"
        w._fit_a_relire = False

        def montrer(nom: str) -> None:
            w._onglet = nom
            choix.set(_t(nom))
            actif = next((p for p in _profils.liste() if p.slug == _profils.actif()), None)
            actif_lbl.configure(
                text=_t("profil actif : {nom}").format(nom=nom_affiche(actif)) if actif else ""
            )
            for f in onglets.values():
                f.pack_forget()
            if nom not in onglets:
                onglets[nom] = {
                    "Profils": self._onglet_profils,
                    "Fit": self._construire_fit,
                    "Compétences": self._onglet_competences,
                }[nom](contenu)
            f = onglets[nom]
            f.pack(fill="both", expand=True)
            self._depot_vers_profil = nom == "Profils"
            if nom == "Fit":
                f._reload(relire_file=w._fit_a_relire)
                w._fit_a_relire = False
            else:
                f._reload()

        w._montrer = montrer
        w._onglets = onglets

    # ── Profils ────────────────────────────────────────────────────────────────
    def _onglet_profils(self: "AppTypee", parent: Any) -> Any:
        w = CF(parent, bg=WORK, plat=True)
        CL(
            w,
            text=_t(
                "Un profil = une recherche complète : sa file d'offres, ses candidatures, "
                "ses CV et lettres, ses réglages. Ouvrir un autre profil redémarre JobHunter "
                "dessus ; un profil archivé est rangé, jamais supprimé."
            ),
            bg=WORK,
            fg=MUT,
            anchor="w",
            justify="left",
            wraplength=820,
        ).pack(fill="x", padx=28, pady=(6, 8))
        liste = CF(w, bg=CARD)
        liste.pack(fill="x", padx=28)
        depot = CF(w, bg=CARD, highlightbackground=ACC, highlightthickness=1)
        depot.pack(fill="x", padx=28, pady=(16, 4))
        zone = CL(
            depot,
            text="",
            bg=CARD,
            fg=ACC,
            font=(_theme.FONT_UI, 14),
            justify="center",
        )
        zone.pack(fill="x", padx=20, pady=(22, 6))
        CB(
            depot,
            text="Choisir un CV…",
            command=lambda: self._nouveau_profil(),
            bg=BTN,
            fg=TX,
            relief="flat",
            cursor="hand2",
        ).pack(pady=(0, 20))
        message = CL(w, text="", bg=WORK, fg=MUT, anchor="w", justify="left", wraplength=900)
        message.pack(fill="x", padx=28, pady=(6, 12))

        def renommer(p: _profils.Profil) -> None:
            nom = ctk.CTkInputDialog(
                text=_t("Nouveau nom du profil"), title="JobHunter"
            ).get_input()
            if not nom or not nom.strip():
                return
            _profils.renommer(p.slug, nom)
            if p.slug == _profils.actif() and self._nom_profil_lbl is not None:
                self._nom_profil_lbl.configure(text="● " + " ".join(nom.split()))
            recharger()

        def archiver(p: _profils.Profil) -> None:
            if p.slug == _profils.actif():
                self._archiver_profil()  # the active one: archived, then back to main
                return
            if not messagebox.askyesno(
                "JobHunter",
                _t(
                    "Archiver « {nom} » ? Son dossier est rangé dans profiles/_archives : "
                    "rien n'est supprimé."
                ).format(nom=nom_affiche(p)),
                parent=self.root,
            ):
                return
            try:
                dest = _profils.archiver(p.slug)
            except RuntimeError:
                messagebox.showwarning(
                    "JobHunter",
                    _t("Une collecte tourne pour ce profil : réessaie quand elle aura fini."),
                    parent=self.root,
                )
                return
            message.configure(text=_t("Profil archivé : {d}").format(d=dest))
            recharger()

        def ligne(p: _profils.Profil, actif: bool, premier: bool) -> None:
            if not premier:
                tk.Frame(liste, height=1, bg=LINE).pack(fill="x", padx=14)
            r = CF(liste, bg=CARD, plat=True)
            r.pack(fill="x", padx=14, pady=8)
            infos = CF(r, bg=CARD, plat=True)
            infos.pack(side="left", fill="x", expand=True)
            CL(
                infos,
                text=("● " if actif else "○ ") + nom_affiche(p),
                bg=CARD,
                fg=ACC if actif else TX,
                font=(_theme.FONT_UI, 14, "bold" if actif else "normal"),
                anchor="w",
            ).pack(fill="x")
            detail = _t("profil actif") if actif else _t("profil principal") if not p.slug else ""
            CL(
                infos,
                text=(detail + " · " if detail else "") + str(p.racine),
                bg=CARD,
                fg=MUT,
                anchor="w",
            ).pack(fill="x")
            specs: list[tuple[str, Any, Any]] = []
            if not actif:
                specs.append(("Ouvrir", lambda: self._changer_profil(p.slug), ACC))
            specs.append(("Renommer…", lambda: renommer(p), BTN))
            if p.slug:  # the main profile is the installation's folder
                specs.append(("Archiver…", lambda: archiver(p), DEL))
            for texte, cmd, fond in reversed(specs):
                CB(r, text=texte, command=cmd, bg=fond, relief="flat", cursor="hand2").pack(
                    side="right", padx=(8, 0)
                )

        def recharger() -> None:
            for x in liste.winfo_children():
                x.destroy()
            actif = _profils.actif()
            for i, p in enumerate(_profils.liste()):
                ligne(p, p.slug == actif, i == 0)
            zone.configure(
                text=_t("Dépose un CV ici (.docx ou .pdf) pour créer un nouveau profil")
                if self._depot_cv
                else _t("Nouveau profil : choisis le CV (.docx ou .pdf) dont il partira")
            )

        w._reload = recharger
        return w

    # ── Compétences ────────────────────────────────────────────────────────────
    def _onglet_competences(self: "AppTypee", parent: Any) -> Any:
        w = CF(parent, bg=WORK, plat=True)
        CL(
            w,
            text=_t(
                "Chaque compétence est reconnue dans une annonce par les mots cherchés. "
                "Elle compte pour le fit dans les axes cochés ; sans axe, elle sert au CV et "
                "aux lettres sans monter le fit. Rien n'est écrit avant « Enregistrer »."
            ),
            bg=WORK,
            fg=MUT,
            anchor="w",
            justify="left",
            wraplength=820,
        ).pack(fill="x", padx=28, pady=(6, 8))
        # The buttons first, at the bottom: packed after a list that expands, they
        # went out of the window.
        message = CL(w, text="", bg=WORK, fg=MUT, anchor="w", justify="left", wraplength=820)
        message.pack(side="bottom", fill="x", padx=28, pady=(0, 12))
        barre = CF(w, bg=WORK, plat=True)
        barre.pack(side="bottom", fill="x", padx=28, pady=(10, 2))
        corps = CF(w, bg=WORK, plat=True)
        corps.pack(fill="both", expand=True, padx=28)
        corps.columnconfigure(0, weight=3, uniform="c")
        corps.columnconfigure(1, weight=2, uniform="c")
        corps.rowconfigure(0, weight=1)

        cadre = CF(corps, bg=CARD)
        cadre.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        tv = ttk.Treeview(cadre, columns=("nom", "axes", "mots"), show="headings")
        for k, lbl, larg in (
            ("nom", "Compétence", 300),
            ("axes", "Axes", 90),
            ("mots", "Mots cherchés", 300),
        ):
            tv.heading(k, text=_t(lbl))
            tv.column(k, width=larg, stretch=(k == "mots"))
        barre_tv = ttk.Scrollbar(cadre, orient="vertical", command=tv.yview)
        tv.configure(yscrollcommand=barre_tv.set)
        barre_tv.pack(side="right", fill="y", pady=8, padx=(0, 6))
        tv.pack(fill="both", expand=True, padx=(8, 0), pady=8)

        ed = CF(corps, bg=CARD)
        ed.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        CL(
            ed, text="Compétence", bg=CARD, fg=TX, font=(_theme.FONT_UI, 12, "bold"), anchor="w"
        ).pack(fill="x", padx=14, pady=(12, 0))
        e_nom = ctk.CTkEntry(ed, font=(_theme.FONT_UI, 12))
        e_nom.pack(fill="x", padx=14)
        CL(
            ed,
            text="Compte pour les axes",
            bg=CARD,
            fg=TX,
            font=(_theme.FONT_UI, 12, "bold"),
            anchor="w",
        ).pack(fill="x", padx=14, pady=(10, 0))
        cases_f = CF(ed, bg=CARD, plat=True)
        cases_f.pack(fill="x", padx=14)
        CL(
            ed,
            text="Mots cherchés dans les annonces (un par ligne)",
            bg=CARD,
            fg=TX,
            font=(_theme.FONT_UI, 12, "bold"),
            anchor="w",
        ).pack(fill="x", padx=14, pady=(10, 0))
        # The buttons and the English name anchored at the bottom: the words box takes
        # what is left, the buttons never go out of the card.
        lbl_en = CL(
            ed,
            text="Nom en anglais (CV et lettres en anglais)",
            bg=CARD,
            fg=TX,
            font=(_theme.FONT_UI, 12, "bold"),
            anchor="w",
        )
        e_en = ctk.CTkEntry(ed, font=(_theme.FONT_UI, 12))
        actions = CF(ed, bg=CARD, plat=True)
        actions.pack(side="bottom", fill="x", padx=14, pady=12)
        e_en.pack(side="bottom", fill="x", padx=14)
        lbl_en.pack(side="bottom", fill="x", padx=14, pady=(10, 0))
        b_mots = ctk.CTkTextbox(ed, height=60, font=(_theme.FONT_UI, 12))
        b_mots.pack(fill="both", expand=True, padx=14)

        etat: dict[str, Any] = {"liste": [], "enregistre": [], "profil": {}, "courant": None}
        cases: dict[str, Any] = {}

        def brut() -> dict[str, Any]:
            return dict(json.loads(Path(_profil.FICHIER).read_text(encoding="utf-8")))

        def remplir_tv() -> None:
            tv.delete(*tv.get_children())
            for i, c in enumerate(etat["liste"]):
                tv.insert(
                    "",
                    "end",
                    iid=str(i),
                    values=(c.nom, ", ".join(c.axes) or "—", ", ".join(c.synonymes)),
                )

        def editer(i: int | None) -> None:
            etat["courant"] = i
            c = etat["liste"][i] if i is not None else None
            e_nom.configure(state="normal")
            e_nom.delete(0, "end")
            b_mots.delete("1.0", "end")
            e_en.delete(0, "end")
            for a, v in cases.items():
                v.set(bool(c and a in c.axes))
            if c is not None:
                e_nom.insert(0, c.nom)
                b_mots.insert("1.0", "\n".join(c.synonymes))
                e_en.insert(0, c.en)
                # never renamed here: letters, CV facts and base skills refer to the name
                if c.nom in {x.nom for x in etat["enregistre"]}:
                    e_nom.configure(state="disabled")

        def lu() -> _comp.Competence:
            ancien = etat["liste"][etat["courant"]] if etat["courant"] is not None else None
            return _comp.Competence(
                nom=" ".join(e_nom.get().split()),
                axes=[a for a, v in cases.items() if v.get()],
                synonymes=_comp.depuis_texte(b_mots.get("1.0", "end")),
                en=e_en.get().strip(),
                autres=dict(ancien.autres) if ancien else {},
            )

        def appliquer_ed() -> None:
            c = lu()
            if not c.nom:
                message.configure(text=_t("Donne un nom à la compétence."))
                return
            if etat["courant"] is None:
                etat["liste"].append(c)
                etat["courant"] = len(etat["liste"]) - 1
            else:
                etat["liste"][etat["courant"]] = c
            remplir_tv()
            tv.selection_set(str(etat["courant"]))
            tv.see(str(etat["courant"]))
            message.configure(text=_t("Modifié dans la liste : « Enregistrer » pour le garder."))

        def nouvelle() -> None:
            tv.selection_remove(*tv.selection())
            editer(None)
            e_nom.focus_set()

        def retirer() -> None:
            i = etat["courant"]
            if i is None:
                return
            del etat["liste"][i]
            remplir_tv()
            editer(None)
            message.configure(text=_t("Retirée de la liste : « Enregistrer » pour le garder."))

        def choisie(_e: Any) -> None:
            sel = tv.selection()
            if sel:
                editer(int(sel[0]))

        tv.bind("<<TreeviewSelect>>", choisie)
        _boutons(
            actions,
            (
                ("Appliquer", appliquer_ed, True),
                ("Nouvelle", nouvelle, False),
                ("Retirer", retirer, False),
            ),
        )

        def recharger() -> None:
            try:
                _profil.recharger()
                p = brut()
            except (OSError, ValueError) as e:
                message.configure(text=f"! {type(e).__name__}: {e}")
                return
            etat["profil"] = p
            etat["liste"] = _comp.lire(p)
            etat["enregistre"] = _comp.lire(p)
            for x in cases_f.winfo_children():
                x.destroy()
            cases.clear()
            for i, a in enumerate(_comp.axes(p)):
                v = tk.BooleanVar(value=False)
                ctk.CTkCheckBox(
                    cases_f,
                    text=a.upper() if len(a) <= 3 else a.capitalize(),
                    variable=v,
                    fg_color=ACC,
                    hover_color=ACC_H,
                    font=(_theme.FONT_UI, 12),
                ).grid(row=i // 3, column=i % 3, sticky="w", padx=(0, 12), pady=2)
                cases[a] = v
            remplir_tv()
            editer(None)
            message.configure(
                text=_t("{n} compétences dans le profil actif.").format(n=len(etat["liste"]))
            )

        def enregistrer() -> None:
            liste = etat["liste"]
            if liste == etat["enregistre"]:
                message.configure(text=_t("Rien à enregistrer."))
                return
            p = brut()
            if erreurs := _comp.valider(liste, p):
                messagebox.showwarning(
                    "JobHunter",
                    _t("Rien n'est enregistré :") + "\n· " + "\n· ".join(erreurs),
                    parent=self.root,
                )
                return
            bak = _reglages.ecrire(Path(_profil.FICHIER), _comp.appliquer(p, liste))
            recharger()
            self._panels["profil"]._fit_a_relire = True  # the axes of the offers changed
            texte = _t("Compétences enregistrées (profil d'avant : {bak}).").format(bak=bak.name)
            message.configure(text=texte)
            self._log(texte + "\n")
            _proposer_rescore(self)

        _boutons(
            barre,
            (
                ("Enregistrer", enregistrer, True),
                ("Annuler les modifications", recharger, False),
            ),
        )
        w._reload = recharger
        # for the tests
        w._etat, w._editer, w._appliquer, w._enregistrer = etat, editer, appliquer_ed, enregistrer
        w._champs = (e_nom, cases, b_mots, e_en)
        return w
