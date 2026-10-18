"""Donnees de l'app : chargement de la file, enrichissement et synchro en arriere-plan, relances.

Partie de jobhunter.app (ancien JobHunter.pyw, phase 3.7)."""

import datetime
import importlib
import json
import subprocess
import threading
from urllib.parse import urlparse

from jobhunter.app import commun as _commun
from jobhunter.app.commun import LF, PY, QUEUE, SCRAPE_TAG, SCRIPTS
from jobhunter.stockage import file as queue_io


class DonneesMixin:
    # ── données ──
    def _oid(self, o):
        return f"{(o.get('entreprise') or '').strip()}|{(o.get('poste') or '').strip()}"

    def _host(self, o):
        u = o.get("url") or ""
        return urlparse(u).netloc.replace("www.", "").lower() if u.startswith("http") else ""

    def _acct_of(self, o):
        """Compte connu pour ce site ? Match host (exact ou sous-domaine). Retour info|None."""
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

    def load_offers(self):
        # la queue change (scan, suppressions) : le texte cherchable mis en cache
        # decrirait sinon des offres qui n'existent plus
        self._search_cache.clear()
        try:
            self.offers = queue_io.charger(QUEUE)
        except Exception:
            self.offers = []
        try:
            self.suivi = importlib.import_module("jobhunter.stockage.suivi").charger(_commun.SUIVI)
        except Exception:
            self.suivi = {}
        try:
            self.comptes = json.loads(_commun.COMPTES.read_text(encoding="utf-8"))
        except Exception:
            self.comptes = {}
        self.refresh_table()

    def _missing_desc(self):
        """Offres avec URL http mais sans description (à enrichir auto)."""
        return [
            o
            for o in self.offers
            if str(o.get("url") or "").startswith("http")
            and not (o.get("description") or "").strip()
        ]

    def _auto_enrich(self):
        """AUTO (pas de bouton) : récupère en fond les descriptions manquantes par lots,
        puis re-score ATS, recharge, et enchaîne tant qu'il en reste. Headless, silencieux.
        VERROU _bg_busy partagé avec _auto_sync : jamais 2 jobs qui écrivent la queue en même temps."""
        if getattr(self, "_desc_busy", False) or getattr(self, "_bg_busy", False):
            return
        # cap par session : évite de scraper 1300 offres d'un coup (rate-limit/ban)
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

        def work():
            try:
                subprocess.run(
                    [PY, "-m", "jobhunter.programmes.scrape_desc", "--all", "--limit", "40"],
                    cwd=str(SCRIPTS),
                    capture_output=True,
                    text=True,
                    timeout=900,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                subprocess.run(
                    [PY, "-m", "jobhunter.programmes.rescore_ats"],
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

        def done():
            self._desc_busy = False
            self._bg_busy = False
            self.load_offers()  # recharge (descriptions + ATS mis à jour) → table rafraîchie
            rest = len(self._missing_desc())
            got = n - rest
            self._log(
                f"✅ descriptions: +{got} récupérées ({rest} restantes, dont Indeed/anti-bot).\n"
            )
            if rest and got:  # il en reste ET on progresse → lot suivant
                self.root.after(1500, self._auto_enrich)

        threading.Thread(target=work, daemon=True).start()

    def _auto_sync(self):
        """AUTO : sync_docs.py en fond — docx modifiés → pdf régénérés, liens queue réparés.
        Relancé toutes les 10 min tant que l'app tourne."""
        if getattr(self, "_sync_busy", False) or getattr(self, "_bg_busy", False):
            self.root.after(120000, self._auto_sync)
            return  # occupé → réessaie dans 2 min
        self._sync_busy = True
        self._bg_busy = True

        def work():
            try:
                r = subprocess.run(
                    [PY, "-m", "jobhunter.programmes.sync_docs"],
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

            def done():
                self._sync_busy = False
                self._bg_busy = False
                if msg and not msg.startswith("pdf créés: 0 · pdf resynchronisés: 0"):
                    self._log(f"🔁 sync docs : {msg}\n")
                self.root.after(600000, self._auto_sync)  # re-check dans 10 min

            self.root.after(0, done)

        threading.Thread(target=work, daemon=True).start()

    _SCRAPE_COOLDOWN_S = 1800  # 30 min minimum entre deux scans declenches

    def _scrape_cooldown_ok(self):
        last = getattr(self, "_scrape_last", None)
        if last is None:
            return True
        return (datetime.datetime.now() - last).total_seconds() >= self._SCRAPE_COOLDOWN_S

    def _on_focus_scrape(self, e=None):
        """La fenetre reprend le focus : on revient dans l'app, on rafraichit.

        Declenchement par evenement plutot que minuterie : pas de scan pendant
        que l'app est en arriere-plan, et les offres sont fraiches au moment ou
        tu les regardes. Le cooldown evite qu'un alt-tab repete relance un scan.
        """
        if e is not None and getattr(e, "widget", None) is not self.root:
            return
        if self._scrape_cooldown_ok():
            self._auto_scrape()

    def _auto_scrape(self):
        """AUTO : scrape_jobs.py en fond — nouvelles offres des sites entreprises.

        Meme motif que _auto_sync, mais espace de 3 h : un scan trop frequent se
        fait rate-limiter ou bannir. Cap par session comme _auto_enrich.
        VERROU _bg_busy partage : jamais 2 jobs qui ecrivent la file en meme temps.
        """
        if getattr(self, "_scrape_busy", False) or getattr(self, "_bg_busy", False):
            self.root.after(300000, self._auto_scrape)
            return  # occupe -> reessaie dans 5 min
        if self.proc and self.proc.poll() is None:
            self.root.after(300000, self._auto_scrape)
            return  # un bouton tourne -> 5 min
        if getattr(self, "_scrape_runs", 0) >= 4:
            return  # cap : 4 scans par session
        self._scrape_busy = True
        self._bg_busy = True
        self._scrape_last = datetime.datetime.now()
        self._scrape_runs = getattr(self, "_scrape_runs", 0) + 1
        avant = len(getattr(self, "offers", []) or [])

        def work():
            try:
                r = subprocess.run(
                    [PY, "-m", "jobhunter.programmes.scrape_jobs", "--headless"],
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

            def done():
                self._scrape_busy = False
                self._bg_busy = False
                self.load_offers()  # table rafraichie
                neuf = len(getattr(self, "offers", []) or []) - avant
                if neuf > 0:
                    self._log(SCRAPE_TAG + " scan auto : +%d offre(s). %s%s" % (neuf, msg, LF))
                elif msg.startswith("!"):
                    self._log(SCRAPE_TAG + " scan auto : %s%s" % (msg, LF))
                # plus de minuterie : le prochain scan viendra du focus fenetre
                if neuf > 0:
                    self.root.after(1500, self._auto_enrich)  # descriptions des nouvelles

            self.root.after(0, done)

        threading.Thread(target=work, daemon=True).start()

    def _check_relances(self):
        """Signale au démarrage les candidatures « postulé » depuis ≥ 10 j sans réponse."""

        def work():
            try:
                import sys as _s

                if str(SCRIPTS) not in _s.path:
                    _s.path.insert(0, str(SCRIPTS))
                from jobhunter.programmes import relances

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

    def _relance_draft(self, o):
        """Brouillon de relance (.txt + mailto ouvert) — TU envoies, puis statut → relancé."""
        key = self._oid(o)

        def work():
            try:
                subprocess.run(
                    [PY, "-m", "jobhunter.programmes.relances", "--draft", key],
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
