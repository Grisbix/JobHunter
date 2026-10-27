"""Screen data and guards of the web interface prototype (jobhunter.web.api)."""

from datetime import date
from pathlib import Path

import pytest

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


def test_filtres_pays_sans_point_d_interrogation():
    file = [
        _offre("A", "a", 8, localisation="Cairo, Egypt"),
        _offre("B", "b", 8, localisation="Vienna, Austria"),
        _offre("C", "c", 8, localisation=""),
        _offre("D", "d", 8, localisation="Luxembourg, Luxembourg, Luxembourg"),
    ]
    d = offres(file, {}, statut="toutes")
    assert d["pays"] == ["Autriche", "Égypte", "Luxembourg"]  # "?" is no choice
    assert "?" not in d["regions"]
    lignes = {l["entreprise"]: l for l in d["lignes"]}
    assert (lignes["C"]["pays"], lignes["C"]["region"]) == ("", "")
    assert lignes["D"]["lieu"] == "Luxembourg"


def test_offres_pagination():
    file = [_offre("A", str(i), 5) for i in range(web_api.PAR_PAGE + 3)]
    d = offres(file, {}, page=1)
    assert (d["total"], d["pages"], len(d["lignes"])) == (web_api.PAR_PAGE + 3, 2, 3)


def test_offres_taille_de_page():
    file = [_offre("A", str(i), 5) for i in range(130)]
    d = offres(file, {}, par_page=100)
    assert (d["par_page"], d["pages"], len(d["lignes"])) == (100, 2, 100)
    d = offres(file, {}, par_page=7)  # not offered: the default
    assert (d["par_page"], len(d["lignes"])) == (web_api.PAR_PAGE, web_api.PAR_PAGE)


def test_filtres_a_plusieurs_valeurs():
    file = [
        _offre("A", "a", 8, domaine="ESG", contrat="CDI"),
        _offre("B", "b", 8, domaine="Finance", contrat="CDD"),
        _offre("C", "c", 8, domaine="IA", contrat="CDI"),
    ]
    d = offres(file, {}, domaine=["ESG", "IA"])
    assert sorted(l["entreprise"] for l in d["lignes"]) == ["A", "C"]
    d = offres(file, {}, domaine=["ESG", "Finance"], contrat="CDD")  # AND across fields
    assert [l["entreprise"] for l in d["lignes"]] == ["B"]
    assert offres(file, {}, domaine=[])["total"] == 3


def test_la_region_limite_les_pays():
    file = [
        _offre("A", "a", 8, localisation="Cairo, Egypt"),
        _offre("B", "b", 8, localisation="Vienna, Austria"),
        _offre("C", "c", 8, localisation="Paris, France"),
    ]
    d = offres(file, {}, region=["Europe"], pays=["Égypte", "Autriche"])
    assert d["pays"] == ["Autriche", "France"]  # Egypt is not offered under Europe
    assert d["choisis"]["pays"] == ["Autriche"]  # and its choice is dropped
    assert [l["entreprise"] for l in d["lignes"]] == ["B"]
    assert offres(file, {}, pays=["Égypte"])["pays"] == ["Autriche", "Égypte", "France"]


def test_reglages_menu_et_taille_de_page():
    r = web_api.reglages({"menu": "etroit", "par_page": 100})
    assert (r["menu"], r["par_page"]) == ("etroit", 100)
    r = web_api.reglages({"menu": "x", "par_page": 13})
    assert (r["menu"], r["par_page"]) == ("large", web_api.PAR_PAGE)


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
    programme = tmp_path / "CV" / "lancer.bat"  # under CV/, but not a document
    programme.write_bytes(b"x")
    assert api.ouvrir_fichier(str(programme)) is False
    assert ouverts == [cv.resolve()]


def _fv(r):
    return {"fond": r["fond"], "verre": r["verre"]}


