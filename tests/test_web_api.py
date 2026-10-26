"""Home screen data of the web interface prototype (jobhunter.web.api.tableau)."""

from datetime import date

from jobhunter.web.api import Api, tableau

JOUR = date(2026, 10, 26)


def _offre(entreprise, poste, fit, statut="Scan 2026-10-25", zone="prioritaire", **kw):
    return {
        "entreprise": entreprise,
        "poste": poste,
        "fit": fit,
        "statut": statut,
        "zone": zone,
        **kw,
    }


def test_vide():
    d = tableau([], {}, JOUR)
    assert d["stats"] == {"file": 0, "neuf": 0, "postulees": 0}
    assert d["collecte"] == [] and d["meilleures"] == [] and d["zones"] == []


def test_collecte_par_scan_sept_derniers():
    offres = [_offre("A", str(i), 5, statut=f"Scan 2026-10-{10 + i:02d}") for i in range(9)]
    offres += [_offre("B", "x", 5, statut="Scan 2026-10-18")]
    d = tableau(offres, {}, JOUR)
    assert [c["jour"] for c in d["collecte"]] == [f"2026-10-{d:02d}" for d in range(12, 19)]
    assert d["collecte"][-1]["n"] == 2


def test_meilleures_seulement_a_traiter_par_fit_puis_fit_fin():
    offres = [
        _offre("A", "a", 9, fit_fin="7"),
        _offre("B", "b", 9, fit_fin=8.5),
        _offre("C", "c", 10, statut="postulé"),
        _offre("D", "d", "bad"),
    ]
    d = tableau(offres, {}, JOUR)
    assert [o["entreprise"] for o in d["meilleures"]] == ["B", "A", "D"]
    assert d["stats"]["neuf"] == 2


def test_relances_apres_sept_jours_et_candidatures_sans_les_ecartees():
    suivi = {
        "A|a": {"s": "postulé", "d": "2026-10-10"},
        "B|b": {"s": "postulé", "d": "2026-10-22"},
        "C|c": {"s": "mauvaise", "d": "2026-10-24"},
        "D|d": {"s": "relancé", "d": "2026-10-01", "retiree": "fermée"},
    }
    d = tableau([_offre("A", "a", 8)], suivi, JOUR)
    assert [(r["entreprise"], r["jours"]) for r in d["relances"]] == [("D", 25), ("A", 16)]
    assert [c["entreprise"] for c in d["candidatures"]] == ["B", "A"]
    assert d["candidatures"][1]["fit"] == 8.0 and d["candidatures"][0]["fit"] is None
    assert d["stats"]["postulees"] == 3


def test_zones_des_offres_notees_sept_et_plus():
    offres = [_offre("A", str(i), 8, zone="international") for i in range(3)]
    offres += [_offre("B", "b", 7), _offre("C", "c", 3, zone="ailleurs")]
    d = tableau(offres, {}, JOUR)
    assert d["zones"] == [
        {"zone": "international", "n": 3, "pct": 75},
        {"zone": "prioritaire", "n": 1, "pct": 25},
    ]


def test_ouvrir_refuse_ce_qui_n_est_pas_un_lien_web(monkeypatch):
    ouverts = []
    monkeypatch.setattr("webbrowser.open", lambda u: ouverts.append(u) or True)
    api = Api()
    assert api.ouvrir("file:///C:/Windows/System32/calc.exe") is False
    assert api.ouvrir("javascript:alert(1)") is False
    assert api.ouvrir("https://example.org/offre") is True
    assert ouverts == ["https://example.org/offre"]
