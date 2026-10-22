"""The main window: App assembles the mixins; main() launches the application.

Part of jobhunter.app (former JobHunter.pyw, phase 3.7)."""

import os
import queue
import sys
import threading
import tkinter as tk
from tkinter import messagebox
from typing import Any

import customtkinter as ctk

from jobhunter import frozen as _gele
from jobhunter import profile as _profil
from jobhunter import root as _racine
from jobhunter.app import compare as _comparer
from jobhunter.app import mail as _courriels
from jobhunter.app import recipes as _recettes
from jobhunter.app import theme as _theme
from jobhunter.app.actions import ActionsMixin
from jobhunter.app.apply_panel import CandidatureMixin
from jobhunter.app.card import FicheMixin
from jobhunter.app.common import MAINT, STEPS
from jobhunter.app.cv_drop import DepotCvMixin
from jobhunter.app.data import DonneesMixin
from jobhunter.app.detail import DetailMixin
from jobhunter.app.execution import ExecutionMixin
from jobhunter.app.fit_panel import FitMixin
from jobhunter.app.language import t as _t
from jobhunter.app.my_search import MaRechercheMixin
from jobhunter.app.panels import PanneauxMixin
from jobhunter.app.profile_panel import ProfilPanneauMixin
from jobhunter.app.profiles_menu import ProfilsMixin, nom_actif
from jobhunter.app.table import TableauMixin
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
    SIDE_CARD,
    SIDE_H,
    SIDE_MUT,
    SIDE_TX,
    TX,
    WORK,
    _resoudre_espacements,
    _resoudre_polices,
)
from jobhunter.welcome import activer_depot as _activer_depot


