"""A CV given as a PDF, rebuilt as a Word file that can be adapted to each offer.

Part of the first launch. A PDF CV went out as is, identical for every offer
(documents.cv copies it): nothing in it can be moved. Most CVs are PDFs, so most new
users got no adaptation at all.

The rebuilt .docx keeps the text and its order (the name first, as cv_text reads
page 1), the headings, the bold and the bullets, on one simple column. The skills
under their heading become a single line, so that documents.cv.ordonner_competences
can put the ones each posting names first. The layout is plainer than the original:
the owner chooses it in the welcome form, and the PDF stays next to it.
"""

import re
import statistics
from pathlib import Path
from typing import Any

from jobhunter import cv_text as _cv_text

# The same heading as documents.cv._RX_TITRE_COMPETENCES (a test keeps them equal):
# importing documents.cv here would read the profile, which does not exist yet.
RX_COMPETENCES = re.compile(
    r"^\s*(?:comp[ée]tences?(?:\s+techniques)?|skills|technical skills|outils|logiciels"
    r"|tools)\s*:?\s*(.*)$",
    re.I,
)
PUCES = "•●○▪■◦‣–-*·"
# Between skills on one line: "Excel • Python · SQL | Power BI".
_SEPARATEURS = re.compile(r"\s*(?:,|;|\s[•·|▪/–-]\s)\s*")
_FIN_DE_PHRASE = (".", "!", "?", ":", ";")


def _est_puce(texte: str) -> bool:
    return texte[:1] in PUCES and texte[1:2] in (" ", "\t", "")


def _sans_puce(texte: str) -> str:
    return texte[1:].strip() if _est_puce(texte) else texte


# Section headings a CV uses: in a skills list, a short line in capitals ("SQL",
# "SAP") is a skill, unless it is one of these.
RX_SECTION = re.compile(
    r"^\s*(?:profil|profile|summary|r[ée]sum[ée]|[àa] propos|about( me)?|exp[ée]riences?"
    r"( professionnelles?)?|(work )?experience|parcours|formations?|[ée]tudes|education"
    r"|dipl[ôo]mes?|langues?|languages?|certifications?|projets?|projects?|contact"
    r"|coordonn[ée]es|centres? d.int[ée]r[êe]ts?|int[ée]r[êe]ts?|interests|loisirs|hobbies"
    r"|b[ée]n[ée]volat|associatif|engagements?|r[ée]f[ée]rences?|publications?|prix|awards)"
    r"\s*:?\s*$",
    re.I,
)


def _est_titre(ligne: _cv_text.Ligne, corps: float) -> bool:
    """A section heading: larger than the body, or short in bold or capitals."""
    t = ligne.texte
    court = len(t) <= 40 and len(t.split()) <= 5 and not t.endswith(_FIN_DE_PHRASE)
    capitales = t.isupper() and sum(c.isalpha() for c in t) >= 3
    return court and (ligne.taille >= corps * 1.15 or ligne.gras or capitales)


def ligne_marquee(ligne: _cv_text.Ligne, corps: float) -> bool:
    """Set apart by its type, larger than the body or in bold, not only by capitals."""
    return ligne.taille >= corps * 1.15 or ligne.gras


def suite_de(avant: _cv_text.Ligne, ligne: _cv_text.Ligne) -> bool:
    """Is `ligne` the next line of the same paragraph: same column, right below?

    Not the PDF block: an export can write each line as a block of its own. After a
    bullet, the next line starts under the text, a little right of the bullet sign.
    """
    hauteur = avant.bbox[3] - avant.bbox[1]
    ecart = ligne.bbox[1] - avant.bbox[3]
    decalage = ligne.bbox[0] - avant.bbox[0]
    return (
        (abs(decalage) <= 3 or (_est_puce(avant.texte) and 0 < decalage <= 25))
        and -1 <= ecart <= 0.8 * hauteur
        and abs(ligne.taille - avant.taille) < 0.5
    )


def _elements(texte: str) -> list[str]:
    """The skills of one line, or [] when it reads as a sentence, not a list."""
    items = [x.strip() for x in _SEPARATEURS.split(_sans_puce(texte)) if x.strip()]
    return items if items and all(len(x) <= 40 and not x.endswith(".") for x in items) else []


