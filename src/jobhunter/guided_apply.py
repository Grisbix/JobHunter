"""The guided application, shared by both windows: the program's events, in words.

`apply_runner --pilote` opens each offer in Chrome, fills in the form, attaches CV and
letter, highlights the send button, then waits. The user checks and clicks Send IN
CHROME, then "J'ai envoyé" in the application. The program then observes the page and
writes the tracking with the state of the proof. Nothing here clicks anything.

Events received (one `@JH {json}` line from the program): offre, dossier, pret, bloque,
attente, resultat, fin. Commands sent (one line on its input): envoye, saute,
reremplir, rouvrir, quitter.

The texts carry a tone ("tx", "acc", "ok", "ambre", "bad", "mut"); each window gives
it its own colour. Decision: docs/adr/0009-proof-distinct-from-declaration.md
"""

from __future__ import annotations

import json
from typing import Any

PREFIXE = "@JH "

# The commands the user may send while the program waits; "quitter" stops it.
COMMANDES = ("envoye", "saute", "reremplir", "rouvrir")

# What the panel says after each offer, depending on the state of the proof (ADR 0009).
RESULTATS = {
    "confirmé": ("✅ Envoi confirmé par le site.", "ok"),
    "incertain": (
        "⚠ Envoi enregistré, mais le site ne l'a pas confirmé : vérifie ta boîte mail ou "
        "ton espace candidat. Rien ne sera renvoyé automatiquement.",
        "ambre",
    ),
    "sauté": ("Offre sautée.", "mut"),
    "erreur": ("✗ Le suivi n'a pas pu être écrit : confirme la candidature dans la fiche.", "bad"),
}


def lire_evenement(ligne: str) -> dict[str, Any] | None:
    """The event of a program line `@JH {json}`, or None (log line)."""
    if not ligne.startswith(PREFIXE):
        return None
    try:
        ev = json.loads(ligne[len(PREFIXE) :])
    except ValueError:
        return None
    return ev if isinstance(ev, dict) and isinstance(ev.get("type"), str) else None


def texte_evenement(ev: dict[str, Any]) -> tuple[str, str, str] | None:
    """(zone, text, tone) to display for an event, or None if it displays nothing.

    Zones: "offre" (the current offer), "dossier" (CV and letter checked), "etat"
    (what is happening), "resultat" (the outcome of the previous offer).
    """
    t = ev.get("type")
    if t == "offre":
        return (
            "offre",
            f"{ev.get('i')}/{ev.get('total')} · {ev.get('entreprise', '')} — {ev.get('poste', '')}",
            "tx",
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
        return "etat", texte, "acc"
    if t == "bloque":
        return (
            "etat",
            f"À toi dans Chrome : {ev.get('raison', 'action requise')}. "
            "Le programme ne contourne rien. Puis « Re-remplir ».",
            "ambre",
        )
    if t == "resultat":
        texte, ton = RESULTATS.get(str(ev.get("etat")), (str(ev.get("etat")), "mut"))
        extrait = str(ev.get("texte") or "")
        if ev.get("etat") in ("confirmé", "incertain") and extrait:
            texte += f"\n« {extrait[:120]} »"
        return "resultat", texte, ton
    if t == "fin":
        return "etat", "Toutes les offres sont passées. « Arrêter » ferme Chrome.", "mut"
    if t == "dossier":
        problemes = [str(p) for p in ev.get("problemes") or []]
        if not problemes:
            return (
                "dossier",
                "Dossier vérifié : CV et lettre lisibles, une page, coordonnées.",
                "ok",
            )
        return (
            "dossier",
            "Dossier à revoir avant d'envoyer : " + " ; ".join(problemes),
            "bad",
        )
    return None


def selection(offres: list[dict[str, Any]]) -> list[dict[str, str]]:
    """What `apply_runner --selection` reads: company and job of each ticked offer."""
    return [{"entreprise": o.get("entreprise", ""), "poste": o.get("poste", "")} for o in offres]
