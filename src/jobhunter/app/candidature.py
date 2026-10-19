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

import json
import subprocess
import threading
import tkinter as tk
from typing import Any

from jobhunter.app import commun as _commun
from jobhunter.app import theme as _theme
from jobhunter.app._type_app import AppTypee
from jobhunter.app.commun import PY, SCRIPTS
from jobhunter.app.langue import t as _t
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
from jobhunter.stockage import suivi as suivi_io

PREFIXE = "@JH "

# What the panel says after each offer, depending on the state of the proof (ADR 0009).
RESULTATS = {
    "confirmé": ("✅ Envoi confirmé par le site.", OK),
    "incertain": (
        "⚠ Envoi enregistré, mais le site ne l'a pas confirmé : vérifie ta boîte mail ou "
        "ton espace candidat. Rien ne sera renvoyé automatiquement.",
        AMBRE,
    ),
    "sauté": ("Offre sautée.", MUT),
    "erreur": ("✗ Le suivi n'a pas pu être écrit : confirme la candidature dans la fiche.", BAD),
}


def lire_evenement(ligne: str) -> dict[str, Any] | None:
    """L'événement d'une ligne `@JH {json}` du programme, ou None (ligne de journal)."""
    if not ligne.startswith(PREFIXE):
        return None
    try:
        ev = json.loads(ligne[len(PREFIXE) :])
    except ValueError:
        return None
    return ev if isinstance(ev, dict) and isinstance(ev.get("type"), str) else None


def texte_evenement(ev: dict[str, Any]) -> tuple[str, str, str] | None:
    """(zone, text, colour) to display for an event, or None if it displays nothing.

    Zones: "offre" (the current offer), "dossier" (CV and letter checked), "etat"
    (what is happening), "resultat" (the outcome of the previous offer).
    """
    t = ev.get("type")
    if t == "offre":
        return (
            "offre",
            f"{ev.get('i')}/{ev.get('total')} · {ev.get('entreprise', '')} — {ev.get('poste', '')}",
            TX,
        )
    if t == "pret":
        details = []
        if ev.get("couverture") is not None:
            details.append(f"{ev['couverture']} % des champs")
        if ev.get("documents"):
            details.append(f"documents : {ev['documents']}")
        bouton = ev.get("bouton") or "le bouton d'envoi"
        texte = "Formulaire prêt" + (f" ({' · '.join(details)})" if details else "") + ". "
        texte += f"Vérifie dans Chrome, clique « {bouton} » toi-même, puis « J'ai envoyé »."
        return "etat", texte, ACC
    if t == "bloque":
        return (
            "etat",
            f"À toi dans Chrome : {ev.get('raison', 'action requise')}. "
            "Le programme ne contourne rien. Puis « Re-remplir ».",
            AMBRE,
        )
    if t == "resultat":
        texte, couleur = RESULTATS.get(str(ev.get("etat")), (str(ev.get("etat")), MUT))
        extrait = str(ev.get("texte") or "")
        if ev.get("etat") in ("confirmé", "incertain") and extrait:
            texte += f"\n« {extrait[:120]} »"
        return "resultat", texte, couleur
    if t == "fin":
        return "etat", "Toutes les offres sont passées. « Arrêter » ferme Chrome.", MUT
    if t == "dossier":
        problemes = [str(p) for p in ev.get("problemes") or []]
        if not problemes:
            return "dossier", "Dossier vérifié : CV et lettre lisibles, une page, coordonnées.", OK
        return (
            "dossier",
            "Dossier à revoir avant d'envoyer : " + " ; ".join(problemes),
            BAD,
        )
    return None


class CandidatureMixin:
    def _candidater(self: "AppTypee", selection: Any, n: Any) -> None:
        """Ouvre le panneau et lance le programme de candidature en mode piloté."""
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
                    "jobhunter.programmes.apply_runner",
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
        """Fil de lecture : événements vers le panneau, le reste vers le journal."""
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
        """Un événement du programme, dans le fil de l'interface."""
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
        """Arrête proprement : « quitter », puis ferme le panneau ; Chrome se ferme."""
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
