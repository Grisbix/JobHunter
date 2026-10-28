"""What CV, letter and message share: cleaned title, skills, company values.

Part of jobhunter.documents (formerly Scripts/tailor_application.py, phase 3.5).
"""

# Names from the lexicon, re-exported: `tailor_application.cv_variant_key` stays valid.
import importlib
import re
import sys
from typing import Any

from jobhunter import lazy as _paresseux
from jobhunter import paths as chemins
from jobhunter import profile as _P
from jobhunter.scoring.lexicon import cv_variant_key, has_skill  # noqa: F401

_ici = sys.modules[__name__]
# Values taken from the profile: computed on first read, not at import
# (jobhunter.lazy). In this module, they are read through `_ici.NAME`.
_PARESSEUX: _paresseux.Fabriques = {}


def __getattr__(nom: str) -> Any:
    return _paresseux.lire(_ici, _PARESSEUX, nom)


_PARESSEUX["_COMP"] = lambda: importlib.import_module("jobhunter.scoring.lexicon")._COMP


_PARESSEUX["_DOMAINES"] = lambda: importlib.import_module("jobhunter.scoring.lexicon")._DOMAINES


_PARESSEUX["CV_VARIANT"] = lambda: importlib.import_module("jobhunter.scoring.lexicon").CV_VARIANT


_PARESSEUX["CV_VARIANT_EN"] = lambda: (
    importlib.import_module("jobhunter.scoring.lexicon").CV_VARIANT_EN
)


_PARESSEUX["SKILL_LEX"] = lambda: importlib.import_module("jobhunter.scoring.lexicon").SKILL_LEX


CV_ATS = chemins.CV_MODELES


# Output folders: created when writing (chemins.preparer), not at import.
_PARESSEUX["CV_OUT"] = lambda: chemins.CV_PAR_OFFRE
_PARESSEUX["LT_OUT"] = lambda: chemins.LT_PAR_OFFRE


_PARESSEUX["_ID"] = lambda: _P.identite()


_PARESSEUX["PROFILE"] = lambda: dict(
    nom=_ici._ID["nom"], ville=_ici._ID["ville"], email=_ici._ID["email"], tel=_ici._ID["tel"]
)


# value hook per company: profile, lettre.valeurs_entreprises_fr/en
_PARESSEUX["COMPANY_VALUE"] = lambda: dict(_P.get("lettre.valeurs_entreprises_fr", {}) or {})


# Words that keep their capital in a job title: residual proper
# nouns. The general rule is that a French job title is a COMMON NOUN
# ("contrôleur de gestion", not "Contrôleur de Gestion"), but postings
# capitalise every word the English way and we copied it as is.
_PROPRES = {
    "france",
    "paris",
    "europe",
    "afrique",
    "asie",
    "amerique",
    "amérique",
    "allemagne",
    "espagne",
    "italie",
    "belgique",
    "suisse",
    "luxembourg",
    "benelux",
    "emea",
    "monde",
}


# Acronyms that keep their capitals even in a shouted title. EXPLICIT
# list: no length rule tells "ESG" from "DES".
_SIGLES = {
    "ESG",
    "RSE",
    "ISR",
    "SFDR",
    "CSRD",
    "CSDDD",
    "GRI",
    "TCFD",
    "SASB",
    "PAI",
    "DCF",
    "LBO",
    "M&A",
    "IFRS",
    "EBITDA",
    "KPI",
    "ERP",
    "SAP",
    "IT",
    "SI",
    "DSI",
    "BI",
    "SQL",
    "VBA",
    "IA",
    "AI",
    "ML",
    "LLM",
    "RH",
    "QHSE",
    "HSE",
    "RGPD",
    "AMF",
    "ACPR",
    "BFR",
    "FP&A",
    "PME",
    "ETI",
    "ONG",
    "SRI",
    "UX",
    "UI",
    "API",
    "CRM",
    "PMO",
    "MOA",
    "MOE",
}


