"""jobhunter.scoring.zones — Where the user wants to work, and how to read it in a place.

Formerly Scripts/zones.py.

DECLARED PREFERENCE (2026-09-08): Bordeaux and Île-de-France first; the South-East
next; the rest of France without much interest.

WHAT THIS MODULE DOES NOT DO: touch the `fit`. The fit measures how well the JOB
fits; geography is another question, and mixing them would make both unreadable. A
perfect offer in Lille stays a perfect offer — it is simply badly located. The zone is
therefore a separate field, filterable and sortable in the app.

THREE TRAPS, all met in the real data:

  1. The Île-de-France communes appear ALONE. "Courbevoie" (17 times) contains neither
     "Paris" nor "Ile-de-France". Hence the _IDF_COMMUNES list.
  2. "France" on its own (74 offers) and the empty value (106) say NOTHING. Classing
     them "ailleurs" would set aside offers that may be in Paris: they count as
     "inconnu", never as a rejection.
  3. Accents and case vary ("Île-de-France", "ile de france", "ILE DE FRANCE"). We
     compare without accent or case.

Run:
  python -m jobhunter.scoring.zones            # distribution of the queue
  python -m jobhunter.scoring.zones --ecrire   # writes the `zone` field into each offer
"""

import argparse
import collections
import re
import sys
from collections.abc import Iterable
from typing import Any

from jobhunter import lazy as _paresseux
from jobhunter.text import sans_accent
from jobhunter.types import Offre

_ici = sys.modules[__name__]
# Values taken from the profile: computed on first read, not at import
# (jobhunter.lazy). In this module, they are read through `_ici.NAME`.
_PARESSEUX: _paresseux.Fabriques = {}


def __getattr__(nom: str) -> Any:
    return _paresseux.lire(_ici, _PARESSEUX, nom)


Secteur = dict[str, Any]  # cle, libelle, lieux, communes, departements, wtj


PRIORITAIRE = "prioritaire"  # priority sectors of the profile
SECONDAIRE = "secondaire"  # secondary sectors of the profile
AILLEURS = "ailleurs"  # rest of FRANCE
INTERNATIONAL = "international"
INCONNU = "inconnu"

# "ailleurs" used to designate the rest of France AND abroad, which
# mixed Lille and Singapore. Since the worldwide search, abroad has its
# own zone: moving to Nantes and moving to Hong Kong are not decided
# the same way.
ORDRE = {PRIORITAIRE: 0, SECONDAIRE: 1, INCONNU: 2, AILLEURS: 3, INTERNATIONAL: 4}

# Île-de-France communes seen in the queue, written without their region.
_IDF_COMMUNES = (
    "courbevoie",
    "puteaux",
    "nanterre",
    "levallois",
    "neuilly",
    "montrouge",
    "issy-les-moulineaux",
    "issy les moulineaux",
    "la defense",
    # "boulogne" alone took Boulogne-sur-Mer (Pas-de-Calais) for Île-de-France.
    "boulogne-billancourt",
    "boulogne billancourt",
    "saint-denis",
    "saint denis",
    "versailles",
    "creteil",
    "nanterre",
    "rueil",
    "clichy",
    "montreuil",
    "ivry",
    "vincennes",
    "malakoff",
    "gennevilliers",
    "asnieres",
    "colombes",
    "suresnes",
    "bagneux",
    "charenton",
    "pantin",
    "aubervilliers",
    "cergy",
    "massy",
    "orsay",
    "saclay",
    "evry",
    "guyancourt",
    "velizy",
    "antony",
    "vanves",
    "fontenay-sous-bois",
    "fontenay sous bois",
    "arcueil",
    "gonesse",
    "corbeil-essonnes",
    "corbeil essonnes",
    # Seen as "ailleurs" on 2026-09-23, without region or department.
    "maisons-alfort",
    "maisons alfort",
    "saint-ouen",
    "saint ouen",
    "bobigny",
    "noisy-le-grand",
    "vitry-sur-seine",
    "rungis",
    "la courneuve",
    "meudon",
    "sevres",
    "le plessis-robinson",
    "moissy-cramayel",
    "vaux-le-penil",
    "montevrain",
    "survilliers",
    "tremblay-en-france",
    "villepinte",
    "orly",
    "fresnes",
    "lisses",
    "melun",
    "les clayes-sous-bois",
    "saint-germain-les-arpajon",
    "baulne",
    "champs-sur-marne",
    "marne-la-vallee",
    "roissy",
    "nogent-sur-marne",
    "saint-cloud",
    "sartrouville",
    "poissy",
    "saint-quentin-en-yvelines",
    "trappes",
    "noisiel",
    "torcy",
    "bussy-saint-georges",
    "chessy",
    "serris",
    "palaiseau",
    "lognes",
    "cachan",
    "boissy-saint-leger",
    "pontoise",
    "andilly",
)

# A place that only says the country, or nothing: no information.
_VAGUE = (
    "",
    "france",
    "fr",
    "remote",
    "teletravail",
    "télétravail",
    "全国",
    "all france",
    "france entiere",
    "national",
    "all france (remote)",
    "remote (fr)",
    "hybride (fr) · france",
    "teletravail, fr · remote",
    "europe",
    "emea",
    "worldwide",
)


def _n(t: object) -> str:
    """Lower case, without accents, blanks collapsed."""
    return re.sub(r"\s+", " ", sans_accent(str(t or "")).lower()).strip()


# Foreign countries, as they appear at the END of a place: LinkedIn writes
# « Geneva, Geneva, Switzerland », « Rotterdam, South Holland, Netherlands ».
# job_sources' _RX_ETRANGER knows neither these countries nor these cities, so 34
# Geneva offers and 30 Rotterdam ones were stored in "the rest of
# France". We read the LAST segment, the one that carries the country.
_PAYS_ETRANGERS = {
    "switzerland",
    "suisse",
    "schweiz",
    "netherlands",
    "nederland",
    "pays-bas",
    "united kingdom",
    "uk",
    "england",
    "scotland",
    "wales",
    "royaume-uni",
    "ireland",
    "irlande",
    "eire",
    "belgium",
    "belgique",
    "belgie",
    "luxembourg",
    "germany",
    "deutschland",
    "allemagne",
    "spain",
    "espana",
    "espagne",
    "italy",
    "italia",
    "italie",
    "portugal",
    "poland",
    "polska",
    "pologne",
    "singapore",
    "singapour",
    "united states",
    "usa",
    "canada",
    "australia",
    "india",
    "china",
    "japan",
    "japon",
    "hong kong",
    "uae",
    "united arab emirates",
    "morocco",
    "maroc",
    "tunisia",
    "tunisie",
    "senegal",
    "sweden",
    "norway",
    "denmark",
    "finland",
    "austria",
    "czechia",
    "czech republic",
    "romania",
    "greece",
    "hungary",
    "turkey",
    "brazil",
    "bresil",
    "mexico",
    "mexique",
    "south africa",
    "israel",
    # FRENCH NAMES. The list was almost entirely English, because the
    # places came from LinkedIn. The Business France V.I.E offers, on the other hand,
    # are written in French: "Copenhague, Danemark" fell into "the rest of
    # France". A country must be recognised in both languages.
    "danemark",
    "suede",
    "norvege",
    "finlande",
    "islande",
    "autriche",
    "hongrie",
    "grece",
    "turquie",
    "chine",
    "inde",
    "australie",
    "coree",
    "coree du sud",
    "republique tcheque",
    "tchequie",
    "roumanie",
    "croatie",
    "slovaquie",
    "slovenie",
    "bulgarie",
    "lituanie",
    "lettonie",
    "estonie",
    "malte",
    "chypre",
    "ukraine",
    "russie",
    "argentine",
    "chili",
    "colombie",
    "perou",
    "vietnam",
    "thailande",
    "indonesie",
    "malaisie",
    "philippines",
    "nouvelle-zelande",
    "emirats arabes unis",
    "afrique du sud",
    "qatar",
    "arabie saoudite",
    "egypte",
    "kenya",
    "nigeria",
    "ghana",
    "algerie",
    "liban",
    "jordanie",
    "etats-unis",
    "royaume uni",
    "angleterre",
    "ecosse",
    "pays de galles",
    "irlande du nord",
    "taiwan",
    # Countries where V.I.E really send people. "POINTE NOIRE (CONGO)" fell
    # into "the rest of France": Business France writes the country between
    # parentheses, and none of these names was known.
    "congo",
    "gabon",
    "angola",
    "cameroun",
    "cote d'ivoire",
    "mozambique",
    "namibie",
    "ouganda",
    "tanzanie",
    "ethiopie",
    "zambie",
    "botswana",
    "madagascar",
    "maurice",
    "oman",
    "koweit",
    "bahrein",
    "azerbaidjan",
    "kazakhstan",
    "ouzbekistan",
    "pakistan",
    "bangladesh",
    "sri lanka",
    "birmanie",
    "cambodge",
    "laos",
    "papouasie",
    "fidji",
    "uruguay",
    "paraguay",
    "bolivie",
    "equateur",
    "venezuela",
    "panama",
    "costa rica",
    "guatemala",
    "cuba",
    "republique dominicaine",
    "serbie",
    "bosnie",
    "albanie",
    "macedoine",
    "montenegro",
    "moldavie",
    "georgie",
    "armenie",
    "belarus",
    "luxembourg ville",
    # ENGLISH NAMES, written by LinkedIn as the last segment. All of these
    # were missing: 28 offers in Bogota, 20 in Santiago were stored in "the
    # rest of France" (measured on 2026-09-23).
    "colombia",
    "chile",
    "peru",
    "argentina",
    "bolivia",
    "ecuador",
    "thailand",
    "indonesia",
    "malaysia",
    "south korea",
    "korea",
    "new zealand",
    "bulgaria",
    "serbia",
    "croatia",
    "slovakia",
    "slovenia",
    "lithuania",
    "latvia",
    "estonia",
    "russia",
    "egypt",
    "iraq",
    "iran",
    "saudi arabia",
    "kuwait",
    "bahrain",
    "jordan",
    "lebanon",
    "mongolia",
    "bosnia and herzegovina",
    "north macedonia",
    "albania",
    "moldova",
    "georgia",
    "armenia",
    "uzbekistan",
    "nepal",
    "cambodia",
    "myanmar",
    "ethiopia",
    "tanzania",
    "uganda",
    "rwanda",
    "cameroon",
    "ivory coast",
    "benin",
    "togo",
    "mali",
    "burkina faso",
    "algeria",
    "iceland",
    "cyprus",
    "malta",
    "dominican republic",
    "puerto rico",
    "jamaica",
    "trinidad",
    "turkiye",
    "suriname",
    "papua new guinea",
    # recruiting macro-regions: never France alone
    "namer",
    "latam",
    "apac",
    "sub-saharan africa",
    "middle east",
    "mena",
}

