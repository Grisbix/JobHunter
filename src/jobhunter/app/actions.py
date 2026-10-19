"""Actions sur les offres : statut, ecarter, supprimer (avec corbeille), postuler (clic humain).

Partie de jobhunter.app (ancien JobHunter.pyw, phase 3.7)."""

import datetime
import json
import os
import tkinter as tk
import webbrowser
from tkinter import messagebox
from typing import Any
from urllib.parse import quote

import customtkinter as ctk

from jobhunter.app import commun as _commun
from jobhunter.app import theme as _theme
from jobhunter.app._type_app import AppTypee
from jobhunter.app.commun import EXPIRE, PAS_INTERESSE, QUEUE, SCRIPTS, ST_EMOJI
from jobhunter.app.langue import t as _t
from jobhunter.app.theme import BG, BTN, BTN_H, CARD, CB, CE, CF, CL, DEL, MUT, TX, WORK
from jobhunter.stockage import file as queue_io
from jobhunter.stockage import suivi as suivi_io


class ActionsMixin:
    def _set_statut(self: "AppTypee", o: Any, statut: Any) -> None:
        """Écrit un statut dans suivi.json (date auto = aujourd'hui si absente). Manuel > auto."""
        if not o:
            return
        oid = self._oid(o)
        # On repart de l'entree TELLE QU'ELLE EST SUR LE DISQUE, pas de la copie
        # memoire : une note ou une relance ajoutee entre-temps doit survivre.
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
        self.refresh_table()

    def _pas_interesse(self: "AppTypee", o: Any) -> None:
        """Suppr / bouton / clic droit : l'offre sort du tableau, reste en file.

        Le curseur passe a la ligne suivante AVANT le rafraichissement : sinon
        il retombe en tete de tableau et chaque offre triee coute un defilement.
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
        """Toutes les offres cochees d'un coup. Un seul Ctrl+Z les rend toutes."""
        oids = [k for k in self.checked if self._find_by_oid(k)]
        if not oids:
            self._log("Coche d'abord des offres (colonne ☐).\n")
            return
        geste: list[Any] = []
        jour = datetime.date.today().isoformat()

        def _f(s: Any) -> None:  # UNE transaction : verrou, relecture, ecriture
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
        """Ctrl+Z : remet le suivi du dernier geste tel qu'il etait avant."""
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
        """Enregistre uniquement un envoi explicitement confirmé par l'utilisateur.

        Déclaration manuelle, sans observation de la page : `envoi` = « déclaré »
        (ADR 0009). Une preuve déjà observée n'est jamais effacée."""
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
        self.refresh_table()

    def _apply_checked(self: "AppTypee") -> None:
        """Postule TOUTES les offres cochées : runner semi-auto (remplit + upload, STOP sur
        Envoyer = toi). Écrit la sélection dans apply_selection.json, lance la console."""
        oids = [o for o in [self._find_by_oid(k) for k in self.checked] if o]
        if not oids:
            self._log("Coche d'abord des offres (colonne ☐).\n")
            return
        sel = [{"entreprise": o.get("entreprise", ""), "poste": o.get("poste", "")} for o in oids]
        SEL = SCRIPTS / "apply_selection.json"
        try:
            SEL.write_text(json.dumps(sel, ensure_ascii=False, indent=1), encoding="utf-8")
        except Exception as ex:
            self._log(f"! écriture sélection KO: {ex}\n")
            return
        # Panneau Candidatures : le programme remplit et s'arrete sur Envoyer, l'utilisateur
        # clique dans Chrome puis « J'ai envoyé » ; plus de console (2.2.0).
        self._candidater(SEL, len(sel))

    def _find_by_oid(self: "AppTypee", oid: Any) -> Any:
        for o in self.offers:
            if self._oid(o) == oid:
                return o
        return None

    def _row_menu(self: "AppTypee", e: Any) -> None:
        """Clic droit sur une ligne → actions par offre (Postuler + statuts rapides)."""
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
                command=lambda s=s: self._set_statut(o, s),  # type: ignore[misc]  # lambda a parametre par defaut (capture de boucle)
            )
        # « mauvaise » a part, apres un separateur : ce n'est pas une etape du
        # parcours de candidature mais un jugement sur l'offre elle-meme.
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
        """Ouvre l'URL de l'offre ; sinon recherche web (entreprise + poste)."""
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
        # Sans ce message on croit l'app cassee : elle ouvre une page
        # d'accueil alors qu'on attendait une offre.
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
        """val True=coche tout (lignes filtrées visibles), False=décoche tout, None=bascule."""
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
        """Écarte les offres cochées AVEC un motif, et retient le refus.

        Supprimer ne suffit pas : le scan retrouve l'offre à la source et la
        réajoute le lendemain. Ici le refus est mémorisé dans exclusions.json,
        que merge_into_queue consulte avant d'ajouter quoi que ce soit.

        Le motif n'est pas un ornement. Un refus sur une offre à fit élevé est
        un désaccord entre le score et le jugement de l'utilisateur — c'est ce que lit
        `python JobHunter.pyw exclusions` pour montrer ce que la notation rate.
        """
        oids = set(self.checked)
        if not oids:
            self._log("Coche d'abord des offres (colonne ☐).\n")
            return
        motif = self._demander_motif(len(oids))
        if not motif:
            return
        try:
            from jobhunter.programmes import exclusions
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
            # On enregistre AVANT de retirer : si l'écriture de la file échoue,
            # mieux vaut une exclusion en trop qu'une offre écartée sans motif.
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
        """Petite boîte : motifs fréquents en boutons, plus un champ libre.

        Rend le motif choisi, ou None si l'utilisateur annule.

        Parente = self.root. Elle etait `self`, l'objet App, qui n'est pas un
        widget : Toplevel(self) levait a chaque clic et « Écarter » ne
        s'ouvrait jamais — l'exception partait dans le journal de panne.
        """
        try:
            from jobhunter.programmes import exclusions

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
        # grab APRES l'affichage : sur Windows, un grab_set sur une fenetre pas
        # encore visible echoue (« grab failed: window not viewable »).
        dlg.after(80, lambda: (dlg.grab_set(), e.focus_set()))
        self.root.wait_window(dlg)
        return choix["v"]

    CORBEILLE = SCRIPTS / "_corbeille"

    def _delete_checked(self: "AppTypee") -> None:
        """Supprime les offres cochées de apply_queue.json, après copie en corbeille.

        La boîte promettait « récupérable via git ». C'était faux le jour où je
        l'ai vérifié : le dernier commit de la file datait de la veille et
        424 offres du disque n'existaient dans aucun commit — dont les 428
        arrivées ce jour-là. Supprimer l'une d'elles la perdait pour de bon.
        On écrit donc une copie horodatée avant de retirer quoi que ce soit ;
        la promesse porte maintenant sur un fichier qui existe vraiment.
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
        # VERROU. Relire le disque juste avant d'ecrire REDUIT la fenetre de course
        # mais ne la ferme pas : un job de fond qui ecrit entre cette relecture et
        # notre ecriture voit son travail efface. L'app etait le SEUL des 14
        # ecrivains de la queue a ne pas prendre le verrou.
        if not self._verrou_queue(True):
            self._log("✗ un autre programme modifie la file — réessaie dans un instant.\n")
            return
        try:
            # état frais : les jobs de fond ont pu enrichir la queue depuis le
            # dernier chargement — sinon on écraserait leurs modifs
            try:
                fresh = queue_io.charger(QUEUE)
            except Exception:
                fresh = list(self.offers)
            before = len(fresh)
            partantes = [o for o in fresh if self._oid(o) in oids]
            fresh = [o for o in fresh if self._oid(o) not in oids]
            removed = before - len(fresh)
            # LA COPIE D'ABORD. Si l'écriture de la file échoue ensuite, on a une
            # corbeille en trop ; dans l'autre ordre, on aurait des offres
            # supprimées sans copie. `charger()` a réinjecté les descriptions,
            # elles partent donc avec.
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
                # sauver() ressort les descriptions vers descriptions.json ;
                # _jwrite les réécrirait dans la file et annulerait la séparation.
                queue_io.sauver(fresh, QUEUE)
            except Exception as ex:
                self._log(f"! écriture queue KO: {ex}\n")
                return
        finally:
            self._verrou_queue(False)
        self.checked.clear()
        self.load_offers()  # recharge l'état frais
        self._log(
            f"🗑 {removed} offre(s) supprimée(s) — copie dans Scripts/_corbeille/{sauvegarde}\n"
        )

    # ── visionneuse CV & LETTRES : panneau INTÉGRÉ (remplace le dashboard, Retour) ──
    # PDF → PyMuPDF (toutes les pages EMPILÉES, molette = dérouler en entier)
    # DOCX/TXT → texte extrait (python-docx) dans un panneau scrollable
    @staticmethod
    def _verrou_queue(prendre: Any, _attente: Any = 20) -> Any:
        """Prend / rend le verrou inter-processus de la queue. True si obtenu.

        Attente courte (20 s) : c'est une action interactive, mieux vaut dire
        « reessaie » que figer la fenetre 3 minutes.
        """
        try:
            from jobhunter.programmes import jutil
        except Exception:
            return True  # jutil introuvable : on n'empeche pas d'agir
        try:
            if prendre:
                return jutil.prendre_verrou(QUEUE, attente=_attente)
            jutil.rendre_verrou(QUEUE)
            return True
        except Exception:
            # UNE PANNE DU VERROU N'EST PAS UN FEU VERT. Ce cas rendait True et
            # l'action destructive continuait sans protection — l'inverse de ce
            # que le verrou existe pour empecher. Rendre la main est sans
            # risque : l'appelant affiche « reessaie ». Le cas « jutil
            # introuvable » ci-dessus reste permissif, lui : sans Scripts/
            # l'app n'a de toute facon pas de file a proteger.
            return not prendre

    @staticmethod
    def _jwrite(path: Any, obj: Any) -> None:
        """Écriture JSON ATOMIQUE (tmp + replace) : un crash mi-écriture ne corrompt jamais le fichier."""
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")
        os.replace(str(tmp), str(path))
