"""The text of a CV file, .docx or .pdf, as complete as the file holds it.

python-docx's `paragraphs` and `tables` only see the top level of the body. CV
templates put their text elsewhere, and the profile built from them came out empty
(measured on 2026-10-26 with fictitious CVs: 0 characters read, "not a CV"):

- floating text boxes (Canva exports, Word "design" templates): `w:txbxContent`;
- block content controls (Microsoft's resume templates): `w:sdt`;
- a table inside a table cell;
- the page header, where many put their name and contact details.

Here every paragraph of the body, at any depth, is read in document order, after the
headers and before the footers. Word stores a text box twice (`mc:Choice`, the
DrawingML version, and `mc:Fallback`, the VML one): the fallback is skipped.

PDF, the format most CVs are sent in (measured the same day on fictitious PDFs):

- ligatures ("ﬁ", "ﬂ" in Canva, InDesign or LaTeX exports) came out as one character,
  so "ﬁnance" matched no keyword: they are expanded, and the text NFKC-normalised;
- a two-column design (Canva) streams its sidebar first: contacts and skills came
  before the name, and a two-word skill could be taken for it. On the first page the
  largest text (the name) now comes first, then its column top to bottom, then the rest;
- a PDF without text (a scan, or text turned into curves) or protected by a password
  is told apart, so the form can say what to do (`pourquoi_peu_de_texte`).
"""

import re
import statistics
import unicodedata
from pathlib import Path
from typing import Any

FORMATS = (".docx", ".pdf")
_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
_REPLI = "{http://schemas.openxmlformats.org/markup-compatibility/2006}Fallback"


def _paragraphes(racine: Any) -> list[str]:
    """The text of every paragraph under `racine` (an lxml element), in document order."""
    lignes = []
    for p in racine.iter(f"{_W}p"):
        if any(a.tag == _REPLI for a in p.iterancestors()):
            continue
        morceaux = []
        for e in p.iter(f"{_W}t", f"{_W}tab", f"{_W}br"):
            # Only this paragraph's own runs: a text box anchored in it has its own.
            if next(e.iterancestors(f"{_W}p"), None) is not p:
                continue
            morceaux.append(
                e.text or "" if e.tag == f"{_W}t" else "\t" if e.tag == f"{_W}tab" else "\n"
            )
        lignes.append("".join(morceaux))
    return lignes


def _entetes_pieds(document: Any, pieds: bool) -> list[str]:
    """The text of the headers (or footers) that exist, each once."""
    lignes: list[str] = []
    vus = set()
    for s in document.sections:
        if pieds:
            zones = (s.first_page_footer, s.footer, s.even_page_footer)
        else:
            zones = (s.first_page_header, s.header, s.even_page_header)
        for z in zones:
            # Checked first: reading a missing header's element would create one.
            if z.is_linked_to_previous or z.part.partname in vus:
                continue
            vus.add(z.part.partname)
            lignes += _paragraphes(z._element)
    return lignes


def texte_docx(document: Any) -> str:
    """The whole text of an open python-docx Document, one line per paragraph."""
    lignes = (
        _entetes_pieds(document, pieds=False)
        + _paragraphes(document.element.body)
        + _entetes_pieds(document, pieds=True)
    )
    return "\n".join(lignes)


# ── PDF ───────────────────────────────────────────────────────────────────────
# Characters a PDF font without a Unicode map produces, and invisible ones.
_PARASITES = re.compile("[\ufffd\u00ad\u200b-\u200d\ufeff\ue000-\uf8ff]")


def _propre(texte: str) -> str:
    return _PARASITES.sub("", unicodedata.normalize("NFKC", texte))


def _drapeaux() -> int:
    import pymupdf

    # The default flags keep ligatures: "ﬁnance" would be one glyph, not "fi".
    return int(pymupdf.TEXTFLAGS_TEXT) & ~int(pymupdf.TEXT_PRESERVE_LIGATURES)


def _premiere_page(page: Any) -> str:
    """Page 1 with the name first: the largest text, then its column, then the rest."""
    lignes = []
    for bloc in page.get_text("dict", flags=_drapeaux())["blocks"]:
        for ligne in bloc.get("lines", ()):
            spans = [s for s in ligne["spans"] if s["text"].strip()]
            if spans:
                texte = "".join(s["text"] for s in ligne["spans"]).strip()
                lignes.append((max(s["size"] for s in spans), ligne["bbox"], texte))
    if len(lignes) < 3:
        return "\n".join(texte for _, _, texte in lignes)
    tailles = [taille for taille, _, _ in lignes]
    grande = max(tailles)
    if grande < 1.3 * statistics.median(tailles):  # no title stands out: as streamed
        return "\n".join(texte for _, _, texte in lignes)
    nom = [l for l in lignes if l[0] >= grande - 0.5][:3]
    x0 = min(l[1][0] for l in nom)
    x1 = max(l[1][2] for l in nom)
    autres = [l for l in lignes if l not in nom]
    colonne = sorted(
        (l for l in autres if l[1][0] < x1 and l[1][2] > x0),
        key=lambda l: (round(l[1][1]), l[1][0]),
    )
    reste = [l for l in autres if l not in colonne]
    return "\n".join(texte for _, _, texte in nom + colonne + reste)


def texte_pdf(document: Any) -> str:
    """The whole text of an open PyMuPDF document; ValueError when it is protected."""
    if document.needs_pass:
        raise ValueError("PDF protégé par un mot de passe")
    pages = [
        _premiere_page(page) if i == 0 else page.get_text("text", flags=_drapeaux())
        for i, page in enumerate(document)
    ]
    return _propre("\n".join(pages))


def pourquoi_peu_de_texte(chemin: Path | str) -> str:
    """Why a CV gave almost no text, as advice for its owner ("" when nothing is known)."""
    p = Path(chemin)
    if p.suffix.lower() != ".pdf":
        return ""
    import pymupdf

    try:
        with pymupdf.open(str(p)) as d:
            if d.needs_pass:
                return "Ce PDF est protégé par un mot de passe : enregistre-le sans protection."
            page = d[0]
            if len(page.get_drawings()) > 40:
                return (
                    "Ce PDF contient ton texte sous forme de dessins (texte vectorisé, export "
                    "« aplati ») : JobHunter ne peut pas le lire. Réexporte-le en PDF standard "
                    "(Canva : « PDF Standard » ; Word : Enregistrer sous → PDF), ou donne le .docx."
                )
            if page.get_images():
                return (
                    "Ce PDF est une image (scan, photo ou export en image) : JobHunter ne peut "
                    "pas en lire le texte. Exporte ton CV en PDF depuis Word, Canva ou Google "
                    "Docs, ou donne le .docx."
                )
    except Exception:  # a damaged file: the generic advice
        return ""
    return ""


def texte_fichier(chemin: Path | str) -> str:
    """The text of a .docx or .pdf CV; ValueError for another format."""
    p = Path(chemin)
    suffixe = p.suffix.lower()
    if suffixe == ".pdf":
        import pymupdf

        with pymupdf.open(str(p)) as d:
            return texte_pdf(d)
    if suffixe == ".docx":
        from docx import Document

        return texte_docx(Document(str(p)))
    raise ValueError(f"format non pris en charge : {p.suffix} (PDF ou DOCX)")
