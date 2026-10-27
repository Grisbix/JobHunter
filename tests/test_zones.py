"""Zones, country, region and displayed place (zones) on REAL places from the queue.

Each case comes from a misfiled offer, measured on 2026-09-23: 409 offers were
wrongly in "the rest of France" (300 abroad, 53 in IDF, 56 in the
South-East). Without network. Converted from Scripts/test_zones.py.
"""

import pytest

from jobhunter.scoring.zones import (
    AILLEURS as A,
)
from jobhunter.scoring.zones import (
    INCONNU as U,
)
from jobhunter.scoring.zones import (
    INTERNATIONAL as I,
)
from jobhunter.scoring.zones import (
    PRIORITAIRE as P,
)
from jobhunter.scoring.zones import (
    SECONDAIRE as S,
)
from jobhunter.scoring.zones import (
    lieu_deduit,
    lieu_effectif,
    lieu_propre,
    pays_lieu,
    region_pays,
    reparer_lieu,
    sous_zone,
    ville_affichee,
    zone_lieu,
)

ZONES = [
    # countries written in English by LinkedIn
    ("Bogota, D.C., Capital District, Colombia", I),
    ("Santiago, Santiago Metropolitan Region, Chile", I),
    ("Bangkok, Bangkok City, Thailand", I),
    ("Sofia, Sofia City, Bulgaria", I),
    ("Tekirdağ, Türkiye", I),
    ("Colombia", I),
    # metropolises without a country
    ("Lisbon Metropolitan Area", I),
    ("Greater Milan Metropolitan Area", I),
    ("Greater Gothenburg Metropolitan Area", I),
    ("Cincinnati Metropolitan Area", I),
    ("Madrid, Remote", I),
    # ... but French metropolises stay French
    ("Greater Paris Metropolitan Region", P),
    ("Greater Lyon Area", S),
    ("Greater Lille Metropolitan Area", A),
    ("Greater Saint-Nazaire Area", A),
    # WTJ: "· France" is the site's, the country code tells the truth
    ("Genève · France", I),
    ("Zaventem, VLG, BE · France", I),
    ("Saint-Ouen, A8, FR · France", P),
    ("Biot, B8, FR · France", S),
    ("Vaulx-en-Velin, ARA, FR · France", S),
    ("Niort, NA, FR · France", A),
    # departments and postcodes
    ("Bobigny - 93", P),
    ("Melun - 77", P),
    ("Télétravail à 94710 Maisons-Alfort", P),
    ("Pessac - 33", P),
    ("Bron - 69", S),
    ("Cluses (74) · France", S),
    ("Télétravail partiel à 82710 Bressols", S),
    ("Nantes - 44", A),
    ("Le Lamentin - 972", A),
    ("97600 Mamoudzou · France", A),
    # a foreign postcode does not become a department
    ("Houston, TX 77002", I),
    ("San Diego, CA 92101", I),
    # communes seules
    ("Maisons-Alfort", P),
    ("Palaiseau", P),
    ("Martillac", P),
    ("Valbonne", S),
    ("Lattes", S),
    ("Mauguio Languedoc-Roussillon FR", S),
    ("Colomiers Midi-Pyrenees FR", S),
    ("Lezennes, Hauts-de-France, France", A),  # Lille suburb, not IDF
    # vague = unknown, never a rejection
    ("France", U),
    ("", U),
    ("Remote (FR)", U),
    ("All France (remote)", U),
    ("Europe", U),
    # non-regressions
    ("Paris, Île-de-France, France", P),
    ("Courbevoie", P),
    ("Singapore, Singapore", I),  # "sinGAPore" is not Gap
    ("Lille, Hauts-de-France, France", A),  # "de" is not Germany
    ("POINTE NOIRE (CONGO)", I),
    ("Chasseneuil-du-Poitou, Nouvelle-Aquitaine, France", A),
    ("Rotterdam, South Holland, Netherlands", I),
    ("Machine Learning Hub, Toulouse", S),  # "Chine" in "Machine"
    # homonymes d'IDF hors d'IDF
    ("Boulogne-sur-Mer", A),
    ("Boulogne Nord-Pas-de-Calais FR", A),
    ("Boulogne-Billancourt", P),
    ("Asnières, Normandy, France", A),
    ("Asnières-sur-Seine", P),
    ("Saint-Denis, Reunion", A),
    ("Saint-Denis", P),
]


@pytest.mark.parametrize(("lieu", "attendu"), ZONES)
def test_zone_lieu(lieu, attendu):
    assert zone_lieu(lieu) == attendu


