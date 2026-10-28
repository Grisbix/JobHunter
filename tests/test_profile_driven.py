"""Target companies and searches drawn from the profile, not from lists per profession.

A fictitious seasonal worker in the mountains (the user, 2026-10-28: « imaginons
j'ai envie de travailler en tant que saisonnier à la montagne »).
"""

import json

import pytest

from jobhunter.scoring import zones
from jobhunter.sources import common, eures, feeds, keywords
from jobhunter.sources import company_sites as cs

SAISONNIER = ["serveur saisonnier", "moniteur de ski", "Serveur saisonnier", "perchman"]


@pytest.fixture
def config(tmp_path, monkeypatch):
    f = tmp_path / "sources_config.json"
    f.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(common, "SOURCES_CFG", f)
    return f


# ── The words each source searches with ──────────────────────────────────────


def test_les_mots_du_profil_remplacent_ceux_du_module(config, monkeypatch):
    monkeypatch.setattr(common, "KEYWORDS", SAISONNIER)
    assert keywords.mots("freehire", ("ESG", "RSE"), 8) == [
        "serveur saisonnier",
        "moniteur de ski",
        "perchman",
    ]


def test_au_plus_n_mots_du_profil(config, monkeypatch):
    monkeypatch.setattr(common, "KEYWORDS", SAISONNIER)
    assert keywords.mots("workday", ("ESG",), 2) == ["serveur saisonnier", "moniteur de ski"]


def test_une_liste_sur_mesure_l_emporte(config, monkeypatch):
    monkeypatch.setattr(common, "KEYWORDS", SAISONNIER)
    config.write_text(json.dumps({"mots_sources": {"eures": ["ski instructor"]}}), "utf-8")
    assert keywords.mots("eures", ("ESG",), 8) == ["ski instructor"]
    assert keywords.mots("freehire", ("ESG",), 1) == ["serveur saisonnier"]


def test_sans_mot_dans_le_profil_la_liste_du_module(config, monkeypatch):
    monkeypatch.setattr(common, "KEYWORDS", [])
    assert keywords.mots("freehire", ("ESG", "RSE"), 8) == ["ESG", "RSE"]


def test_eures_avec_les_mots_du_profil_le_titre_doit_en_nommer_un():
    mots = ["moniteur de ski", "serveur saisonnier"]
    assert eures._parle_de("Moniteur ski alpin - saison 2026/2027", mots)
    assert eures._parle_de("Serveur (H/F) Courchevel", mots)
    assert not eures._parle_de("Data Analyst", mots)


# ── The seasonal contract ─────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "titre",
    [
        "Serveur saisonnier H/F",
        "Réceptionniste saisonnière",
        "CDD saisonnier - perchman",
        "Seasonal ski instructor",
    ],
)
def test_contrat_saisonnier_dans_le_titre(titre):
    assert common.contrat_du_titre(titre) == "Saisonnier"


def test_contrat_saisonnier_dans_la_description():
    desc = "Hôtel 4 étoiles au pied des pistes. Type de contrat : saisonnier, de décembre à avril."
    assert common.contrat_de_la_description(desc) == "Saisonnier"
    corps = "Nous recrutons pour un emploi saisonnier en cuisine, logement fourni sur place."
    assert common.contrat_de_la_description(corps) == "Saisonnier"


def test_un_cdd_reste_un_cdd():
    assert common.contrat_du_titre("Comptable CDD 6 mois") == "CDD"


# ── The mountain zone ─────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("lieu", "dedans"),
    [
        ("Val d'Isère (73)", True),
        ("Courchevel, Savoie", True),
        ("L'Alpe d'Huez", True),
        ("Font-Romeu", True),
        ("Lyon, Auvergne-Rhône-Alpes", False),
        ("Nice, Alpes-Maritimes", False),
        ("Bayonne, Pyrénées-Atlantiques", False),
    ],
)
def test_zone_montagne(lieu, dedans):
    s = zones._secteur("montagne")
    assert s is not None
    assert zones._dans_secteur(zones._n(lieu), s) is dedans


# ── Companies followed on their own ───────────────────────────────────────────

FLUX = {
    "ucpa": {"outil": "lever", "cle": "ucpa", "url": "https://jobs.lever.co/ucpa/1"},
    "compagnie des alpes": {
        "outil": "workday",
        "cle": ["cda", "wd3", "Careers"],
        "url": "https://cda.wd3.myworkdayjobs.com/Careers/job/1",
    },
    "petit hotel": {"outil": "greenhouse", "cle": "petithotel", "url": "https://x/1"},
}
NOMS = {"ucpa": "UCPA", "compagnie des alpes": "Compagnie des Alpes", "petit hotel": "Petit Hôtel"}


@pytest.fixture
def suivi(config, monkeypatch):
    monkeypatch.setattr(
        cs, "_fits_par_entreprise", lambda: {"ucpa": 9, "compagnie des alpes": 8, "petit hotel": 4}
    )
    monkeypatch.setattr(cs, "_suivis", lambda: (set(), set()))
    monkeypatch.setattr(common, "ATS_SLUGS", {})
    monkeypatch.setattr(common, "WORKDAY_FLUX", [])
    monkeypatch.setattr(common, "AUTRES_FLUX", [])
    return config


def test_les_entreprises_bien_notees_sont_suivies(suivi):
    assert cs.suivre_seules(suivi, FLUX, NOMS) == ["UCPA", "Compagnie des Alpes"]
    cfg = json.loads(suivi.read_text(encoding="utf-8"))
    assert cfg["ats_slugs"]["lever"] == ["ucpa"]
    assert cfg["workday_flux"] == [["cda", "wd3", "Careers", "Cda"]]
    assert set(cfg[feeds.CLE_SUIVI_AUTO]) == {"lever:ucpa", "workday:cda"}
    assert b"\r\n" not in suivi.read_bytes()


def test_une_entreprise_retiree_ne_revient_pas(suivi):
    suivi.write_text(json.dumps({feeds.CLE_RETIRES: {"lever:ucpa": "2026-10-01"}}), "utf-8")
    assert cs.suivre_seules(suivi, FLUX, NOMS) == ["Compagnie des Alpes"]


def test_deja_suivie_rien_a_faire(suivi, monkeypatch):
    monkeypatch.setattr(cs, "_suivis", lambda: ({("lever", "ucpa"), ("workday", "cda")}, set()))
    assert cs.suivre_seules(suivi, FLUX, NOMS) == []
    assert json.loads(suivi.read_text(encoding="utf-8")) == {}


def test_le_seuil_et_l_arret(suivi):
    suivi.write_text(json.dumps({"suivi_auto": {"fit_min": 9}}), "utf-8")
    assert cs.suivre_seules(suivi, FLUX, NOMS) == ["UCPA"]
    suivi.write_text(json.dumps({"suivi_auto": False}), "utf-8")
    assert cs.suivre_seules(suivi, FLUX, NOMS) == []


def test_au_plus_suivi_max_par_passe(suivi, monkeypatch):
    monkeypatch.setattr(cs, "SUIVI_MAX", 1)
    assert cs.suivre_seules(suivi, FLUX, NOMS) == ["UCPA"]