# Foreign cities written WITHOUT a country: LinkedIn says "Lisbon Metropolitan
# Area", "Greater Milan Metropolitan Area"; WTJ even sticks "· France" onto
# "Genève" or "Zurich". No country to read — the city is the only clue.
_VILLES_ETRANGERES = {
    "lisbon",
    "lisboa",
    "porto",
    "copenhagen",
    "stockholm",
    "oslo",
    "helsinki",
    "sao paulo",
    "rio de janeiro",
    "mumbai",
    "pune",
    "bangalore",
    "bengaluru",
    "delhi",
    "hyderabad",
    "chennai",
    "turin",
    "milan",
    "rome",
    "naples",
    "bologna",
    "basel",
    "bale",
    "bern",
    "berne",
    "zurich",
    "geneva",
    "geneve",
    "lausanne",
    "eindhoven",
    "utrecht",
    "rotterdam",
    "the hague",
    "amsterdam",
    "uden-veghel",
    "kuala lumpur",
    "jakarta",
    "bangkok",
    "manila",
    "seoul",
    "tokyo",
    "shanghai",
    "beijing",
    "shenzhen",
    "dubai",
    "abu dhabi",
    "doha",
    "riyadh",
    "cairo",
    "montreal",
    "ottawa",
    "vancouver",
    "calgary",
    "houston",
    "chicago",
    "boston",
    "los angeles",
    "seattle",
    "salt lake city",
    "dallas",
    "atlanta",
    "miami",
    "lima",
    "bogota",
    "medellin",
    "santiago",
    "buenos aires",
    "mexico city",
    "asuncion",
    "dakar",
    "tunis",
    "abidjan",
    "casablanca",
    "rabat",
    "nairobi",
    "lagos",
    "accra",
    "johannesburg",
    "cape town",
    "malaga",
    "valencia",
    "sevilla",
    "bilbao",
    "zaventem",
    "oostende",
    "antwerp",
    "anvers",
    "gent",
    "gand",
    "liege",
    "stoke-on-trent",
    "birmingham",
    "leeds",
    "edinburgh",
    "glasgow",
    "bristol",
    "vienna",
    "prague",
    "warsaw",
    "krakow",
    "budapest",
    "bucharest",
    "sofia",
    "belgrade",
    "zagreb",
    "vilnius",
    "riga",
    "tallinn",
    "athens",
    "istanbul",
    "madrid",
    "barcelona",
    "kortrijk",
    "cologne",
    "karlsruhe",
    "enschede",
}

# The FORMAT of LinkedIn metropolitan areas — "Greater X Area", "X Metropolitan
# Area/Region", "Greater X", "X Metro" — is used mostly outside France: the
# list of cities would never end (Gothenburg, Cincinnati, Surabaya…).
# So we read it as a foreign clue, UNLESS a French city is
# reconnue : LinkedIn ecrit aussi « Greater Lille Metropolitan Area ».
_RX_METRO = re.compile(r"^greater\s|\s(metropolitan\s(area|region)|metro|area|region)$")
_METROS_FR = (
    "saint-nazaire",
    "saint nazaire",
    "le havre",
    "mulhouse",
    "valenciennes",
    "dunkerque",
    "pau",
    "bayonne",
    "la rochelle",
    "poitiers",
    "le mans",
    "saint-brieuc",
    "lorient",
    "vannes",
    "quimper",
    "niort",
    "angouleme",
    "troyes",
    "chartres",
    "brive",
    "cherbourg",
    "calais",
    "boulogne-sur-mer",
)

# « Bobigny - 93 », « Cluses (74) », « 94710 Maisons-Alfort ». Outre-mer : 97x/98x.
_RX_DEP = re.compile(
    r"(?:\s-\s*|\()(9[78]\d|\d{2}|2[ab])\)?\s*(?:·|$)"
    r"|(?<!\d)(?:(9[78]\d)\d{2}|(\d{2})\d{3})(?!\d)"
)
# « Muret, Haute-Garonne » names its department without its number. Normalised
# names (_n). Left out, because they are also a city, a region's piece or a common
# word: Ain, Aube, Cher, Eure, Gers, Indre, Loire, Lot, Manche, Marne, Nord, Oise,
# Orne, Paris, Rhône, Savoie, Somme, Var, Vienne (Austria).
_DEPARTEMENTS_NOMMES = {
    "aisne": "02", "allier": "03", "alpes-de-haute-provence": "04", "hautes-alpes": "05",
    "alpes-maritimes": "06", "ardeche": "07", "ardennes": "08", "ariege": "09",
    "aude": "11", "aveyron": "12", "bouches-du-rhone": "13", "calvados": "14",
    "cantal": "15", "charente": "16", "charente-maritime": "17", "correze": "19",
    "corse-du-sud": "2a", "haute-corse": "2b", "cote-d'or": "21", "cotes-d'armor": "22",
    "creuse": "23", "dordogne": "24", "doubs": "25", "drome": "26", "eure-et-loir": "28",
    "finistere": "29", "gard": "30", "haute-garonne": "31", "gironde": "33",
    "herault": "34", "ille-et-vilaine": "35", "indre-et-loire": "37", "isere": "38",
    "jura": "39", "landes": "40", "loir-et-cher": "41", "haute-loire": "43",
    "loire-atlantique": "44", "loiret": "45", "lot-et-garonne": "47", "lozere": "48",
    "maine-et-loire": "49", "haute-marne": "52", "mayenne": "53",
    "meurthe-et-moselle": "54", "meuse": "55", "morbihan": "56", "moselle": "57",
    "nievre": "58", "pas-de-calais": "62", "puy-de-dome": "63",
    "pyrenees-atlantiques": "64", "hautes-pyrenees": "65", "pyrenees-orientales": "66",
    "bas-rhin": "67", "haut-rhin": "68", "haute-saone": "70", "saone-et-loire": "71",
    "sarthe": "72", "haute-savoie": "74", "seine-maritime": "76", "seine-et-marne": "77",
    "yvelines": "78", "deux-sevres": "79", "tarn": "81", "tarn-et-garonne": "82",
    "vaucluse": "84", "vendee": "85", "haute-vienne": "87", "vosges": "88", "yonne": "89",
    "territoire de belfort": "90", "essonne": "91", "hauts-de-seine": "92",
    "seine-saint-denis": "93", "val-de-marne": "94", "val-d'oise": "95",
}  # fmt: skip
# Longest first: « haute-garonne » before a shorter name it contains.
_RX_DEP_NOMME = re.compile(
    r"(?<![a-z0-9-])("
    + "|".join(re.escape(k) for k in sorted(_DEPARTEMENTS_NOMMES, key=len, reverse=True))
    + r")(?![a-z0-9-])"
)
# Code de region WTJ : « Saint-Ouen, A8, FR », « Biot, B8, FR », « …, ARA, FR ».
_RX_REGION_WTJ = re.compile(r",\s*([a-z0-9]{1,3})\s*,\s*([a-z]{2})\b")

