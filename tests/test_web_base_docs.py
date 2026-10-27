"""The base CV and the base letter seen and edited from the window (web.workshop)."""

from jobhunter import paths, profile
from jobhunter.documents import common
from jobhunter.web.api import Api


def test_documents_de_base(tmp_path, monkeypatch):
    modeles, lettres = tmp_path / "modeles", tmp_path / "lettres"
    modeles.mkdir()
    lettres.mkdir()
    (modeles / "CV_a.docx").write_bytes(b"x")
    (lettres / "Lettre_1.docx").write_bytes(b"x")
    (lettres / "~$Lettre_1.docx").write_bytes(b"x")  # Word's lock file
    monkeypatch.setattr(paths, "CV_MODELES", modeles)
    monkeypatch.setattr(common, "LT_OUT", lettres, raising=False)
    monkeypatch.setattr(
        profile,
        "charger",
        lambda: {
            "domaines": [{"cv": "CV_a.docx"}, {"cv": "CV_b.docx"}],
            "lettre": {"phrase_profil_fr": "Ma formation.", "phrase_profil_en": "My training."},
        },
    )
    d = Api().documents_de_base()
    assert [c["nom"] for c in d["cvs"]] == ["CV_a.docx", "CV_b.docx"]
    assert d["cvs"][0]["chemin"].endswith("CV_a.docx") and d["cvs"][1]["chemin"] == ""
    assert d["exemple"].endswith("Lettre_1.docx") and "~$" not in d["exemple"]
    assert (d["phrase_fr"], d["phrase_en"]) == ("Ma formation.", "My training.")


def test_enregistrer_phrases_lettre_garde_le_reste():
    a = Api()
    ecrit = {}
    a._profil_brut = lambda: {"nom": "X", "lettre": {"contextes": [1], "phrase_profil_fr": "a"}}
    a._ecrire_profil = lambda p: ecrit.update(p) or "profile.json.bak"
    r = a.enregistrer_phrases_lettre("  Nouvelle phrase. ", "New sentence.")
    assert r == {"ok": True, "bak": "profile.json.bak"}
    assert ecrit["nom"] == "X" and ecrit["lettre"]["contextes"] == [1]
    assert ecrit["lettre"]["phrase_profil_fr"] == "Nouvelle phrase."
    assert ecrit["lettre"]["phrase_profil_en"] == "New sentence."


def test_accueil_compte_les_documents(monkeypatch, tmp_path):
    cv = tmp_path / "cv.docx"
    cv.write_bytes(b"x")
    a = Api()
    a._suivi = lambda: {}
    a._file = lambda: [
        {"entreprise": "A", "poste": "P", "fit": 9, "cv": str(cv), "lettre": str(cv)},
        {"entreprise": "B", "poste": "P", "fit": 8},
        {"entreprise": "C", "poste": "P", "fit": 5},
    ]
    assert a.tableau()["documents"] == {"bonnes": 2, "prets": 1, "a_preparer": 1}