def test_reglages_valeurs_par_defaut_et_bornes():
    assert web_api.reglages(None) == web_api.REGLAGES
    assert _fv(web_api.reglages({"fond": "mica", "verre": 140})) == {"fond": "mica", "verre": 100}
    assert _fv(web_api.reglages({"fond": "net", "verre": -5})) == {"fond": "net", "verre": 0}
    assert _fv(web_api.reglages({"fond": "autre", "verre": "x"})) == {
        "fond": "acrylique",
        "verre": 50,
    }


def test_ecrire_reglages_garde_la_langue(monkeypatch, tmp_path):
    import json

    f = tmp_path / "_interface.json"
    f.write_text('{"langue": "de"}', encoding="utf-8")
    monkeypatch.setattr(web_api, "_fichier_reglages", lambda: f)
    fonds = []
    api = Api()
    api._fond = fonds.append
    voulu = {**web_api.REGLAGES, "fond": "mica", "verre": 20, "teinte": "bleu"}
    assert api.regler({"fond": "mica", "verre": 20, "teinte": "bleu"}) == voulu
    assert json.loads(f.read_text(encoding="utf-8")) == {"langue": "de", "web": voulu}
    assert fonds == ["mica"] and api.reglages() == voulu


def test_ecrire_reglages_laisse_un_fichier_illisible(monkeypatch, tmp_path):
    f = tmp_path / "_interface.json"
    f.write_text("{pas du json", encoding="utf-8")
    monkeypatch.setattr(web_api, "_fichier_reglages", lambda: f)
    web_api.ecrire_reglages({"verre": 10})
    assert f.read_text(encoding="utf-8") == "{pas du json"


def test_reglages_teinte_et_police():
    r = web_api.reglages({"teinte": "vert", "police": "georgia"})
    assert (r["teinte"], r["police"]) == ("vert", "georgia")
    r = web_api.reglages({"teinte": "rose", "police": "comic"})
    assert (r["teinte"], r["police"]) == ("terre", "segoe")


def test_reglages_mode_clair_ou_sombre():
    assert web_api.reglages({"mode": "sombre"})["mode"] == "sombre"
    assert web_api.reglages({"mode": "nuit"})["mode"] == "auto"


def _api_sur(file, suivi):
    api = Api()
    api._file = lambda: file
    api._suivi = lambda: suivi
    return api


def test_marquer_date_le_statut_sous_verrou(monkeypatch):
    from jobhunter.storage import applications

    disque = {"A|a": {"s": "postulé", "d": "2026-10-01", "n": "garder"}}
    monkeypatch.setattr(applications, "modifier", lambda fn, attente=30: fn(disque))
    api = _api_sur([_offre("B", "b", 8)], disque)
    assert api.marquer("A|a", "relancé")["ok"]
    assert disque["A|a"]["s"] == "relancé" and disque["A|a"]["n"] == "garder"
    assert disque["A|a"]["d"] == date.today().isoformat()
    assert api.marquer("B|b", "postulé")["ok"] and disque["B|b"]["s"] == "postulé"
    assert not api.marquer("C|c", "postulé")["ok"]
    assert not api.marquer("A|a", "envoyé")["ok"]


def test_marquer_dit_quand_le_suivi_est_occupe(monkeypatch):
    from jobhunter.storage import applications

    def occupe(fn, attente=30):
        raise applications.VerrouIndisponible("x")

    monkeypatch.setattr(applications, "modifier", occupe)
    r = _api_sur([_offre("A", "a", 8)], {}).marquer("A|a", "postulé")
    assert not r["ok"] and "réessaie" in r["erreur"]