# Overseas: France, but not a target. Tested BEFORE the communes:
# "Saint-Denis, Reunion" is the capital of La Réunion, not the 93.
_OUTRE_MER = (
    "reunion",
    "la reunion",
    "guadeloupe",
    "martinique",
    "guyane",
    "mayotte",
    "nouvelle-caledonie",
    "nouvelle caledonie",
    "noumea",
    "polynesie",
    "tahiti",
    "saint-pierre-et-miquelon",
    "saint-martin",
)

# French regions OUTSIDE the target. A homonymous Île-de-France commune does not count there:
# "Asnières, Normandy" is not Asnières-sur-Seine.
_REGIONS_AUTRES = (
    "normandy",
    "normandie",
    "hauts-de-france",
    "nord-pas-de-calais",
    "bretagne",
    "brittany",
    "pays de la loire",
    "grand est",
    "centre-val de loire",
    "bourgogne",
    "franche-comte",
    "nouvelle-aquitaine",
    "picardie",
    "lorraine",
    "alsace",
    "champagne",
)

# ── SECTEURS GEOGRAPHIQUES ───────────────────────────────────────────────────
# The profile ("zones" section) chooses its PRIORITY and
# SECONDARY sectors in this catalogue, by their key. Each sector: a label,
# place names (communes, metropolis, region), departments and WTJ region
# codes. A sector missing from the catalogue is declared in the profile:
#     "zones": {"prioritaires": ["lyon", {"cle": "chambery", "libelle": "Chambéry",
#                                         "lieux": ["chambery", "aix-les-bains"],
#                                         "departements": ["73"]}]}
#
# A METROPOLIS is not its region: "Chasseneuil-du-Poitou, Nouvelle-
# Aquitaine" is not Bordeaux, the region stretches four hours' drive away.
# A region name is not a place.
_IDF = (
    "ile-de-france",
    "ile de france",
    "paris",
    "greater paris",
    "hauts-de-seine",
    "seine-saint-denis",
    "val-de-marne",
    "yvelines",
    "essonne",
    "val-d'oise",
    "seine-et-marne",
)

CATALOGUE = {
    "idf": {
        "libelle": "Île-de-France",
        "lieux": _IDF,
        "communes": _IDF_COMMUNES,
        "departements": {"75", "77", "78", "91", "92", "93", "94", "95"},
        "wtj": {"a8", "idf"},
    },
    "bordeaux": {
        "libelle": "Bordeaux",
        "departements": {"33"},
        "lieux": (
            "bordeaux",
            "gironde",
            "merignac",
            "mérignac",
            "pessac",
            "talence",
            "begles",
            "bègles",
            "saint-loubes",
            "saint loubes",
            "libourne",
            "arcachon",
            "cestas",
            "le haillan",
            "eysines",
            "bruges",
            "villenave",
            "gradignan",
            "cenon",
            "floirac",
            "lormont",
            "martillac",
            "canejan",
            "blanquefort",
            "saint-medard-en-jalles",
            "le bouscat",
        ),
    },
    "paca": {
        "libelle": "PACA",
        "departements": {"04", "05", "06", "13", "83", "84"},
        "wtj": {"b8"},
        "lieux": (
            "provence",
            "alpes-cote d'azur",
            "alpes cote d'azur",
            "paca",
            "marseille",
            "aix-en-provence",
            "aix en provence",
            "nice",
            "toulon",
            "avignon",
            "cannes",
            "antibes",
            "gap",
            "digne",
            "valbonne",
            "sophia antipolis",
            "sophia-antipolis",
            "biot",
            "bouc-bel-air",
            "peymeinade",
            "port-saint-louis-du-rhone",
            "saint-paul-les-durance",
            "cadarache",
            "vitrolles",
            "marignane",
            "la ciotat",
            "aubagne",
            "sophia",
            "grasse",
            "menton",
            "frejus",
            "hyeres",
        ),
    },
    "auvergne-rhone-alpes": {
        "libelle": "Auvergne-Rhône-Alpes",
        "departements": {"01", "03", "07", "15", "26", "38", "42", "43", "63", "69", "73", "74"},
        "wtj": {"ara", "v1", "b9", "a7"},
        "lieux": (
            "auvergne-rhone-alpes",
            "auvergne rhone alpes",
            "rhone-alpes",
            "rhone alpes",
            "lyon",
            "grenoble",
            "saint-etienne",
            "saint etienne",
            "annecy",
            "chambery",
            "valence",
            "clermont-ferrand",
            "clermont ferrand",
            "villeurbanne",
            "vienne",
            "bourg-en-bresse",
            "bourg en bresse",
            "limonest",
            "ecully",
            "dardilly",
            "rillieux-la-pape",
            "vaulx-en-velin",
            "saint-priest",
            "genay",
            "fontanil-cornillon",
            "bron",
            "crolles",
            "gieres",
            "meylan",
            "cluses",
        ),
    },
    "occitanie": {
        "libelle": "Occitanie",
        "departements": {
            "09",
            "11",
            "12",
            "30",
            "31",
            "32",
            "34",
            "46",
            "48",
            "65",
            "66",
            "81",
            "82",
        },
        "wtj": {"o", "occ", "b2"},
        "lieux": (
            "occitanie",
            "montpellier",
            "nimes",
            "perpignan",
            "toulouse",
            "beziers",
            "sete",
            "carcassonne",
            "albi",
            "tarbes",
            "languedoc-roussillon",
            "languedoc roussillon",
            "midi-pyrenees",
            "midi pyrenees",
            "lattes",
            "mauguio",
            "labege",
            "quint-fonsegrives",
            "colomiers",
            "blagnac",
            "montauban",
            "castelnau-le-lez",
        ),
    },
    "corse": {
        "libelle": "Corse",
        "departements": {"2a", "2b", "20"},
        "lieux": ("corse", "ajaccio", "bastia"),
    },
    # Metropolises and regions, for a profile that searches elsewhere.
    "lyon": {
        "libelle": "Lyon",
        "departements": {"69"},
        "lieux": (
            "lyon",
            "villeurbanne",
            "venissieux",
            "bron",
            "ecully",
            "limonest",
            "dardilly",
            "saint-priest",
            "vaulx-en-velin",
            "rillieux-la-pape",
            "caluire",
        ),
    },
    "lille": {
        "libelle": "Lille",
        "departements": {"59"},
        "lieux": (
            "lille",
            "roubaix",
            "tourcoing",
            "villeneuve-d'ascq",
            "villeneuve d'ascq",
            "marcq-en-baroeul",
            "lambersart",
            "lomme",
        ),
    },
    "nantes": {
        "libelle": "Nantes",
        "departements": {"44"},
        "lieux": ("nantes", "saint-herblain", "reze", "carquefou", "saint-nazaire", "orvault"),
    },
    "toulouse": {
        "libelle": "Toulouse",
        "departements": {"31"},
        "lieux": ("toulouse", "blagnac", "colomiers", "labege", "balma", "tournefeuille"),
    },
    "marseille": {
        "libelle": "Marseille",
        "departements": {"13"},
        "lieux": (
            "marseille",
            "aix-en-provence",
            "aix en provence",
            "aubagne",
            "vitrolles",
            "marignane",
            "la ciotat",
        ),
    },
    "strasbourg": {
        "libelle": "Strasbourg",
        "departements": {"67"},
        "lieux": ("strasbourg", "schiltigheim", "illkirch", "bas-rhin"),
    },
    "rennes": {
        "libelle": "Rennes",
        "departements": {"35"},
        "lieux": ("rennes", "cesson-sevigne", "ille-et-vilaine"),
    },
    "montpellier": {
        "libelle": "Montpellier",
        "departements": {"34"},
        "lieux": ("montpellier", "lattes", "mauguio", "castelnau-le-lez"),
    },
    "nice": {
        "libelle": "Nice",
        "departements": {"06"},
        "lieux": (
            "nice",
            "sophia antipolis",
            "sophia-antipolis",
            "valbonne",
            "antibes",
            "cannes",
            "biot",
            "grasse",
            "menton",
        ),
    },
    "grenoble": {
        "libelle": "Grenoble",
        "departements": {"38"},
        "lieux": ("grenoble", "meylan", "crolles", "gieres", "echirolles", "isere"),
    },
    "hauts-de-france": {
        "libelle": "Hauts-de-France",
        "departements": {"02", "59", "60", "62", "80"},
        "lieux": ("hauts-de-france", "nord-pas-de-calais", "picardie", "lille", "amiens"),
    },
    "bretagne": {
        "libelle": "Bretagne",
        "departements": {"22", "29", "35", "56"},
        "lieux": ("bretagne", "brittany", "rennes", "brest", "lorient", "vannes", "quimper"),
    },
    "pays-de-la-loire": {
        "libelle": "Pays de la Loire",
        "departements": {"44", "49", "53", "72", "85"},
        "lieux": ("pays de la loire", "nantes", "angers", "le mans"),
    },
    "grand-est": {
        "libelle": "Grand Est",
        "departements": {"08", "10", "51", "52", "54", "55", "57", "67", "68", "88"},
        "lieux": (
            "grand est",
            "alsace",
            "lorraine",
            "champagne",
            "strasbourg",
            "metz",
            "nancy",
            "reims",
            "mulhouse",
        ),
    },
    "normandie": {
        "libelle": "Normandie",
        "departements": {"14", "27", "50", "61", "76"},
        "lieux": ("normandie", "normandy", "rouen", "caen", "le havre"),
    },
    "nouvelle-aquitaine": {
        "libelle": "Nouvelle-Aquitaine",
        "departements": {"16", "17", "19", "23", "24", "33", "40", "47", "64", "79", "86", "87"},
        "lieux": (
            "nouvelle-aquitaine",
            "bordeaux",
            "limoges",
            "poitiers",
            "pau",
            "bayonne",
            "la rochelle",
        ),
    },
    "centre-val-de-loire": {
        "libelle": "Centre-Val de Loire",
        "departements": {"18", "28", "36", "37", "41", "45"},
        "lieux": ("centre-val de loire", "orleans", "tours"),
    },
    "bourgogne-franche-comte": {
        "libelle": "Bourgogne-Franche-Comté",
        "departements": {"21", "25", "39", "58", "70", "71", "89", "90"},
        "lieux": ("bourgogne", "franche-comte", "dijon", "besancon"),
    },
}
# The catalogue holds two kinds of sector: a whole region, or a city with the towns
# around it. Toulouse is in Occitanie, Occitanie is not in Toulouse: the screen says
# which kind each one is (genre_secteur).
REGIONS = frozenset(
    {
        "idf",
        "paca",
        "auvergne-rhone-alpes",
        "occitanie",
        "corse",
        "hauts-de-france",
        "bretagne",
        "pays-de-la-loire",
        "grand-est",
        "normandie",
        "nouvelle-aquitaine",
        "centre-val-de-loire",
        "bourgogne-franche-comte",
    }
)


