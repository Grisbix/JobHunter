"""jobhunter.scoring.zones — Ou l'utilisateur veut travailler, et comment le lire dans un lieu. (ancien Scripts/zones.py)

PREFERENCE DECLAREE (2026-09-08) : Bordeaux et l'Ile-de-France d'abord ; le
Sud-Est ensuite ; le reste de la France sans grand interet.

CE QUE CE MODULE NE FAIT PAS : toucher au `fit`. Le fit mesure l'adequation du
POSTE ; la geographie est une autre question, et les melanger rendrait les deux
illisibles. Une offre parfaite a Lille reste une offre parfaite — elle est
simplement mal placee. La zone est donc un champ a part, filtrable et triable
dans l'app.

TROIS PIEGES, tous rencontres dans les donnees reelles :

  1. Les communes d'Ile-de-France apparaissent SEULES. « Courbevoie » (17 fois)
     ne contient ni « Paris » ni « Ile-de-France ». D'ou la liste _IDF_COMMUNES.
  2. « France » tout court (74 offres) et le vide (106) ne disent RIEN. Les
     classer « ailleurs » ecarterait des offres peut-etre parisiennes : ils
     valent « inconnu », jamais un rejet.
  3. Les accents et la casse varient (« Île-de-France », « ile de france »,
     « ILE DE FRANCE »). On compare sans accent ni casse.

Run :
  python -m jobhunter.scoring.zones            # repartition de la file
  python -m jobhunter.scoring.zones --ecrire   # inscrit le champ `zone` dans chaque offre
"""

import argparse
import collections
import re
import sys
from collections.abc import Iterable
from typing import Any

from jobhunter import paresseux as _paresseux
from jobhunter import racine as _racine
from jobhunter.texte import sans_accent

_ici = sys.modules[__name__]
# Valeurs tirees du profil : calculees a la premiere lecture, pas a l'import
# (jobhunter.paresseux). Dans ce module, on les lit par `_ici.NOM`.
_PARESSEUX: _paresseux.Fabriques = {}


def __getattr__(nom: str) -> Any:
    return _paresseux.lire(_ici, _PARESSEUX, nom)


Secteur = dict[str, Any]  # cle, libelle, lieux, communes, departements, wtj

# TRANSITION (phase 3) : imports differes de modules encore dans Scripts/
# (doublons, rejets_tri, depuis tri). A retirer quand ils auront rejoint le paquet.
_SCRIPTS = _racine.scripts()
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

PRIORITAIRE = "prioritaire"  # secteurs prioritaires du profil
SECONDAIRE = "secondaire"  # secteurs secondaires du profil
AILLEURS = "ailleurs"  # reste de la FRANCE
INTERNATIONAL = "international"
INCONNU = "inconnu"

# « ailleurs » designait jusqu'ici le reste de la France ET l'etranger, ce qui
# melangeait Lille et Singapour. Depuis la recherche mondiale, l'etranger a sa
# propre zone : deplacer a Nantes et deplacer a Hong Kong ne se decident pas de
# la meme facon.
ORDRE = {PRIORITAIRE: 0, SECONDAIRE: 1, INCONNU: 2, AILLEURS: 3, INTERNATIONAL: 4}

# Communes d'IDF vues dans la file, ecrites sans leur region.
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
    # « boulogne » seul prenait Boulogne-sur-Mer (Pas-de-Calais) pour l'IDF.
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
    # Vues « ailleurs » le 2026-09-23, sans region ni departement.
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

# Un lieu qui ne dit que le pays, ou rien : aucune information.
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
    """Minuscules, sans accent, blancs ecrases."""
    return re.sub(r"\s+", " ", sans_accent(str(t or "")).lower()).strip()


# Pays etrangers, tels qu'ils apparaissent en FIN de lieu : LinkedIn ecrit
# « Geneva, Geneva, Switzerland », « Rotterdam, South Holland, Netherlands ».
# _RX_ETRANGER de job_sources ne connait ni ces pays ni ces villes, donc 34
# offres genevoises et 30 rotterdamoises etaient rangees dans « le reste de la
# France ». On lit le DERNIER segment, celui qui porte le pays.
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
    # NOMS FRANCAIS. La liste etait presque entierement anglaise, parce que les
    # lieux venaient de LinkedIn. Les offres V.I.E de Business France, elles,
    # sont ecrites en francais : « Copenhague, Danemark » tombait en « reste de
    # la France ». Un pays doit etre reconnu dans les deux langues.
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
    # Pays ou les V.I.E envoient reellement. « POINTE NOIRE (CONGO) » tombait
    # en « reste de la France » : Business France ecrit le pays entre
    # parentheses, et aucun de ces noms n'etait connu.
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
    # NOMS ANGLAIS, ecrits par LinkedIn en dernier segment. Il manquait tous
    # ceux-ci : 28 offres a Bogota, 20 a Santiago etaient rangees dans « le
    # reste de la France » (mesure du 2026-09-23).
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
    # macro-regions de recrutement : jamais la France seule
    "namer",
    "latam",
    "apac",
    "sub-saharan africa",
    "middle east",
    "mena",
}

