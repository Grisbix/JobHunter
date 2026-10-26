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
"""

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


def texte_fichier(chemin: Path | str) -> str:
    """The text of a .docx or .pdf CV; ValueError for another format."""
    p = Path(chemin)
    suffixe = p.suffix.lower()
    if suffixe == ".pdf":
        import pymupdf as fitz

        with fitz.open(str(p)) as d:
            return "\n".join(page.get_text() for page in d)
    if suffixe == ".docx":
        from docx import Document

        return texte_docx(Document(str(p)))
    raise ValueError(f"format non pris en charge : {p.suffix} (PDF ou DOCX)")
