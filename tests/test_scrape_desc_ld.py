"""Postings whose page refuses the automated browser but serves its JobPosting block.

Measured 2026-10-24: jobs.makesense.org answers 403 to headless Chromium and 200 to the
plain request its own source makes; scrape_desc read 0 out of 2 of them. They are now
read the way the source reads them, before any browser.
"""

from conftest import Reponse

from jobhunter.programs import scrape_desc as sd

PAGE = (
    '<html><script type="application/ld+json">{"@type": "JobPosting", "title": "Dev", '
    '"description": "<p>' + "Vous développerez notre plateforme. " * 8 + '</p>"}</script></html>'
)


def test_makesense_lu_par_son_bloc_jobposting(faux_reseau):
    faux_reseau.routes({"jobs.makesense.org": PAGE})
    r = sd.fetch_api("https://jobs.makesense.org/fr/jobs/x-dev-123")
    assert r["ok"] and r["via"] == "ld+json"
    assert r["text"].startswith("Vous développerez notre plateforme.")
    assert "<p>" not in r["text"]


def test_refus_rien_et_pas_d_insistance(faux_reseau):
    faux_reseau.routes({"jobs.makesense.org": Reponse("Forbidden", 403)})
    assert sd.fetch_api("https://jobs.makesense.org/fr/jobs/x-dev-123") is None
    assert len(faux_reseau.appels) == 1


def test_autre_site_pas_concerne(faux_reseau):
    assert sd.fetch_api("https://boards.greenhouse.io/x/jobs/1") is None
    assert faux_reseau.appels == []
