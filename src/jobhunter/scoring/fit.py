"""jobhunter.scoring.fit (formerly Scripts/ats_match.py).

ats_match.py — ATS scoring in the style of Resume-Matcher (light, offline).

For each offer: extracts the REQUIRED skills (in Missions + Required profile), looks at
which ones are COVERED by the chosen CV variant, computes a match % and lists the
MISSING skills (gaps to add to the CV/letter).

Reuses tailor_application's multi-profile lexicon (SKILL_LEX).

Run:
    python -m jobhunter.scoring.fit --company Amundi
    python -m jobhunter.scoring.fit --all --min 0          # full report -> ats_report.csv
    python -m jobhunter.scoring.fit --n 12
"""

import re
import sys
from dataclasses import dataclass
from typing import Any

try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]  # console : TextIOWrapper
except Exception:
    pass

import importlib

from jobhunter import lazy as _paresseux
from jobhunter import profile as _P
from jobhunter import root as _racine
from jobhunter.paths import CV_MODELES as CV_ATS
from jobhunter.scoring import lexicon as _lexique
from jobhunter.scoring import weights as _poids
from jobhunter.scoring.lexicon import cv_variant_key, has_skill

_ici = sys.modules[__name__]
# Values taken from the profile: computed on first read, not at import
# (jobhunter.lazy). In this module, they are read through `_ici.NAME`.
_PARESSEUX: _paresseux.Fabriques = {}


def __getattr__(nom: str) -> Any:
    return _paresseux.lire(_ici, _PARESSEUX, nom)


_PARESSEUX["CV_VARIANT"] = lambda: importlib.import_module("jobhunter.scoring.lexicon").CV_VARIANT


_PARESSEUX["SKILL_LEX"] = lambda: importlib.import_module("jobhunter.scoring.lexicon").SKILL_LEX


ROOT = _racine.racine()
OUT_CSV = _racine.scripts() / "ats_report.csv"


def cv_text(variant_key: str) -> str:
    """Texte concaténé du CV variant (lower)."""
    p = CV_ATS / _ici.CV_VARIANT[variant_key]
    if not p.exists():
        return ""
    try:
        # A PDF CV read as a .docx gave "": every offer at ATS 0 % (2026-10-24). Text
        # boxes, content controls and headers count too (jobhunter.cv_text).
        from jobhunter.cv_text import texte_fichier

        return " ".join(texte_fichier(p).split("\n")).lower()
    except Exception:
        return ""


_cv_cache: dict[str, str] = {}


def cv_text_cached(k: str) -> str:
    """The text of a variant's CV, read once per process.

    Args:
        k: the CV variant key (domain).

    Returns:
        The text of the CV.
    """
    if k not in _cv_cache:
        _cv_cache[k] = cv_text(k)
    return _cv_cache[k]


def skills_in(text: str | None) -> set[str]:
    """Set of the SKILL_LEX labels present in the text.

    Matcher shared with tailor_application (has_skill): short acronyms = WHOLE word,
    long phrases = substring. Avoids the false positives 'ges' in "GEStion", 'gri' in
    "aGRIcole", 'pai' in "PAIement".
    """
    return _lexique.skills_present((text or "").lower())


# ── Required experience detector ──
# Not the "5" of "3.5 years": a digit after a decimal point is not a number of years.
_EXP_NUM = re.compile(r"(?<![\d.,])(\d{1,2})\s*(?:\+|ans?|an\b|années?|years?|yrs?)\+?", re.I)
# "years of" alone is not a context: "over 15 years of working together" is the
# company's age. "5 years of relevant experience" still has "experien" in its window.
_EXP_CTX = re.compile(
    r"(exp[ée]rien|experien|ann[ée]es?\s+d|d['e]\s*exp(?!ert)|years?\s+of\s+(?:relevant|related|"
    r"professional|post|combined|progressive|industry|prior|previous|practical|hands-on|"
    r"demonstrated|proven|direct|work\s+exp))",
    re.I,
)
# Years that describe someone else: "une équipe apportant en moyenne 10 ans
# d'expérience" (BNP AM) is the team's, the posting asked for 2.
_EXP_AUTRUI = re.compile(r"(en moyenne|on average|cumul[ée]e?s?|apportant|combined team)\W*$", re.I)
# Target level: profil.json, "niveau" section. Searched in the TITLE alone
# (see fit_detail); "lead" is not there as a substring — it catches "Lead
# Generation" — it is `senior_en_fin` that handles it, with the right negation.
_PARESSEUX["JUNIOR"] = lambda: tuple(_P.get("niveau.mots_junior", []) or [])
_PARESSEUX["SENIOR"] = lambda: tuple(_P.get("niveau.mots_senior", []) or [])
_PARESSEUX["_RX_SENIOR_FIN"] = lambda: _P.motif(_P.get("niveau.senior_en_fin", []))
_PARESSEUX["NEG"] = lambda: tuple(_P.get("niveau.mots_negatifs", []) or [])


_EXP_FOURCHETTE = re.compile(
    r"\b(\d{1,2})\s*(?:à|a|-|–|to|bis)\s*\d{1,2}\s*(?=ans?\b|années?|years?|yrs?|jahre)", re.I
)

_JUNIOR_OFFRE = (
    "alternance",
    "alternant",
    "apprenti",
    "stage",
    "stagiaire",
    "internship",
    "intern ",
    "working student",
    "jeune diplôm",
    "débutant",
    "debutant",
    "entry level",
    "graduate program",
    "grad program",
    "trainee",
)

