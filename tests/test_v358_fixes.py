"""3.58: what the user found on a fresh install (2026-10-28).

The update button that never finished, the header band out of line with the filters,
the base CV given as a .docx that showed nothing, the base letter, the « Refaire »
buttons with nothing to redo, the empty Documents screen, the logo.
"""

import io
import re
from pathlib import Path

from tests.test_documents_editing import _docx

from jobhunter.documents import common, rendering
from jobhunter.programs import update as mise_a_jour
from jobhunter.web import workshop
from jobhunter.web.api import Api

STATIQUE = Path(__file__).resolve().parent.parent / "src" / "jobhunter" / "web" / "static"
CSS = (STATIQUE / "style.css").read_text(encoding="utf-8")
JS = (STATIQUE / "app.js").read_text(encoding="utf-8")


# --- The update ---------------------------------------------------------------------


def test_un_moteur_installe_par_pip_se_met_a_jour_par_pip(monkeypatch, tmp_path):
    # The data folder has its own git repository: before 3.58 the update took it for
    # the engine's and stopped on « ne suit aucune branche distante ».
    paquet = tmp_path / "site-packages" / "jobhunter"
    paquet.mkdir(parents=True)
    donnees = tmp_path / "Recherche"
    donnees.mkdir()
    monkeypatch.setattr(mise_a_jour, "RACINE", donnees)
    monkeypatch.setattr(mise_a_jour, "_dossier_moteur", lambda: paquet)
    assert mise_a_jour.paquet_pip()
    (donnees / "VERSION").write_text("3.57.0")  # a published ZIP / git installation
    assert not mise_a_jour.paquet_pip()
    (donnees / "VERSION").unlink()
    (tmp_path / "pyproject.toml").write_text("")  # a source checkout: development copy
    monkeypatch.setattr(mise_a_jour, "_dossier_moteur", lambda: tmp_path / "src" / "jobhunter")
    assert not mise_a_jour.paquet_pip()


def test_maj_paquet_installe_les_fichiers_signes(monkeypatch, capsys):
    monkeypatch.setattr(mise_a_jour, "version_paquet", lambda: "3.57.0")
    monkeypatch.setattr(mise_a_jour, "_get", lambda url, t: b"3.58.0\n")
    monkeypatch.setattr(mise_a_jour, "file_libre", lambda garder=True: True)
    monkeypatch.setattr(
        mise_a_jour,
        "fichiers_a_installer",
        lambda distante=None: {"pyproject.toml": b"[project]\n"},
    )
    vus = {}

    class Fait:
        returncode = 0

    def pip(cmd):
        vus["cmd"] = cmd
        vus["fichiers"] = sorted(p.name for p in Path(cmd[-1]).iterdir())
        return Fait()

    monkeypatch.setattr(mise_a_jour.subprocess, "run", pip)
    assert mise_a_jour.maj_paquet(False) == 0
    assert vus["cmd"][1:4] == ["-m", "pip", "install"] and vus["fichiers"] == ["pyproject.toml"]
    sortie = capsys.readouterr().out
    assert "Étape 1/2" in sortie and "Étape 2/2" in sortie


def test_maj_paquet_deja_a_jour(monkeypatch, capsys):
    monkeypatch.setattr(mise_a_jour, "version_paquet", lambda: "3.58.0")
    monkeypatch.setattr(mise_a_jour, "_get", lambda url, t: b"3.58.0")
    assert mise_a_jour.maj_paquet(False) == 0
    assert "Déjà à jour" in capsys.readouterr().out


def test_le_telechargement_dit_son_pourcentage(monkeypatch, capsys):
    class Reponse(io.BytesIO):
        headers = {"Content-Length": str(1 << 20)}

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(
        mise_a_jour.urllib.request, "urlopen", lambda req, timeout: Reponse(b"x" * (1 << 20))
    )
    assert len(mise_a_jour._get("https://example.org/f", 5)) == 1 << 20
    lignes = capsys.readouterr().out.splitlines()
    assert lignes[0] == "Téléchargement : 10 %" and lignes[-1] == "Téléchargement : 100 %"


def test_hors_paquet_msix_rien_du_store():
    from jobhunter import frozen

    assert frozen.msix_du_store() is False


def test_le_bouton_suit_la_mise_a_jour():
    corps = JS[JS.index("function suivreMaj(e)") :][:1600]
    assert "b.title = info" in corps and "duree(e.duree)" in corps and "%" in corps
    assert "suivreMaj(e);" in JS
    assert '"Mise à jour en cours…"' not in JS  # the label that never ended


# --- First opening, logo, header band -------------------------------------------------


def test_opaque_a_la_premiere_ouverture():
    from jobhunter.web import api

    assert api.reglages(None)["verre"] == 0


def test_un_seul_logo():
    icone = Path(__file__).resolve().parent.parent / "src" / "jobhunter" / "app" / "assets"
    assert (STATIQUE / "logo.png").read_bytes() == (icone / "jobhunter.png").read_bytes()
    assert re.search(r'\.logo \{[^}]*url\("logo\.png"\)', CSS)
    welcome = (icone.parent.parent / "welcome.py").read_text(encoding="utf-8")
    assert "SetCurrentProcessExplicitAppUserModelID" in welcome


