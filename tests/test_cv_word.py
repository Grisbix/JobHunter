"""A PDF CV rebuilt as a .docx: same text, name first, skills on one line.

Fictitious CVs only, built here with PyMuPDF.
"""

import pymupdf
import pytest
from docx import Document

from jobhunter import cv_text, cv_word


def _cv_pdf(chemin, protege=False):
    d = pymupdf.open()
    pg = d.new_page()
    y = 160  # the sidebar first in the stream, as Canva writes it
    for l in ("CONTACT", "camille.exemple@example.com", "COMPÉTENCES", "Excel", "Python", "SQL"):
        pg.insert_text((30, y), l, fontsize=10)
        y += 18
    pg.insert_text((220, 70), "Camille EXEMPLE", fontsize=28)
    pg.insert_text((220, 100), "Analyste ESG", fontsize=14)
    y = 160
    for l in (
        "EXPÉRIENCE",
        "Stage analyste ESG, 6 mois : classification SFDR de 300 fonds",
        "et revue des indicateurs extra-financiers du portefeuille.",
        "• Reporting CSRD de deux filiales.",
        "FORMATION",
        "Master finance durable, 2025. Mémoire sur la taxonomie verte européenne.",
    ):
        pg.insert_text((220, y), l, fontsize=10)
        y += 18
    opts = {"encryption": pymupdf.PDF_ENCRYPT_AES_256, "user_pw": "x"} if protege else {}
    d.save(str(chemin), **opts)
    return chemin


def test_blocs_dans_l_ordre(tmp_path):
    b = cv_word.lire(_cv_pdf(tmp_path / "cv.pdf"))
    assert b[0] == ("nom", "Camille EXEMPLE")
    assert b[1] == ("poste", "Analyste ESG")
    assert ("titre", "EXPÉRIENCE") in b
    # Two lines of one sentence make one paragraph; the bullet stays a bullet.
    assert (
        "texte",
        "Stage analyste ESG, 6 mois : classification SFDR de 300 fonds et revue des "
        "indicateurs extra-financiers du portefeuille.",
    ) in b
    assert ("puce", "Reporting CSRD de deux filiales.") in b
    assert ("texte", "Excel, Python, SQL") in b


def test_docx_relu_et_competences_reordonnees(tmp_path):
    from jobhunter.documents.cv import ordonner_competences

    sortie = cv_word.pdf_en_docx(_cv_pdf(tmp_path / "cv.pdf"), tmp_path / "cv.docx")
    doc = Document(str(sortie))
    texte = cv_text.texte_docx(doc)
    assert texte.startswith("Camille EXEMPLE")
    assert "camille.exemple@example.com" in texte
    assert ordonner_competences(doc, "Nous cherchons un profil SQL et Python.")
    assert "Python, SQL, Excel" in [p.text for p in doc.paragraphs]


def test_pdf_protege_refuse(tmp_path):
    with pytest.raises(ValueError, match="protégé"):
        cv_word.pdf_en_docx(_cv_pdf(tmp_path / "cv.pdf", protege=True), tmp_path / "cv.docx")


def test_pdf_sans_texte_refuse(tmp_path):
    d = pymupdf.open()
    d.new_page()
    d.save(str(tmp_path / "vide.pdf"))
    with pytest.raises(ValueError, match="texte"):
        cv_word.pdf_en_docx(tmp_path / "vide.pdf", tmp_path / "cv.docx")
    assert not (tmp_path / "cv.docx").exists()


def test_meme_titre_de_competences_que_les_documents():
    from jobhunter.documents import cv

    assert cv_word.RX_COMPETENCES.pattern == cv._RX_TITRE_COMPETENCES.pattern


def test_premier_lancement_cv_pdf_en_word_et_parcours(tmp_path):
    # The welcome window's path: a PDF CV, "adapt to each offer" ticked, a background
    # paragraph taken from a letter.
    import json
    import os
    import subprocess
    import sys
    from pathlib import Path

    from jobhunter.welcome import arguments_profil

    for d in ("data", "profile"):
        (tmp_path / d).mkdir()
    cv = _cv_pdf(tmp_path / "cv.pdf")
    parcours = "Diplômée d'un master en finance durable, j'ai effectué deux stages en analyse ESG."
    rep = {
        "prenom": "Camille",
        "nom": "Exemple",
        "metiers": "Analyste ESG",
        "annees": 1,
        "genre": "f",
        "prioritaires": ["bordeaux"],
        "word": True,
        "parcours": parcours,
    }
    env = {k: v for k, v in os.environ.items() if k != "PROFIL_JOBHUNTER"}
    env.update(JOBHUNTER_RACINE=str(tmp_path), JOBHUNTER_PRINCIPALE=str(tmp_path))
    r = subprocess.run(
        [sys.executable, "-m", "jobhunter.programs.first_launch", *arguments_profil(str(cv), rep)],
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        stdin=subprocess.DEVNULL,
        timeout=120,
        cwd=str(Path(__file__).resolve().parent.parent),
    )
    assert r.returncode == 0, r.stdout + r.stderr
    profil = json.loads((tmp_path / "profile" / "profile.json").read_text(encoding="utf-8"))
    modeles = sorted(p.name for p in (tmp_path / "CV").glob("*/CV_*"))
    assert modeles == ["CV_Camille_Exemple.docx", "CV_Camille_Exemple.pdf"]
    assert json.dumps(profil, ensure_ascii=False).count("CV_Camille_Exemple.docx") >= 1
    assert profil["domaines"][0]["parcours_fr"] == parcours