# App label: Bordeaux and IDF share the zone, not the label.
@pytest.mark.parametrize(
    ("lieu", "attendu"),
    [
        ("Bordeaux, Nouvelle-Aquitaine, France", "bordeaux"),
        ("33700 Mérignac", "bordeaux"),
        ("Blanquefort - 33", "bordeaux"),
        ("Paris, Île-de-France, France", "idf"),
        ("Courbevoie", "idf"),
        ("Lyon", ""),
    ],
)
def test_sous_zone(lieu, attendu):
    assert sous_zone(lieu) == attendu


# App's Country filter: one French name per country, whatever the language.
@pytest.mark.parametrize(
    ("lieu", "attendu"),
    [
        ("Geneva, Geneva, Switzerland", "Suisse"),
        ("Zürich", "Suisse"),
        ("GLASGOW (ROYAUME-UNI)", "Royaume-Uni"),
        ("POINTE NOIRE (CONGO)", "Congo"),
        ("Zaventem, VLG, BE · France", "Belgique"),
        ("Houston, TX 77002", "États-Unis"),
        ("New York City Metropolitan Area", "États-Unis"),
        ("Mexico City, Mexico", "Mexique"),
        ("Bogota, Colombia", "Colombie"),
        ("Lisbon Metropolitan Area", "Portugal"),
        ("Paris, Île-de-France, France", "France"),
        ("Nantes - 44", "France"),
        ("Remote", "?"),
        # recheck of the queue on 2026-10-07
        ("France", "France"),
        ("All France (remote)", "France"),
        ("Birmingham, AL", "États-Unis"),
        ("New Orleans, LA", "États-Unis"),
        ("Dublin, OH", "États-Unis"),
        ("Rive-de-Gier", "France"),
        ("La Cañada, Querétaro, Mexico", "Mexique"),
        ("Mexicali, Baja California, Mexico", "Mexique"),
        ("Cerro Colorado, Arequipa, Peru", "Pérou"),
        ("Green Bay, Wisconsin Metropolitan Area", "États-Unis"),
        ("Albuquerque-Santa Fe Metropolitan Area", "États-Unis"),
        ("Delft Zuid-Holland NL", "Pays-Bas"),
        ("Arlington VA US", "États-Unis"),
        ("Port Louis, Mauritius", "Maurice"),
        ("Saint-Maurice-d’Ibie, Auvergne-Rhône-Alpes, France", "France"),
        ("Tbilisi, Georgia", "Géorgie"),
        ("Belfast", "Royaume-Uni"),
        ("Lahore, Punjab, Pakistan", "Pakistan"),
        ("Cracow Metropolitan Area", "Pologne"),
    ],
)
def test_pays_lieu(lieu, attendu):
    assert pays_lieu(lieu) == attendu


# Displayed place: the whole IDF becomes "Paris", the rest does not move.
@pytest.mark.parametrize(
    ("lieu", "attendu"),
    [
        ("La Défense - 92", "Paris"),
        ("Courbevoie", "Paris"),
        ("Greater Paris Metropolitan Region", "Paris"),
        ("Bordeaux, Nouvelle-Aquitaine, France", "Bordeaux, Nouvelle-Aquitaine, France"),
        ("Lyon", "Lyon"),
    ],
)
def test_ville_affichee(lieu, attendu):
    assert ville_affichee(lieu) == attendu


# Effective place: the title that names a foreign city wins over a French
# place ("VIE - New York" given "Paris" by an aggregator).
@pytest.mark.parametrize(
    ("titre", "lieu", "attendu"),
    [
        ("Forward Deployed Engineer (VIE - New York)", "Paris", "New York, États-Unis"),
        ("Forward Deployed Engineer (VIE - New York)", "Boston, MA", "Boston, MA"),
        ("Analyste ESG - couverture UK", "Paris", "Paris"),
        ("Analyste Marchés US", "Paris", "Paris"),
        ("Chargé RSE Porto-Vecchio", "Corse", "Corse"),
    ],
)
def test_lieu_effectif(titre, lieu, attendu):
    assert lieu_effectif(lieu, titre) == attendu


# App filter's region (2026-10-07).
@pytest.mark.parametrize(
    ("pays", "attendu"),
    [
        ("France", "Europe"),
        ("Royaume-Uni", "Europe"),
        ("États-Unis", "Amérique du Nord"),
        ("Mexique", "Amérique latine"),
        ("Singapour", "Asie"),
        ("Émirats arabes unis", "Moyen-Orient"),
        ("Gabon", "Afrique"),
        ("Australie", "Océanie"),
        ("?", "?"),
        ("étranger (autre)", "?"),
    ],
)
def test_region_pays(pays, attendu):
    assert region_pays(pays) == attendu


