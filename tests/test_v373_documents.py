"""3.73: a document's pages shown as pictures, elements added or removed, deletion that holds.

Synthetic documents only (public repository).
"""

import json
from pathlib import Path

import pytest
from docx import Document

from jobhunter.documents import editing, rendering
from jobhunter.programs import exclusions
from jobhunter.storage import applications
from jobhunter.web import api

RACINE = Path(__file__).resolve().parent.parent
JS = (RACINE / "src" / "jobhunter" / "web" / "static" / "app.js").read_text(encoding="utf-8")


def _docx(tmp_path):
    d = Document()
    d.add_paragraph("Titre")
    p = d.add_paragraph(style="List Bullet")
    r = p.add_run("Premier point")
    r.bold = True
    d.add_paragraph("Second point", style="List Bullet")
    t = d.add_table(rows=1, cols=1)
    t.cell(0, 0).text = "Seul dans sa cellule"
    f = tmp_path / "cv.docx"
    d.save(str(f))
    return f


def test_ajouter_garde_la_forme(tmp_path):
    f = _docx(tmp_path)
    assert editing.structurer(f, "ajouter", 1, "Premier point", "Nouveau")
    assert editing.lire(f)[:4] == ["Titre", "Premier point", "Nouveau", "Second point"]
    p = Document(str(f)).paragraphs[2]
    assert p.style.name == "List Bullet" and p.runs[0].bold


def test_supprimer(tmp_path):
    f = _docx(tmp_path)
    assert editing.structurer(f, "supprimer", 2, "Second point")
    assert editing.lire(f) == ["Titre", "Premier point", "Seul dans sa cellule"]


def test_seul_dans_une_cellule_est_vide(tmp_path):
    f = _docx(tmp_path)
    assert editing.structurer(f, "supprimer", 3, "Seul dans sa cellule")
    assert editing.lire(f)[3] == ""  # Word wants a paragraph in each cell


def test_fichier_change_rien_fait(tmp_path):
    f = _docx(tmp_path)
    avant = f.read_bytes()
    assert not editing.structurer(f, "supprimer", 2, "autre texte")
    assert not editing.structurer(f, "supprimer", 9, "Second point")
    assert not editing.structurer(f, "inconnue", 2, "Second point")
    assert f.read_bytes() == avant


def test_pages_en_images(tmp_path):
    import pymupdf

    pdf = tmp_path / "x.pdf"
    doc = pymupdf.open()
    for _ in range(2):
        doc.new_page().insert_text((72, 72), "Bonjour")
    doc.save(str(pdf))
    images = rendering.pages_png(pdf, largeur=200)
    assert len(images) == 2 and images[0][:8] == b"\x89PNG\r\n\x1a\n"
    assert rendering.pages_png(tmp_path / "absent.pdf") == []


def test_api_structurer(monkeypatch, tmp_path):
    f = _docx(tmp_path)
    monkeypatch.setattr(api, "_document_permis", lambda c: f)
    monkeypatch.setattr(rendering, "to_pdf", lambda d: None)
    a = api.Api()
    r = a.structurer_document(str(f), "ajouter", 1, "Premier point", "Nouveau")
    assert r == {"ok": True, "pdf": False}
    assert (tmp_path / "cv.docx.orig").exists()
    assert not a.structurer_document(str(f), "ajouter", 1, "faux")["ok"]
    assert not a.structurer_document(str(f), "rm", 1, "Premier point")["ok"]


# --- deletion holds ------------------------------------------------------------------------


def test_supprimer_memorise_le_refus(monkeypatch, tmp_path):
    from jobhunter.storage import queue as queue_io

    q = tmp_path / "apply_queue.json"
    q.write_text(json.dumps([{"entreprise": "A", "poste": "a"}, {"entreprise": "B", "poste": "b"}]))
    monkeypatch.setattr(queue_io, "CHEMIN", q)
    monkeypatch.setattr(queue_io, "DESCRIPTIONS", tmp_path / "descriptions.json")
    monkeypatch.setattr(queue_io, "_est_la_file", lambda p: Path(p) == q)
    monkeypatch.setattr("jobhunter.root.scripts", lambda: tmp_path)
    monkeypatch.setattr(exclusions, "FICHIER", tmp_path / "exclusions.json")
    monkeypatch.setattr(applications, "charger", lambda *a, **k: {})
    r = api.Api().supprimer(["A|a"])
    assert r["ok"] and r["n"] == 1
    assert exclusions.charger()["A|a"]["motif"] == exclusions.SUPPRIMEE
    assert [o["entreprise"] for o in queue_io.charger(q)] == ["B"]


@pytest.mark.parametrize(
    "texte",
    [
        'class: "apercu-pages"',
        'structurer("ajouter", i)',
        'structurer("supprimer", i)',
        "structurer_document(chemin, action, i, textes[i]",
    ],
)
def test_interface(texte):
    assert texte in JS