class App(
    TableauMixin,
    DonneesMixin,
    FicheMixin,
    ActionsMixin,
    PanneauxMixin,
    DetailMixin,
    ExecutionMixin,
    CandidatureMixin,
    DepotCvMixin,
    ProfilsMixin,
    MaRechercheMixin,
    FitMixin,
    ProfilPanneauMixin,
):
    """The JobHunter window. Each mixin carries a domain; they share nothing but `self`."""

    def __init__(self, root: Any) -> None:
        _resoudre_polices()  # a window exists: we know which font families are installed
        _resoudre_espacements(root)
        self.root = root
        self.proc: Any = None
        # Candidatures panel (app/apply_panel.py): piloted program and its widgets
        self._cand_proc: Any = None
        self._cand_win: Any = None
        self._cand_lbl: dict[str, Any] = {}
        self._cand_boutons: list[Any] = []
        self.q: Any = queue.Queue()
        # An exception in a Tk callback is printed on stderr. In a .pyw there
        # is no console: it goes into the void, the button does nothing
        # and nothing says so. We store it in a file and display it.
        root.report_callback_exception = self._panne_tk
        self.offers = []
        self.suivi = {}
        self.rowmap: dict[str, Any] = {}
        self.comptes = {}
        self._search_cache: dict[
            str, Any
        ] = {}  # oid -> searchable text (emptied at each load_offers)
        self._search_termes_actifs = []  # terms REALLY applied to the table
        self._search_job = None  # pending after() (anti-stutter)
        try:
            self.myemail = _profil.identite()["email"]
        except Exception:
            self.myemail = ""
        root.title("JobHunter — " + (nom_actif() or _t("Principal")))
        # 1320x840 is NOT the opening size: it is the one found again when
        # un-maximising. The window opens maximised.
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
        # CustomTkinter re-applies ITS geometry after __init__ (tracking of the DPI
        # scaling factor), which un-maximised the window just after opening.
        # So we re-assert it once the event loop has started. Two
        # callbacks: the first is usually enough, the second covers a slow
        # start. "zoomed" keeps the title bar and the system controls —
        # it is indeed maximised, not borderless full screen.
        root.after(80, _maximiser)
        root.after(400, _maximiser)

        body = CF(root, bg=BG)
        body.pack(fill="both", expand=True, padx=0, pady=0)
        # Recruitment CRM: permanent navigation, scrolling secondary tools.
        self.sidebar = CF(body, bg=SIDE, width=238, corner_radius=0)
        self.sidebar.pack(side="left", fill="y", padx=0)
        self.sidebar.pack_propagate(False)
        self._sidebar_on = True
        tete = CF(self.sidebar, bg=SIDE, plat=True)
        tete.pack(fill="x", padx=(18, 8), pady=(20, 3))
        CL(tete, text="JOBHUNTER", fg=SIDE_TX, bg=SIDE, font=(_theme.FONT_UI, 17, "bold")).pack(
            side="left"
        )
        # Folds the menu where the eye already is; ☰ Menu in the top bar opens it again.
        CB(
            tete,
            text="«",
            command=self._toggle_sidebar,
            bg=SIDE,
            fg=SIDE_MUT,
            activebackground=SIDE_H,
            width=34,
            font=(_theme.FONT_UI, 16),
        ).pack(side="right")
        # THE ACTIVE PROFILE, always named at the top left: the whole window (queue,
        # CVs, letters, settings, fit) belongs to it. A click opens the Profil panel,
        # where another profile is opened or created.
        CL(
            self.sidebar,
            text="PROFIL ACTIF",
            fg=SIDE_MUT,
            bg=SIDE,
            font=(_theme.FONT_UI, 10, "bold"),
        ).pack(anchor="w", padx=18, pady=(0, 2))
        self._nom_profil_lbl = CB(
            self.sidebar,
            text="● " + (nom_actif() or _t("Principal")),
            command=lambda: (self._profil_panel("Profils"), self._nav_actif("profil")),  # type: ignore[func-returns-value]  # Tk lambda chaining calls without a value
            cursor="hand2",
            bg=SIDE_CARD,
            fg=SIDE_TX,
            activebackground=SIDE_H,
            relief="flat",
            font=(_theme.FONT_UI, 14, "bold"),
            anchor="w",
        )
        self._nom_profil_lbl.pack(fill="x", padx=12, pady=(0, 16))
        self._nav = {}
        for cle, texte, fn in (
            ("offres", "Offres", self._show_dash),
            ("recherche", "Ma recherche", self._ma_recherche_panel),
            ("profil", "Profil", self._profil_panel),
            ("cv", "Mes CV", self._cv_viewer),
            ("entreprises", "Entreprises", self._companies_panel),
            ("sites", "Sites d'offres", self._sources_panel),
            ("stats", "Statistiques", self._stats_panel),
            ("acces", "Accès", self._acces_panel),
        ):
            b = CB(
                self.sidebar,
                text=texte,
                command=lambda c=cle, f=fn: (f(), self._nav_actif(c)),  # type: ignore[func-returns-value]  # Tk lambda chaining calls without a value
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
        # The morning collection in one line — fresh, running, stopped or missed — and
        # the button to start it when it did not happen (jobhunter.collect_state).
        self._collecte_lbl = CL(
            outils,
            text="",
            bg=SIDE,
            fg=SIDE_MUT,
            font=(_theme.FONT_UI, 11),
            anchor="w",
            justify="left",
            wraplength=230,
        )
        self._collecte_lbl.pack(fill="x", padx=12, pady=(0, 4))
        self._collecte_btn = CB(
            outils,
            text="Lancer la collecte du matin",
            command=self._lancer_collecte,
            font=(_theme.FONT_UI, 12),
            bg=SIDE_CARD,
            fg=SIDE_TX,
            relief="flat",
            activebackground=SIDE_H,
            cursor="hand2",
            pady=5,
        )
        self.root.after(1500, self._maj_collecte)
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
        # MAINTENANCE section folded: buttons rarely useful
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
        self.maint = CF(outils, bg=SIDE, plat=True)  # filled in, displayed on demand
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
                        else self._basculer_langue()
                        if c == "langue"
                        else self._planifier()
                        if c == "planifier"
                        else _courriels.ouvrir(self)
                        if c == "courriels"
                        else self._menu_profils()
                        if c == "profils"
                        else _comparer.ouvrir(self)
                        if c == "comparer"
                        else _recettes.ouvrir(self)
                        if c == "recettes"
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
        # ONE SINGLE NAVIGATION RULE, otherwise nothing says where to look for
        # what: the top bar only carries DESTINATIONS (where I go),
        # the sidebar only ACTIONS (what I do). "Fermer Chrome"
        # was an action placed among the destinations, and already duplicated
        # Maintenance > Access & diagnostics.
        tp = CF(self.main, bg=BG)
        tp.pack(fill="x", pady=(0, _theme.GAP))
        # Folds or opens the left menu (Ctrl+B): the table then takes the whole
        # width. Named "Outils" until 3.15, nothing said it hid the menu.
        self.b_menu = CB(
            tp,
            text="« Réduire le menu",
            command=self._toggle_sidebar,
            bg=BTN,
            fg=TX,
            relief="flat",
            activebackground=BTN_H,
            cursor="hand2",
            font=(_theme.FONT_UI, 13),
        )
        self.b_menu.pack(side="left", padx=(2, 0), pady=2)
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
        # The main navigation lives in the left column, not duplicated
        # in the header. This bar only keeps the context of the work.
        # The title follows the open page (_nav_actif): a fixed title "Suivi des
        # candidatures" also topped Mes CV, Entreprises and Accès.
        self.nav_context = CL(tp, text="Offres", bg=BG, fg=TX, font=(_theme.FONT_UI, 17, "bold"))
        self.nav_context.pack(side="left", padx=(20, 0))
        # The log lives in the sidebar, FOLDED at start-up: everything the
        # travail de fond (auto-enrichissement, relances dues, taches lancees
        # from the top bar) was written into a panel nobody
        # sees. This line keeps the latest information always readable.
        footer = CF(self.main, bg=BG, plat=True)
        footer.pack(side="bottom", fill="x", pady=(8, 0))
        self.status = CL(footer, text="", bg=BG, fg=MUT, font=(_theme.FONT_UI, 12), anchor="e")
        self.status.pack(side="left", fill="x", expand=True)
        # dashboard and viewer = 2 panels INSIDE the same window (no popup)
        self.dash = CF(self.main, bg=WORK)
        self.dash.pack(fill="both", expand=True)
        self._build_dash(self.dash)
        self.viewer = None  # CV & Letters panel, built on first use
        self._dv = None  # full-screen offer detail panel
        self._panels: dict[str, Any] = {}  # Companies / Job sites panels
        # The left menu as the user left it (« Réduire le menu » / Ctrl+B, remembered in
        # _vues.json). The status line stays visible.
        from jobhunter.app import views as _vues

        if not _vues.barre_ouverte():
            self._toggle_sidebar(memo=False, garder=False)
        self._desc_busy = False
        self.load_offers()
        # A CV dragged onto the window (tkinterdnd2; without it, the CV panel's button).
        self._depot_cv = _activer_depot(self.root, self._deposer_cv)
        self.root.after(100, self._drain)
        self._raccourcis()
        # Did the last update really start its version? (programs.update.confirmer_demarrage)
        try:
            from jobhunter.programs import update as _maj

            if msg := _maj.confirmer_demarrage():
                self._log(msg + "\n")
        except Exception:  # never a reason not to open
            pass
        # JOBHUNTER_SANS_FOND=1 : aucun travail de fond (scan, descriptions,
        # sync). To open the app for a visual check without
        # triggering a scan at the first return of focus.
        if os.environ.get("JOBHUNTER_SANS_FOND"):
            # Hook of the visual tests (run from the source code): never in
            # the installed application, where an environment variable must not be
            # enough to execute code.
            act = os.environ.get("JOBHUNTER_ACTION")
            if act and not _gele.est_gele():
                self.root.after(1500, lambda: exec(act, {"app": self, "tk": tk}))  # nosec B102
            return
        # AUTO: as soon as there are offers without a description, they are fetched in the background (at start-up
        # + after each addition/rebuild). No button — silent.
        self.root.after(2500, self._auto_enrich)
        # AUTO: docx→pdf sync + links (a docx modified somewhere = pdf/links realigned)
        self.root.after(6000, self._auto_sync)
        # AUTO: the table follows the queue when another program writes it
        self.root.after(15000, self._surveiller_file)
        self.root.after(4000, self._check_relances)  # relances dues → log
        # AUTO: scan of company sites, 2 min after launch then every 3 h
        self.root.after(120000, self._auto_scrape)
        self.root.bind("<FocusIn>", self._on_focus_scrape, add="+")

    def _raccourcis(self) -> None:
        """Keyboard layer over ALREADY existing actions — no new ones.

        448 offers to process one by one: every round trip to the mouse is a cost
        paid 448 times. The existing bindings were all local to a widget (Enter in
        a field, click on the table); there was no global shortcut.
        """
        for touches, action in (
            ("<Escape>", self._show_dash),  # back to the table
            ("<Control-r>", self.load_offers),  # recharger
            ("<F5>", self.run_all),  # DO EVERYTHING
            ("<Control-b>", self._toggle_sidebar),  # fold/open the bar
            ("<Control-l>", lambda: self.e_url.focus_set()),
            ("<Control-w>", self.stop),  # stop the task
            ("<Control-f>", self._focus_search),  # search the offers
            ("<Alt-Left>", self._dispo_retour),  # annuler agrandir/retrecir
        ):
            self.root.bind_all(touches, lambda e, f=action: (f(), "break")[1])
        # Business shortcuts reserved for the table. bind_all() also intercepted
        # Ctrl+A and Ctrl+Z in the search, note and URL fields: the native
        # text selection/undo triggered a business action.
        for touches, action in (
            ("<Control-Return>", self._apply_checked),
            ("<Control-a>", lambda: self._check_all(True)),
            ("<Control-d>", lambda: self._check_all(False)),
            ("<Control-z>", self._annuler_dernier),
        ):
            self.tree.bind(touches, lambda e, f=action: (f(), "break")[1])  # type: ignore[misc]  # lambda with a default parameter (loop capture)
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
                text=_t(
                    {
                        "offres": "Offres",
                        "recherche": "Ma recherche",
                        "profil": "Profil",
                        "cv": "Mes CV",
                        "entreprises": "Entreprises",
                        "sites": "Sites d'offres",
                        "stats": "Statistiques",
                        "acces": "Accès",
                    }.get(cle, cle)
                )
            )
        for c, b in getattr(self, "_nav", {}).items():
            if c == cle:
                b.configure(fg_color=ACC, text_color=ACC_TX, hover_color=ACC_H)
            else:
                b.configure(fg_color=SIDE, text_color=SIDE_MUT, hover_color=SIDE_H)

    def _basculer_langue(self) -> None:
        """Menu of the interface languages, each under its own name; applies at the next start."""
        import functools
        import tkinter as tk

        from jobhunter.app import language as _langue

        menu = tk.Menu(self.root, tearoff=0)
        self._langue_var = tk.StringVar(self.root, _langue.LANGUE)  # the current one is ticked
        for code, nom in _langue.noms().items():
            menu.add_radiobutton(
                label=nom,
                value=code,
                variable=self._langue_var,
                command=functools.partial(self._choisir_langue, code),
            )
        x, y = self.root.winfo_pointerxy()
        try:
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()

    def _choisir_langue(self, code: str) -> None:
        """Saves the chosen language and says, in it, that a restart applies it."""
        from jobhunter.app import language as _langue

        if code == _langue.LANGUE:
            return
        _langue.choisir(code)
        messagebox.showinfo("JobHunter", _langue.message_relance(code), parent=self.root)

    def _planifier(self) -> None:
        """Collection every morning: creates the Windows task at the chosen time, or removes it."""
        from tkinter import simpledialog

        from jobhunter import scheduling as _plan
        from jobhunter.app import language as _langue

        if _plan.planifiee():
            if not messagebox.askyesno(
                "JobHunter",
                _t("La collecte quotidienne est déjà planifiée. La retirer ?"),
                parent=self.root,
            ):
                return
            ok, msg = _plan.supprimer()
        else:
            heure = simpledialog.askstring(
                "JobHunter",
                _t("Collecter les offres chaque jour à quelle heure ? (format 08:00)"),
                initialvalue="08:00",
                parent=self.root,
            )
            if not heure:
                return
            ok, msg = _plan.creer(heure.strip())
        self._log(msg + "\n")
        (messagebox.showinfo if ok else messagebox.showwarning)(
            "JobHunter", _langue.journal(msg), parent=self.root
        )

    def _toggle_maint(self) -> None:
        if self._maint_on:
            self.maint.pack_forget()
            self.b_maint.configure(text=_t("Maintenance ▸"))
        else:
            self.maint.pack(fill="x", after=self.b_maint)
            self.b_maint.configure(text=_t("Maintenance ▾"))
        self._maint_on = not self._maint_on

    # ── Retour de disposition ──
    # the user, 2026-10-07: a widened panel, a stretched column, an enlarged
    # card or a folded Outils bar had no way back — the gesture
    # had to be redone by hand, to the pixel. So we remember the
    # layout BEFORE each gesture; "↶ Retour" (Alt+Left) restores it, and
    # each press goes back one gesture. The content (tracking, statuses) is
    # not in it: that is Ctrl+Z, in the table.
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
        """Pushes the layout `etat` (by default: the current one)."""
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
        # The table must be displayed and measured before putting the separator back.
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
        """Remembers the layout before any drag on `widget`
        (panel separator, edge of a column)."""

        def _avant(_e: Any) -> None:
            self._dispo_avant = self._dispo_etat()

        def _apres(_e: Any) -> None:
            avant = getattr(self, "_dispo_avant", None)
            if avant is not None and avant != self._dispo_etat():
                self._dispo_memo(avant)
            self._dispo_avant = None

        widget.bind("<ButtonPress-1>", _avant, add="+")
        widget.bind("<ButtonRelease-1>", _apres, add="+")

    def _toggle_sidebar(self, memo: Any = True, garder: bool = True) -> None:
        """Folds or opens the left menu; `garder`: remembered for the next start."""
        if memo and hasattr(self, "_dispo_pile"):
            self._dispo_memo()
        if self._sidebar_on:
            self.sidebar.pack_forget()
        else:
            self.sidebar.pack(side="left", fill="y", padx=0, before=self.main)
        self._sidebar_on = not self._sidebar_on
        if getattr(self, "b_menu", None) is not None:
            self.b_menu.configure(
                text=_t("« Réduire le menu") if self._sidebar_on else _t("☰ Menu")
            )
        if garder:
            from jobhunter.app import views as _vues

            try:
                _vues.memoriser_barre(self._sidebar_on)
            except OSError:
                pass  # read-only folder: the choice simply lasts this session


