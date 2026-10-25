"""Read emails: local export (.mbox, .eml) or the Gmail API, read-only.

Part of jobhunter.mail. Each source returns `Courriel` objects: sender, subject,
date and raw text of the body (HTML reduced to text). Attachments are ignored.

**The Gmail API** requires a "desktop application" OAuth client that the user creates
themselves in their Google Cloud console, and whose file they drop into
`Scripts/gmail_client.json`. On first use, their browser opens on Google's consent page,
where they accept the **gmail.readonly** scope; the token obtained goes into
`Scripts/gmail_token.json`. The program never sees a password and can neither send,
nor modify, nor delete an email. Required library: `google-auth-oauthlib`
(`pip install "jobhunter[gmail]"`).
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
    """A received email, reduced to what serves to propose a status."""

    de: str  # « Nom <adresse> » tel quel
    sujet: str
    le: str  # YYYY-MM-DD; "" if the date is unreadable
    corps: str  # texte brut


def _texte_html(h: str) -> str:
    h = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", h, flags=re.S | re.I)
    h = re.sub(r"<br\s*/?>|</p>|</div>|</li>", "\n", h, flags=re.I)
    return html.unescape(re.sub(r"<[^>]+>", " ", h))


def _corps(m: Message) -> str:
    """The message text: the text/plain part, otherwise the HTML reduced to text."""
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
        except LookupError:  # unknown character set
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
    """The emails of an .mbox file (Google Takeout export, Thunderbird…)."""
    boite = mailbox.mbox(str(chemin), create=False)
    try:
        for m in boite:
            yield depuis_message(m)
    finally:
        boite.close()


def depuis_eml(dossier: Path) -> Iterator[Courriel]:
    """The .eml files of a folder (an email dragged out of the mail client).

    One .eml file given directly is read too: it gave "0 courriel(s) lus" silently.
    """
    for p in [dossier] if dossier.is_file() else sorted(dossier.rglob("*.eml")):
        yield depuis_octets(p.read_bytes())


def depuis_gmail(scripts: Path, jours: int = 60, maximum: int = 500) -> Iterator[Courriel]:
    """The emails received over the last `jours` days, through the Gmail API, read-only.

    Args:
        scripts: the `Scripts/` folder (OAuth client and token).
        jours: maximum age.
        maximum: maximum number of emails read.

    Raises:
        FileNotFoundError: no `gmail_client.json` (see the module header).
        ImportError: `google-auth-oauthlib` missing.
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
        # The user's browser opens on Google's page: it is the user who
        # consents, to reading only.
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
