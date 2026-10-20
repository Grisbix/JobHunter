"""Log and execution of the programs (steps, maintenance, update).

Part of jobhunter.app (former JobHunter.pyw, phase 3.7)."""

import datetime
import queue
import subprocess
import threading
from tkinter import messagebox, scrolledtext, simpledialog
from typing import Any

from jobhunter import frozen as _gele
from jobhunter.app import language as _langue
from jobhunter.app import theme as _theme
from jobhunter.app._app_type import AppTypee
from jobhunter.app.common import INTERACTIVE, PY, QUEUE, ROOT, SCRIPTS, ouvrir
from jobhunter.app.language import t as _t
from jobhunter.app.theme import ACC, CB, CF, DEL, DEL_TX, LOGBG, LOGFG, SIDE, SIDE_H, SIDE_TX
from jobhunter.links import existe as _doc_existe
from jobhunter.storage import queue as queue_io


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
        txt = _langue.journal(str(txt))  # the app's messages; F5
        self.log.insert("end", txt)
        self.log.see("end")
        # Same fallback, the log must be summarisable at a glance.
        ligne = next((l.strip() for l in reversed(str(txt).split(chr(10))) if l.strip()), "")
        if ligne and getattr(self, "status", None) is not None:
            self.status.configure(text=ligne[:96])

    # ── execution ──
    def run_step(self: "AppTypee", cmd: Any, label: Any) -> None:
        # interactive scripts OR ones reusing Chrome (--chrome) -> new console (Chrome visible)
        if any(s in cmd for s in INTERACTIVE) or "--chrome" in cmd:
            self.run_console(cmd, label)
            return
        if self._occupe():
            return
        self._log(f"\n{'=' * 56}\n▶ {label}\n{'=' * 56}\n")
        threading.Thread(target=self._exec, args=(cmd, cmd[-1]), daemon=True).start()

    def _occupe(self: "AppTypee") -> Any:
        """Is something already writing the queue? Says so, and returns True if yes.

        `_bg_busy` covered the two automatic jobs between themselves, but NOT the
        buttons: starting "TOUT FAIRE" while the auto-enrichment was running made
        one of the two hit the lock, after having started. The scan can last thirty
        minutes — better to say so beforehand.
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
        """Launches in a dedicated console: visible Chrome + keyboard prompt (Enter per offer)."""
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
        # SHORT version of the pipeline: six steps, by hand. The scheduled task
        # runs daily_pipeline, which does more (collection in five
        # passes fusionnees chacune, sauvegarde, sites carriere, dossiers).
        # The old sequence stopped at the re-score: no descriptions, no
        # export CSV, ni alerte.
        seq = [
            ("1/6 Scan offres (ATS + LinkedIn + V.I.E)", [PY, "-m", "jobhunter.sources", "--all"]),
            (
                "2/6 Descriptions LinkedIn",
                [
                    PY,
                    "-m",
                    "jobhunter.programs.scrape_desc",
                    "--all",
                    "--canal",
                    "linkedin",
                    "--limit",
                    "150",
                ],
            ),
            ("3/6 Re-score fit + ATS", [PY, "-m", "jobhunter.programs.rescore_ats"]),
            (
                "4/6 Verif liens morts",
                [PY, "-m", "jobhunter.programs.recheck_dead", "--status", "OK", "--limit", "120"],
            ),
            ("5/6 Export CSV", [PY, "-m", "jobhunter.programs.export_queue_csv", "--keep", "8"]),
            (
                "6/6 Alerte nouveaux matchs",
                [PY, "-m", "jobhunter.programs.notify_matches", "--min-fit", "8"],
            ),
        ]
        self._log(f"\n{'=' * 56}\n▶ TOUT FAIRE — pipeline complet (6 etapes)\n{'=' * 56}\n")
        threading.Thread(target=self._exec_seq, args=(seq,), daemon=True).start()

    def mettre_a_jour(self: "AppTypee", en_attente: Any = False) -> None:
        """update.py in the app's log, then offers to restart JobHunter on the
        new version (the code already loaded stays the old one).

        At start-up, the announcement often arrives during background work (auto
        scan, docs sync): `_occupe()` then silently refused the "Oui". We wait for
        that work to finish — replacing the scripts under a running program is not
        an option."""
        if _gele.est_gele():
            # Installed application: the update is the new installer, which
            # the tool downloads, checks (author's signature) and opens; the data
            # does not move. Its messages go to the log, line by line.
            import contextlib
            import io

            from jobhunter.programs import update as _maj

            q = self.q

            class _VersJournal(io.TextIOBase):
                def write(self, s: str) -> int:
                    q.put(("line", s))
                    return len(s)

            self._log(f"\n{'=' * 56}\n▶ Mise à jour de JobHunter\n{'=' * 56}\n")

            def maj_installee() -> None:
                with contextlib.redirect_stdout(_VersJournal()):
                    _maj.maj_application(False)

            threading.Thread(target=maj_installee, daemon=True).start()
            return
        if (self.proc and self.proc.poll() is None) or getattr(self, "_bg_busy", False):
            if not en_attente:
                self._log("\n⏳ Mise à jour : elle démarre dès que le travail en cours est fini.\n")
            self.root.after(3000, lambda: self.mettre_a_jour(en_attente=True))
            return
        try:
            from jobhunter.programs import update as mise_a_jour

            avant = mise_a_jour.version_locale()
        except Exception:
            mise_a_jour, avant = None, "?"  # type: ignore[assignment]  # module missing: None, tested below
        self._log(f"\n{'=' * 56}\n▶ Mise à jour de JobHunter\n{'=' * 56}\n")

        def tache() -> None:
            ok = self._exec([PY, "-m", "jobhunter.programs.update"], "mise à jour")
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
            return  # already up to date: nothing to restart
        if messagebox.askyesno(
            _t("JobHunter — mise à jour"),
            _t("Version {v} installée. Relancer JobHunter maintenant ?").format(v=apres),
            parent=self.root,
        ):
            subprocess.Popen([PY, str(ROOT / "JobHunter.pyw")], cwd=str(ROOT))
            self.root.destroy()

    def _exec_seq(self: "AppTypee", seq: Any) -> None:
        """seq: list of (label, command). The label is for the log — cmd[-1]
        displayed the last ARGUMENT ("8", "linkedin"), not the step."""
        # The outcome travels with the event: None = everything succeeded, otherwise the step
        # that failed. "TOUT FAIRE terminé" was displayed even after a failure (audit 19/10).
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
        # Code 3 = another program holds the queue lock (jutil.garder).
        # "[exit 3]" alone tells nothing: we say what happened, and above all
        # that nothing was changed.
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

    # ── crash log ────────────────────────────────────────────────────────────
    JOURNAL = SCRIPTS / "_logs" / "app_erreurs.log"

    def _journal_panne(self: "AppTypee", contexte: Any, exc: Any = None) -> None:
        """Stores a trace in _logs/app_erreurs.log and summarises it in the UI.

        Without it, a failure in a Tk callback is invisible: `.pyw` has no
        console, stderr goes nowhere, and the app still looks alive.
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
            pass  # logging must never become the next failure
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
            # ONE FAULTY LINE KILLED THE APP. Only queue.Empty was
            # caught: any other failure exited BEFORE the `after` of the
            # last line, and nothing rescheduled itself any more. Measured: 1 loop
            # iteration instead of 20, and zero reloads — the table never
            # refreshed again after a scan, without the slightest sign.
            self._journal_panne("_drain", ex)
        finally:
            # The `finally` is the fix: the loop reschedules itself WHATEVER
            # HAPPENS. A lost line is better than a frozen application.
            self.root.after(100, self._drain)

    def stop(self: "AppTypee") -> None:
        """Stops the current task, CHILDREN INCLUDED.

        proc.terminate() only kills the Python that was started; Playwright and
        Chrome are its grandchildren and survive. We found 14 orphans holding the
        dedicated profile, which then prevented any restart. taskkill /T cuts the
        whole tree."""
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
        """Generates CV + letter for the N best-scored offers that do not have them.

        The number was fixed at 30: with 284 offers without documents, one had to
        click ten times. We ask for it, offering the real count to do."""
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
            [PY, "-m", "jobhunter.programs.generate_docs", "--top", str(n)],
            f"CV/lettres — {n} offre(s)",
        )
