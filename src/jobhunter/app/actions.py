"""Actions on offers: status, set aside, delete (with recycle bin), apply (human click).

Part of jobhunter.app (former JobHunter.pyw, phase 3.7)."""

import datetime
import json
import os
import threading
import tkinter as tk
import webbrowser
from tkinter import messagebox
from typing import Any
from urllib.parse import quote

import customtkinter as ctk

from jobhunter import guided_apply as _guidee
from jobhunter.app import common as _commun
from jobhunter.app import theme as _theme
from jobhunter.app._app_type import AppTypee
from jobhunter.app.common import EXPIRE, PAS_INTERESSE, QUEUE, SCRIPTS, ST_EMOJI
from jobhunter.app.language import t as _t
from jobhunter.app.theme import BG, BTN, BTN_H, CARD, CB, CE, CF, CL, DEL, MUT, TX, WORK
from jobhunter.storage import applications as suivi_io
from jobhunter.storage import queue as queue_io


class ActionsMixin:
    def _set_statut(self: "AppTypee", o: Any, statut: Any) -> None:
        """Writes a status into suivi.json (automatic date = today if missing). Manual > auto."""
        if not o:
            return
        oid = self._oid(o)
        # We start again from the entry AS IT IS ON DISK, not from the in-memory
        # copy: a note or a follow-up added in the meantime must survive.
        avant = dict(suivi_io.charger(_commun.SUIVI).get(oid, {}))
        rec = dict(avant)
        if statut:
            rec["s"] = statut
            rec.setdefault("d", datetime.date.today().isoformat())
        else:
            rec = {}
        if not self._ecrire_suivi(oid, rec):
            return
        self._annuler.append([(oid, avant)])
        self._log(f"📌 statut: {o.get('entreprise', '')} → {statut or '(vidé)'}\n")
        self._garder_annonce(o, statut)
        self.refresh_table()

    def _garder_annonce(self: "AppTypee", o: Any, statut: Any) -> None:
        """Keeps the posting's copy (jobhunter.postings) when the offer is applied to.

        In a thread: writing the PDF takes a moment, the click must not wait. A
        failure only costs the copy, which the morning pipeline tries again.
        """
        from jobhunter import postings

        if not o or statut not in postings.ENVOYEES:
            return

        def tache() -> None:
            try:
                p = postings.archiver(o)
            except Exception as ex:  # disk full, rights: the pipeline will retry
                nom = type(ex).__name__
                self.root.after(0, lambda: self._log(f"! annonce non gardée ({nom})\n"))
                return
            if p is not None:
                self.root.after(0, lambda: self._log(f"🗂 annonce gardée : {p.name}\n"))

        threading.Thread(target=tache, daemon=True).start()

    def _pas_interesse(self: "AppTypee", o: Any) -> None:
        """Del / button / right click: the offer leaves the table, stays in the queue.

        The cursor moves to the next row BEFORE the refresh: otherwise it falls back
        to the top of the table and each sorted offer costs a scroll.
        """
        if not o:
            self._log("Sélectionne d'abord une offre.\n")
            return
        suivante = None
        kids = self.tree.get_children()
        cur = self.tree.focus()
        if cur in kids:
            i = kids.index(cur)
            voisin = kids[i + 1] if i + 1 < len(kids) else (kids[i - 1] if i else None)
            suivante = self._oid(self.rowmap[voisin]) if voisin else None
        self._set_statut(o, PAS_INTERESSE)
        self.checked.discard(self._oid(o))
        if suivante:
            self._focus_oid(suivante)

    def _focus_oid(self: "AppTypee", oid: Any) -> None:
        for iid, x in self.rowmap.items():
            if self._oid(x) == oid:
                self.tree.selection_set(iid)
                self.tree.focus(iid)
                self.tree.see(iid)
                self.tree.focus_set()
                return

    def _pas_interesse_checked(self: "AppTypee") -> None:
        """All the ticked offers at once. A single Ctrl+Z restores them all."""
        oids = [k for k in self.checked if self._find_by_oid(k)]
        if not oids:
            self._log("Coche d'abord des offres (colonne ☐).\n")
            return
        geste: list[Any] = []
        jour = datetime.date.today().isoformat()

        def _f(s: Any) -> None:  # ONE transaction: lock, re-read, write
            geste.clear()
            for oid in oids:
                avant = dict(s.get(oid, {}))
                rec = dict(avant)
                rec["s"] = PAS_INTERESSE
                rec.setdefault("d", jour)
                s[oid] = rec
                geste.append((oid, avant))

        try:
            suivi_io.modifier(_f, _commun.SUIVI, attente=4)
        except suivi_io.VerrouIndisponible:
            self._log("✗ un autre programme écrit suivi.json — réessaie dans un instant.\n")
            return
        except Exception as ex:
            self._log(f"! écriture suivi.json KO: {ex}\n")
            return
        self.suivi = suivi_io.charger(_commun.SUIVI)
        self._annuler.append(list(geste))
        self.checked.clear()
        self.refresh_table()
        self._log(f"⊖ {len(geste)} offre(s) « pas intéressé » — masquées, Ctrl+Z pour annuler.\n")

    def _annuler_dernier(self: "AppTypee") -> None:
        """Ctrl+Z: puts the tracking of the last action back as it was before."""
        if not self._annuler:
            self._log("Rien à annuler.\n")
            return
        geste = self._annuler.pop()

        def _f(s: Any) -> None:
            for oid, avant in geste:
                if avant:
                    s[oid] = avant
                else:
                    s.pop(oid, None)

        try:
            suivi_io.modifier(_f, _commun.SUIVI, attente=4)
        except Exception as ex:
            self._annuler.append(geste)
            self._log(f"✗ annulation impossible pour l'instant ({type(ex).__name__}) — réessaie.\n")
            return
        self.suivi = suivi_io.charger(_commun.SUIVI)
        self.refresh_table()
        if len(geste) == 1:
            self._focus_oid(geste[0][0])
        self._log(f"↶ annulé ({len(geste)} offre(s)).\n")

    def _postuler(self: "AppTypee", o: Any) -> None:
        """Records only a sending explicitly confirmed by the user.

        Manual declaration, without observing the page: `envoi` = "déclaré"
        (ADR 0009). A proof already observed is never erased."""
        if not o:
            return
        if not messagebox.askyesno(
            _t("Confirmer l'envoi"), _t("As-tu envoyé cette candidature ?"), parent=self.root
        ):
            return
        oid = self._oid(o)
        avant = dict(suivi_io.charger(_commun.SUIVI).get(oid, {}))
        try:
            suivi_io.declarer_envoi(oid, "déclaré", chemin=_commun.SUIVI, attente=4)
        except suivi_io.VerrouIndisponible:
            self._log("⏳ suivi.json occupé par un autre programme — réessaie dans un instant.\n")
            return
        self._annuler.append([(oid, avant)])
        self.suivi = suivi_io.charger(_commun.SUIVI)
        self._log(f"📌 statut: {o.get('entreprise', '')} → postulé (envoi déclaré)\n")
        self._garder_annonce(o, "postulé")
        self.refresh_table()

    def _apply_checked(self: "AppTypee") -> None:
        """Applies to ALL the ticked offers: semi-automatic runner (fills + uploads, STOPS on
        Send = you). Writes the selection into apply_selection.json, launches the console."""
        oids = [o for o in [self._find_by_oid(k) for k in self.checked] if o]
        if not oids:
            self._log("Coche d'abord des offres (colonne ☐).\n")
            return
        sel = _guidee.selection(oids)
        SEL = SCRIPTS / "apply_selection.json"
        try:
            SEL.write_text(json.dumps(sel, ensure_ascii=False, indent=1), encoding="utf-8")
        except Exception as ex:
            self._log(f"! écriture sélection KO: {ex}\n")
            return
        # Applications panel: the program fills in and stops on Send, the user
        # clicks in Chrome then "J'ai envoyé"; no console any more (2.2.0).
        self._candidater(SEL, len(sel))

    def _find_by_oid(self: "AppTypee", oid: Any) -> Any:
        for o in self.offers:
            if self._oid(o) == oid:
                return o
        return None

    def _row_menu(self: "AppTypee", e: Any) -> None:
        """Right click on a row → per-offer actions (Apply + quick statuses)."""
        iid = self.tree.identify_row(e.y)
        if not iid:
            return
        self.tree.selection_set(iid)
        self.tree.focus(iid)
        o = self.rowmap.get(iid)
        if not o:
            return
        m = tk.Menu(
            self.root,
            tearoff=0,
            bg=CARD,
            fg=TX,
            activebackground=BTN_H,
            activeforeground=TX,
            relief="flat",
            borderwidth=1,
            font=(_theme.FONT_UI, 11),
        )
        m.add_command(
            label=_t("Confirmer une candidature envoyée…"), command=lambda: self._postuler(o)
        )
        m.add_command(label=_t("🌐 Ouvrir l'offre"), command=lambda: self._open_offer(o))
        if self._statut_of(o)[0] == PAS_INTERESSE:
            m.add_command(
                label=_t("↶ Finalement intéressé (vider le statut)"),
                command=lambda: self._set_statut(o, ""),
            )
        else:
            m.add_command(
                label=f"{ST_EMOJI[PAS_INTERESSE]} Pas intéressé   (Suppr)",
                command=lambda: self._pas_interesse(o),
            )
        if self._statut_of(o)[0] in ("postulé", "relancé"):
            m.add_command(
                label=_t("🔔 Relance (brouillon mail)"), command=lambda: self._relance_draft(o)
            )
        m.add_separator()
        for s in ("à postuler", "à vérifier", "postulé", "relancé", "entretien", "refus"):
            m.add_command(
                label=f"{ST_EMOJI.get(s, '')} {s}",
                command=lambda s=s: self._set_statut(o, s),  # type: ignore[misc]  # lambda with a default parameter (loop capture)
            )
        # "mauvaise" apart, after a separator: it is not a step of the
        # application journey but a judgement on the offer itself.
        m.add_separator()
        m.add_command(
            label=f"{ST_EMOJI['mauvaise']} mauvaise (offre sans intérêt)",
            command=lambda: self._set_statut(o, "mauvaise"),
        )
        m.add_command(
            label=f"{ST_EMOJI[EXPIRE]} expiré (annonce fermée)",
            command=lambda: self._set_statut(o, EXPIRE),
        )
        m.add_separator()
        m.add_command(label=_t("✖ vider le statut"), command=lambda: self._set_statut(o, ""))
        try:
            m.tk_popup(e.x_root, e.y_root)
        finally:
            m.grab_release()

    def _open_offer(self: "AppTypee", o: Any) -> None:
        """Opens the offer's URL; otherwise a web search (company + job)."""
        if not o:
            return
        u = o.get("url") or ""
        if not u.startswith("http"):
            self._search_web(o)
            return
        webbrowser.open(u)
        marque = self._marque_lien(o)
        if not marque:
            self._log(f"→ {u[:78]}" + chr(10))
            return
        # Without this message one thinks the app is broken: it opens a home
        # page when an offer was expected.
        quoi = "page de resultats" if marque == "≡" else "page carrieres / accueil"
        mort = " — le lien direct etait mort" if o.get("url_orig") else ""
        self._log(
            f"→ {u[:78]}"
            + chr(10)
            + f"   ATTENTION : {quoi}, pas l'offre elle-meme{mort}."
            + chr(10)
        )

    def _search_web(self: "AppTypee", o: Any) -> None:
        if not o:
            return
        qy = quote(f"{o.get('entreprise', '')} {o.get('poste', '')} recrutement")
        webbrowser.open(f"https://www.google.com/search?q={qy}")
        self._log(f"🔍 recherche web: {o.get('entreprise', '')}\n")

    def _click_cell(self: "AppTypee", e: Any) -> None:
        """Clic colonne ☐ = coche/décoche ; colonne Lien = ouvre l'offre."""
        if self.tree.identify_region(e.x, e.y) != "cell":
            return
        col = self.tree.identify_column(e.x)
        o = self.rowmap.get(self.tree.identify_row(e.y))
        if not o:
            return
        if col == self._chkcol:
            self._toggle_check(o)
            return
        if col == self._urlcol:
            self._open_offer(o)

    def _toggle_check(self: "AppTypee", o: Any) -> None:
        oid = self._oid(o)
        if oid in self.checked:
            self.checked.discard(oid)
        else:
            self.checked.add(oid)
        self.refresh_table()
        self._upd_apply_btn()

    def _check_all(self: "AppTypee", val: Any) -> None:
        """val True=tick all (visible filtered rows), False=untick all, None=toggle."""
        vis = [self.rowmap[i] for i in self.tree.get_children()]
        oids = [self._oid(o) for o in vis]
        if val is None:
            val = not all(x in self.checked for x in oids) if oids else False
        if val:
            self.checked.update(oids)
        else:
            if len(self.checked) == len(oids) and set(oids) == self.checked:
                self.checked.clear()
            else:
                self.checked.difference_update(oids)
        self.refresh_table()
        self._upd_apply_btn()

    def _upd_apply_btn(self: "AppTypee") -> None:
        n = len(self.checked)
        try:
            if n:
                self.lbl_sel.configure(text=f"{n} cochée(s)")
                self.lbl_aide.pack_forget()
                self.selbar.pack(side="right")
            else:
                self.selbar.pack_forget()
                self.lbl_aide.pack(side="right")
        except Exception:
            pass

    def _ecarter_checked(self: "AppTypee") -> None:
        """Sets the ticked offers aside WITH a reason, and remembers the refusal.

        Deleting is not enough: the scan finds the offer at the source again and
        re-adds it the next day. Here the refusal is stored in exclusions.json,
        which merge_into_queue checks before adding anything.

        The reason is not decoration. A refusal on a high-fit offer is a
        disagreement between the score and the user's judgement — that is what
        `python JobHunter.pyw exclusions` reads to show what the scoring misses.
        """
        oids = set(self.checked)
        if not oids:
            self._log("Coche d'abord des offres (colonne ☐).\n")
            return
        motif = self._demander_motif(len(oids))
        if not motif:
            return
        try:
            from jobhunter.programs import exclusions
        except Exception as ex:
            self._log(f"! exclusions.py introuvable: {ex}\n")
            return
        if not self._verrou_queue(True):
            self._log("✗ un autre programme modifie la file — réessaie dans un instant.\n")
            return
        try:
            try:
                fresh = queue_io.charger(QUEUE)
            except Exception:
                fresh = list(self.offers)
            vises = [o for o in fresh if self._oid(o) in oids]
            # We record BEFORE removing: if writing the queue fails,
            # better one exclusion too many than an offer set aside without a reason.
            n_exc = exclusions.ajouter(vises, motif)
            restant = [o for o in fresh if self._oid(o) not in oids]
            retirees = len(fresh) - len(restant)
            try:
                queue_io.sauver(restant, QUEUE)
            except Exception as ex:
                self._log(f"! écriture queue KO: {ex}\n")
                return
        finally:
            self._verrou_queue(False)
        self.checked.clear()
        self.load_offers()
        self._log(
            f"✕ {retirees} offre(s) écartée(s) — « {motif} ». "
            f"{n_exc} nouvelle(s) exclusion(s) ; elles ne reviendront pas au scan.\n"
            f"   Bilan de ce que la notation rate : python JobHunter.pyw exclusions\n"
        )

    def _demander_motif(self: "AppTypee", n: Any) -> Any:
        """Small dialog: frequent reasons as buttons, plus a free field.

        Returns the chosen reason, or None if the user cancels.

        Parent = self.root. It used to be `self`, the App object, which is not a
        widget: Toplevel(self) raised on every click and "Écarter" never
        opened — the exception went to the crash log.
        """
        try:
            from jobhunter.programs import exclusions

            motifs = list(exclusions.MOTIFS)
        except Exception:
            motifs = [
                "Trop d'expérience demandée",
                "Poste trop senior",
                "Pas le bon métier",
                "Lieu impossible",
            ]
        dlg = ctk.CTkToplevel(self.root)
        dlg.title("Écarter des offres")
        dlg.configure(fg_color=BG)
        dlg.transient(self.root)
        dlg.resizable(False, False)
        choix = {"v": None}
        carte = CF(dlg, bg=CARD)
        carte.pack(fill="both", expand=True, padx=16, pady=16)
        CL(
            carte,
            text=f"Pourquoi écarter ces {n} offre(s) ?",
            bg=CARD,
            fg=TX,
            font=(_theme.FONT_UI, 15, "bold"),
            anchor="w",
        ).pack(fill="x", padx=18, pady=(16, 2))
        CL(
            carte,
            text="Retirées de la file et bloquées au prochain scan. Le motif sert à "
            "corriger la notation.",
            bg=CARD,
            fg=MUT,
            font=(_theme.FONT_UI, 11),
            anchor="w",
            wraplength=380,
            justify="left",
        ).pack(fill="x", padx=18, pady=(0, 12))

        def prendre(m: Any) -> None:
            choix["v"] = m
            dlg.destroy()

        for m in motifs:
            CB(
                carte,
                text=m,
                command=lambda m=m: prendre(m),
                bg=BTN,
                anchor="w",
                font=(_theme.FONT_UI, 12),
                width=380,
            ).pack(fill="x", padx=18, pady=3)
        CL(
            carte,
            text="ou une autre raison :",
            bg=CARD,
            fg=MUT,
            font=(_theme.FONT_UI, 11),
            anchor="w",
        ).pack(fill="x", padx=18, pady=(12, 2))
        e = CE(carte, bg=WORK, fg=TX, width=54)
        e.pack(fill="x", padx=18)
        e.bind("<Return>", lambda ev: prendre(e.get().strip() or None))
        e.bind("<Escape>", lambda ev: dlg.destroy())
        barre = CF(carte, bg=CARD, plat=True)
        barre.pack(fill="x", padx=18, pady=(14, 16))
        CB(barre, text="Annuler", command=dlg.destroy, bg=BTN).pack(side="right")
        CB(barre, text="Écarter", command=lambda: prendre(e.get().strip() or None), bg=DEL).pack(
            side="right", padx=8
        )
        # grab AFTER display: on Windows, a grab_set on a window not
        # encore visible echoue (« grab failed: window not viewable »).
        dlg.after(80, lambda: (dlg.grab_set(), e.focus_set()))
        self.root.wait_window(dlg)
        return choix["v"]

    CORBEILLE = SCRIPTS / "_corbeille"

    def _delete_checked(self: "AppTypee") -> None:
        """Deletes the ticked offers from apply_queue.json, after a copy to the recycle bin.

        The dialog promised "recoverable via git". That was false the day I checked
        it: the last commit of the queue was from the day before and 424 offers on
        disk existed in no commit — including the 428 that arrived that day.
        Deleting one of them lost it for good. So a timestamped copy is written
        before removing anything; the promise now rests on a file that really
        exists.
        """
        oids = set(self.checked)
        if not oids:
            self._log("Coche d'abord des offres (colonne ☐).\n")
            return
        if not messagebox.askyesno(
            _t("Supprimer les offres"),
            _t(
                "Supprimer {n} offre(s) cochée(s) de la liste ?\n\n"
                "Une copie est gardée dans Scripts/_corbeille/ — rien n'est perdu.\n"
                "Pour qu'elles ne reviennent pas au prochain scan, préfère\n"
                "« Écarter » : le motif est retenu."
            ).format(n=len(oids)),
        ):
            return
        # LOCK. Re-reading the disk just before writing NARROWS the race window
        # but does not close it: a background job that writes between this re-read and
        # our write sees its work erased. The app was the ONLY one of the 14
        # writers of the queue not to take the lock.
        if not self._verrou_queue(True):
            self._log("✗ un autre programme modifie la file — réessaie dans un instant.\n")
            return
        try:
            # fresh state: the background jobs may have enriched the queue since the
            # last load — otherwise we would overwrite their changes
            try:
                fresh = queue_io.charger(QUEUE)
            except Exception:
                fresh = list(self.offers)
            before = len(fresh)
            partantes = [o for o in fresh if self._oid(o) in oids]
            fresh = [o for o in fresh if self._oid(o) not in oids]
            removed = before - len(fresh)
            # THE COPY FIRST. If writing the queue then fails, we have one recycle bin
            # too many; in the other order, we would have offers
            # deleted without a copy. `charger()` re-injected the descriptions,
            # so they go with them.
            sauvegarde = ""
            try:
                self.CORBEILLE.mkdir(parents=True, exist_ok=True)
                f = self.CORBEILLE / f"supprimees_{datetime.datetime.now():%Y-%m-%d_%H%M%S}.json"
                self._jwrite(f, partantes)
                sauvegarde = f.name
            except Exception as ex:
                self._log(f"! copie de sauvegarde KO ({ex}) — suppression ANNULÉE.\n")
                return
            try:
                # sauver() moves the descriptions out to descriptions.json;
                # _jwrite would write them back into the queue and undo the separation.
                queue_io.sauver(fresh, QUEUE)
            except Exception as ex:
                self._log(f"! écriture queue KO: {ex}\n")
                return
        finally:
            self._verrou_queue(False)
        self.checked.clear()
        self.load_offers()  # reloads the fresh state
        self._log(
            f"🗑 {removed} offre(s) supprimée(s) — copie dans Scripts/_corbeille/{sauvegarde}\n"
        )

    # ── CV & LETTERS viewer: BUILT-IN panel (replaces the dashboard, Back) ──
    # PDF → PyMuPDF (all the pages STACKED, mouse wheel = scroll all the way)
    # DOCX/TXT → extracted text (python-docx) in a scrollable panel
    @staticmethod
    def _verrou_queue(prendre: Any, _attente: Any = 20) -> Any:
        """Takes / releases the inter-process lock of the queue. True if obtained.

        Short wait (20 s): this is an interactive action, better to say
        "try again" than to freeze the window for 3 minutes.
        """
        try:
            from jobhunter.programs import util as jutil
        except Exception:
            return True  # jutil not found: we do not prevent acting
        try:
            if prendre:
                return jutil.prendre_verrou(QUEUE, attente=_attente)
            jutil.rendre_verrou(QUEUE)
            return True
        except Exception:
            # A LOCK FAILURE IS NOT A GREEN LIGHT. This case returned True and
            # the destructive action went on without protection — the opposite of what
            # the lock exists to prevent. Giving control back carries no
            # risk: the caller displays "try again". The "jutil
            # not found" case above stays permissive: without Scripts/
            # the app has no queue to protect anyway.
            return not prendre

    @staticmethod
    def _jwrite(path: Any, obj: Any) -> None:
        """ATOMIC JSON write (tmp + replace): a crash mid-write never corrupts the file."""
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")
        os.replace(str(tmp), str(path))
