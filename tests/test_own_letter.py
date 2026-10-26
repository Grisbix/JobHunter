"""The background paragraph taken from the candidate's own letter. Fictitious letters."""

import pymupdf
from docx import Document

from jobhunter import own_letter

LETTRE = [
    "Camille Exemple",
    "camille.exemple@example.com · 06 00 00 00 00",
    "Objet : candidature au poste d'analyste ESG",
    "Madame, Monsieur,",
    "Votre société accompagne les investisseurs dans leur transition, et votre équipe "
    "ESG publie des analyses que je lis depuis deux ans : rejoindre votre groupe serait "
    "pour moi une évidence.",
    "Diplômée d'un master en finance durable, j'ai effectué deux stages en analyse ESG, "
    "dont six mois à classer 300 fonds selon SFDR. Cette expérience m'a appris à lire un "
    "reporting extra-financier avec exigence.",
    "Je vous prie d'agréer, Madame, Monsieur, l'expression de mes salutations distinguées.",
]


def test_le_paragraphe_de_parcours_pas_celui_sur_l_entreprise():
    assert own_letter.parcours(LETTRE).startswith("Diplômée d'un master")


def test_rien_quand_aucun_paragraphe_ne_parle_du_parcours():
    assert own_letter.parcours(LETTRE[:5] + LETTRE[6:]) == ""


def test_lettre_docx(tmp_path):
    d = Document()
    for l in LETTRE:
        d.add_paragraph(l)
    d.save(str(tmp_path / "lettre.docx"))
    assert own_letter.parcours_de_lettre(tmp_path / "lettre.docx").startswith("Diplômée")


def test_lettre_pdf_lignes_recollees(tmp_path):
    d = pymupdf.open()
    pg = d.new_page()
    y = 60
    for l in LETTRE[:5]:
        pg.insert_text((60, y), l[:80], fontsize=10)
        y += 30
    # One paragraph wrapped on three full lines; the second starts with a capital.
    for l in (
        "Diplômée d'un master en finance durable, j'ai effectué deux stages en analyse",
        "ESG, dont six mois à classer 300 fonds selon SFDR. Cette expérience m'a appris à",
        "lire un reporting extra-financier avec exigence.",
    ):
        pg.insert_text((60, y), l, fontsize=10)
        y += 13
    d.save(str(tmp_path / "lettre.pdf"))
    p = own_letter.parcours_de_lettre(tmp_path / "lettre.pdf")
    assert p.startswith("Diplômée") and p.endswith("avec exigence.")
    assert "analyse ESG, dont" in p
