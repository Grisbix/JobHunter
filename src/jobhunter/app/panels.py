"""Panels: statistics, site access, companies, sources, adding an offer by URL.

Part of jobhunter.app (former JobHunter.pyw, phase 3.7)."""

import importlib
import json
import subprocess
import threading
import webbrowser
from tkinter import ttk
from typing import Any
from urllib.parse import quote, urlparse

from jobhunter import root as _racine
from jobhunter.app import common as _commun
from jobhunter.app import inventory as _inventaire
from jobhunter.app import theme as _theme
from jobhunter.app._app_type import AppTypee
from jobhunter.app.common import PAS_INTERESSE, PY, QUEUE, SCRIPTS
from jobhunter.app.language import t as _t
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
from jobhunter.links import existe as _doc_existe
from jobhunter.storage import queue as queue_io


def _t_etat(etat: str) -> str:
    """A source state ("ok — 3 offres", "refusé — pas avant le 14/11"), translated.

    The verdict comes from the catalogue; the rest, made of numbers and dates, is
    translated word for word.
    """
    tete, sep, reste = etat.partition(" — ")
    for mot in ("pas avant le", "offres", "offre", "vérifie-la"):
        reste = reste.replace(mot, _t(mot))
    return str(_t(tete)) + sep + reste


def _date_fr(iso: Any) -> str:
    """ "2026-10-19…" → "19/10/2026"; "" if empty or unreadable."""
    t = str(iso or "")[:10]
    return f"{t[8:10]}/{t[5:7]}/{t[:4]}" if len(t) == 10 and t[4] == "-" else ""


# What the connection test found (sources.connexion.Resultat.etat), said plainly.
MESSAGES_TEST = {
    "ok": "{nom} : connexion vérifiée, la clé fonctionne.",
    "absente": "{nom} : aucune clé enregistrée (Saisir la clé).",
    "refusee": "{nom} : clé refusée par le service — vérifie-la ou crée-en une nouvelle.",
    "quota": "{nom} : quota atteint — la clé est bonne, réessaie demain.",
    "panne": "{nom} : le service répond mais en erreur — réessaie plus tard.",
    "reseau": "{nom} : pas de réponse (hors ligne ?).",
}