def nord_americain(lieu: str | None) -> bool:
    """Is the offer in the United States or Canada? Unknown place: the profile's country.

    There, a letter opens with « Dear Hiring Manager » and closes with « Sincerely »,
    and the date reads « October 28, 2026 »; in Britain and elsewhere, « Dear Sir or
    Madam », « Yours faithfully » and « 28 October 2026 ».
    """
    from jobhunter.scoring import zones

    p = zones.pays_lieu(lieu) if str(lieu or "").strip() else "?"
    if p in ("États-Unis", "Canada"):
        return True
    return p == "?" and str(zones.PAYS_MAISON) in ("us", "ca")


def minuscule_titre(t: str) -> str:
    """“Contrôleur de Gestion Financier” -> "contrôleur de gestion financier".

    An acronym stays intact ("Analyste RSE-ESG" keeps RSE-ESG), and so does a known
    proper noun. Everything else goes lower case: in French a job title is a common
    noun.

    BUT a posting may be written ENTIRELY in capitals — "CORPORATE FINANCE",
    "GESTIONNAIRE DES RISQUES". Taking every word for an acronym then left the
    letter's subject shouting. When most long words are in capitals, it is a
    shouting posting, not a series of acronyms: we lower EVERYTHING, and only raise
    back the recognised acronyms.

    Length is not enough to tell an acronym: "DES" has three letters and stays an
    article, hence "gestionnaire DES risques".
    """
    mots = (t or "").split(" ")
    longs = [m.strip(",.;:()[]") for m in mots if len(m.strip(",.;:()[]")) > 4]
    crie = bool(longs) and sum(1 for m in longs if m.upper() == m) > len(longs) / 2

    sortie = []
    for m in mots:
        nu = m.strip(",.;:()[]")
        if not nu:
            sortie.append(m)
        elif nu.lower() in _PROPRES:
            # A proper noun keeps its capital, but not ALL its capitals:
            # « CHARGE DE MISSION RSE FRANCE » donnait « … RSE FRANCE ».
            sortie.append(m.capitalize() if crie else m)
        elif crie:
            sortie.append(m if nu.upper() in _SIGLES else m.lower())
        elif nu.upper() == nu and any(c.isalpha() for c in nu):
            sortie.append(m)  # sigle : RSE, M&A, IT, SAP
        else:
            sortie.append(m.lower())
    # The State keeps its capital: "infirmier diplômé d'État", not "d'état".
    return re.sub(r"\b([dl]['’])état\b", r"\1État", " ".join(sortie))


def _de(mot: str, apostrophe: str = "'") -> str:
    r"""Elision: 'de Amundi' -> "d'Amundi".

    'h' and 'y' EXCLUDED: "de Hollande" and "de Yann" are correct, not "d'Hollande".

    `apostrophe`: the CV template is written with the TYPOGRAPHIC apostrophe
    ("d’une expertise", "d’un mémoire"). Injecting a straight apostrophe into it
    gave, in the same sentence: "d’un poste d'Analyste RSE-ESG". Two different
    apostrophes six words apart, on a CV.
    """
    mot = (mot or "").strip()
    if mot[:1].lower() in "aàâäeéèêëiîïoôöuùûü":
        return "d" + apostrophe + mot
    return "de " + mot


# ── Cleaning the job title ───────────────────────────────────────────────────
# The raw title of a posting is NOT a job title: it carries the gender
# mention, the contract type, the city, the internal reference… Written as is in
# "Objet : Candidature au poste de …", it gives unreadable letters.
# The \b are ESSENTIAL: without them, "DAF - Finance" matches "F - F"
# (the final F of DAF, the dash, the initial F of Finance) and the cleaning produces
# "DA inance". The pattern must only accept ISOLATED letters — and "&" binds a
# letter too: "H&M - H/F" lost its M ("H&"), the M taken for a gender letter.
# The en and em dashes separate like "-": "Analyste – F – H" kept its mention, which
# the dash normalisation below then turned into "F - H", removed only by a SECOND
# cleaning (found by tests/test_properties.py).
RX_GENRE = re.compile(
    r"[(\[]?\s*(?<![\w&])[HFMWX](?![\w&])"
    r"(?:\s*[/|.\-–—]\s*(?<![\w&])[HFMWXD](?![\w&])){1,2}\s*[)\]]?",
    re.I,
)


