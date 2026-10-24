"""The search edited in the app (search_settings), its preview, and CV suggestions."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from jobhunter import cv_suggestions as S
from jobhunter import search_settings as R

EXEMPLE = Path(__file__).resolve().parent.parent / "profile" / "example_finance_esg.json"


@pytest.fixture
def profil():
    return json.loads(EXEMPLE.read_text(encoding="utf-8"))


def test_lire_appliquer_aller_retour(profil):
    r = R.lire(profil)
    assert r.mots_cles and r.garder and r.ecarter
    r.mots_cles.append("analyste climat")
    nouveau = R.appliquer(profil, r)
    assert R.lire(nouveau).mots_cles[-1] == "analyste climat"
    assert list(nouveau) == list(profil)  # every other section, in the same order
    assert nouveau["competences"] == profil["competences"]
    assert "analyste climat" not in profil["collecte"]["mots_cles"]  # a copy


def test_depuis_texte():
    assert R.depuis_texte(" a \n\nB\nb\n a\nc ") == ["a", "B", "c"]


def test_valider():
    assert R.valider(R.Reglages(["x"], ["analyste"], [])) == []
    erreurs = R.valider(R.Reglages([], [], ["re:(oups"]))
    assert len(erreurs) == 3 and "motif invalide" in erreurs[2]


def test_ecrire_garde_un_bak_et_l_indentation(tmp_path, profil):
    f = tmp_path / "profile.json"
    f.write_text(json.dumps(profil, ensure_ascii=False, indent=2), encoding="utf-8")
    avant = f.read_text(encoding="utf-8")
    r = R.lire(profil)
    r.ecarter.append("stage")
    bak = R.ecrire(f, R.appliquer(profil, r))
    assert bak.read_text(encoding="utf-8") == avant
    texte = f.read_text(encoding="utf-8")
    assert texte.splitlines()[1].startswith('  "') and "stage" in texte
    assert not (tmp_path / "profile.json.tmp").exists()


def test_apercu_sur_la_file(tmp_path, profil):
    r = tmp_path / "jh"
    (r / "data").mkdir(parents=True)
    (r / "profile").mkdir()
    (r / "profile" / "profile.json").write_text(json.dumps(profil), encoding="utf-8")
    offres = [
        {"entreprise": "A", "poste": "Analyste ESG", "url": "u1"},
        {"entreprise": "B", "poste": "Chargé ESG stage", "url": "u2"},
    ]
    (r / "data" / "apply_queue.json").write_text(json.dumps(offres), encoding="utf-8")
    reg = R.lire(profil)
    reg.ecarter.append("stage")
    candidat = tmp_path / "candidat.json"
    candidat.write_text(json.dumps(R.appliquer(profil, reg)), encoding="utf-8")
    src = str(EXEMPLE.parent.parent / "src")  # the CI runs the tests without installing
    chemins = os.pathsep.join(p for p in (src, os.environ.get("PYTHONPATH", "")) if p)
    env = {**os.environ, "JOBHUNTER_RACINE": str(r), "PYTHONPATH": chemins}
    env.pop("PROFIL_JOBHUNTER", None)
    env.pop("JOBHUNTER_PRINCIPALE", None)

    def gardees(*args):
        p = subprocess.run(
            [sys.executable, "-m", "jobhunter.programs.search_preview", *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env,
        )
        assert p.returncode == 0, p.stderr[-2000:]
        return json.loads(p.stdout.strip().splitlines()[-1])

    assert set(gardees()["gardees"]) == {"A|Analyste ESG", "B|Chargé ESG stage"}
    assert gardees("--profil", str(candidat))["gardees"] == ["A|Analyste ESG"]


CV = (
    "Camille Exemple\n"
    "Stage d'analyste : classification SFDR de 300 fonds, rapports en Python.\n"
    "Langues : anglais courant, espagnol.\n"
)


def test_suggestions_seulement_ce_que_le_cv_atteste():
    profil = {"competences": {}, "collecte": {"mots_cles": []}}
    liste = S.suggestions(CV, profil)
    noms = {(s.genre, s.libelle) for s in liste}
    assert ("competence", "Espagnol") in noms
    for s in liste:  # each proof is a sentence of the CV
        assert s.phrase and s.phrase in " ".join(CV.split())
    assert all(s.genre == "competence" for s in liste if s.libelle == "Espagnol")  # no search


def test_rien_de_ce_que_le_profil_a_deja(profil):
    liste = S.suggestions(CV, profil)
    assert not any(s.libelle in profil["competences"] for s in liste)


def test_appliquer_ajoute_sans_rien_retirer(profil):
    liste = S.suggestions("Je parle italien couramment.", profil)
    italien = [s for s in liste if s.libelle == "Italien"]
    assert italien
    nouveau = S.appliquer(profil, italien)
    assert "Italien" in nouveau["competences"]
    assert set(profil["competences"]) <= set(nouveau["competences"])
    assert nouveau["collecte"]["mots_cles"] == profil["collecte"]["mots_cles"]


def test_lire_cv_docx(tmp_path):
    from docx import Document

    d = Document()
    d.add_paragraph("Python et SQL")
    d.save(str(tmp_path / "cv.docx"))
    assert "Python" in S.lire_cv(tmp_path / "cv.docx")
    with pytest.raises(ValueError):
        S.lire_cv(tmp_path / "cv.txt")


def test_lieux_lus_et_ecrits(profil):
    r = R.lire(profil)
    assert r.prioritaires == ["bordeaux", "idf"]  # the example profile
    r.prioritaires = ["idf"]
    r.secondaires = ["bordeaux", "lyon"]
    zones = R.appliquer(profil, r)["zones"]
    assert zones == {"prioritaires": ["idf"], "secondaires": ["bordeaux", "lyon"]}


def test_lieux_non_edites_laisses_tels_quels(profil):
    nouveau = R.appliquer(profil, R.Reglages(["x"], ["analyste"], []))
    assert nouveau["zones"] == profil["zones"]


def test_secteur_declare_a_la_main_garde(profil):
    a_la_main = {"cle": "geneve", "libelle": "Genève", "lieux": ["geneve"]}
    profil["zones"]["prioritaires"].append(a_la_main)
    r = R.lire(profil)
    assert r.prioritaires == ["bordeaux", "idf"]  # only the catalogue keys are edited
    r.prioritaires = ["lyon"]
    assert R.appliquer(profil, r)["zones"]["prioritaires"] == [a_la_main, "lyon"]
