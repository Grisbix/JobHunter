"""The offers' order (scoring.ranking) and where it disagrees with the user (calibration)."""

from jobhunter.scoring import calibration, ranking

R = ranking.reglages({})


def test_reglages_par_defaut():
    assert R == {"malus_republiee": 0.3, "republiee_des": 3, "bonus_contrat": {}}


def test_rang():
    assert ranking.rang({"fit_fin": 9.2}, R) == 9.2
    assert ranking.rang({"fit": 7}, R) == 7.0
    assert ranking.rang({"fit": "8"}, R) == 8.0
    assert ranking.rang({}, R) == 0.0
    assert ranking.rang({"fit_fin": 9.2, "republiee": 2}, R) == 9.2
    assert round(ranking.rang({"fit_fin": 9.2, "republiee": 3}, R), 2) == 8.9
    r = ranking.reglages({"bonus_contrat": {"V.I.E": 0.5}, "malus_republiee": 1})
    assert ranking.rang({"fit_fin": 7.0, "contrat": "V.I.E"}, r) == 7.5
    assert ranking.rang({"fit_fin": 7.0, "contrat": "CDI", "republiee": 4}, r) == 6.0


def _juges():
    # V.I.E. offers scored low but chosen, CDI offers scored high but rejected.
    vie = [({"fit_fin": 6.0 + i / 10, "contrat": "V.I.E"}, True) for i in range(8)]
    cdi = [({"fit_fin": 7.0 + i / 10, "contrat": "CDI"}, False) for i in range(8)]
    bons_cdi = [({"fit_fin": 9.0 + i / 10, "contrat": "CDI"}, True) for i in range(3)]
    return vie + cdi + bons_cdi


def test_par_valeur():
    lignes = calibration.par_valeur(_juges(), "contrat", R)
    assert lignes[0][:3] == ("CDI", 3, 8)
    assert lignes[1][:3] == ("V.I.E", 8, 0)
    assert round(lignes[1][3], 2) == 6.35


def test_suggestion_fiable_quand_le_gain_tient():
    s = calibration.suggestions(_juges(), R)
    assert s[0]["contrat"] == "V.I.E" and s[0]["bonus"] == 1.5 and s[0]["fiable"]
    assert s[0]["gain"] > 0.3


def test_pas_de_suggestion_sur_trop_peu():
    juges = [
        ({"fit_fin": 6.0, "contrat": "V.I.E"}, True),
        ({"fit_fin": 8.0, "contrat": "CDI"}, False),
    ]
    assert calibration.suggestions(juges, R) == []
