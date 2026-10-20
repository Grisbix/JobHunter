"""Cleanup recipes (jobhunter.cleanup_recipes, idea 3 of the architecture notes)."""

import json

import pytest

from jobhunter import cleanup_recipes as R

RECETTES = R.depuis_texte(
    "# a comment\n"
    "entreprise | PricewaterhouseCoopers | PwC\n"
    "entreprise | re:\\s+(SAS|SA|GmbH)$ |\n"
    "localisation | re:^Paris \\d+e$ | Paris\n"
)


def offres():
    return [
        {"entreprise": "PricewaterhouseCoopers", "poste": "Analyste", "localisation": "Paris 8e"},
        {"entreprise": "Acme SAS", "poste": "Chargé ESG", "localisation": "Lyon"},
        {"entreprise": "Postulée SA", "poste": "Auditeur"},
        {"entreprise": "Beta GmbH", "poste": "Analyst"},
        {"entreprise": "Beta", "poste": "Analyst"},  # the rename would collide with it
    ]


def test_texte_aller_retour():
    assert R.depuis_texte(R.en_texte(RECETTES)) == RECETTES
    assert len(RECETTES) == 3


@pytest.mark.parametrize(
    "texte,morceau",
    [
        ("poste | a | b", "champ"),
        ("entreprise |  | b", "rien à remplacer"),
        ("entreprise | re:( | b", "motif invalide"),
    ],
)
def test_valider(texte, morceau):
    (erreur,) = R.valider(R.depuis_texte(texte))
    assert morceau in erreur


def test_apercu_protege_candidatures_et_doublons():
    chg = R.apercu(offres(), RECETTES, {"Postulée SA|Auditeur"})
    vus = {(c.oid, c.champ): (c.apres, c.ecarte) for c in chg}
    assert vus[("PricewaterhouseCoopers|Analyste", "entreprise")] == ("PwC", "")
    assert vus[("PricewaterhouseCoopers|Analyste", "localisation")] == ("Paris", "")
    assert vus[("Acme SAS|Chargé ESG", "entreprise")] == ("Acme", "")
    assert vus[("Postulée SA|Auditeur", "entreprise")] == ("Postulée", "candidature")
    assert vus[("Beta GmbH|Analyst", "entreprise")] == ("Beta", "doublon")
    assert ("Acme SAS|Chargé ESG", "localisation") not in vus  # Lyon: nothing to do


def test_appliquer_puis_rejouer_ne_change_rien():
    file_ = offres()
    n = R.appliquer(file_, R.apercu(file_, RECETTES, {"Postulée SA|Auditeur"}))
    assert n == 3
    assert [o["entreprise"] for o in file_] == ["PwC", "Acme", "Postulée SA", "Beta GmbH", "Beta"]
    assert file_[0]["localisation"] == "Paris"
    again = [c for c in R.apercu(file_, RECETTES, {"Postulée SA|Auditeur"}) if not c.ecarte]
    assert again == []  # idempotent


def test_regle_qui_viderait_le_champ_ignoree():
    r = R.depuis_texte("entreprise | re:.* |")
    assert R.apercu([{"entreprise": "Acme", "poste": "x"}], r, set()) == []


def test_lire_ecrire(tmp_path):
    f = tmp_path / R.FICHIER
    R.ecrire(f, RECETTES)
    assert R.lire(f) == RECETTES
    assert json.loads(f.read_text("utf-8"))[0]["vers"] == "PwC"
    assert R.lire(tmp_path / "absent.json") == []


def test_programme_apercu_puis_appliquer(
    file_temporaire, suivi_temporaire, tmp_path, monkeypatch, capsys
):
    from jobhunter.programs import recipes as prog
    from jobhunter.storage import queue as queue_io

    queue_io.sauver(offres())
    monkeypatch.setattr(prog._racine, "scripts", lambda: tmp_path)
    R.ecrire(tmp_path / R.FICHIER, RECETTES)
    assert prog.main([]) == 0
    assert "Rien n'est écrit" in capsys.readouterr().out
    assert queue_io.charger(descriptions=False)[0]["entreprise"] == "PricewaterhouseCoopers"
    assert prog.main(["--appliquer"]) == 0
    assert queue_io.charger(descriptions=False)[0]["entreprise"] == "PwC"