# The GLUED gender marker, without a separator: "CORPORATE FINANCE HF".
# RX_GENRE requires a separator (H/F, H-F, H.F) and therefore let this one through,
# so that the subject announced a "corporate finance hf" job. Anchored at
# FIN de chaine seulement : ailleurs, « HF » peut vouloir dire haute frequence.
RX_GENRE_COLLE = re.compile(r"\s*[(\[]?\s*\b(?:HF|FH|MW|FM|MF)\b\s*[)\]]?\s*$", re.I)


RX_CONTRAT = re.compile(
    r"\b(CDI|CDD|VIE|V\.I\.E|int[ée]rim|freelance|temps\s+plein|temps\s+partiel|"
    r"full[\s-]?time|part[\s-]?time|permanent|remote|t[ée]l[ée]travail|hybride|"
    r"\d+\s*mois|\d+\s*months|\d+\s*ans)\b",
    re.I,
)


RX_BRUIT = re.compile(
    r"\b(nouveau|new|urgent|poste\s+\d+|r[ée]f\.?\s*\S+|"
    r"job\s*id\s*:?\s*\d+|\d{3,}\s*days?)\b",
    re.I,
)


# "#00137324": no word character before the #, so a \b before it would NEVER match
RX_REF = re.compile(r"#\s*\d+")


RX_LIEU_FIN = re.compile(r"[\s,(-]+[A-ZÀ-Ý][\wÀ-ÿ'-]*\s*\(?\d{5}\)?\s*\)?\s*$")


RX_ADRESSE = re.compile(
    r"\b\d{1,4}\s+(rue|avenue|boulevard|impasse|chemin|place)\b"
    r"|\b\d{5}\s+[A-ZÀ-Ý]",
    re.I,
)


for _n, _rx in list(globals().items()):
    # A "\b" eaten by a heredoc becomes \x08: the pattern never matches any more,
    # without an error. We refuse to start rather than generate wrong letters.
    if _n.startswith("RX_") and hasattr(_rx, "pattern"):
        assert "\x08" not in _rx.pattern, "motif corrompu (backspace littéral) : " + _n


def titre_poste(t: str | None, maxlen: int = 80) -> str:
    """Readable job title from the raw title of a posting.

    Cuts at the last separator BEFORE maxlen, never in the middle of a word.
    Returns "" if it is not a job title (postal address, empty): the caller then
    writes a neutral phrase rather than an absurd sentence.

    Repeated until nothing changes: one cut can make the next one possible — "F -
    CDI - H" only becomes the gender mention "F - H" once the contract is gone.
    Cleaning a clean title again must change nothing (refresh_letters reruns it).
    """
    for _ in range(3):
        propre = _titre_une_passe(t, maxlen)
        if propre == t:
            break
        t = propre
    return t or ""


def _titre_une_passe(t: str | None, maxlen: int) -> str:
    """One pass of titre_poste's cleaning."""
    t = re.sub(r"\s+", " ", (t or "").strip())
    if RX_ADRESSE.search(t):
        return ""
    t = RX_GENRE.sub(" ", t)
    t = RX_GENRE_COLLE.sub("", t)
    t = RX_CONTRAT.sub(" ", t)
    t = RX_BRUIT.sub(" ", t)
    t = RX_REF.sub(" ", t)
    # Parentheses empty or reduced to digits/punctuation by the previous
    # cuts: "CDD (2.5 mois)" left "- (2. )" once the contract
    # and the duration were removed.
    t = re.sub(r"[(\[]\s*[\d.,;:\s-]*\s*[)\]]", " ", t)
    t = re.sub(r"\s*,(\s*,)+", ",", t)
    t = RX_LIEU_FIN.sub("", t)
    # separators: only those SURROUNDED by spaces — "LCB-FT" and "H2-Power"
    # are words, not separators
    t = re.sub(r"\s+[-–—:|]\s+", " - ", t)
    t = re.sub(r"\s*[–—:|]\s*", " - ", t)
    t = re.sub(r"(\s*-\s*){2,}", " - ", t)
    t = re.sub(r"\s{2,}", " ", t).strip(" -,.;:|")
    if len(t) > maxlen:
        coupe = t[:maxlen]
        for sep in (" - ", ", ", " "):
            i = coupe.rfind(sep)
            if i > maxlen * 0.5:
                coupe = coupe[:i]
                break
        t = coupe.strip(" -,.;:|")
    return t