def genre_secteur(cle: str) -> str:
    """Kind of sector: "region" for a whole region, "ville" for a city and its towns."""
    return "region" if cle in REGIONS else "ville"


def _secteur(x: object) -> Secteur | None:
    """Sector of the catalogue (by key) or declared in the profile (dict)."""
    if isinstance(x, dict):
        return {
            "cle": x.get("cle") or _n(x.get("libelle", "")),
            "libelle": x.get("libelle", ""),
            "lieux": tuple(_n(v) for v in x.get("lieux") or ()),
            "communes": (),
            "departements": set(x.get("departements") or ()),
            "wtj": set(x.get("wtj") or ()),
        }
    c = CATALOGUE.get(str(x).lower())
    if c is None:
        return None
    return {
        "cle": str(x).lower(),
        "libelle": c["libelle"],
        "lieux": tuple(c.get("lieux", ())),
        "communes": tuple(c.get("communes", ())),
        "departements": set(c.get("departements", ())),
        "wtj": set(c.get("wtj", ())),
    }


def _secteurs(cle_profil: str, defaut: list[Any]) -> list[Secteur]:
    try:
        from jobhunter import profile as _P

        brut = _P.get(f"zones.{cle_profil}", defaut)
    except Exception:
        brut = defaut
    return [s for s in (_secteur(x) for x in (brut or [])) if s]


_PARESSEUX["SECTEURS_PRIORITAIRES"] = lambda: _secteurs("prioritaires", [])
_PARESSEUX["SECTEURS_SECONDAIRES"] = lambda: _secteurs("secondaires", [])
_PARESSEUX["_DEP_PRIORITAIRE"] = lambda: set().union(
    *(s["departements"] for s in _ici.SECTEURS_PRIORITAIRES)
)
_PARESSEUX["_DEP_SUD_EST"] = lambda: set().union(
    *(s["departements"] for s in _ici.SECTEURS_SECONDAIRES)
)
_PARESSEUX["_WTJ_PRIORITAIRE"] = lambda: set().union(
    *(s["wtj"] for s in _ici.SECTEURS_PRIORITAIRES)
)
_PARESSEUX["_WTJ_SUD_EST"] = lambda: set().union(*(s["wtj"] for s in _ici.SECTEURS_SECONDAIRES))


def _dans_secteur(t: str, s: Secteur) -> bool:
    """Does the normalised place `t` name the sector `s`? (IDF communes: not if another region is named — "Asnières, Normandy")."""
    if s["lieux"] and _contient(t, s["lieux"]):
        return True
    return bool(s["communes"]) and _contient(t, s["communes"]) and not _contient(t, _REGIONS_AUTRES)


_RX_CACHE: dict[object, re.Pattern[str]] = {}  # key: the tuple, or its id()


def _contient(t: str, tokens: Iterable[str]) -> bool:
    """Does one of the `tokens` appear as a WHOLE WORD in `t`?

    The substring comparison put "Singapore" in the South-East: "sinGAPore" contains
    "gap". Same family as the false positives already fixed elsewhere ("RSE" in
    "diveRSE", "climat" in "climatisation"). Word boundaries remove the whole class.
    """
    # Key = the tuple ITSELF when it is hashable. id() is only valid for the
    # module constants: a freed temporary tuple gives back its address, the
    # next one takes it and inherits the other's pattern. `_contient(t, (v,))`
    # in a loop thus answered with the previous city's pattern.
    cle = tokens if isinstance(tokens, (tuple, frozenset)) else id(tokens)
    rx = _RX_CACHE.get(cle)
    if rx is None:
        motif = "|".join(re.escape(k.strip()) for k in tokens if k.strip())
        rx = _RX_CACHE[cle] = re.compile(r"(?<![a-z0-9])(?:" + motif + r")(?![a-z0-9])")
    return bool(rx.search(t))


def _departement(t: str) -> str | None:
    """Department number read in the normalised place, or None."""
    m = _RX_DEP.search(t)
    if not m:
        nomme = _RX_DEP_NOMME.search(t)
        return _DEPARTEMENTS_NOMMES[nomme.group(1)] if nomme else None
    d = next(g for g in m.groups() if g)
    # A 5-digit postcode does not start with 00; "20xxx" is Corsica.
    return None if d == "00" else d


# The WHOLE place is "City, ST" with a state code in capitals.
_RX_VILLE_ETAT = re.compile(
    r"^[^,]+,\s*(AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|MA|MD|ME|MI"
    r"|MN|MO|MS|MT|NC|ND|NE|NH|NJ|NM|NV|NY|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VA"
    r"|VT|WA|WI|WV|WY|DC)(?:\s+\d{5})?\s*$"
)


def _code_etranger(job_sources: Any, lieu: str) -> bool:
    """_RX_ETRANGER, without taking a particle for a country code: its pattern is case-insensitive, and "Rive-de-Gier" became Germany in it ("de").

    A two-letter code only counts in CAPITALS and outside a compound name
    ("Düsseldorf … DE" yes, "-de-" no).
    """
    for m in job_sources._RX_ETRANGER.finditer(lieu):
        s = m.group(0)
        if len(s) != 2:
            return True
        avant, apres = lieu[m.start() - 1 : m.start()], lieu[m.end() : m.end() + 1]
        if s.isupper() and avant != "-" and apres != "-":
            return True
    return False


_RX_N_LIEUX = re.compile(r"\d+ (?:locations?|lieux|sites|standorte)")


