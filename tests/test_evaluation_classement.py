"""Evaluation of the ranking on the tracker's judgements (scoring.evaluation)."""

import pytest

from jobhunter.scoring import evaluation as E


def oid(o):
    return f"{o['entreprise']}|{o['poste']}"


def test_jugements():
    suivi = {
        "A|1": {"s": "postulé"},
        "B|2": {"s": "mauvaise"},
        "C|3": {"s": "pas intéressé"},
        "D|4": {"s": "expiré"},
        "E|5": {"s": "à vérifier"},
        "F|6": {"s": "mauvaise", "n": "pourvu"},  # a fact, not a judgement
        "G|7": {"s": "mauvaise", "n": "stage"},  # a real judgement
        "H|8": {"s": "refus"},
    }
    assert E.jugements(suivi) == {
        "A|1": True,
        "B|2": False,
        "C|3": False,
        "G|7": False,
        "H|8": True,
    }


@pytest.mark.parametrize(
    ("pos", "neg", "attendu"),
    [
        ([9, 8], [3, 2], 1.0),
        ([3, 2], [9, 8], 0.0),
        ([5], [5], 0.5),
        ([9, 4], [6], 0.5),
        ([], [1], None),
    ],
)
def test_auc(pos, neg, attendu):
    assert E.auc(pos, neg) == attendu


def test_precision():
    assert E.precision_n([(9, True), (8, False), (7, True), (1, False)]) == 0.5
    assert E.precision_n([(1, False)]) is None


def test_note_prefere_fit_fin():
    assert E.note({"fit": 8, "fit_fin": 8.4}) == 8.4
    assert E.note({"fit": 7}) == 7.0
    assert E.note({}) == 0.0


def test_intervalle_reproductible_et_encadre():
    i1 = E.intervalle([9, 8, 7, 4], [6, 5, 3, 2])
    assert i1 == E.intervalle([9, 8, 7, 4], [6, 5, 3, 2])
    assert i1[0] <= E.auc([9, 8, 7, 4], [6, 5, 3, 2]) <= i1[1]


def test_evaluer_et_pires_erreurs():
    offres = [
        {"entreprise": "A", "poste": "1", "fit_fin": 9.5},
        {"entreprise": "B", "poste": "2", "fit_fin": 9.9},  # inutile tres bien notee
        {"entreprise": "C", "poste": "3", "fit_fin": 4.0},  # pertinente mal notee
        {"entreprise": "Z", "poste": "9", "fit_fin": 9.0},  # non jugee : ignoree
    ]
    suivi = {"A|1": {"s": "postulé"}, "B|2": {"s": "mauvaise"}, "C|3": {"s": "postulé"}}
    r = E.evaluer(offres, suivi, oid)
    assert (r["pertinentes"], r["inutiles"], r["auc"]) == (2, 1, 0.0)
    assert r["pires"]["inutiles_hautes"][0][1] == "B"
    assert r["pires"]["pertinentes_basses"][0][1] == "C"
