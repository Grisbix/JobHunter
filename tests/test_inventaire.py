"""Données des panneaux Entreprises, Accès et Mes CV (jobhunter.app.inventaire)."""

import datetime
import os
import time

from jobhunter import liens
from jobhunter.app import inventaire as inv


def _flux():
    return inv.flux_suivis(
        {"greenhouse": ["forvismazars"], "lever": ["back-market"]},
        [("pwc", "wd3", "Global_Experienced_Careers", "PwC")],
        [
            ("sfrss", "careers.ey.com|ey.com", "EY"),
            ("sitemap", "https://www.sia-partners.com/sitemap.xml|/en/career/", "Sia Partners"),
        ],
        ["https://www.bil.com/fr/carrieres"],
    )


def test_flux_suivis_liens_et_noms():
    f = {x.nom: x for x in _flux()}
    assert f["Forvismazars"].lien == "https://job-boards.greenhouse.io/forvismazars"
    assert f["Back Market"].lien == "https://jobs.lever.co/back-market"
    assert f["PwC"].lien == "https://pwc.wd3.myworkdayjobs.com/Global_Experienced_Careers"
    assert f["EY"].cle == "careers.ey.com"
    assert f["EY"].lien == "https://careers.ey.com"
    assert f["Sia Partners"].lien == "https://sia-partners.com"
    assert f["Bil"].outil == "site"
    assert [x.nom for x in _flux()] == sorted((x.nom for x in _flux()), key=str.lower)


def test_flux_suivis_vides():
    assert inv.flux_suivis({}, [], []) == []


def test_compter_par_marqueur_exact_jamais_par_sous_chaine():
    flux = _flux()
    offres = [
        {"source": "workday:pwc", "fit": 7, "date_publication": "2026-10-01"},
        {"source": "workday:pwc", "fit": 9, "vu_le": "2026-10-18"},
        {"source": "greenhouse:ForvisMazars", "fit": 5},
        {"source": "sfrss:careers.ey.com", "fit": 3},
        {"source": "workday:pwc.wd3/Global_Campus_Careers", "fit": 4},  # ancien marqueur
        {"source": "sitemap:www.sia-partners.com", "fit": 2},
        # « bil » dans « mobilité » : l'ancien panneau la comptait pour Bil
        {"source": "linkedin-search:mobilite", "url": "https://x.com/mobilite-bil", "fit": 10},
        {"source": "https://www.bil.com", "url": "https://www.bil.com/fr/carrieres/123", "fit": 6},
    ]
    c = {f.nom: v for f, v in inv.compter(offres, flux).items()}
    assert c["PwC"] == inv.Compte(3, 9, "2026-10-18")
    assert c["Sia Partners"].offres == 1
    assert c["Forvismazars"].offres == 1
    assert c["EY"].offres == 1
    assert c["Bil"] == inv.Compte(1, 6, "")
    assert c["Back Market"] == inv.Compte()


def test_flux_depuis_url():
    assert inv.flux_depuis_url("https://job-boards.greenhouse.io/forvismazars/jobs/1") == (
        "greenhouse",
        "forvismazars",
    )
    assert inv.flux_depuis_url("https://boards.greenhouse.io/embed/job_board?for=mirakl") == (
        "greenhouse",
        "mirakl",
    )
    assert inv.flux_depuis_url("https://jobs.lever.co/agicap/abc") == ("lever", "agicap")
    assert inv.flux_depuis_url("https://jobs.ashbyhq.com/alan") == ("ashby", "alan")
    assert inv.flux_depuis_url("https://ibanfirst.recruitee.com/o/x") == ("recruitee", "ibanfirst")
    assert inv.flux_depuis_url("https://careers.smartrecruiters.com/Ecovadis") == (
        "smartrecruiters",
        "Ecovadis",
    )
    assert inv.flux_depuis_url("https://eiffage.wd3.myworkdayjobs.com/fr-FR/externe/job/1") == (
        "workday",
        ("eiffage", "wd3", "externe"),
    )
    assert inv.flux_depuis_url("https://www.bnpparibas.com/carrieres") is None


def test_etat_sources():
    journal = [
        {"le": "2026-10-10T07:00:00", "sources": {"apec": {"verdict": "ok", "ramenees": 4}}},
        {
            "le": "2026-10-15T07:00:00",
            "sources": {
                "apec": {"verdict": "refusé", "ramenees": 0},
                "linkedin": {"verdict": "ok", "ramenees": 1},
                "efc": {"verdict": "limité", "ramenees": 3},
            },
        },
    ]
    etats = {
        e.source: e
        for e in inv.etat_sources(
            journal, lambda f: f == "francetravail.json", datetime.date(2026, 10, 19)
        )
    }
    assert etats["apec"].etat == "refusé — pas avant le 14/11"
    assert etats["apec"].gravite == "ko"
    assert etats["apec"].le == "2026-10-15"
    assert etats["linkedin"].etat == "ok — 1 offre"
    assert etats["efc"].gravite == "ancien"
    assert etats["adzuna"].etat == "clé à créer"
    assert etats["jooble"].acces == "clé"
    assert etats["francetravail"].etat == "pas encore mesurée"
    assert "indeed" not in etats  # hors de la collecte depuis le 2026-10-03


