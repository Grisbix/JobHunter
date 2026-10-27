"""The guided application in the web window: the desktop's "Candidatures" panel.

Mixed into `Api` (jobhunter.web.api). It runs `apply_runner --selection --pilote` and
talks to it, as app.apply_panel does: the program opens each ticked offer in Chrome,
fills in the form, attaches CV and letter, highlights the send button, then waits. The
user checks and clicks Send IN CHROME, then « J'ai envoyé » in the page. Nothing here
clicks anything, and the page cannot send a command the program does not know
(guided_apply.COMMANDES). The events and their texts are jobhunter.guided_apply's.

Nothing here imports jobhunter.app (tests/test_architecture).
"""

from __future__ import annotations

import json
import subprocess
import threading
import time
from typing import Any

from jobhunter import guided_apply as guidee

ZONES = ("offre", "dossier", "etat", "resultat")


class Seance:
    """One run of the guided application: the program, and what the page shows of it."""

    def __init__(self, n: int, cmd: list[str], cwd: str) -> None:
        """Starts the program without a console window; a thread reads its events."""
        self.n = n
        self.zones = {z: {"texte": "", "ton": "tx"} for z in ZONES}
        self.zones["offre"]["texte"] = "Ouverture de Chrome…"
        self.attente = False  # the program waits for a command
        self.code: int | None = None
        self.envois = 0  # results written to the tracking (confirmed or uncertain)
        self.journal: list[str] = []
        self.proc = subprocess.Popen(  # nosec B603 : our own program, fixed arguments
            cmd,
            cwd=cwd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        threading.Thread(target=self._lire, daemon=True).start()

    def _lire(self) -> None:
        assert self.proc.stdout is not None
        for ligne in self.proc.stdout:
            ev = guidee.lire_evenement(ligne)
            if ev is None:
                if ligne.strip():
                    self.journal = [*self.journal[-199:], ligne.rstrip("\n")]
                continue
            self.evenement(ev)
        self.code = self.proc.wait()
        self.attente = False
        self.zones["etat"] = {"texte": "Programme terminé.", "ton": "mut"}

    def evenement(self, ev: dict[str, Any]) -> None:
        """One event of the program, into the zones the page shows."""
        if ev.get("type") == "attente":
            self.attente = True
            return
        aff = guidee.texte_evenement(ev)
        if aff:
            zone, texte, ton = aff
            self.zones[zone] = {"texte": texte, "ton": ton}
        if ev.get("type") == "resultat" and ev.get("etat") in ("confirmé", "incertain"):
            self.envois += 1

    def envoyer(self, ligne: str) -> bool:
        """Writes one command line to the program; False when it no longer listens."""
        if self.proc.poll() is not None or self.proc.stdin is None:
            return False
        try:
            self.proc.stdin.write(ligne + "\n")
            self.proc.stdin.flush()
        except OSError:
            return False
        return True

    def etat(self) -> dict[str, Any]:
        """What the panel shows: the four zones, whether the buttons are active, the end."""
        return {
            "n": self.n,
            "zones": self.zones,
            "attente": self.attente,
            "fini": self.code is not None,
            "envois": self.envois,
            "journal": self.journal[-6:],
        }


class CandidatureApi:
    """Methods of the guided application, for `window.pywebview.api`."""

    _seance: Seance | None = None

    def _file(self) -> list[Any]:  # provided by Api
        raise NotImplementedError

    def candidature_guidee(self, idents: list[str]) -> dict[str, Any]:
        """Starts the guided application on the ticked offers (one run at a time)."""
        from jobhunter import frozen, root

        if self._seance is not None and self._seance.code is None:
            return {"ok": False, "erreur": "Une candidature guidée est déjà en cours."}
        voulus = {str(i) for i in (idents if isinstance(idents, list) else [])}
        offres = [o for o in self._file() if _oid(o) in voulus]
        if not offres:
            return {"ok": False, "erreur": "Coche d'abord des offres."}
        dossier = root.scripts()
        sel = dossier / "apply_selection.json"
        try:
            sel.write_text(
                json.dumps(guidee.selection(offres), ensure_ascii=False, indent=1),
                encoding="utf-8",
            )
            self._seance = Seance(
                len(offres),
                [
                    frozen.interpreteur(),
                    "-m",
                    "jobhunter.programs.apply_runner",
                    "--selection",
                    str(sel),
                    "--pilote",
                ],
                str(dossier),
            )
        except OSError as e:
            return {"ok": False, "erreur": f"Lancement impossible : {e}"}
        return {"ok": True, "n": len(offres)}

    def candidature_etat(self) -> dict[str, Any] | None:
        """The running (or last) guided application; None when none was started."""
        return self._seance.etat() if self._seance else None

    def candidature_commande(self, cmd: str) -> dict[str, Any]:
        """Passes one of the user's commands on, only while the program waits for one."""
        s = self._seance
        if cmd not in guidee.COMMANDES:
            return {"ok": False, "erreur": f"commande inconnue : {cmd}"}
        if s is None or not s.attente:
            return {"ok": False, "erreur": "Le programme travaille : attends qu'il soit prêt."}
        s.attente = False
        s.zones["etat"] = {
            "texte": "Observation de la page…" if cmd == "envoye" else "…",
            "ton": "mut",
        }
        return {"ok": s.envoyer(cmd)}

    def candidature_arreter(self) -> bool:
        """Stops cleanly: "quitter" (Chrome closes), then ends the program if it lingers."""
        s = self._seance
        if s is None or s.code is not None:
            return False
        s.envoyer("quitter")
        s.attente = False

        def finir() -> None:
            time.sleep(8)
            if s.proc.poll() is None:
                s.proc.terminate()

        threading.Thread(target=finir, daemon=True).start()
        return True

    def _fermer_seance(self) -> None:
        """The window closes: the program gets "quitter" (Chrome closes), never left behind."""
        s = self._seance
        if s is None or s.code is not None:
            return
        s.envoyer("quitter")
        try:
            s.proc.wait(timeout=8)
        except subprocess.TimeoutExpired:
            s.proc.terminate()
            s.proc.wait(timeout=5)


def _oid(o: dict[str, Any]) -> str:
    return f"{(o.get('entreprise') or '').strip()}|{(o.get('poste') or '').strip()}"
