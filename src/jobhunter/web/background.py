"""The desktop's background work, in the web window.

Mixed into `Api` (jobhunter.web.api). The classic window ran, unasked, while it was
open (app.data): the missing descriptions fetched in batches then the ATS re-scored,
the docx → pdf sync every 10 minutes, and a scan of the company sites 2 minutes after
start then every 3 hours (4 at most per session, against rate limits). Here one thread
runs them one after the other, so two of them never write the queue at once, and
waits while a task started by a button or a guided application runs.

JOBHUNTER_SANS_FOND=1 turns it off, as on the desktop (visual checks, the installer's
CI). Each program takes the queue's lock itself (code 3 when it is busy).
Nothing here imports jobhunter.app (tests/test_architecture).
"""

from __future__ import annotations

import os
import re
import subprocess
import threading
import time
from collections.abc import Callable
from typing import Any

LOT_DESCRIPTIONS = 8  # batches of 40 descriptions per session at most (the desktop's cap)
SCANS_MAX = 4  # company-site scans per session
PREMIER_SCAN_S = 120
ECART_SCAN_S = 3 * 3600
ECART_SYNC_S = 600


def _lancer(args: list[str], delai: int) -> subprocess.CompletedProcess[str]:
    """One program, without a console window, its output kept; never raises on its code."""
    from jobhunter import frozen, root

    return subprocess.run(  # nosec B603 : our own programs, fixed arguments
        [frozen.interpreteur(), "-m", *args],
        cwd=str(root.scripts()),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=delai,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def descriptions_manquantes() -> int:
    """Offers with a web link but no description: what the batches fetch."""
    from jobhunter.storage import queue

    return sum(
        1
        for o in queue.charger()
        if str(o.get("url") or "").startswith("http") and not (o.get("description") or "").strip()
    )


def _changes_sync(sortie: str) -> tuple[int, int, int]:
    """(pdf made, pdf regenerated, links repaired) read from sync_docs' summary lines."""

    def n(motif: str) -> int:
        m = re.search(motif + r"\s*:\s*(\d+)", sortie)
        return int(m.group(1)) if m else 0

    return n("pdf créés"), n("pdf resynchronisés"), n("liens queue réparés")


class Fond:
    """The background loop: what is due runs, one program at a time."""

    def __init__(self, occupe: Callable[[], bool]) -> None:
        """`occupe`: True while a button's task or a guided application runs."""
        self.occupe = occupe
        self.messages: list[dict[str, Any]] = []
        self.version = 0  # grows when the data may have changed: the page redraws
        self.lots = 0
        self.eues = 0  # descriptions fetched since the last ATS re-scoring
        self.scans = 0
        debut = time.time()
        self.prochain = {
            "descriptions": debut + 2.5,
            "sync": debut + 6,
            "scan": debut + PREMIER_SCAN_S,
        }

    def dire(self, texte: str, change: bool = False) -> None:
        """A message for the page; `change`: the data changed, the page redraws."""
        self.messages = [*self.messages[-49:], {"heure": time.strftime("%H:%M"), "texte": texte}]
        if change:
            self.version += 1

    def demarrer(self) -> None:
        """Starts the loop in a daemon thread (it ends with the window)."""
        threading.Thread(target=self._boucle, daemon=True).start()

    def _boucle(self) -> None:
        while True:
            time.sleep(5)
            if self.occupe():
                continue
            maintenant = time.time()
            for nom in ("descriptions", "sync", "scan"):
                if self.prochain.get(nom, float("inf")) <= maintenant:
                    try:
                        getattr(self, nom)()
                    except Exception as e:  # noqa: BLE001 — background: said, never fatal
                        self.dire(f"! {nom} : {type(e).__name__}")
                    break  # one program per round: the busy check runs again first

    def descriptions(self) -> None:
        """A batch of missing descriptions, then the ATS re-scored; again while it helps."""
        self.prochain.pop("descriptions", None)
        if self.lots >= LOT_DESCRIPTIONS:
            return
        avant = descriptions_manquantes()
        if not avant:
            return
        self.lots += 1
        _lancer(["jobhunter.programs.scrape_desc", "--all", "--limit", "40"], 900)
        reste = descriptions_manquantes()
        eu = avant - reste
        self.eues += eu
        suite = bool(reste and eu > 0 and self.lots < LOT_DESCRIPTIONS)
        # The ATS re-scoring reads the whole queue (a minute for 12 000 offers): once,
        # after the last batch, not after each (the user, 2026-10-28: « je trouve ça
        # lent » — three batches kept a core busy for four minutes after opening).
        if not suite and self.eues:
            _lancer(["jobhunter.programs.rescore_ats"], 300)
            self.eues = 0
        self.dire(f"Descriptions : +{eu} récupérées ({reste} restantes).", change=eu > 0)
        if suite:
            self.prochain["descriptions"] = time.time() + 1.5

    def sync(self) -> None:
        """Modified docx → regenerated pdf, queue links repaired."""
        self.prochain["sync"] = time.time() + ECART_SYNC_S
        # Said only when something changed: the desktop's filter compared the wrong
        # lines and logged the sync every 10 minutes.
        crees, refaits, liens = _changes_sync(
            _lancer(["jobhunter.programs.sync_docs"], 3000).stdout or ""
        )
        if crees or refaits or liens:
            self.dire(
                f"Documents synchronisés : {crees} pdf créés, {refaits} refaits, {liens} liens réparés.",
                change=True,
            )

    def scan(self) -> None:
        """New offers from the followed company sites, then their descriptions."""
        from jobhunter.storage import queue

        self.scans += 1
        self.prochain["scan"] = (
            time.time() + ECART_SCAN_S if self.scans < SCANS_MAX else float("inf")
        )
        avant = len(queue.charger(descriptions=False))
        r = _lancer(["jobhunter.programs.scrape_jobs", "--headless"], 1800)
        neuf = len(queue.charger(descriptions=False)) - avant
        if neuf > 0:
            self.dire(f"Scan des sites d'entreprise : +{neuf} offre(s).", change=True)
            self.prochain["descriptions"] = time.time() + 1.5
        elif r.returncode not in (0, 3):
            self.dire(f"! Scan des sites d'entreprise : code {r.returncode}.")


class FondApi:
    """Methods of the background work, for `window.pywebview.api`."""

    _fond: Fond | None = None

    def _occupe(self) -> bool:
        tache = getattr(self, "_tache", None)
        seance = getattr(self, "_seance", None)
        return bool(
            (tache is not None and tache.code is None)
            or (seance is not None and seance.code is None)
        )

    def demarrer_fond(self) -> None:
        """Starts the loop, unless JOBHUNTER_SANS_FOND is set (called by __main__)."""
        if self._fond is None and not os.environ.get("JOBHUNTER_SANS_FOND"):
            self._fond = Fond(self._occupe)
            self._fond.demarrer()

    def demarrage(self) -> str | None:
        """At start: did the last update really start its version (programs.update)?"""
        try:
            from jobhunter.programs import update

            return update.confirmer_demarrage()
        except Exception:  # noqa: BLE001 — never a reason not to open
            return None

    def fond_etat(self) -> dict[str, Any]:
        """The background's messages and a version that grows when the data changed.

        The version also follows the queue and the tracking files: another program
        writing them (the morning collection, a console tool) redraws the page, as the
        desktop's table followed the queue.
        """
        from jobhunter.storage import applications, queue

        f = self._fond
        fichiers = 0
        for chemin in (queue.CHEMIN, applications.CHEMIN):
            try:
                fichiers += int(chemin.stat().st_mtime)
            except OSError:
                pass
        if f:
            return {"version": f"{f.version}.{fichiers}", "messages": f.messages[-5:]}
        return {"version": f"0.{fichiers}", "messages": []}