def _annonce_mise_a_jour(root: Any, app: Any) -> None:
    """At start-up, in the background: a more recent version on GitHub?
    At most one check per day; offline, nothing is displayed."""

    def proposer(v: Any, installee: Any) -> None:
        if messagebox.askyesno(
            _t("JobHunter — mise à jour disponible"),
            _t(
                "La version {v} est disponible (installée : {installee}).\n\n"
                "L'installer maintenant ? Ton profil, ton CV, tes lettres et ton suivi ne "
                "sont pas touchés, et la version d'avant est sauvegardée."
            ).format(v=v, installee=installee),
            parent=root,
        ):
            app.mettre_a_jour()

    def verifier() -> None:
        try:
            from jobhunter.programs import update as mise_a_jour

            v = mise_a_jour.nouvelle_version()
            installee = mise_a_jour.version_locale()
        except Exception:
            v = None
        if v:
            root.after(0, lambda: proposer(v, installee))

    threading.Thread(target=verifier, daemon=True).start()


def _hors_profil_actif() -> bool:
    """True, after relaunching the app properly, when it was started outside the active profile.

    A launcher that does not call `profiles.appliquer()` first (an old copy of
    JobHunter.pyw) opened the main profile whatever profile was chosen: switching
    profile did nothing. The paths are fixed at import, so the only remedy is a new
    process, through `python -m jobhunter.app`, which applies the active profile.
    """
    from jobhunter import profiles as _profils

    if os.environ.get(_profils.ENV_PRINCIPALE) or _gele.est_gele():
        return False  # the profile was applied (or the frozen app applies it itself)
    try:
        principale = _racine.racine()
        voulu = _profils.racine_de(_profils.actif(principale), principale)
    except RuntimeError:
        return False
    if voulu.resolve() == principale.resolve():
        return False
    import subprocess

    env = {**os.environ, "JOBHUNTER_RACINE": str(principale)}
    subprocess.Popen(  # nosec B603 : our own program
        [sys.executable, "-m", "jobhunter.app"], cwd=str(principale), env=env
    )
    return True


def main() -> None:
    # Without a console (JobHunter.pyw, the windowed exe), sys.stdout is None; some
    # fifty modules call `sys.stdout.reconfigure(...)` at import, and
    # the panel that loaded one of them crashed. A null sink makes them harmless.
    for nom in ("stdout", "stderr"):
        if getattr(sys, nom) is None:
            setattr(sys, nom, open(os.devnull, "w", encoding="utf-8"))  # noqa: SIM115
    _racine.exporter_paquet()  # the steps run `python -m jobhunter...`
    if _hors_profil_actif():
        return
    r = ctk.CTk()
    a = App(r)
    _annonce_mise_a_jour(r, a)
    r.mainloop()