# Experience asked for without a number of years. "Expérience confirmée" is what the
# Caisse des Dépôts and many French postings write instead of "3 à 5 ans"; LinkedIn
# adds its own "Niveau hiérarchique : Confirmé / Mid-Senior level" to the text.
# "première expérience confirmée/réussie" is a junior's first job: left out.
_EXP_QUALITATIVE = [
    (
        re.compile(
            r"(?<!premi[eè]re )(?<!premiere )\b(?:exp[ée]rience (?:confirm[ée]e|significative|solide|"
            r"approfondie|av[ée]r[ée]e)|solide exp[ée]rience|exp[ée]rience professionnelle "
            r"confirm[ée]e|(?:significant|extensive|proven|substantial|solid) (?:\w+ ){0,2}"
            r"experience|niveau hi[ée]rarchique :? ?confirm[ée]|seniority level :? ?mid-senior)",
        ),
        3,
    ),
    (
        re.compile(
            r"(?:niveau hi[ée]rarchique :? ?directeur|seniority level :? ?(?:director|executive))"
        ),
        7,
    ),
]


def experience_years(text: str | None, titre: str | None = None) -> int:
    r"""Years of experience REQUIRED detected (0 if none).

    Takes the max of the numbers appearing near an 'expérience' word. E.g. '10 ans
    d'expérience' → 10. Cap 15 (>15 = noise: age, company seniority…). Ignored if the
    job is junior/work-study.

    Blanks are COLLAPSED before the search. The context window is only 28 characters
    on either side of the number, and structured postings separate the label from its
    value with bursts of carriage returns:

        Niveau d'expérience \r\n \r\n \r\n \r\n Plus de 10 ans

    The word "expérience" then fell outside the window and the requirement went
    unnoticed. CNP "EXPERT INVESTISSEMENT RESPONSABLE" thus came out at fit 10 with
    exp_requise = 0 while the posting asks for more than ten years.

    THE JUNIOR TEST READS THE TITLE when it is given. On the whole text, one word was
    enough: "2 années d'expérience minimum (stages et alternance compris)" (BNP AM), a
    "manage interns" line, an "INTERNSHIP" tag in a job board's footer — and the
    requirement went to 0, the offer to fit 10. Seven of the twenty offers the user set
    aside by October 2026 asked for experience the engine had not seen.
    """
    t = re.sub(r"\s+", " ", (text or "")).replace("’", "'").lower()
    # A range asks for its LOWER bound: "3 à 5 ans" is met with 3. Read as 5, it reached
    # the sort's experience_max and removed offers a three-year candidate qualifies for.
    t = _EXP_FOURCHETTE.sub(r"\1 ", t)  # the unit stays: "1-2 years of" → "1 years of"
    porte = re.sub(r"\s+", " ", titre).lower() if titre is not None else t
    if any(k in porte for k in _JUNIOR_OFFRE):
        return 0  # junior offer: an isolated '10 ans' = noise
    yrs = 0
    for rx, n in _EXP_QUALITATIVE:
        if rx.search(t):
            yrs = max(yrs, n)
    for m in _EXP_NUM.finditer(t):
        a, b = m.start(), m.end()
        # WINDOW WIDER ON THE LEFT THAN ON THE RIGHT. The requirement is almost
        # always written "expérience … de N ans": the trigger word precedes the
        # number, often by far. "expérience professionnelle antérieure de
        # 3 à 5 ans" puts "expérience" 44 characters away from "5 ans" — outside
        # a window of 28, and the Crédit Mutuel AM offer (3 to 5 years required)
        # came out at exp_requise = 0. On the RIGHT we stay tight: "5 ans"
        # followed thirty characters further by an "expérience" belonging to
        # the next sentence says nothing about that number.
        ctx = t[max(0, a - 70) : min(len(t), b + 28)]
        if _EXP_CTX.search(ctx) and not _EXP_AUTRUI.search(t[max(0, a - 30) : a]):
            n = int(m.group(1))
            if 1 <= n <= 15:  # realistic exp; >15 = age/seniority → ignored
                yrs = max(yrs, n)
    return yrs


# ── VECTOR scoring: weighted axes, instead of "+1 per skill" ──
# L'ancien fit = 2 + len(skills_in) saturait : « Assistant administratif » matchait
# Excel + English + Communication and came out 10/10. The GENERIC skills
# (office tools, languages) are in NO axis: they do not raise the score.
#
# Everything comes from the profile ("scoring" section):
#   axes            {name: {poids, competences}} — the CORE axis is the first
#                   target, the COMPLEMENT axis a secondary target
#   cible_score     weighted sum that is worth fit = 10
#   saturation_axe  an axis saturates at N distinct labels (we do not divide by the
#                   size of the axis: a wide axis would be mechanically disadvantaged)
_PARESSEUX["_SC"] = lambda: _P.get("scoring", {}) or {}
_PARESSEUX["AXES"] = lambda: (
    {a: list(v.get("competences") or []) for a, v in (_ici._SC.get("axes") or {}).items()}
)
_PARESSEUX["POIDS"] = lambda: (
    {a: float(v.get("poids", 1.0)) for a, v in (_ici._SC.get("axes") or {}).items()}
)
_PARESSEUX["COEUR"] = lambda: (
    _ici._SC.get("axe_coeur") or (next(iter(_ici.AXES)) if _ici.AXES else "")
)
_PARESSEUX["COMPLEMENT"] = lambda: _ici._SC.get("axe_complement") or ""
_PARESSEUX["_CAP"] = lambda: int(_ici._SC.get("saturation_axe", 3))
_PARESSEUX["_TARGET"] = lambda: float(_ici._SC.get("cible_score", 3.0))
_PARESSEUX["_PLAFOND_SANS_COEUR"] = lambda: float(_ici._SC.get("plafond_sans_coeur", 6.0))
_PARESSEUX["_PLAFOND_COMPLEMENT"] = lambda: float(_ici._SC.get("plafond_complement", 8.0))
_PARESSEUX["_PLAFOND_SECOND"] = lambda: float(_ici._SC.get("plafond_second", 8.0))
_PARESSEUX["_PLAFOND_VETO"] = lambda: float(_ici._SC.get("plafond_veto", 6.0))

