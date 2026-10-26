"""The whole text of a CV, wherever its template puts it (jobhunter.cv_text).

Measured on 2026-10-26 with fictitious CVs: a Canva or Word "design" template (text
boxes), a Microsoft resume template (content controls) and a table inside a table gave
0 characters, so the first launch said "almost no text read" and wrote no profile; a
name in the page header was lost.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from docx import Document
from lxml import etree

from jobhunter.cv_text import texte_fichier
from jobhunter.welcome import arguments_profil

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
MC = "http://schemas.openxmlformats.org/markup-compatibility/2006"
LIGNES = [
    "Camille Exemple",
    "Analyste ESG junior",
    "camille.exemple@example.com · 06 00 00 00 00 · Bordeaux",
    "COMPÉTENCES",
    "Analyse ESG · CSRD · SFDR · Empreinte carbone · Excel · Python · SQL",
]


def _paras(lignes):
    return "".join(f"<w:p><w:r><w:t>{l}</w:t></w:r></w:p>" for l in lignes)


def _zone_de_texte(tmp_path):
    # As Word saves a text box: the DrawingML version, and a VML copy as fallback.
    d = Document()
    r = d.add_paragraph().add_run()
    xml = (
        f'<mc:AlternateContent xmlns:mc="{MC}" xmlns:w="{W}">'
        f"<mc:Choice><w:drawing><w:txbxContent>{_paras(LIGNES)}</w:txbxContent></w:drawing></mc:Choice>"
        f"<mc:Fallback><w:pict><w:txbxContent>{_paras(LIGNES)}</w:txbxContent></w:pict></mc:Fallback>"
        "</mc:AlternateContent>"
    )
    r._r.append(etree.fromstring(xml))
    d.save(tmp_path / "cv.docx")
    return tmp_path / "cv.docx"


def test_zone_de_texte_lue_une_fois(tmp_path):
    texte = texte_fichier(_zone_de_texte(tmp_path))
    assert texte.count("Camille Exemple") == 1
    assert "SFDR" in texte


def test_controle_de_contenu(tmp_path):
    d = Document()
    sdt = etree.fromstring(
        f'<w:sdt xmlns:w="{W}"><w:sdtContent>{_paras(LIGNES)}</w:sdtContent></w:sdt>'
    )
    d.element.body.insert(0, sdt)
    d.save(tmp_path / "cv.docx")
    assert "camille.exemple@example.com" in texte_fichier(tmp_path / "cv.docx")


def test_tableau_dans_un_tableau_et_ordre(tmp_path):
    d = Document()
    d.add_paragraph("Camille Exemple")
    t = d.add_table(rows=1, cols=2)
    t.cell(0, 0).text = "Profil"
    t.cell(0, 1).add_table(rows=1, cols=1).cell(0, 0).text = "CSRD, SFDR"
    d.add_paragraph("Fin")
    lignes = [l for l in texte_fichier_docx(d, tmp_path).splitlines() if l]
    assert lignes == ["Camille Exemple", "Profil", "CSRD, SFDR", "Fin"]


def texte_fichier_docx(d, tmp_path):
    d.save(tmp_path / "cv.docx")
    return texte_fichier(tmp_path / "cv.docx")


def test_en_tete_et_pied_de_page(tmp_path):
    d = Document()
    d.sections[0].header.add_paragraph("Camille Exemple")
    d.sections[0].footer.add_paragraph("camille.exemple@example.com")
    d.add_paragraph("Analyste ESG junior")
    lignes = [l for l in texte_fichier_docx(d, tmp_path).splitlines() if l]
    assert lignes == ["Camille Exemple", "Analyste ESG junior", "camille.exemple@example.com"]


def test_sans_en_tete_rien_n_est_cree(tmp_path):
    d = Document()
    d.add_paragraph("x")
    texte_fichier_docx(d, tmp_path)
    assert Document(str(tmp_path / "cv.docx")).sections[0].header.is_linked_to_previous


def test_autre_format_refuse(tmp_path):
    (tmp_path / "cv.odt").write_bytes(b"")
    with pytest.raises(ValueError):
        texte_fichier(tmp_path / "cv.odt")


def test_reponses_du_formulaire_en_options():
    args = arguments_profil(
        "cv.docx",
        {
            "prenom": " Camille ",
            "nom": "Exemple",
            "email": "",
            "metiers": "Analyste ESG",
            "annees": "2",
            "genre": "f",
            "prioritaires": ["bordeaux", "idf"],
            "secondaires": [],
            "entreprises": True,
        },
    )
    assert args[:2] == ["cv.docx", "--auto"]
    o = dict(zip(args[2::2], args[3::2], strict=True))
    assert o["--prenom"] == "Camille" and o["--email"] == "" and o["--annees"] == "2"
    assert o["--prioritaires"] == "bordeaux,idf" and o["--secondaires"] == ""
    assert (o["--genre"], o["--entreprises"]) == ("f", "o")


def test_profil_d_un_cv_en_zones_de_texte_sans_clavier(tmp_path):
    # The welcome window's path: every answer as an option, no console, no keyboard.
    for d in ("data", "profile"):
        (tmp_path / d).mkdir()
    cv = _zone_de_texte(tmp_path)
    # Enough text to pass the "almost nothing read" check, as a real CV.
    d = Document(str(cv))
    for _ in range(4):
        d.add_paragraph("Stage de six mois : classification SFDR de 300 fonds, reporting CSRD.")
    d.save(str(cv))
    env = {k: v for k, v in os.environ.items() if k != "PROFIL_JOBHUNTER"}
    env.update(JOBHUNTER_RACINE=str(tmp_path), JOBHUNTER_PRINCIPALE=str(tmp_path))
    rep = {
        "prenom": "Camille",
        "nom": "Exemple",
        "email": "camille.exemple@example.com",
        "metiers": "Analyste ESG",
        "annees": 1,
        "genre": "f",
        "prioritaires": ["bordeaux"],
    }
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
    assert profil["identite"]["prenom"] == "Camille"
    assert profil["identite"]["email"] == "camille.exemple@example.com"


def test_fenetres_d_accueil_aux_couleurs_de_l_interface_web():
    # welcome draws in customtkinter what web/static/style.css draws in HTML.
    import re

    from jobhunter import welcome

    css = (Path(welcome.__file__).parent / "web" / "static" / "style.css").read_text("utf-8")
    racine = css[css.index(":root {") : css.index("}", css.index(":root {"))]
    var = dict(re.findall(r"--([\w-]+):\s*([^;]+);", racine))
    for nom, cle in (
        ("ENCRE", "encre"),
        ("TEXTE_DOUX", "texte-doux"),
        ("SOMBRE", "sombre"),
        ("BRUN", "brun"),
        ("C1B", "c1b"),
    ):
        assert getattr(welcome, nom).lower() == var[cle].strip().lower(), nom
    r, g, b = (int(x) for x in var["fond-rgb"].split(","))
    assert welcome.FOND.lower() == f"#{r:02x}{g:02x}{b:02x}"
    assert welcome.ICONE.is_file()


# ── PDF ──────────────────────────────────────────────────────────────────────
def _pdf_deux_colonnes(chemin):
    import pymupdf

    d = pymupdf.open()
    pg = d.new_page()
    y = 160  # the sidebar first in the stream, as Canva writes it
    for l in (
        "CONTACT",
        "06 00 00 00 00",
        "camille.exemple@example.com",
        "Bordeaux",
        "COMPETENCES",
        "Gestion de projet",
        "Analyse ESG",
    ):
        pg.insert_text((30, y), l, fontsize=10)
        y += 18
    pg.insert_text((220, 70), "Camille EXEMPLE", fontsize=28)
    pg.insert_text((220, 100), "Analyste ESG junior", fontsize=14)
    pg.insert_text((220, 160), "Stage analyste ESG, 6 mois : classification SFDR.", fontsize=10)
    d.save(str(chemin))
    return chemin


def test_pdf_deux_colonnes_le_nom_d_abord(tmp_path):
    from jobhunter.programs.first_launch import propositions

    texte = texte_fichier(_pdf_deux_colonnes(tmp_path / "cv.pdf"))
    assert texte.splitlines()[:2] == ["Camille EXEMPLE", "Analyste ESG junior"]
    p = propositions(texte)
    assert (p["prenom"], p["nom"], p["metiers"]) == ("Camille", "Exemple", "Analyste ESG junior")
    assert p["email"] == "camille.exemple@example.com"


def test_pdf_ligatures_et_caracteres_invisibles():
    from jobhunter.cv_text import _propre

    assert _propre("ﬁnance durable, ﬂux­, �x") == "finance durable, flux, x"


def test_pdf_protege_et_sans_texte(tmp_path):
    import pymupdf

    from jobhunter.cv_text import pourquoi_peu_de_texte

    src = _pdf_deux_colonnes(tmp_path / "cv.pdf")
    pymupdf.open(str(src)).save(
        str(tmp_path / "protege.pdf"), encryption=pymupdf.PDF_ENCRYPT_AES_256, user_pw="x"
    )
    with pytest.raises(ValueError):
        texte_fichier(tmp_path / "protege.pdf")
    assert "mot de passe" in pourquoi_peu_de_texte(tmp_path / "protege.pdf")
    d = pymupdf.open()
    pg = d.new_page()
    for i in range(60):  # text turned into curves
        pg.draw_rect(pymupdf.Rect(30 + i * 5, 50, 33 + i * 5, 60))
    d.save(str(tmp_path / "courbes.pdf"))
    assert texte_fichier(tmp_path / "courbes.pdf") == ""
    assert "dessins" in pourquoi_peu_de_texte(tmp_path / "courbes.pdf")
    pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 20, 20), False)
    d = pymupdf.open()
    pg = d.new_page()
    pg.insert_image(pg.rect, pixmap=pix)
    d.save(str(tmp_path / "scan.pdf"))
    assert "image" in pourquoi_peu_de_texte(tmp_path / "scan.pdf")
    assert pourquoi_peu_de_texte(src) == ""