# Villes etrangeres ecrites SANS pays : LinkedIn dit « Lisbon Metropolitan
# Area », « Greater Milan Metropolitan Area » ; WTJ colle meme « · France » a
# « Genève » ou « Zurich ». Aucun pays a lire — la ville est le seul indice.
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

# Le FORMAT des metropoles LinkedIn — « Greater X Area », « X Metropolitan
# Area/Region », « Greater X », « X Metro » — sert surtout hors de France : la
# liste de villes ne s'arretera jamais (Gothenburg, Cincinnati, Surabaya…).
# On le lit donc comme un indice etranger, SAUF si une ville francaise est
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
# Code de region WTJ : « Saint-Ouen, A8, FR », « Biot, B8, FR », « …, ARA, FR ».
_RX_REGION_WTJ = re.compile(r",\s*([a-z0-9]{1,3})\s*,\s*([a-z]{2})\b")

# Outre-mer : la France, mais pas une cible. Teste AVANT les communes :
# « Saint-Denis, Reunion » est le chef-lieu de La Reunion, pas le 93.
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

# Regions francaises HORS cible. Une commune d'IDF homonyme n'y compte pas :
# « Asnières, Normandy » n'est pas Asnieres-sur-Seine.
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
# Le profil (section « zones ») choisit ses secteurs PRIORITAIRES et
# SECONDAIRES dans ce catalogue, par leur cle. Chaque secteur : un libelle, des
# noms de lieux (communes, metropole, region), des departements et des codes de
# region WTJ. Un secteur absent du catalogue se declare dans le profil :
#     "zones": {"prioritaires": ["lyon", {"cle": "chambery", "libelle": "Chambéry",
#                                         "lieux": ["chambery", "aix-les-bains"],
#                                         "departements": ["73"]}]}
#
# Une METROPOLE n'est pas sa region : « Chasseneuil-du-Poitou, Nouvelle-
# Aquitaine » n'est pas Bordeaux, la region s'etend a quatre heures de route.
# Un nom de region n'est pas un lieu.
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
        "libelle": "Paris",
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
    # Metropoles et regions, pour un profil qui cherche ailleurs.
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


def _secteur(x: object) -> Secteur | None:
    """Secteur du catalogue (par cle) ou declare dans le profil (dict)."""
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
        from jobhunter import profil as _P

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
    """Le lieu normalise `t` nomme-t-il le secteur `s` ? (communes d'IDF : pas
    si une autre region est nommee — « Asnières, Normandy »)."""
    if s["lieux"] and _contient(t, s["lieux"]):
        return True
    return bool(s["communes"]) and _contient(t, s["communes"]) and not _contient(t, _REGIONS_AUTRES)


_RX_CACHE: dict[object, re.Pattern[str]] = {}  # cle : le tuple, ou son id()


def _contient(t: str, tokens: Iterable[str]) -> bool:
    """Un des `tokens` apparait-il comme MOT ENTIER dans `t` ?

    La comparaison en sous-chaine faisait entrer « Singapore » dans le Sud-Est :
    « sinGAPore » contient « gap ». Meme famille que les faux positifs deja
    corriges ailleurs (« RSE » dans « diveRSE », « climat » dans
    « climatisation »). Les bornes de mot suppriment la classe entiere.
    """
    # Cle = le tuple LUI-MEME quand il est hachable. id() ne vaut que pour les
    # constantes du module : un tuple temporaire libere rend son adresse, le
    # suivant la reprend et herite du motif de l'autre. `_contient(t, (v,))`
    # dans une boucle repondait ainsi avec le motif de la ville precedente.
    cle = tokens if isinstance(tokens, (tuple, frozenset)) else id(tokens)
    rx = _RX_CACHE.get(cle)
    if rx is None:
        motif = "|".join(re.escape(k.strip()) for k in tokens if k.strip())
        rx = _RX_CACHE[cle] = re.compile(r"(?<![a-z0-9])(?:" + motif + r")(?![a-z0-9])")
    return bool(rx.search(t))


