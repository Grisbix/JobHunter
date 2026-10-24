"""HelloWork: job names, category pages, offer pages (sources.hellowork).

Without network: bodies copied from the real structure of hellowork.com on 2026-10-24
(the ld+json type is HTML-escaped there: `application/ld&#x2B;json`).
"""

import datetime
import json

from conftest import Reponse

from jobhunter import sources as J
from jobhunter.sources import hellowork as H

BASE = "https://www.hellowork.com"

INDEX = """
<a href="/fr-fr/emploi/metier_ingenieur.html">x</a>
<a href="/fr-fr/emploi/index-domaine_finance.html">Finance</a>
<a href="/fr-fr/emploi/domaine_finance.html">Finance</a>
"""
DOMAINE = """
<a href="/fr-fr/emploi/metier_analyste-isr.html">a</a>
<a href="/fr-fr/emploi/metier_assistant-comptable.html">b</a>
<a href="/fr-fr/emploi/metier_analyste-isr.html">a</a>
"""


def _carte(ident, titre):
    return (
        f'<a data-turbo="false" href="/fr-fr/emplois/{ident}.html" '
        f'title="{titre}" class="no-underline" data-cy="offerTitle">'
    )


LISTE = (
    _carte(101, "Analyste ISR H/F - Sycomore AM")
    + _carte(102, "Office Manager H/F - Acme")
    + _carte(101, "Analyste ISR H/F - Sycomore AM")
)


def _offre(titre="Analyste ISR H/F", ville="Paris"):
    jp = {
        "@context": "https://schema.org",
        "@type": "JobPosting",
        "title": titre,
        "description": "<p>" + "Analyse ESG des émetteurs, reporting SFDR. " * 8 + "</p>",
        "datePosted": "2026-10-24T03:30:09Z",
        "hiringOrganization": {"@type": "Organization", "name": "Sycomore AM"},
        "jobLocation": {
            "@type": "Place",
            "address": {"addressLocality": ville, "addressCountry": "FR"},
        },
    }
    return f'<script type="application/ld&#x2B;json">\n {json.dumps(jp)}\n</script>'


def test_slug_metier():
    assert H.slug_metier("Analyste ISR") == "analyste-isr"
    assert H.slug_metier("Chargé d'affaires financement") == "charge-d-affaires-financement"


def test_cartes_titre_sans_entreprise_ni_doublon():
    assert H.cartes(LISTE) == [
        (f"{BASE}/fr-fr/emplois/101.html", "Analyste ISR H/F"),
        (f"{BASE}/fr-fr/emplois/102.html", "Office Manager H/F"),
    ]


def test_fiche_lit_le_type_echappe():
    assert H.fiche(_offre())["title"] == "Analyste ISR H/F"
    assert H.fiche("<html></html>") is None


def test_metiers_de_page():
    assert H.metiers_de_page(DOMAINE) == ["analyste-isr", "assistant-comptable"]


def test_choisir_metiers_mot_rare_avant_mot_courant():
    metiers = ["analyste-financier", "office-manager", "analyste-isr", "data-analyst"]
    mots = ["analyste isr", "analyste financier", "analyste credit", "analyste esg"]
    # The keywords that are job names first, in the keywords' order; office-manager
    # shares no word.
    assert H.choisir_metiers(metiers, mots) == ["analyste-isr", "analyste-financier"]
    # "isr" (one keyword) outweighs "analyste" (four).
    assert H.choisir_metiers(metiers, ["isr", "analyste esg", "analyste credit"])[0] == (
        "analyste-isr"
    )


def _scanner(monkeypatch, tmp_path, routes, mots=("analyste isr",)):
    monkeypatch.setattr(J, "HERE", tmp_path)
    monkeypatch.setattr(J, "QUEUE", tmp_path / "apply_queue.json")
    monkeypatch.setattr(J, "KEYWORDS", list(mots))
    monkeypatch.setattr(H, "HELLOWORK_PAUSE", 0)
    appels = []

    def envoi(_client, url, **kw):
        appels.append(url)
        for motif, rep in routes.items():
            if motif in url:
                return rep
        return Reponse("", 404)

    monkeypatch.setattr(J, "_get_borne", envoi)
    J.INCIDENTS.clear()
    return H.scan_hellowork(limite=30), appels


def test_scan_lit_index_metier_puis_offre_retenue(monkeypatch, tmp_path):
    offres, appels = _scanner(
        monkeypatch,
        tmp_path,
        {
            "index-categorie": Reponse(INDEX),
            "index-domaine_finance": Reponse(DOMAINE),
            "metier_analyste-isr": Reponse(LISTE),
            "emplois/101": Reponse(_offre()),
        },
    )
    # Office Manager is never opened; the list of job names is kept for 30 days.
    assert appels == [
        f"{BASE}/fr-fr/emploi/index-categorie.html",
        f"{BASE}/fr-fr/emploi/index-domaine_finance.html",
        f"{BASE}/fr-fr/emploi/metier_analyste-isr.html",
        f"{BASE}/fr-fr/emplois/101.html",
    ]
    assert [(o["titre"], o["entreprise"], o["location"]) for o in offres] == [
        ("Analyste ISR H/F", "Sycomore AM", "Paris FR")
    ]
    cache = json.loads((tmp_path / H.METIERS_FICHIER).read_text(encoding="utf-8"))
    assert cache["metiers"] == ["ingenieur", "analyste-isr", "assistant-comptable"]


def test_liste_des_metiers_relue_apres_30_jours(monkeypatch, tmp_path):
    vieux = (datetime.date.today() - datetime.timedelta(days=31)).isoformat()
    (tmp_path / H.METIERS_FICHIER).write_text(
        json.dumps({"le": vieux, "metiers": ["analyste-isr"]}), encoding="utf-8"
    )
    _, appels = _scanner(monkeypatch, tmp_path, {"index-categorie": Reponse(INDEX)})
    assert appels[0].endswith("index-categorie.html")
    frais = datetime.date.today().isoformat()
    (tmp_path / H.METIERS_FICHIER).write_text(
        json.dumps({"le": frais, "metiers": ["analyste-isr"]}), encoding="utf-8"
    )
    _, appels = _scanner(monkeypatch, tmp_path, {"metier_analyste-isr": Reponse("")})
    assert appels == [f"{BASE}/fr-fr/emploi/metier_analyste-isr.html"]


def test_refus_arrete_la_passe_et_compte(monkeypatch, tmp_path):
    offres, appels = _scanner(
        monkeypatch,
        tmp_path,
        {
            "index-categorie": Reponse(
                '<div id="cf-error-details">Sorry, you have been blocked', 403
            )
        },
    )
    assert offres == [] and len(appels) == 1
    assert dict(J.INCIDENTS["hellowork"]) == {"HTTP 403": 1}
    J.INCIDENTS.clear()


def test_hors_de_collecte_complete():
    from jobhunter.sources import cli

    source = open(cli.__file__, encoding="utf-8").read()
    assert "if a.hellowork:" in source  # its own flag only, never `a.all or`
