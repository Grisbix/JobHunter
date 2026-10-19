"""La fenetre principale : App assemble les mixins ; main() lance l'application.

Partie de jobhunter.app (ancien JobHunter.pyw, phase 3.7)."""

import os
import queue
import threading
import tkinter as tk
from tkinter import messagebox
from typing import Any

import customtkinter as ctk

from jobhunter import profil as _profil
from jobhunter import racine as _racine
from jobhunter.app import theme as _theme
from jobhunter.app.actions import ActionsMixin
from jobhunter.app.commun import MAINT, STEPS
from jobhunter.app.detail import DetailMixin
from jobhunter.app.donnees import DonneesMixin
from jobhunter.app.execution import ExecutionMixin
from jobhunter.app.fiche import FicheMixin
from jobhunter.app.panneaux import PanneauxMixin
from jobhunter.app.tableau import TableauMixin
from jobhunter.app.theme import (
    ACC,
    ACC_H,
    ACC_TX,
    BG,
    BTN,
    BTN_H,
    CB,
    CF,
    CL,
    MUT,
    SIDE,
    SIDE_H,
    SIDE_MUT,
    SIDE_TX,
    TX,
    WORK,
    _resoudre_espacements,
    _resoudre_polices,
)


class App(
    TableauMixin,
    DonneesMixin,
    FicheMixin,
    ActionsMixin,
    PanneauxMixin,
    DetailMixin,
    ExecutionMixin,
):
    """La fenetre JobHunter. Chaque mixin porte un domaine ; ils ne se partagent que `self`."""

    def __init__(self, root: Any) -> None:
        _resoudre_polices()  # une fenetre existe : on sait quelles familles sont installees
        _resoudre_espacements(root)
        self.root = root
        self.proc: Any = None
        self.q: Any = queue.Queue()
        # Une exception dans un rappel Tk s'imprime sur stderr. Dans un .pyw il
        # n'y a pas de console : elle part dans le vide, le bouton ne fait rien
        # et rien ne le dit. On la range dans un fichier et on l'affiche.
        root.report_callback_exception = self._panne_tk
        self.offers = []
        self.suivi = {}
        self.rowmap: dict[str, Any] = {}
        self.comptes = {}
        self._search_cache: dict[
            str, Any
        ] = {}  # oid -> texte cherchable (vide a chaque load_offers)
        self._search_termes_actifs = []  # termes REELLEMENT appliques au tableau
        self._search_job = None  # after() en attente (anti-saccade)
        try:
            self.myemail = _profil.identite()["email"]
        except Exception:
            self.myemail = ""
        root.title("Offres — suivi candidatures")
        # 1320x840 n'est PAS la taille d'ouverture : c'est celle qu'on retrouve en
        # de-maximisant. La fenetre s'ouvre maximisee.
        root.geometry("1320x840")
        root.minsize(1080, 680)
        root.configure(fg_color=BG)

        def _maximiser() -> None:
            try:
                root.state("zoomed")
            except Exception:
                try:
                    root.attributes("-zoomed", True)  # repli Linux
                except Exception:
                    pass

        _maximiser()
        # CustomTkinter re-applique SA geometrie apres __init__ (suivi du facteur
        # d'echelle DPI), ce qui de-maximisait la fenetre juste apres l'ouverture.
        # On re-affirme donc une fois la boucle d'evenements demarree. Deux
        # rappels : le premier suffit d'ordinaire, le second couvre un demarrage
        # lent. « zoomed » garde la barre de titre et les controles systeme —
        # c'est bien maximise, pas du plein ecran sans bordure.
        root.after(80, _maximiser)
        root.after(400, _maximiser)

        body = CF(root, bg=BG)
        body.pack(fill="both", expand=True, padx=0, pady=0)
        # Recruitment CRM : navigation permanente, outils secondaires défilants.
        self.sidebar = CF(body, bg=SIDE, width=238, corner_radius=0)
        self.sidebar.pack(side="left", fill="y", padx=0)
        self.sidebar.pack_propagate(False)
        self._sidebar_on = True
        CL(
            self.sidebar, text="JOBHUNTER", fg=SIDE_TX, bg=SIDE, font=(_theme.FONT_UI, 17, "bold")
        ).pack(anchor="w", padx=18, pady=(20, 3))
        CL(
            self.sidebar,
            text="RECHERCHE D'EMPLOI",
            fg=SIDE_MUT,
            bg=SIDE,
            font=(_theme.FONT_UI, 10, "bold"),
        ).pack(anchor="w", padx=18, pady=(0, 18))
        self._nav = {}
        for cle, texte, fn in (
            ("offres", "Offres", self._show_dash),
            ("cv", "Mes CV", self._cv_viewer),
            ("entreprises", "Entreprises", self._companies_panel),
            ("sites", "Sites d'offres", self._sources_panel),
            ("stats", "Statistiques", self._stats_panel),
            ("acces", "Accès", self._acces_panel),
        ):
            b = CB(
                self.sidebar,
                text=texte,
                command=lambda c=cle, f=fn: (f(), self._nav_actif(c)),  # type: ignore[func-returns-value]  # lambda Tk qui enchaine des appels sans valeur
                bg=SIDE,
                fg=SIDE_MUT,
                activebackground=SIDE_H,
                anchor="w",
                font=(_theme.FONT_UI, 13),
            )
            b.pack(fill="x", padx=10, pady=2)
            self._nav[cle] = b
        self._nav_actif("offres")
        CL(
            self.sidebar, text="ACTIONS", fg=SIDE_MUT, bg=SIDE, font=(_theme.FONT_UI, 10, "bold")
        ).pack(anchor="w", padx=18, pady=(18, 4))
        journal = CF(self.sidebar, bg=SIDE, plat=True)
        journal.pack(side="bottom", fill="x")
        self._build_log(journal)
        outils = ctk.CTkScrollableFrame(
            self.sidebar, fg_color=SIDE, corner_radius=0, scrollbar_button_color=SIDE_H
        )
        outils.pack(fill="both", expand=True)
        CB(
            outils,
            text="Actualiser les offres",
            command=self.run_all,
            font=(_theme.FONT_UI, 13, "bold"),
            bg=ACC,
            fg=ACC_TX,
            relief="flat",
            activebackground=ACC_H,
            cursor="hand2",
            pady=8,
        ).pack(fill="x", padx=10, pady=(8, 6))
        for label, color, cmd, tip in STEPS:
            CB(
                outils,
                text=label,
                command=lambda c=cmd, l=label: self.run_step(c, l),
                font=(_theme.FONT_UI, 12),
                bg=SIDE,
                fg=SIDE_MUT,
                relief="flat",
                activebackground=SIDE_H,
                cursor="hand2",
                pady=5,
                anchor="w",
            ).pack(fill="x", padx=10, pady=3)
        # section MAINTENANCE pliée : boutons rarement utiles
        self._maint_on = False
        self.b_maint = CB(
            outils,
            text="Maintenance ▸",
            command=self._toggle_maint,
            bg=SIDE,
            fg=SIDE_MUT,
            relief="flat",
            cursor="hand2",
            activebackground=SIDE_H,
            font=(_theme.FONT_UI, 12),
            anchor="w",
            pady=4,
        )
        self.b_maint.pack(fill="x", padx=10, pady=(6, 0))
        self.maint = CF(outils, bg=SIDE, plat=True)  # rempli, affiché à la demande
        for groupe, items in MAINT:
            CL(
                self.maint,
                text=groupe,
                bg=SIDE,
                fg=SIDE_MUT,
                font=(_theme.FONT_UI, 11, "bold"),
                anchor="w",
            ).pack(fill="x", padx=16, pady=(12, 2))
            for label, cmd in items:
                CB(
                    self.maint,
                    text=label,
                    command=lambda c=cmd, l=label: (
                        self._gen_docs()
                        if c is None
                        else self.mettre_a_jour()
                        if c == "maj"
                        else self.run_step(c, l)
                    ),
                    font=(_theme.FONT_UI, 12),
                    bg=SIDE,
                    fg=SIDE_MUT,
                    relief="flat",
                    activebackground=SIDE_H,
                    cursor="hand2",
                    pady=3,
                    anchor="w",
                ).pack(fill="x", padx=16, pady=2)
        CB(
            outils,
            text="Recharger",
            command=self.load_offers,
            bg=SIDE,
            fg=SIDE_MUT,
            activebackground=SIDE_H,
            relief="flat",
            cursor="hand2",
        ).pack(fill="x", padx=10, pady=(6, 2))

        self.main = CF(body, bg=BG)
        self.main.pack(
            side="left",
            fill="both",
            expand=True,
            padx=_theme.PAD_PAGE,
            pady=(_theme.GAP // 2, _theme.GAP // 2),
        )
        # UNE SEULE REGLE DE NAVIGATION, faute de quoi rien ne dit ou chercher
        # quoi : la barre du haut ne porte que des DESTINATIONS (ou je vais),
        # la barre laterale que des ACTIONS (ce que je fais). « Fermer Chrome »
        # etait une action posee parmi les destinations, et doublonnait deja
        # avec Maintenance > Acces & diagnostic.
        tp = CF(self.main, bg=BG)
        tp.pack(fill="x", pady=(0, _theme.GAP))
        CB(
            tp,
            text="Outils",
            command=self._toggle_sidebar,
            bg=BTN,
            fg=TX,
            relief="flat",
            activebackground=BTN_H,
            cursor="hand2",
            font=(_theme.FONT_UI, 13),
        ).pack(side="left", padx=(2, 0), pady=2)
        # Retour de disposition : voir _dispo_retour.
        self._dispo_pile: list[Any] = []
        self.b_dispo = CB(
            tp,
            text="↶ Retour",
            command=self._dispo_retour,
            bg=BTN,
            fg=MUT,
            relief="flat",
            activebackground=BTN_H,
            cursor="hand2",
            font=(_theme.FONT_UI, 13),
        )
        self.b_dispo.pack(side="left", padx=(8, 0), pady=2)
        # La navigation principale habite la colonne gauche, pas en doublon
        # dans l'en-tête. Cette barre ne garde que le contexte du travail.
        CL(tp, text="Suivi des candidatures", bg=BG, fg=TX, font=(_theme.FONT_UI, 17, "bold")).pack(
            side="left", padx=(20, 0)
        )
        self.nav_context = CL(tp, text="Offres", bg=BG, fg=MUT, font=(_theme.FONT_UI, 12))
        self.nav_context.pack(side="right", padx=(0, 12))
        # Le journal vit dans la barre laterale, REPLIEE au demarrage : tout le
        # travail de fond (auto-enrichissement, relances dues, taches lancees
        # depuis la barre du haut) s'ecrivait dans un panneau que personne ne
        # voit. Cette ligne rend la derniere information toujours lisible.
        footer = CF(self.main, bg=BG, plat=True)
        footer.pack(side="bottom", fill="x", pady=(8, 0))
        self.status = CL(footer, text="", bg=BG, fg=MUT, font=(_theme.FONT_UI, 12), anchor="e")
        self.status.pack(side="left", fill="x", expand=True)
        # dashboard et visionneuse = 2 panneaux DANS la même fenêtre (pas de popup)
        self.dash = CF(self.main, bg=WORK)
        self.dash.pack(fill="both", expand=True)
        self._build_dash(self.dash)
        self.viewer = None  # panneau CV & Lettres, construit au 1er usage
        self._dv = None  # panneau détail offre plein écran
        self._panels: dict[str, Any] = {}  # panneaux Entreprises / Sites d'offres
        # Navigation CRM visible au démarrage ; Outils / Ctrl+B la replie
        # pour les écrans plus étroits. La ligne d'état reste visible.
        self._desc_busy = False
        self.load_offers()
        self.root.after(100, self._drain)
        self._raccourcis()
        # JOBHUNTER_SANS_FOND=1 : aucun travail de fond (scan, descriptions,
        # sync). Pour ouvrir l'app le temps d'une verification visuelle sans
        # declencher un scan au premier retour de focus.
        if os.environ.get("JOBHUNTER_SANS_FOND"):
            act = os.environ.get("JOBHUNTER_ACTION")
            if act:
                self.root.after(1500, lambda: exec(act, {"app": self, "tk": tk}))
            return
        # AUTO : dès qu'il y a des offres sans description, on les récupère en fond (au démarrage
        # + après chaque ajout/rebuild). Aucun bouton — silencieux.
        self.root.after(2500, self._auto_enrich)
        # AUTO : sync docx→pdf + liens (un docx modifié quelque part = pdf/liens réalignés)
        self.root.after(6000, self._auto_sync)
        self.root.after(4000, self._check_relances)  # relances dues → log
        # AUTO : scan des sites entreprises, 2 min apres le lancement puis toutes les 3 h
        self.root.after(120000, self._auto_scrape)
        self.root.bind("<FocusIn>", self._on_focus_scrape, add="+")

    def _raccourcis(self) -> None:
        """Couche clavier sur les actions DEJA existantes — aucune nouvelle.

        448 offres a traiter une par une : chaque aller-retour a la souris est
        un cout paye 448 fois. Les liaisons existantes etaient toutes locales a
        un widget (Entree dans un champ, clic sur le tableau) ; il n'y avait
        aucun raccourci global.
        """
        for touches, action in (
            ("<Escape>", self._show_dash),  # revenir au tableau
            ("<Control-r>", self.load_offers),  # recharger
            ("<F5>", self.run_all),  # TOUT FAIRE
            ("<Control-b>", self._toggle_sidebar),  # replier/ouvrir la barre
            ("<Control-l>", lambda: self.e_url.focus_set()),
            ("<Control-w>", self.stop),  # arreter la tache
            ("<Control-f>", self._focus_search),  # rechercher dans les offres
            ("<Alt-Left>", self._dispo_retour),  # annuler agrandir/retrecir
        ):
            self.root.bind_all(touches, lambda e, f=action: (f(), "break")[1])
        # Raccourcis métier réservés au tableau. bind_all() interceptait aussi
        # Ctrl+A et Ctrl+Z dans les champs de recherche, note et URL : la
        # sélection/annulation native du texte déclenchait une action métier.
        for touches, action in (
            ("<Control-Return>", self._apply_checked),
            ("<Control-a>", lambda: self._check_all(True)),
            ("<Control-d>", lambda: self._check_all(False)),
            ("<Control-z>", self._annuler_dernier),
        ):
            self.tree.bind(touches, lambda e, f=action: (f(), "break")[1])  # type: ignore[misc]  # lambda a parametre par defaut (capture de boucle)
        self._log(
            "Raccourcis : Echap retour · Alt+Gauche annule agrandir/rétrécir · "
            "Ctrl+R recharger · F5 tout faire · "
            "Ctrl+B barre · dans le tableau : Ctrl+Entree postuler, "
            "Ctrl+A/D cocher/decocher, Ctrl+Z annuler · "
            "Ctrl+L coller un lien · Ctrl+W arreter · Suppr pas intéressé" + chr(10)
        )

    def _nav_actif(self, cle: Any) -> None:
        contexte = getattr(self, "nav_context", None)
        if contexte is not None:
            contexte.configure(
                text={
                    "offres": "Offres",
                    "cv": "Mes CV",
                    "entreprises": "Entreprises",
                    "sites": "Sites d'offres",
                    "stats": "Statistiques",
                    "acces": "Accès",
                }.get(cle, cle)
            )
        for c, b in getattr(self, "_nav", {}).items():
            if c == cle:
                b.configure(fg_color=ACC, text_color=ACC_TX, hover_color=ACC_H)
            else:
                b.configure(fg_color=SIDE, text_color=SIDE_MUT, hover_color=SIDE_H)

    def _toggle_maint(self) -> None:
        if self._maint_on:
            self.maint.pack_forget()
            self.b_maint.configure(text="Maintenance ▸")
        else:
            self.maint.pack(fill="x", after=self.b_maint)
            self.b_maint.configure(text="Maintenance ▾")
        self._maint_on = not self._maint_on

    # ── Retour de disposition ──
    # l'utilisateur, 2026-10-07 : un panneau elargi, une colonne etiree, la fiche
    # agrandie ou la barre Outils repliee n'avaient aucun retour arriere — il
    # fallait refaire le geste a la main, au pixel pres. On memorise donc la
    # disposition AVANT chaque geste ; « ↶ Retour » (Alt+Gauche) la remet, et
    # chaque appui remonte d'un geste. Le contenu (suivi, statuts) n'y est
    # pas : c'est Ctrl+Z, dans le tableau.
    def _dispo_etat(self) -> Any:
        etat = {
            "dash": self.dash.winfo_manager() == "pack",
            "barre": bool(getattr(self, "_sidebar_on", True)),
        }
        try:
            etat["split"] = self._offer_split.sash_coord(0)[0]
        except Exception:
            pass
        try:
            etat["cols"] = {c: int(self.tree.column(c, "width")) for c in self._visible_cols}
        except Exception:
            pass
        return etat

    def _dispo_memo(self, etat: Any = None) -> None:
        """Empile la disposition `etat` (par defaut : l'actuelle)."""
        etat = etat or self._dispo_etat()
        if not self._dispo_pile or self._dispo_pile[-1] != etat:
            self._dispo_pile.append(etat)
            del self._dispo_pile[:-30]
        self._dispo_maj_bouton()

    def _dispo_maj_bouton(self) -> None:
        try:
            self.b_dispo.configure(fg=TX if self._dispo_pile else MUT)
        except Exception:
            pass

    def _dispo_retour(self) -> None:
        if not self._dispo_pile:
            self._log("Retour : aucune disposition à rétablir.\n")
            return
        e = self._dispo_pile.pop()
        if e.get("dash") and self.dash.winfo_manager() != "pack":
            self._show_dash()
        if e.get("barre") != self._sidebar_on:
            self._toggle_sidebar(memo=False)
        # Le tableau doit etre affiche et mesure avant de replacer le separateur.
        self.root.update_idletasks()
        if "split" in e:
            try:
                self._offer_split.sash_place(0, e["split"], self._offer_split.sash_coord(0)[1])
            except Exception:
                pass
        for c, w in (e.get("cols") or {}).items():
            try:
                self.tree.column(c, width=w)
            except Exception:
                pass
        self._dispo_maj_bouton()

    def _dispo_suivre(self, widget: Any) -> None:
        """Memorise la disposition d'avant tout glisser sur `widget`
        (separateur de panneaux, bord d'une colonne)."""

        def _avant(_e: Any) -> None:
            self._dispo_avant = self._dispo_etat()

        def _apres(_e: Any) -> None:
            avant = getattr(self, "_dispo_avant", None)
            if avant is not None and avant != self._dispo_etat():
                self._dispo_memo(avant)
            self._dispo_avant = None

        widget.bind("<ButtonPress-1>", _avant, add="+")
        widget.bind("<ButtonRelease-1>", _apres, add="+")

    def _toggle_sidebar(self, memo: Any = True) -> None:
        if memo and hasattr(self, "_dispo_pile"):
            self._dispo_memo()
        if self._sidebar_on:
            self.sidebar.pack_forget()
        else:
            self.sidebar.pack(side="left", fill="y", padx=0, before=self.main)
        self._sidebar_on = not self._sidebar_on


def _annonce_mise_a_jour(root: Any, app: Any) -> None:
    """Au demarrage, en arriere-plan : une version plus recente sur GitHub ?
    Au plus une verification par jour ; hors ligne, rien ne s'affiche."""

    def proposer(v: Any, installee: Any) -> None:
        if messagebox.askyesno(
            "JobHunter — mise à jour disponible",
            f"La version {v} est disponible (installée : {installee}).\n\n"
            "L'installer maintenant ? Ton profil, ton CV, tes lettres et ton suivi ne "
            "sont pas touchés, et la version d'avant est sauvegardée.",
            parent=root,
        ):
            app.mettre_a_jour()

    def verifier() -> None:
        try:
            from jobhunter.programmes import mise_a_jour

            v = mise_a_jour.nouvelle_version()
            installee = mise_a_jour.version_locale()
        except Exception:
            v = None
        if v:
            root.after(0, lambda: proposer(v, installee))

    threading.Thread(target=verifier, daemon=True).start()


def main() -> None:
    _racine.exporter_paquet()  # les etapes lancent `python -m jobhunter...`
    r = ctk.CTk()
    a = App(r)
    _annonce_mise_a_jour(r, a)
    r.mainloop()
