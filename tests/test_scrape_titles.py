"""The universal extraction of job offers (scrape_jobs.EXTRACT_OFFERS_JS), in a real browser.

recrutement.bpce.fr wraps the whole card in one link: title, brand, contract, city and a
"Découvrir" button. The link's text came out glued: "Chargé d'affaires … - CDIGroupe Crédit
CoopératifCDIGrenobleDécouvrir". Its heading is the title.
"""

from jobhunter.programs.scrape_jobs import EXTRACT_OFFERS_JS

_CARTE = (
    '<li><a class="c-offerLink" href="/job/{slug}"><div class="c-offerDefault">'
    '<h3 class="title-25 c-offer-title">{titre}</h3>'
    '<div class="c-offer-brand">Groupe Crédit Coopératif</div>'
    '<ul class="c-offer-infos"><li><i class="icon-contract"></i>CDI</li>'
    '<li><i class="icon-location"></i>{ville}</li></ul></div>'
    '<div class="c-offerHover"><div class="c-button">Découvrir</div></div></a></li>'
)


def test_titre_du_lien_carte_entiere_bpce(page):
    cartes = "".join(
        _CARTE.format(slug=s, titre=t, ville=v)
        for s, t, v in (
            ("charge-affaires", "Chargé d'affaires Personnes morales F/H", "Grenoble"),
            ("conseiller", "Conseiller Clientèle Particuliers (F/H)", "Lille"),
        )
    )
    page.set_content(f'<ul class="offer-list">{cartes}</ul>')
    offres = page.evaluate(EXTRACT_OFFERS_JS)
    assert [(o["title"], o["location"]) for o in offres] == [
        ("Chargé d'affaires Personnes morales F/H", "Grenoble"),
        ("Conseiller Clientèle Particuliers (F/H)", "Lille"),
    ]


def test_lien_sans_titre_interne_garde_son_texte(page):
    page.set_content(
        '<ul><li><a href="/job/a">Analyste ESG H/F</a></li>'
        '<li><a href="/job/b">Chargé de reporting extra-financier</a></li></ul>'
    )
    titres = [o["title"] for o in page.evaluate(EXTRACT_OFFERS_JS)]
    assert titres == ["Analyste ESG H/F", "Chargé de reporting extra-financier"]
