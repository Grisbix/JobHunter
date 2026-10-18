"""Le tableau des offres : construction, filtres type Excel, recherche, tri, rafraichissement.

Partie de jobhunter.app (ancien JobHunter.pyw, phase 3.7)."""

import json
import tkinter as tk
from tkinter import ttk
from urllib.parse import urlparse

import customtkinter as ctk

from jobhunter.app import theme as _theme
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
    # ── dashboard plein écran : filtres Excel (clic entête) + table + détail + édition ──
    def _build_dash(self, parent):
        self.colsel = {}  # key -> ("keep"|"excl", set) | None (None = toutes)
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
        # Entete : plan 3 (widgets), texte attenue en capitales de fait — la
        # donnee doit peser plus lourd que son etiquette.
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
        # Barres de defilement : celles de clam sont grises et claires, seules
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
        self.checked = set()  # oids des offres cochées (à postuler en lot)
        self._voir_masquees = False
        self._annuler = []  # pile Ctrl+Z : [(oid, entree de suivi AVANT), ...] par geste

        # ── ligne 1 : chercher · voir masquées ········· coller un lien ──
        # Deux lignes au lieu d'une : sur une seule, les cinq boutons de
        # selection repoussaient la recherche et le champ « coller un lien »
        # HORS de la fenetre — ils existaient sans qu'on puisse les voir.
        heading = CF(parent, bg=WORK, plat=True)
        heading.pack(fill="x", padx=18, pady=(4, 12))
        CL(heading, text="Offres", fg=TX, font=(_theme.FONT_UI, 26, "bold")).pack(side="left")
        # CRM : trois indicateurs de travail, pas dix cartes décoratives. Ils
        # restent synchronisés avec la file chargée et le suivi manuel.
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
        # ＋ coller un lien d'offre → analyse (titre/entreprise/description) + queue + CV/lettre
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

        # ── ligne 2 : compteur ········· actions sur la sélection (si cochées) ──
        bar2 = CF(parent, bg=WORK, plat=True)
        bar2.pack(fill="x", padx=18, pady=(10, 0))
        # Sans compteur, rien ne distingue « 12 offres apres filtre » de « 2879 »,
        # ni un filtre trop strict d'une queue vide : le tableau restait blanc et
        # muet dans les deux cas.
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
        # Les actions de lot n'apparaissent QUE s'il y a une selection : quatre
        # boutons « (0) » permanents etaient du bruit, et le plus dangereux
        # (Supprimer) attirait l'oeil en rouge sans rien avoir a faire.
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

        # Le bas (detail + suivi) est place AVANT le tableau, cote bas : le
        # packer sert les widgets dans l'ordre, et le tableau extensible,
        # place en premier, prenait toute la hauteur — le suivi etait coupe.
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
            # entête _chk = cocher/décocher tout ; autres = menu filtre
            cmd = (
                (lambda: self._check_all(None))
                if key == "_chk"
                else (lambda k=key: self._col_menu(k))
            )
            self.tree.heading(key, text=lbl, command=cmd, anchor=anc)
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
        self._urlcol = None  # lien disponible dans la fiche et le menu contextuel
        self._chkcol = "#%d" % (1 + [c[0] for c in COLS].index("_chk"))
        self.tree.bind("<Button-1>", self._click_cell, add="+")
        self._dispo_suivre(split)  # separateur tableau | fiche
        self._dispo_suivre(self.tree)  # largeur des colonnes
        self.tree.bind("<Double-1>", self._fiche_popup)  # double-clic = fiche complète
        self.tree.bind("<Return>", self._fiche_popup)
        self.tree.bind("<Button-3>", self._row_menu)  # clic droit = actions (Postuler + statuts)
        self.tree.bind("<<TreeviewSelect>>", self._load_edit)
        # Suppr sur une ligne = pas intéressé, et le curseur passe a la
        # suivante : trier 400 offres devient une suite de touches. Lie au
        # TABLEAU seulement — dans un champ texte, Suppr efface une lettre.
        self.tree.bind("<Delete>", lambda e: (self._pas_interesse(self._cur), "break")[1])
        self.tree.tag_configure("odd", background=ROW1)
        self.tree.tag_configure("even", background=ROW0)
        for ls, col in LS_COLOR.items():
            self.tree.tag_configure("ls_" + ls, foreground=col)
        # Poses APRES les couleurs de lien : sur une meme ligne, le dernier tag
        # configure l'emporte, et le jugement de l'utilisateur prime sur l'etat du lien.
        for st, col in ST_COULEUR.items():
            self.tree.tag_configure("st_" + st, foreground=col)
        self._sort = (None, False)

        # ── bas : détail de l'offre (gauche) + suivi (droite) ──
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
        self.detail.bind("<Double-1>", lambda e: self._detail_full())  # double-clic = plein écran
        self._detail_vide()

        # ── panneau d'édition du suivi (écrit suivi.json) ──
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
        # Le titre figure déjà dans la fiche ; conserver le widget pour les mises à jour.
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

    def _toggle_columns(self):
        """Vue compacte par défaut, toutes les colonnes restent accessibles."""
        all_cols = tuple(c[0] for c in COLS)
        current = tuple(self.tree.cget("displaycolumns"))
        visible = all_cols if current == self._visible_cols else self._visible_cols
        self.tree.configure(displaycolumns=visible)
        self._urlcol = "#%d" % (visible.index("_url") + 1) if "_url" in visible else None

    def _toggle_suivi(self):
        self._suivi_open = not self._suivi_open
        if self._suivi_open:
            self._suivi_fields.grid()
        else:
            self._suivi_fields.grid_remove()
        self.b_suivi.configure(text="Suivi et note " + ("▾" if self._suivi_open else "▸"))

    def _zone_texte(self, parent, height=7, bg=ROW0):
        """Texte en lecture, au theme : tk.Text + barre ttk stylee.

        ScrolledText impose une barre tk que Windows dessine toujours en gris
        clair. Le cadre porteur est `t.master` — c'est lui qu'on place.
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

    def _detail_vide(self):
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

    def _basculer_masquees(self):
        self._voir_masquees = bool(self.sw_masq.get())
        self.refresh_table()

    def _clear_filters(self):
        self.colsel.clear()
        self.refresh_table()

    def _cell(self, o, key):
        """Valeur affichée d'une colonne (pour liste de valeurs + filtre)."""
        return str(self._row_vals(o)[self._colidx[key]])

    def _col_menu(self, key):
        """Menu type Excel sur l'entête : tri croissant/décroissant + choisir les valeurs."""
        win = tk.Toplevel(self.root)
        win.overrideredirect(True)
        win.configure(bg=LINE)
        x, y = self.root.winfo_pointerxy()
        win.geometry(f"+{x}+{y + 6}")
        fr = CF(win, bg=CARD)
        fr.pack(padx=2, pady=2)

        def sort(asc):
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

        def fill(flt=""):
            lb.delete(0, "end")
            shown.clear()
            for v in vals:
                if flt and flt not in v.lower():
                    continue
                shown.append(v)
                i = lb.size()
                lb.insert("end", v if v else "(vide)")
                # coché = valeur retenue à l'affichage (keep→dans set ; excl→hors set)
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

        def _sel():
            return {shown[i] for i in lb.curselection()}

        def keep():  # garder seulement la sélection
            sel = _sel()
            self.colsel[key] = None if len(sel) >= len(vals) else ("keep", sel)
            win.destroy()
            self.refresh_table()

        def excl():  # exclure la sélection, montrer le reste
            sel = _sel()
            self.colsel[key] = ("excl", sel) if sel else None
            win.destroy()
            self.refresh_table()

        def only(_e):  # double-clic une valeur → seulement celle-ci
            c = lb.curselection()
            if not c:
                return
            self.colsel[key] = ("keep", {shown[c[0]]})
            win.destroy()
            self.refresh_table()

        lb.bind("<Double-Button-1>", only)

        def tout():
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

        def _close_if_out():
            try:
                f = win.focus_get()
            except Exception:
                f = None
            # ne ferme QUE si le focus a quitté le popup (pas un clic sur un enfant)
            if f is None or not str(f).startswith(str(win)):
                win.destroy()

        win.bind("<FocusOut>", lambda e: win.after(120, _close_if_out))
        win.after(50, win.focus_force)

    def _statut_of(self, o):
        """Statut effectif = suivi MANUEL uniquement (toi). apply_runner_done.json = essais
        machine (form rempli/test), PAS une vraie candidature → jamais affiché comme 'postulé'."""
        sv = self.suivi.get(self._oid(o), {})
        return (sv["s"], "manuel") if sv.get("s") else ("", "")

    def _fitnum(self, o):
        f = str(o.get("fit") or "").strip()
        return int(f) if f.isdigit() else -1

    def _fitfin(self, o):
        """Fit decimal (ats_match.fit_detail, 2026-10-09) : departage les ex aequo
        d'un meme fit entier. Absent sur une offre pas encore rescoree : le fit
        entier tient lieu."""
        f = o.get("fit_fin")
        return float(f) if isinstance(f, (int, float)) else float(self._fitnum(o))

    def _fit_aff(self, o):
        """fit_fin a une decimale, SANS plafond : il va de fit - 0,45 a fit + 0,45,
        donc jusqu'a 10,4 au sommet. Plafonne a 10, tout le haut de la file
        affichait 10.0 et le tri ne se voyait plus."""
        f = o.get("fit_fin")
        return f"{f:.1f}" if isinstance(f, (int, float)) else o.get("fit", "")

    def _sortkey(self, o, key):
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

    # Types d'URL qui ne menent PAS a une offre precise : page d'accueil,
    # portail carrieres, page de resultats. Les ouvrir donne l'impression que
    # l'app se trompe, alors que le lien direct etait mort et a ete remplace
    # a dessein (queue_tools.writeback garde l'original dans url_orig).
    _PAS_DIRECT = {
        "HOMEPAGE": "⌂",
        "CAREERS_PORTAL": "⌂",
        "OTHER": "⌂",
        "RECHERCHE": "≡",
        "BOARD_SEARCH": "≡",
    }

    def _marque_lien(self, o):
        """Glyphe d'avertissement, ou '' si le lien ouvre bien une offre."""
        g = self._PAS_DIRECT.get(str(o.get("url_type") or ""), "")
        if g:
            return g
        # Le type ne suffit pas : jobs.smartrecruiters.com/<Societe> etait classe
        # OFFRE_DIRECTE alors qu'il ouvre le tableau d'offres de la societe, pas
        # une offre. Un lien d'offre porte toujours un identifiant — un segment
        # de chemin supplementaire, un nombre, ou une requete.
        u = str(o.get("url") or "")
        if not u.startswith("http"):
            return ""
        d = urlparse(u)
        seg = [c for c in (d.path or "").split("/") if c]
        # UNE RECHERCHE N'EST PAS UNE OFFRE. Le test `d.query` plus bas prenait
        # toute chaine de requete pour un identifiant d'offre : les 15 liens
        # `welcometothejungle.com/fr/jobs?query=Amundi+Analyste+ESG` passaient
        # donc pour des liens directs, sans le moindre avertissement. Quatre
        # d'entre eux trônaient a fit 10 en tete de liste, et cliquer dessus
        # ouvrait la page de resultats de WTJ — ce que l'utilisateur a vu comme
        # « l'accueil ». Ce sont des cibles notees a la main, pas des annonces.
        if _RX_RECHERCHE_Q.search(d.query or ""):
            return "≡"
        # Un chemin qui SE TERMINE par un mot de rubrique ouvre la liste des
        # postes, jamais un poste : /careers, /recrutement, /companies/<slug>…
        if seg and seg[-1].lower().strip("-_") in _RUBRIQUES:
            return "⌂"
        if d.query or len(seg) >= 2 or any(c.isdigit() for c in "".join(seg)):
            return ""
        return "⌂"

    # ── RECHERCHE LIBRE ─────────────────────────────────────────────────────
    # _sansaccent vivait ici, en 4e copie de la meme normalisation.
    _sansaccent = staticmethod(sans_accent)

    def _texte_offre(self, o):
        """Tout le texte cherchable d'une offre, mis en cache par identifiant.

        Sans cache, chaque frappe reconstruisait la chaine pour 2500 offres dont
        la description fait plusieurs milliers de caracteres — la saisie devenait
        saccadee. Le cache est vide a chaque load_offers().
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

    def _focus_search(self, e=None):
        """Ctrl+F : donne le focus au champ et efface l'invite."""
        self.e_search.focus_set()
        self._search_focus()

    def _search_focus(self, e=None):
        if self.e_search.get() == SEARCH_HINT:
            self.e_search.delete(0, "end")

    def _search_termes(self):
        """Termes saisis, ou [] si le champ est vide / affiche l'invite."""
        q = self.e_search.get().strip()
        if not q or q == SEARCH_HINT:
            return []
        return [m for m in self._sansaccent(q).split() if m]

    def _search_differe(self, e=None):
        """Relance la recherche 300 ms apres la DERNIERE frappe.

        Sans ce delai, refresh_table() reconstruit les 2500 lignes du tableau a
        chaque caractere tape : la fenetre se fige entre deux touches.
        """
        if getattr(self, "_search_job", None):
            try:
                self.root.after_cancel(self._search_job)
            except Exception:
                pass
        self._search_job = self.root.after(300, self._search_now)

    def _search_now(self, e=None):
        self._search_job = None
        termes = self._search_termes()
        if termes == self._search_termes_actifs:
            return  # rien de neuf : on ne redessine pas
        self._search_termes_actifs = termes
        self.refresh_table()

    def _search_clear(self, e=None):
        self.e_search.delete(0, "end")
        self.e_search.insert(0, SEARCH_HINT)
        self.root.focus_set()  # sinon l'invite serait effacee par le FocusIn
        self._search_termes_actifs = []
        self.refresh_table()

    def _row_vals(self, o):
        sv = self.suivi.get(self._oid(o), {})
        stt, src = self._statut_of(o)
        u = o.get("url") or ""
        host = urlparse(u).netloc.replace("www.", "") if u.startswith("http") else "chercher"
        marque = self._marque_lien(o)
        poste = o.get("poste", "")
        if marque and u.startswith("http"):
            host = marque + " " + host
            # LE MARQUEUR DOIT ETRE LA OU L'OEIL VA. Il ne vivait que dans la
            # colonne « site », tout a droite : en triant par fit on ne le voit
            # pas. Quatre lignes dont le lien est une RECHERCHE trônaient a
            # fit 10, et cliquer dessus ouvrait la page de resultats du site —
            # « ça m'envoie sur l'accueil ». On le met aussi devant l'intitule.
            poste = f"{marque} {poste}"
        st_txt = f"{ST_EMOJI.get(stt, '')} {stt}".strip() if stt else DEFAULT_ST
        chk = "☑" if self._oid(o) in self.checked else "☐"
        # ZONE. Bordeaux et l'Ile-de-France d'abord, le Sud-Est ensuite : c'est
        # une preference de l'utilisateur, PAS une mesure d'adequation du poste. Elle
        # vit donc dans sa propre colonne, filtrable, et ne touche pas au fit —
        # une offre parfaite a Lille reste une offre parfaite, mal placee.
        zone = o.get("zone") or ""
        zone_txt = ZONE_ETIQ.get(zone, zone)
        if zone == "prioritaire":
            _sz = _sous_zone(o.get("localisation"))
            if _sz:
                zone_txt = "1 · " + _libelle_secteur(_sz)
        contrat = o.get("contrat") or ""
        # LIEU : toute l'Ile-de-France s'affiche « Paris » (l'utilisateur, 2026-10-05).
        # « La Defense - 92 », « Paris, Ile-de-France, France », « Courbevoie »
        # faisaient chacun une case du filtre. Le lieu exact reste dans la fiche.
        # PAYS : sa propre colonne, filtrable — 61 pays dans la file.
        # REGION (2026-10-07) : Europe, Amerique du Nord, Asie... un clic par continent.
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

    def _contrats_exclus(self):
        """Types de contrat masques, lus dans sources_config.json — le MEME
        fichier que le scan. Le reglage reste donc dans les parametres : il
        suffit de vider la liste pour tout revoir, sans toucher au code.
        Relu a chaque rafraichissement, pour ne pas exiger un redemarrage."""
        try:
            cfg = json.loads((SCRIPTS / "sources_config.json").read_text(encoding="utf-8"))
            return set(cfg.get("contrats_exclus") or [])
        except Exception:
            return set()

    def _exclu(self, o):
        """Le contrat vient du champ, sinon de l'intitule : les offres deja en
        file portent encore « CDI » la ou LinkedIn s'est trompe."""
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

    def refresh_table(self):
        for r in self.tree.get_children():
            self.tree.delete(r)
        self.rowmap.clear()
        self._exclus = self._contrats_exclus()
        active = {k: v for k, v in self.colsel.items() if v is not None}
        sk, asc = self._sort
        if sk:
            rows = sorted(self.offers, key=lambda o: self._sortkey(o, sk), reverse=not asc)
        else:
            # Departage par entreprise : ats_pct servait de second critere, mais
            # la colonne a ete retiree et le score ne veut plus rien dire ici.
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
            # tous les termes doivent etre presents (ET), dans n'importe quel champ
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
            # Une offre jugee mauvaise reste visible — l'utilisateur doit pouvoir
            # revenir sur son verdict — mais grisee, pour que l'oeil la saute.
            # Les autres statuts colorent la ligne (ST_COULEUR).
            if stt in ST_COULEUR:
                tags.append("st_" + stt)
            iid = self.tree.insert("", "end", values=vals, tags=tuple(tags))
            self.rowmap[iid] = o
            n += 1
        for key, lbl, _ in COLS:
            if key == "_chk":
                continue  # entête ☐ garde son libellé (cocher/décocher tout)
            arrow = (" ▲" if asc else " ▼") if sk == key else ""
            filt = " ▾" if self.colsel.get(key) is not None else ""
            self.tree.heading(key, text=lbl + arrow + filt)
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