# Repeated segments (the user, 2026-10-27: "Luxembourg, Luxembourg, Luxembourg").
@pytest.mark.parametrize(
    ("lieu", "attendu"),
    [
        ("Luxembourg, Luxembourg, Luxembourg", "Luxembourg"),
        ("Kirchberg, Luxembourg, Luxembourg", "Kirchberg, Luxembourg"),
        ("Geneva, Geneva, Switzerland", "Geneva, Switzerland"),
        ("Singapore,  singapore", "Singapore"),
        ("Paris, Île-de-France, France", "Paris, Île-de-France, France"),
        ("", ""),
    ],
)
def test_lieu_propre(lieu, attendu):
    assert lieu_propre(lieu) == attendu


# Countries the filter showed as "étranger (autre)" (2026-10-27).
@pytest.mark.parametrize(
    ("lieu", "attendu"),
    [
        ("Milano, Provincia di Milano", "Italie"),
        ("Köln", "Allemagne"),
        ("Paço de Arcos, PT, 2770-131", "Portugal"),
        ("Timisoara, RO", "Roumanie"),
        ("Iskandar Puteri, 01, MY, 79250", "Malaisie"),
        ("US", "États-Unis"),
        ("Kuwait", "Koweït"),
        ("Toronto, ON, CA", "Canada"),
        ("Birmingham, AL", "États-Unis"),
        ("3 Locations", "?"),
    ],
)
def test_pays_lieu_codes_et_villes(lieu, attendu):
    assert pays_lieu(lieu) == attendu


def test_plusieurs_lieux_workday_inconnu():
    assert zone_lieu("3 Locations") == U


# A place the source did not give: from the text, else the address; never a guess.
@pytest.mark.parametrize(
    ("url", "description", "attendu"),
    [
        (
            "https://x.fr/offre/1",
            "Intro\nLocalisation du poste : Paris (75007)\nSuite",
            "Paris (75007)",
        ),
        ("https://x.eu/j/1", "Country\nItaly\nCity\nMILANO\n", "Milano, Italy"),
        ("https://x.eu/j/1", "City\nVienna\nCountry\nAustria", "Vienna, Austria"),
        (
            "https://x.com/c/1",
            "Consultant\n\n21 Rue de Berri, 75008 Paris, France\n\nI'm interested",
            "Paris, France",
        ),
        ("https://x.nl/v/1", "FEC Analyst\nNederland\nAmersfoort\n36-40", "Amersfoort, Nederland"),
        ("https://a.wd103.myworkdayjobs.com/acc/job/Lyon/Consultant_R1", "", "Lyon"),
        ("https://a.wd3.myworkdayjobs.com/acc/job/Analyst_Req1", "", ""),
        (
            "https://www.welcometothejungle.com/fr/companies/sg/jobs/conseiller_strasbourg_SG_Nb",
            "",
            "Strasbourg",
        ),
        ("https://recrute.fr/offre/data-analyst-fh-paris-2/", "", "Paris"),
        ("https://www.sia-partners.com/en/career/consultant-bureau-de-lyon", "", "Lyon"),
        ("https://www.efinancialcareers.fr/emploi-France-Paris-Consultant_DataOps.id1", "", ""),
        ("https://es.linkedin.com/jobs/view/analyst-at-zurich-insurance-4440748821", "", ""),
        (
            "https://www.linkfinance.fr/emploi?x=1",
            "Localisation\nEffacer tous les filtres\nPays de la Loire, Rezé",
            "",
        ),
        ("https://x.com/j/1", "Lieu : Brest, France Construisons ensemble un avenir", ""),
        ("https://lu.linkedin.com/jobs/view/supply-chain-esg-specialist-at-vodafone-1", "", ""),
    ],
)
def test_lieu_deduit(url, description, attendu):
    assert lieu_deduit(url, description) == attendu


def test_lieu_effectif_complete_le_lieu_absent():
    url = "https://a.wd103.myworkdayjobs.com/acc/job/Milano/Consultant_R1"
    assert lieu_effectif("", "Consultant", url, "") == "Milano"
    assert lieu_effectif("3 Locations", "Consultant", url, "") == "Milano (3 Locations)"
    assert lieu_effectif("Luxembourg, Luxembourg", "Analyst", url, "") == "Luxembourg"


def test_reparer_lieu_met_la_zone_a_jour():
    o = {
        "poste": "Analyste",
        "localisation": "",
        "zone": U,
        "url": "https://x.fr/o/1",
        "description": "Ville : Paris 15",
    }
    assert reparer_lieu(o) is True
    assert o["localisation"] == "Paris 15"
    assert o["zone"] == zone_lieu("Paris 15") != U
    assert reparer_lieu(o) is False