def zone_lieu(lieu: str | None) -> str:
    """Zone of a place: prioritaire / sud-est / ailleurs / international / inconnu.

    Order: target French names, then foreign clues, THEN department. The department
    comes after abroad because an American postcode ("Houston, TX 77002") read as a
    department would give "Seine-et-Marne".
    """
    t = _n(lieu)
    # Workday's "3 Locations" names no place: it was read as the rest of France.
    if t in _VAGUE or not t or _RX_N_LIEUX.fullmatch(t):
        return INCONNU
    # American "City, ST" BEFORE the French names: "New Orleans, LA"
    # was stored in France because of "Orleans" (2026-10-07).
    if _RX_VILLE_ETAT.match(lieu or ""):
        return INTERNATIONAL
    wtj = _RX_REGION_WTJ.search(t)
    reg, pays = (wtj.group(1), wtj.group(2)) if wtj else ("", "")
    # The profile's sectors first: they are the declared targets. Overseas
    # before everything: "Saint-Denis, Reunion" is not the 93.
    if _contient(t, _OUTRE_MER):
        return AILLEURS
    if any(_dans_secteur(t, s) for s in _ici.SECTEURS_PRIORITAIRES) or (
        pays == "fr" and reg in _ici._WTJ_PRIORITAIRE
    ):
        return PRIORITAIRE
    if any(_dans_secteur(t, s) for s in _ici.SECTEURS_SECONDAIRES) or (
        pays == "fr" and reg in _ici._WTJ_SUD_EST
    ):
        return SECONDAIRE
    # WTJ country code other than FR: "Zaventem, VLG, BE · France". The final
    # "France" is the site's, not the place's.
    if pays and pays != "fr":
        return INTERNATIONAL
    # WHEREVER THE COUNTRY IS IN THE STRING. LinkedIn puts it as the last
    # segment ("Geneva, Geneva, Switzerland") but Business France puts it
    # between PARENTHESES ("POINTE NOIRE (CONGO)"): reading only the final
    # segment stored Congo and Gabon in "the rest of France".
    # So we look for the country everywhere, as a whole word — the word boundary prevents
    # "Inde" from matching "Indre" or "Chine" from matching "Machine".
    if _contient(t, _PAYS_ETRANGERS) or _contient(t, _VILLES_ETRANGERES):
        return INTERNATIONAL
    # Any country of the Country filter, not only those of _PAYS_ETRANGERS: without
    # that "Port Louis, Mauritius" ended up "elsewhere in France".
    if _contient(t, _PAYS_TOUS) or _contient(t, _VILLES_TOUTES):
        return INTERNATIONAL
    if _RX_METRO.search(t) and not _contient(t, _METROS_FR):
        try:
            from jobhunter.sources import common as job_sources

            if not job_sources._RX_FR.search(lieu or ""):
                return INTERNATIONAL
        except Exception:
            pass
    # France or abroad? We rely on job_sources' detector, the only
    # place where the lists of countries and American state codes live.
    # Late import: job_sources imports zones to label on addition.
    try:
        from jobhunter.sources import common as job_sources

        # FRANCE IS TESTED FIRST. _RX_ETRANGER contains the country code
        # "de", which matches the "de" of "Hauts-de-France": Lille and Nantes
        # partaient a l'international.
        francais = bool(job_sources._RX_FR.search(lieu or ""))
        # en_france() returns True for EVERYTHING when the worldwide search is
        # active — so we ask the patterns directly.
        etranger = not francais and bool(
            job_sources._RX_ETAT_US.search(lieu or "") or _code_etranger(job_sources, lieu or "")
        )
    except Exception:
        etranger = False
    if etranger:
        return INTERNATIONAL
    # Department: only 75 and 92 were known, as tokens. "Bobigny - 93",
    # "Melun - 77" or "Bron - 69" fell into "the rest of France".
    d = _departement(t)
    if d in _ici._DEP_PRIORITAIRE:
        return PRIORITAIRE
    if d in _ici._DEP_SUD_EST:
        return SECONDAIRE
    return AILLEURS


def sous_zone(lieu: str | None) -> str:
    """For a PRIORITY offer: "bordeaux" or "idf". Otherwise ''.

    The two targets share a zone (same sorting priority), but not a label: the app
    displayed "1 · Bordeaux/IDF" on 1275 offers of which only 56 were in Bordeaux —
    the user read "Bordeaux" on Paris.
    """
    if zone_lieu(lieu) != PRIORITAIRE:
        return ""
    t = _n(lieu)
    d = _departement(t)
    for s in _ici.SECTEURS_PRIORITAIRES:
        if _dans_secteur(t, s) or (d and d in s["departements"]):
            return str(s["cle"])
    return str(_ici.SECTEURS_PRIORITAIRES[0]["cle"]) if _ici.SECTEURS_PRIORITAIRES else ""


def libelle_secteur(cle: str) -> str:
    """The label ("Paris", "Bordeaux"…) of a key returned by sous_zone."""
    for s in _ici.SECTEURS_PRIORITAIRES + _ici.SECTEURS_SECONDAIRES:
        if s["cle"] == cle:
            return str(s["libelle"])
    return cle


