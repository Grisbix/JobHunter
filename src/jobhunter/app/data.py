"""App data: loading the queue, background enrichment and sync, follow-ups.

Part of jobhunter.app (former JobHunter.pyw, phase 3.7)."""

import datetime
import importlib
import json
import subprocess
import threading
from typing import Any
from urllib.parse import urlparse

from jobhunter.app import common as _commun
from jobhunter.app._app_type import AppTypee
from jobhunter.app.common import LF, PY, QUEUE, SCRAPE_TAG, SCRIPTS
from jobhunter.storage import queue as queue_io


class DonneesMixin:
    # ── data ──
    def _oid(self: "AppTypee", o: Any) -> Any:
        return f"{(o.get('entreprise') or '').strip()}|{(o.get('poste') or '').strip()}"

    def _host(self: "AppTypee", o: Any) -> Any:
        u = o.get("url") or ""
        return urlparse(u).netloc.replace("www.", "").lower() if u.startswith("http") else ""

    def _acct_of(self: "AppTypee", o: Any) -> Any:
        """Known account for this site? Host match (exact or subdomain). Returns info|None."""
        host = self._host(o)
        if not host:
            return None
        if o.get("etat"):
            return {
                "site": o.get("entreprise", ""),
                "login": o.get("url", ""),
                "email": self.myemail,
                "src": "etat",
            }
        for h, info in self.comptes.items():
            if host == h or host.endswith("." + h) or h.endswith("." + host):
                return info
        return None

    def load_offers(self: "AppTypee") -> None:
        # the queue changes (scan, deletions): the cached searchable text
        # would otherwise describe offers that no longer exist
        self._search_cache.clear()
        try:
            self.offers = queue_io.charger(QUEUE)
        except Exception:
            self.offers = []
        try:
            self.suivi = importlib.import_module("jobhunter.storage.applications").charger(
                _commun.SUIVI
            )
        except Exception:
            self.suivi = {}
        try:
            self.comptes = json.loads(_commun.COMPTES.read_text(encoding="utf-8"))
        except Exception:
            self.comptes = {}
        self.refresh_table()

    def _missing_desc(self: "AppTypee") -> Any:
        """Offers with an http URL but no description (to enrich automatically)."""
        return [
            o
            for o in self.offers
            if str(o.get("url") or "").startswith("http")
            and not (o.get("description") or "").strip()
        ]

    def _auto_enrich(self: "AppTypee") -> None:
        """AUTO (no button): fetches the missing descriptions in the background, in batches,
        then re-scores ATS, reloads, and chains while some remain. Headless, silent.
        _bg_busy LOCK shared with _auto_sync: never 2 jobs writing the queue at the same time."""
        if getattr(self, "_desc_busy", False) or getattr(self, "_bg_busy", False):
            return
        # cap per session: avoids scraping 1300 offers at once (rate limit/ban)
        if getattr(self, "_desc_batches", 0) >= 8:
            return
        todo = self._missing_desc()
        if not todo:
            return
        self._desc_busy = True
        self._bg_busy = True
        self._desc_batches = getattr(self, "_desc_batches", 0) + 1
        n = len(todo)
        self._log(f"ℹ {n} description(s) manquante(s) — récupération auto en fond…\n")

        def work() -> None:
            try:
                subprocess.run(
                    [PY, "-m", "jobhunter.programs.scrape_desc", "--all", "--limit", "40"],
                    cwd=str(SCRIPTS),
                    capture_output=True,
                    text=True,
                    timeout=900,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                subprocess.run(
                    [PY, "-m", "jobhunter.programs.rescore_ats"],
                    cwd=str(SCRIPTS),
                    capture_output=True,
                    text=True,
                    timeout=300,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
            except Exception as e:
                err = type(e).__name__
                self.root.after(0, lambda n=err: self._log(f"! auto-desc: {n}\n"))
            self.root.after(0, done)

        def done() -> None:
            self._desc_busy = False
            self._bg_busy = False
            self.load_offers()  # reload (descriptions + ATS updated) → table refreshed
            rest = len(self._missing_desc())
            got = n - rest
            self._log(
                f"✅ descriptions: +{got} récupérées ({rest} restantes, dont Indeed/anti-bot).\n"
            )
            if rest and got:  # some remain AND we are making progress → next batch
                self.root.after(1500, self._auto_enrich)

        threading.Thread(target=work, daemon=True).start()

    def _auto_sync(self: "AppTypee") -> None:
        """AUTO: sync_docs.py in the background — modified docx → regenerated pdf, queue links repaired.
        Rerun every 10 min while the app runs."""
        if getattr(self, "_sync_busy", False) or getattr(self, "_bg_busy", False):
            self.root.after(120000, self._auto_sync)
            return  # busy → try again in 2 min
        self._sync_busy = True
        self._bg_busy = True

        def work() -> None:
            try:
                r = subprocess.run(
                    [PY, "-m", "jobhunter.programs.sync_docs"],
                    cwd=str(SCRIPTS),
                    capture_output=True,
                    text=True,
                    timeout=3000,
                    encoding="utf-8",
                    errors="replace",
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                lines = [l for l in (r.stdout or "").splitlines() if l.strip()]
                msg = " · ".join(lines[-2:])[:110] if lines else ""
            except Exception as e:
                msg = f"! {type(e).__name__}"

            def done() -> None:
                self._sync_busy = False
                self._bg_busy = False
                if msg and not msg.startswith("pdf créés: 0 · pdf resynchronisés: 0"):
                    self._log(f"🔁 sync docs : {msg}\n")
                self.root.after(600000, self._auto_sync)  # re-check in 10 min

            self.root.after(0, done)

        threading.Thread(target=work, daemon=True).start()

    _SCRAPE_COOLDOWN_S = 1800  # 30 min minimum between two triggered scans

    def _scrape_cooldown_ok(self: "AppTypee") -> Any:
        last = getattr(self, "_scrape_last", None)
        if last is None:
            return True
        return (datetime.datetime.now() - last).total_seconds() >= self._SCRAPE_COOLDOWN_S

    def _on_focus_scrape(self: "AppTypee", e: Any = None) -> None:
        """The window gets the focus back: we are back in the app, we refresh.

        Triggered by an event rather than a timer: no scan while the app is in the
        background, and the offers are fresh at the moment you look at them. The
        cooldown prevents a repeated alt-tab from starting a scan again.
        """
        if e is not None and getattr(e, "widget", None) is not self.root:
            return
        if self._scrape_cooldown_ok():
            self._auto_scrape()

    def _auto_scrape(self: "AppTypee") -> None:
        """AUTO: scrape_jobs.py in the background — new offers from company sites.

        Same pattern as _auto_sync, but 3 h apart: a scan that is too frequent gets
        rate-limited or banned. Cap per session like _auto_enrich.
        Shared _bg_busy LOCK: never 2 jobs writing the queue at the same time.
        """
        if getattr(self, "_scrape_busy", False) or getattr(self, "_bg_busy", False):
            self.root.after(300000, self._auto_scrape)
            return  # busy -> try again in 5 min
        if self.proc and self.proc.poll() is None:
            self.root.after(300000, self._auto_scrape)
            return  # a button is running -> 5 min
        if getattr(self, "_scrape_runs", 0) >= 4:
            return  # cap: 4 scans per session
        self._scrape_busy = True
        self._bg_busy = True
        self._scrape_last = datetime.datetime.now()
        self._scrape_runs = getattr(self, "_scrape_runs", 0) + 1
        avant = len(getattr(self, "offers", []) or [])

        def work() -> None:
            try:
                r = subprocess.run(
                    [PY, "-m", "jobhunter.programs.scrape_jobs", "--headless"],
                    cwd=str(SCRIPTS),
                    capture_output=True,
                    text=True,
                    timeout=1800,
                    encoding="utf-8",
                    errors="replace",
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                lines = [l for l in (r.stdout or "").splitlines() if l.strip()]
                msg = " - ".join(lines[-2:])[:110] if lines else ""
                if r.returncode != 0:
                    err = [l for l in (r.stderr or "").strip().splitlines() if l.strip()]
                    msg = (
                        ("! code %d - %s" % (r.returncode, err[-1][:80]))
                        if err
                        else ("! code %d" % r.returncode)
                    )
            except Exception as e:
                msg = "! %s" % type(e).__name__

            def done() -> None:
                self._scrape_busy = False
                self._bg_busy = False
                self.load_offers()  # table rafraichie
                neuf = len(getattr(self, "offers", []) or []) - avant
                if neuf > 0:
                    self._log(SCRAPE_TAG + " scan auto : +%d offre(s). %s%s" % (neuf, msg, LF))
                elif msg.startswith("!"):
                    self._log(SCRAPE_TAG + " scan auto : %s%s" % (msg, LF))
                # no more timer: the next scan will come from the window focus
                if neuf > 0:
                    self.root.after(1500, self._auto_enrich)  # descriptions of the new ones

            self.root.after(0, done)

        threading.Thread(target=work, daemon=True).start()

    def _check_relances(self: "AppTypee") -> None:
        """Reports at startup the "postulé" applications without answer for ≥ 10 d."""

        def work() -> None:
            try:
                import sys as _s

                if str(SCRIPTS) not in _s.path:
                    _s.path.insert(0, str(SCRIPTS))
                from jobhunter.programs import follow_ups as relances

                lst = relances.a_relancer(10)
            except Exception:
                lst = []
            if lst:
                names = ", ".join(o.get("entreprise", "")[:18] for o, *_ in lst[:5])
                self.root.after(
                    0,
                    lambda: self._log(
                        f"🔔 {len(lst)} candidature(s) à relancer : {names}\n"
                        "   (clic droit sur l'offre → 🔔 Relance)\n"
                    ),
                )

        threading.Thread(target=work, daemon=True).start()

    def _relance_draft(self: "AppTypee", o: Any) -> None:
        """Brouillon de relance (.txt + mailto ouvert) — TU envoies, puis statut → relancé."""
        key = self._oid(o)

        def work() -> None:
            try:
                subprocess.run(
                    [PY, "-m", "jobhunter.programs.follow_ups", "--draft", key],
                    cwd=str(SCRIPTS),
                    capture_output=True,
                    timeout=60,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                self.root.after(
                    0,
                    lambda: self._log(
                        f"📧 brouillon relance ouvert ({o.get('entreprise', '')}) — "
                        "envoie-le puis passe le statut à « relancé ».\n"
                    ),
                )
            except Exception as e:
                err = type(e).__name__
                self.root.after(0, lambda n=err: self._log(f"! relance: {n}\n"))

        threading.Thread(target=work, daemon=True).start()
