"""Card of an offer: editing the tracking (status, note, date), description, accounts.

Part of jobhunter.app (former JobHunter.pyw, phase 3.7)."""

import subprocess
import threading
import tkinter as tk
from typing import Any

from jobhunter.app import common as _commun
from jobhunter.app import language as _langue
from jobhunter.app._app_type import AppTypee
from jobhunter.app.common import PY, QUEUE, SCRIPTS
from jobhunter.app.language import t as _t
from jobhunter.app.theme import ACC, ACC_H, ACC_TX, BG, BTN, BTN_H, CARD, CB, CF, TX
from jobhunter.storage import applications as suivi_io
from jobhunter.storage import queue as queue_io


class FicheMixin:
    # ── tracking editing (writes suivi.json directly) ──
    def _load_edit(self: "AppTypee", e: Any = None) -> None:
        it = self.tree.focus()
        o = self.rowmap.get(it)
        if not o:
            return
        self._cur = o
        sv = self.suivi.get(self._oid(o), {})
        acc = self._acct_of(o)
        self.sel.configure(text=f"{o.get('entreprise', '')} — {o.get('poste', '')[:70]}")
        self.b_acct.configure(text=_t("Retirer le compte" if acc else "Associer un compte"))
        self.e_st.set(sv.get("s", ""))
        self.e_note.delete(0, "end")
        self.e_note.insert(0, sv.get("n", ""))
        self.e_date.delete(0, "end")
        self.e_date.insert(0, sv.get("d", ""))
        self._show_detail(o)

    def _fill_detail(self: "AppTypee", d: Any, o: Any) -> None:
        """Writes ALL the offer's Excel columns into the text widget d."""
        d.configure(state="normal")
        d.delete("1.0", "end")
        d.insert("end", f"{o.get('entreprise', '')} — {o.get('poste', '')}\n", "h")
        acc = self._acct_of(o)
        d.insert("end", ("● compte  ·  " if acc else "") + f"{self._host(o)}\n", "m")
        meta = []
        for lbl, k in [
            ("Fit", "fit"),
            ("Action", "action"),
            ("Contrat", "contrat"),
            ("Lieu", "localisation"),
            ("Télétravail", "teletravail"),
            ("Domaine", "domaine"),
            ("Compétences", "skills_match"),
            ("Correspondance ATS", "ats_pct"),
            ("Canal", "canal"),
            ("Type", "url_type"),
            ("État lien", "link_status"),
        ]:
            v = o.get(k)
            if v not in (None, "", "Non précisé"):
                meta.append(f"{_t(lbl)} : {str(v).replace('_', ' ')}")
        if o.get("autres_lieux"):  # same job published in other cities
            meta.append(_t("Aussi à") + " : " + ", ".join(str(x) for x in o["autres_lieux"]))
        yrs = o.get("exp_requise")
        if yrs:  # years of experience required (junior user → fit penalised if ≥3)
            exp = _t("Expérience requise : {n} ans").format(n=yrs)
            meta.append("⚠️ " + exp if yrs >= 3 else exp)
        meta.extend(self._etat_candidature(o))
        meta.extend(self._etat_dossier(o))
        if meta:
            d.insert("end", "\n".join(meta) + "\n", "m")
        raisons = self._raisons_fit(o)
        if raisons:
            d.insert("end", "\n" + _t("Pourquoi ce fit") + "\n", "k")
            d.insert("end", "\n".join("· " + r for r in raisons) + "\n", "m")
        # Where the offer was seen (sources.merge.noter_source): which searches find it.
        vus = o.get("vus_sur") or []
        if len(vus) > 1:
            d.insert("end", "\n" + _t("Trouvée par") + "\n", "k")
            d.insert("end", "\n".join("· " + str(v) for v in vus) + "\n", "m")
        # What its site changed since (sources.merge.changements); values not replaced.
        if chg := o.get("changements"):
            d.insert("end", "\n" + _t("Modifiée par son site") + "\n", "k")
            d.insert(
                "end",
                "\n".join(
                    f"· {c.get('date', '')} — {_t(c.get('champ', ''))} : "
                    f"{c.get('avant', '')} → {c.get('apres', '')}"
                    for c in chg
                )
                + "\n",
                "m",
            )
        # Its successive fits, and why (scoring.history).
        if len(hist := o.get("historique_fit") or []) >= 2:
            d.insert("end", "\n" + _t("Historique du score") + "\n", "k")
            lignes, regles = [], None
            for e in hist:
                ligne = f"· {e.get('date', '?')} — fit {e.get('fit', '?')}"
                if e.get("cause") not in (None, "?"):
                    # the causes scoring.history writes, translated
                    cause = {"description": "description", "re-score": "re-score"}.get(
                        str(e["cause"]), str(e["cause"])
                    )
                    ligne += f" ({_t(cause)})"
                if regles and e.get("regles") and e["regles"] != regles:
                    ligne += " · " + _t("règles changées")
                regles = e.get("regles") or regles
                lignes.append(ligne)
            d.insert("end", "\n".join(lignes) + "\n", "m")
        desc = (o.get("description") or "").strip()
        if desc:
            d.insert("end", "\nDescription\n", "k")
            d.insert("end", desc + "\n")
        for lbl, k in [
            ("Salaire / Avantages", "salaire"),
            ("Profil requis", "profil"),
            ("Missions / Compétences", "missions"),
            ("Pourquoi", "pourquoi"),
            ("Recruteur", "rh"),
            ("Source", "source"),
            ("Process", "process"),
            ("CV", "cv"),
            ("Lettre", "lettre"),
            ("URL", "url"),
        ]:
            v = (o.get(k) or "").strip()
            if v and v != "Non précisé":
                d.insert("end", f"\n{_t(lbl)} : ", "k")
                d.insert("end", v)
        d.configure(state="disabled")
        d.see("1.0")

    def _raisons_fit(self: "AppTypee", o: Any) -> list[str]:
        """The fit computation in plain words (scoring.fit.expliquer); [] without text or on error.

        Recomputed on the offer's text: if the queue's fit differs (profile changed
        since), the last line says so.
        """
        texte = f"{o.get('poste', '')} {o.get('description', '')}".strip()
        if not texte:
            return []
        try:
            from jobhunter.scoring.fit import expliquer

            raisons = expliquer(texte, o.get("poste", ""))
        except Exception:  # the card is displayed even if the profile is incomplete
            return []
        raisons = [_langue.explication(r) for r in raisons]
        if raisons and str(o.get("fit")) not in ("", "None") and raisons[-1] != f"fit {o['fit']}":
            raisons[-1] += " " + _t("(file : {fit}, recalcul au prochain re-score)").format(
                fit=o["fit"]
            )
        return raisons

    def _etat_dossier(self: "AppTypee", o: Any) -> list[str]:
        """Is the file (CV, letter) ready to go? Nothing if the offer has none."""
        if not (o.get("cv") or o.get("lettre")):
            return []
        from jobhunter.documents.checks import controler_dossier

        problemes = controler_dossier(o)
        if not problemes:
            return [_t("Dossier : prêt (CV et lettre lisibles, une page, coordonnées)")]
        return [_t("Dossier à revoir") + " : " + " ; ".join(problemes)]

    def _etat_candidature(self: "AppTypee", o: Any) -> list[str]:
        """The tracking status and the state of the proof of sending (ADR 0009), for the sheet."""
        sv = self.suivi.get(self._oid(o), {})
        if not sv.get("s"):
            return []
        ligne = _t("Candidature") + f" : {sv['s']}" + (f" le {sv['d']}" if sv.get("d") else "")
        envoi = sv.get("envoi")
        if envoi:
            ligne += {
                "confirmé": " · envoi confirmé par le site",
                "incertain": " · envoi NON confirmé par le site (à vérifier)",
                "déclaré": " · envoi déclaré",
            }.get(envoi, f" · {envoi}")
        lignes = [ligne]
        preuve = sv.get("preuve") or {}
        if preuve.get("texte"):
            lignes.append(f"  « {str(preuve['texte'])[:140]} »")
        if preuve.get("capture"):
            lignes.append(f"  capture : {preuve['capture']}")
        return lignes

    def _show_detail(self: "AppTypee", o: Any) -> None:
        self._fill_detail(self.detail, o)

    def _fiche_popup(self: "AppTypee", e: Any = None) -> None:
        o = self.rowmap.get(self.tree.focus())
        if not o:
            return
        w = tk.Toplevel(self.root)
        w.title(f"Fiche — {o.get('entreprise', '')}")
        w.geometry("820x680")
        w.configure(bg=BG)
        carte = CF(w, bg=CARD)
        carte.pack(fill="both", expand=True, padx=20, pady=(20, 12))
        t = self._zone_texte(carte, bg=CARD)
        t.master.pack(fill="both", expand=True, padx=16, pady=14)
        self._fill_detail(t, o)
        btn = CF(w, bg=BG)
        btn.pack(fill="x", padx=20, pady=(0, 16))
        CB(
            btn,
            text="Envoi confirmé",
            command=lambda: (self._postuler(o), self._fill_detail(t, o)),
            bg=ACC,
            fg=ACC_TX,
            activebackground=ACC_H,
            relief="flat",
        ).pack(side="left")
        CB(
            btn,
            text="Pas intéressé",
            command=lambda: (self._pas_interesse(o), w.destroy()),  # type: ignore[func-returns-value]  # Tk lambda chaining calls without a value
            bg=BTN,
        ).pack(side="left", padx=(12, 0))
        CB(
            btn,
            text="Ouvrir l'offre",
            command=lambda: self._open_offer(o),
            bg=BTN,
            fg=TX,
            activebackground=BTN_H,
            relief="flat",
        ).pack(side="left", padx=12)
        bd = CB(btn, text="Description", bg=BTN, fg=TX, activebackground=BTN_H, relief="flat")
        bd.configure(command=lambda: self._fetch_desc(o, t, bd))
        bd.pack(side="left", padx=12)
        cvp = self._cv_of(o)
        if cvp:
            CB(
                btn,
                text="Voir CV",
                command=lambda: (w.destroy(), self._cv_viewer(str(cvp))),  # type: ignore[func-returns-value]  # Tk lambda chaining calls without a value
                bg=BTN,
                fg=TX,
                relief="flat",
            ).pack(side="left", padx=12)
        ltp = self._lettre_of(o)
        if ltp:
            CB(
                btn,
                text="Voir lettre",
                command=lambda: (w.destroy(), self._cv_viewer(str(ltp))),  # type: ignore[func-returns-value]  # Tk lambda chaining calls without a value
                bg=BTN,
                fg=TX,
                relief="flat",
            ).pack(side="left", padx=12)
        CB(btn, text="Fermer", command=w.destroy, bg=BTN, fg=TX, relief="flat").pack(side="right")

    def _fetch_desc(self: "AppTypee", o: Any, textwidget: Any, btn: Any) -> None:
        """Fetches the offer's description online (scrape_desc.py, headless) → queue → detail."""
        key = self._oid(o)
        if not (o.get("url") or "").startswith("http"):
            self._log("✗ pas d'URL http pour récupérer la description\n")
            return
        try:
            btn.configure(text=_t("Chargement…"), state="disabled")
        except Exception:
            pass

        def work() -> None:
            try:
                r = subprocess.run(
                    [PY, "-m", "jobhunter.programs.scrape_desc", "--key", key],
                    cwd=str(SCRIPTS),
                    capture_output=True,
                    text=True,
                    timeout=100,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                out = (r.stdout or "") + (r.stderr or "")
            except Exception as e:
                out = f"err {type(e).__name__}: {e}"
            self.root.after(0, lambda: done(out))

        def done(out: Any) -> None:
            try:
                q = queue_io.charger(QUEUE)
                for x in q:
                    if self._oid(x) == key:
                        o["description"] = x.get("description", "")
                        break
            except Exception:
                pass
            try:
                self._fill_detail(textwidget, o)
            except Exception:
                pass
            try:
                btn.configure(text=_t("Description"), state="normal")
            except Exception:
                pass
            self._log(
                "✅ description récupérée\n"
                if o.get("description")
                else "✗ description introuvable (page JS/mur login ?)\n"
            )

        threading.Thread(target=work, daemon=True).start()

    def _toggle_account(self: "AppTypee") -> None:
        """Marks/unmarks an account for this site (comptes_sites.json)."""
        o = self._cur
        if not o:
            return
        host = self._host(o)
        if not host:
            self._log("(pas d'URL → pas de host)\n")
            return
        if self._acct_of(o) and not o.get("etat"):
            for h in [
                k
                for k in list(self.comptes)
                if host == k or host.endswith("." + k) or k.endswith("." + host)
            ]:
                self.comptes.pop(h, None)
            self._log(f"－ compte retiré: {host}\n")
        else:
            self.comptes[host] = {
                "site": o.get("entreprise", ""),
                "login": o.get("url", ""),
                "email": self.myemail,
                "src": "manuel",
            }
            self._log(f"Associer un compte ajouté: {host}\n")
        try:
            self._jwrite(_commun.COMPTES, self.comptes)
        except Exception as ex:
            self._log(f"! écriture comptes_sites.json KO: {ex}\n")
        self.refresh_table()
        self._load_edit()

    def save_edit(self: "AppTypee") -> None:
        if not self._cur:
            self._log("Sélectionne d'abord une offre.\n")
            return
        oid = self._oid(self._cur)
        rec = {}
        if self.e_st.get():
            rec["s"] = self.e_st.get()
        if self.e_note.get().strip():
            rec["n"] = self.e_note.get().strip()
        if self.e_date.get().strip():
            rec["d"] = self.e_date.get().strip()
        if not self._ecrire_suivi(oid, rec):
            return
        self._log(f"💾 suivi enregistré: {oid} → {rec or '(vidé)'}\n")
        self.refresh_table()

    def _ecrire_suivi(self: "AppTypee", oid: Any, rec: Any) -> Any:
        """ONE application, written under lock on the fresh state of the disk.

        The app used to write `self.suivi`, its in-memory snapshot: a "postulé" click
        rewrote the whole file and erased what `follow_ups.py` had put there in the
        meantime. Reproduced — two follow-ups lost without a word. Only one entry is
        written now, and `suivi_io` re-reads the disk inside the lock: the others'
        work is kept.
        """
        try:
            # SHORT wait: Tkinter is single-threaded, a long wait in a
            # click handler freezes the window and the app looks crashed.
            suivi_io.poser(oid, rec, _commun.SUIVI, attente=4)
        except suivi_io.VerrouIndisponible:
            self._log("✗ un autre programme écrit suivi.json — réessaie dans un instant.\n")
            return False
        except Exception as ex:
            self._log(f"! écriture suivi.json KO: {ex}\n")
            return False
        # We reload from disk rather than patching memory: it is
        # the only state that accounts for the other writers.
        self.suivi = suivi_io.charger(_commun.SUIVI)
        return True