# ── Country of a place, for the app's "Pays" filter (2026-10-05) ─────────────
# One canonical name per country, in French, whatever the language of the place:
# "Switzerland", "Suisse" and "Schweiz" must fall into the same box
# of the filter, otherwise three boxes have to be ticked for a single country.
_PAYS_CANON = {
    "Suisse": ("switzerland", "suisse", "schweiz"),
    "Pays-Bas": ("netherlands", "nederland", "pays-bas"),
    "Royaume-Uni": (
        "united kingdom",
        "uk",
        "england",
        "scotland",
        "wales",
        "royaume-uni",
        "royaume uni",
        "angleterre",
        "ecosse",
        "pays de galles",
        "irlande du nord",
    ),
    "Irlande": ("ireland", "irlande", "eire"),
    "Belgique": ("belgium", "belgique", "belgie"),
    "Luxembourg": ("luxembourg", "luxembourg ville"),
    "Allemagne": ("germany", "deutschland", "allemagne"),
    "Espagne": ("spain", "espana", "espagne"),
    "Italie": ("italy", "italia", "italie"),
    "Portugal": ("portugal",),
    "Pologne": ("poland", "polska", "pologne"),
    "Singapour": ("singapore", "singapour"),
    "États-Unis": ("united states", "usa", "etats-unis"),
    "Canada": ("canada",),
    "Australie": ("australia", "australie"),
    "Inde": ("india", "inde"),
    "Chine": ("china", "chine"),
    "Japon": ("japan", "japon"),
    "Hong Kong": ("hong kong",),
    "Taïwan": ("taiwan",),
    "Émirats arabes unis": ("uae", "united arab emirates", "emirats arabes unis"),
    "Maroc": ("morocco", "maroc"),
    "Tunisie": ("tunisia", "tunisie"),
    "Sénégal": ("senegal",),
    "Suède": ("sweden", "suede"),
    "Norvège": ("norway", "norvege"),
    "Danemark": ("denmark", "danemark"),
    "Finlande": ("finland", "finlande"),
    "Autriche": ("austria", "autriche"),
    "Tchéquie": ("czechia", "czech republic", "republique tcheque", "tchequie"),
    "Roumanie": ("romania", "roumanie"),
    "Grèce": ("greece", "grece"),
    "Hongrie": ("hungary", "hongrie"),
    "Turquie": ("turkey", "turquie", "turkiye"),
    "Brésil": ("brazil", "bresil"),
    "Mexique": ("mexico", "mexique"),
    "Afrique du Sud": ("south africa", "afrique du sud"),
    "Israël": ("israel",),
    "Corée du Sud": ("south korea", "korea", "coree", "coree du sud"),
    "Croatie": ("croatia", "croatie"),
    "Slovaquie": ("slovakia", "slovaquie"),
    "Slovénie": ("slovenia", "slovenie"),
    "Bulgarie": ("bulgaria", "bulgarie"),
    "Lituanie": ("lithuania", "lituanie"),
    "Lettonie": ("latvia", "lettonie"),
    "Estonie": ("estonia", "estonie"),
    "Malte": ("malta", "malte"),
    "Chypre": ("cyprus", "chypre"),
    "Ukraine": ("ukraine",),
    "Russie": ("russia", "russie"),
    "Argentine": ("argentina", "argentine"),
    "Chili": ("chile", "chili"),
    "Colombie": ("colombia", "colombie"),
    "Pérou": ("peru", "perou"),
    "Viêt Nam": ("vietnam",),
    "Thaïlande": ("thailand", "thailande"),
    "Indonésie": ("indonesia", "indonesie"),
    "Malaisie": ("malaysia", "malaisie"),
    "Philippines": ("philippines",),
    "Nouvelle-Zélande": ("new zealand", "nouvelle-zelande"),
    "Qatar": ("qatar",),
    "Koweït": ("kuwait", "koweit"),
    "Arabie saoudite": ("saudi arabia", "arabie saoudite"),
    "Égypte": ("egypt", "egypte"),
    "Kenya": ("kenya",),
    "Nigeria": ("nigeria",),
    "Ghana": ("ghana",),
    "Algérie": ("algeria", "algerie"),
    "Liban": ("lebanon", "liban"),
    "Jordanie": ("jordan", "jordanie"),
    "Congo": ("congo",),
    "Gabon": ("gabon",),
    "Côte d'Ivoire": ("cote d'ivoire", "ivory coast"),
    "Cameroun": ("cameroon", "cameroun"),
    "Islande": ("iceland", "islande"),
    "Serbie": ("serbia", "serbie"),
    "Tanzanie": ("tanzania", "tanzanie"),
    "Moldavie": ("moldova", "moldavie"),
    "Bosnie-Herzégovine": ("bosnia and herzegovina", "bosnie"),
    "Kazakhstan": ("kazakhstan",),
    "Guatemala": ("guatemala",),
    "Cambodge": ("cambodia", "cambodge"),
    "Albanie": ("albania", "albanie"),
    "Mongolie": ("mongolia",),
    "Bénin": ("benin",),
    "Maurice": ("maurice", "mauritius"),
    "Bangladesh": ("bangladesh",),
    "Ouzbékistan": ("uzbekistan", "ouzbekistan"),
    "Sri Lanka": ("sri lanka",),
    "Paraguay": ("paraguay",),
    "Uruguay": ("uruguay",),
    # Added on 2026-10-07: stored as "étranger (autre)" for lack of an entry.
    "Pakistan": ("pakistan",),
    "Équateur": ("ecuador", "equateur"),
    "Costa Rica": ("costa rica",),
    "Suriname": ("suriname",),
    "Bolivie": ("bolivia", "bolivie"),
    "Irak": ("iraq", "irak"),
    "Bahreïn": ("bahrain", "bahrein"),
    "Madagascar": ("madagascar",),
    "Rwanda": ("rwanda",),
    "Arménie": ("armenia", "armenie"),
    "Papouasie-Nouvelle-Guinée": ("papua new guinea",),
    "Ouganda": ("uganda", "ouganda"),
    "Éthiopie": ("ethiopia", "ethiopie"),
    "Togo": ("togo",),
    "Oman": ("oman",),
    "Népal": ("nepal",),
    "République dominicaine": ("dominican republic",),
    "Myanmar": ("myanmar",),
    "Mozambique": ("mozambique",),
    "Mali": ("mali",),
    "Tadjikistan": ("tajikistan", "tadjikistan"),
    "Azerbaïdjan": ("azerbaijan", "azerbaidjan"),
    "Guernesey": ("guernsey", "guernesey"),
    "Guyana": ("guyana",),
    "Fidji": ("fiji", "fidji"),
    "Djibouti": ("djibouti",),
    "Sierra Leone": ("sierra leone",),
}
# For zone_lieu. Without "maurice": Saint-Maurice is a French commune.
_PAYS_TOUS = tuple(a for al in _PAYS_CANON.values() for a in al if a != "maurice")
# American states spelled out ("Green Bay, Wisconsin Metropolitan Area").
# Without "Georgia": it is also a country ("Tbilisi, Georgia").
_ETATS_US = (
    "alabama",
    "alaska",
    "arizona",
    "arkansas",
    "california",
    "colorado",
    "connecticut",
    "delaware",
    "florida",
    "hawaii",
    "idaho",
    "illinois",
    "indiana",
    "iowa",
    "kansas",
    "kentucky",
    "louisiana",
    "maine",
    "maryland",
    "massachusetts",
    "michigan",
    "minnesota",
    "mississippi",
    "missouri",
    "montana",
    "nebraska",
    "nevada",
    "new hampshire",
    "new jersey",
    "new mexico",
    "north carolina",
    "north dakota",
    "ohio",
    "oklahoma",
    "oregon",
    "pennsylvania",
    "rhode island",
    "south carolina",
    "south dakota",
    "tennessee",
    "texas",
    "utah",
    "vermont",
    "virginia",
    "west virginia",
    "wisconsin",
    "wyoming",
)
# Cities written without a country (see _VILLES_ETRANGERES).
_VILLE_PAYS = {
    "Portugal": ("lisbon", "lisboa", "porto", "guimaraes"),
    "Danemark": ("copenhagen", "aalborg"),
    "Suède": ("stockholm", "umea", "gothenburg"),
    "Norvège": ("oslo",),
    "Finlande": ("helsinki",),
    "Brésil": ("sao paulo", "rio de janeiro", "belo horizonte", "florianopolis"),
    "Inde": (
        "mumbai",
        "pune",
        "bangalore",
        "bengaluru",
        "delhi",
        "hyderabad",
        "chennai",
        "kolkata",
        "vadodara",
        "lucknow",
    ),
    "Italie": (
        "turin",
        "torino",
        "milan",
        "milano",
        "rome",
        "roma",
        "naples",
        "napoli",
        "firenze",
        "padova",
        "bologna",
        "reggio emilia",
        "bolzano",
        "brescia",
    ),
    "Suisse": ("basel", "bale", "bern", "berne", "zurich", "geneva", "geneve", "lausanne"),
    "Pays-Bas": (
        "eindhoven",
        "utrecht",
        "rotterdam",
        "the hague",
        "amsterdam",
        "uden-veghel",
        "enschede",
        "delft",
        "amstelveen",
    ),
    "Malaisie": ("kuala lumpur", "malacca"),
    "Indonésie": ("jakarta", "surabaya"),
    "Thaïlande": ("bangkok",),
    "Philippines": ("manila", "cebu", "taguig"),
    "Corée du Sud": ("seoul",),
    "Japon": ("tokyo",),
    "Chine": ("shanghai", "beijing", "shenzhen"),
    "Émirats arabes unis": ("dubai", "abu dhabi"),
    "Qatar": ("doha",),
    "Arabie saoudite": ("riyadh",),
    "Égypte": ("cairo",),
    "Canada": (
        "montreal",
        "ottawa",
        "vancouver",
        "calgary",
        "edmonton",
        "toronto",
        "winnipeg",
        "st. john's",
    ),
    "États-Unis": (
        "houston",
        "philadelphia",
        "chicago",
        "boston",
        "los angeles",
        "seattle",
        "salt lake city",
        "dallas",
        "atlanta",
        "miami",
        "new york",
        "san francisco",
        "washington dc",
        "denver",
        "tampa",
        "indianapolis",
        "raleigh",
        "des moines",
        "st. louis",
        "milwaukee",
        "pittsburgh",
        "jacksonville",
        "cleveland",
        "minneapolis",
        "oklahoma city",
        "albuquerque",
    ),
    "Irlande": ("dublin",),
    "Australie": ("sydney", "melbourne"),
    "Viêt Nam": ("hanoi", "ho chi minh city"),
    "Mexique": ("mexico city", "monterrey"),
    "Pérou": ("lima",),
    "Colombie": ("bogota", "medellin", "cali"),
    "Chili": ("santiago",),
    "Argentine": ("buenos aires", "rosario"),
    "Équateur": ("quito",),
    "Géorgie": ("tbilisi",),
    "Taïwan": ("taipei", "tainan"),
    "Paraguay": ("asuncion",),
    "Sénégal": ("dakar",),
    "Tunisie": ("tunis",),
    "Côte d'Ivoire": ("abidjan",),
    "Maroc": ("casablanca", "rabat", "fes"),
    "Kenya": ("nairobi",),
    "Nigeria": ("lagos",),
    "Ghana": ("accra",),
    "Afrique du Sud": ("johannesburg", "cape town"),
    "Espagne": ("malaga", "valencia", "sevilla", "bilbao", "madrid", "barcelona"),
    "Belgique": ("zaventem", "oostende", "antwerp", "anvers", "gent", "gand", "liege", "kortrijk"),
    "Royaume-Uni": (
        "stoke-on-trent",
        "birmingham",
        "leeds",
        "edinburgh",
        "glasgow",
        "bristol",
        "london",
        "londres",
        "manchester",
        "belfast",
    ),
    "Autriche": ("vienna", "wien", "salzburg", "innsbruck", "graz", "linz"),
    "Tchéquie": ("prague",),
    "Pologne": ("warsaw", "warszawa", "krakow", "cracow", "lodz", "wroclaw", "poznan"),
    "Hongrie": ("budapest",),
    "Roumanie": ("bucharest",),
    "Bulgarie": ("sofia",),
    "Serbie": ("belgrade",),
    "Croatie": ("zagreb",),
    "Lituanie": ("vilnius",),
    "Lettonie": ("riga",),
    "Estonie": ("tallinn",),
    "Grèce": ("athens", "thessaloniki"),
    "Turquie": ("istanbul",),
    "Allemagne": (
        "cologne",
        "koln",
        "munchen",
        "dusseldorf",
        "nuremberg",
        "nurnberg",
        "karlsruhe",
        "berlin",
        "munich",
        "frankfurt",
        "hamburg",
        "stuttgart",
        "rhein-neckar",
    ),
}
_VILLES_TOUTES = tuple(v for vs in _VILLE_PAYS.values() for v in vs)
_WTJ_PAYS = {
    "be": "Belgique",
    "ch": "Suisse",
    "lu": "Luxembourg",
    "de": "Allemagne",
    "es": "Espagne",
    "nl": "Pays-Bas",
    "gb": "Royaume-Uni",
    "uk": "Royaume-Uni",
    "it": "Italie",
    "pt": "Portugal",
    "us": "États-Unis",
    "ca": "Canada",
}
# ISO code at the end of a place, format "City Region CC" (Talent, Glassdoor).
_ISO_PAYS = {
    **_WTJ_PAYS,
    "fr": "France",
    "sg": "Singapour",
    "ie": "Irlande",
    "at": "Autriche",
    "se": "Suède",
    "dk": "Danemark",
    "no": "Norvège",
    "fi": "Finlande",
    "pl": "Pologne",
    "in": "Inde",
    "au": "Australie",
    "jp": "Japon",
    "cn": "Chine",
    "hk": "Hong Kong",
    "br": "Brésil",
    "mx": "Mexique",
    "ae": "Émirats arabes unis",
    "za": "Afrique du Sud",
    "ma": "Maroc",
    "cz": "Tchéquie",
    "ro": "Roumanie",
    "hu": "Hongrie",
    "gr": "Grèce",
    "ph": "Philippines",
    "my": "Malaisie",
    "kw": "Koweït",
}