# TITLES. The title says what the job IS, the description only
# mentions subjects: it is the one that raises or lowers the cap.
#   intitules_coeur        raises the cap to 10, except off-target profession
#   intitules_coeur_forts  raises the cap to 10 in all cases
#   intitules_second       profession targeted second: cap 8 (+2 x core axis)
#   veto_sigles / veto_si + veto_et: neighbouring profession to set aside (cap 6)
#   intitules_techniques (except ..._sauf) and intitules_hors_metier: the
#     target's vocabulary does not bring these professions closer to the profile
# The historical names (_ESG_TITLE_RX…) stay: the tests and the density read them.
_PARESSEUX["_ESG_TITLE_RX"] = lambda: _P.motif(_ici._SC.get("intitules_coeur"))
_PARESSEUX["_ESG_TITRE_FORT"] = lambda: _P.motif(_ici._SC.get("intitules_coeur_forts"))
_PARESSEUX["_TITRE_FINANCE"] = lambda: _P.motif(_ici._SC.get("intitules_second"))
_PARESSEUX["_RX_HSE_SIGLE"] = lambda: _P.motif(_ici._SC.get("veto_sigles"))
_PARESSEUX["_RX_SECURITE"] = lambda: _P.motif(_ici._SC.get("veto_si"))
_PARESSEUX["_RX_SANTE_ENV"] = lambda: _P.motif(_ici._SC.get("veto_et"))
_PARESSEUX["_RX_TECHNIQUE_TITRE"] = lambda: _P.motif(_ici._SC.get("intitules_techniques"))
_PARESSEUX["_RX_TITRE_FINANCE"] = lambda: _P.motif(_ici._SC.get("intitules_techniques_sauf"))
_PARESSEUX["_RX_HORS_METIER"] = lambda: _P.motif(_ici._SC.get("intitules_hors_metier"))
_c = _P.cherche


def _titre_hse(role: str) -> bool:
    """Title of a neighbouring profession to set aside (sustainable finance example: HSE)."""
    return bool(
        _c(_ici._RX_HSE_SIGLE, role)
        or (_c(_ici._RX_SECURITE, role) and _c(_ici._RX_SANTE_ENV, role))
    )


def _titre_hors_cible(role: str) -> bool:
    """Technical or off-profession job: the target's vocabulary does not bring it closer to the profile."""
    tech = _c(_ici._RX_TECHNIQUE_TITRE, role) and not _c(_ici._RX_TITRE_FINANCE, role)
    return bool(tech or _c(_ici._RX_HORS_METIER, role))


# ── Anti-boilerplate ─────────────────────────────────────────────────────────
# A company description of 8000 characters that says ONCE each of
# three words of the target saturates the axis: it is employer talk, not the
# job. The DENSITY (core title markers per 1000 characters) separates
# the two; below the threshold, the core axis is reduced pro rata.
_PARESSEUX["_ESG_DENSITE_MIN"] = lambda: float(
    _ici._SC.get("densite_coeur_min", 1.0)
)  # markers per 1000 characters
_PARESSEUX["_ESG_DENSITE_LONG"] = lambda: int(
    _ici._SC.get("densite_coeur_longueur", 800)
)  # below that, the text is too short for a density to mean anything


def densite_esg(text: str | None) -> float:
    """ESG markers per 1000 characters. 0.0 on an empty text."""
    t = text or ""
    if not t or _ici._ESG_TITLE_RX is None:
        return 0.0
    return 1000.0 * sum(1 for _ in _ici._ESG_TITLE_RX.finditer(t)) / len(t)


def axis_scores(text: str | None) -> dict[str, float]:
    """Density 0.0-1.0 per axis. Useful to understand WHY an offer scores."""
    got = skills_in(text)
    out: dict[str, float] = {}
    for axe, labels in _ici.AXES.items():
        cap = min(_ici._CAP, len(labels)) or 1
        out[axe] = min(sum(1 for l in labels if l in got), cap) / cap
    # The ESG axis, and it alone, is reduced when its markers are drowned: it is
    # the only one that raises the fit cap, hence the only one where a passing mention
    # costs a lot. A short text escapes the check — "Analyste ESG" alone
    # is 12 characters for one marker, its density makes no sense.
    if (
        out.get(_ici.COEUR, 0) > 0
        and _ici._ESG_TITLE_RX is not None
        and len(text or "") >= _ici._ESG_DENSITE_LONG
    ):
        d = densite_esg(text)
        if d < _ici._ESG_DENSITE_MIN:
            out[_ici.COEUR] *= d / _ici._ESG_DENSITE_MIN
    return out


