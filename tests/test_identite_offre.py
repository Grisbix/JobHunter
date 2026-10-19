"""Identité d'une offre (ADR 0010) : la clé « entreprise|poste » reste, ses pertes sont réparées.

1. Même poste dans plusieurs villes : le dédoublonnage du scan garde la ville de la
   meilleure zone du profil et note les autres (`autres_lieux`).
2. Même URL d'annonce sous deux clés (intitulé retouché, flux renommé) : `doublons`
   les réunit, en gardant l'offre suivie puis la version la plus récemment servie.
"""

import pytest

from jobhunter.programmes import doublons as D
from jobhunter.scoring import zones
from jobhunter.sources import cli


def offre(lieu, titre="Analyste ESG", entreprise="Acme"):
    return {"entreprise": entreprise, "titre": titre, "location": lieu, "url": f"https://x/{lieu}"}


@pytest.fixture
def zones_fixes(monkeypatch):
    table = {
        "Paris": "prioritaire",
        "Lyon": "secondaire",
        "Brest": "ailleurs",
        "Berlin": "international",
    }
    monkeypatch.setattr(zones, "zone_lieu", lambda lieu: table.get(lieu or "", "inconnu"))


def test_meilleure_ville_gardee(zones_fixes):
    uniq = cli.dedoublonner([offre("Berlin"), offre("Brest"), offre("Paris"), offre("Lyon")])
    assert len(uniq) == 1
    assert uniq[0]["location"] == "Paris"
    assert uniq[0]["autres_lieux"] == ["Berlin", "Brest", "Lyon"]


def test_egalite_garde_la_premiere_vue(zones_fixes):
    uniq = cli.dedoublonner([offre("Berlin"), offre("Berlin bis")])
    assert uniq[0]["location"] == "Berlin"


def test_postes_differents_intacts(zones_fixes):
    uniq = cli.dedoublonner([offre("Paris"), offre("Paris", titre="Contrôleur de gestion")])
    assert len(uniq) == 2 and all("autres_lieux" not in o for o in uniq)


def test_meme_ville_pas_d_autres_lieux(zones_fixes):
    uniq = cli.dedoublonner([offre("Paris"), offre("paris")])
    assert "autres_lieux" not in uniq[0]


# ── même URL d'annonce sous deux clés ──────────────────────────────────────────
def ligne(entreprise, poste, url, vu_le=""):
    return {"entreprise": entreprise, "poste": poste, "url": url, "vu_le": vu_le}


def oid(o):
    return f"{o['entreprise']}|{o['poste']}"


def test_meme_url_garde_la_version_actuelle():
    u = "https://jobs.lever.co/qonto/1591d10c-c025-42ef-ab54-f9e1a3a93fa2"
    file = [
        ligne("Qonto", "Staff Compliance Data Analyst", u, ""),
        ligne("Qonto", "Staff Data Analyst - Ops & Compliance", u, "2026-10-19"),
    ]
    assert list(D.doublons(file, oid=oid, rang_source=lambda u: 0)) == [
        "Qonto|Staff Compliance Data Analyst"
    ]


def test_meme_url_l_offre_suivie_reste():
    u = "https://pwc.wd3.myworkdayjobs.com/Global/job/Neuilly/Consultant_R123456"
    file = [ligne("PwC France", "Consultant", u, ""), ligne("PwC", "Consultant", u, "2026-10-19")]
    retires = D.doublons(
        file, proteges=frozenset({"PwC France|Consultant"}), oid=oid, rang_source=lambda u: 0
    )
    assert list(retires) == ["PwC|Consultant"]


def test_page_carriere_generique_n_unit_rien():
    u = "https://www.acme.com/careers"
    file = [ligne("Acme", "Analyste ESG", u), ligne("Acme", "Juriste", u)]
    assert D.doublons(file, oid=oid, rang_source=lambda u: 0) == {}
