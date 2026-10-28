"""Company lists by sector (sources.company_lists): ticked lists, conversion, collection."""

import json

import pytest

from jobhunter import root
from jobhunter.sources import common, company_lists, feeds
from jobhunter.web.api import Api


def test_chaque_liste_est_lisible_et_sans_doublon():
    listes = company_lists.toutes()
    assert listes[0].ident == company_lists.FINANCE
    assert {"tech", "sante", "industrie", "commerce"} <= {x.ident for x in listes}
    for x in listes:
        assert x.titre and x.description
        cles = [(o, s.lower()) for o, slugs in x.ats_slugs.items() for s in slugs]
        cles += [("workday", f[0].lower(), f[2].lower()) for f in x.workday_flux]
        assert cles and len(cles) == len(set(cles)), x.ident
        assert all(len(f) == 4 and all(f) for f in x.workday_flux), x.ident


def test_ancienne_configuration_inchangee():
    assert company_lists.flux_effectifs({"ats_slugs": {"lever": ["a"]}}) is None


def test_premiere_coche_garde_la_finance_utilisee():
    cfg = {"ats_slugs": {"lever": ["maison"]}}  # Workday and others: the engine's lists
    company_lists.activer(cfg, "tech")
    assert cfg["listes"] == ["finance", "tech"]
    assert cfg["workday_flux"] == [] and cfg["autres_flux"] == []
    ats, workday, _ = company_lists.flux_effectifs(cfg)
    assert "maison" in ats["lever"]
    assert ("doctolib" in ats["greenhouse"]) and workday  # tech, and finance's Workday


def _collectes(cfg):
    """What a configuration collects: effective feeds minus the suspended ones."""
    ats, workday, autres = company_lists.flux_effectifs(cfg)
    s = feeds.suspendus(cfg)
    return (
        {(o, x.lower()) for o, v in ats.items() for x in v if feeds.cle(o, x) not in s},
        {f[0] for f in workday if feeds.cle("workday", f[0]) not in s},
        {(f[0], f[1]) for f in autres if feeds.cle(f[0], f[1]) not in s},
    )


def test_conversion_ne_change_pas_ce_qui_est_collecte(tmp_path, monkeypatch):
    own = {"lever": ["maison"], "greenhouse": list(common.DEFAUTS_FLUX[0]["greenhouse"][1:])}
    f = tmp_path / "sources_config.json"
    monkeypatch.setattr(common, "SOURCES_CFG", f)
    f.write_text(json.dumps({"ats_slugs": own}), encoding="utf-8")
    common._load_cfg()  # the old rule: own ATS slugs, the engine's Workday and others
    avant = (
        {(o, x.lower()) for o, v in common.ATS_SLUGS.items() for x in v},
        {w[0] for w in common.WORKDAY_FLUX},
        {(a[0], a[1]) for a in common.AUTRES_FLUX},
    )
    cfg = {"ats_slugs": own}
    company_lists.activer(cfg, company_lists.FINANCE)
    assert _collectes(cfg) == avant
    retiree = common.DEFAUTS_FLUX[0]["greenhouse"][0]
    assert feeds.cle("greenhouse", retiree) in feeds.suspendus(cfg)  # unticked, not back
    f.write_text(json.dumps({}), encoding="utf-8")
    common._load_cfg()


def test_profil_sans_finance_ne_recoit_que_ses_listes():
    cfg = {"ats_slugs": {}, "workday_flux": [], "autres_flux": [], "listes": []}
    assert company_lists.flux_effectifs(cfg) == ({}, [], [])
    company_lists.activer(cfg, "sante")
    ats, workday, autres = company_lists.flux_effectifs(cfg)
    sante = company_lists.par_ident("sante")
    assert len(workday) == len(sante.workday_flux)
    assert sum(map(len, ats.values())) == sum(map(len, sante.ats_slugs.values()))
    company_lists.activer(cfg, "sante", False)
    assert company_lists.flux_effectifs(cfg) == ({}, [], [])


def test_une_entreprise_dans_deux_listes_une_seule_fois():
    cfg = {"ats_slugs": {}, "workday_flux": [], "autres_flux": [], "listes": []}
    company_lists.activer(cfg, "tech")
    company_lists.activer(cfg, "sante")  # Doctolib and Alan are in both
    ats, _, _ = company_lists.flux_effectifs(cfg)
    assert ats["greenhouse"].count("doctolib") == 1
    assert sorted(company_lists.origine(cfg, "greenhouse", "doctolib")) == ["sante", "tech"]
    assert company_lists.origine(cfg, "greenhouse", "inconnue") == []


def test_liste_inconnue_refusee():
    with pytest.raises(ValueError):
        company_lists.activer({}, "nulle-part")


