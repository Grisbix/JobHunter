"""The desktop panels ported to the web interface (jobhunter.web.panels), on synthetic data."""

import json

import pytest

from jobhunter import api_keys, root
from jobhunter.web.api import Api
from jobhunter.web.panels import statistiques


def _offre(entreprise, poste, fit, **kw):
    return {"entreprise": entreprise, "poste": poste, "fit": fit, "zone": "prioritaire", **kw}


@pytest.fixture
def donnees(tmp_path, monkeypatch):
    """An empty data folder: config files and keys live there, never in the real one."""
    monkeypatch.setattr(root, "scripts", lambda: tmp_path)
    monkeypatch.setattr(root, "dossier_cles", lambda: tmp_path)
    api = Api()
    api._file = lambda: []
    api._suivi = lambda: {}
    return api, tmp_path


def test_statistiques_cartes_et_entonnoir():
    file = [_offre("Alpha", "Analyste ESG", 8), _offre("Beta", "Chargé RSE", 5)]
    suivi = {
        "Alpha|Analyste ESG": {"statut": "postulé", "date": "2026-10-01"},
        "Beta|Chargé RSE": {"statut": "entretien", "date": "2026-10-02"},
    }
    s = statistiques(file, suivi)
    assert s["cartes"] and all({"nom", "n"} <= set(c) for c in s["cartes"])
    assert s["sections"] and all({"titre", "lignes"} <= set(x) for x in s["sections"])
    e = s["entonnoir"]
    assert e is None or e["envoyees"] >= e["entretiens"]


def test_statistiques_lisent_les_descriptions_a_part(tmp_path):
    """The screen's queue has no descriptions: they come from their own file."""
    cv, lettre = tmp_path / "cv.pdf", tmp_path / "lettre.pdf"
    cv.write_bytes(b"%PDF"), lettre.write_bytes(b"%PDF")
    o = _offre("Alpha", "Analyste ESG", 9, cv=str(cv), lettre=str(lettre), ls_check="2026-10-27")
    o["source"] = "linkedin-search:analyste isr"
    sans = statistiques([o], {})
    assert sans["sections"][0]["lignes"][0]["n"] == 1  # not checked: counted ready
    avec = statistiques([o], {}, {"Alpha|Analyste ESG": "court"})
    assert dict((c["nom"], c["n"]) for c in avec["cartes"])["Dossiers prêts"] == 0
    avec = statistiques([o], {}, {"Alpha|Analyste ESG": "x" * 300})
    assert dict((c["nom"], c["n"]) for c in avec["cartes"])["Dossiers prêts"] == 1
    titres = {x["titre"]: x for x in avec["sections"]}
    assert titres["Sites d'où viennent les offres"]["lignes"][0]["nom"] == "LinkedIn"
    assert titres["Mots-clés qui rapportent le plus"]["lignes"][0]["nom"] == "analyste isr"
    assert not {"Canal", "État des liens"} & titres.keys()


def test_cle_champs_ne_rend_jamais_la_valeur(donnees):
    api, _ = donnees
    nom = next(iter(api_keys.CLES))
    cle = api_keys.CLES[nom]
    secret = "valeur-de-test-0123456789"
    assert api.saisir_cle(nom, dict.fromkeys(cle.champs, secret)) == {"ok": True}
    r = api.cle_champs(nom)
    assert r["ok"] and r["deja"] is True
    assert secret not in json.dumps(r)


def test_cle_inconnue_refusee(donnees):
    api, _ = donnees
    assert api.cle_champs("inexistante")["ok"] is False
    assert api.saisir_cle("inexistante", {"x": "y"})["ok"] is False


def test_connexion_refuse_un_site_inconnu(donnees):
    api, _ = donnees
    assert api.connexion("exemple.invalid")["ok"] is False


def test_sites_offres_ajout_et_retrait(donnees):
    api, dossier = donnees
    assert api.ajouter_site_offres("board", "pas-une-adresse")["ok"] is False
    assert api.ajouter_site_offres("board", "https://offres.example/emplois")["ok"]
    assert api.ajouter_site_offres("board", "https://offres.example/emplois")["ok"] is False
    assert "https://offres.example/emplois" in (dossier / "unique_domains.txt").read_text(
        encoding="utf-8"
    )
    assert api.retirer_site_offres("board", "https://offres.example/emplois")["ok"]
    assert "offres.example" not in (dossier / "unique_domains.txt").read_text(encoding="utf-8")


def test_slug_ats_ajout_et_retrait(donnees):
    api, dossier = donnees
    genre = api.sites_offres()["types"][1]
    assert api.ajouter_site_offres("inconnu", "x")["ok"] is False
    assert api.ajouter_site_offres(genre, "societe-test")["ok"]
    c = json.loads((dossier / "sources_config.json").read_text(encoding="utf-8"))
    assert c["ats_slugs"][genre] == ["societe-test"]
    api.retirer_site_offres(genre, "societe-test")
    c = json.loads((dossier / "sources_config.json").read_text(encoding="utf-8"))
    assert c["ats_slugs"][genre] == []


def test_suivre_entreprise_refuse_un_nom_et_un_site_general(donnees):
    api, _ = donnees
    assert api.suivre_entreprise("Alpha")["ok"] is False
    assert api.suivre_entreprise("https://www.linkedin.com/company/x")["ok"] is False


def test_ouvrir_lien_seulement_web(donnees):
    api, _ = donnees
    assert api.ouvrir_lien("file:///C:/Windows") is False


def test_documents_une_ligne_par_document(donnees, monkeypatch):
    """A CV's .docx and .pdf are one document; the .docx is the one to edit."""
    from jobhunter.web import api as api_mod

    api, dossier = donnees
    cv, lettres = dossier / "cv", dossier / "lettres"
    cv.mkdir(), lettres.mkdir()
    (cv / "CV_Alpha_Analyste.docx").write_bytes(b"x")
    (cv / "cv_alpha_analyste.pdf").write_bytes(b"x")
    (lettres / "Lettre_Beta.pdf").write_bytes(b"x")
    monkeypatch.setattr(api_mod, "_dossiers_documents", lambda: {"CV": cv, "Lettre": lettres})
    d = api.documents()
    assert d["total"] == 2
    lignes = {x["genre"]: x for x in d["fichiers"]}
    assert lignes["CV"]["chemin"].endswith(".docx") and lignes["CV"]["modifiable"]
    assert lignes["Lettre"]["chemin"].endswith(".pdf") and not lignes["Lettre"]["modifiable"]
    assert api.documents({"texte": "beta"})["total"] == 1