_PARESSEUX["_NIV"] = lambda: _P.get("niveau", {}) or {}
_PARESSEUX["_BONUS_JUNIOR"] = lambda: float(_ici._NIV.get("bonus_junior", 1.0))
_PARESSEUX["_MALUS_SENIOR"] = lambda: float(_ici._NIV.get("malus_senior", 2.0))
_PARESSEUX["_MALUS_EXP"] = lambda: sorted(
    ((int(k), float(v)) for k, v in (_ici._NIV.get("malus_experience") or {}).items()), reverse=True
)


def _malus_experience(yrs: int) -> float:
    """Penalty for `yrs` years required: the highest step reached."""
    return next((m for seuil, m in _ici._MALUS_EXP if yrs >= seuil), 0.0)


def fit_score(text: str | None, title: str | None = "") -> tuple[int, int]:
    """(fit entier 1-10, annees d'experience exigees). Voir fit_detail."""
    fit, yrs, _fin = fit_detail(text, title)
    return fit, yrs


# ── LANGUAGE: an offer in a language the user does not speak ────────────────
# The professional vocabulary (ESG, reporting, analyst) is the same in all
# languages: without this rule, a posting in Dutch came out at 10 for someone who
# does not read Dutch. Two cases, two caps:
#   - posting WRITTEN in a language not spoken -> 2 (unreadable)
#   - posting that REQUIRES a language not spoken ("fluent Dutch", "Nederlands
#     vereist") -> 4. "Dutch is a plus" requires nothing: ignored.
# Languages spoken: profile "langues_parlees" (codes fr, en, de, es, it, nl, pt...).
_PARESSEUX["LANGUES_PARLEES"] = lambda: set(_P.get("langues_parlees", ["fr", "en"]) or ["fr", "en"])

# Function words specific to each language (articles, pronouns, prepositions) and
# a few posting words without an equivalent elsewhere. Words common to two
# languages ("de", "en", "die") are avoided.
_MOTS_OUTILS = {
    "fr": {
        "le",
        "la",
        "les",
        "des",
        "du",
        "et",
        "pour",
        "vous",
        "nous",
        "avec",
        "dans",
        "une",
        "sur",
    },
    "en": {"the", "and", "you", "with", "our", "for", "will", "are", "your", "this", "that", "of"},
    "de": {"und", "der", "wir", "sie", "mit", "für", "ist", "das", "eine", "auf", "zu", "ihre"},
    "nl": {
        "het",
        "een",
        "wij",
        "jij",
        "jouw",
        "voor",
        "zijn",
        "bij",
        "ons",
        "onze",
        "wordt",
        "naar",
        "ook",
        "deze",
        "dit",
        "wat",
        "ervaring",
        "kennis",
        "functie",
        "solliciteren",
        "vacature",
        "werkzaamheden",
        "beheer",
    },
    "es": {"los", "las", "para", "con", "una", "del", "por", "nuestro", "nuestra", "usted", "y"},
    "it": {"il", "della", "delle", "per", "con", "gli", "nostro", "nostra", "sono", "nel"},
    "pt": {"os", "para", "com", "uma", "nosso", "nossa", "você", "não", "pelo", "pela"},
    "pl": {"jest", "oraz", "dla", "się", "przez", "jako", "nasz", "nasza", "lub", "które"},
    "sv": {"och", "att", "för", "med", "som", "är", "vår", "våra", "har", "inom"},
    "da": {"og", "af", "til", "med", "som", "er", "vores", "har", "inden", "skal"},
}
_RX_MOT = re.compile(r"[a-zà-ÿąćęłńóśźżåæø]+")

# Names of each language, as a posting writes them (English, French,
# the language itself, Dutch). The spoken languages leave the list of
# "foreign" languages and serve to recognise an alternative.
_NOMS_LANGUES = {
    "fr": r"french|fran[cç]ais|frans",
    "en": r"english|anglais|engels",
    "de": r"german|allemand|deutsch|duits",
    "nl": r"dutch|nederlands|n[ée]erlandais|flemish|vlaams|flamand",
    "es": r"spanish|espa[ñn]ol|espagnol|castellano",
    "it": r"italian|italiano|italien",
    "pt": r"portuguese|portugu[eê]s|portugais",
    "pl": r"polish|polski|polonais",
    "sv": r"swedish|svenska|su[ée]dois",
    "da": r"danish|dansk|danois",
    "no": r"norwegian|norsk|norv[ée]gien",
    "fi": r"finnish|finnois",
    "cs": r"czech|tch[eè]que",
    "hu": r"hungarian|hongrois",
    "ro": r"romanian|roumain",
    "el": r"greek|grec",
    "ja": r"japanese|japonais",
    "zh": r"mandarin|chinese|chinois|cantonese",
    "ar": r"arabic|arabe",
    "ru": r"russian|russe",
    "tr": r"turkish|turc",
    "ko": r"korean|cor[ée]en",
}


