"""The offers table: construction, Excel-style filters, search, sorting, refresh.

Part of jobhunter.app (former JobHunter.pyw, phase 3.7)."""

import json
import tkinter as tk
from tkinter import ttk
from typing import Any
from urllib.parse import urlparse

import customtkinter as ctk

from jobhunter.app import theme as _theme
from jobhunter.app._type_app import AppTypee
from jobhunter.app.commun import (
    _RUBRIQUES,
    _RX_ALT,
    _RX_RECHERCHE_Q,
    _RX_STAGE,
    COLS,
    CONTRAT_COURT,
    DEFAULT_ST,
    DOM_SHORT,
    LS_COLOR,
    MASQUANTS,
    SCRIPTS,
    SEARCH_HINT,
    ST_COULEUR,
    ST_EMOJI,
    ZONE_ETIQ,
    _ChoixStatut,
    _pays_lieu,
    _region_lieu,
    _ville_affichee,
)
from jobhunter.app.langue import t as _t
from jobhunter.app.theme import (
    ACC,
    ACC_H,
    ACC_TX,
    BTN,
    BTN_H,
    CARD,
    CB,
    CE,
    CF,
    CL,
    DEL,
    DEL_TX,
    LINE,
    MUT,
    ROW0,
    ROW1,
    TX,
    TX_AMBRE,
    WORK,
)
from jobhunter.scoring.zones import libelle_secteur as _libelle_secteur
from jobhunter.scoring.zones import sous_zone as _sous_zone
from jobhunter.texte import sans_accent


