"""Is an offer's folder ready to go? Check of the FINAL files.

The CV and the letter have been generated; this module looks at what will really be
sent: the PDFs referenced by the offer. A folder is "ready" only if no problem is found:

- each document exists, opens and contains text (a PDF without text is often an
  image, which the ATS read badly);
- the CV fits on ONE page, and so does the letter;
- the profile's contact details are in it: name, email, phone;
- no template was left unfilled ("[nom du poste]", "{entreprise}", "XXX"…).

What it does NOT check: the accuracy of the sentences. The facts of the automatic CV
come from the validated bank (CV/Faits.json); a tailor-made text stays the
responsibility of its author.
"""

import re
import unicodedata
from pathlib import Path
from typing import Any

from jobhunter import links as liens
from jobhunter import profile as _profil

PIECES = (("cv", "CV"), ("lettre", "lettre"))

# Unfilled templates: brackets in capitals or "nom du poste", format braces,
# draft markers. Case-sensitive, except "nom du poste" and "lorem ipsum":
# with re.I on the whole pattern, "brackets in capitals" took any text
# between brackets — including the UN title "Green Finance Analyst [Open to internal and external
# applicants]", wrongly reported as a forgotten template (seen on 19/10/2026).
_RX_GABARIT = re.compile(
    r"\[(?i:nom du poste)\]|\[[A-ZÉÈ][A-ZÉÈ _'-]{2,}\]|\{[a-z_]{3,}\}|<(?:DATE|NOM|POSTE)>"
    r"|\bXXX+\b|(?i:lorem ipsum)"
)


def _plat(texte: str) -> str:
    """Lower case, without accents or multiple spaces: to search for a name or an email."""
    t = unicodedata.normalize("NFKD", texte).encode("ascii", "ignore").decode().lower()
    return " ".join(t.split())


def piece_finale(chemin: Path | None) -> Path | None:
    """The document that will really be sent: the PDF derived from a .docx, if it exists and is up to date.

    22 offers pointed to the .docx letter while its PDF existed next to it: the
    application program would have attached the .docx. The PDF is only preferred if
    it is not older than the .docx (otherwise it does not reflect the last edit).

    Args:
        chemin: the file referenced by the offer, or None.

    Returns:
        The up-to-date PDF if it exists, otherwise `chemin` as is.
    """
    if chemin is None or chemin.suffix.lower() != ".docx":
        return chemin
    pdf = chemin.with_suffix(".pdf")
    try:
        if pdf.exists() and pdf.stat().st_mtime >= chemin.stat().st_mtime:
            return pdf
    except OSError:
        pass
    return chemin


def lire_pdf(chemin: Path) -> tuple[str, int] | None:
    """(text, number of pages) of a PDF, or None if it does not open."""
    try:
        import pymupdf as fitz

        with fitz.open(str(chemin)) as doc:
            texte = "\n".join(page.get_text() for page in doc)
            return texte, int(doc.page_count)
    except Exception:
        return None


def controler_piece(chemin: Path | None, nom: str, identite: dict[str, str]) -> list[str]:
    """Problems of one document of the folder (empty = nothing to object to).

    Args:
        chemin: the file referenced by the offer, or None.
        nom: "CV" or "lettre", for the messages.
        identite: the profile's contact details (`profil.identite()`).

    Returns:
        The problems, in short sentences.
    """
    if chemin is None:
        return [f"{nom} absent"]
    if not chemin.exists():
        return [f"{nom} introuvable : {chemin.name}"]
    if chemin.suffix.lower() != ".pdf":
        if chemin.with_suffix(".pdf").exists():
            return [
                f"{nom} : le PDF est plus ancien que le .docx ({chemin.name}) — relancer sync_docs"
            ]
        return [f"{nom} n'est pas un PDF : {chemin.name}"]
    lu = lire_pdf(chemin)
    if lu is None:
        return [f"{nom} illisible (PDF abîmé)"]
    texte, pages = lu
    problemes = []
    if len(texte.strip()) < 200:
        return [f"{nom} sans texte lisible (image ?)"]
    if pages > 1:
        problemes.append(f"{nom} de {pages} pages")
    plat = _plat(texte)
    chiffres = re.sub(r"\D", "", texte)
    nom_candidat = _plat(identite.get("nom", ""))
    if nom_candidat and nom_candidat != "candidat" and nom_candidat not in plat:
        problemes.append(f"{nom} : nom du candidat absent")
    email = (identite.get("email") or "").strip().lower()
    if email and email not in plat.replace(" ", ""):
        problemes.append(f"{nom} : courriel absent")
    tel = re.sub(r"\D", "", identite.get("tel") or "")[-9:]
    if len(tel) == 9 and tel not in chiffres:
        problemes.append(f"{nom} : téléphone absent")
    gabarit = _RX_GABARIT.search(texte)
    if gabarit:
        problemes.append(f"{nom} : gabarit non rempli « {gabarit.group(0)} »")
    return problemes


def controler_dossier(offre: Any, identite: dict[str, str] | None = None) -> list[str]:
    """Problems of an offer's folder: CV and letter. Empty = folder ready.

    Args:
        offre: the offer (`cv` and `lettre` fields: file:/// links or paths).
        identite: the contact details; None = the profile's.

    Returns:
        The problems of the two documents, in short sentences.
    """
    ident = identite if identite is not None else _profil.identite()
    problemes: list[str] = []
    for cle, nom in PIECES:
        problemes += controler_piece(piece_finale(liens.chemin_de(offre.get(cle))), nom, ident)
    return problemes