class PanneauxMixin:
    def _hide_all(self: "AppTypee") -> None:
        """Hides all the panels (dash, viewer, detail, lists)."""
        self.dash.pack_forget()
        if self.viewer is not None:
            self.viewer.pack_forget()
        if self._dv is not None:
            self._dv.pack_forget()
        for p in self._panels.values():
            p.pack_forget()
        self._depot_vers_profil = False  # a dropped CV asks again what to do with it

    def _show_dash(self: "AppTypee") -> None:
        self._hide_all()
        if getattr(self, "_viewer_close", None):
            self._viewer_close()  # unlocks the displayed pdf
        self.dash.pack(fill="both", expand=True)
        self._nav_actif("offres")

    def _stats_panel(self: "AppTypee") -> None:
        """📊 STATS: summary view of the queue (the data exists in
        apply_queue.json + suivi.json but was visible nowhere)."""
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
            text="Rafraîchir",
            command=lambda: w._reload(),
            bg=BTN,
            fg=TX,
            activebackground=BTN_H,
            relief="flat",
            cursor="hand2",
        ).pack(side="right", padx=24)

        # Equal-column grid: ten cards side by side with pack() went
        # out of the window, and the last three (Entretien, Refus…) were cut off.
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
            ("cat", "Catégorie", 460, "w"),  # 300 cut "dossiers préparés (envoi à…"
            ("n", "Nb", 70, "center"),
            ("bar", "Répartition", 520, "w"),
        ):
            tv.heading(k, text=_t(lbl))
            tv.column(k, width=wd, anchor=anc, stretch=(k == "bar"))  # type: ignore[call-overload]  # typeshed wants a Literal for anchor
        tv.pack(fill="both", expand=True)
        tv.tag_configure("h", foreground=ACC, font=(_theme.FONT_UI, 13, "bold"))
        w._tv = tv

        def reload_() -> None:
            # re-reads the DISK: the pipeline runs in the background, self.offers may be stale
            try:
                q = queue_io.charger(QUEUE)
            except Exception:
                q = list(self.offers)
            try:
                sv = (
                    importlib.import_module("jobhunter.storage.applications").charger(_commun.SUIVI)
                    if _commun.SUIVI.exists()
                    else {}
                )
            except Exception:
                sv = {}
            # Key "s", not "statut": it is what _set_statut and
            # suivi_io write. With "statut", the Postulé/Relancé/Entretien/
            # Refus cards showed 0 while ten applications were tracked.
            st = [str((v or {}).get("s") or "").lower() for v in sv.values()]
            ok = [
                o for o in q if str(o.get("link_status") or "").upper() not in ("MORT", "EXPIREE")
            ]

            # READY TO SEND = the only figure that decides an evening.
            # "fit >= 8" alone is misleading: an offer whose CV or letter
            # no longer exists ON DISK cannot be sent, and the queue
            # may well keep the reference of a deleted file.
            def _fichier(u: Any) -> Any:
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

            def section(titre: Any, pairs: Any) -> None:
                if not pairs:
                    return
                tv.insert("", "end", values=(_t(titre), "", ""), tags=("h",))
                mx = max((n for _, n in pairs), default=0) or 1
                for nom, n in pairs:
                    nom = _t(nom)  # a label of the app; data values pass through as they are
                    bar = "█" * max(0, round(38 * n / mx))
                    pct = f"{100 * n / len(q):.0f}%" if q else ""
                    tv.insert("", "end", values=(f"   {nom}", n, f"{bar} {pct}"))

            def count(key: Any, src: Any = None) -> Any:
                d: dict[str, Any] = {}
                for o in src or q:
                    v = str(o.get(key) or "—").strip() or "—"
                    d[v] = d.get(v, 0) + 1
                return sorted(d.items(), key=lambda x: -x[1])

            # What separates a well-scored offer from a sendable one. Without this
            # detail, "487 a fit >= 8" suggests that everything is ready.
            section(
                "▶ Sur les offres à fit ≥ 8",
                [
                    ("dossiers préparés (envoi à vérifier)", len(_pretes)),
                    ("bloquees : CV ou lettre absent du disque", len(_sans_doc)),
                    ("bloquees : description trop courte", len(_sans_desc)),
                    ("bloquees : lien jamais verifie", len(_lien_douteux)),
                ],
            )
            # From sending to answer (status history, 3.15): the figures that say
            # whether the search works, not only how much it collects.
            from jobhunter import funnel as _funnel

            e = _funnel.entonnoir(sv, {queue_io.oid(o): o for o in q})
            if e["envoyees"]:
                tv.insert(
                    "",
                    "end",
                    values=(_t("▶ Candidatures envoyées"), e["envoyees"], ""),
                    tags=("h",),
                )
                taux = f"{e['taux']:.0%}" if e["taux"] is not None else ""
                for lib, n, txt in (
                    (_t("réponses (entretien ou refus)"), e["reponses"], taux),
                    (_t("entretiens"), e["entretiens"], ""),
                    (_t("sans réponse depuis 30 jours"), e["silence"], ""),
                    (
                        _t("délai médian de réponse"),
                        ""
                        if e["delai_median"] is None
                        else _t("{n} j").format(n=f"{e['delai_median']:.0f}"),
                        _t("sur {n} réponse(s) datée(s)").format(n=len(e["delais"]))
                        if e["delais"]
                        else _t("dates d'envoi enregistrées depuis la 3.15"),
                    ),
                ):
                    tv.insert("", "end", values=(f"   {lib}", n, txt))
                for champ, titre in (
                    ("contrat", "Réponses par contrat"),
                    ("domaine", "Réponses par domaine"),
                ):
                    lignes = [x for x in e["par"][champ] if x[1]][:6]
                    if len(lignes) < 2:
                        continue
                    tv.insert("", "end", values=(_t(titre), "", ""), tags=("h",))
                    for val, env, rep, ent in lignes:
                        tv.insert(
                            "",
                            "end",
                            values=(
                                f"   {val}",
                                env,
                                _t("{r} réponse(s), {e} entretien(s) · {p}").format(
                                    r=rep, e=ent, p=f"{rep / env:.0%}"
                                ),
                            ),
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

    def _acces_panel(self: "AppTypee") -> None:
        """ACCESS: what each source of the collection needs, and its last measured state.

        Two tabs. "Collecte des offres": free access or API key, and the verdict of
        each source's last collection (`_rendement.jsonl`) — refusal, limit, nothing
        to take; keys are entered there and a single source can be collected there.
        "Connexions pour candidater": the sites where one logs in oneself.
        No key is read back here: only its presence counts (jobhunter.api_keys), and
        passwords stay in Chrome's manager."""
        self._hide_all()
        if "acces" in self._panels:
            w = self._panels["acces"]
            w._reload()
            w.pack(fill="both", expand=True)
            return
        import customtkinter as ctk

        from jobhunter import api_keys as cles_api
        from jobhunter.app.keys import saisir_cle

        w = CF(self.main, bg=WORK)
        self._panels["acces"] = w
        top = CF(w, bg=BG)
        top.pack(fill="x")
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

        pages: dict[str, Any] = {}
        onglets = (_t("Collecte des offres"), _t("Connexions pour candidater"))

        def montrer(nom: str) -> None:
            for cle_, page in pages.items():
                if cle_ == nom:
                    page.pack(fill="both", expand=True)
                else:
                    page.pack_forget()

        choix = ctk.CTkSegmentedButton(
            w,
            values=list(onglets),
            command=montrer,
            selected_color=ACC,
            selected_hover_color=ACC_H,
            font=(_theme.FONT_UI, 13),
        )
        choix.pack(anchor="w", padx=28, pady=(10, 4))

        # ── Tab 1: the collection ─────────────────────────────────────────────
        col = CF(w, bg=WORK)
        pages[onglets[0]] = col
        CL(
            col,
            text="État de la dernière collecte de chaque source. Un refus n'est pas "
            "réessayé avant 30 jours. Double-clic sur une source à clé : saisir sa clé.",
            bg=BG,
            fg=MUT,
            font=(_theme.FONT_UI, 13),
            anchor="w",
            justify="left",
            wraplength=900,
        ).pack(fill="x", padx=28, pady=(4, 0))
        cols_s = ("src", "acces", "etat", "le")
        tvs = ttk.Treeview(
            col,
            columns=cols_s,
            show="headings",
            selectmode="browse",
            height=len(_inventaire.SOURCES_COLLECTE),
        )
        for k, lbl, wd in (
            ("src", "Source", 420),
            ("acces", "Accès", 80),
            ("etat", "Dernier état", 300),
            ("le", "Collecte du", 130),
        ):
            tvs.heading(k, text=_t(lbl))
            tvs.column(k, width=wd, anchor="w", stretch=(k == "etat"))
        tvs.pack(fill="x", padx=28, pady=(0, 6))
        tvs.tag_configure("ok", foreground=TX_OK)
        tvs.tag_configure("ko", foreground=TX_BAD)
        tvs.tag_configure("ancien", foreground=TX_AMBRE)
        etats: dict[str, _inventaire.EtatSource] = {}

        def choisie() -> str | None:
            sel = tvs.selection()
            if not sel:
                self._log("Sélectionne d'abord une source dans la liste.\n")
                return None
            return str(sel[0])

        def saisir(nom: str | None = None) -> None:
            nom = nom or choisie()
            if nom is None:
                return
            if nom not in cles_api.CLES:
                self._log(
                    f"{_t(etats[nom].libelle)} : " + _t("accès libre, aucune clé à saisir.") + "\n"
                )
                return
            saisir_cle(self, nom, lambda: w._reload())

        def collecter() -> None:
            nom = choisie()
            if nom is None:
                return
            e = etats[nom]
            if e.bloque:
                # A refused entry stops: no new attempt before 30 days (ADR 0004).
                self._log(f"⛔ {_t(e.libelle)} : {_t_etat(e.etat)}\n")
                return
            if nom in cles_api.CLES and not cles_api.presente(_racine.dossier_cles(), nom):
                self._log(f"{_t(e.libelle)} : " + _t("saisis d'abord sa clé.") + "\n")
                return
            self.run_step(
                [PY, "-m", "jobhunter.sources", _inventaire.DRAPEAUX_COLLECTE[nom]],
                f"Collecte {_t(e.libelle)}",
            )

        def tester() -> None:
            """One minimal request with the saved key, in the background (sources.connexion)."""
            nom = choisie()
            if nom is None:
                return
            if nom not in cles_api.CLES:
                self._log(
                    f"{_t(etats[nom].libelle)} : " + _t("accès libre, aucune clé à saisir.") + "\n"
                )
                return
            libelle = _t(etats[nom].libelle)
            self._log(
                _t("Test de {nom} : une requête, aucune offre importée…").format(nom=libelle) + "\n"
            )

            def tache() -> None:
                from jobhunter.sources import connexion as _cx

                try:
                    r = _cx.tester(nom)
                except Exception as e:  # never the message: it may hold a URL with the key
                    r = _cx.Resultat("reseau", type(e).__name__)
                texte = _t(MESSAGES_TEST.get(r.etat, r.etat)).format(nom=libelle)
                ligne = ("✓ " if r.etat == "ok" else "✗ ") + texte
                if r.detail:
                    ligne += f" ({r.detail})"
                self.root.after(0, lambda: self._log(ligne + "\n"))

            threading.Thread(target=tache, daemon=True).start()

        tvs.bind("<Double-1>", lambda e: saisir(tvs.identify_row(e.y) or None))
        bar_s = CF(col, bg=BG)
        bar_s.pack(fill="x", padx=28, pady=(0, 10))
        CB(
            bar_s,
            text="Saisir la clé",
            command=saisir,
            bg=ACC,
            fg=ACC_TX,
            activebackground=ACC_H,
            relief="flat",
            cursor="hand2",
        ).pack(side="left")
        CB(
            bar_s,
            text="Tester la connexion",
            command=tester,
            bg=BTN,
            fg=TX,
            activebackground=BTN_H,
            relief="flat",
            cursor="hand2",
        ).pack(side="left", padx=(18, 0))
        CB(
            bar_s,
            text="Collecter cette source",
            command=collecter,
            bg=BTN,
            fg=TX,
            activebackground=BTN_H,
            relief="flat",
            cursor="hand2",
        ).pack(side="left", padx=18)
        CB(
            bar_s,
            text="Rendement des sources",
            command=lambda: self.run_step(
                [PY, "-m", "jobhunter.programs.source_yield"], "Rendement"
            ),
            bg=BTN,
            fg=TX,
            activebackground=BTN_H,
            relief="flat",
            cursor="hand2",
        ).pack(side="left")
        # Calls made today with the shared keys, every profile together (sources.quota).
        from jobhunter.sources import quota as _quota

        usages = []
        for cle_q, libelle in (
            ("adzuna", "Adzuna"),
            ("jooble", "Jooble"),
            ("francetravail", "France Travail"),
        ):
            n, cap = _quota.usage(cle_q), _quota.plafond(cle_q)
            usages.append(f"{libelle} {n}" + (f"/{cap}" if cap else ""))
        CL(
            col,
            text=_t("Appels d'API aujourd'hui (tous profils) : ") + " · ".join(usages),
            bg=BG,
            fg=MUT,
            anchor="w",
        ).pack(fill="x", padx=28, pady=(0, 8))

        # ── Tab 2: the logins for applying ────────────────────────────────────
        cnx = CF(w, bg=WORK)
        pages[onglets[1]] = cnx
        CL(
            cnx,
            text="Tu te connectes toi-même ; les mots de passe restent dans Chrome.",
            bg=BG,
            fg=MUT,
            font=(_theme.FONT_UI, 13),
            anchor="w",
            justify="left",
            wraplength=900,
        ).pack(fill="x", padx=28, pady=(4, 0))
        cols = ("site", "id", "sess", "date")
        tv = ttk.Treeview(cnx, columns=cols, show="headings", selectmode="browse", height=8)
        for k, lbl, wd in (
            ("site", "Site", 300),
            ("id", "Identifiant (email)", 260),
            ("sess", "Session", 170),
            ("date", "Vérifiée le", 130),
        ):
            tv.heading(k, text=_t(lbl))
            tv.column(k, width=wd, anchor="w", stretch=(k == "id"))
        tv.pack(fill="x", padx=28, pady=(0, 6))
        tv.tag_configure("ok", foreground=TX_OK)
        tv.tag_configure("ko", foreground=TX_BAD)
        tv.tag_configure("ancien", foreground=TX_AMBRE)
        w._tv = tv
        bar = CF(cnx, bg=BG)
        bar.pack(fill="x", padx=28, pady=(0, 10))
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
            command=lambda: self.run_step(
                [PY, "-m", "jobhunter.programs.access", "--check"], "Vérif sessions"
            ),
            bg=BTN,
            fg=TX,
            activebackground=BTN_H,
            relief="flat",
            cursor="hand2",
        ).pack(side="left", padx=18)

        def reload_() -> None:
            from jobhunter.programs import access as m
            from jobhunter.sources import source_yield as _rendement

            sel = tvs.selection()
            tvs.delete(*tvs.get_children())
            etats.clear()
            journal = _rendement.lire_journal(_racine.dans(SCRIPTS, "_rendement.jsonl"))
            fichiers = {c.fichier: c.nom for c in cles_api.CLES.values()}
            for etat in _inventaire.etat_sources(
                journal, lambda f: cles_api.presente(_racine.dossier_cles(), fichiers[f])
            ):
                etats[etat.source] = etat
                tvs.insert(
                    "",
                    "end",
                    iid=etat.source,
                    values=(
                        _t(etat.libelle),
                        _t(etat.acces),
                        _t_etat(etat.etat),
                        _date_fr(etat.le) or "—",
                    ),
                    tags=(etat.gravite,),
                )
            if sel and tvs.exists(sel[0]):
                tvs.selection_set(sel[0])
            try:
                comptes = json.loads(
                    (_racine.dans(SCRIPTS, "comptes.json")).read_text(encoding="utf-8")
                )
            except Exception:
                comptes = {}
            tv.delete(*tv.get_children())
            for host in m.SITES_CONNEXION:
                e = comptes.get(host) or {}
                s = str(e.get("session") or "?")
                label, tag = _session_presentation(s, e.get("session_verif"))
                if not e.get("session_verif"):
                    label, tag = "Jamais vérifié", ""
                label = _t(label)
                tv.insert(
                    "",
                    "end",
                    values=(
                        host,
                        e.get("identifiant") or "—",
                        label,
                        _date_fr(e.get("session_verif")) or "—",
                    ),
                    tags=(tag,),
                )

        w._reload = reload_
        reload_()
        choix.set(onglets[0])
        montrer(onglets[0])
        w.pack(fill="both", expand=True)

    def _acces_open(self: "AppTypee", w: Any) -> None:
        """Opens the login page of the selected site in the browser."""
        sel = w._tv.selection()
        if not sel:
            self._log("Selectionne d'abord un site dans la liste.\n")
            return
        host = w._tv.item(sel[0], "values")[0]
        self.run_step([PY, "-m", "jobhunter.programs.access", "--open", host], f"Connexion {host}")

    # general JOB sites (boards) — NOT companies
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

    def _is_board(self: "AppTypee", url: Any) -> Any:
        return any(b in url.lower() for b in self.BOARD_HOSTS)

    def _domains_file(self: "AppTypee") -> Any:
        F = SCRIPTS / "unique_domains.txt"
        try:
            return F, [
                l.split("|", 1)[-1].strip()
                for l in F.read_text(encoding="utf-8").splitlines()
                if l.strip()
            ]
        except Exception:
            return F, []

    def _companies_panel(self: "AppTypee") -> None:
        """COMPANIES: the feeds really collected and the queue's offers that come from them.

        One row per followed company, read through its recruiting tool (public API:
        `sources_config.json`) or, failing that, through its career site in the
        browser (`unique_domains.txt`). The counts come from jobhunter.app.inventory:
        exact, by source marker. A pasted URL is recognised: an ATS readable through
        an API becomes a feed, another site goes into the list read by the browser."""
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
        w._count = CL(top, text="", bg=BG, fg=MUT)
        w._count.pack(side="right", padx=24)
        CL(
            w,
            text="Chaque entreprise est lue par son outil de recrutement (API publique) "
            "ou, à défaut, par son site carrière. Double-clic : ouvrir sa page. "
            "Les sites d'offres généraux (LinkedIn, WTJ…) sont dans « Sites d'offres ».",
            bg=BG,
            fg=MUT,
            font=(_theme.FONT_UI, 13),
            anchor="w",
            justify="left",
            wraplength=900,
        ).pack(fill="x", padx=28)
        barre_f = CF(w, bg=BG)
        barre_f.pack(fill="x", padx=28, pady=(10, 0))
        filtre = CE(barre_f, bg=ROW0, fg=TX, insertbackground=TX, relief="flat", width=40)
        filtre.configure(placeholder_text=_t("Filtrer : entreprise, outil ou adresse"))
        filtre.pack(side="left", ipady=2)
        filtre.bind("<KeyRelease>", lambda e: w._reload())
        cols = ("ent", "outil", "collecte", "offres", "fit", "derniere", "url")
        tv = ttk.Treeview(w, columns=cols, show="headings", selectmode="browse")
        for k, lbl, wd, anc in (
            ("ent", "Entreprise", 230, "w"),
            ("outil", "Lue par", 150, "w"),
            ("collecte", "Dernière collecte", 210, "w"),
            ("offres", "Offres", 80, "center"),
            ("fit", "Fit max", 95, "center"),
            ("derniere", "Dernière", 130, "center"),
            ("url", "Page", 340, "w"),
        ):
            tv.heading(k, text=_t(lbl))
            tv.column(k, width=wd, anchor=anc, stretch=(k == "url"))  # type: ignore[call-overload]  # typeshed wants a Literal for anchor
        tv.pack(fill="both", expand=True, padx=28, pady=18)
        tv.tag_configure("odd", background=ROW1)
        tv.tag_configure("even", background=ROW0)
        tv.tag_configure("vide", foreground=MUT)
        tv.tag_configure("suspendue", foreground=MUT)
        lignes: dict[str, _inventaire.Flux] = {}

        def _collecte(f: _inventaire.Flux, etat: dict[str, Any], suspendus: set[str]) -> str:
            """The feed's last collection (sources.feeds): suspended, incident, or success."""
            from jobhunter.sources import feeds as _flux

            if f.outil == "site":
                return "—"  # read by the browser, not by a collection pass
            ident = _flux.cle(f.outil, f.cle)
            if ident in suspendus:
                return "⏸ " + _t("suspendue")
            e = etat.get(ident) or {}
            m = _flux.muet(e)
            if m:  # silent for a month: its page may have moved (sources.feeds.muet)
                return f"◌ {m}"
            if e.get("incident"):
                return f"⚠ {e['incident']} ({_date_fr(str(e.get('incident_le', ''))[:10])})"
            if e.get("succes"):
                return f"✓ {_date_fr(str(e['succes'])[:10])} · {e.get('offres', 0)}"
            return "—"

        def _defauts() -> dict[str, Any]:
            from jobhunter.sources import common as _src

            return {
                "ats_slugs": {k: list(v) for k, v in _src.ATS_SLUGS.items()},
                "workday_flux": [list(x) for x in _src.WORKDAY_FLUX],
                "autres_flux": [list(x) for x in _src.AUTRES_FLUX],
            }

        def reload() -> None:
            from jobhunter.sources import common as _src
            from jobhunter.sources import feeds as _flux

            _src._load_cfg()
            tv.delete(*tv.get_children())
            lignes.clear()
            etat = _flux.lire(SCRIPTS / _flux.FICHIER)
            suspendus = _flux.suspendus()
            _, urls = self._domains_file()
            sites = [u for u in urls if not self._is_board(u)]
            flux = _inventaire.flux_suivis(
                _src.ATS_SLUGS, _src.WORKDAY_FLUX, _src.AUTRES_FLUX, sites
            )
            comptes = _inventaire.compter(self.offers, flux)
            ordre = sorted(flux, key=lambda f: (-comptes[f].offres, f.nom.lower()))
            cherche = filtre.get().strip().lower()
            if cherche:
                ordre = [
                    f
                    for f in ordre
                    if cherche
                    in f"{f.nom} {_inventaire.NOMS_OUTILS.get(f.outil, f.outil)} {f.lien}".lower()
                ]
            for i, f in enumerate(ordre):
                c = comptes[f]
                iid = tv.insert(
                    "",
                    "end",
                    values=(
                        f.nom,
                        _t(_inventaire.NOMS_OUTILS.get(f.outil, f.outil)),
                        _collecte(f, etat, suspendus),
                        c.offres,
                        c.meilleur_fit if c.offres else "—",
                        _date_fr(c.derniere) or "—",
                        f.lien,
                    ),
                    tags=("odd" if i % 2 else "even",)
                    + (("vide",) if not c.offres else ())
                    + (("suspendue",) if _flux.cle(f.outil, f.cle) in suspendus else ()),
                )
                lignes[iid] = f
            total = sum(c.offres for c in comptes.values())
            vides = sum(1 for c in comptes.values() if not c.offres)
            texte = _t("{n} entreprises · {t} offres en file · {v} sans offre en file").format(
                n=len(flux), t=total, v=vides
            )
            n_muets = len(_flux.muets(etat, suspendus))
            if n_muets:
                texte += " · ◌ " + _t("{n} muette(s) depuis {j} j").format(
                    n=n_muets, j=_flux.MUET_JOURS
                )
            if cherche:
                texte = f"{len(ordre)} / " + texte
            w._count.configure(text=texte)

        w._reload = reload

        def ouvrir(e: Any) -> None:
            it = tv.identify_row(e.y)
            f = lignes.get(it)
            if f and f.lien:
                webbrowser.open(f.lien)
                self._log(f"🌐 {f.lien[:70]}\n")

        tv.bind("<Double-1>", ouvrir)

        bar = CF(w, bg=BG)
        bar.pack(fill="x", padx=28, pady=(0, 10))
        ent = CE(bar, bg=ROW0, fg=TX, insertbackground=TX, relief="flat", width=60)
        ent.configure(
            placeholder_text=_t("Adresse de sa page carrière, ou nom de l'entreprise (annuaire)")
        )
        ent.pack(side="left", ipady=4, fill="x", expand=True)
        CFG = SCRIPTS / "sources_config.json"

        def _lire_cfg() -> dict[str, Any]:
            try:
                c = json.loads(CFG.read_text(encoding="utf-8"))
                return c if isinstance(c, dict) else {}
            except Exception:
                return {}

        def suivis() -> set[tuple[str, str]]:
            from jobhunter.sources import common as _src

            _src._load_cfg()
            return {(o, str(s).lower()) for o, slugs in _src.ATS_SLUGS.items() for s in slugs}

        def suivre_entree(e: Any) -> None:
            c = _lire_cfg()
            self._log(_inventaire.ajouter_flux(c, _defauts(), (e.outil, e.jeton)) + f" ({e.nom})\n")
            self._jwrite(CFG, c)
            reload()

        def annuaire(texte: str = "") -> None:
            from jobhunter.app.directory import choisir

            choisir(self, texte, suivis, suivre_entree)

        def add() -> None:
            v = ent.get().strip()
            if not v.startswith("http"):
                # A name: it is searched in the Lever, Ashby, Greenhouse directories.
                annuaire(v)
                ent.delete(0, "end")
                return
            if self._is_board(v):
                self._log("↪ c'est un site d'offres général → ajoute-le dans « Sites d'offres »\n")
                return
            trouve = _inventaire.flux_depuis_url(v)
            if trouve:
                c = _lire_cfg()
                self._log(_inventaire.ajouter_flux(c, _defauts(), trouve) + "\n")
                self._jwrite(CFG, c)
            else:
                F, urls = self._domains_file()
                if v in urls:
                    self._log("déjà suivi\n")
                    return
                F.write_text(("\n".join(urls + [v])).strip() + "\n", encoding="utf-8")
                self._log(f"＋ site carrière ajouté, lu par le navigateur : {v}\n")
            ent.delete(0, "end")
            reload()

        def dele() -> None:
            f = lignes.get(tv.focus())
            if f is None:
                self._log("Sélectionne d'abord une entreprise dans la liste.\n")
                return
            if f.outil == "site":
                F, urls = self._domains_file()
                F.write_text(
                    "\n".join(u for u in urls if u != f.cle).strip() + "\n", encoding="utf-8"
                )
            else:
                c = _lire_cfg()
                if not _inventaire.retirer_flux(c, _defauts(), f):
                    self._log(f"✗ {f.nom} : flux introuvable dans sources_config.json\n")
                    return
                self._jwrite(CFG, c)
            self._log(f"－ {f.nom} ne sera plus collectée\n")
            reload()

        def suspendre() -> None:
            """Stops (or resumes) a company's collections; its offers and history stay."""
            from jobhunter.sources import feeds as _flux

            f = lignes.get(tv.focus())
            if f is None:
                self._log(_t("Sélectionne d'abord une entreprise dans la liste.") + "\n")
                return
            if f.outil == "site":
                self._log(_t("Un site lu par le navigateur ne se suspend pas : retire-le.") + "\n")
                return
            c = _lire_cfg()
            ident = _flux.cle(f.outil, f.cle)
            oui = ident not in _flux.suspendus(c)
            _flux.suspendre(c, ident, oui)
            self._jwrite(CFG, c)
            self._log(
                (_t("⏸ {a} suspendue") if oui else _t("▶ {a} reprise")).format(a=f.nom) + "\n"
            )
            reload()

        ent.bind("<Return>", lambda e: add())
        CB(
            bar,
            text="Suivre",
            command=add,
            bg=ACC,
            fg=ACC_TX,
            activebackground=ACC_H,
            relief="flat",
            cursor="hand2",
        ).pack(side="left", padx=(18, 6))
        CB(
            bar,
            text="Annuaire",
            command=lambda: annuaire(ent.get().strip()),
            bg=BTN,
            fg=TX,
            activebackground=BTN_H,
            relief="flat",
            cursor="hand2",
        ).pack(side="left", padx=(0, 12))
        CB(
            bar,
            text="Suspendre / Reprendre",
            command=suspendre,
            bg=BTN,
            fg=TX,
            activebackground=BTN_H,
            relief="flat",
            cursor="hand2",
        ).pack(side="left", padx=6)
        CB(
            bar,
            text="Ne plus suivre",
            command=dele,
            bg=DEL,
            fg=DEL_TX,
            activebackground=DEL_H,
            relief="flat",
            cursor="hand2",
        ).pack(side="left", padx=6)
        CB(
            bar,
            text="Lire les sites carrière",
            command=lambda: self.run_step(
                [PY, "-m", "jobhunter.programs.scrape_jobs", "--headless"],
                "Sites carrière",
            ),
            bg=BTN,
            fg=TX,
            activebackground=BTN_H,
            relief="flat",
            cursor="hand2",
        ).pack(side="left", padx=28)
        reload()
        w.pack(fill="both", expand=True)

    def _sources_panel(self: "AppTypee") -> None:
        """Sources of the offer scan (job_sources): keywords + ATS slugs. sources_config.json."""
        CFG = SCRIPTS / "sources_config.json"

        def _cfg() -> Any:
            try:
                return json.loads(CFG.read_text(encoding="utf-8"))
            except Exception:
                # seed from the module defaults
                try:
                    from jobhunter import sources as js

                    return {"keywords": list(js.KEYWORDS), "ats_slugs": dict(js.ATS_SLUGS)}  # type: ignore[attr-defined]  # KEYWORDS and ATS_SLUGS are lazy values
                except Exception:
                    return {"keywords": [], "ats_slugs": {}}

        def _save(c: Any) -> None:
            CFG.write_text(json.dumps(c, ensure_ascii=False, indent=1), encoding="utf-8")

        def add(v: Any) -> Any:
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

        def dele(v: Any) -> None:
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

        # ── column table: Type | Source | Offers found | 🔗 Link ──
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
            tv.heading(k, text=_t(lbl))
            tv.column(k, width=wd, anchor=anc, stretch=(k == "url"))  # type: ignore[call-overload]  # typeshed wants a Literal for anchor
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

        def n_src(needle: Any) -> Any:
            return sum(1 for o in self.offers if needle in (o.get("source") or "").lower())

        def rows() -> Any:
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

        def reload() -> None:
            for r in tv.get_children():
                tv.delete(r)
            rs = rows()
            for i, r in enumerate(rs):
                tv.insert("", "end", values=r, tags=("odd" if i % 2 else "even",))
            w._count.configure(text=f"{len(rs)} sources")

        w._reload = reload

        def click(e: Any) -> None:
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

        def do_add() -> None:
            msg = add(ent.get().strip())
            self._log((msg or f"＋ ajouté : {ent.get().strip()}") + "\n")
            ent.delete(0, "end")
            reload()

        def do_del() -> None:
            it = tv.focus()
            if not it:
                return
            t, s, _n, u = tv.item(it)["values"]  # type: ignore[str-unpack]  # typeshed: values may be str; here always a tuple
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

    def _add_offer_url(self: "AppTypee") -> None:
        """Analyse le lien collé (add_offer.py) : titre+entreprise+description → queue → CV/lettre."""
        url = self.e_url.get().strip()
        if not url.startswith("http"):
            self._log("✗ colle une URL http d'offre.\n")
            return
        self.b_addurl.configure(text=_t("Analyse…"), state="disabled")
        self._log(f"🔎 analyse de l'offre : {url[:70]}…\n")

        def work() -> None:
            try:
                r = subprocess.run(
                    [PY, "-m", "jobhunter.programs.add_offer", "--url", url],
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

        def done(out: Any) -> None:
            for line in out.splitlines():
                if line.strip():
                    self._log("  " + line.strip()[:100] + "\n")
            self.b_addurl.configure(text=_t("Ajouter une offre"), state="normal")
            self.e_url.delete(0, "end")
            self.load_offers()

        threading.Thread(target=work, daemon=True).start()