class TableauMixin:
    # ── full-screen dashboard: Excel filters (header click) + table + detail + editing ──
    def _build_dash(self: "AppTypee", parent: Any) -> None:
        self.colsel: dict[str, Any] = {}  # key -> ("keep"|"excl", set) | None (None = toutes)
        self._colidx = {k: i for i, (k, _, _) in enumerate(COLS)}
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Treeview",
            background=ROW0,
            foreground=TX,
            fieldbackground=ROW0,
            rowheight=38,
            borderwidth=0,
            font=(_theme.FONT_UI, 12),
            bordercolor=WORK,
            lightcolor=WORK,
            darkcolor=WORK,
        )
        # Header: layer 3 (widgets), dimmed text, effectively in capitals — the
        # data must weigh more than its label.
        style.configure(
            "Treeview.Heading",
            background=CARD,
            foreground=MUT,
            font=(_theme.FONT_UI, 11, "bold"),
            relief="flat",
            borderwidth=0,
            padding=(6, 7),
        )
        style.map("Treeview.Heading", background=[("active", BTN_H)], foreground=[("active", TX)])
        style.map("Treeview", background=[("selected", BTN_H)], foreground=[("selected", TX)])
        # Scrollbars: clam's are grey and light, only
        # taches blanches de toute l'application.
        for orient in ("Vertical", "Horizontal"):
            style.configure(
                f"{orient}.TScrollbar",
                background=BTN,
                troughcolor=WORK,
                bordercolor=WORK,
                lightcolor=BTN,
                darkcolor=BTN,
                arrowcolor=MUT,
                gripcount=0,
                relief="flat",
            )
            style.map(f"{orient}.TScrollbar", background=[("active", BTN_H)])
        self.checked: set[Any] = set()  # oids of the ticked offers (to apply to in a batch)
        self._voir_masquees = False
        self._annuler: list[
            Any
        ] = []  # Ctrl+Z stack: [(oid, tracking entry BEFORE), ...] per gesture

        # ── row 1: search · show hidden ········· paste a link ──
        # Two rows instead of one: on a single one, the five selection
        # buttons pushed the search and the "coller un lien" field
        # OUT of the window — they existed without anyone being able to see them.
        heading = CF(parent, bg=WORK, plat=True)
        heading.pack(fill="x", padx=18, pady=(4, 12))
        CL(heading, text="Offres", fg=TX, font=(_theme.FONT_UI, 26, "bold")).pack(side="left")
        # CRM: three work indicators, not ten decorative cards. They
        # stay in sync with the loaded queue and the manual tracking.
        kpis = CF(parent, bg=WORK, plat=True)
        kpis.pack(fill="x", padx=18, pady=(0, 6))
        self._offer_kpis = {}
        for index, (key, label) in enumerate(
            (("total", "OFFRES EN FILE"), ("fit", "FIT ≥ 8"), ("post", "CANDIDATURES ENVOYÉES"))
        ):
            kpis.grid_columnconfigure(index, weight=1, uniform="indicateur")
            tile = CF(kpis, bg=CARD)
            tile.grid(row=0, column=index, sticky="ew", padx=(0, 10 if index < 2 else 0))
            CL(tile, text=label, fg=MUT, bg=CARD, font=(_theme.FONT_UI, 10, "bold")).pack(
                anchor="w", padx=14, pady=(10, 0)
            )
            value = CL(tile, text="—", fg=TX, bg=CARD, font=(_theme.FONT_UI, 22, "bold"))
            value.pack(anchor="w", padx=14, pady=(0, 8))
            self._offer_kpis[key] = value
        bar = CF(parent, bg=WORK, plat=True)
        bar.pack(fill="x", padx=18, pady=(8, 0))
        self.e_search = CE(bar, width=40, bg=CARD, fg=TX, font=(_theme.FONT_UI, 13))
        self.e_search.pack(side="left", fill="x", expand=True, ipady=3)
        self.e_search.insert(0, SEARCH_HINT)
        self.e_search.bind("<FocusIn>", self._search_focus)
        self.e_search.bind("<KeyRelease>", self._search_differe)
        self.e_search.bind("<Return>", lambda e: (self._search_now(), "break")[1])
        self.e_search.bind("<Escape>", lambda e: (self._search_clear(), "break")[1])
        self.b_search = CB(bar, text="Chercher", command=self._search_now, bg=BTN, width=80)
        self.b_search.pack(side="left", padx=(6, 2))
        self.b_search_x = CB(bar, text="✕", command=self._search_clear, bg=BTN, fg=MUT, width=40)
        self.b_search_x.pack(side="left", padx=(0, 4))
        self.sw_masq = ctk.CTkSwitch(
            bar,
            text="Voir les masquées",
            command=self._basculer_masquees,
            font=ctk.CTkFont(_theme.FONT_UI, 12),
            text_color=MUT,
            progress_color=ACC,
            button_color=TX,
            button_hover_color=ACC_H,
            fg_color=LINE,
        )
        self.sw_masq.pack(side="left", padx=(18, 0))
        # ＋ paste an offer link → analysis (title/company/description) + queue + CV/letter
        importbar = CF(parent, bg=WORK, plat=True)
        importbar.pack(fill="x", padx=18, pady=(8, 0))
        self.b_addurl = CB(importbar, text="Ajouter une offre", command=self._add_offer_url, bg=BTN)
        self.b_addurl.pack(side="right", padx=(6, 0))
        self.e_url = CE(importbar, width=40, bg=CARD, fg=TX, font=(_theme.FONT_UI, 12))
        self.e_url.pack(side="left", fill="x", expand=True, ipady=3)
        self.e_url.insert(0, "coller un lien d'offre…")
        self.e_url.bind(
            "<FocusIn>",
            lambda e: self.e_url.get().startswith("coller") and self.e_url.delete(0, "end"),
        )
        self.e_url.bind("<Return>", lambda e: self._add_offer_url())

        # ── row 2: counter ········· actions on the selection (if ticked) ──
        bar2 = CF(parent, bg=WORK, plat=True)
        bar2.pack(fill="x", padx=18, pady=(10, 0))
        # Without a counter, nothing tells "12 offers after filter" from "2879",
        # nor a filter that is too strict from an empty queue: the table stayed blank and
        # silent in both cases.
        self.lbl_count = CL(bar2, text="", bg=WORK, fg=MUT, font=(_theme.FONT_UI, 12), anchor="w")
        self.lbl_count.pack(side="left")
        CB(
            bar2,
            text="Colonnes",
            command=self._toggle_columns,
            bg=WORK,
            fg=MUT,
            width=80,
            font=(_theme.FONT_UI, 12),
        ).pack(side="right", padx=(8, 0))
        # Batch actions appear ONLY if there is a selection: four permanent
        # "(0)" buttons were noise, and the most dangerous one
        # (Delete) caught the eye in red while having nothing to do.
        self.selbar = CF(bar2, bg=WORK, plat=True)
        self.lbl_sel = CL(self.selbar, text="", bg=WORK, fg=TX, font=(_theme.FONT_UI, 12, "bold"))
        self.lbl_sel.pack(side="left", padx=(0, 10))
        self.b_apply = CB(
            self.selbar,
            text="Postuler",
            command=self._apply_checked,
            bg=ACC,
            font=(_theme.FONT_UI, 12, "bold"),
        )
        self.b_apply.pack(side="left", padx=3)
        self.b_pasint = CB(
            self.selbar,
            text="Pas intéressé",
            command=self._pas_interesse_checked,
            bg=BTN,
            font=(_theme.FONT_UI, 12),
        )
        self.b_pasint.pack(side="left", padx=3)
        self.b_ecarter = CB(
            self.selbar,
            text="Écarter…",
            command=self._ecarter_checked,
            bg=BTN,
            font=(_theme.FONT_UI, 12),
        )
        self.b_ecarter.pack(side="left", padx=3)
        self.b_del = CB(
            self.selbar,
            text="Supprimer",
            command=self._delete_checked,
            bg=DEL,
            font=(_theme.FONT_UI, 12),
        )
        self.b_del.pack(side="left", padx=3)
        CB(
            self.selbar,
            text="Décocher",
            command=lambda: self._check_all(False),
            bg=WORK,
            fg=MUT,
            activebackground=BTN,
            font=(_theme.FONT_UI, 12),
        ).pack(side="left", padx=(8, 0))
        self.lbl_aide = CL(
            bar2,
            text="En-tête : filtrer  ·  Double-clic : fiche",
            bg=WORK,
            fg=MUT,
            font=(_theme.FONT_UI, 11),
            anchor="e",
        )

        # The bottom (detail + tracking) is placed BEFORE the table, bottom side: the
        # packer serves the widgets in order, and the expandable table,
        # placed first, took the whole height — the tracking was cut off.
        split = tk.PanedWindow(
            parent,
            orient="horizontal",
            bg=LINE,
            sashwidth=6,
            borderwidth=0,
            sashrelief="flat",
            opaqueresize=True,
        )
        split.pack(fill="both", expand=True, padx=8, pady=(12, 0))
        twrap = CF(split, bg=WORK, plat=True)
        bas = CF(split, bg=CARD)
        scale = self.root._get_window_scaling()
        split.add(twrap, minsize=int(380 * scale), stretch="always", width=int(720 * scale))
        split.add(bas, minsize=int(340 * scale), stretch="never", width=int(390 * scale))
        self._offer_split = split
        cols = [c[0] for c in COLS]
        self.tree = ttk.Treeview(
            twrap, columns=cols, show="headings", selectmode="browse", height=16
        )
        for key, lbl, wdt in COLS:
            anc = "center" if key in ("fit", "_chk") else "w"
            # _chk header = tick/untick all; others = filter menu
            cmd = (
                (lambda: self._check_all(None))
                if key == "_chk"
                else (lambda k=key: self._col_menu(k))  # type: ignore[misc]  # lambda with a default parameter (loop capture)
            )
            self.tree.heading(key, text=_t(lbl), command=cmd, anchor=anc)
            compact = {
                "_chk": 34,
                "entreprise": 135,
                "poste": 235,
                "fit": 45,
                "contrat": 70,
                "localisation": 115,
                "pays": 85,
                "region": 95,
                "_st": 105,
            }
            self.tree.column(
                key,
                width=compact.get(key, wdt),
                minwidth=compact.get(key, wdt),
                anchor=anc,
                stretch=(key == "poste"),
            )
        self._visible_cols = (
            "_chk",
            "entreprise",
            "poste",
            "fit",
            "contrat",
            "localisation",
            "pays",
            "region",
            "_st",
        )
        self.tree.configure(displaycolumns=self._visible_cols)
        _hsb = ttk.Scrollbar(twrap, orient="horizontal", command=self.tree.xview)
        _vsb = ttk.Scrollbar(twrap, orient="vertical", command=self.tree.yview)
        self.tree.configure(xscrollcommand=_hsb.set, yscrollcommand=_vsb.set)
        _hsb.pack(side="bottom", fill="x")
        _vsb.pack(side="right", fill="y")
        self.tree.pack(side="top", fill="both", expand=True)
        self._urlcol = None  # link available in the card and the context menu
        self._chkcol = "#%d" % (1 + [c[0] for c in COLS].index("_chk"))
        self.tree.bind("<Button-1>", self._click_cell, add="+")
        self._dispo_suivre(split)  # separateur tableau | fiche
        self._dispo_suivre(self.tree)  # column widths
        self.tree.bind("<Double-1>", self._fiche_popup)  # double-click = full card
        self.tree.bind("<Return>", self._fiche_popup)
        self.tree.bind("<Button-3>", self._row_menu)  # clic droit = actions (Postuler + statuts)
        self.tree.bind("<<TreeviewSelect>>", self._load_edit)
        # Del on a row = not interested, and the cursor moves to the
        # next one: sorting 400 offers becomes a series of keystrokes. Bound to the
        # TABLE only — in a text field, Del erases a letter.
        self.tree.bind("<Delete>", lambda e: (self._pas_interesse(self._cur), "break")[1])
        self.tree.tag_configure("odd", background=ROW1)
        self.tree.tag_configure("even", background=ROW0)
        for ls, col in LS_COLOR.items():
            self.tree.tag_configure("ls_" + ls, foreground=col)
        # Set AFTER the link colours: on the same row, the last configured
        # tag wins, and the user's judgement takes precedence over the link state.
        for st, col in ST_COULEUR.items():
            self.tree.tag_configure("st_" + st, foreground=col)
        self._sort = (None, False)

        # ── bottom: offer detail (left) + tracking (right) ──
        dcard = CF(bas, bg=CARD)
        dcard.pack(side="top", fill="both", expand=True)
        dtop = CF(dcard, bg=CARD, plat=True)
        dtop.pack(fill="x", padx=14, pady=(10, 0))
        CL(dtop, text="FICHE DE L’OFFRE", bg=CARD, fg=MUT, font=(_theme.FONT_UI, 11, "bold")).pack(
            side="left"
        )
        CB(
            dtop,
            text="Agrandir",
            command=self._detail_full,
            bg=CARD,
            fg=MUT,
            font=(_theme.FONT_UI, 11),
            pady=2,
        ).pack(side="right")
        self.detail = self._zone_texte(dcard, height=7, bg=CARD)
        self.detail.master.pack(fill="both", expand=True, padx=(14, 6), pady=(4, 10))
        self.detail.bind("<Double-1>", lambda e: self._detail_full())  # double-click = full screen
        self._detail_vide()

        # ── tracking editing panel (writes suivi.json) ──
        ed = CF(bas, bg=CARD)
        ed.pack(side="bottom", fill="x", padx=14, pady=14, before=dcard)
        ed.grid_columnconfigure(1, weight=1)
        self.b_suivi = CB(
            ed,
            text="Suivi et note ▸",
            command=self._toggle_suivi,
            bg=CARD,
            fg=MUT,
            anchor="w",
            font=(_theme.FONT_UI, 13),
        )
        self.b_suivi.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        fields = CF(ed, bg=CARD, plat=True)
        fields.grid(row=1, column=0, columnspan=2, sticky="ew")
        fields.grid_columnconfigure(1, weight=1)
        self._suivi_fields = fields
        self._suivi_open = False
        fields.grid_remove()
        self.sel = CL(
            ed,
            text="Sélectionne une offre",
            fg=MUT,
            font=(_theme.FONT_UI, 12),
            anchor="w",
            wraplength=320,
            justify="left",
        )
        # The title already appears in the card; keep the widget for updates.
        CL(fields, text="Statut", fg=MUT).grid(row=2, column=0, sticky="w", padx=(0, 12))
        self.e_st = _ChoixStatut(fields)
        self.e_st.grid(row=2, column=1, sticky="ew", pady=3)
        CL(fields, text="Date", fg=MUT).grid(row=3, column=0, sticky="w")
        self.e_date = CE(fields, width=13, bg=WORK, fg=TX)
        self.e_date.grid(row=3, column=1, sticky="ew", pady=3)
        CL(fields, text="Note", fg=MUT).grid(row=4, column=0, sticky="w")
        self.e_note = CE(fields, width=25, bg=WORK, fg=TX)
        self.e_note.grid(row=4, column=1, sticky="ew", pady=3)
        self.e_note.bind("<Return>", lambda e: self.save_edit())
        acts = CF(ed, bg=CARD, plat=True)
        acts.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        acts.grid_columnconfigure((0, 1), weight=1)
        CB(
            acts,
            text="Ouvrir l'offre",
            command=lambda: self._open_offer(self._cur),
            bg=ACC,
            font=(_theme.FONT_UI, 13, "bold"),
        ).grid(row=0, column=0, sticky="ew", padx=(0, 4), pady=4)
        CB(
            acts,
            text="Envoi confirmé",
            command=lambda: self._postuler(self._cur),
            bg=BTN,
            font=(_theme.FONT_UI, 13),
        ).grid(row=0, column=1, sticky="ew", padx=(4, 0), pady=4)
        CB(
            acts,
            text="Pas intéressé",
            command=lambda: self._pas_interesse(self._cur),
            bg=BTN,
            font=(_theme.FONT_UI, 12),
        ).grid(row=1, column=0, sticky="ew", padx=(0, 4), pady=4)
        CB(
            acts, text="Enregistrer", command=self.save_edit, bg=BTN, font=(_theme.FONT_UI, 12)
        ).grid(row=1, column=1, sticky="ew", padx=(4, 0), pady=4)
        self.b_acct = CB(
            acts,
            text="Associer un compte",
            command=self._toggle_account,
            bg=CARD,
            fg=MUT,
            font=(_theme.FONT_UI, 12),
        )
        self.b_acct.grid(row=2, column=0, columnspan=2, sticky="w", pady=(4, 0))
        self._cur = None

    def _toggle_columns(self: "AppTypee") -> None:
        """Compact view by default, all the columns remain accessible."""
        all_cols = tuple(c[0] for c in COLS)
        current = tuple(self.tree.cget("displaycolumns"))
        visible = all_cols if current == self._visible_cols else self._visible_cols
        self.tree.configure(displaycolumns=visible)
        self._urlcol = "#%d" % (visible.index("_url") + 1) if "_url" in visible else None

    def _toggle_suivi(self: "AppTypee") -> None:
        self._suivi_open = not self._suivi_open
        if self._suivi_open:
            self._suivi_fields.grid()
        else:
            self._suivi_fields.grid_remove()
        self.b_suivi.configure(text=_t("Suivi et note ") + ("▾" if self._suivi_open else "▸"))

    def _zone_texte(self: "AppTypee", parent: Any, height: Any = 7, bg: Any = ROW0) -> Any:
        """Read-only text, themed: tk.Text + styled ttk bar.

        ScrolledText imposes a tk bar that Windows always draws in light grey. The
        carrying frame is `t.master` — that is the one we place.
        """
        fr = tk.Frame(parent, bg=bg)
        t = tk.Text(
            fr,
            height=height,
            bg=bg,
            fg=TX,
            insertbackground=TX,
            font=(_theme.FONT_UI, 12),
            relief="flat",
            wrap="word",
            state="disabled",
            borderwidth=0,
            highlightthickness=0,
            padx=2,
            pady=2,
            spacing1=1,
            spacing3=2,
            selectbackground=BTN_H,
            selectforeground=TX,
        )
        sb = ttk.Scrollbar(fr, orient="vertical", command=t.yview)
        t.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        t.pack(side="left", fill="both", expand=True)
        t.tag_configure("k", foreground=ACC, font=(_theme.FONT_UI, 12, "bold"))
        t.tag_configure("h", foreground=TX, font=(_theme.FONT_UI, 15, "bold"), spacing3=4)
        t.tag_configure("m", foreground=MUT)
        return t

    def _detail_vide(self: "AppTypee") -> None:
        d = self.detail
        d.configure(state="normal")
        d.delete("1.0", "end")
        d.insert("end", "Sélectionne une offre dans le tableau.\n", "m")
        d.insert(
            "end",
            "Double-clic ou Entrée : fiche complète  ·  clic droit : actions  ·  "
            "Suppr : pas intéressé",
            "m",
        )
        d.configure(state="disabled")

    def _basculer_masquees(self: "AppTypee") -> None:
        self._voir_masquees = bool(self.sw_masq.get())
        self.refresh_table()

    def _clear_filters(self: "AppTypee") -> None:
        self.colsel.clear()
        self.refresh_table()

    def _cell(self: "AppTypee", o: Any, key: Any) -> Any:
        """Displayed value of a column (for the value list + filter)."""
        return str(self._row_vals(o)[self._colidx[key]])

    def _col_menu(self: "AppTypee", key: Any) -> None:
        """Excel-like menu on the header: ascending/descending sort + choose the values."""
        win = tk.Toplevel(self.root)
        win.overrideredirect(True)
        win.configure(bg=LINE)
        x, y = self.root.winfo_pointerxy()
        win.geometry(f"+{x}+{y + 6}")
        fr = CF(win, bg=CARD)
        fr.pack(padx=2, pady=2)

        def sort(asc: Any) -> None:
            self._sort = (key, asc)
            win.destroy()
            self.refresh_table()

        CB(
            fr,
            text="▲  Croissant",
            anchor="w",
            command=lambda: sort(True),
            bg=CARD,
            fg=TX,
            relief="flat",
            cursor="hand2",
        ).pack(fill="x")
        CB(
            fr,
            text="▼  Décroissant",
            anchor="w",
            command=lambda: sort(False),
            bg=CARD,
            fg=TX,
            relief="flat",
            cursor="hand2",
        ).pack(fill="x")
        CF(fr, bg=LINE, height=1).pack(fill="x", pady=6)
        vals = sorted({self._cell(o, key) for o in self.offers}, key=lambda s: s.lower())
        srch = CE(fr, bg=ROW0, fg=TX, insertbackground=TX, relief="flat", width=22)
        srch.pack(fill="x", padx=6)
        lbf = CF(fr, bg=CARD)
        lbf.pack()
        lb = tk.Listbox(
            lbf,
            selectmode="multiple",
            height=min(12, len(vals) or 1),
            bg=ROW0,
            fg=TX,
            relief="flat",
            width=24,
            exportselection=False,
        )
        sb = tk.Scrollbar(lbf, command=lb.yview)
        lb.configure(yscrollcommand=sb.set)
        lb.pack(side="left", fill="both")
        sb.pack(side="right", fill="y")
        cur = self.colsel.get(key)  # ("keep"|"excl", set) | None
        cmode, cset = cur if cur else (None, set())
        shown = list(vals)

        def fill(flt: Any = "") -> None:
            lb.delete(0, "end")
            shown.clear()
            for v in vals:
                if flt and flt not in v.lower():
                    continue
                shown.append(v)
                i = lb.size()
                lb.insert("end", v if v else "(vide)")
                # ticked = value kept on display (keep→in set; excl→out of set)
                keep = (
                    (cur is None)
                    or (cmode == "keep" and v in cset)
                    or (cmode == "excl" and v not in cset)
                )
                if keep:
                    lb.selection_set(i)

        fill()
        srch.bind("<KeyRelease>", lambda e: fill(srch.get().strip().lower()))
        hint = CL(
            fr, text="double-clic = seulement celle-ci", bg=CARD, fg=MUT, font=(_theme.FONT_UI, 12)
        )
        hint.pack(anchor="w", padx=6)
        bt = CF(fr, bg=CARD)
        bt.pack(fill="x", pady=(2, 0))

        def _sel() -> Any:
            return {shown[i] for i in lb.curselection()}  # type: ignore[no-untyped-call]  # curselection : typeshed : non annotee

        def keep() -> None:  # keep only the selection
            sel = _sel()
            self.colsel[key] = None if len(sel) >= len(vals) else ("keep", sel)
            win.destroy()
            self.refresh_table()

        def excl() -> None:  # exclude the selection, show the rest
            sel = _sel()
            self.colsel[key] = ("excl", sel) if sel else None
            win.destroy()
            self.refresh_table()

        def only(_e: Any) -> None:  # double-click a value → only that one
            c = lb.curselection()  # type: ignore[no-untyped-call]  # curselection : typeshed : non annotee
            if not c:
                return
            self.colsel[key] = ("keep", {shown[c[0]]})
            win.destroy()
            self.refresh_table()

        lb.bind("<Double-Button-1>", only)

        def tout() -> None:
            self.colsel.pop(key, None)
            win.destroy()
            self.refresh_table()

        CB(bt, text="Garder", command=keep, bg=ACC, fg=ACC_TX, relief="flat", cursor="hand2").pack(
            side="left", padx=6
        )
        CB(bt, text="Exclure", command=excl, bg=DEL, fg=DEL_TX, relief="flat", cursor="hand2").pack(
            side="left", padx=6
        )
        CB(bt, text="Tout", command=tout, bg=BTN, fg=TX, relief="flat", cursor="hand2").pack(
            side="left", padx=6
        )
        CB(bt, text="✕", command=win.destroy, bg=BTN, fg=TX, relief="flat").pack(
            side="right", padx=6
        )

        def _close_if_out() -> None:
            try:
                f = win.focus_get()
            except Exception:
                f = None
            # closes ONLY if the focus left the popup (not a click on a child)
            if f is None or not str(f).startswith(str(win)):
                win.destroy()

        win.bind("<FocusOut>", lambda e: win.after(120, _close_if_out))
        win.after(50, win.focus_force)

    def _statut_of(self: "AppTypee", o: Any) -> Any:
        """Effective status = MANUAL tracking only (you). apply_runner_done.json = machine
        trials (form filled/test), NOT a real application → never displayed as 'postulé'."""
        sv = self.suivi.get(self._oid(o), {})
        return (sv["s"], "manuel") if sv.get("s") else ("", "")

    def _fitnum(self: "AppTypee", o: Any) -> Any:
        f = str(o.get("fit") or "").strip()
        return int(f) if f.isdigit() else -1

    def _fitfin(self: "AppTypee", o: Any) -> Any:
        """Decimal fit (ats_match.fit_detail, 2026-10-09): breaks ties between offers with
        the same integer fit. Missing on an offer not yet rescored: the integer fit
        stands in."""
        f = o.get("fit_fin")
        return float(f) if isinstance(f, (int, float)) else float(self._fitnum(o))

    def _fit_aff(self: "AppTypee", o: Any) -> Any:
        """fit_fin has one decimal, WITHOUT a cap: it goes from fit - 0.45 to fit + 0.45,
        hence up to 10.4 at the top. Capped at 10, the whole top of the queue
        displayed 10.0 and the sort could no longer be seen."""
        f = o.get("fit_fin")
        return f"{f:.1f}" if isinstance(f, (int, float)) else o.get("fit", "")

    def _sortkey(self: "AppTypee", o: Any, key: Any) -> Any:
        if key == "_st":
            return self._statut_of(o)[0] or "zzz"
        if key == "_url":
            return urlparse(o.get("url") or "").netloc.replace("www.", "")
        if key == "_date":
            return self.suivi.get(self._oid(o), {}).get("d", "")
        if key == "fit":
            return self._fitfin(o)
        if key == "pays":
            return _pays_lieu(o.get("localisation") or "")
        if key == "region":
            return _region_lieu(o.get("localisation") or "")
        if key == "localisation":
            return _ville_affichee(o.get("localisation") or "")
        v = o.get(key)
        return v if v is not None else ""

    # URL types that do NOT lead to a specific offer: home page,
    # careers portal, results page. Opening them gives the impression that
    # the app is wrong, while the direct link was dead and was replaced
    # on purpose (queue_tools.writeback keeps the original in url_orig).
    _PAS_DIRECT = {
        "HOMEPAGE": "⌂",
        "CAREERS_PORTAL": "⌂",
        "OTHER": "⌂",
        "RECHERCHE": "≡",
        "BOARD_SEARCH": "≡",
    }

    def _marque_lien(self: "AppTypee", o: Any) -> Any:
        """Warning glyph, or '' if the link does open an offer."""
        g = self._PAS_DIRECT.get(str(o.get("url_type") or ""), "")
        if g:
            return g
        # The type is not enough: jobs.smartrecruiters.com/<Company> was classified
        # OFFRE_DIRECTE while it opens the company's job board, not
        # an offer. An offer link always carries an identifier — an extra path
        # segment, a number, or a query.
        u = str(o.get("url") or "")
        if not u.startswith("http"):
            return ""
        d = urlparse(u)
        seg = [c for c in (d.path or "").split("/") if c]
        # A SEARCH IS NOT AN OFFER. The `d.query` test below took
        # any query string for an offer identifier: the 15 links
        # `welcometothejungle.com/fr/jobs?query=Amundi+Analyste+ESG` passaient
        # hence for direct links, without the slightest warning. Four
        # of them sat at fit 10 at the top of the list, and clicking them
        # opened WTJ's results page — what the user saw as
        # "the home page". These are targets noted by hand, not postings.
        if _RX_RECHERCHE_Q.search(d.query or ""):
            return "≡"
        # A path that ENDS with a section word opens the list of
        # jobs, never a job: /careers, /recrutement, /companies/<slug>…
        if seg and seg[-1].lower().strip("-_") in _RUBRIQUES:
            return "⌂"
        if d.query or len(seg) >= 2 or any(c.isdigit() for c in "".join(seg)):
            return ""
        return "⌂"

    # ── RECHERCHE LIBRE ─────────────────────────────────────────────────────
    # _sansaccent lived here, as the 4th copy of the same normalisation.
    _sansaccent = staticmethod(sans_accent)

    def _texte_offre(self: "AppTypee", o: Any) -> Any:
        """All the searchable text of an offer, cached by identifier.

        Without a cache, each keystroke rebuilt the string for 2500 offers whose
        description is several thousand characters long — typing became jerky. The
        cache is emptied at each load_offers().
        """
        oid = self._oid(o)
        t = self._search_cache.get(oid)
        if t is None:
            t = self._sansaccent(
                " ".join(
                    str(o.get(k) or "")
                    for k in (
                        "entreprise",
                        "poste",
                        "domaine",
                        "contrat",
                        "localisation",
                        "process",
                        "url",
                        "description",
                        "missions",
                        "profil",
                        "skills_match",
                    )
                )
            )
            self._search_cache[oid] = t
        return t

    def _focus_search(self: "AppTypee", e: Any = None) -> None:
        """Ctrl+F: gives the focus to the field and clears the placeholder."""
        self.e_search.focus_set()
        self._search_focus()

    def _search_focus(self: "AppTypee", e: Any = None) -> None:
        if self.e_search.get() == SEARCH_HINT:
            self.e_search.delete(0, "end")

    def _search_termes(self: "AppTypee") -> Any:
        """Terms typed, or [] if the field is empty / shows the placeholder."""
        q = self.e_search.get().strip()
        if not q or q == SEARCH_HINT:
            return []
        return [m for m in self._sansaccent(q).split() if m]

    def _search_differe(self: "AppTypee", e: Any = None) -> None:
        """Restarts the search 300 ms after the LAST keystroke.

        Without this delay, refresh_table() rebuilds the 2500 rows of the table at
        each character typed: the window freezes between two keys.
        """
        if getattr(self, "_search_job", None):
            try:
                self.root.after_cancel(self._search_job)
            except Exception:
                pass
        self._search_job = self.root.after(300, self._search_now)

    def _search_now(self: "AppTypee", e: Any = None) -> None:
        self._search_job = None
        termes = self._search_termes()
        if termes == self._search_termes_actifs:
            return  # nothing new: no redraw
        self._search_termes_actifs = termes
        self.refresh_table()

    def _search_clear(self: "AppTypee", e: Any = None) -> None:
        self.e_search.delete(0, "end")
        self.e_search.insert(0, SEARCH_HINT)
        self.root.focus_set()  # otherwise the placeholder would be erased by the FocusIn
        self._search_termes_actifs = []
        self.refresh_table()

    def _row_vals(self: "AppTypee", o: Any) -> Any:
        sv = self.suivi.get(self._oid(o), {})
        stt, src = self._statut_of(o)
        u = o.get("url") or ""
        host = urlparse(u).netloc.replace("www.", "") if u.startswith("http") else "chercher"
        marque = self._marque_lien(o)
        poste = o.get("poste", "")
        if marque and u.startswith("http"):
            host = marque + " " + host
            # THE MARKER MUST BE WHERE THE EYE GOES. It only lived in the
            # "site" column, far right: sorting by fit, one does not see
            # it. Four rows whose link is a SEARCH sat at
            # fit 10, and clicking them opened the site's results page —
            # "it sends me to the home page". We also put it before the title.
            poste = f"{marque} {poste}"
        st_txt = f"{ST_EMOJI.get(stt, '')} {stt}".strip() if stt else DEFAULT_ST
        chk = "☑" if self._oid(o) in self.checked else "☐"
        # ZONE. Bordeaux and Île-de-France first, the South-East next: it is
        # a preference of the user, NOT a measure of how well the job fits. It
        # therefore lives in its own filterable column, and does not touch the fit —
        # a perfect offer in Lille stays a perfect offer, badly located.
        zone = o.get("zone") or ""
        zone_txt = ZONE_ETIQ.get(zone, zone)
        if zone == "prioritaire":
            _sz = _sous_zone(o.get("localisation"))
            if _sz:
                zone_txt = "1 · " + _libelle_secteur(_sz)
        contrat = o.get("contrat") or ""
        # LIEU : toute l'Ile-de-France s'affiche « Paris » (l'utilisateur, 2026-10-05).
        # "La Defense - 92", "Paris, Ile-de-France, France", "Courbevoie"
        # each made a box of the filter. The exact place stays in the card.
        # COUNTRY: its own filterable column — 61 countries in the queue.
        # REGION (2026-10-07): Europe, North America, Asia... one click per continent.
        lieu = o.get("localisation") or ""
        return [
            chk,
            st_txt,
            o.get("entreprise", ""),
            poste,
            DOM_SHORT.get(o.get("domaine"), o.get("domaine") or ""),
            self._fit_aff(o),
            CONTRAT_COURT.get(contrat, contrat),
            zone_txt,
            _ville_affichee(lieu),
            _pays_lieu(lieu),
            _region_lieu(lieu),
            o.get("process", ""),
            host,
            sv.get("d", ""),
        ]

    def _contrats_exclus(self: "AppTypee") -> Any:
        """Hidden contract types, read from sources_config.json — the SAME file as the
        scan. The setting thus stays in the parameters: emptying the list is enough
        to see everything again, without touching the code.
        Re-read at each refresh, so as not to require a restart."""
        try:
            cfg = json.loads((SCRIPTS / "sources_config.json").read_text(encoding="utf-8"))
            return set(cfg.get("contrats_exclus") or [])
        except Exception:
            return set()

    def _exclu(self: "AppTypee", o: Any) -> Any:
        """The contract comes from the field, otherwise from the title: the offers already in
        the queue still carry "CDI" where LinkedIn got it wrong."""
        ex = self._exclus
        if not ex:
            return False
        c = str(o.get("contrat") or "")
        if c in ex:
            return True
        t = str(o.get("poste") or "")
        if "Alternance" in ex and _RX_ALT.search(t):
            return True
        return "Stage" in ex and _RX_STAGE.search(t)

    def refresh_table(self: "AppTypee") -> None:
        for r in self.tree.get_children():
            self.tree.delete(r)
        self.rowmap.clear()
        self._exclus = self._contrats_exclus()
        active = {k: v for k, v in self.colsel.items() if v is not None}
        sk, asc = self._sort
        if sk:
            rows = sorted(self.offers, key=lambda o: self._sortkey(o, sk), reverse=not asc)
        else:
            # Tie-break by company: ats_pct served as second criterion, but
            # the column was removed and the score no longer means anything here.
            rows = sorted(
                self.offers, key=lambda o: (-self._fitnum(o), str(o.get("entreprise") or ""))
            )
        n = 0
        masques = 0
        pas_int = 0
        termes = self._search_termes_actifs
        hors_recherche = 0
        for o in rows:
            if self._exclu(o):
                masques += 1
                continue
            stt = self._statut_of(o)[0]
            if stt in MASQUANTS:
                pas_int += 1
                if not self._voir_masquees:
                    continue
            # all the terms must be present (AND), in any field
            if termes:
                txt = self._texte_offre(o)
                if not all(m in txt for m in termes):
                    hors_recherche += 1
                    continue
            vals = [str(v) for v in self._row_vals(o)]
            skip = False
            for k, (mode, sel) in active.items():
                c = vals[self._colidx[k]]
                if (mode == "keep" and c not in sel) or (mode == "excl" and c in sel):
                    skip = True
                    break
            if skip:
                continue
            tags = ["odd" if n % 2 else "even"]
            ls = o.get("link_status", "")
            if ls in LS_COLOR:
                tags.append("ls_" + ls)
            # An offer judged bad stays visible — the user must be able to
            # go back on their verdict — but greyed out, so that the eye skips it.
            # The other statuses colour the row (ST_COULEUR).
            if stt in ST_COULEUR:
                tags.append("st_" + stt)
            iid = self.tree.insert("", "end", values=vals, tags=tuple(tags))
            self.rowmap[iid] = o
            n += 1
        for key, lbl, _ in COLS:
            if key == "_chk":
                continue  # ☐ header keeps its label (tick/untick all)
            arrow = (" ▲" if asc else " ▼") if sk == key else ""
            filt = " ▾" if self.colsel.get(key) is not None else ""
            self.tree.heading(key, text=str(_t(lbl)) + arrow + filt)
        if getattr(self, "lbl_count", None) is not None:
            filtres = sum(1 for v in self.colsel.values() if v is not None)
            if n == 0:
                if termes:
                    msg = "aucune offre ne contient « %s » — Echap ou ✕ pour effacer" % " ".join(
                        termes
                    )
                elif filtres:
                    msg = "aucune offre ne passe les filtres — clique sur ▾ dans une entete pour les lever"
                else:
                    msg = "aucune offre dans la file"
                self.lbl_count.configure(text=msg, text_color=TX_AMBRE)
            else:
                base = len(self.offers) - masques - (0 if self._voir_masquees else pas_int)
                detail = f" sur {base}" if n != base else ""
                cache = (
                    f"   ·   {masques} masquee(s) : {', '.join(sorted(self._exclus))}"
                    if masques
                    else ""
                )
                rech = f"   ·   🔍 « {' '.join(termes)} »" if termes else ""
                self.lbl_count.configure(text=f"{n} offre(s){detail}{rech}{cache}", text_color=MUT)
        if getattr(self, "_offer_kpis", None):
            stats = {
                "total": len(self.offers),
                "fit": sum(1 for o in self.offers if self._fitnum(o) >= 8),
                "post": sum(
                    1
                    for v in self.suivi.values()
                    if str((v or {}).get("s") or "").lower() == "postulé"
                ),
            }
            for key, label in self._offer_kpis.items():
                label.configure(text=str(stats[key]))
        if getattr(self, "sw_masq", None) is not None:
            self.sw_masq.configure(text=f"Voir les masquées ({pas_int})")
        self._upd_apply_btn()
