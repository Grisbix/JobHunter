"""Jobs that make sense: sitemap, pre-filter on the slug, JobPosting of the page (sources.makesense).

Without network: bodies copied from the real structure of jobs.makesense.org on 2026-10-24.
"""

import datetime
import json

from conftest import Reponse

from jobhunter import sources as J
from jobhunter.sources import makesense as M

AUJ = datetime.date.today().isoformat()


def _url(slug):
    return f"https://jobs.makesense.org/fr/jobs/{slug}"


SLUG_ESG = "goodvest-sustainable-finance-analyst-hf-0cmJrU4rGMPmutpi4VXH"
SLUG_HORS = "acme-office-manager-hf-3VJAqBVv7A2QxrBouYhX"
SLUG_VIEUX = "acme-esg-analyst-hf-5VLzvXf7FIUebIlMAgm9"


def _sitemap():
    def bloc(slug, date, langue="fr"):
        return (
            f"<url>\n    <loc>https://jobs.makesense.org/{langue}/jobs/{slug}</loc>\n"
            f"    <lastmod>{date}</lastmod>\n  </url>"
        )

    return (
        '<?xml version="1.0"?><urlset>'
        + bloc(SLUG_ESG, AUJ)
        + bloc(SLUG_ESG, AUJ, "en")  # the English twin is not read twice
        + bloc(SLUG_HORS, AUJ)
        + bloc(SLUG_VIEUX, "2020-01-01")
        + "</urlset>"
    )


def _page(titre, lieu="Paris", pays="France"):
    jp = {
        "@context": "https://schema.org/",
        "@type": "JobPosting",
        "title": titre,
        "description": "<p>" + "Reporting SFDR et taxonomie. " * 10 + "</p>",
        "datePosted": "2026-10-20",
        "hiringOrganization": {"name": "Goodvest"},
        "jobLocation": {"address": {"addressLocality": lieu, "addressCountry": pays}},
    }
    return f'<html><script type="application/ld+json">{json.dumps(jp)}</script></html>'


def test_entrees_francaises_recentes_sans_doublon():
    e = M.entrees(_sitemap(), "2026-01-01")
    assert e == [(_url(SLUG_ESG), AUJ), (_url(SLUG_HORS), AUJ)]


def test_texte_du_slug_sans_identifiant():
    assert M.texte_du_slug(_url(SLUG_ESG)) == "goodvest sustainable finance analyst hf"


def test_fiche_lit_le_jobposting():
    assert M.fiche(_page("ESG Analyst"))["title"] == "ESG Analyst"
    assert M.fiche("<html>rien</html>") is None


def _scanner(monkeypatch, tmp_path, pages, limite=30):
    monkeypatch.setattr(J, "QUEUE", tmp_path / "apply_queue.json")
    monkeypatch.setattr(M, "MAKESENSE_PAUSE", 0)
    appels = []

    def envoi(_client, url, **kw):
        appels.append(url)
        for motif, rep in pages.items():
            if motif in url:
                return rep
        return Reponse("", 404)

    monkeypatch.setattr(J, "_get_borne", envoi)
    J.INCIDENTS.clear()
    return M.scan_makesense(limite=limite), appels


def test_scan_lit_seulement_les_offres_retenues(monkeypatch, tmp_path):
    offres, appels = _scanner(
        monkeypatch,
        tmp_path,
        {
            "sitemap-jobs.xml": Reponse(_sitemap()),
            SLUG_ESG: Reponse(_page("Sustainable Finance Analyst")),
        },
    )
    # The off-target and the old offer are never opened.
    assert appels == [M.MAKESENSE_SITEMAP, _url(SLUG_ESG)]
    assert [(o["titre"], o["entreprise"], o["url"]) for o in offres] == [
        ("Sustainable Finance Analyst", "Goodvest", _url(SLUG_ESG))
    ]
    assert "taxonomie" in offres[0]["description"]


def test_scan_refuse_titre_exact_hors_metier(monkeypatch, tmp_path):
    offres, _ = _scanner(
        monkeypatch,
        tmp_path,
        {"sitemap-jobs.xml": Reponse(_sitemap()), SLUG_ESG: Reponse(_page("Office Manager"))},
    )
    assert offres == []


def test_scan_s_arrete_sur_un_refus(monkeypatch, tmp_path):
    offres, _ = _scanner(
        monkeypatch,
        tmp_path,
        {"sitemap-jobs.xml": Reponse(_sitemap()), SLUG_ESG: Reponse("", 429)},
    )
    assert offres == []
    assert dict(J.INCIDENTS["makesense"]) == {"HTTP 429": 1}
    J.INCIDENTS.clear()


def test_sitemap_refuse_compte_comme_incident(monkeypatch, tmp_path):
    offres, appels = _scanner(monkeypatch, tmp_path, {"sitemap-jobs.xml": Reponse("", 403)})
    assert offres == [] and appels == [M.MAKESENSE_SITEMAP]
    assert dict(J.INCIDENTS["makesense"]) == {"HTTP 403": 1}
    J.INCIDENTS.clear()