def test_lancer_seulement_les_taches_connues(monkeypatch):
    lances = []

    class Faux:
        def __init__(self, cle, libelle, cmd, cwd):
            lances.append(cmd)
            self.code, self.libelle = None, libelle

    monkeypatch.setattr(web_api, "Tache", Faux)
    monkeypatch.setattr("jobhunter.root.scripts", lambda: Path("."))
    api = _api_sur([_offre("A", "a", 8, url="https://ex.org/1"), _offre("B", "b", 8)], {})
    assert not api.lancer("rm -rf")["ok"]
    assert not api.lancer("documents", "B|b")["ok"]  # no link
    assert api.lancer("documents", "A|a")["ok"]
    assert lances[-1][-3:] == ["jobhunter.programs.generate_docs", "--url", "https://ex.org/1"]
    assert not api.lancer("collecte")["ok"]  # one at a time
    api._tache.code = 0
    assert api.lancer("collecte")["ok"]
    assert lances[-1][-2:] == ["jobhunter.programs.daily_pipeline", "--un-profil"]
    assert all("apply" not in " ".join(c) for _, c in web_api.TACHES.values())


def test_tache_lit_la_sortie_et_le_code(tmp_path):
    import sys
    import time

    t = web_api.Tache(
        "x",
        "Essai",
        [sys.executable, "-c", "print('un'); print('deux'); raise SystemExit(3)"],
        tmp_path,
    )
    for _ in range(100):
        if t.etat()["fini"]:
            break
        time.sleep(0.05)
    e = t.etat()
    assert e["fini"] and e["code"] == 3 and e["lignes"] == ["un", "deux"]


PROFIL = {
    "identite": {"prenom": "Ada", "nom": "Lovelace", "ville": "Londres"},
    "langues_parlees": ["fr"],
    "collecte": {"mots_cles": ["analyste esg"]},
    "filtre_titre": {"metier": ["re:(esg|climat)"], "exclus": ["stage"]},
    "zones": {"prioritaires": ["idf"], "secondaires": []},
    "competences": {"IA": {"synonymes": ["ia ", "machine learning"], "prose_fr": "l'IA"}},
    "competences_de_base": ["IA"],
    "scoring": {"axes": {"data": {"competences": ["IA"]}, "esg": {"competences": []}}},
}


@pytest.fixture
def profil_tmp(tmp_path, monkeypatch):
    import json

    from jobhunter import profile, search_settings

    f = tmp_path / "profile.json"
    f.write_text(json.dumps(PROFIL, ensure_ascii=False, indent=2), encoding="utf-8")
    src = tmp_path / "sources_config.json"
    src.write_text('{"keywords": ["analyste esg"], "pays_exclus": ["Inde"]}', encoding="utf-8")
    monkeypatch.setattr(profile, "FICHIER", f)
    monkeypatch.setattr(profile, "recharger", lambda *a: None)
    monkeypatch.setattr(search_settings, "_fichier_sources", lambda: src)
    api = Api()
    api.lanceees = []
    monkeypatch.setattr(api, "lancer", lambda cle, ident="": api.lanceees.append(cle))
    return api, f, src


def test_recherche_sans_changement_ne_reecrit_rien(profil_tmp):
    api, f, src = profil_tmp
    avant, savant = f.read_text(encoding="utf-8"), src.read_text(encoding="utf-8")
    r = api.recherche()
    assert len(r["garder"]) == 2  # "re:(a|b)" shown one word per line
    assert api.enregistrer_recherche(r)["ok"]
    assert f.read_text(encoding="utf-8").strip() == avant.strip()
    assert src.read_text(encoding="utf-8") == savant and api.lanceees == []


def test_recherche_ajout_mot_cle_et_lieu(profil_tmp):
    import json

    api, f, src = profil_tmp
    r = api.recherche()
    r["mots_cles"].append("finance durable")
    r["secondaires"].append({"entree": {"cle": "geneve", "libelle": "Genève"}, "libelle": "Genève"})
    res = api.enregistrer_recherche(r)
    assert res["ok"] and res["zones"] and api.lanceees == ["zones"]
    p = json.loads(f.read_text(encoding="utf-8"))
    assert p["collecte"]["mots_cles"] == ["analyste esg", "finance durable"]
    assert p["zones"]["secondaires"] == [
        {"cle": "geneve", "libelle": "Genève", "lieux": ["Genève"]}
    ]
    assert json.loads(src.read_text(encoding="utf-8"))["keywords"][-1] == "finance durable"
    assert (f.parent / "profile.json.bak").exists()


