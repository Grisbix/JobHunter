"""Sources for a profile outside finance (measured 2026-10-24, aerospace engineer).

- eFC and FIR only list finance and ESG jobs: skipped when the title filter keeps
  no finance title, kept for the reference profile.
- A company feed guessed from the name is followed only when it holds one of the
  offers already seen at that company ("aura" is not AURA-AERO).
"""

from jobhunter.programs import probe_ats_queue as pq
from jobhunter.sources import cli
from jobhunter.sources import common as _commun


def test_profil_de_reference_vise_la_finance():
    assert cli._vise_finance()


def test_profil_ingenieur_ne_vise_pas_la_finance(monkeypatch):
    monkeypatch.setattr(_commun, "title_ok", lambda t: "ingénieur" in t.lower())
    assert not cli._vise_finance()


def test_flux_confirme_par_une_offre_deja_vue():
    vus = pq.titres_par_entreprise(
        [
            {"entreprise": "AURA-AERO", "poste": "Ingénieur  Structure"},
            {"entreprise": "Relativity Space", "poste": "Structural Analysis Engineer II"},
        ]
    )
    assert pq.confirme(
        ["Structural Analysis Engineer II", "Weld Engineer"], vus["Relativity Space"]
    )
    assert not pq.confirme(["Senior Software Engineer, Device Platform"], vus["AURA-AERO"])
    assert pq.confirme(["ingénieur structure"], vus["AURA-AERO"])  # case and blanks


def test_ajouter_les_flux_confirmes(monkeypatch, tmp_path):
    import json

    monkeypatch.setattr(pq, "HERE", tmp_path)
    (tmp_path / "sources_config.json").write_text('{"ats_slugs": {}}', encoding="utf-8")
    r = {"ats": "greenhouse", "slug": "relativity", "entreprise": "Relativity Space"}
    pq.ajouter([r])
    pq.ajouter([r])  # twice: followed once
    cfg = json.loads((tmp_path / "sources_config.json").read_text(encoding="utf-8"))
    assert cfg["ats_slugs"] == {"greenhouse": ["relativity"]}


def test_mots_cles_a_sonder_du_profil_de_reference():
    from jobhunter.programs import probe_keywords as pk

    # The owner's run is unchanged: every built-in theme, whole.
    assert pk.candidats_du_profil() == pk.CANDIDATS


def test_mots_cles_a_sonder_d_une_infirmiere(monkeypatch):
    import jobhunter.sources
    from jobhunter import profile as _P
    from jobhunter.programs import probe_keywords as pk

    monkeypatch.setattr(jobhunter.sources, "title_ok", lambda t: "infirm" in t, raising=False)
    valeurs = {
        "scoring": {"axe_coeur": "sante", "axes": {"sante": {"competences": ["Réa"]}}},
        "competences": {"Réa": {"synonymes": ["réanimation", "soins intensifs"]}},
    }
    monkeypatch.setattr(_P, "get", lambda k, d=None: valeurs.get(k, d))
    monkeypatch.setattr(_P, "domaines", lambda: [{"mots_titre": ["infirmier"]}, {}])
    # No "notation esg" for a nurse: her job word with her core skills.
    assert pk.candidats_du_profil() == {
        "Ton métier": ["infirmier réanimation", "infirmier soins intensifs"]
    }


def test_offre_ajoutee_depuis_linkedin_en_francais():
    from jobhunter.programs.add_offer import titre_et_entreprise

    url = "https://fr.linkedin.com/jobs/view/controleur-de-gestion-at-meilleurtaux-4482052576"
    meta = {
        "ogTitle": "Meilleurtaux recrute pour des postes de Contrôleur de Gestion H/F (Courbevoie)",
        "ogSite": "LinkedIn",
    }
    assert titre_et_entreprise(meta, url) == ("Contrôleur de Gestion H/F", "Meilleurtaux")
    # Not "Fr", the language subdomain: the company named in the URL.
    assert (
        titre_et_entreprise({"title": "Contrôleur", "ogSite": "LinkedIn"}, url)[1] == "Meilleurtaux"
    )


def test_titre_et_entreprise_nettoyes_a_la_source():
    # break-ui: "AT&amp;T <b>France</b>" and a line break went as is into the table,
    # the letter's subject and the file names.
    o = _commun._mk(
        "Contrôleur\n de  gestion <b>H/F</b>", "https://x.fr/1", "AT&amp;T <b>France</b>"
    )
    assert (o["titre"], o["entreprise"]) == ("Contrôleur de gestion H/F", "AT&T France")
