"""The profile's home country, for the sources: which ones run, and where they search.

The home country is `pays` in the profile (ISO code, France when absent:
scoring.zones.PAYS_MAISON). A French source (France Travail, the V.I.E, Welcome to the
Jungle…) only lists offers in France: it runs for a profile in France. EURES lists
Europe's: it runs for a profile in Europe.
"""

from typing import Any

# Country names as LinkedIn, Jooble and the job boards write them.
NOMS = {
    "fr": "France", "us": "United States", "ca": "Canada", "gb": "United Kingdom",
    "ie": "Ireland", "de": "Germany", "at": "Austria", "ch": "Switzerland",
    "be": "Belgium", "nl": "Netherlands", "lu": "Luxembourg", "es": "Spain",
    "pt": "Portugal", "it": "Italy", "se": "Sweden", "dk": "Denmark", "no": "Norway",
    "fi": "Finland", "pl": "Poland", "cz": "Czechia", "gr": "Greece", "au": "Australia",
    "nz": "New Zealand", "in": "India", "sg": "Singapore", "za": "South Africa",
    "br": "Brazil", "mx": "Mexico", "jp": "Japan", "ae": "United Arab Emirates",
}  # fmt: skip

# The European Economic Area and Switzerland: EURES's countries.
EUROPE = frozenset(
    "at be bg ch cy cz de dk ee es fi fr gr hr hu ie is it li lt lu lv mt nl no pl pt ro "
    "se si sk".split()
)

# The sources that only list offers in France.
FRANCAISES = frozenset(
    ("vie", "fir", "makesense", "francetravail", "wtj", "apec", "glassdoor", "hellowork")
)


# The regions a profile may name in `monde`, as sets of countries.
REGIONS = {"europe": EUROPE}
# The words that mean the whole world.
MONDE_MOTS = frozenset(("monde", "world", "worldwide", "partout", "international", "welt", "mundo"))


def _simple(s: str) -> str:
    import unicodedata

    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return " ".join(s.lower().split())


def code(texte: str) -> str:
    """The ISO code of a country as typed (« Suisse », « Switzerland », « ch »); "" if unknown."""
    from jobhunter.scoring import zones

    t = _simple(texte)
    if t in NOMS:
        return t
    for iso, n in NOMS.items():
        if _simple(n) == t:
            return iso
    for iso, n in zones._ISO_PAYS.items():
        if len(iso) == 2 and _simple(n) == t:
            return iso
    for canon, variantes in zones._PAYS_CANON.items():
        if t == _simple(canon) or t in variantes:
            return zones.code_pays(canon)
    return ""


def etranger_vise(valeur: Any) -> tuple[bool, frozenset[str], list[str]]:
    """The profile's `monde`: (the whole world?, ISO codes searched abroad, their names).

    Absent or true: the whole world, as before 3.53. False: the home country only. A
    list (« Suisse », « Belgique », « Europe »): the home country and those.
    """
    if valeur is None or valeur is True:
        return True, frozenset(), []
    if not isinstance(valeur, list):
        return False, frozenset(), []
    isos: set[str] = set()
    noms: list[str] = []
    for x in valeur:
        t = _simple(str(x))
        if t in MONDE_MOTS:
            return True, frozenset(), []
        if t in REGIONS:
            isos |= REGIONS[t] - {maison()}
            noms.append(t.title())
            continue
        iso = code(str(x))
        if iso and iso != maison() and iso not in isos:
            isos.add(iso)
            noms.append(nom(iso))
    return False, frozenset(isos), noms


def maison() -> str:
    """The home country's ISO code: `pays` in the profile, "fr" when absent."""
    from jobhunter.scoring import zones

    return str(zones.PAYS_MAISON)


def nom(iso: str | None = None) -> str:
    """The country's name in English (« United States »); the home country by default."""
    iso = (iso or maison()).lower()
    return NOMS.get(iso, iso.upper())


def en_france() -> bool:
    """Does the profile live in France?"""
    return maison() == "fr"


def en_europe() -> bool:
    """Does the profile live in EURES's Europe?"""
    return maison() in EUROPE


def parle(langue: str) -> bool:
    """Does the profile speak `langue` (`langues_parlees`)? French when the list is absent."""
    try:
        from jobhunter import profile as _P

        langues: Any = _P.get("langues_parlees", None)
    except Exception:
        langues = None
    if not isinstance(langues, list) or not langues:
        return langue == "fr"
    return langue in [str(x).lower() for x in langues]


def source_du_pays(nom_source: str) -> bool:
    """Does `nom_source` list offers where the profile lives?"""
    if nom_source in FRANCAISES:
        return en_france()
    if nom_source == "eures":
        return en_europe()
    if nom_source == "arbeitsagentur":  # Germany's: for a German speaker in Europe
        return en_europe() and (maison() in ("de", "at", "ch") or parle("de"))
    if nom_source == "usajobs":
        return maison() == "us"
    return True