def _departement(t: str) -> str | None:
    """Numero de departement lu dans le lieu normalise, ou None."""
    m = _RX_DEP.search(t)
    if not m:
        return None
    d = next(g for g in m.groups() if g)
    # Un code postal a 5 chiffres ne commence pas par 00 ; « 20xxx » est la Corse.
    return None if d == "00" else d


# Le lieu ENTIER est « Ville, ST » avec un code d'Etat en majuscules.
_RX_VILLE_ETAT = re.compile(
    r"^[^,]+,\s*(AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|MA|MD|ME|MI"
    r"|MN|MO|MS|MT|NC|ND|NE|NH|NJ|NM|NV|NY|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VA"
    r"|VT|WA|WI|WV|WY|DC)(?:\s+\d{5})?\s*$"
)


def _code_etranger(job_sources: Any, lieu: str) -> bool:
    """_RX_ETRANGER, sans prendre une particule pour un code pays : son motif
    est insensible a la casse, et « Rive-de-Gier » y devenait l'Allemagne
    (« de »). Un code de deux lettres ne compte qu'en MAJUSCULES et hors d'un
    nom compose (« Düsseldorf … DE » oui, « -de- » non)."""
    for m in job_sources._RX_ETRANGER.finditer(lieu):
        s = m.group(0)
        if len(s) != 2:
            return True
        avant, apres = lieu[m.start() - 1 : m.start()], lieu[m.end() : m.end() + 1]
        if s.isupper() and avant != "-" and apres != "-":
            return True
    return False


def zone_lieu(lieu: str | None) -> str:
    """Zone d'un lieu : prioritaire / sud-est / ailleurs / international / inconnu.

    Ordre : noms francais cibles, puis indices etrangers, PUIS departement.
    Le departement vient apres l'etranger parce qu'un code postal americain
    (« Houston, TX 77002 ») lu comme departement donnerait « Seine-et-Marne ».
    """
    t = _n(lieu)
    if t in _VAGUE or not t:
        return INCONNU
    # « Ville, ST » americain AVANT les noms francais : « New Orleans, LA »
    # etait rangee en France a cause d'« Orleans » (2026-10-07).
    if _RX_VILLE_ETAT.match(lieu or ""):
        return INTERNATIONAL
    wtj = _RX_REGION_WTJ.search(t)
    reg, pays = (wtj.group(1), wtj.group(2)) if wtj else ("", "")
    # Les secteurs du profil d'abord : ce sont les cibles declarees. L'outre-mer
    # avant tout : « Saint-Denis, Reunion » n'est pas le 93.
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
    # Code pays WTJ autre que FR : « Zaventem, VLG, BE · France ». Le « France »
    # final est celui du site, pas du lieu.
    if pays and pays != "fr":
        return INTERNATIONAL
    # OU QUE LE PAYS SE TROUVE DANS LA CHAINE. LinkedIn le met en dernier
    # segment (« Geneva, Geneva, Switzerland ») mais Business France le met
    # entre PARENTHESES (« POINTE NOIRE (CONGO) ») : ne lire que le segment
    # final rangeait le Congo et le Gabon dans « le reste de la France ».
    # On cherche donc le pays partout, en mot entier — la borne de mot evite
    # qu'« Inde » ne matche « Indre » ou « Chine » « Machine ».
    if _contient(t, _PAYS_ETRANGERS) or _contient(t, _VILLES_ETRANGERES):
        return INTERNATIONAL
    # Tout pays du filtre Pays, pas seulement ceux de _PAYS_ETRANGERS : sans
    # cela « Port Louis, Mauritius » finissait « ailleurs en France ».
    if _contient(t, _PAYS_TOUS) or _contient(t, _VILLES_TOUTES):
        return INTERNATIONAL
    if _RX_METRO.search(t) and not _contient(t, _METROS_FR):
        try:
            from jobhunter.sources import commun as job_sources

            if not job_sources._RX_FR.search(lieu or ""):
                return INTERNATIONAL
        except Exception:
            pass
    # France ou etranger ? On s'appuie sur le detecteur de job_sources, seul
    # endroit ou vivent les listes de pays et de codes d'Etats americains.
    # Import tardif : job_sources importe zones pour etiqueter a l'ajout.
    try:
        from jobhunter.sources import commun as job_sources

        # LA FRANCE SE TESTE EN PREMIER. _RX_ETRANGER contient le code pays
        # « de », qui matche le « de » de « Hauts-de-France » : Lille et Nantes
        # partaient a l'international.
        francais = bool(job_sources._RX_FR.search(lieu or ""))
        # en_france() rend True pour TOUT quand la recherche mondiale est
        # active — on interroge donc les motifs directement.
        etranger = not francais and bool(
            job_sources._RX_ETAT_US.search(lieu or "") or _code_etranger(job_sources, lieu or "")
        )
    except Exception:
        etranger = False
    if etranger:
        return INTERNATIONAL
    # Departement : seuls 75 et 92 etaient connus, en jetons. « Bobigny - 93 »,
    # « Melun - 77 » ou « Bron - 69 » tombaient dans « le reste de la France ».
    d = _departement(t)
    if d in _ici._DEP_PRIORITAIRE:
        return PRIORITAIRE
    if d in _ici._DEP_SUD_EST:
        return SECONDAIRE
    return AILLEURS