# Scripts other than the Latin one: the function words above cannot see them, so a
# posting in Japanese or Korean came out "undecided" and kept its fit (the user,
# 2026-10-26: 103 offers in CJK, Hangul, Hebrew, Greek, Cyrillic… in the queue).
# Kana before the ideographs: a Japanese text uses both, a Chinese one only the second.
_ECRITURES = (
    ("ja", re.compile(r"[\u3040-\u30ff]")),
    ("zh", re.compile(r"[\u4e00-\u9fff]")),
    ("ko", re.compile(r"[\uac00-\ud7af\u1100-\u11ff]")),
    ("th", re.compile(r"[\u0e00-\u0e7f]")),
    ("he", re.compile(r"[\u0590-\u05ff]")),
    ("ar", re.compile(r"[\u0600-\u06ff]")),
    ("el", re.compile(r"[\u0370-\u03ff]")),
    ("ru", re.compile(r"[\u0400-\u04ff]")),
    ("hi", re.compile(r"[\u0900-\u097f]")),
    ("bn", re.compile(r"[\u0980-\u09ff]")),
    ("ta", re.compile(r"[\u0b80-\u0bff]")),
    ("ka", re.compile(r"[\u10a0-\u10ff]")),
    ("hy", re.compile(r"[\u0530-\u058f]")),
)
_RX_LETTRE = re.compile(r"[^\W\d_]")


def _ecriture(t: str) -> str:
    """Code of a non-Latin script making a fifth of the letters (at least 30), else ''."""
    lettres = len(_RX_LETTRE.findall(t))
    for code, rx in _ECRITURES:
        n = len(rx.findall(t))
        # Japanese: the kana alone are fewer than the ideographs around them.
        if code == "ja" and n >= 10:
            n += len(_ECRITURES[1][1].findall(t))
        if n >= 30 and n >= 0.2 * lettres:
            return code
    return ""


def _compte_langues(mots: list[str]) -> dict[str, int]:
    return {k: sum(1 for m in mots if m in v) for k, v in _MOTS_OUTILS.items()}


def langue_redaction(t: str | None) -> str:
    """Code of the dominant language of the text ('' if the text is too short or undecided).

    The HEADER counts separately: EURES automatically translates Dutch postings into
    English; the English body won (26 function words against 4). The first lines are
    the employer's: if they are clearly in a language not spoken, the posting is.
    """
    ecrite = _ecriture((t or "")[:4000])
    if ecrite:
        return ecrite
    tete = _compte_langues(_RX_MOT.findall((t or "")[:600].lower()))
    lg = max(tete, key=tete.__getitem__)
    parlees = [tete[k] for k in _ici.LANGUES_PARLEES if k in tete] or [0]
    if lg not in _ici.LANGUES_PARLEES and tete[lg] >= 4 and tete[lg] >= 2 * max(parlees):
        return lg
    mots = _RX_MOT.findall((t or "")[:4000].lower())
    if len(mots) < 60:
        return ""
    compte = _compte_langues(mots)
    ordre = sorted(compte, key=compte.__getitem__, reverse=True)
    premier, second = compte[ordre[0]], compte[ordre[1]]
    if premier < 12 or premier < 1.5 * second:
        return ""
    return ordre[0]


_PARESSEUX["_LANGUES_ETRANGERES"] = lambda: (
    "(?:" + "|".join(v for k, v in _NOMS_LANGUES.items() if k not in _ici.LANGUES_PARLEES) + ")"
)
_PARESSEUX["_PARLEES"] = lambda: (
    "(?:" + "|".join(v for k, v in _NOMS_LANGUES.items() if k in _ici.LANGUES_PARLEES) + ")"
)
# The language name designates a market or an entity, not a skill:
# « strong presence in Chinese markets », « Dutch GAAP », « Italian clients ».
_PAS_UNE_LANGUE = (
    r"(?![\s-]+(?:markets?|clients?|customers?|compan\w*|business\w*|teams?"
    r"|entit\w*|subsidiar\w*|operations?|government|law|gaap|regulat\w*"
    r"|portfolio|assets?|real\s+estate|banks?|offices?|sites?)\b)"
)
# "Fluent in English and Dutch", "maitrise du neerlandais". Only words
# that talk about LANGUAGE introduce it: "strong", "excellent" preceded
# a market just as well.
_PARESSEUX["_RX_LANGUE_AVANT"] = lambda: re.compile(
    r"\b(?:fluen(?:t|cy)|native|mother\s+tongue|proficien\w*|business[- ]level"
    r"|courant|ma[iî]trise|bilingue?|bilingual|vloeiend)\W+(?:\w+\W+){0,4}?"
    + _ici._LANGUES_ETRANGERES
    + r"\b"
    + _PAS_UNE_LANGUE,
    re.I,
)
# « Dutch is required », « Dutch speaking », « Nederlands vereist », « neerlandais exige »
_PARESSEUX["_RX_LANGUE_APRES"] = lambda: re.compile(
    r"\b"
    + _ici._LANGUES_ETRANGERES
    + _PAS_UNE_LANGUE
    + r"\W+(?:\w+\W+){0,3}?(?:required|mandatory|essential|must|speak(?:ing|er)s?|native"
    r"|fluent|fluency|language|skills|proficiency|vereist|noodzakelijk|verplicht"
    r"|exig[ée]e?|obligatoire|indispensable|requis[e]?|courant)\b",
    re.I,
)
# A "neerlandophone" posting requires Dutch.
_RX_NEERLANDOPHONE = re.compile(r"\bnederlandstalig\w*|\bnederlandse\s+taal\b", re.I)
# What follows the language and makes it optional.
_RX_FACULTATIF = re.compile(
    r"^\W*(?:\w+\W+){0,4}?(?:a\s+|an\s+)?(?:plus|asset|advantage|bonus|nice[- ]to[- ]have"
    r"|prefer\w*|desirable|beneficial|atout|souhait\w*|appr[ée]ci\w*|pluspunt|voordeel)\b",
    re.I,
)
# What PRECEDES the language and makes it optional: "preferable in Dutch too".
_RX_FACULTATIF_AVANT = re.compile(
    r"\b(?:prefer\w*|ideally|id[ée]alement|optional\w*|souhait\w*|bonus|plus)\W+(?:\w+\W+){0,2}$",
    re.I,
)
# An alternative with a spoken language requires nothing: "Dutch and/or French".
_PARESSEUX["_RX_ALTERNATIVE"] = lambda: re.compile(
    r"(?:"
    + _ici._PARLEES
    + r"\s*(?:and\s*/\s*or|et\s*/\s*ou|or|ou|of)\s+"
    + _ici._LANGUES_ETRANGERES
    + r"|"
    + _ici._LANGUES_ETRANGERES
    + r"\s*(?:and\s*/\s*or|et\s*/\s*ou|or|ou|of)\s+"
    + _ici._PARLEES
    + r")\b",
    re.I,
)
_PARESSEUX["_RX_NOM_LANGUE"] = lambda: re.compile(r"\b" + _ici._LANGUES_ETRANGERES + r"\b", re.I)


