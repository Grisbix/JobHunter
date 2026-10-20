"""A replacement link must lead to THE POSTING, not elsewhere (resolve_offer_links).

Real cases. The costliest: a Deloitte RESULTS page (`results.htm`)
accepted as a posting, which had replaced a LinkedIn link leading to the offer.
Converted from Scripts/test_offer_links.py.
"""

import pytest

from jobhunter.programs.resolve_offer_links import RX_OFFRE, RX_RECHERCHE, accepte, specificite


def verdict(url):
    """OFFRE only if the link carries an identifier AND is not a search."""
    return "REJET" if (RX_RECHERCHE.search(url) or not RX_OFFRE.search(url)) else "OFFRE"


@pytest.mark.parametrize(
    "url",
    [
        "https://www.deloitte.com/fr/fr/careers/content/job/results.htm",  # the real case
        "https://www.deloitte.com/fr/fr/careers/content/job/results",
        "https://x.com/jobs/search",
        "https://x.com/carriere/recherche/",
        "https://x.com/emploi/listing.html",
        "https://samse.fr/catalogsearch/result/?q=analyste",
        "https://effektiv.fr/?search_keyword=esg",
        "https://x.com/jobs?query=esg",
        # a slug without digits or hyphen is not an identifier
        "https://x.com/jobs/candidature",
        "https://x.com/offres/spontanee",
    ],
)
def test_recherche_ou_slug_rejete(url):
    assert verdict(url) == "REJET"


@pytest.mark.parametrize(
    "url",
    [
        "https://x.com/jobs/analyste-esg-h-f-12345",
        "https://x.com/offres/consultant-junior-esg-2026",
        "https://boards.greenhouse.io/sweep/jobs/4567890",
        "https://x.com/job/12345678",
        "https://jobs.lever.co/agicap/97f57bd6-c156-42cd-b67a-f770ed9a1b2c",
        "https://jobs.ashbyhq.com/alan/118f5ad8-5db5-48ec-940e-1a880b3c4d5e",
        "https://tikehaucapital.recruitee.com/o/alternant-esg-immobilier-durable",
    ],
)
def test_vraie_annonce_acceptee(url):
    assert verdict(url) == "OFFRE"


@pytest.mark.parametrize(
    ("base", "url", "titre", "texte", "attendu"),
    [
        (
            "https://axa-im.com",
            "https://group.bnpparibas/jobs/analyste-esg-123",
            "Analyste ESG",
            "analyste esg",
            False,
        ),
        (
            "https://x.com",
            "https://x.com/jobs/analyste-esg-h-f-9912",
            "Analyste ESG",
            "Analyste ESG chez X",
            True,
        ),
        (
            "https://x.com",
            "https://x.com/jobs/comptable-paie-4471",
            "Analyste ESG Climat",
            "Comptable paie",
            False,
        ),
        (
            "https://x.com",
            "https://boards.greenhouse.io/x/jobs/771122",
            "Analyste ESG",
            "Analyste ESG",
            True,
        ),
    ],
    ids=[
        "autre societe refusee",
        "meme societe et titre accepte",
        "autre offre refusee",
        "ATS connu accepte malgre le domaine",
    ],
)
def test_accepte(base, url, titre, texte, attendu):
    ok, _pourquoi = accepte(base, url, titre, texte)
    assert ok is attendu


def test_annonce_plus_specifique_que_accueil():
    assert specificite("https://x.com/jobs/analyste-esg-1234") > specificite("https://x.com")