def sous_zone(lieu: str | None) -> str:
    """Pour une offre PRIORITAIRE : « bordeaux » ou « idf ». Sinon ''.

    Les deux cibles partagent une zone (meme priorite de tri), mais pas une
    etiquette : l'app affichait « 1 · Bordeaux/IDF » sur 1275 offres dont 56
    seulement etaient a Bordeaux — l'utilisateur lisait « Bordeaux » sur Paris.
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
    """« Paris », « Bordeaux »… pour une cle rendue par sous_zone."""
    for s in _ici.SECTEURS_PRIORITAIRES + _ici.SECTEURS_SECONDAIRES:
        if s["cle"] == cle:
            return str(s["libelle"])
    return cle


# ── Pays d'un lieu, pour le filtre « Pays » de l'app (2026-10-05) ───────────
# Un nom canonique par pays, en francais, quelle que soit la langue du lieu :
# « Switzerland », « Suisse » et « Schweiz » doivent tomber dans la meme case
# du filtre, sinon il faut cocher trois cases pour un seul pays.
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
    # Ajoutes le 2026-10-07 : rangés « étranger (autre) » faute d'entree.
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
# Pour zone_lieu. Sans « maurice » : Saint-Maurice est une commune francaise.
_PAYS_TOUS = tuple(a for al in _PAYS_CANON.values() for a in al if a != "maurice")
# Etats americains en toutes lettres (« Green Bay, Wisconsin Metropolitan Area »).
# Sans « Georgia » : c'est aussi un pays (« Tbilisi, Georgia »).
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
# Villes ecrites sans pays (voir _VILLES_ETRANGERES).
_VILLE_PAYS = {
    "Portugal": ("lisbon", "lisboa", "porto", "guimaraes"),
    "Danemark": ("copenhagen", "aalborg"),
    "Suède": ("stockholm", "umea", "gothenburg"),
    "Norvège": ("oslo",),
    "Finlande": ("helsinki",),
    "Brésil": ("sao paulo", "rio de janeiro"),
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
        "milan",
        "rome",
        "naples",
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
    "Philippines": ("manila", "cebu"),
    "Corée du Sud": ("seoul",),
    "Japon": ("tokyo",),
    "Chine": ("shanghai", "beijing", "shenzhen"),
    "Émirats arabes unis": ("dubai", "abu dhabi"),
    "Qatar": ("doha",),
    "Arabie saoudite": ("riyadh",),
    "Égypte": ("cairo",),
    "Canada": ("montreal", "ottawa", "vancouver", "calgary", "toronto", "winnipeg", "st. john's"),
    "États-Unis": (
        "houston",
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
    "Autriche": ("vienna",),
    "Tchéquie": ("prague",),
    "Pologne": ("warsaw", "krakow", "cracow", "lodz", "wroclaw", "poznan"),
    "Hongrie": ("budapest",),
    "Roumanie": ("bucharest",),
    "Bulgarie": ("sofia",),
    "Serbie": ("belgrade",),
    "Croatie": ("zagreb",),
    "Lituanie": ("vilnius",),
    "Lettonie": ("riga",),
    "Estonie": ("tallinn",),
    "Grèce": ("athens",),
    "Turquie": ("istanbul",),
    "Allemagne": (
        "cologne",
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
# Code ISO en fin de lieu, format « Ville Region CC » (Talent, Glassdoor).
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
}


def pays_lieu(lieu: str | None) -> str:
    """Pays d'un lieu, en francais : « France », « Suisse »…, ou « ? ».

    La France se decide par zone_lieu, qui connait deja departements, communes
    d'IDF et formats WTJ. A l'etranger, le PAYS ECRIT l'emporte sur la ville
    (« Paris, Texas » n'existe pas ici, mais « London, Ontario » si).
    """
    z = zone_lieu(lieu)
    t = _n(lieu)
    if z == INCONNU:
        # Vague pour la ZONE (quelle region ?), pas pour le PAYS : « France »,
        # « All France (remote) » et « Remote (FR) » sont en France.
        return "France" if _contient(t, ("france", "fr")) else "?"
    if z != INTERNATIONAL:
        return "France"
    if _RX_VILLE_ETAT.match(lieu or ""):
        return "États-Unis"  # « Birmingham, AL » n'est pas en Angleterre
    wtj = _RX_REGION_WTJ.search(t)
    if wtj and wtj.group(2) in _WTJ_PAYS:
        return _WTJ_PAYS[wtj.group(2)]
    # Code ISO en dernier mot : « Delft Zuid-Holland NL », « Arlington VA US ».
    fin = re.search(r"\s([A-Z]{2})\s*$", lieu or "")
    if fin and fin.group(1).lower() in _ISO_PAYS:
        return _ISO_PAYS[fin.group(1).lower()]
    # Le DERNIER segment, s'il est un pays, l'emporte : « La Cañada, Querétaro,
    # Mexico » n'est pas le Canada, « Mexicali, Baja California, Mexico » pas
    # la Californie.
    dernier = _n((lieu or "").split(",")[-1])
    for canon, alias in _PAYS_CANON.items():
        if dernier in alias:
            return canon
    # Avant les pays : « New Mexico » n'est pas le Mexique.
    if _contient(t, _ETATS_US):
        return "États-Unis"
    for canon, alias in _PAYS_CANON.items():
        if _contient(t, alias):
            return canon
    for canon, villes in _VILLE_PAYS.items():
        if _contient(t, villes):
            return canon
    try:
        from jobhunter.sources import commun as job_sources

        if job_sources._RX_ETAT_US.search(lieu or ""):
            return "États-Unis"
    except Exception:
        pass
    return "étranger (autre)"


# Region du filtre de l'app (l'utilisateur, 2026-10-07) : un clic pour toute
# l'Europe ou toute l'Asie, au lieu de cocher trente pays.
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
    """Region d'un pays rendu par pays_lieu. La France est en Europe, comme
    tout pays europeen non liste ailleurs ; « ? » et « étranger (autre) »
    restent « ? »."""
    if pays in ("?", "étranger (autre)", "", None):
        return "?"
    return _PAYS_REGION.get(pays, "Europe")


def lieu_du_titre(titre: str | None) -> str | None:
    """Ville etrangere nommee dans l'INTITULE (« … (VIE - New York) »), ou None.

    POURQUOI. Talent et Glassdoor donnent parfois le SIEGE comme lieu : Numberly
    « Forward Deployed Engineer (VIE - New York) » etait rangee « Paris », et
    l'utilisateur lisait « New York » sous le filtre France (2026-10-07). L'employeur
    ne se trompe pas sur son propre intitule.

    Les VILLES seulement, pas les pays : « Analyste ESG — couverture UK » ou
    « Marches US » decrivent un perimetre, pas un lieu de travail. Une ville
    nommee dans un intitule, elle, est presque toujours le lieu du poste."""
    t = _n(titre)
    for pays, villes in _VILLE_PAYS.items():
        for v in villes:
            # Pas de trait d'union apres : « Porto-Vecchio » est en Corse.
            if re.search(r"(?<![a-z0-9-])" + re.escape(v) + r"(?![a-z0-9]|-[a-z])", t):
                return f"{v.title()}, {pays}"
    return None


def lieu_effectif(lieu: str | None, titre: str | None) -> str | None:
    """Le lieu a retenir : celui de l'annonce, sauf s'il est francais (ou vide)
    alors que l'intitule nomme une ville etrangere."""
    t = lieu_du_titre(titre)
    if t and zone_lieu(lieu) != INTERNATIONAL:
        return t
    return lieu


def ville_affichee(lieu: str | None) -> str:
    """Le lieu tel que l'app l'affiche : toute l'Ile-de-France devient « Paris »
    (l'utilisateur, 2026-10-05). « La Defense », « Paris - 75 », « Courbevoie, Ile-de-
    France » et « Greater Paris Metropolitan Region » sont une seule recherche
    pour lui ; dans la colonne Lieu, ils faisaient cinquante cases a cocher."""
    if sous_zone(lieu) == "idf":
        return "Paris"
    return lieu or ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--ecrire", action="store_true", help="inscrit le champ `zone` dans chaque offre de la file"
    )
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]  # console : TextIOWrapper

    from jobhunter.stockage import file as queue_io

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