def _nom_probable(texte: str) -> bool:
    """A first line that can be a name: two to four words, no digit, no address."""
    mots = texte.split()
    return 2 <= len(mots) <= 4 and not re.search(r"[\d@/:]", texte)


def blocs(lignes: list[_cv_text.Ligne]) -> list[tuple[str, str]]:
    """The CV as (kind, text) in reading order.

    Kinds: "nom", "poste" (the line under the name: a job title, larger than the
    body), "contact" (the contact details, gathered under them), "titre" (a section
    heading), "gras" (a bold line, often a job and its company), "puce" and "texte".

    Lines of one PDF block that continue a sentence are joined into one paragraph;
    the short lines under a skills heading become one comma-separated line.
    """
    if not lignes:
        return []
    corps = statistics.median(l.taille for l in lignes)
    # The widest line of each column: a wrapped line nearly fills it.
    largeur: dict[int, float] = {}
    for l in lignes:
        x = round(l.bbox[0])
        largeur[x] = max(largeur.get(x, 0.0), l.bbox[2] - l.bbox[0])
    grande = max(l.taille for l in lignes)
    sortie: list[tuple[str, str]] = []
    precedente: _cv_text.Ligne | None = None
    competences: list[str] | None = None

    def fermer_competences() -> None:
        nonlocal competences
        if competences is not None and len(competences) >= 3:
            sortie.append(("texte", ", ".join(competences)))
        elif competences:
            sortie.extend(("puce", c) for c in competences)
        competences = None

    for l in lignes:
        t = l.texte.strip()
        if not sortie and (
            (grande >= corps * 1.3 and l.taille >= grande - 0.5) or _nom_probable(t)
        ):
            sortie.append(("nom", t))
        elif (
            len(sortie) == 1
            and sortie[0][0] == "nom"
            and len(t) <= 60
            and not t.endswith(_FIN_DE_PHRASE)
            and not _COORDONNEE.search(t)
        ):
            sortie.append(("poste", t))
        elif (
            _est_titre(l, corps)
            and not _est_puce(t)
            and (competences is None or RX_SECTION.match(t) or ligne_marquee(l, corps))
        ):
            fermer_competences()
            sortie.append(("titre", t))
            m = RX_COMPETENCES.match(t)
            if m:
                competences = _elements(m.group(1))
        elif competences is not None and _elements(t):
            competences += _elements(t)
        elif _est_puce(t):
            fermer_competences()
            sortie.append(("puce", _sans_puce(t)))
        elif (
            sortie
            and sortie[-1][0] in (("gras",) if l.gras else ("texte", "puce"))
            and precedente is not None
            and suite_de(precedente, l)
            and not _COORDONNEE.search(t)
            and not precedente.texte.endswith(_FIN_DE_PHRASE)
            and (
                t[:1].islower()
                # A full line goes on, even if the next word has a capital ("ESG").
                or precedente.bbox[2] - precedente.bbox[0]
                >= 0.8 * largeur[round(precedente.bbox[0])]
            )
        ):
            sortie[-1] = (sortie[-1][0], f"{sortie[-1][1]} {t}")
        else:
            fermer_competences()
            sortie.append(("gras" if l.gras else "texte", t))
        precedente = l
    fermer_competences()
    return _contact_en_tete(sortie)


_COORDONNEE = re.compile(r"@|\+?\d[\d .]{8,}\d|linkedin\.com|https?://", re.I)
_TITRE_CONTACT = re.compile(r"^\s*(?:contact|coordonn[ée]es|contact details)\s*:?\s*$", re.I)