def pays_lieu(lieu: str | None) -> str:
    """Country of a place, in French: "France", "Suisse"…, or "?".

    France is decided by zone_lieu, which already knows departments, Île-de-France
    communes and WTJ formats. Abroad, the WRITTEN COUNTRY wins over the city ("Paris,
    Texas" does not exist here, but "London, Ontario" does).
    """
    z = zone_lieu(lieu)
    t = _n(lieu)
    if z == INCONNU:
        # Vague for the ZONE (which region?), not for the COUNTRY: "France",
        # "All France (remote)" and "Remote (FR)" are in France.
        return "France" if _contient(t, ("france", "fr")) else "?"
    if z != INTERNATIONAL:
        return "France"
    if _RX_VILLE_ETAT.match(lieu or ""):
        return "États-Unis"  # "Birmingham, AL" is not in England
    wtj = _RX_REGION_WTJ.search(t)
    if wtj and wtj.group(2) in _WTJ_PAYS:
        return _WTJ_PAYS[wtj.group(2)]
    # ISO code as the last word: "Delft Zuid-Holland NL", "Arlington VA US".
    fin = re.search(r"\s([A-Z]{2})\s*$", lieu or "")
    if fin and fin.group(1).lower() in _ISO_PAYS:
        return _ISO_PAYS[fin.group(1).lower()]
    # ISO code as a segment of its own, before the postcode: "Paço de Arcos, PT,
    # 2770-131", "Timisoara, RO", or "US" alone.
    for seg in reversed((lieu or "").split(",")):
        if re.fullmatch(r"\s*[A-Z]{2}\s*", seg) and seg.strip().lower() in _ISO_PAYS:
            return _ISO_PAYS[seg.strip().lower()]
    # The LAST segment, if it is a country, wins: "La Cañada, Querétaro,
    # Mexico" is not Canada, "Mexicali, Baja California, Mexico" is not
    # California.
    dernier = _n((lieu or "").split(",")[-1])
    for canon, alias in _PAYS_CANON.items():
        if dernier in alias:
            return canon
    # Before the countries: "New Mexico" is not Mexico.
    if _contient(t, _ETATS_US):
        return "États-Unis"
    for canon, alias in _PAYS_CANON.items():
        if _contient(t, alias):
            return canon
    for canon, villes in _VILLE_PAYS.items():
        if _contient(t, villes):
            return canon
    try:
        from jobhunter.sources import common as job_sources

        if job_sources._RX_ETAT_US.search(lieu or ""):
            return "États-Unis"
    except Exception:
        pass
    return "étranger (autre)"


# Region of the app's filter (the user, 2026-10-07): one click for all of
# Europe or all of Asia, instead of ticking thirty countries.
_REGIONS = {
    "Amérique du Nord": ("États-Unis", "Canada"),
    "Amérique latine": (
        "Mexique",
        "Brésil",
        "Argentine",
        "Chili",
        "Colombie",
        "Pérou",
        "Paraguay",
        "Uruguay",
        "Guatemala",
        "Équateur",
        "Costa Rica",
        "Suriname",
        "Bolivie",
        "République dominicaine",
        "Guyana",
    ),
    "Asie": (
        "Singapour",
        "Inde",
        "Chine",
        "Japon",
        "Hong Kong",
        "Taïwan",
        "Corée du Sud",
        "Viêt Nam",
        "Thaïlande",
        "Indonésie",
        "Malaisie",
        "Philippines",
        "Bangladesh",
        "Sri Lanka",
        "Cambodge",
        "Mongolie",
        "Kazakhstan",
        "Ouzbékistan",
        "Pakistan",
        "Népal",
        "Myanmar",
        "Tadjikistan",
    ),
    "Moyen-Orient": (
        "Émirats arabes unis",
        "Qatar",
        "Arabie saoudite",
        "Israël",
        "Liban",
        "Jordanie",
        "Irak",
        "Bahreïn",
        "Koweït",
        "Oman",
        "Turquie",
    ),
    "Afrique": (
        "Maroc",
        "Tunisie",
        "Algérie",
        "Égypte",
        "Sénégal",
        "Côte d'Ivoire",
        "Cameroun",
        "Congo",
        "Gabon",
        "Kenya",
        "Nigeria",
        "Ghana",
        "Afrique du Sud",
        "Tanzanie",
        "Bénin",
        "Maurice",
        "Madagascar",
        "Rwanda",
        "Ouganda",
        "Éthiopie",
        "Togo",
        "Mozambique",
        "Mali",
        "Djibouti",
        "Sierra Leone",
    ),
    "Océanie": ("Australie", "Nouvelle-Zélande", "Papouasie-Nouvelle-Guinée", "Fidji"),
}
_PAYS_REGION = {p: r for r, ps in _REGIONS.items() for p in ps}


def region_pays(pays: str | None) -> str:
    """Region of a country returned by pays_lieu.

    France is in Europe, like any European country not listed elsewhere; "?" and
    "étranger (autre)" stay "?".
    """
    if pays in ("?", "étranger (autre)", "", None):
        return "?"
    return _PAYS_REGION.get(pays, "Europe")


def lieu_du_titre(titre: str | None) -> str | None:
    """Foreign city named in the TITLE ("… (VIE - New York)"), or None.

    WHY. Talent and Glassdoor sometimes give the HEADQUARTERS as the place: Numberly
    "Forward Deployed Engineer (VIE - New York)" was stored "Paris", and the user read
    "New York" under the France filter (2026-10-07). The employer is not wrong about
    their own title.

    CITIES only, not countries: "Analyste ESG — couverture UK" or "Marchés US"
    describe a scope, not a workplace. A city named in a title, on the other hand, is
    almost always the place of the job.
    """
    t = _n(titre)
    for pays, villes in _VILLE_PAYS.items():
        for v in villes:
            # No hyphen after: "Porto-Vecchio" is in Corsica.
            if re.search(r"(?<![a-z0-9-])" + re.escape(v) + r"(?![a-z0-9]|-[a-z])", t):
                return f"{v.title()}, {pays}"
    return None


def lieu_propre(lieu: str | None) -> str:
    """The place without its repeated segments: "Luxembourg, Luxembourg, Luxembourg" -> "Luxembourg".

    LinkedIn writes city, region, country, and for a city-state the three are the
    same word (the user, 2026-10-27: "pas faux mais moche"). Only a segment equal to
    the one BEFORE it goes: "Geneva, Geneva, Switzerland" keeps its country.
    """
    gardes: list[str] = []
    for seg in (lieu or "").split(","):
        seg = " ".join(seg.split())
        if seg and (not gardes or _n(seg) != _n(gardes[-1])):
            gardes.append(seg)
    return ", ".join(gardes)


def _lieu_sur(lieu: str) -> bool:
    """Is this a place we KNOW? In France, one of the catalogue's; abroad, one that names its country.

    zone_lieu classes any unknown word "ailleurs" (the rest of France): "Vodafone"
    or "Effacer tous les filtres" would pass for French towns.
    """
    z = zone_lieu(lieu)
    if z == INTERNATIONAL:
        return pays_lieu(lieu) not in ("?", "étranger (autre)")
    if z == INCONNU:
        return False
    t = _n(lieu)
    return any((s := _secteur(c)) is not None and _dans_secteur(t, s) for c in CATALOGUE)


