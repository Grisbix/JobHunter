"""Lire des courriels : export local (.mbox, .eml) ou API Gmail en lecture seule.

Partie de jobhunter.courriels. Chaque source rend des `Courriel` : expéditeur, sujet,
date et texte brut du corps (HTML réduit au texte). Les pièces jointes sont ignorées.

**L'API Gmail** demande un client OAuth « application de bureau » que l'utilisateur crée
lui-même dans sa console Google Cloud, et dont il dépose le fichier dans
`Scripts/gmail_client.json`. Au premier usage, son navigateur s'ouvre sur la page de
consentement de Google, où il accepte la portée **gmail.readonly** ; le jeton obtenu va
dans `Scripts/gmail_token.json`. Le programme ne voit jamais de mot de passe et ne peut
ni envoyer, ni modifier, ni supprimer un courriel. Bibliothèque requise :
`google-auth-oauthlib` (`pip install "jobhunter[gmail]"`).
"""

import base64
import email
import email.policy
import email.utils
import html
import mailbox
import re
from collections.abc import Iterator
from dataclasses import dataclass
from email.message import Message
from pathlib import Path

PORTEE = "https://www.googleapis.com/auth/gmail.readonly"
CLIENT = "gmail_client.json"
JETON = "gmail_token.json"
_LIMITE_CORPS = 20000


@dataclass(frozen=True)
class Courriel:
    """Un courriel reçu, réduit à ce qui sert à proposer un statut."""

    de: str  # « Nom <adresse> » tel quel
    sujet: str
    le: str  # AAAA-MM-JJ ; "" si la date est illisible
    corps: str  # texte brut


def _texte_html(h: str) -> str:
    h = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", h, flags=re.S | re.I)
    h = re.sub(r"<br\s*/?>|</p>|</div>|</li>", "\n", h, flags=re.I)
    return html.unescape(re.sub(r"<[^>]+>", " ", h))


def _corps(m: Message) -> str:
    """Le texte du message : la partie text/plain, sinon le HTML réduit au texte."""
    simple: list[str] = []
    riche: list[str] = []
    for partie in m.walk() if m.is_multipart() else [m]:
        if partie.get_content_disposition() == "attachment":
            continue
        type_ = partie.get_content_type()
        if type_ not in ("text/plain", "text/html"):
            continue
        octets = partie.get_payload(decode=True)
        if not isinstance(octets, bytes):
            continue
        try:
            texte = octets.decode(partie.get_content_charset() or "utf-8", "replace")
        except LookupError:  # jeu de caractères inconnu
            texte = octets.decode("utf-8", "replace")
        (simple if type_ == "text/plain" else riche).append(texte)
    texte = "\n".join(simple) if simple else _texte_html("\n".join(riche))
    return " ".join(texte.split())[:_LIMITE_CORPS]


def _date(valeur: str | None) -> str:
    try:
        d = email.utils.parsedate_to_datetime(valeur or "")
    except (TypeError, ValueError, IndexError):
        return ""
    return d.date().isoformat() if d else ""


def depuis_message(m: Message) -> Courriel:
    """Un message `email` → `Courriel`."""
    return Courriel(
        de=str(m.get("From") or ""),
        sujet=" ".join(str(m.get("Subject") or "").split()),
        le=_date(m.get("Date")),
        corps=_corps(m),
    )


def depuis_octets(brut: bytes) -> Courriel:
    """Un courriel brut (RFC 5322) → `Courriel`."""
    return depuis_message(email.message_from_bytes(brut, policy=email.policy.default))


def depuis_mbox(chemin: Path) -> Iterator[Courriel]:
    """Les courriels d'un fichier .mbox (export Google Takeout, Thunderbird…)."""
    boite = mailbox.mbox(str(chemin), create=False)
    try:
        for m in boite:
            yield depuis_message(m)
    finally:
        boite.close()


def depuis_eml(dossier: Path) -> Iterator[Courriel]:
    """Les fichiers .eml d'un dossier (un courriel glissé hors du client de messagerie)."""
    for p in sorted(dossier.rglob("*.eml")):
        yield depuis_octets(p.read_bytes())


def depuis_gmail(scripts: Path, jours: int = 60, maximum: int = 500) -> Iterator[Courriel]:
    """Les courriels reçus ces `jours` derniers, par l'API Gmail en lecture seule.

    Args:
        scripts: le dossier `Scripts/` (client OAuth et jeton).
        jours: ancienneté maximale.
        maximum: nombre maximal de courriels lus.

    Raises:
        FileNotFoundError: pas de `gmail_client.json` (voir l'en-tête du module).
        ImportError: `google-auth-oauthlib` absent.
    """
    client = scripts / CLIENT
    if not client.exists():
        raise FileNotFoundError(
            f"{client} absent : crée un client OAuth « application de bureau » dans ta "
            "console Google Cloud (API Gmail activée) et dépose son fichier ici."
        )
    from google.auth.transport.requests import AuthorizedSession, Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    jeton = scripts / JETON
    cred = Credentials.from_authorized_user_file(str(jeton), [PORTEE]) if jeton.exists() else None
    if cred and cred.expired and cred.refresh_token:
        cred.refresh(Request())
    if not cred or not cred.valid:
        # Le navigateur de l'utilisateur s'ouvre sur la page de Google : c'est lui qui
        # consent, à la seule lecture.
        cred = InstalledAppFlow.from_client_secrets_file(str(client), [PORTEE]).run_local_server(
            port=0
        )
    if set(cred.scopes or []) - {PORTEE}:
        raise PermissionError("le jeton porte d'autres droits que la lecture seule : refusé")
    jeton.write_text(cred.to_json(), encoding="utf-8")
    s = AuthorizedSession(cred)
    base = "https://gmail.googleapis.com/gmail/v1/users/me/messages"
    page, lus = None, 0
    while lus < maximum:
        params = {"q": f"newer_than:{int(jours)}d -in:sent", "maxResults": "100"}
        if page:
            params["pageToken"] = page
        r = s.get(base, params=params, timeout=30)
        r.raise_for_status()
        donnees = r.json()
        for ref in donnees.get("messages", []):
            if lus >= maximum:
                break
            m = s.get(f"{base}/{ref['id']}", params={"format": "raw"}, timeout=30)
            m.raise_for_status()
            yield depuis_octets(base64.urlsafe_b64decode(m.json()["raw"]))
            lus += 1
        page = donnees.get("nextPageToken")
        if not page:
            break
