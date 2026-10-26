"""Screen data and guards of the web interface prototype (jobhunter.web.api)."""

from datetime import date

from jobhunter.web import api as web_api
from jobhunter.web.api import Api, candidatures, fiche, offres, rendement, tableau

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


def test_offres_a_traiter_filtres_et_tri():
    file = [
        _offre("Alpha", "Analyste ESG", 8, localisation="Paris"),
        _offre("Beta", "Analyste risque", 9, zone="international"),
        _offre("Gamma", "ESG manager", 6),
        _offre("Delta", "Analyste ESG", 9.5, statut="Expirée"),
        _offre("Eps", "Analyste ESG", 7),
    ]
    suivi = {"Eps|Analyste ESG": {"s": "postulé", "d": "2026-10-20"}}
    d = offres(file, suivi)
    assert [l["entreprise"] for l in d["lignes"]] == ["Beta", "Alpha", "Gamma"]
    assert d["zones"] == ["international", "prioritaire"]
    assert [l["entreprise"] for l in offres(file, suivi, texte="esg paris")["lignes"]] == ["Alpha"]
    assert offres(file, suivi, zone="international", fit_min=8)["total"] == 1
    assert [l["entreprise"] for l in offres(file, suivi, statut="postulées")["lignes"]] == ["Eps"]
    assert offres(file, suivi, statut="toutes")["total"] == 5
    assert [l["entreprise"] for l in offres(file, suivi, tri="entreprise")["lignes"]] == [
        "Alpha",
        "Beta",
        "Gamma",
    ]


def test_offres_pagination():
    file = [_offre("A", str(i), 5) for i in range(web_api.PAR_PAGE + 3)]
    d = offres(file, {}, page=1)
    assert (d["total"], d["pages"], len(d["lignes"])) == (web_api.PAR_PAGE + 3, 2, 3)


def test_fiche_reprend_le_suivi_et_la_description():
    o = _offre("A", "a", 8, fit_fin="8.4", source="linkedin", cv="file:///C:/x.pdf")
    f = fiche(o, {"A|a": {"s": "postulé", "d": "2026-10-20", "n": "relu"}}, "Texte")
    assert (f["id"], f["fit_fin"], f["suivi"], f["note"], f["postule_le"]) == (
        "A|a",
        8.4,
        "postulé",
        "relu",
        "2026-10-20",
    )
    assert f["description"] == "Texte" and f["cv"] == "file:///C:/x.pdf" and f["lettre"] == ""


def test_candidatures_par_colonne_sans_ecartees_ni_retirees():
    suivi = {
        "A|a": {"s": "postulé", "d": "2026-10-10"},
        "B|b": {"s": "postulé", "d": "2026-10-20"},
        "C|c": {"s": "mauvaise"},
        "D|d": {"s": "entretien", "retiree": "fermée"},
        "E|e": {"s": "à vérifier", "d": "2026-10-01"},
        "F|f": {"n": "sans statut"},
    }
    d = candidatures([_offre("A", "a", 8)], suivi)
    cols = {c["statut"]: [e["entreprise"] for e in c["entrees"]] for c in d["colonnes"]}
    assert list(cols) == [*web_api.COLONNES, "autres"]
    assert cols["postulé"] == ["B", "A"] and cols["autres"] == ["E"] and cols["entretien"] == []
    assert d["ecartees"] == 1


def test_rendement_cumule_et_garde_le_dernier_verdict():
    lignes = [
        {
            "le": "2026-10-24T08:00",
            "sources": {"apec": {"ramenees": 5, "nouvelles": 1, "verdict": "ok"}},
        },
        {
            "le": "2026-10-25T08:00",
            "sources": {
                "apec": {"ramenees": 0, "nouvelles": 0, "verdict": "refus"},
                "efc": {"ramenees": 9, "nouvelles": 4, "verdict": "ok"},
            },
        },
    ]
    r = rendement(lignes)
    assert [s["source"] for s in r] == ["efc", "apec"]
    assert (r[1]["ramenees"], r[1]["nouvelles"], r[1]["verdict"], r[1]["dernier"]) == (
        5,
        1,
        "refus",
        "2026-10-25",
    )


def test_chemin_local():
    assert web_api._chemin_local("https://example.org/a.pdf") is None
    assert web_api._chemin_local("") is None
    p = web_api._chemin_local("file:///C:/Dossier%20A/cv.pdf")
    assert p is not None and p.name == "cv.pdf" and p.parent.name == "Dossier A"


def test_brouillon_refuse_un_chemin():
    api = Api()
    assert api.brouillon("../secret.txt") == ""
    assert api.brouillon(r"C:\x.txt") == ""
    assert api.brouillon("note.md") == ""


def test_ouvrir_fichier_seulement_sous_cv_ou_lettres(monkeypatch, tmp_path):
    from jobhunter import root

    (tmp_path / "CV").mkdir()
    (tmp_path / "Letters").mkdir()
    cv = tmp_path / "CV" / "cv.pdf"
    cv.write_bytes(b"x")
    dehors = tmp_path / "autre.exe"
    dehors.write_bytes(b"x")
    monkeypatch.setattr(root, "racine", lambda: tmp_path)
    monkeypatch.setattr(root, "dossier", lambda nom: tmp_path / "Letters")
    ouverts = []
    monkeypatch.setattr("os.startfile", lambda p: ouverts.append(p), raising=False)
    api = Api()
    assert api.ouvrir_fichier(str(dehors)) is False
    assert api.ouvrir_fichier(str(tmp_path / "CV" / ".." / "autre.exe")) is False
    assert api.ouvrir_fichier("https://example.org/cv.pdf") is False
    assert api.ouvrir_fichier(cv.as_uri()) is True
    assert ouverts == [cv.resolve()]


def test_reglages_valeurs_par_defaut_et_bornes():
    assert web_api.reglages(None) == {"fond": "acrylique", "verre": 50}
    assert web_api.reglages({"fond": "mica", "verre": 140}) == {"fond": "mica", "verre": 100}
    assert web_api.reglages({"fond": "autre", "verre": "x"}) == {"fond": "acrylique", "verre": 50}


def test_ecrire_reglages_garde_la_langue(monkeypatch, tmp_path):
    import json

    f = tmp_path / "_interface.json"
    f.write_text('{"langue": "de"}', encoding="utf-8")
    monkeypatch.setattr(web_api, "_fichier_reglages", lambda: f)
    fonds = []
    api = Api()
    api._fond = fonds.append
    assert api.regler({"fond": "mica", "verre": 20}) == {"fond": "mica", "verre": 20}
    assert json.loads(f.read_text(encoding="utf-8")) == {
        "langue": "de",
        "web": {"fond": "mica", "verre": 20},
    }
    assert fonds == ["mica"] and api.reglages() == {"fond": "mica", "verre": 20}


def test_ecrire_reglages_laisse_un_fichier_illisible(monkeypatch, tmp_path):
    f = tmp_path / "_interface.json"
    f.write_text("{pas du json", encoding="utf-8")
    monkeypatch.setattr(web_api, "_fichier_reglages", lambda: f)
    web_api.ecrire_reglages({"verre": 10})
    assert f.read_text(encoding="utf-8") == "{pas du json"