def test_la_collecte_lit_les_listes_cochees(tmp_path, monkeypatch):
    f = tmp_path / "sources_config.json"
    monkeypatch.setattr(common, "SOURCES_CFG", f)
    f.write_text(
        json.dumps(
            {"ats_slugs": {}, "workday_flux": [], "autres_flux": [], "listes": ["commerce"]}
        ),
        encoding="utf-8",
    )
    common._load_cfg()
    assert {f[0] for f in common.WORKDAY_FLUX} >= {"cc", "richemont"}
    assert "brookfield" not in {f[0] for f in common.WORKDAY_FLUX}  # finance not ticked
    # Back to an old configuration: the engine's lists again, not the previous load's.
    f.write_text(json.dumps({}), encoding="utf-8")
    common._load_cfg()
    assert common.WORKDAY_FLUX == list(common.DEFAUTS_FLUX[1])


@pytest.fixture
def api(tmp_path, monkeypatch):
    monkeypatch.setattr(root, "scripts", lambda: tmp_path)
    monkeypatch.setattr(root, "dossier_cles", lambda: tmp_path)
    monkeypatch.setattr(common, "SOURCES_CFG", tmp_path / "sources_config.json")
    a = Api()
    a._file = lambda: []
    a._suivi = lambda: {}
    return a, tmp_path


def test_ecran_cocher_une_liste_puis_une_entreprise(api):
    a, dossier = api
    listes = {x["id"]: x for x in a.listes_entreprises()}
    assert listes["finance"]["active"] and not listes["tech"]["active"]  # no file: defaults
    assert a.activer_liste("tech", True)["ok"]
    assert a.activer_liste("nulle-part", True)["ok"] is False
    listes = {x["id"]: x for x in a.listes_entreprises()}
    assert listes["tech"]["active"] and all(e["suivie"] for e in listes["tech"]["entreprises"])
    miro = next(e for e in listes["tech"]["entreprises"] if e["cle"] == "realtimeboardglobal")
    assert miro["nom"] == "Miro"
    assert a.suivre_dans_liste("greenhouse", "realtimeboardglobal", False)["ok"]
    c = json.loads((dossier / "sources_config.json").read_text(encoding="utf-8"))
    assert "greenhouse:realtimeboardglobal" in feeds.suspendus(c)
    assert a.suivre_dans_liste("greenhouse", "a b", True)["ok"] is False


def test_retirer_une_entreprise_de_liste_dit_quoi_faire(api):
    a, _ = api
    a.activer_liste("tech", True)
    ident = next(x["id"] for x in a.entreprises()["lignes"] if x["nom"] == "Miro")
    r = a.retirer_entreprise(ident)
    assert r["ok"] is False and "Tech et numérique" in r["erreur"]


def test_une_ligne_par_entreprise_et_son_vrai_nom(api):
    from jobhunter.inventory import Flux

    a, _ = api
    a._flux = lambda: [
        Flux(
            "Societegenerale", "site", "https://careers.example.com", "https://careers.example.com"
        ),
        Flux("SocieteGenerale", "smartrecruiters", "SocieteGenerale", "https://x.example/sg"),
        Flux("Alpha", "greenhouse", "alpha", "https://x.example/alpha"),
    ]
    a._file = lambda: [
        {"entreprise": "Société Générale", "source": "smartrecruiters:SocieteGenerale", "fit": 8},
        {"entreprise": "Société Générale", "url": "https://careers.example.com/1", "fit": 6},
    ]
    lignes = {x["nom"]: x for x in a.entreprises()["lignes"]}
    assert set(lignes) == {"Société Générale", "Alpha"}
    sg = lignes["Société Générale"]
    assert sg["offres"] == 2 and sg["fit"] == 8 and len(sg["flux"]) == 2
    assert sg["outil"] == "SmartRecruiters + site (navigateur)"
    assert len(lignes["Alpha"]["flux"]) == 1


def test_beau_nom():
    from collections import Counter

    from jobhunter.web.panels import _beau_nom

    assert _beau_nom(["Bnpparibas"], Counter({"BNP Paribas": 3, "BNP": 1})) == "BNP Paribas"
    assert _beau_nom(["Ey", "EY"], None) == "EY"
    assert _beau_nom(["Swiss Re", "Swissre"], Counter({"x": 1})) == "Swiss Re"
    assert _beau_nom(["Alpha"], None) == "Alpha"
    assert _beau_nom([], Counter({"CDC": 2}), ["Caissedesdepots Recrute"]) == "CDC"
    assert _beau_nom([], None, ["Rejoindre"]) == "Rejoindre"


def test_suivie_auto_puis_retiree_pour_de_bon(api):
    a, dossier = api
    f = dossier / "sources_config.json"
    f.write_text(
        json.dumps(
            {
                "ats_slugs": {"lever": ["ucpa"]},
                "workday_flux": [],
                "autres_flux": [],
                "listes": [],
                feeds.CLE_SUIVI_AUTO: {"lever:ucpa": "2026-10-28"},
            }
        ),
        encoding="utf-8",
    )
    ligne = next(x for x in a.entreprises()["lignes"] if x["outil"] == "Lever")
    assert ligne["ajoutee"] == "2026-10-28"
    assert a.retirer_entreprise(ligne["id"])["ok"]
    c = json.loads(f.read_text(encoding="utf-8"))
    assert "lever:ucpa" in c[feeds.CLE_RETIRES]
    assert "lever:ucpa" not in c[feeds.CLE_SUIVI_AUTO]