# A place the posting states in its text, as a label then a value: "Localisation du
# poste : Paris (75007)", "Ville : Paris 15", or Avature's "City\nVienna" and
# "Country\nAustria" on two lines. A line that goes on after the value ("Lieu : Brest,
# France Construisons ensemble…") is prose, not a field.
_RX_LIEU_TEXTE = re.compile(
    r"(?im)^[ \t]*(localisation du poste|lieu de travail|localisation|lieu|location|ville"
    r"|city|country|pays)(?:[ \t]*:[ \t]*(?:\r?\n[ \t\r\n]*)?|[ \t]*\r?\n[ \t\r\n]*)"
    r"([^\n:]{2,60}?)[ \t\r]*$"
)
# A country written on a line of its own, in any of its spellings.
_PAYS_ALIAS = frozenset(a for alias in _PAYS_CANON.values() for a in alias)
# A postal address: "…, 75008 Paris, France" -> ("Paris", "France").
_RX_ADRESSE = re.compile(
    r"\b\d{5}\s+([^\W\d][\w' -]{1,40}?)(?:\s+cedex\b[^,]*)?(?:,\s*([^\W\d][\w -]{1,30}))?\s*$"
)
# Workday puts the place in the address: …/job/Blagnac/Consultant-junior_R00347347.
_RX_WORKDAY_LIEU = re.compile(r"myworkdayjobs\.com/(?:[^/?#]+/)*job/([^/?#]+)/[^/?#]+/?$")
# What ends a slug without being a place: "-f-h", "-2", "_1326".
_FIN_SLUG = {"h", "f", "m", "x", "fh", "hf", "mf", "fm", "hfx"}


def _lieu_du_texte(description: str) -> str:
    villes: list[str] = []
    pays: list[str] = []
    for cle, valeur in _RX_LIEU_TEXTE.findall(description or ""):
        v = valeur.strip(" .;-")
        if len(v.split()) > 5:
            continue  # a sentence, not a place
        if v.isupper():
            v = v.title()  # "MILANO" -> "Milano"
        (pays if cle.lower() in ("country", "pays") else villes).append(v)
    for v in villes:
        lieu = f"{v}, {pays[0]}" if pays else v
        if _lieu_sur(lieu):
            return lieu
    p = next((p for p in pays if _lieu_sur(p)), "")
    if p:
        return p
    # No label, but a line of its own at the top of the page: Sia Partners' address
    # "21 Rue de Berri, 75008 Paris, France", ABN AMRO's "Nederland" then "Amersfoort".
    lignes = [" ".join(x.split()) for x in (description or "")[:2000].splitlines()]
    for i, ligne in enumerate(lignes):
        adr = _RX_ADRESSE.search(ligne) if len(ligne) <= 80 else None
        if adr:
            lieu = ", ".join(x for x in adr.groups() if x)
            if _lieu_sur(lieu):
                return lieu
        suite = lignes[i + 1] if i + 1 < len(lignes) else ""
        if (
            _n(ligne) in _PAYS_ALIAS
            and 1 < len(suite) <= 40
            and not re.search(r"\d", suite)
            and _lieu_sur(f"{suite}, {ligne}")
        ):
            return f"{suite}, {ligne}"
    return ""


def _lieu_de_l_url(url: str) -> str:
    u = (url or "").split("?")[0].split("#")[0]
    wd = _RX_WORKDAY_LIEU.search(u)
    if wd:
        lieu = " ".join(wd.group(1).replace("-", " ").split())
        return lieu if _lieu_sur(lieu) else ""
    # The city ends the slug: "…-chef-de-projet-fh-paris-2/", "…-bureau-de-lyon",
    # WTJ's "conseiller-clientele-premium_strasbourg_SG_NblzLwP". The shortest
    # ending first: "lyon" before "de-lyon"; "fontenay-sous-bois" needs all three.
    dernier = re.sub(r"\.(aspx|html?|php)$", "", u.rstrip("/").rsplit("/", 1)[-1])
    # LinkedIn ends with the employer: "…-analyst-at-zurich-insurance-4440748821".
    dernier = dernier.rsplit("-at-", 1)[0]
    for morceau in reversed(dernier.split("_")):
        mots = [m for m in morceau.lower().split("-") if m]
        while mots and (mots[-1].isdigit() or mots[-1] in _FIN_SLUG):
            mots.pop()
        for n in (1, 2, 3):
            if len(mots) < n:
                break
            lieu = "-".join(mots[-n:])
            # "paris-consultant" names Paris through its FIRST word: the city
            # does not end this slug.
            if _lieu_sur(lieu) and (n == 1 or not _lieu_sur("-".join(mots[-n:-1]))):
                return lieu.title()
    return ""


def lieu_deduit(url: str | None, description: str | None) -> str:
    """The place of an offer whose source gave none: from its text, else its address; "" if neither says.

    WHY. 178 offers of the queue had no place (2026-10-27): Workday, Avature, Sia
    Partners, ABN AMRO. The country filter showed them as "?". Their text or
    their address says where they are; only a recognised place is kept, never a guess.
    """
    return _lieu_du_texte(description or "") or _lieu_de_l_url(url or "")


def lieu_effectif(
    lieu: str | None, titre: str | None, url: str | None = None, description: str | None = None
) -> str | None:
    """The place to keep: the posting's, unless it is French (or empty) while the title names a foreign city.

    Cleaned of its repeated segments; when it names no country ("", "Télétravail"),
    completed from the posting's text or address (lieu_deduit).
    """
    if lieu:
        lieu = lieu_propre(lieu)
    if pays_lieu(lieu) == "?":
        d = lieu_deduit(url, description)
        if d:
            lieu = f"{d} ({lieu})" if lieu else d
    t = lieu_du_titre(titre)
    if t and zone_lieu(lieu) != INTERNATIONAL:
        return t
    return lieu


def reparer_lieu(o: Offre) -> bool:
    """Bring an offer of the queue to lieu_effectif, with its zone; True when it changed.

    The offers stored before a rule existed: the sorting runs it each day, after the
    descriptions are fetched — most sources give the text after the merge.
    """
    avant = o.get("localisation") or ""
    apres = (
        lieu_effectif(
            avant, o.get("poste"), o.get("url"), o.get("description") or o.get("missions")
        )
        or ""
    )
    if apres == avant:
        return False
    o["localisation"] = apres
    o["zone"] = zone_lieu(apres)
    return True


def ville_affichee(lieu: str | None) -> str:
    """The place as the app displays it: all of Île-de-France becomes "Paris" (the user, 2026-10-05).

    "La Defense", "Paris - 75", "Courbevoie, Ile-de- France" and "Greater Paris
    Metropolitan Region" are a single search for them; in the Place column, they made
    fifty boxes to tick.
    """
    if sous_zone(lieu) == "idf":
        return "Paris"
    return lieu or ""


def main() -> int:
    """Command line: summary of the queue's zones, or writing with --ecrire."""
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--ecrire", action="store_true", help="inscrit le champ `zone` dans chaque offre de la file"
    )
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]  # console : TextIOWrapper

    from jobhunter.storage import queue as queue_io

    if not a.ecrire:
        q = queue_io.charger(descriptions=False)
        c = collections.Counter(zone_lieu(o.get("localisation")) for o in q)
        haut = collections.Counter(
            zone_lieu(o.get("localisation")) for o in q if (o.get("fit") or 0) >= 8
        )
        print(f"{len(q)} offres\n")
        for z in sorted(c, key=lambda z: ORDRE[z]):
            print(f"  {z:12} {c[z]:5}   dont fit >= 8 : {haut.get(z, 0)}")
        print("\nExemples classes « ailleurs » a fit >= 8 :")
        for o in q:
            if (o.get("fit") or 0) >= 8 and zone_lieu(o.get("localisation")) == AILLEURS:
                print(
                    f"  fit {o['fit']}  {(o.get('localisation') or '')[:34]:34} "
                    f"{(o.get('poste') or '')[:38]}"
                )
        return 0

    try:
        with queue_io.transaction(descriptions=False) as q:
            n = 0
            for o in q:
                z = zone_lieu(o.get("localisation"))
                if o.get("zone") != z:
                    o["zone"] = z
                    n += 1
            print(f"{n} offre(s) etiquetee(s). Champ `zone` a jour.")
    except queue_io.VerrouIndisponible as e:
        print(f"! {e}")
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
