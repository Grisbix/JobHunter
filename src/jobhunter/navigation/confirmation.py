"""Après « j'ai envoyé » : la page dit-elle que la candidature est arrivée ?

Partie de jobhunter.navigation. Le programme ne clique JAMAIS le bouton d'envoi : c'est
l'utilisateur qui le fait, puis qui le déclare. Ce module regarde seulement ce que la page
affiche ensuite, et rend l'un des deux états de la preuve :

confirmé    la page montre un message de confirmation (« Merci pour votre candidature »,
            « Application submitted », « Vielen Dank für Ihre Bewerbung »…) ou une adresse
            de confirmation (/thank-you, /confirmation), ET le formulaire n'est plus là ;
incertain   tout le reste : formulaire toujours affiché, message d'erreur, page muette.

Une déclaration seule — un clic, une touche — ne vaut jamais « confirmé » : il faut un
signal observé. Et « incertain » ne relance jamais rien ; c'est à l'utilisateur de
vérifier (voir sa boîte mail, le site).

Decision : docs/adr/0009-preuve-distincte-de-la-declaration.md
"""

import re
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

CONFIRME = "confirmé"
INCERTAIN = "incertain"

# Messages de confirmation. Volontairement des PHRASES, pas des mots seuls : « merci »
# ou « candidature » figurent sur presque tous les formulaires avant l'envoi.
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
# Une adresse de confirmation (le chemin, pas le domaine ni la requête).
_RX_URL = re.compile(
    r"/(?:[^/?#]*[-_/])?(?:confirmation|confirmed|thank[-_]?you|thanks|merci|success|submitted|"
    r"application[-_]?sent|bestaetigung|danke)(?:[-_/.]|$)",
    re.I,
)
# Un message d'erreur de formulaire : l'envoi n'est pas passé.
_RX_ERREUR = re.compile(
    r"champ (?:est )?obligatoire|ce champ est requis|this field is required|required field"
    r"|veuillez (?:corriger|renseigner|remplir|compléter)|please (?:correct|fill|complete|enter)"
    r"|une erreur (?:s'est produite|est survenue)|an error (?:has )?occurred|something went wrong"
    r"|pflichtfeld|bitte füllen sie",
    re.I,
)

# Le formulaire est-il encore là ? Un bouton d'envoi final VISIBLE, ou des champs à
# remplir visibles en nombre, disent que l'utilisateur est toujours devant le formulaire.
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
    """Décide l'état de la preuve à partir de ce que la page montre.

    Args:
        texte: le texte visible de la page (et de ses cadres).
        url: l'adresse de la page.
        formulaire_visible: un bouton d'envoi final ou des champs à remplir sont encore là.

    Returns:
        (état, extrait) : l'état (`CONFIRME` ou `INCERTAIN`) et le passage qui le justifie,
        ou la raison de l'incertitude.
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
    chemin = urlsplit(url or "").path  # ni le domaine, ni la requete
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
    """Regarde la page après la déclaration d'envoi, jusqu'à `attente` secondes.

    Une page de confirmation met souvent une ou deux secondes à venir : on relit tant que
    l'état est incertain. Rien n'est cliqué, rien n'est saisi.

    Args:
        page: la page Playwright où l'utilisateur vient d'envoyer.
        attente: durée maximale d'observation, en secondes.
        pas: intervalle entre deux lectures.

    Returns:
        {"etat", "texte", "url"} : l'état de la preuve, l'extrait qui la justifie, l'adresse.
    """
    fin = time.monotonic() + attente
    while True:
        texte, url, formulaire = _lire(page)
        etat, extrait = analyser_confirmation(texte, url, formulaire)
        if etat == CONFIRME or time.monotonic() >= fin:
            return {"etat": etat, "texte": extrait, "url": url}
        time.sleep(pas)


def capturer_preuve(page: Any, chemin: Path) -> str | None:
    """Capture de la page entière, gardée comme justificatif. None si impossible."""
    try:
        chemin.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(chemin), full_page=True, timeout=15000)
        return str(chemin)
    except Exception:
        return None
