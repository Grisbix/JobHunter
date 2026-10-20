"""After "j'ai envoyé": does the page say the application arrived?

Part of jobhunter.navigation. The program NEVER clicks the send button: it is the user
who does it, then declares it. This module only looks at what the page displays next,
and returns one of the two states of the proof:

confirmé    the page shows a confirmation message ("Merci pour votre candidature",
            "Application submitted", "Vielen Dank für Ihre Bewerbung"…) or a
            confirmation address (/thank-you, /confirmation), AND the form is gone;
incertain   everything else: form still displayed, error message, silent page.

A declaration alone — a click, a key — is never worth "confirmé": an observed signal is
required. And "incertain" never retries anything; it is up to the user to check (their
mailbox, the site).

Decision: docs/adr/0009-proof-distinct-from-declaration.md
"""

import re
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

CONFIRME = "confirmé"
INCERTAIN = "incertain"

# Confirmation messages. Deliberately SENTENCES, not single words: "merci"
# or "candidature" appear on almost every form before the send.
_RX_MERCI = re.compile(
    r"merci (?:beaucoup )?(?:pour|de) (?:votre|ta) candidature"
    r"|(?:votre|ta) candidature (?:a (?:bien )?été|est) (?:bien )?"
    r"(?:envoyée|reçue|transmise|enregistrée|prise en compte)"
    r"|nous avons (?:bien )?reçu (?:votre|ta) candidature"
    r"|candidature (?:bien )?(?:envoyée|reçue|transmise|enregistrée)(?: avec succès)?"
    r"|thank you for (?:your )?(?:applying|application|submitting|your interest and application)"
    r"|thanks for applying"
    r"|(?:your )?application (?:has been |was )?(?:successfully )?(?:submitted|received|sent)"
    r"|we(?:'ve| have) (?:successfully )?received your application"
    r"|vielen dank für ihre bewerbung"
    r"|ihre bewerbung (?:wurde|ist) (?:erfolgreich )?(?:eingegangen|versendet|übermittelt|abgeschickt)",
    re.I,
)
# A confirmation address (the path, not the domain nor the query).
_RX_URL = re.compile(
    r"/(?:[^/?#]*[-_/])?(?:confirmation|confirmed|thank[-_]?you|thanks|merci|success|submitted|"
    r"application[-_]?sent|bestaetigung|danke)(?:[-_/.]|$)",
    re.I,
)
# A form error message: the send did not go through.
_RX_ERREUR = re.compile(
    r"champ (?:est )?obligatoire|ce champ est requis|this field is required|required field"
    r"|veuillez (?:corriger|renseigner|remplir|compléter)|please (?:correct|fill|complete|enter)"
    r"|une erreur (?:s'est produite|est survenue)|an error (?:has )?occurred|something went wrong"
    r"|pflichtfeld|bitte füllen sie",
    re.I,
)

# Is the form still there? A VISIBLE final send button, or fields to
# fill visible in numbers, say the user is still in front of the form.
_FORMULAIRE_JS = r"""
() => {
  const vis = el => { const r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0 && getComputedStyle(el).visibility !== 'hidden'; };
  const FINAL = /(envoyer ma candidature|soumettre|submit application|submit your application|postuler maintenant|confirmer et envoyer|valider (et )?envoyer|finaliser (ma |la )?candidature|envoyer definitivement|bewerbung absenden)/i;
  const boutons = [...document.querySelectorAll('button, input[type=submit], [role=button]')]
    .filter(el => vis(el) && FINAL.test((el.innerText || el.value || '').trim()));
  const champs = [...document.querySelectorAll('input[type=text], input[type=email], input[type=tel], input[type=file], textarea')]
    .filter(vis);
  return {bouton: boutons.length > 0, champs: champs.length};
}
"""


def _extrait(texte: str, debut: int, fin: int, marge: int = 60) -> str:
    return texte[max(0, debut - marge) : fin + marge].strip()


def analyser_confirmation(
    texte: str | None, url: str | None, formulaire_visible: bool
) -> tuple[str, str]:
    """Decides the state of the proof from what the page shows.

    Args:
        texte: the visible text of the page (and of its frames).
        url: the address of the page.
        formulaire_visible: a final send button or fields to fill are still there.

    Returns:
        (state, extract): the state (`CONFIRME` or `INCERTAIN`) and the passage that
        justifies it, or the reason for the uncertainty.
    """
    t = " ".join((texte or "").split())
    if formulaire_visible:
        return INCERTAIN, "le formulaire est toujours affiché"
    erreur = _RX_ERREUR.search(t)
    if erreur:
        return INCERTAIN, "message d'erreur : " + _extrait(t, erreur.start(), erreur.end())
    merci = _RX_MERCI.search(t)
    if merci:
        return CONFIRME, _extrait(t, merci.start(), merci.end())
    chemin = urlsplit(url or "").path  # neither the domain nor the query
    if _RX_URL.search(chemin):
        return CONFIRME, "adresse de confirmation : " + (url or "")
    return INCERTAIN, "aucun message de confirmation sur la page"


def _lire(page: Any) -> tuple[str, str, bool]:
    """Texte visible (page et cadres), adresse, formulaire encore là."""
    morceaux = []
    for cadre in [page.main_frame, *[f for f in page.frames if f is not page.main_frame]]:
        try:
            morceaux.append(cadre.inner_text("body", timeout=2000)[:20000])
        except Exception:
            continue
    formulaire = False
    try:
        r = page.evaluate(_FORMULAIRE_JS)
        formulaire = bool(r.get("bouton")) or int(r.get("champs") or 0) >= 3
    except Exception:
        pass
    return "\n".join(morceaux), str(page.url or ""), formulaire


def observer_confirmation(page: Any, attente: float = 8.0, pas: float = 0.5) -> dict[str, Any]:
    """Watches the page after the send declaration, for up to `attente` seconds.

    A confirmation page often takes one or two seconds to come: we re-read as long as
    the state is uncertain. Nothing is clicked, nothing is typed.

    Args:
        page: the Playwright page where the user has just sent.
        attente: maximum observation time, in seconds.
        pas: interval between two reads.

    Returns:
        {"etat", "texte", "url"}: the state of the proof, the extract that justifies it, the address.
    """
    fin = time.monotonic() + attente
    while True:
        texte, url, formulaire = _lire(page)
        etat, extrait = analyser_confirmation(texte, url, formulaire)
        if etat == CONFIRME or time.monotonic() >= fin:
            return {"etat": etat, "texte": extrait, "url": url}
        time.sleep(pas)


def capturer_preuve(page: Any, chemin: Path) -> str | None:
    """Screenshot of the whole page, kept as evidence. None if impossible."""
    try:
        chemin.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(chemin), full_page=True, timeout=15000)
        return str(chemin)
    except Exception:
        return None