def test_la_bande_d_en_tete_va_d_un_bord_a_l_autre_du_panneau():
    assert re.search(
        r"\.vue\.plein \.remplit > \.defile[^{]*\{ margin: 0 -24px; padding: 0 24px; \}", CSS
    )
    assert re.search(r"thead th:first-child::before \{ left: -24px; \}", CSS)
    assert re.search(r"thead th:last-child::after \{ right: -24px; \}", CSS)


# --- Documents ------------------------------------------------------------------------


def test_documents_compte_les_existants_malgre_les_filtres(monkeypatch, tmp_path):
    from jobhunter.web import api as web_api

    cv, lt = tmp_path / "cv", tmp_path / "lt"
    cv.mkdir()
    lt.mkdir()
    (cv / "CV_A.pdf").write_bytes(b"x")
    (cv / "CV_A.docx").write_bytes(b"x")
    (cv / "CV_B.pdf").write_bytes(b"x")
    monkeypatch.setattr(web_api, "_dossiers_documents", lambda: {"CV": cv, "Lettre": lt})
    d = Api().documents({"texte": "introuvable"})
    assert d["total"] == 0 and d["existants"] == {"CV": 2, "Lettre": 0}


def test_refaire_seulement_s_il_y_a_quelque_chose_et_premiers_pas_sinon():
    corps = JS[JS.index("ECRANS.documents = {") :][:4000]
    assert "actions: () => []" in corps
    assert "ex.CV ? action(" in corps and "ex.Lettre ? action(" in corps
    assert "premiersDocuments()" in corps and "function premiersDocuments()" in JS


def test_un_cv_de_base_docx_sans_pdf_se_voit(monkeypatch, tmp_path):
    from jobhunter import root

    (tmp_path / "CV").mkdir()
    cv = _docx(tmp_path).replace(tmp_path / "CV" / "CV_base.docx")
    monkeypatch.setattr(root, "racine", lambda: tmp_path)
    monkeypatch.setattr(root, "dossier", lambda nom: tmp_path / "Letters")
    faits = []

    def to_pdf(p):
        faits.append(p)
        p.with_suffix(".pdf").write_bytes(b"%PDF-1.4")
        return p.with_suffix(".pdf")

    monkeypatch.setattr(rendering, "to_pdf", to_pdf)
    d = Api().document(str(cv))
    assert d["ok"] and faits == [cv] and d["pdf"] == "JVBERi0xLjQ="


def test_un_cv_de_base_pdf_seul_se_voit(monkeypatch, tmp_path):
    from jobhunter import root

    (tmp_path / "CV").mkdir()
    pdf = tmp_path / "CV" / "CV_base.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    monkeypatch.setattr(root, "racine", lambda: tmp_path)
    monkeypatch.setattr(root, "dossier", lambda nom: tmp_path / "Letters")
    d = Api().document(str(pdf))
    assert d["ok"] and d["docx"] == "" and d["pdf"] == "JVBERi0xLjQ="


def test_sans_pdf_l_apercu_montre_le_texte():
    assert "texte-doc" in JS and "installe LibreOffice" in JS


# --- The base letter ------------------------------------------------------------------


def test_la_lettre_de_base_gardee_l_ancienne_en_bak(monkeypatch, tmp_path):
    from jobhunter import own_letter

    base = tmp_path / "Letters" / "Base"
    monkeypatch.setattr(workshop, "_dossier_lettre_base", lambda: base)
    monkeypatch.setattr(
        own_letter,
        "parcours_de_lettre",
        lambda f: "Diplômé d'un master, j'ai trois ans d'expérience.",
    )
    a = Api()
    for nom in ("Ma_lettre.docx", "Nouvelle.pdf"):
        f = tmp_path / nom
        f.write_bytes(nom.encode())
        a._lettre_choisie = f
        r = a.remplacer_lettre_base()
        assert r["ok"] and r["nom"] == nom and r["parcours"].startswith("Diplômé")
    assert sorted(p.name for p in base.iterdir()) == ["Ma_lettre.docx.bak", "Nouvelle.pdf"]
    assert workshop.lettre_de_base() == base / "Nouvelle.pdf"


def test_documents_de_base_donne_la_lettre(monkeypatch, tmp_path):
    from jobhunter import paths, profile

    base = tmp_path / "Base"
    base.mkdir()
    (base / "Ma_lettre.pdf").write_bytes(b"x")
    monkeypatch.setattr(workshop, "_dossier_lettre_base", lambda: base)
    monkeypatch.setattr(paths, "CV_MODELES", tmp_path)
    monkeypatch.setattr(common, "LT_OUT", tmp_path / "rien", raising=False)
    monkeypatch.setattr(profile, "charger", lambda: {})
    d = Api().documents_de_base()
    assert d["lettre_base"]["nom"] == "Ma_lettre.pdf"