def test_recherche_refuse_sans_intitule(profil_tmp):
    api, f, _ = profil_tmp
    avant = f.read_text(encoding="utf-8")
    r = {**api.recherche(), "garder": []}
    res = api.enregistrer_recherche(r)
    assert not res["ok"] and res["erreurs"] and f.read_text(encoding="utf-8") == avant


def test_competences_gardent_l_espace_et_la_prose(profil_tmp):
    import json

    api, f, _ = profil_tmp
    c = api.competences()
    assert c["axes"] == ["data", "esg"] and c["liste"][0]["base"]
    liste = c["liste"]
    liste[0]["axes"] = ["data", "esg"]
    liste.append({"nom": "SFDR", "axes": ["esg"], "synonymes": ["sfdr"], "en": ""})
    assert api.enregistrer_competences(liste)["ok"]
    p = json.loads(f.read_text(encoding="utf-8"))
    assert p["competences"]["IA"]["synonymes"] == ["ia ", "machine learning"]
    assert p["competences"]["IA"]["prose_fr"] == "l'IA"
    assert p["scoring"]["axes"]["esg"]["competences"] == ["IA", "SFDR"]
    assert not api.enregistrer_competences([])["ok"]  # a CV base skill cannot go


def test_identite_et_langues(profil_tmp):
    import json

    api, f, _ = profil_tmp
    assert not api.enregistrer_identite({"prenom": ""})["ok"]
    assert not api.enregistrer_identite({"langues": ["français"]})["ok"]
    assert api.enregistrer_identite({"ville": "Bordeaux", "langues": ["fr", "EN", "fr"]})["ok"]
    p = json.loads(f.read_text(encoding="utf-8"))
    assert p["identite"]["ville"] == "Bordeaux" and p["langues_parlees"] == ["fr", "en"]


def test_exclusions_gardent_les_autres_cles(profil_tmp):
    import json

    api, _, src = profil_tmp
    assert api.enregistrer_exclusions({"contrats_exclus": ["stage", "stage"]})["ok"]
    conf = json.loads(src.read_text(encoding="utf-8"))
    assert conf == {
        "keywords": ["analyste esg"],
        "pays_exclus": ["Inde"],
        "contrats_exclus": ["stage"],
    }


def test_appliquer_une_proposition_de_courriel(monkeypatch):
    from jobhunter.programs import mail_statuses

    vus = []
    monkeypatch.setattr(mail_statuses, "appliquer", lambda p, attente=30: vus.append(p) or p == "b")
    api = Api()
    api._propositions = ["a", "b"]
    assert not api.appliquer_proposition(5)["ok"]
    assert not api.appliquer_proposition(0)["ok"]  # the tracking moved: nothing written
    assert api.appliquer_proposition(1)["ok"] and vus == ["a", "b"]


def test_titulaire_du_profil_ouvert(monkeypatch):
    api = Api()
    monkeypatch.setattr(
        api, "_profil_brut", lambda: {"identite": {"prenom": "Ada", "nom": "Lovelace"}}
    )
    assert api._titulaire() == "Ada Lovelace"
    monkeypatch.setattr(api, "_profil_brut", lambda: {})
    assert api._titulaire() == ""

    def illisible():
        raise ValueError

    monkeypatch.setattr(api, "_profil_brut", illisible)
    assert api._titulaire() == ""


def test_icone_de_la_fenetre_livree():
    from jobhunter.web.__main__ import ICONE

    assert ICONE.is_file()


def test_gmail_pas_relie_dit_quoi_faire(monkeypatch, tmp_path):
    from jobhunter import root

    monkeypatch.setattr(root, "dossier_cles", lambda: tmp_path)
    r = Api().lire_courriels("gmail")
    assert r["ok"] is False and "pas encore relié" in r["erreur"]
    assert str(tmp_path / "gmail_client.json") in r["erreur"]
