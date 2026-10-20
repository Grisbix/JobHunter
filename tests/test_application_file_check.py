"""Check of the final file (documents.controle): what will really be sent.

PDFs made on the fly (PyMuPDF): a good file, then each defect alone.
"""

import fitz
import pytest

from jobhunter.documents import checks as controle

IDENT = {"nom": "Camille Exemple", "email": "camille@example.com", "tel": "+33 6 12 34 56 78"}
CORPS = (
    "Camille Exemple\ncamille@example.com · 06 12 34 56 78\n"
    "Analyste ESG junior. Modèles de valorisation, analyse extra-financière, SFDR, CSRD. " * 3
)


def pdf(chemin, *pages):
    doc = fitz.open()
    for texte in pages:
        page = doc.new_page()
        page.insert_textbox(fitz.Rect(40, 40, 560, 800), texte, fontsize=9)
    doc.save(str(chemin))
    doc.close()
    return chemin


def test_bon_dossier(tmp_path):
    offre = {
        "cv": (pdf(tmp_path / "cv.pdf", CORPS)).as_uri(),
        "lettre": str(pdf(tmp_path / "lettre.pdf", CORPS)),
    }
    assert controle.controler_dossier(offre, IDENT) == []


@pytest.mark.parametrize(
    ("pages", "attendu"),
    [
        ((CORPS, CORPS), "CV de 2 pages"),
        ((CORPS.replace("camille@example.com", "autre@example.com"),), "CV : courriel absent"),
        ((CORPS.replace("06 12 34 56 78", "01 00 00 00 00"),), "CV : téléphone absent"),
        ((CORPS.replace("Camille Exemple", "Dominique"),), "CV : nom du candidat absent"),
        (
            (CORPS + "\nCandidature au poste de [nom du poste]",),
            "CV : gabarit non rempli « [nom du poste] »",
        ),
        ((CORPS + "\nChez {entreprise}",), "CV : gabarit non rempli « {entreprise} »"),
        (("Camille",), "CV sans texte lisible (image ?)"),
    ],
    ids=["2 pages", "courriel", "telephone", "nom", "crochets", "accolades", "sans texte"],
)
def test_un_defaut_a_la_fois(tmp_path, pages, attendu):
    chemin = pdf(tmp_path / "cv.pdf", *pages)
    assert controle.controler_piece(chemin, "CV", IDENT) == [attendu]


def test_accents_et_casse_du_nom(tmp_path):
    ident = dict(IDENT, nom="Hélène Élise")
    chemin = pdf(tmp_path / "cv.pdf", CORPS.replace("Camille Exemple", "HELENE ELISE"))
    assert controle.controler_piece(chemin, "CV", ident) == []


def test_pieces_absentes_ou_cassees(tmp_path):
    abime = tmp_path / "abime.pdf"
    abime.write_bytes(b"%PDF-1.4 pas vraiment un pdf")
    docx = tmp_path / "lettre.docx"
    docx.write_bytes(b"PK")
    assert controle.controler_piece(None, "CV", IDENT) == ["CV absent"]
    assert controle.controler_piece(tmp_path / "x.pdf", "CV", IDENT) == ["CV introuvable : x.pdf"]
    assert controle.controler_piece(abime, "CV", IDENT) == ["CV illisible (PDF abîmé)"]
    assert controle.controler_piece(docx, "lettre", IDENT) == [
        "lettre n'est pas un PDF : lettre.docx"
    ]


def test_dossier_sans_lettre(tmp_path):
    offre = {"cv": str(pdf(tmp_path / "cv.pdf", CORPS)), "lettre": None}
    assert controle.controler_dossier(offre, IDENT) == ["lettre absent"]


# ── the document actually sent: the up-to-date PDF rather than its .docx ─────────────
def test_pdf_a_jour_prefere_au_docx(tmp_path):
    import os

    docx = tmp_path / "lettre.docx"
    docx.write_bytes(b"PK")
    pdf(tmp_path / "lettre.pdf", CORPS)
    os.utime(docx, (1_000_000, 1_000_000))  # the .docx is older than its PDF
    assert controle.piece_finale(docx) == tmp_path / "lettre.pdf"
    assert controle.controler_dossier({"cv": None, "lettre": str(docx)}, IDENT) == ["CV absent"]


def test_pdf_perime_signale(tmp_path):
    import os

    docx = tmp_path / "lettre.docx"
    pdf(tmp_path / "lettre.pdf", CORPS)
    docx.write_bytes(b"PK")
    os.utime(tmp_path / "lettre.pdf", (1_000_000, 1_000_000))  # .docx retouched after the PDF
    assert controle.piece_finale(docx) == docx
    assert "relancer sync_docs" in controle.controler_piece(docx, "lettre", IDENT)[0]
