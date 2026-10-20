"""A CV dropped on the window (or chosen from the CV panel) replaces the base CV.

The pure part is called directly: which dropped file is a CV, which base CV it replaces,
the copy (old file kept as .bak) and the profile update when the extension changes.
The window part with a stand-in for the application: the dialogs answer yes, the
regeneration of the CVs is offered through run_step. A real drag from the file
explorer cannot be simulated (Tk does not pass the data of a generated <<Drop>>).
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from jobhunter import welcome
from jobhunter.app import cv_drop


def fichier(p: Path, contenu: bytes = b"x") -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(contenu)
    return p


def test_choisir_cv(tmp_path):
    docx = fichier(tmp_path / "CV Camille.docx")
    pdf = fichier(tmp_path / "cv.PDF")
    image = fichier(tmp_path / "photo.png")
    assert welcome.choisir_cv([image, docx, pdf]) == docx
    assert welcome.choisir_cv([pdf]) == pdf
    assert welcome.choisir_cv([image]) is None
    assert welcome.choisir_cv([tmp_path / "absent.docx"]) is None
    assert welcome.choisir_cv([tmp_path]) is None  # a folder named like nothing


def test_chemins_deposes_avec_espaces(fenetre_tk):
    data = "{C:/Mes documents/CV Camille.docx} C:/x.pdf"
    assert welcome.chemins_deposes(fenetre_tk.tk, data) == [
        Path("C:/Mes documents/CV Camille.docx"),
        Path("C:/x.pdf"),
    ]


def test_cvs_de_base():
    profil = {"domaines": [{"cv": "CV_a.docx"}, {"cv": "CV_b.docx"}, {"cv": "CV_a.docx"}, {}]}
    assert cv_drop.cvs_de_base(profil) == ["CV_a.docx", "CV_b.docx"]
    assert cv_drop.cvs_de_base({}) == []


@pytest.fixture
def profil(tmp_path):
    f = tmp_path / "profile" / "profile.json"
    f.parent.mkdir()
    f.write_text(
        json.dumps(
            {"domaines": [{"cle": "esg", "cv": "CV_camille.docx"}, {"cle": "fin", "cv": "x"}]}
        ),
        encoding="utf-8",
    )
    return f


def test_remplacer_meme_extension(tmp_path, profil):
    modeles = tmp_path / "CV" / "Templates"
    fichier(modeles / "CV_camille.docx", b"ancien")
    nouveau = fichier(tmp_path / "depot" / "mon cv.docx", b"nouveau")
    avant = profil.read_text(encoding="utf-8")
    assert cv_drop.remplacer_cv_de_base(nouveau, "CV_camille.docx", modeles, profil) == (
        "CV_camille.docx"
    )
    assert (modeles / "CV_camille.docx").read_bytes() == b"nouveau"
    assert (modeles / "CV_camille.docx.bak").read_bytes() == b"ancien"
    assert profil.read_text(encoding="utf-8") == avant  # same name: profile untouched


def test_remplacer_par_un_pdf_met_le_profil_a_jour(tmp_path, profil):
    modeles = tmp_path / "CV" / "Templates"
    fichier(modeles / "CV_camille.docx", b"ancien")
    nouveau = fichier(tmp_path / "cv.pdf", b"%PDF")
    assert cv_drop.remplacer_cv_de_base(nouveau, "CV_camille.docx", modeles, profil) == (
        "CV_camille.pdf"
    )
    assert (modeles / "CV_camille.pdf").read_bytes() == b"%PDF"
    assert (modeles / "CV_camille.docx").read_bytes() == b"ancien"  # left in place
    p = json.loads(profil.read_text(encoding="utf-8"))
    assert [d["cv"] for d in p["domaines"]] == ["CV_camille.pdf", "x"]
    assert (profil.parent / "profile.json.bak").exists()


def test_activer_depot(fenetre_tk):
    vu = []
    assert welcome.activer_depot(fenetre_tk, vu.append)
    assert hasattr(fenetre_tk, "dnd_bind")


def test_sans_tkinterdnd2_rien_ne_change(fenetre_tk, monkeypatch):
    monkeypatch.setitem(sys.modules, "tkinterdnd2", None)  # import fails
    assert welcome.activer_depot(fenetre_tk, print) is False


class _App(cv_drop.DepotCvMixin):
    """What the mixin uses of the application."""

    def __init__(self, racine):
        self.root = racine
        self.journal = []
        self.etapes = []

    def _log(self, txt):
        self.journal.append(txt)

    def run_step(self, cmd, label):
        self.etapes.append((cmd, label))


def test_depot_dans_l_application(fenetre_tk, tmp_path, profil, monkeypatch):
    modeles = tmp_path / "CV" / "Templates"
    fichier(modeles / "CV_camille.docx", b"ancien")
    monkeypatch.setattr(cv_drop.chemins, "CV_MODELES", modeles, raising=False)
    monkeypatch.setattr(cv_drop._profil, "FICHIER", profil)
    monkeypatch.setattr(
        cv_drop._profil, "charger", lambda: json.loads(profil.read_text(encoding="utf-8"))
    )
    monkeypatch.setattr(cv_drop._profil, "recharger", lambda *a: None)
    monkeypatch.setattr(cv_drop, "choisir", lambda *a: 0)  # "Remplacer mon CV de base"
    app = _App(fenetre_tk)
    nouveau = fichier(tmp_path / "nouveau.docx", b"nouveau")
    with (
        patch.object(cv_drop.messagebox, "askyesno", return_value=True) as oui,
        patch.object(cv_drop.messagebox, "showwarning") as attention,
    ):
        app._deposer_cv([tmp_path / "photo.png"])
        assert attention.called and not oui.called
        app._deposer_cv([nouveau])
    assert (modeles / "CV_camille.docx").read_bytes() == b"nouveau"
    assert app.etapes and app.etapes[0][0][-2:] == ["jobhunter.programs.regenerate_docs", "--cv"]
    assert any("CV_camille.docx" in t for t in app.journal)


def test_refus_ne_touche_a_rien(fenetre_tk, tmp_path, profil, monkeypatch):
    modeles = tmp_path / "CV" / "Templates"
    fichier(modeles / "CV_camille.docx", b"ancien")
    monkeypatch.setattr(cv_drop.chemins, "CV_MODELES", modeles, raising=False)
    monkeypatch.setattr(
        cv_drop._profil, "charger", lambda: json.loads(profil.read_text(encoding="utf-8"))
    )
    monkeypatch.setattr(cv_drop, "choisir", lambda *a: 0)
    app = _App(fenetre_tk)
    with patch.object(cv_drop.messagebox, "askyesno", return_value=False):
        app._deposer_cv([fichier(tmp_path / "n.docx")])
    assert (modeles / "CV_camille.docx").read_bytes() == b"ancien"
    assert not (modeles / "CV_camille.docx.bak").exists() and not app.etapes


def test_depot_nouveau_profil_ou_annule(fenetre_tk, tmp_path, monkeypatch):
    """The second choice starts a new profile from the dropped CV; closing does nothing."""
    app = _App(fenetre_tk)
    crees = []
    app._nouveau_profil = crees.append
    app._remplacer_cv = lambda cv: pytest.fail("remplacement non demande")
    cv = fichier(tmp_path / "autre.pdf")
    monkeypatch.setattr(cv_drop, "choisir", lambda *a: 1)
    app._deposer_cv([cv])
    monkeypatch.setattr(cv_drop, "choisir", lambda *a: None)
    app._deposer_cv([cv])
    assert crees == [cv]
