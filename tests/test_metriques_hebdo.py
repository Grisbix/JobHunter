"""Weekly report (metriques_hebdo): tracker dates, follow-ups, pipeline logs.

Converted from Scripts/test_metriques_hebdo.py.
"""

from datetime import date

import pytest

from jobhunter.programs import weekly_metrics as M

AUJ = date(2026, 10, 12)


@pytest.mark.parametrize(
    ("brut", "attendu"),
    [
        ("2026-10-07", date(2026, 10, 7)),
        ("04/09", date(2026, 9, 4)),  # dd/mm of this year
        ("20/12", date(2025, 12, 20)),  # dd/mm in the future = last year
        ("", None),
        (None, None),
        ("bientôt", None),
    ],
    ids=["ISO", "jj/mm cette annee", "jj/mm futur", "vide", "None", "illisible"],
)
def test_lire_date(brut, attendu):
    assert M.lire_date(brut, AUJ) == attendu


SUIVI = {
    "A|Analyste": {"s": "postulé", "d": "2026-10-10"},  # this week
    "B|Chargé": {"s": "postulé", "d": "2026-09-20"},  # a relancer (22 j)
    "C|Consultant": {"s": "relancé", "d": "2026-10-01"},  # a relancer (11 j)
    "D|Data": {"s": "postulé", "d": ""},  # without date
    "E|Entretien": {"s": "entretien", "d": "2026-10-05"},  # reponse < 30 j
    "F|Refus": {"s": "refus", "d": "2026-08-01"},  # reponse > 30 j
    "G|Mauvaise": {"s": "mauvaise", "d": "2026-10-11"},  # not sent
    "H|Rien": {"n": "note seule"},  # without status
    "I|Vide": None,
}


@pytest.fixture(scope="module")
def bilan():
    return M.bilan_suivi(SUIVI, AUJ)


@pytest.mark.parametrize(
    ("cle", "attendu"),
    [
        ("envoyees_periode", 1),
        ("en_attente", 4),  # postule + relance
        ("reponses_30j", 1),
        ("envoyees_total", 6),
        ("taux_reponse", 2 / 6),
        ("sans_date", 1),
        ("a_relancer", [("B|Chargé", 22), ("C|Consultant", 11)]),  # oldest first
    ],
)
def test_bilan_suivi(bilan, cle, attendu):
    assert bilan[cle] == attendu


def test_mauvaise_n_est_pas_une_candidature(bilan):
    assert bilan["statuts"]["mauvaise"] == 1


def test_entree_sans_statut_comptee(bilan):
    assert bilan["statuts"]["(aucun)"] == 2


def test_statut_en_majuscules_reconnu():
    suivi = {"X|Y": {"s": "Postulé", "d": "2026-10-11"}}
    assert M.bilan_suivi(suivi, AUJ)["envoyees_periode"] == 1


def test_suivi_vide_sans_division_par_zero():
    assert M.bilan_suivi({}, AUJ)["taux_reponse"] is None


@pytest.fixture(scope="module")
def pipeline(tmp_path_factory):
    t = tmp_path_factory.mktemp("journaux")
    (t / "pipeline_2026-10-10_1200.log").write_text(
        "Merge : +8 nouvelles, 0 enrichies\nMerge [DRY] : +3 nouvelles\n", encoding="utf-8"
    )
    (t / "pipeline_2026-10-11_0900.log").write_text("Merge : +2 nouvelles\n", encoding="utf-8")
    (t / "pipeline_2026-10-11_1800.log").write_text("Merge : +5 nouvelles\n", encoding="utf-8")
    (t / "pipeline_2026-10-01_1200.log").write_text("Merge : +99 nouvelles\n", encoding="utf-8")
    (t / "scan_manuel_2026-10-11_1605.log").write_text("Merge : +50 nouvelles\n", encoding="utf-8")
    return M.bilan_pipeline(t, AUJ)


def test_somme_des_fusions_d_un_journal(pipeline):
    assert pipeline["par_jour"][date(2026, 10, 10)] == 11


def test_deux_runs_le_meme_jour_additionnes(pipeline):
    assert pipeline["par_jour"][date(2026, 10, 11)] == 7


def test_journal_hors_periode_ignore(pipeline):
    assert date(2026, 10, 1) not in pipeline["par_jour"]


def test_journal_d_un_autre_programme_ignore(pipeline):
    assert pipeline["total"] == 18


def test_jours_sans_run_signales(pipeline):
    assert len(pipeline["jours_sans_run"]) == 5


def test_aujourd_hui_sans_run_signale(pipeline):
    assert date(2026, 10, 12) in pipeline["jours_sans_run"]


@pytest.fixture(scope="module")
def rapport(bilan, pipeline):
    return M.rapport(bilan, pipeline, AUJ)


@pytest.mark.parametrize(
    "extrait",
    ["B — Chargé (22 j)", "1 candidature(s) sans date", "Pas de journal du pipeline"],
    ids=["relances", "absence de date", "jours sans pipeline"],
)
def test_rapport_dit(rapport, extrait):
    assert extrait in rapport