def _contact_en_tete(blocs_: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """The contact details on one line under the name, wherever the PDF had them.

    A two-column CV keeps them in its sidebar, which reads after the main column: the
    rebuilt CV gave the e-mail at the bottom of the page. Their "Contact" heading goes.
    """
    contact: list[str] = []
    reste: list[tuple[str, str]] = []
    dans_contact = False
    for genre, texte in blocs_:
        if genre == "titre":
            dans_contact = bool(_TITRE_CONTACT.match(texte))
            if dans_contact:
                continue
        if genre in ("texte", "gras", "puce") and (dans_contact or _COORDONNEE.search(texte)):
            contact += [x.strip() for x in re.split(r"\s[·•|]\s", texte) if x.strip()]
            continue
        reste.append((genre, texte))
    if not contact:
        return blocs_
    i = 0
    while i < len(reste) and reste[i][0] in ("nom", "poste"):
        i += 1
    return [*reste[:i], ("contact", " · ".join(contact)), *reste[i:]]


def rattacher(lignes: list[_cv_text.Ligne]) -> list[_cv_text.Ligne]:
    """A short right-aligned line ("Madrid · 2023") joined to the line it faces.

    Dates and places sit at the right edge, on the row of a job title. Read as their
    own lines they fell out of the reading column, at the bottom of the rebuilt CV.
    """
    courtes = [l for l in lignes if len(l.texte) <= 35]
    sortie = list(lignes)
    for l in courtes:
        # Right-aligned: another short line ends at the same place (the next job's dates).
        if sum(abs(c.bbox[2] - l.bbox[2]) <= 2 for c in courtes) < 2:
            continue
        face = [
            m
            for m in sortie
            if m is not l
            and m.bbox[2] + 10 < l.bbox[0]
            and min(m.bbox[3], l.bbox[3]) - max(m.bbox[1], l.bbox[1])
            > 0.5 * (l.bbox[3] - l.bbox[1])
        ]
        if face and l in sortie:
            m = max(face, key=lambda x: x.bbox[2])
            sortie[sortie.index(m)] = m._replace(
                texte=f"{m.texte} · {l.texte}", bbox=(*m.bbox[:2], l.bbox[2], m.bbox[3])
            )
            sortie.remove(l)
    return sortie


def lire(pdf: Path | str) -> list[tuple[str, str]]:
    """The blocks of a PDF CV, every page; ValueError when it is protected."""
    import pymupdf

    with pymupdf.open(str(pdf)) as d:
        if d.needs_pass:
            raise ValueError("PDF protégé par un mot de passe")
        lignes: list[_cv_text.Ligne] = []
        for i, page in enumerate(d):
            ls = rattacher(_cv_text.lignes_pdf(page))
            lignes += _cv_text.ordre_lecture(ls) if i == 0 else ls
    return [(k, _cv_text._propre(t)) for k, t in blocs(lignes)]


def ecrire(contenu: list[tuple[str, str]], sortie: Path | str) -> Path:
    """The blocks as a plain one-column .docx (python-docx's default template)."""
    from docx import Document
    from docx.shared import Cm, Pt, RGBColor

    doc: Any = Document()
    for s in doc.sections:
        s.top_margin = s.bottom_margin = Cm(1.3)
        s.left_margin = s.right_margin = Cm(1.6)
    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(10)
    normal.paragraph_format.space_after = Pt(1)
    normal.paragraph_format.line_spacing = 1.0
    puces = doc.styles["List Bullet"].paragraph_format
    puces.space_after = Pt(0)
    puces.line_spacing = 1.0
    for genre, texte in contenu:
        if genre == "puce":
            p = doc.add_paragraph(texte, style="List Bullet")
            continue
        p = doc.add_paragraph()
        r = p.add_run(texte)
        if genre == "nom":
            r.bold = True
            r.font.size = Pt(20)
            p.paragraph_format.space_after = Pt(0)
        elif genre == "contact":
            r.font.size = Pt(10)
            r.font.color.rgb = RGBColor(0x6F, 0x67, 0x63)
            p.paragraph_format.space_after = Pt(6)
        elif genre == "gras":
            r.bold = True
            p.paragraph_format.space_before = Pt(3)
            p.paragraph_format.keep_with_next = True
        elif genre == "poste":
            r.font.size = Pt(13)
            p.paragraph_format.space_after = Pt(4)
        elif genre == "titre":
            r.bold = True
            r.font.size = Pt(11.5)
            r.font.color.rgb = RGBColor(0x5C, 0x3C, 0x2E)
            p.paragraph_format.space_before = Pt(6)
            p.paragraph_format.keep_with_next = True
    sortie = Path(sortie)
    doc.save(str(sortie))
    return sortie


def pdf_en_docx(pdf: Path | str, sortie: Path | str) -> Path:
    """Rebuilds the PDF CV `pdf` as the .docx `sortie`.

    Raises:
        ValueError: protected PDF, or no text in it (a scan, text turned into curves).
    """
    contenu = lire(pdf)
    if sum(len(t) for _, t in contenu) < 200:
        raise ValueError("presque aucun texte dans ce PDF")
    return ecrire(contenu, sortie)
