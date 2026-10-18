"""Panneaux : statistiques, acces aux sites, societes, sources, ajout d'offre par URL.

Partie de jobhunter.app (ancien JobHunter.pyw, phase 3.7)."""

import importlib
import json
import subprocess
import sys
import threading
import webbrowser
from tkinter import ttk
from urllib.parse import quote, urlparse

from jobhunter.app import commun as _commun
from jobhunter.app import theme as _theme
from jobhunter.app.commun import DOM_SHORT, PAS_INTERESSE, PY, QUEUE, SCRIPTS
from jobhunter.app.theme import (
    ACC,
    ACC_H,
    ACC_TX,
    BG,
    BTN,
    BTN_H,
    CARD,
    CB,
    CE,
    CF,
    CL,
    DEL,
    DEL_H,
    DEL_TX,
    MUT,
    ROW0,
    ROW1,
    TX,
    TX_AMBRE,
    TX_BAD,
    TX_OK,
    WORK,
    _session_presentation,
)
from jobhunter.liens import existe as _doc_existe
from jobhunter.stockage import file as queue_io


class PanneauxMixin:
    def _hide_all(self):
        """Cache tous les panneaux (dash, visionneuse, détail, listes)."""
        self.dash.pack_forget()
        if self.viewer is not None:
            self.viewer.pack_forget()
        if self._dv is not None:
            self._dv.pack_forget()
        for p in self._panels.values():
            p.pack_forget()

    def _show_dash(self):
        self._hide_all()
        if getattr(self, "_viewer_close", None):
            self._viewer_close()  # déverrouille le pdf affiché
        self.dash.pack(fill="both", expand=True)
        self._nav_actif("offres")

    def _stats_panel(self):
        """📊 STATS : vue synthétique de la queue (les données existent dans
        apply_queue.json + suivi.json mais n'étaient visibles nulle part)."""
        self._hide_all()
        if "stats" in self._panels:
            w = self._panels["stats"]
            w._reload()
            w.pack(fill="both", expand=True)
            return
        w = CF(self.main, bg=WORK)
        self._panels["stats"] = w
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
        CL(top, text="Statistiques", bg=BG, fg=TX, font=(_theme.FONT_UI, 16)).pack(
            side="left", padx=28
        )
        CB(
            top,
            text="Rafraîchir",
            command=lambda: w._reload(),
            bg=BTN,
            fg=TX,
            activebackground=BTN_H,
            relief="flat",
            cursor="hand2",
        ).pack(side="right", padx=24)

        # Grille a colonnes egales : dix cartes cote a cote en pack() sortaient
        # de la fenetre, et les trois dernieres (Entretien, Refus…) etaient coupees.
        cards = CF(w, bg=WORK, plat=True)
        cards.pack(fill="x", padx=28, pady=(12, 4))
        w._cards = {}
        for i, (k, lbl) in enumerate(
            (
                ("total", "Offres"),
                ("vivantes", "Liens OK"),
                ("desc", "Avec description"),
                ("fit8", "Fit ≥ 8"),
                ("pretes", "Dossiers préparés"),
                ("post", "Postulé"),
                ("rel", "Relancé"),
                ("ent", "Entretien"),
                ("ref", "Refus"),
                ("pasint", "Pas intéressé"),
            )
        ):
            cards.grid_columnconfigure(i % 5, weight=1, uniform="carte")
            c = CF(cards, bg=CARD)
            c.grid(row=i // 5, column=i % 5, sticky="ew", padx=5, pady=5)
            v = CL(c, text="—", bg=CARD, fg=ACC if k == "pretes" else TX, font=(_theme.FONT_UI, 26))
            v.pack(padx=8, pady=(10, 0))
            CL(c, text=lbl, bg=CARD, fg=MUT, font=(_theme.FONT_UI, 13)).pack(padx=8, pady=(0, 14))
            w._cards[k] = v

        body = CF(w, bg=BG)
        body.pack(fill="both", expand=True, padx=28, pady=18)
        cols = ("cat", "n", "bar")
        tv = ttk.Treeview(body, columns=cols, show="headings", selectmode="none")
        for k, lbl, wd, anc in (
            ("cat", "Catégorie", 300, "w"),
            ("n", "Nb", 70, "center"),
            ("bar", "Répartition", 520, "w"),
        ):
            tv.heading(k, text=lbl)
            tv.column(k, width=wd, anchor=anc, stretch=(k == "bar"))
        tv.pack(fill="both", expand=True)
        tv.tag_configure("h", foreground=ACC, font=(_theme.FONT_UI, 13, "bold"))
        w._tv = tv

        def reload_():
            # relit le DISQUE : le pipeline tourne en fond, self.offers peut être périmé
            try:
                q = queue_io.charger(QUEUE)
            except Exception:
                q = list(self.offers)
            try:
                sv = (
                    importlib.import_module("jobhunter.stockage.suivi").charger(_commun.SUIVI)
                    if _commun.SUIVI.exists()
                    else {}
                )
            except Exception:
                sv = {}
            # Cle « s », pas « statut » : c'est ce qu'ecrivent _set_statut et
            # suivi_io. Avec « statut », les cartes Postulé/Relancé/Entretien/
            # Refus affichaient 0 alors que dix candidatures etaient suivies.
            st = [str((v or {}).get("s") or "").lower() for v in sv.values()]
            ok = [
                o for o in q if str(o.get("link_status") or "").upper() not in ("MORT", "EXPIREE")
            ]

            # PRETES A ENVOYER = le seul chiffre qui decide d'une soiree.
            # « fit >= 8 » seul est trompeur : une offre dont le CV ou la lettre
            # n'existe plus SUR LE DISQUE ne peut pas etre envoyee, et la queue
            # peut tres bien garder la reference d'un fichier efface.
            def _fichier(u):
                if not u:
                    return False
                try:
                    return _doc_existe(u)
                except Exception:
                    return False

            _top = [o for o in ok if (o.get("fit") or 0) >= 8]
            _pretes, _sans_doc, _sans_desc, _lien_douteux = [], [], [], []
            for o in _top:
                if not (_fichier(o.get("cv")) and _fichier(o.get("lettre"))):
                    _sans_doc.append(o)
                    continue
                if len(str(o.get("description") or "")) < 200:
                    _sans_desc.append(o)
                    continue
                if not o.get("ls_check"):
                    _lien_douteux.append(o)
                    continue
                _pretes.append(o)
            vals = {
                "total": len(q),
                "vivantes": len(ok),
                "desc": sum(1 for o in q if str(o.get("description") or "").strip()),
                "fit8": sum(1 for o in ok if (o.get("fit") or 0) >= 8),
                "pretes": len(_pretes),
                "post": sum(1 for s in st if s == "postulé"),
                "rel": sum(1 for s in st if s == "relancé"),
                "ent": sum(1 for s in st if s == "entretien"),
                "ref": sum(1 for s in st if s == "refus"),
                "pasint": sum(1 for s in st if s == PAS_INTERESSE),
            }
            for k, lab in w._cards.items():
                lab.configure(text=str(vals[k]))

            tv.delete(*tv.get_children())

            def section(titre, pairs):
                if not pairs:
                    return
                tv.insert("", "end", values=(titre, "", ""), tags=("h",))
                mx = max((n for _, n in pairs), default=0) or 1
                for nom, n in pairs:
                    bar = "█" * max(0, round(38 * n / mx))
                    pct = f"{100 * n / len(q):.0f}%" if q else ""
                    tv.insert("", "end", values=(f"   {nom}", n, f"{bar} {pct}"))

            def count(key, src=None):
                d = {}
                for o in src or q:
                    v = str(o.get(key) or "—").strip() or "—"
                    d[v] = d.get(v, 0) + 1
                return sorted(d.items(), key=lambda x: -x[1])

            # Ce qui separe une offre bien notee d'une offre envoyable. Sans ce
            # detail, « 487 a fit >= 8 » laisse croire que tout est pret.
            section(
                "▶ Sur les offres a fit ≥ 8",
                [
                    ("dossiers préparés (envoi à vérifier)", len(_pretes)),
                    ("bloquees : CV ou lettre absent du disque", len(_sans_doc)),
                    ("bloquees : description trop courte", len(_sans_desc)),
                    ("bloquees : lien jamais verifie", len(_lien_douteux)),
                ],
            )
            section("Domaine", count("domaine")[:8])
            section("Canal", count("canal"))
            section("État des liens", count("link_status"))
            fits = [
                (f"fit {i}", sum(1 for o in ok if (o.get("fit") or 0) == i))
                for i in range(10, 0, -1)
            ]
            section("Fit (offres vivantes)", [p for p in fits if p[1]])
            ats_b = [
                ("100 %", 0),
                ("80-99 %", 0),
                ("60-79 %", 0),
                ("40-59 %", 0),
                ("< 40 %", 0),
                ("non scoré", 0),
            ]
            d = dict(ats_b)
            for o in ok:
                a = o.get("ats_pct")
                if a is None:
                    d["non scoré"] += 1
                elif a >= 100:
                    d["100 %"] += 1
                elif a >= 80:
                    d["80-99 %"] += 1
                elif a >= 60:
                    d["60-79 %"] += 1
                elif a >= 40:
                    d["40-59 %"] += 1
                else:
                    d["< 40 %"] += 1
            section("ATS % (offres vivantes)", [(k, v) for k, v in d.items() if v])
            src = count("source")
            section("Sources (top 10)", [(s[:46], n) for s, n in src[:10]])

        w._reload = reload_
        reload_()
        w.pack(fill="both", expand=True)

    def _acces_panel(self):
        """🔐 ACCÈS : état de connexion par site + clés d'API.
        AUCUN mot de passe n'est stocké ici — ils restent dans le gestionnaire
        de Chrome, qui remplit lui-même les formulaires quand les scripts
        tournent avec --chrome sur le profil Chrome DÉDIÉ (jamais le profil personnel)."""
        self._hide_all()
        if "acces" in self._panels:
            w = self._panels["acces"]
            w._reload()
            w.pack(fill="both", expand=True)
            return
        w = CF(self.main, bg=WORK)
        self._panels["acces"] = w
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
        CL(top, text="Accès aux sites", bg=BG, fg=TX, font=(_theme.FONT_UI, 16)).pack(
            side="left", padx=28
        )
        CL(
            w,
            text="Ouvre un site pour te connecter, puis vérifie la session. "
            "Les mots de passe restent dans Chrome.",
            bg=BG,
            fg=MUT,
            font=(_theme.FONT_UI, 13),
            anchor="w",
            justify="left",
            wraplength=700,
        ).pack(fill="x", padx=28, pady=(2, 4))

        bar = CF(w, bg=BG)
        bar.pack(fill="x", padx=28, pady=(0, 4))
        CB(
            bar,
            text="Ouvrir la connexion",
            command=lambda: self._acces_open(w),
            bg=ACC,
            fg=ACC_TX,
            activebackground=ACC_H,
            relief="flat",
            cursor="hand2",
        ).pack(side="left")
        CB(
            bar,
            text="Vérifier les sessions",
            command=lambda: self.run_step([PY, "acces.py", "--check"], "Vérif sessions"),
            bg=BTN,
            fg=TX,
            activebackground=BTN_H,
            relief="flat",
            cursor="hand2",
        ).pack(side="left", padx=18)
        CB(
            bar,
            text="Saisir une clé d'API",
            command=lambda: self.run_step(
                [PY, "acces.py", "--set-key", "francetravail"], "Clé API"
            ),
            bg=BTN,
            fg=TX,
            activebackground=BTN_H,
            relief="flat",
            cursor="hand2",
        ).pack(side="left")
        CB(
            bar,
            text="Rafraîchir",
            command=lambda: w._reload(),
            bg=BTN,
            fg=TX,
            activebackground=BTN_H,
            relief="flat",
            cursor="hand2",
        ).pack(side="right")

        cols = ("site", "id", "sess", "date")
        tv = ttk.Treeview(w, columns=cols, show="headings", selectmode="browse")
        for k, lbl, wd in (
            ("site", "Site", 300),
            ("id", "Identifiant (email)", 260),
            ("sess", "Dernier contrôle", 160),
            ("date", "Vérifié le", 120),
        ):
            tv.heading(k, text=lbl)
            tv.column(k, width=wd, anchor="w", stretch=(k == "id"))
        tv.pack(fill="both", expand=True, padx=28, pady=12)
        tv.tag_configure("ok", foreground=TX_OK)
        tv.tag_configure("ko", foreground=TX_BAD)
        tv.tag_configure("ancien", foreground=TX_AMBRE)
        w._tv = tv

        keys = CL(w, text="", bg=BG, fg=MUT, font=(_theme.FONT_UI, 13), anchor="w", justify="left")
        keys.pack(fill="x", padx=28, pady=(0, 8))

        def reload_():
            import importlib.util as _iu

            spec = _iu.spec_from_file_location("acces", SCRIPTS / "acces.py")
            m = _iu.module_from_spec(spec)
            spec.loader.exec_module(m)
            try:
                comptes = json.loads((SCRIPTS / "comptes.json").read_text(encoding="utf-8"))
            except Exception:
                comptes = {}
            tv.delete(*tv.get_children())
            for host in m.SITES_CONNEXION:
                e = comptes.get(host) or {}
                s = str(e.get("session") or "?")
                label, tag = _session_presentation(s, e.get("session_verif"))
                tv.insert(
                    "",
                    "end",
                    values=(
                        host,
                        e.get("identifiant") or "—",
                        label,
                        e.get("session_verif") or "—",
                    ),
                    tags=(tag,),
                )
            kp = SCRIPTS / "api_keys.json"
            try:
                k = json.loads(kp.read_text(encoding="utf-8")) if kp.exists() else {}
            except Exception:
                k = {}
            ft = "✓ installée" if (SCRIPTS / "francetravail.json").exists() else "✗ absente"
            noms = ", ".join(sorted(k)) if k else "aucune"
            keys.configure(
                text=f"Clés d'API enregistrées : {noms}   ·   France Travail : {ft}"
                "   (les valeurs ne sont jamais affichées)"
            )

        w._reload = reload_
        reload_()
        w.pack(fill="both", expand=True)

    def _acces_open(self, w):
        """Ouvre la page de connexion du site sélectionné dans le navigateur."""
        sel = w._tv.selection()
        if not sel:
            self._log("Selectionne d'abord un site dans la liste.\n")
            return
        host = w._tv.item(sel[0], "values")[0]
        self.run_step([PY, "acces.py", "--open", host], f"Connexion {host}")

    # sites d'OFFRES généraux (boards) — PAS des entreprises
    BOARD_HOSTS = (
        "linkedin",
        "indeed",
        "welcometothejungle",
        "glassdoor",
        "efinancialcareers",
        "wizbii",
        "jobteaser",
        "hellowork",
        "apec.fr",
        "meteojob",
        "monster",
        "jobs.smartrecruiters",
        "engagement-jeunes",
        "wttj",
    )

    def _is_board(self, url):
        return any(b in url.lower() for b in self.BOARD_HOSTS)

    def _domains_file(self):
        F = SCRIPTS / "unique_domains.txt"
        try:
            return F, [
                l.split("|", 1)[-1].strip()
                for l in F.read_text(encoding="utf-8").splitlines()
                if l.strip()
            ]
        except Exception:
            return F, []

    def _companies_panel(self):
        """🏢 ENTREPRISES (boards exclus → panneau Sites) : tableau à colonnes,
        Entreprise | Type | Offres en queue | ATS | 🔗 Lien (dernière, clic = ouvre)."""
        self._hide_all()
        if "companies" in self._panels:
            w = self._panels["companies"]
            w._reload()
            w.pack(fill="both", expand=True)
            return
        w = CF(self.main, bg=WORK)
        self._panels["companies"] = w
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
        CL(top, text="Entreprises à scraper", bg=BG, fg="#b45309", font=(_theme.FONT_UI, 16)).pack(
            side="left", padx=28
        )
        w._count = CL(top, text="", bg=BG, fg=MUT)
        w._count.pack(side="right", padx=24)
        CL(
            w,
            text="Sites CARRIÈRE d'entreprises (les sites d'offres généraux type LinkedIn/WTJ/Indeed "
            "sont dans « Sites d'offres »). Clic sur la colonne Lien = ouvre le site.",
            bg=BG,
            fg=MUT,
            font=(_theme.FONT_UI, 13),
            anchor="w",
            justify="left",
        ).pack(fill="x", padx=28)
        cols = ("ent", "dom", "type", "offres", "ats", "url")
        tv = ttk.Treeview(w, columns=cols, show="headings", selectmode="browse")
        for k, lbl, wd, anc in (
            ("ent", "Entreprise", 180, "w"),
            ("dom", "Domaine", 95, "w"),
            ("type", "Type", 95, "w"),
            ("offres", "Offres en queue", 95, "center"),
            ("ats", "ATS", 100, "w"),
            ("url", "Lien", 400, "w"),
        ):
            tv.heading(k, text=lbl)
            tv.column(k, width=wd, anchor=anc, stretch=(k == "url"))
        tv.pack(fill="both", expand=True, padx=28, pady=18)
        tv.tag_configure("odd", background=ROW1)
        tv.tag_configure("even", background=ROW0)

        def company_name(u):
            host = urlparse(u).netloc.lower()
            for p in (
                "careers.",
                "jobs.",
                "recrutement.",
                "talents.",
                "career.",
                "www.",
                "rejoindre-",
                "group.",
            ):
                host = host.replace(p, "")
            return host.split(".")[0].replace("-", " ").title()

        def site_type(u):
            h = urlparse(u).netloc.lower()
            return (
                "carrières"
                if any(
                    h.startswith(p)
                    for p in ("careers.", "jobs.", "recrutement.", "talents.", "career.")
                )
                or any(
                    s in u.lower()
                    for s in ("/careers", "/carriere", "/recrutement", "/nous-rejoindre")
                )
                else "corporate"
            )

        def ats_of(u):
            for a in (
                "smartrecruiters",
                "talent-soft",
                "talentsoft",
                "workday",
                "breezy",
                "greenhouse",
                "lever.co",
                "recruitee",
                "ashby",
                "icims",
                "successfactors",
                "teamtailor",
            ):
                if a in u.lower():
                    return a.split(".")[0]
            return "—"

        def offers_stats(u):
            """(nb offres en queue, domaine majoritaire) pour ce site."""
            root_d = urlparse(u).netloc.lower().replace("www.", "")
            core = root_d.split(".")[-2] if "." in root_d else root_d  # axa-im.com -> axa-im
            n = 0
            doms = {}
            for o in self.offers:
                ou = (o.get("url") or "").lower()
                if core and core in ou:
                    n += 1
                    d = DOM_SHORT.get(o.get("domaine"), o.get("domaine") or "")
                    if d:
                        doms[d] = doms.get(d, 0) + 1
            dom = max(doms, key=doms.get) if doms else "—"
            return n, dom

        def reload():
            for r in tv.get_children():
                tv.delete(r)
            _, urls = self._domains_file()
            ents = [u for u in urls if not self._is_board(u)]
            for i, u in enumerate(sorted(ents, key=company_name)):
                n, dom = offers_stats(u)
                tv.insert(
                    "",
                    "end",
                    values=(company_name(u), dom, site_type(u), n, ats_of(u), u),
                    tags=("odd" if i % 2 else "even",),
                )
            w._count.configure(
                text=f"{len(ents)} entreprises · {sum(1 for u in urls if self._is_board(u))} boards (→ Sites d'offres)"
            )

        w._reload = reload

        def click(e):
            if tv.identify_region(e.x, e.y) != "cell":
                return
            if tv.identify_column(e.x) != "#6":
                return
            it = tv.identify_row(e.y)
            if it:
                webbrowser.open(tv.item(it)["values"][5])
                self._log(f"🌐 {tv.item(it)['values'][5][:70]}\n")

        tv.bind("<Button-1>", click)

        bar = CF(w, bg=BG)
        bar.pack(fill="x", padx=28, pady=(0, 10))
        ent = CE(bar, bg=ROW0, fg=TX, insertbackground=TX, relief="flat", width=60)
        ent.pack(side="left", ipady=4, fill="x", expand=True)

        def add():
            v = ent.get().strip()
            if not v.startswith("http"):
                self._log("✗ URL http requise (site carrière de l'entreprise)\n")
                return
            if self._is_board(v):
                self._log("↪ c'est un site d'offres général → ajoute-le dans « Sites d'offres »\n")
                return
            F, urls = self._domains_file()
            if v in urls:
                self._log("déjà présent\n")
                return
            F.write_text(("\n".join(urls + [v])).strip() + "\n", encoding="utf-8")
            self._log(f"＋ entreprise ajoutée : {v}\n")
            reload()

        def dele():
            it = tv.focus()
            if not it:
                return
            v = tv.item(it)["values"][5]
            F, urls = self._domains_file()
            F.write_text("\n".join(u for u in urls if u != v).strip() + "\n", encoding="utf-8")
            self._log(f"－ retiré : {v}\n")
            reload()

        ent.bind("<Return>", lambda e: add())
        CB(
            bar,
            text="Ajouter",
            command=add,
            bg=ACC,
            fg=ACC_TX,
            activebackground=ACC_H,
            relief="flat",
            cursor="hand2",
        ).pack(side="left", padx=18)
        CB(
            bar,
            text="Retirer",
            command=dele,
            bg=DEL,
            fg=DEL_TX,
            activebackground=DEL_H,
            relief="flat",
            cursor="hand2",
        ).pack(side="left", padx=6)
        CB(
            bar,
            text="Scraper ces sites",
            command=lambda: self.run_step(
                [PY, "scrape_jobs.py", "--headless"], "Scrape sites entreprises"
            ),
            bg=ACC,
            fg=ACC_TX,
            relief="flat",
            cursor="hand2",
        ).pack(side="left", padx=28)
        reload()
        w.pack(fill="both", expand=True)

    def _sources_panel(self):
        """Sources du Scan offres (job_sources) : mots-clés + slugs ATS. sources_config.json."""
        CFG = SCRIPTS / "sources_config.json"

        def _cfg():
            try:
                return json.loads(CFG.read_text(encoding="utf-8"))
            except Exception:
                # seed depuis les défauts du module
                sys.path.insert(0, str(SCRIPTS))
                try:
                    from jobhunter import sources as js

                    return {"keywords": list(js.KEYWORDS), "ats_slugs": dict(js.ATS_SLUGS)}
                except Exception:
                    return {"keywords": [], "ats_slugs": {}}

        def _save(c):
            CFG.write_text(json.dumps(c, ensure_ascii=False, indent=1), encoding="utf-8")

        def add(v):
            if ":" not in v:
                return (
                    "✗ format « kw: mots clés » (recherche LinkedIn/WTJ), "
                    "« greenhouse|lever|ashby|recruitee|smartrecruiters: slug » (API ATS) "
                    "ou « board: https://… » (site d'offres scanné par le Scrape)"
                )
            kind, val = [s.strip() for s in v.split(":", 1)]
            c = _cfg()
            if kind == "kw":
                if val not in c.setdefault("keywords", []):
                    c["keywords"].append(val)
            elif kind in ("greenhouse", "lever", "ashby", "recruitee", "smartrecruiters"):
                if val not in c.setdefault("ats_slugs", {}).setdefault(kind, []):
                    c["ats_slugs"][kind].append(val)
            elif kind == "board":
                if not val.startswith("http"):
                    return "✗ board: URL http requise"
                F, urls = self._domains_file()
                if val in urls:
                    return "déjà présent"
                F.write_text(("\n".join(urls + [val])).strip() + "\n", encoding="utf-8")
                return f"＋ board ajouté : {val}"
            else:
                return f"✗ type inconnu « {kind} »"
            _save(c)

        def dele(v):
            if ":" not in v:
                return
            kind, val = [s.strip() for s in v.split(":", 1)]
            if kind == "board":
                F, urls = self._domains_file()
                F.write_text(
                    "\n".join(u for u in urls if u != val).strip() + "\n", encoding="utf-8"
                )
                return
            c = _cfg()
            if kind == "kw" and val in c.get("keywords", []):
                c["keywords"].remove(val)
            elif val in c.get("ats_slugs", {}).get(kind, []):
                c["ats_slugs"][kind].remove(val)
            _save(c)

        # ── tableau à colonnes : Type | Source | Offres trouvées | 🔗 Lien ──
        self._hide_all()
        if "sources" in self._panels:
            w = self._panels["sources"]
            w._reload()
            w.pack(fill="both", expand=True)
            return
        w = CF(self.main, bg=WORK)
        self._panels["sources"] = w
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
        CL(
            top, text="Sites d'offres généraux", bg=BG, fg="#b45309", font=(_theme.FONT_UI, 16)
        ).pack(side="left", padx=28)
        w._count = CL(top, text="", bg=BG, fg=MUT)
        w._count.pack(side="right", padx=24)
        CL(
            w,
            text="Sources du Scan : « kw: … » = recherche LinkedIn public + WTJ ·"
            "« greenhouse|lever|ashby|recruitee|smartrecruiters: slug » = API ATS · "
            "« board: https://… » = site scanné par « Scrape les sites ». Clic sur Lien = ouvre.",
            bg=BG,
            fg=MUT,
            font=(_theme.FONT_UI, 13),
            anchor="w",
            justify="left",
        ).pack(fill="x", padx=28)
        tv = ttk.Treeview(
            w, columns=("type", "src", "offres", "url"), show="headings", selectmode="browse"
        )
        for k, lbl, wd, anc in (
            ("type", "Type", 120, "w"),
            ("src", "Source", 260, "w"),
            ("offres", "Offres en queue", 100, "center"),
            ("url", "Lien", 420, "w"),
        ):
            tv.heading(k, text=lbl)
            tv.column(k, width=wd, anchor=anc, stretch=(k == "url"))
        tv.pack(fill="both", expand=True, padx=28, pady=18)
        tv.tag_configure("odd", background=ROW1)
        tv.tag_configure("even", background=ROW0)

        ATS_URL = {
            "greenhouse": "https://boards.greenhouse.io/{s}",
            "lever": "https://jobs.lever.co/{s}",
            "ashby": "https://jobs.ashbyhq.com/{s}",
            "recruitee": "https://{s}.recruitee.com",
            "smartrecruiters": "https://careers.smartrecruiters.com/{s}",
        }

        def n_src(needle):
            return sum(1 for o in self.offers if needle in (o.get("source") or "").lower())

        def rows():
            c = _cfg()
            out = []
            for k in c.get("keywords", []):
                n = n_src(f"linkedin-search:{k}".lower()) + n_src(f"wtj-search:{k}".lower())
                out.append(
                    ("kw", k, n, "https://www.linkedin.com/jobs/search?keywords=" + quote(k))
                )
            for kind, slugs in c.get("ats_slugs", {}).items():
                for s in slugs:
                    out.append(
                        (
                            kind,
                            s,
                            n_src(f"{kind}:{s}".lower()),
                            ATS_URL.get(kind, "{s}").format(s=s),
                        )
                    )
            _, urls = self._domains_file()
            for u in urls:
                if self._is_board(u):
                    host = urlparse(u).netloc.replace("www.", "")
                    n = sum(1 for o in self.offers if host and host in (o.get("url") or ""))
                    out.append(("board", host, n, u))
            return out

        def reload():
            for r in tv.get_children():
                tv.delete(r)
            rs = rows()
            for i, r in enumerate(rs):
                tv.insert("", "end", values=r, tags=("odd" if i % 2 else "even",))
            w._count.configure(text=f"{len(rs)} sources")

        w._reload = reload

        def click(e):
            if tv.identify_region(e.x, e.y) != "cell" or tv.identify_column(e.x) != "#4":
                return
            it = tv.identify_row(e.y)
            if it:
                webbrowser.open(tv.item(it)["values"][3])
                self._log(f"🌐 {str(tv.item(it)['values'][3])[:70]}\n")

        tv.bind("<Button-1>", click)

        bar = CF(w, bg=BG)
        bar.pack(fill="x", padx=28, pady=(0, 10))
        ent = CE(bar, bg=ROW0, fg=TX, insertbackground=TX, relief="flat", width=60)
        ent.pack(side="left", ipady=4, fill="x", expand=True)

        def do_add():
            msg = add(ent.get().strip())
            self._log((msg or f"＋ ajouté : {ent.get().strip()}") + "\n")
            ent.delete(0, "end")
            reload()

        def do_del():
            it = tv.focus()
            if not it:
                return
            t, s, _n, u = tv.item(it)["values"]
            dele(f"{t}: {u if t == 'board' else s}")
            self._log(f"－ retiré : {t}: {s}\n")
            reload()

        ent.bind("<Return>", lambda e: do_add())
        CB(
            bar,
            text="Ajouter",
            command=do_add,
            bg=ACC,
            fg=ACC_TX,
            activebackground=ACC_H,
            relief="flat",
            cursor="hand2",
        ).pack(side="left", padx=18)
        CB(
            bar,
            text="Retirer",
            command=do_del,
            bg=DEL,
            fg=DEL_TX,
            activebackground=DEL_H,
            relief="flat",
            cursor="hand2",
        ).pack(side="left", padx=6)
        CB(
            bar,
            text="Scanner maintenant",
            command=lambda: self.run_step([PY, "-m", "jobhunter.sources", "--all"], "Scan offres"),
            bg=ACC,
            fg=ACC_TX,
            relief="flat",
            cursor="hand2",
        ).pack(side="left", padx=28)
        reload()
        w.pack(fill="both", expand=True)

    def _add_offer_url(self):
        """Analyse le lien collé (add_offer.py) : titre+entreprise+description → queue → CV/lettre."""
        url = self.e_url.get().strip()
        if not url.startswith("http"):
            self._log("✗ colle une URL http d'offre.\n")
            return
        self.b_addurl.configure(text="Analyse…", state="disabled")
        self._log(f"🔎 analyse de l'offre : {url[:70]}…\n")

        def work():
            try:
                r = subprocess.run(
                    [PY, "add_offer.py", "--url", url],
                    cwd=str(SCRIPTS),
                    capture_output=True,
                    text=True,
                    timeout=300,
                    encoding="utf-8",
                    errors="replace",
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                out = (r.stdout or "") + (r.stderr or "")
            except Exception as e:
                out = f"! {type(e).__name__}"
            self.root.after(0, lambda: done(out))

        def done(out):
            for line in out.splitlines():
                if line.strip():
                    self._log("  " + line.strip()[:100] + "\n")
            self.b_addurl.configure(text="Ajouter une offre", state="normal")
            self.e_url.delete(0, "end")
            self.load_offers()

        threading.Thread(target=work, daemon=True).start()
