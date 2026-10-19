"""Journal et execution des programmes (etapes, maintenance, mise a jour).

Partie de jobhunter.app (ancien JobHunter.pyw, phase 3.7)."""

import datetime
import queue
import subprocess
import threading
from tkinter import messagebox, scrolledtext, simpledialog
from typing import Any

from jobhunter import gele as _gele
from jobhunter.app import langue as _langue
from jobhunter.app import theme as _theme
from jobhunter.app._type_app import AppTypee
from jobhunter.app.commun import INTERACTIVE, PY, QUEUE, ROOT, SCRIPTS, ouvrir
from jobhunter.app.langue import t as _t
from jobhunter.app.theme import ACC, CB, CF, DEL, DEL_TX, LOGBG, LOGFG, SIDE, SIDE_H, SIDE_TX
from jobhunter.liens import existe as _doc_existe
from jobhunter.stockage import file as queue_io


class ExecutionMixin:
    def _build_log(self: "AppTypee", parent: Any) -> None:
        qf = CF(parent, bg=SIDE, plat=True)
        qf.pack(fill="x", padx=12, pady=(8, 2))
        CB(
            qf,
            text="Dossier",
            command=lambda: ouvrir(ROOT),
            bg=SIDE_H,
            fg=SIDE_TX,
            activebackground=ACC,
            relief="flat",
        ).pack(side="left")
        CB(qf, text="Arrêter", command=self.stop, bg=DEL, fg=DEL_TX, relief="flat").pack(
            side="right"
        )
        self.log = scrolledtext.ScrolledText(
            parent,
            bg=LOGBG,
            fg=LOGFG,
            insertbackground=LOGFG,
            font=(_theme.FONT_MONO, 10),
            relief="flat",
            height=3,
            wrap="word",
        )
        self.log.pack(fill="both", expand=True, padx=12, pady=(6, 12))
        self._log("Prêt. « ▶ TOUT FAIRE » régénère.\n")

    # ── UI helpers ──
    def _log(self: "AppTypee", txt: Any) -> None:
        txt = _langue.journal(str(txt))  # les messages de l'app ; F5
        self.log.insert("end", txt)
        self.log.see("end")
        # Meme repli, le journal doit pouvoir se resumer en un coup d'oeil.
        ligne = next((l.strip() for l in reversed(str(txt).split(chr(10))) if l.strip()), "")
        if ligne and getattr(self, "status", None) is not None:
            self.status.configure(text=ligne[:96])

    # ── exécution ──
    def run_step(self: "AppTypee", cmd: Any, label: Any) -> None:
        # scripts interactifs OU réutilisant Chrome (--chrome) -> nouvelle console (Chrome visible)
        if any(s in cmd for s in INTERACTIVE) or "--chrome" in cmd:
            self.run_console(cmd, label)
            return
        if self._occupe():
            return
        self._log(f"\n{'=' * 56}\n▶ {label}\n{'=' * 56}\n")
        threading.Thread(target=self._exec, args=(cmd, cmd[-1]), daemon=True).start()

    def _occupe(self: "AppTypee") -> Any:
        """Quelque chose écrit-il déjà la file ? Le dit, et rend True si oui.

        `_bg_busy` couvrait les deux jobs automatiques entre eux, mais PAS les
        boutons : lancer « TOUT FAIRE » pendant que l'auto-enrichissement
        tournait faisait tomber l'un des deux sur le verrou, après avoir
        démarré. Le scan peut durer trente minutes — autant le dire avant.
        """
        if self.proc and self.proc.poll() is None:
            self._log("⏳ tâche en cours.\n")
            return True
        if getattr(self, "_bg_busy", False):
            self._log(
                "⏳ un travail de fond écrit la file (descriptions ou sync docs).\n"
                "   Réessaie dans un instant — il se termine tout seul.\n"
            )
            return True
        return False

    def run_console(self: "AppTypee", cmd: Any, label: Any) -> None:
        """Lance dans une console dédiée : Chrome visible + prompt clavier (Entrée par offre)."""
        self._log(
            f"\n▶ {label} — fenêtre CONSOLE ouverte. Chrome s'ouvre ; "
            f"tape Entrée après chaque envoi. Ferme la console pour arrêter.\n"
        )
        try:
            subprocess.Popen(
                cmd, cwd=str(SCRIPTS), creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0x10)
            )
        except Exception as e:
            self._log(f"! lancement console KO: {e}\n")

    def run_all(self: "AppTypee") -> None:
        if self._occupe():
            return
        # Version COURTE du pipeline : six etapes, a la main. La tache planifiee
        # lance pipeline_quotidien.py, qui en fait davantage (collecte en cinq
        # passes fusionnees chacune, sauvegarde, sites carriere, dossiers).
        # L'ancien enchainement s'arretait au re-score : ni descriptions, ni
        # export CSV, ni alerte.
        seq = [
            ("1/6 Scan offres (ATS + LinkedIn + V.I.E)", [PY, "-m", "jobhunter.sources", "--all"]),
            (
                "2/6 Descriptions LinkedIn",
                [
                    PY,
                    "-m",
                    "jobhunter.programmes.scrape_desc",
                    "--all",
                    "--canal",
                    "linkedin",
                    "--limit",
                    "150",
                ],
            ),
            ("3/6 Re-score fit + ATS", [PY, "-m", "jobhunter.programmes.rescore_ats"]),
            (
                "4/6 Verif liens morts",
                [PY, "-m", "jobhunter.programmes.recheck_dead", "--status", "OK", "--limit", "120"],
            ),
            ("5/6 Export CSV", [PY, "-m", "jobhunter.programmes.export_queue_csv", "--keep", "8"]),
            (
                "6/6 Alerte nouveaux matchs",
                [PY, "-m", "jobhunter.programmes.notify_matches", "--min-fit", "8"],
            ),
        ]
        self._log(f"\n{'=' * 56}\n▶ TOUT FAIRE — pipeline complet (6 etapes)\n{'=' * 56}\n")
        threading.Thread(target=self._exec_seq, args=(seq,), daemon=True).start()

    def mettre_a_jour(self: "AppTypee", en_attente: Any = False) -> None:
        """mise_a_jour.py dans le journal de l'app, puis propose de relancer
        JobHunter sur la nouvelle version (le code deja charge reste l'ancien).

        Au demarrage, l'annonce arrive souvent pendant un travail de fond (scan
        auto, sync docs) : `_occupe()` refusait alors le « Oui » en silence. On
        attend la fin de ce travail — remplacer les scripts sous un programme qui
        tourne n'est pas une option."""
        if _gele.est_gele():
            # Application installée : la mise à jour est le nouvel installateur, que
            # l'utilisateur télécharge et lance ; ses données ne bougent pas.
            import webbrowser

            from jobhunter.programmes import mise_a_jour as _maj

            self._log("🌐 Télécharge JobHunterSetup.exe sur la page ouverte, puis lance-le.\n")
            webbrowser.open(_maj.PAGE_VERSIONS)
            return
        if (self.proc and self.proc.poll() is None) or getattr(self, "_bg_busy", False):
            if not en_attente:
                self._log("\n⏳ Mise à jour : elle démarre dès que le travail en cours est fini.\n")
            self.root.after(3000, lambda: self.mettre_a_jour(en_attente=True))
            return
        try:
            from jobhunter.programmes import mise_a_jour

            avant = mise_a_jour.version_locale()
        except Exception:
            mise_a_jour, avant = None, "?"  # type: ignore[assignment]  # module absent : None, teste plus bas
        self._log(f"\n{'=' * 56}\n▶ Mise à jour de JobHunter\n{'=' * 56}\n")

        def tache() -> None:
            ok = self._exec([PY, "-m", "jobhunter.programmes.mise_a_jour"], "mise à jour")
            apres = mise_a_jour.version_locale() if mise_a_jour else "?"
            self.q.put(("maj_fin", (ok, avant, apres)))

        threading.Thread(target=tache, daemon=True).start()

    def _apres_mise_a_jour(self: "AppTypee", ok: Any, avant: Any, apres: Any) -> None:
        if not ok:
            messagebox.showwarning(
                _t("JobHunter — mise à jour"),
                _t(
                    "La mise à jour n'a pas abouti ; le détail est dans "
                    "le journal. Tes données n'ont pas été touchées."
                ),
                parent=self.root,
            )
            return
        if apres == avant:
            return  # deja a jour : rien a relancer
        if messagebox.askyesno(
            _t("JobHunter — mise à jour"),
            _t("Version {v} installée. Relancer JobHunter maintenant ?").format(v=apres),
            parent=self.root,
        ):
            subprocess.Popen([PY, str(ROOT / "JobHunter.pyw")], cwd=str(ROOT))
            self.root.destroy()

    def _exec_seq(self: "AppTypee", seq: Any) -> None:
        """seq : liste de (libelle, commande). Le libelle sert au log — cmd[-1]
        affichait le dernier ARGUMENT (« 8 », « linkedin »), pas l'etape."""
        # L'issue voyage avec l'evenement : None = tout a reussi, sinon l'etape qui a
        # echoue. « TOUT FAIRE termine » s'affichait meme apres un echec (audit 19/10).
        echec = None
        for label, cmd in seq:
            if not self._exec(cmd, label, announce=True):
                echec = label
                break
        self.q.put(("done_all", echec))

    def _exec(self: "AppTypee", cmd: Any, label: Any, announce: Any = False) -> Any:
        if announce:
            self.q.put(("line", f"\n--- {label} ---\n"))
        try:
            self.proc = subprocess.Popen(
                cmd,
                cwd=str(SCRIPTS),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except Exception as e:
            self.q.put(("line", f"! lancement KO: {e}\n"))
            return False
        for line in self.proc.stdout:
            self.q.put(("line", line))
        code = self.proc.wait()
        self.q.put(("line", f"[exit {code}]\n"))
        # Code 3 = un autre programme tient le verrou de la queue (jutil.garder).
        # « [exit 3] » seul n'apprend rien : on dit ce qui s'est passe, et surtout
        # que rien n'a ete modifie.
        if code == 3:
            self.q.put(
                (
                    "line",
                    "⚠ Un autre programme ecrit apply_queue.json en ce moment.\n"
                    "  Rien n'a ete touche. Reessaie quand il aura fini.\n",
                )
            )
        self.q.put(("reload", None))
        return code == 0

    # ── journal des pannes ───────────────────────────────────────────────────
    JOURNAL = SCRIPTS / "_logs" / "app_erreurs.log"

    def _journal_panne(self: "AppTypee", contexte: Any, exc: Any = None) -> None:
        """Range une trace dans _logs/app_erreurs.log et la résume dans l'UI.

        Sans ça, une panne dans un rappel Tk est invisible : `.pyw` n'a pas de
        console, stderr ne va nulle part, et l'app garde l'air vivante.
        """
        import traceback

        trace = traceback.format_exc()
        try:
            self.JOURNAL.parent.mkdir(parents=True, exist_ok=True)
            with open(self.JOURNAL, "a", encoding="utf-8") as f:
                f.write(
                    f"\n{'=' * 60}\n{datetime.datetime.now():%Y-%m-%d %H:%M:%S}  "
                    f"[{contexte}]\n{trace}"
                )
        except Exception:
            pass  # journaliser ne doit jamais devenir la panne suivante
        resume = (
            f"{type(exc).__name__}: {exc}" if exc is not None else trace.strip().split("\n")[-1]
        )
        try:
            self._log(
                f"! panne interne [{contexte}] — {resume[:120]}\n"
                f"  trace complète : Scripts/_logs/app_erreurs.log\n"
            )
        except Exception:
            pass

    def _panne_tk(self: "AppTypee", typ: Any, val: Any, tb: Any) -> None:
        """Rappel d'exception global de Tk (bouton, menu, binding)."""
        self._journal_panne("rappel Tk", val)

    def _drain(self: "AppTypee") -> None:
        try:
            while True:
                kind, val = self.q.get_nowait()
                if kind == "line":
                    self._log(val)
                elif kind == "reload":
                    self.load_offers()
                    self.root.after(1500, self._auto_enrich)
                elif kind == "done_all":
                    if val is None:
                        self._log("\n✅ TOUT FAIRE terminé.\n")
                    else:
                        self._log(f"\n✗ TOUT FAIRE interrompu à l'étape « {val} ».\n")
                    self.load_offers()
                    self.root.after(1500, self._auto_enrich)
                elif kind == "maj_fin":
                    self._apres_mise_a_jour(*val)
                elif kind == "candidature":
                    self._cand_evenement(val)
        except queue.Empty:
            pass
        except Exception as ex:
            # UNE SEULE LIGNE FAUTIVE TUAIT L'APP. Seul queue.Empty etait
            # rattrape : toute autre panne sortait AVANT le `after` de la
            # derniere ligne, et plus rien ne se reprogrammait. Mesure : 1 tour
            # de boucle au lieu de 20, et zero rechargement — la table ne se
            # rafraichissait plus jamais apres un scan, sans le moindre signe.
            self._journal_panne("_drain", ex)
        finally:
            # Le `finally` est le correctif : la boucle se reprogramme QUOI QU'IL
            # ARRIVE. Une ligne perdue vaut mieux qu'une application figee.
            self.root.after(100, self._drain)

    def stop(self: "AppTypee") -> None:
        """Arrete la tache en cours, ENFANTS COMPRIS.

        proc.terminate() ne tue que le Python lance ; Playwright et Chrome sont
        ses petits-enfants et survivent. On en a retrouve 14 orphelins tenant le
        profil dedie, ce qui empechait ensuite toute relance. taskkill /T coupe
        l'arbre entier."""
        if not (self.proc and self.proc.poll() is None):
            self._log("(aucune tache en cours)\n")
            return
        pid = self.proc.pid
        try:
            subprocess.run(
                ["taskkill", "/T", "/F", "/PID", str(pid)],
                capture_output=True,
                timeout=20,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            self._log(f"⏹ arrete (arbre du PID {pid})." + "\n")
        except Exception as e:
            err = type(e).__name__
            self._log(f"! arret KO ({err}) — repli sur terminate\n")
            try:
                self.proc.terminate()
            except Exception:
                pass

    def _gen_docs(self: "AppTypee") -> None:
        """Genere CV + lettre pour les N offres les mieux notees qui n'en ont pas.

        Le nombre etait fige a 30 : avec 284 offres sans documents, il fallait
        cliquer dix fois. On le demande, en proposant le compte reel a faire."""
        try:
            q = queue_io.charger(QUEUE)
        except Exception:
            q = list(self.offers)

        def _f(u: Any) -> Any:
            if not u:
                return False
            try:
                return _doc_existe(u)
            except Exception:
                return False

        reste = sum(
            1
            for o in q
            if (o.get("fit") or 0) >= 8 and not (_f(o.get("cv")) and _f(o.get("lettre")))
        )
        n = simpledialog.askinteger(
            "CV / lettres",
            f"Combien d'offres traiter ?\n\n"
            f"{reste} offre(s) a fit ≥ 8 attendent encore leurs documents.",
            parent=self.root,
            initialvalue=min(reste or 30, 50),
            minvalue=1,
            maxvalue=1000,
        )
        if not n:
            return
        self.run_step(
            [PY, "-m", "jobhunter.programmes.generate_docs", "--top", str(n)],
            f"CV/lettres — {n} offre(s)",
        )