def _coupe_mot(t: str | None, n: int) -> str:
    """Truncates to n characters WITHOUT cutting a word, and without leaving dangling punctuation.

    "…help to build a better wor" went out in a real letter: a quotation cut in
    the middle of a word is more visible than a missing quotation.
    """
    t = " ".join((t or "").split())
    if len(t) <= n:
        return t.rstrip(" ,;:.-")
    coupe = t[:n]
    i = coupe.rfind(" ")
    if i > n * 0.6:
        coupe = coupe[:i]
    return coupe.rstrip(" ,;:.-") + "…"


def company_value(company: str | None) -> str:
    """Known hook for this company, or "": when the company is unknown, the letter lends it NO commitment, it talks about the job."""
    c = (company or "").lower()
    for k, v in _ici.COMPANY_VALUE.items():
        if k in c:
            return str(v)
    return ""


# ── THE HAND-WRITTEN BODY ────────────────────────────────────────────────────
# The template serves 5374 postings. So it cannot say anything specific about
# any of them: it names skills, never a fund, never a mission from
# the posting. That is the right trade-off for mass applying and the
# wrong one for the five offers of the year that deserve an hour of work.
#
# When `Lettres/Sur_mesure/<entreprise>__<poste>.txt` exists, its paragraphs
# replace the BODY. Everything else is still generated: the header, the
# date, the subject, the salutation — which knows how to name two recipients — and
# the agreed closing. We do not rewrite by hand what the code
# does better.
#
# It is an INPUT, just like CV/Modeles: `regenerate_docs.py` does not
# touch it, and regenerating the letter takes it back as is.
_RX_SLUG = re.compile(r"[^a-z0-9]+")


def _slug(s: str | None) -> str:
    return _RX_SLUG.sub("_", (s or "").lower()).strip("_")


# Skill labels in ENGLISH. The English letter quotes them in full;
# leaving them in French betrays automatic generation more
# surely than a style mistake. The regulatory acronyms (SFDR, CSRD, GRI,
# TCFD, PAI) are NOT translated: they are the same European texts.
_PARESSEUX["SKILL_EN"] = lambda: ({lab: v.get("en") or lab for lab, v in _ici._COMP.items()})


_SKILL_EN_NORM = None


def skills_en(labels: list[str]) -> list[str]:
    """Translated labels.

    The search ignores ACCENTS: the keys of SKILL_EN are written without them, the
    real labels carry them ("Analyse financière" versus "Analyse financiere").
    Comparing them as they are found nothing and the English letter stayed stuffed
    with French.

    An unknown label is RETURNED AS IS rather than removed: better a visible French
    word than a skill that disappeared.
    """
    global _SKILL_EN_NORM
    if _SKILL_EN_NORM is None:
        from jobhunter.programs.util import sans_accent

        _SKILL_EN_NORM = {sans_accent(k).lower(): v for k, v in _ici.SKILL_EN.items()}
    from jobhunter.programs.util import sans_accent

    return [_SKILL_EN_NORM.get(sans_accent(x).lower(), x) for x in labels]


# Labels used for SCORING but not written in a letter: they
# are internal category names, not skills. "Durabilité / ESG
# (généraliste)" ended up as is, parentheses included, in an
# English letter sent to EY Geneva — between SFDR and GRI/TCFD, it
# gave away the system that had written it.
_PARESSEUX["SKILL_INTERNES"] = lambda: ({lab for lab, v in _ici._COMP.items() if v.get("interne")})


def match_skills(offer_text: str | None, max_n: int = 8) -> list[str]:
    """The lexicon's skills present in a posting, excluding internal skills.

    Args:
        offer_text: the posting's text.
        max_n: maximum number of skills returned.

    Returns:
        The labels found, in lexicon order.
    """
    t = (offer_text or "").lower()
    hits = []
    for label in _ici.SKILL_LEX:
        if label in _ici.SKILL_INTERNES:
            continue
        if has_skill(label, t):
            hits.append(label)
    # neutral base (no ESG bias) if the offer is poor in text
    if len(hits) < 3:
        for base in _P.get("competences_de_base", []) or []:
            if base not in hits:
                hits.append(base)
    return hits[:max_n]