def langue_exigee(t: str | None) -> str:
    """Name of a language not spoken that the posting REQUIRES, otherwise ''."""
    t = t or ""
    if "nl" not in _ici.LANGUES_PARLEES and _RX_NEERLANDOPHONE.search(t):
        return "nederlands"
    for rx in (_ici._RX_LANGUE_AVANT, _ici._RX_LANGUE_APRES):
        for m in rx.finditer(t):
            nom: re.Match[str] | None = _ici._RX_NOM_LANGUE.search(m.group(0))
            debut = nom.start() + m.start() if nom else m.start()
            fin = nom.end() + m.start() if nom else m.end()
            if _RX_FACULTATIF.search(t[fin : fin + 60]):
                continue
            if _RX_FACULTATIF_AVANT.search(t[max(0, debut - 40) : debut]):
                continue
            if _ici._RX_ALTERNATIVE.search(t[max(0, debut - 30) : fin + 30]):
                continue
            return (nom.group(0) if nom else m.group(0)).lower()
    return ""


def plafond_langue(t: str | None) -> tuple[float, str]:
    """(cap, reason): 2 if written in a language not spoken, 4 if it requires one, (10, '') otherwise."""
    lg = langue_redaction(t)
    if lg and lg not in _ici.LANGUES_PARLEES:
        return 2.0, f"redigee en {lg}"
    exige = langue_exigee(t)
    if exige:
        return 4.0, f"exige {exige}"
    return 10.0, ""


def fit_detail(
    text: str | None,
    title: str | None = "",
    raisons: list[str] | None = None,
    poids: "_poids.Ponderation | None" = None,
) -> tuple[int, int, float]:
    """(fit, yrs, fit_fin). `fit_fin` breaks ties between offers with the same fit.

    `raisons`, if passed, receives each step of the computation in plain words (see
    `expliquer`); the computation is the same with or without it. `poids`: other
    weights than the active profile's (the "Comprendre le fit" panel, before saving).

    The user, 2026-10-09: 546 offers at 10, 1203 at 8, 3321 at 6 — within a level, the
    order meant nothing. fit_fin = fit +/- 0.45: its rounding ALWAYS returns `fit`, no
    threshold (>= 8...) moves. Within the level, it follows _departage: ESG title, ESG
    density, skills cited, experience.

    Vector fit 1-10: 6 weighted axes (ESG ×3, finance ×2, AI ×1.5, rest ×1), then
    junior/senior/sales penalties and the EXPERIENCE PENALTY (the user is junior).

    `title`: the seniority/role penalties apply to the title ALONE when it is
    provided. Searched in the whole description, they produce false positives —
    "Lead Generation" triggered the SENIOR penalty and "présence commerciale" the NEG
    penalty, i.e. −4 on an offer that is neither senior nor sales.
    The level and the type of job are read in the title, not in the company's
    presentation.
    """
    t = (text or "").lower()
    role = (title or text or "").lower()
    c = composantes(text, title)
    p = poids or ponderation()
    fit = fit_de(c, p)
    if raisons is not None:
        got = skills_in(t)
        for axe, labels in _ici.AXES.items():
            trouves = [l for l in labels if l in got]
            if trouves:
                raisons.append(
                    f"{axe} {c.axes[axe]:.0%} (x{p.axes[axe]:g}) : " + ", ".join(trouves[:6])
                )
        raisons.append(f"vocabulaire : {_vocabulaire(c, p):.1f}/10")
        raisons.extend(c.notes)
        if c.junior:
            raisons.append(f"intitulé junior « {c.junior} » : +{p.bonus_junior:g}")
        if c.senior:
            raisons.append(f"intitulé senior : -{p.malus_senior:g}")
        if c.ecarte:
            raisons.append(f"intitulé écarté « {c.ecarte} » : -2")
        if c.note_langue:
            raisons.append(c.note_langue)
        if p.malus_annees(c.annees):
            raisons.append(
                f"{c.annees} an(s) d'expérience demandés : -{p.malus_annees(c.annees):g}"
            )
    entier = max(1, min(10, round(fit)))
    yrs = c.annees
    return entier, yrs, round(entier - 0.45 + 0.9 * _departage(t, role, fit, entier, yrs), 3)


