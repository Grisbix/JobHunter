"""The "Candidatures" panel: apply from the application, without a console.

Part of jobhunter.app (2.2.0). The panel runs `apply_runner --pilote` as a subprocess
and talks to it: the program opens each offer in Chrome, fills in the form, attaches
CV and letter, highlights the send button, then waits. It is the user who checks and
clicks Send IN CHROME, then "J'ai envoyé" here. The program then observes the page and
writes the tracking with the state of the proof.

Events received (one `@JH {json}` line from the program): offre, pret, bloque, attente,
resultat, fin. Commands sent (one line on its input): envoye, saute, reremplir,
rouvrir, quitter. None of them clicks anything.

Decision: docs/adr/0009-proof-distinct-from-declaration.md
"""

import subprocess
import threading
import tkinter as tk
from typing import Any

from jobhunter import guided_apply as _guidee
from jobhunter.app import common as _commun
from jobhunter.app import theme as _theme
from jobhunter.app._app_type import AppTypee
from jobhunter.app.common import PY, SCRIPTS
from jobhunter.app.language import t as _t
from jobhunter.app.theme import (
    ACC,
    ACC_H,
    ACC_TX,
    AMBRE,
    BAD,
    BG,
    BTN,
    BTN_H,
    CB,
    CF,
    CL,
    MUT,
    OK,
    TX,
)
from jobhunter.storage import applications as suivi_io

# The events and their texts are shared with the web window (jobhunter.guided_apply).
PREFIXE = _guidee.PREFIXE
lire_evenement = _guidee.lire_evenement
TONS = {"tx": TX, "acc": ACC, "ok": OK, "ambre": AMBRE, "bad": BAD, "mut": MUT}
RESULTATS = {k: (texte, TONS[ton]) for k, (texte, ton) in _guidee.RESULTATS.items()}


def texte_evenement(ev: dict[str, Any]) -> tuple[str, str, str] | None:
    """(zone, text, colour) to display for an event, or None if it displays nothing."""
    aff = _guidee.texte_evenement(ev)
    if aff is None:
        return None
    zone, texte, ton = aff
    return zone, texte, TONS[ton]


class CandidatureMixin:
    def _candidater(self: "AppTypee", selection: Any, n: Any) -> None:
        """Opens the panel and launches the application program in driven mode."""
        if self._cand_proc is not None and self._cand_proc.poll() is None:
            self._cand_win.lift()
            self._log("Le panneau Candidatures est déjà ouvert.\n")
            return
        win = tk.Toplevel(self.root)
        win.title(f"Candidatures — {n} offre(s)")
        win.geometry("660x340")
        win.configure(bg=BG)
        self._cand_win = win
        carte = CF(win, bg=BG, plat=True)
        carte.pack(fill="both", expand=True, padx=16, pady=14)
        self._cand_lbl = {}
        for zone, police in (("offre", 14), ("dossier", 11), ("etat", 12), ("resultat", 12)):
            lbl = CL(
                carte,
                text="",
                bg=BG,
                fg=TX,
                font=(_theme.FONT_UI, police, "bold" if zone == "offre" else "normal"),
                anchor="w",
                justify="left",
                wraplength=620,
            )
            lbl.pack(fill="x", pady=(0, 10))
            self._cand_lbl[zone] = lbl
        self._cand_lbl["offre"].configure(text=_t("Ouverture de Chrome…"))
        rangee = CF(carte, bg=BG, plat=True)
        rangee.pack(fill="x", side="bottom")
        self._cand_boutons = []
        for texte, cmd, principal in (
            ("J'ai envoyé  (Ctrl+Entrée)", "envoye", True),
            ("Sauter", "saute", False),
            ("Re-remplir", "reremplir", False),
            ("Rouvrir l'offre", "rouvrir", False),
        ):
            b = CB(
                rangee,
                text=texte,
                command=lambda c=cmd: self._cand_commande(c),
                bg=ACC if principal else BTN,
                fg=ACC_TX if principal else TX,
                activebackground=ACC_H if principal else BTN_H,
            )
            b.pack(side="left", padx=(0, 8))
            self._cand_boutons.append(b)
        CB(rangee, text="Arrêter", command=self._cand_arreter, bg=BTN, fg=TX).pack(side="right")
        win.bind("<Control-Return>", lambda e: self._cand_commande("envoye"))
        win.protocol("WM_DELETE_WINDOW", self._cand_arreter)
        self._cand_actif(False)
        try:
            self._cand_proc = subprocess.Popen(
                [
                    PY,
                    "-m",
                    "jobhunter.programs.apply_runner",
                    "--selection",
                    str(selection),
                    "--pilote",
                ],
                cwd=str(SCRIPTS),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except Exception as e:
            self._cand_lbl["etat"].configure(text=f"Lancement impossible : {e}", text_color=BAD)
            return
        threading.Thread(target=self._cand_lire, args=(self._cand_proc,), daemon=True).start()
        self._log(f"📮 Candidatures : {n} offre(s), panneau ouvert. Chrome s'ouvre.\n")

    def _cand_lire(self: "AppTypee", proc: Any) -> None:
        """Reading thread: events to the panel, the rest to the log."""
        for ligne in proc.stdout:
            ev = lire_evenement(ligne)
            self.q.put(("candidature", ev) if ev else ("line", ligne))
        self.q.put(("candidature", {"type": "termine", "code": proc.wait()}))

    def _cand_actif(self: "AppTypee", actif: bool) -> None:
        for b in self._cand_boutons:
            b.configure(state="normal" if actif else "disabled")

    def _cand_commande(self: "AppTypee", cmd: str) -> None:
        """Passes a command on to the program, if it is waiting."""
        proc = self._cand_proc
        if proc is None or proc.poll() is not None or proc.stdin is None:
            return
        if str(self._cand_boutons[0].cget("state")) == "disabled":
            return  # the program is working: the command will wait for the next "attente"
        self._cand_actif(False)
        self._cand_lbl["etat"].configure(
            text="Observation de la page…" if cmd == "envoye" else "…", text_color=MUT
        )
        try:
            proc.stdin.write(cmd + "\n")
            proc.stdin.flush()
        except OSError:
            pass

    def _cand_evenement(self: "AppTypee", ev: dict[str, Any]) -> None:
        """An event of the program, in the interface thread."""
        if not self._cand_lbl:
            return
        t = ev.get("type")
        if t == "attente":
            self._cand_actif(True)
            return
        if t == "termine":
            self._cand_actif(False)
            self._cand_lbl["etat"].configure(text=_t("Programme terminé."), text_color=MUT)
            return
        aff = texte_evenement(ev)
        if aff:
            zone, texte, couleur = aff
            try:
                self._cand_lbl[zone].configure(text=texte, text_color=couleur)
            except tk.TclError:
                return  # panneau ferme entre-temps
        if t == "resultat" and ev.get("etat") in ("confirmé", "incertain"):
            self.suivi = suivi_io.charger(_commun.SUIVI)  # the program has just written it
            self.refresh_table()

    def _cand_arreter(self: "AppTypee") -> None:
        """Stops cleanly: "quitter", then closes the panel; Chrome closes."""
        proc = self._cand_proc
        if proc is not None and proc.poll() is None and proc.stdin is not None:
            try:
                proc.stdin.write("quitter\n")
                proc.stdin.flush()
            except OSError:
                pass
            self.root.after(8000, lambda: proc.poll() is None and proc.terminate())
        try:
            self._cand_win.destroy()
        except Exception:
            pass
        self._cand_lbl = {}
        self._cand_boutons = []