def test_etat_sources_refus_ancien_ne_dit_plus_d_attendre():
    journal = [{"le": "2026-08-01T07:00:00", "sources": {"apec": {"verdict": "refusé"}}}]
    (e,) = [x for x in inv.etat_sources(journal, lambda f: True) if x.source == "apec"]
    assert e.etat == "refusé"


def test_dossiers(tmp_path):
    cv_docx = tmp_path / "CV_a.docx"
    cv_docx.write_bytes(b"x")
    lettre_docx = tmp_path / "L_a.docx"
    lettre_docx.write_bytes(b"x")
    lettre_pdf = tmp_path / "L_a.pdf"
    lettre_pdf.write_bytes(b"x")
    t = time.time() + 5
    os.utime(lettre_pdf, (t, t))
    cv_pdf = tmp_path / "CV_b.pdf"
    cv_pdf.write_bytes(b"x")
    offres = [
        {
            "entreprise": "A",
            "poste": "Analyste",
            "fit": 7,
            "cv": str(cv_docx),
            "lettre": liens.url_de(lettre_docx),
        },
        {
            "entreprise": "B",
            "poste": "Chargé",
            "fit": 9,
            "cv": str(cv_pdf),
            "lettre": str(lettre_pdf),
        },
        {"entreprise": "C", "poste": "Sans dossier", "fit": 10},
        {"entreprise": "D", "poste": "Manquant", "fit": 1, "cv": str(tmp_path / "absent.pdf")},
    ]
    ds = inv.dossiers(offres)
    assert [d.titre for d in ds] == ["B — Chargé", "A — Analyste", "D — Manquant"]
    assert ds[0].etat == "prêt"
    assert ds[1].etat == "PDF à refaire"
    assert ds[1].lettre == lettre_pdf  # le PDF à jour est préféré au .docx
    assert ds[2].etat == "incomplet"
    assert ds[2].cv is None
    assert [d.titre for d in inv.dossiers(offres, "analy")] == ["A — Analyste"]


DEFAUTS = {
    "ats_slugs": {"lever": ["agicap"], "ashby": ["alan"]},
    "workday_flux": [("pwc", "wd3", "Global", "PwC")],
    "autres_flux": [("sfrss", "careers.ey.com|ey.com", "EY")],
}


def test_ajouter_flux_seme_les_defauts_sans_les_perdre():
    cfg = {"keywords": ["esg"]}
    msg = inv.ajouter_flux(cfg, DEFAUTS, ("lever", "pigment"))
    assert msg.startswith("＋")
    assert cfg["ats_slugs"] == {"lever": ["agicap", "pigment"], "ashby": ["alan"]}
    assert inv.ajouter_flux(cfg, DEFAUTS, ("lever", "Pigment")).startswith("déjà suivi")
    inv.ajouter_flux(cfg, DEFAUTS, ("workday", ("eiffage", "wd3", "externe")))
    assert cfg["workday_flux"] == [
        ["pwc", "wd3", "Global", "PwC"],
        ["eiffage", "wd3", "externe", "Eiffage"],
    ]
    assert inv.ajouter_flux(cfg, DEFAUTS, ("workday", ("pwc", "wd3", "x"))).startswith("déjà")
    assert DEFAUTS["ats_slugs"]["lever"] == ["agicap"]  # les défauts ne sont pas modifiés


def test_retirer_flux():
    cfg: dict = {"ats_slugs": {"lever": ["agicap", "pigment"]}}
    assert inv.retirer_flux(cfg, DEFAUTS, inv.Flux("Pigment", "lever", "pigment", ""))
    assert cfg["ats_slugs"]["lever"] == ["agicap"]
    assert inv.retirer_flux(cfg, DEFAUTS, inv.Flux("PwC", "workday", "pwc", ""))
    assert cfg["workday_flux"] == []
    assert inv.retirer_flux(cfg, DEFAUTS, inv.Flux("EY", "sfrss", "careers.ey.com", ""))
    assert cfg["autres_flux"] == []
    assert not inv.retirer_flux(cfg, DEFAUTS, inv.Flux("Bil", "site", "https://bil.com", ""))
