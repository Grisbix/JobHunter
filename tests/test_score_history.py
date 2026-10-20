"""Why an offer's score changed: its successive fits (scoring.history)."""

from jobhunter.scoring import history as H


def test_pas_d_historique_sans_changement():
    o = {"fit": 7}
    H.poser(o, 7, 0, 7.1, "re-score")
    assert "historique_fit" not in o and o["fit_fin"] == 7.1


def test_nouvelle_offre_sans_historique():
    o: dict = {}
    H.poser(o, 8, 0, 8.0, "description")
    assert "historique_fit" not in o and o["fit"] == 8


def test_changement_garde_l_ancienne_valeur_puis_la_nouvelle():
    o = {"fit": 6, "process": "2026-10-01"}
    H.poser(o, 9, 0, 9.2, "description")
    h = o["historique_fit"]
    assert [e["fit"] for e in h] == [6, 9]
    assert h[0]["date"] == "2026-10-01" and h[1]["cause"] == "description"
    assert h[1]["regles"] == H.regles()
    H.poser(o, 8, 3, 8.0, "re-score")
    assert [e["fit"] for e in o["historique_fit"]] == [6, 9, 8]
    assert o["exp_requise"] == 3


def test_borne():
    o = {"fit": 1}
    for f in range(2, 2 + H.MAX + 5):
        H.poser(o, f % 10 + 1, 0, 0.0, "re-score")
    assert len(o["historique_fit"]) == H.MAX


def test_regles_identifient_moteur_et_profil():
    r = H.regles()
    assert "·" in r and r.split("·")[1] != "?"