@dataclass(frozen=True)
class Composantes:
    """What the fit of an offer is made of, apart from the weights the user can tune.

    `axes`: share of each axis covered by the text (0..1). `plafond`: the cap set by the
    core share, the title and the language. `junior`/`ecarte`: the word of the title that
    triggers the bonus / the penalty ("" = none). `annees`: experience asked for.
    `notes`/`note_langue`: the steps of the cap, in plain words, for `expliquer`.
    """

    axes: dict[str, float]
    plafond: float
    junior: str
    senior: bool
    ecarte: str
    annees: int
    notes: tuple[str, ...] = ()
    note_langue: str = ""


def ponderation() -> _poids.Ponderation:
    """The weights of the active profile."""
    return _poids.Ponderation(
        axes=dict(_ici.POIDS),
        cible=_ici._TARGET,
        bonus_junior=_ici._BONUS_JUNIOR,
        malus_senior=_ici._MALUS_SENIOR,
        malus_experience=dict(_ici._MALUS_EXP),
    )


def _vocabulaire(c: Composantes, p: _poids.Ponderation) -> float:
    raw = sum(c.axes[a] * p.axes.get(a, 0.0) for a in c.axes)
    return 1 + 9 * min(1.0, raw / p.cible)  # 1..10, no stacked magic number


def fit_de(c: Composantes, p: _poids.Ponderation | None = None) -> float:
    """The fit before rounding, from the components and the weights.

    The active profile's weights by default. Same operations, in the same order, as
    before the split (3.18).
    """
    p = p or ponderation()
    fit = _vocabulaire(c, p)
    # THE BONUSES FIRST, THE CAP AFTERWARDS. The cap was applied before, and
    # the junior bonus went over it: "Auditeur junior analyste" came out at
    # 10 with a cap computed at 8.7. A cap that a bonus can exceed
    # caps nothing — and the rule "neither ESG nor AI -> 6 max" no longer held.
    if c.junior:
        fit += p.bonus_junior
    if c.senior:
        fit -= p.malus_senior
    if c.ecarte:
        fit -= 2
    fit = min(fit, c.plafond)
    return fit - p.malus_annees(c.annees)


def fit_entier(c: Composantes, p: _poids.Ponderation | None = None) -> int:
    """The integer fit 1..10 shown in the queue."""
    return max(1, min(10, round(fit_de(c, p))))


def composantes(text: str | None, title: str | None = "") -> Composantes:
    """Reads in the offer everything the fit needs, except the weights. See fit_detail."""
    t = (text or "").lower()
    role = (title or text or "").lower()
    sc = axis_scores(t)
    notes: list[str] = []
    # CAP BY PROFILE PRIORITY. Without it, finance + risk + consulting are enough
    # to reach _TARGET without the slightest ESG signal: 251 offers came out at
    # fit >= 8 with the ESG axis at ZERO, and the TOP 25 only contained 3
    # ESG titles. The score measured the richness of the vocabulary, not the fit.
    #   ESG present            -> jusqu'a 10 (coeur de cible)
    #   no ESG but AI          -> 8 max (market targeted as a complement)
    #   neither ESG nor AI     -> 6 max (finance fallback, never ahead of an ESG offer)
    # The cap follows the ESG DENSITY, not its mere presence: a single label
    # caught in passing in a long description (esg=0.33) was enough to get round
    # a binary cap, and "ANALYSTE M&A" stayed at 10.
    #   esg 0.00 -> 6   esg 0.33 -> 7.3   esg 0.67 -> 8.7   esg 1.00 -> 10
    coeur = sc.get(_ici.COEUR, 0.0) if _ici.COEUR else 1.0  # without a core axis: no cap
    compl = sc.get(_ici.COMPLEMENT, 0.0) if _ici.COMPLEMENT else 0.0
    cap = _ici._PLAFOND_SANS_COEUR + (10.0 - _ici._PLAFOND_SANS_COEUR) * coeur
    if coeur == 0 and compl >= 0.5:
        cap = _ici._PLAFOND_COMPLEMENT  # cible secondaire
    if _c(_ici._TITRE_FINANCE, role):
        cap = max(
            cap, _ici._PLAFOND_SECOND + (10.0 - _ici._PLAFOND_SECOND) * coeur
        )  # profession targeted second
        notes.append("intitulé du métier visé en second (finance)")
    # An explicitly ESG title raises the cap: the title says what the
    # job IS, the description only mentions subjects.
    fort = _c(_ici._ESG_TITRE_FORT, role)
    hors = _titre_hors_cible(role)
    if fort or (_c(_ici._ESG_TITLE_RX, role) and not hors):
        cap = 10.0
        notes.append("intitulé du cœur de cible : plafond 10")
    else:
        notes.append(f"plafond {cap:.1f} (cœur {coeur:.0%}, complément {compl:.0%})")
    # Vetoes last: HSE, technical or non-finance profession win over
    # the environmental vocabulary of the title AND of the description, never
    # over an ESG-finance marker. The technical profession only lost the
    # raise given by the title: a description dense in carbon still returned
    # even 10 for "Engineer Sustainability & Product Compliance".
    # The profession veto's cap follows the general rule: 8 if the job talks
    # about AI (secondary target), 6 otherwise. A cap fixed at 6 cost two
    # points to 137 "AI Engineer" jobs that nobody judged too high.
    if not fort and _titre_hse(role):
        cap = min(cap, _ici._PLAFOND_VETO)
        notes.append(f"intitulé HSE : plafond {cap:g}")
    elif not fort and hors:
        cap = min(cap, _ici._PLAFOND_COMPLEMENT if compl >= 0.5 else _ici._PLAFOND_VETO)
        notes.append(f"métier hors cible dans l'intitulé : plafond {cap:g}")
    # JUNIOR ON THE TITLE ALONE, like SENIOR and NEG. It was also searched
    # in the whole description: an "... ouvert aux alternants" at the bottom
    # of a posting gave +1 to a job that has nothing junior about it. It is exactly
    # the false positive already fixed for the two other lists, left here.
    junior = next((k.strip() for k in _ici.JUNIOR if k in role), "")
    senior = bool(any(k in role for k in _ici.SENIOR) or _c(_ici._RX_SENIOR_FIN, role))
    ecarte = next((k.strip() for k in _ici.NEG if k in role), "")
    # The language last: no title or bonus makes readable a
    # posting in a language the user does not speak.
    plafond_lg, motif_lg = plafond_langue(text or "")
    return Composantes(
        axes=sc,
        plafond=min(cap, plafond_lg),
        junior=junior,
        senior=senior,
        ecarte=ecarte,
        annees=experience_years(t, role),
        notes=tuple(notes),
        note_langue=f"annonce {motif_lg} : plafond {plafond_lg:g}" if motif_lg else "",
    )


