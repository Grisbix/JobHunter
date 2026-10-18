"""Fiche d'une offre : edition du suivi (statut, note, date), description, comptes.

Partie de jobhunter.app (ancien JobHunter.pyw, phase 3.7)."""

import subprocess
import threading
import tkinter as tk

from jobhunter.app import commun as _commun
from jobhunter.app.commun import PY, QUEUE, SCRIPTS
from jobhunter.app.theme import ACC, ACC_H, ACC_TX, BG, BTN, BTN_H, CARD, CB, CF, TX
from jobhunter.stockage import file as queue_io
from jobhunter.stockage import suivi as suivi_io


class FicheMixin:
    # ── édition suivi (écrit suivi.json direct) ──
    def _load_edit(self, e=None):
        it = self.tree.focus()
        o = self.rowmap.get(it)
        if not o:
            return
        self._cur = o
        sv = self.suivi.get(self._oid(o), {})
        acc = self._acct_of(o)
        self.sel.configure(text=f"{o.get('entreprise', '')} — {o.get('poste', '')[:70]}")
        self.b_acct.configure(text="Retirer le compte" if acc else "Associer un compte")
        self.e_st.set(sv.get("s", ""))
        self.e_note.delete(0, "end")
        self.e_note.insert(0, sv.get("n", ""))
        self.e_date.delete(0, "end")
        self.e_date.insert(0, sv.get("d", ""))
        self._show_detail(o)

    def _fill_detail(self, d, o):
        """Écrit TOUTES les colonnes Excel de l'offre dans le widget texte d."""
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
                meta.append(f"{lbl} : {str(v).replace('_', ' ')}")
        yrs = o.get("exp_requise")
        if yrs:  # années d'expérience exigées (l'utilisateur junior → fit pénalisé si ≥3)
            meta.append(f"⚠️ Exp requise: {yrs} ans" if yrs >= 3 else f"Exp requise: {yrs} ans")
        if meta:
            d.insert("end", "\n".join(meta) + "\n", "m")
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
                d.insert("end", f"\n{lbl} : ", "k")
                d.insert("end", v)
        d.configure(state="disabled")
        d.see("1.0")

    def _show_detail(self, o):
        self._fill_detail(self.detail, o)

    def _fiche_popup(self, e=None):
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
            btn, text="Pas intéressé", command=lambda: (self._pas_interesse(o), w.destroy()), bg=BTN
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
                command=lambda: (w.destroy(), self._cv_viewer(str(cvp))),
                bg=BTN,
                fg=TX,
                relief="flat",
            ).pack(side="left", padx=12)
        ltp = self._lettre_of(o)
        if ltp:
            CB(
                btn,
                text="Voir lettre",
                command=lambda: (w.destroy(), self._cv_viewer(str(ltp))),
                bg=BTN,
                fg=TX,
                relief="flat",
            ).pack(side="left", padx=12)
        CB(btn, text="Fermer", command=w.destroy, bg=BTN, fg=TX, relief="flat").pack(side="right")

    def _fetch_desc(self, o, textwidget, btn):
        """Récupère la description de l'offre en ligne (scrape_desc.py, headless) → queue → détail."""
        key = self._oid(o)
        if not (o.get("url") or "").startswith("http"):
            self._log("✗ pas d'URL http pour récupérer la description\n")
            return
        try:
            btn.configure(text="Chargement…", state="disabled")
        except Exception:
            pass

        def work():
            try:
                r = subprocess.run(
                    [PY, "scrape_desc.py", "--key", key],
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

        def done(out):
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
                btn.configure(text="Description", state="normal")
            except Exception:
                pass
            self._log(
                "✅ description récupérée\n"
                if o.get("description")
                else "✗ description introuvable (page JS/mur login ?)\n"
            )

        threading.Thread(target=work, daemon=True).start()

    def _toggle_account(self):
        """Marque/retire un compte pour ce site (comptes_sites.json)."""
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

    def save_edit(self):
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

    def _ecrire_suivi(self, oid, rec):
        """UNE candidature, écrite sous verrou sur l'état frais du disque.

        L'app écrivait `self.suivi`, son instantané mémoire : un clic « postulé »
        réécrivait tout le fichier et effaçait ce que `relances.py` y avait mis
        entre-temps. Reproduit — deux relances perdues sans un mot. On n'écrit
        plus qu'une entrée, et `suivi_io` relit le disque à l'intérieur du
        verrou : le travail des autres est conservé.
        """
        try:
            # Attente COURTE : Tkinter est mono-fil, une attente longue dans un
            # gestionnaire de clic fige la fenetre et l'app parait plantee.
            suivi_io.poser(oid, rec, _commun.SUIVI, attente=4)
        except suivi_io.VerrouIndisponible:
            self._log("✗ un autre programme écrit suivi.json — réessaie dans un instant.\n")
            return False
        except Exception as ex:
            self._log(f"! écriture suivi.json KO: {ex}\n")
            return False
        # On recharge depuis le disque plutot que de patcher la memoire : c'est
        # le seul etat qui tienne compte des autres ecrivains.
        self.suivi = suivi_io.charger(_commun.SUIVI)
        return True