def _departage(t: str, role: str, fit: float, entier: int, yrs: int) -> float:
    """0..1: rank of an offer among those with the same integer fit.

    The fit's axes cap at 1: at the top, all the rich offers came out equal. So we
    take signals that do not saturate (or only gently): what the TITLE says, the ESG
    density of the text, the number of ESG/finance skills cited, the position of the
    raw score within the level, and the required experience (less is better: the user
    is junior).
    """
    titre = 1.0 if _c(_ici._ESG_TITRE_FORT, role) else 0.6 if _c(_ici._ESG_TITLE_RX, role) else 0.0
    d = densite_esg(t)
    got = skills_in(t)
    # The two heaviest axes: the target and the base profession.
    lourds = sorted(_ici.AXES, key=lambda a: -_ici.POIDS.get(a, 0))[:2]
    n = sum(1 for axe in lourds for l in _ici.AXES[axe] if l in got)
    pos = max(0.0, min(1.0, fit - (entier - 0.5)))
    return (
        0.30 * titre
        + 0.20 * d / (d + 2.0)
        + 0.25 * n / (n + 8.0)
        + 0.15 * pos
        + 0.10 * (1.0 - min(yrs, 5) / 5.0)
    )


def score_offer(offer: dict[str, Any]) -> dict[str, Any]:
    """Coverage of the skills the posting asks for by the CV of its domain.

    Args:
        offer: the offer (role, missions, profil, domaine).

    Returns:
        {required, covered, missing, pct}; pct = None if the posting asks for no
        known skill.
    """
    texte = f"{offer['role']} {offer['missions']} {offer['profil']}"
    required = skills_in(texte)
    # Skills of the job that the CV may lack (profile key competences_ats, written by
    # first_launch): a profile built from the CV alone covered 100 % of every posting.
    t = texte.lower()
    autres = {
        lab: list(v.get("synonymes") or [])
        for lab, v in (_P.get("competences_ats", {}) or {}).items()
        if lab not in _ici.SKILL_LEX
    }
    required |= {lab for lab, ns in autres.items() if _lexique.contient(ns, t)}
    if not required:
        # nothing detected -> neutral
        return dict(required=set(), covered=set(), missing=set(), pct=None)
    cv = cv_text_cached(cv_variant_key(offer["domaine"]))
    covered = {  # same matcher (whole word)
        s
        for s in required
        if (_lexique.contient(autres[s], cv) if s in autres else has_skill(s, cv))
    }
    missing = required - covered
    pct = round(100 * len(covered) / len(required))
    return dict(required=required, covered=covered, missing=missing, pct=pct)


# Safeguard, at the END of the module: globals() must be complete to see everything.
# It was missing here, and it is precisely here that a pattern was corrupted —
# `_ESG_TITLE_RX` started with a backspace, so "an explicitly ESG title
# raises the cap to 10" NEVER applied. The core of the scoring
# ran with its main rule dead, without anything reporting it.
__import__("jobhunter.text", fromlist=["x"]).verifier_motifs(globals(), minimum=4)


def expliquer(
    text: str | None, title: str | None = "", poids: "_poids.Ponderation | None" = None
) -> list[str]:
    """Why the offer has this fit, step by step, in plain words.

    The skills found per axis, the vocabulary score, the cap and its reason, the
    title's bonuses and penalties, the language, the experience asked for, then the fit.
    """
    raisons: list[str] = []
    fit, _yrs, _fin = fit_detail(text, title, raisons, poids)
    raisons.append(f"fit {fit}")
    return raisons


if __name__ == "__main__":
    print("Module de scoring (score_offer/fit_score). CLI : rescore_ats.py")
