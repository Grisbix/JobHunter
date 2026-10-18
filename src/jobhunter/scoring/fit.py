"""jobhunter.scoring.fit (ancien Scripts/ats_match.py).

ats_match.py — Scoring ATS façon Resume-Matcher (léger, offline).

Pour chaque offre : extrait les compétences REQUISES (dans Missions + Profil requis),
regarde lesquelles sont COUVERTES par le CV variant choisi, calcule un match %
et liste les compétences MANQUANTES (gaps à ajouter au CV/lettre).

Réutilise le lexique multi-profil de tailor_application (SKILL_LEX).

Run:
    python ats_match.py --company Amundi
    python ats_match.py --all --min 0          # rapport complet -> ats_report.csv
    python ats_match.py --n 12
"""

import re
import sys
from typing import Any

from docx import Document

try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]  # console : TextIOWrapper
except Exception:
    pass

from jobhunter import profil as _P
from jobhunter import racine as _racine
from jobhunter.chemins import CV_MODELES as CV_ATS
from jobhunter.scoring.lexique import CV_VARIANT, SKILL_LEX, cv_variant_key, has_skill

ROOT = _racine.racine()
OUT_CSV = ROOT / "Scripts" / "ats_report.csv"


def cv_text(variant_key: str) -> str:
    """Texte concaténé du CV variant (lower)."""
    p = CV_ATS / CV_VARIANT[variant_key]
    if not p.exists():
        return ""
    try:
        d = Document(str(p))
        return " ".join(par.text for par in d.paragraphs).lower()
    except Exception:
        return ""


_cv_cache: dict[str, str] = {}


def cv_text_cached(k: str) -> str:
    if k not in _cv_cache:
        _cv_cache[k] = cv_text(k)
    return _cv_cache[k]


def skills_in(text: str | None) -> set[str]:
    """Set des libellés SKILL_LEX présents dans le texte.
    Matcher partagé avec tailor_application (has_skill) : sigles courts = mot
    ENTIER, expressions longues = sous-chaîne. Évite les faux positifs 'ges' dans
    « GEStion », 'gri' dans « aGRIcole », 'pai' dans « PAIement »."""
    t = (text or "").lower()
    return {label for label in SKILL_LEX if has_skill(label, t)}


# ── Détecteur d'expérience requise ──
_EXP_NUM = re.compile(r"(\d{1,2})\s*(?:\+|ans?|an\b|années?|years?|yrs?)\+?", re.I)
_EXP_CTX = re.compile(r"(exp[ée]rien|experien|ann[ée]es?\s+d|years?\s+of|d['e]\s*exp)", re.I)
# Niveau vise : profil.json, section « niveau ». Cherches dans l'INTITULE seul
# (voir fit_detail) ; « lead » n'y est pas en sous-chaine — il attrape « Lead
# Generation » — c'est `senior_en_fin` qui s'en charge, avec la negation qu'il faut.
JUNIOR = tuple(_P.get("niveau.mots_junior", []) or [])
SENIOR = tuple(_P.get("niveau.mots_senior", []) or [])
_RX_SENIOR_FIN = _P.motif(_P.get("niveau.senior_en_fin", []))
NEG = tuple(_P.get("niveau.mots_negatifs", []) or [])


def experience_years(text: str | None) -> int:
    """Années d'expérience EXIGÉES détectées (0 si aucune). Prend le max des nombres
    apparaissant près d'un mot 'expérience'. Ex '10 ans d'expérience' → 10.
    Plafond 15 (>15 = bruit : âge, ancienneté société…). Ignore si poste junior/alternance.

    Les blancs sont ÉCRASÉS avant la recherche. La fenêtre de contexte ne fait que
    28 caractères de part et d'autre du nombre, et les fiches structurées séparent
    l'étiquette de sa valeur par des rafales de retours chariot :

        Niveau d'expérience \r\n \r\n \r\n \r\n Plus de 10 ans

    Le mot « expérience » tombait alors hors fenêtre et l'exigence passait
    inaperçue. CNP « EXPERT INVESTISSEMENT RESPONSABLE » sortait ainsi à fit 10
    avec exp_requise = 0 alors que l'annonce demande plus de dix ans."""
    t = re.sub(r"\s+", " ", (text or "")).lower()
    if any(
        k in t
        for k in (
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
        )
    ):
        return 0  # offre junior : un '10 ans' isolé = bruit
    yrs = 0
    for m in _EXP_NUM.finditer(t):
        a, b = m.start(), m.end()
        # FENÊTRE À GAUCHE PLUS LARGE QU'À DROITE. L'exigence s'écrit presque
        # toujours « expérience … de N ans » : le mot déclencheur précède le
        # nombre, souvent de loin. « expérience professionnelle antérieure de
        # 3 à 5 ans » place « expérience » à 44 caractères de « 5 ans » — hors
        # d'une fenêtre de 28, et l'offre Crédit Mutuel AM (3 à 5 ans exigés)
        # ressortait à exp_requise = 0. À DROITE on reste serré : « 5 ans »
        # suivi trente caractères plus loin d'un « expérience » appartenant à
        # la phrase suivante ne dit rien de ce nombre-là.
        ctx = t[max(0, a - 70) : min(len(t), b + 28)]
        if _EXP_CTX.search(ctx):
            n = int(m.group(1))
            if 1 <= n <= 15:  # exp réaliste ; >15 = âge/ancienneté → ignoré
                yrs = max(yrs, n)
    return yrs


# ── Scoring VECTORIEL : axes ponderes, au lieu de « +1 par competence » ──
# L'ancien fit = 2 + len(skills_in) saturait : « Assistant administratif » matchait
# Excel + Anglais + Communication et sortait 10/10. Les competences GENERIQUES
# (bureautique, langues) ne sont dans AUCUN axe : elles ne font pas monter le score.
#
# Tout vient du profil (section « scoring ») :
#   axes            {nom: {poids, competences}} — l'axe COEUR est la cible
#                   premiere, l'axe COMPLEMENT une cible secondaire
#   cible_score     somme ponderee qui vaut fit = 10
#   saturation_axe  un axe sature a N libelles distincts (on ne divise pas par la
#                   taille de l'axe : un axe large serait mecaniquement desavantage)
_SC = _P.get("scoring", {}) or {}
AXES = {a: list(v.get("competences") or []) for a, v in (_SC.get("axes") or {}).items()}
POIDS = {a: float(v.get("poids", 1.0)) for a, v in (_SC.get("axes") or {}).items()}
COEUR = _SC.get("axe_coeur") or (next(iter(AXES)) if AXES else "")
COMPLEMENT = _SC.get("axe_complement") or ""
_CAP = int(_SC.get("saturation_axe", 3))
_TARGET = float(_SC.get("cible_score", 3.0))
_PLAFOND_SANS_COEUR = float(_SC.get("plafond_sans_coeur", 6.0))
_PLAFOND_COMPLEMENT = float(_SC.get("plafond_complement", 8.0))
_PLAFOND_SECOND = float(_SC.get("plafond_second", 8.0))
_PLAFOND_VETO = float(_SC.get("plafond_veto", 6.0))

# INTITULES. Le titre dit ce QU'EST le poste, la description ne fait que
# mentionner des sujets : c'est lui qui leve ou abaisse le plafond.
#   intitules_coeur        leve le plafond a 10, sauf metier hors cible
#   intitules_coeur_forts  leve le plafond a 10 dans tous les cas
#   intitules_second       metier vise en second : plafond 8 (+2 x axe coeur)
#   veto_sigles / veto_si + veto_et : metier voisin a ecarter (plafond 6)
#   intitules_techniques (sauf ..._sauf) et intitules_hors_metier : le
#     vocabulaire de la cible ne rapproche pas ces metiers du profil
# Les noms historiques (_ESG_TITLE_RX…) restent : les tests et la densite les lisent.
_ESG_TITLE_RX = _P.motif(_SC.get("intitules_coeur"))
_ESG_TITRE_FORT = _P.motif(_SC.get("intitules_coeur_forts"))
_TITRE_FINANCE = _P.motif(_SC.get("intitules_second"))
_RX_HSE_SIGLE = _P.motif(_SC.get("veto_sigles"))
_RX_SECURITE = _P.motif(_SC.get("veto_si"))
_RX_SANTE_ENV = _P.motif(_SC.get("veto_et"))
_RX_TECHNIQUE_TITRE = _P.motif(_SC.get("intitules_techniques"))
_RX_TITRE_FINANCE = _P.motif(_SC.get("intitules_techniques_sauf"))
_RX_HORS_METIER = _P.motif(_SC.get("intitules_hors_metier"))
_c = _P.cherche


def _titre_hse(role: str) -> bool:
    """Intitule d'un metier voisin a ecarter (exemple finance durable : HSE)."""
    return bool(_c(_RX_HSE_SIGLE, role) or (_c(_RX_SECURITE, role) and _c(_RX_SANTE_ENV, role)))


def _titre_hors_cible(role: str) -> bool:
    """Metier technique ou hors metier : le vocabulaire de la cible ne le rapproche pas du profil."""
    tech = _c(_RX_TECHNIQUE_TITRE, role) and not _c(_RX_TITRE_FINANCE, role)
    return bool(tech or _c(_RX_HORS_METIER, role))


# ── Anti-boilerplate ─────────────────────────────────────────────────────────
# Une description d'entreprise de 8000 caracteres qui dit UNE fois chacun de
# trois mots de la cible sature l'axe : c'est du discours d'employeur, pas le
# poste. La DENSITE (marqueurs de l'intitule coeur pour 1000 caracteres) separe
# les deux ; en dessous du seuil, l'axe coeur est attenue au prorata.
_ESG_DENSITE_MIN = float(_SC.get("densite_coeur_min", 1.0))  # marqueurs pour 1000 caracteres
_ESG_DENSITE_LONG = int(
    _SC.get("densite_coeur_longueur", 800)
)  # en deca, le texte est trop court pour qu'une densite veuille dire quelque chose


def densite_esg(text: str | None) -> float:
    """Marqueurs ESG pour 1000 caractères. 0.0 sur un texte vide."""
    t = text or ""
    if not t or _ESG_TITLE_RX is None:
        return 0.0
    return 1000.0 * sum(1 for _ in _ESG_TITLE_RX.finditer(t)) / len(t)


def axis_scores(text: str | None) -> dict[str, float]:
    """Densité 0.0-1.0 par axe. Utile pour comprendre POURQUOI une offre score."""
    got = skills_in(text)
    out: dict[str, float] = {}
    for axe, labels in AXES.items():
        cap = min(_CAP, len(labels)) or 1
        out[axe] = min(sum(1 for l in labels if l in got), cap) / cap
    # L'axe ESG, et lui seul, est attenue quand ses marqueurs sont noyes : c'est
    # le seul qui leve le plafond de fit, donc le seul ou une mention de passage
    # coute cher. Un texte court echappe au controle — « Analyste ESG » seul
    # fait 12 caracteres pour un marqueur, sa densite n'a pas de sens.
    if out.get(COEUR, 0) > 0 and _ESG_TITLE_RX is not None and len(text or "") >= _ESG_DENSITE_LONG:
        d = densite_esg(text)
        if d < _ESG_DENSITE_MIN:
            out[COEUR] *= d / _ESG_DENSITE_MIN
    return out


_NIV = _P.get("niveau", {}) or {}
_BONUS_JUNIOR = float(_NIV.get("bonus_junior", 1.0))
_MALUS_SENIOR = float(_NIV.get("malus_senior", 2.0))
_MALUS_EXP = sorted(
    ((int(k), float(v)) for k, v in (_NIV.get("malus_experience") or {}).items()), reverse=True
)


def _malus_experience(yrs: int) -> float:
    """Malus pour `yrs` annees exigees : le palier le plus haut atteint."""
    return next((m for seuil, m in _MALUS_EXP if yrs >= seuil), 0.0)


def fit_score(text: str | None, title: str | None = "") -> tuple[int, int]:
    """(fit entier 1-10, annees d'experience exigees). Voir fit_detail."""
    fit, yrs, _fin = fit_detail(text, title)
    return fit, yrs


# ── LANGUE : une offre dans une langue que l'utilisateur ne parle pas ───────
# Le vocabulaire metier (ESG, reporting, analyst) est le meme dans toutes les
# langues : sans cette regle, une annonce en neerlandais sortait a 10 pour qui
# ne lit pas le neerlandais. Deux cas, deux plafonds :
#   - annonce REDIGEE dans une langue non parlee -> 2 (illisible)
#   - annonce qui EXIGE une langue non parlee (« fluent Dutch », « Nederlands
#     vereist ») -> 4. « Dutch is a plus » n'exige rien : ignore.
# Langues parlees : profil « langues_parlees » (codes fr, en, de, es, it, nl, pt...).
LANGUES_PARLEES = set(_P.get("langues_parlees", ["fr", "en"]) or ["fr", "en"])

# Mots-outils propres a chaque langue (articles, pronoms, prepositions) et
# quelques mots d'annonce sans equivalent ailleurs. Les mots communs a deux
# langues (« de », « en », « die ») sont evites.
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

# Noms de chaque langue, tels qu'une annonce les ecrit (anglais, francais,
# langue elle-meme, neerlandais). Les langues parlees sortent de la liste des
# langues « etrangeres » et servent a reconnaitre une alternative.
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


def _compte_langues(mots: list[str]) -> dict[str, int]:
    return {k: sum(1 for m in mots if m in v) for k, v in _MOTS_OUTILS.items()}


def langue_redaction(t: str | None) -> str:
    """Code de la langue dominante du texte ('' si texte trop court ou indecis).

    L'EN-TETE compte a part : EURES traduit automatiquement en anglais des
    annonces neerlandaises ; le corps anglais l'emportait (26 mots-outils contre
    4). Les premieres lignes sont celles de l'employeur : si elles sont
    nettement dans une langue non parlee, l'annonce l'est."""
    tete = _compte_langues(_RX_MOT.findall((t or "")[:600].lower()))
    lg = max(tete, key=tete.__getitem__)
    parlees = [tete[k] for k in LANGUES_PARLEES if k in tete] or [0]
    if lg not in LANGUES_PARLEES and tete[lg] >= 4 and tete[lg] >= 2 * max(parlees):
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


_LANGUES_ETRANGERES = (
    "(?:" + "|".join(v for k, v in _NOMS_LANGUES.items() if k not in LANGUES_PARLEES) + ")"
)
_PARLEES = "(?:" + "|".join(v for k, v in _NOMS_LANGUES.items() if k in LANGUES_PARLEES) + ")"
# Le nom de langue designe un marche ou une entite, pas une competence :
# « strong presence in Chinese markets », « Dutch GAAP », « Italian clients ».
_PAS_UNE_LANGUE = (
    r"(?![\s-]+(?:markets?|clients?|customers?|compan\w*|business\w*|teams?"
    r"|entit\w*|subsidiar\w*|operations?|government|law|gaap|regulat\w*"
    r"|portfolio|assets?|real\s+estate|banks?|offices?|sites?)\b)"
)
# « Fluent in English and Dutch », « maitrise du neerlandais ». Seuls des mots
# qui parlent de LANGUE introduisent : « strong », « excellent » precedaient
# aussi bien un marche.
_RX_LANGUE_AVANT = re.compile(
    r"\b(?:fluen(?:t|cy)|native|mother\s+tongue|proficien\w*|business[- ]level"
    r"|courant|ma[iî]trise|bilingue?|bilingual|vloeiend)\W+(?:\w+\W+){0,4}?"
    + _LANGUES_ETRANGERES
    + r"\b"
    + _PAS_UNE_LANGUE,
    re.I,
)
# « Dutch is required », « Dutch speaking », « Nederlands vereist », « neerlandais exige »
_RX_LANGUE_APRES = re.compile(
    r"\b"
    + _LANGUES_ETRANGERES
    + _PAS_UNE_LANGUE
    + r"\W+(?:\w+\W+){0,3}?(?:required|mandatory|essential|must|speak(?:ing|er)s?|native"
    r"|fluent|fluency|language|skills|proficiency|vereist|noodzakelijk|verplicht"
    r"|exig[ée]e?|obligatoire|indispensable|requis[e]?|courant)\b",
    re.I,
)
# Une annonce « neerlandophone » exige le neerlandais.
_RX_NEERLANDOPHONE = re.compile(r"\bnederlandstalig\w*|\bnederlandse\s+taal\b", re.I)
# Ce qui suit la langue et la rend facultative.
_RX_FACULTATIF = re.compile(
    r"^\W*(?:\w+\W+){0,4}?(?:a\s+|an\s+)?(?:plus|asset|advantage|bonus|nice[- ]to[- ]have"
    r"|prefer\w*|desirable|beneficial|atout|souhait\w*|appr[ée]ci\w*|pluspunt|voordeel)\b",
    re.I,
)
# Ce qui PRECEDE la langue et la rend facultative : « preferable in Dutch too ».
_RX_FACULTATIF_AVANT = re.compile(
    r"\b(?:prefer\w*|ideally|id[ée]alement|optional\w*|souhait\w*|bonus|plus)\W+(?:\w+\W+){0,2}$",
    re.I,
)
# Une alternative avec une langue parlee n'exige rien : « Dutch and/or French ».
_RX_ALTERNATIVE = re.compile(
    r"(?:"
    + _PARLEES
    + r"\s*(?:and\s*/\s*or|et\s*/\s*ou|or|ou|of)\s+"
    + _LANGUES_ETRANGERES
    + r"|"
    + _LANGUES_ETRANGERES
    + r"\s*(?:and\s*/\s*or|et\s*/\s*ou|or|ou|of)\s+"
    + _PARLEES
    + r")\b",
    re.I,
)
_RX_NOM_LANGUE = re.compile(r"\b" + _LANGUES_ETRANGERES + r"\b", re.I)


def langue_exigee(t: str | None) -> str:
    """Nom d'une langue non parlee que l'annonce EXIGE, sinon ''."""
    t = t or ""
    if "nl" not in LANGUES_PARLEES and _RX_NEERLANDOPHONE.search(t):
        return "nederlands"
    for rx in (_RX_LANGUE_AVANT, _RX_LANGUE_APRES):
        for m in rx.finditer(t):
            nom = _RX_NOM_LANGUE.search(m.group(0))
            debut = nom.start() + m.start() if nom else m.start()
            fin = nom.end() + m.start() if nom else m.end()
            if _RX_FACULTATIF.search(t[fin : fin + 60]):
                continue
            if _RX_FACULTATIF_AVANT.search(t[max(0, debut - 40) : debut]):
                continue
            if _RX_ALTERNATIVE.search(t[max(0, debut - 30) : fin + 30]):
                continue
            return (nom.group(0) if nom else m.group(0)).lower()
    return ""


def plafond_langue(t: str | None) -> tuple[float, str]:
    """(plafond, motif) : 2 si redigee dans une langue non parlee, 4 si elle en
    exige une, (10, '') sinon."""
    lg = langue_redaction(t)
    if lg and lg not in LANGUES_PARLEES:
        return 2.0, f"redigee en {lg}"
    exige = langue_exigee(t)
    if exige:
        return 4.0, f"exige {exige}"
    return 10.0, ""


def fit_detail(text: str | None, title: str | None = "") -> tuple[int, int, float]:
    """(fit, yrs, fit_fin). `fit_fin` departage les ex aequo d'un meme fit.

    l'utilisateur, 2026-10-09 : 546 offres a 10, 1203 a 8, 3321 a 6 — dans un niveau,
    l'ordre ne voulait rien dire. fit_fin = fit +/- 0,45 : son arrondi rend
    TOUJOURS `fit`, aucun seuil (>= 8...) ne bouge. Dans le niveau, il suit
    _departage : intitule ESG, densite ESG, competences citees, experience.

    Fit 1-10 vectoriel : 6 axes pondérés (ESG ×3, finance ×2, IA ×1.5, reste ×1),
    puis malus junior/senior/sales et MALUS EXPÉRIENCE (l'utilisateur est junior).

    `title` : les malus séniorité/rôle s'appliquent au SEUL intitulé quand il est
    fourni. Cherchés dans la description entière, ils produisent des faux positifs
    — « Lead Generation » déclenchait le malus SENIOR et « présence commerciale »
    le malus NEG, soit −4 sur une offre qui n'est ni senior ni commerciale.
    Le niveau et le type de poste se lisent dans l'intitulé, pas dans la
    présentation de l'entreprise."""
    t = (text or "").lower()
    role = (title or text or "").lower()
    sc = axis_scores(t)
    raw = sum(sc[a] * POIDS[a] for a in AXES)
    fit = 1 + 9 * min(1.0, raw / _TARGET)  # 1..10, pas de magic number empilé
    # PLAFOND PAR PRIORITE DE PROFIL. Sans lui, finance + risk + conseil suffisent
    # a atteindre _TARGET sans le moindre signal ESG : 251 offres sortaient a
    # fit >= 8 avec l'axe ESG a ZERO, et le TOP 25 ne contenait plus que 3
    # intitules ESG. Le score mesurait la richesse du vocabulaire, pas l'adequation.
    #   ESG present            -> jusqu'a 10 (coeur de cible)
    #   pas d'ESG mais IA      -> 8 max (marche vise en complement)
    #   ni ESG ni IA           -> 6 max (repli finance, jamais devant une offre ESG)
    # Le plafond suit la DENSITE ESG, pas sa simple presence : un seul libelle
    # capte au detour d'une longue description (esg=0.33) suffisait a contourner
    # un plafond binaire, et « ANALYSTE M&A » restait a 10.
    #   esg 0.00 -> 6   esg 0.33 -> 7.3   esg 0.67 -> 8.7   esg 1.00 -> 10
    coeur = sc.get(COEUR, 0.0) if COEUR else 1.0  # sans axe coeur : pas de plafond
    compl = sc.get(COMPLEMENT, 0.0) if COMPLEMENT else 0.0
    cap = _PLAFOND_SANS_COEUR + (10.0 - _PLAFOND_SANS_COEUR) * coeur
    if coeur == 0 and compl >= 0.5:
        cap = _PLAFOND_COMPLEMENT  # cible secondaire
    if _c(_TITRE_FINANCE, role):
        cap = max(cap, _PLAFOND_SECOND + (10.0 - _PLAFOND_SECOND) * coeur)  # metier vise en second
    # Un intitule explicitement ESG leve le plafond : le titre dit ce QU'EST le
    # poste, la description ne fait que mentionner des sujets.
    fort = _c(_ESG_TITRE_FORT, role)
    hors = _titre_hors_cible(role)
    if fort or (_c(_ESG_TITLE_RX, role) and not hors):
        cap = 10.0
    # Vetos en dernier : HSE, metier technique ou hors finance l'emportent sur
    # le vocabulaire environnemental de l'intitule ET de la description, jamais
    # sur un marqueur ESG-finance. Le metier technique ne faisait que perdre la
    # levee par l'intitule : une description dense en carbone rendait quand
    # meme 10 a « Engineer Sustainability & Product Compliance ».
    # Le plafond du veto metier suit la regle generale : 8 si le poste parle
    # d'IA (cible secondaire), 6 sinon. Un plafond fixe a 6 faisait perdre deux
    # points a 137 postes « AI Engineer » que personne ne jugeait trop hauts.
    if not fort and _titre_hse(role):
        cap = min(cap, _PLAFOND_VETO)
    elif not fort and hors:
        cap = min(cap, _PLAFOND_COMPLEMENT if compl >= 0.5 else _PLAFOND_VETO)
    # LES BONUS D'ABORD, LE PLAFOND ENSUITE. Le plafond etait applique avant, et
    # le bonus junior le franchissait : « Auditeur junior analyste » sortait a
    # 10 avec un plafond calcule a 8.7. Un plafond qu'un bonus peut depasser ne
    # plafonne rien — et la regle « ni ESG ni IA -> 6 max » ne tenait plus.
    #
    # JUNIOR SUR L'INTITULE SEUL, comme SENIOR et NEG. Il etait aussi cherche
    # dans toute la description : un « ... ouvert aux alternants » en pied
    # d'annonce donnait +1 a un poste qui n'a rien de junior. C'est exactement
    # le faux positif deja corrige pour les deux autres listes, laisse ici.
    if any(k in role for k in JUNIOR):
        fit += _BONUS_JUNIOR
    if any(k in role for k in SENIOR) or _c(_RX_SENIOR_FIN, role):
        fit -= _MALUS_SENIOR
    if any(k in role for k in NEG):
        fit -= 2
    # La langue en dernier : aucun intitule ni bonus ne rend lisible une
    # annonce dans une langue que l'utilisateur ne parle pas.
    cap = min(cap, plafond_langue(text or "")[0])
    fit = min(fit, cap)
    yrs = experience_years(t)
    fit -= _malus_experience(yrs)
    entier = max(1, min(10, round(fit)))
    return entier, yrs, round(entier - 0.45 + 0.9 * _departage(t, role, fit, entier, yrs), 3)


def _departage(t: str, role: str, fit: float, entier: int, yrs: int) -> float:
    """0..1 : rang d'une offre parmi celles de meme fit entier.

    Les axes du fit plafonnent a 1 : au sommet, toutes les offres riches
    sortaient egales. On prend donc des signaux qui ne saturent pas (ou
    doucement) : ce que dit l'INTITULE, la densite ESG du texte, le nombre de
    competences ESG/finance citees, la place du score brut dans le niveau, et
    l'experience exigee (moins vaut mieux : l'utilisateur est junior)."""
    titre = 1.0 if _c(_ESG_TITRE_FORT, role) else 0.6 if _c(_ESG_TITLE_RX, role) else 0.0
    d = densite_esg(t)
    got = skills_in(t)
    # Les deux axes les plus lourds : la cible et le metier de base.
    lourds = sorted(AXES, key=lambda a: -POIDS.get(a, 0))[:2]
    n = sum(1 for axe in lourds for l in AXES[axe] if l in got)
    pos = max(0.0, min(1.0, fit - (entier - 0.5)))
    return (
        0.30 * titre
        + 0.20 * d / (d + 2.0)
        + 0.25 * n / (n + 8.0)
        + 0.15 * pos
        + 0.10 * (1.0 - min(yrs, 5) / 5.0)
    )


def score_offer(offer: dict[str, Any]) -> dict[str, Any]:
    required = skills_in(f"{offer['role']} {offer['missions']} {offer['profil']}")
    if not required:
        # rien de détecté -> neutre
        return dict(required=set(), covered=set(), missing=set(), pct=None)
    cv = cv_text_cached(cv_variant_key(offer["domaine"]))
    covered = {s for s in required if has_skill(s, cv)}  # même matcher (mot entier)
    missing = required - covered
    pct = round(100 * len(covered) / len(required))
    return dict(required=required, covered=covered, missing=missing, pct=pct)


# Garde-fou, en FIN de module : globals() doit etre complet pour tout voir.
# Il manquait ici, et c'est precisement ici qu'un motif etait corrompu —
# `_ESG_TITLE_RX` commencait par un backspace, donc « un intitule explicitement
# ESG leve le plafond a 10 » ne s'appliquait JAMAIS. Le coeur du scoring
# tournait avec sa regle principale morte, sans que rien ne le signale.
__import__("jobhunter.texte", fromlist=["x"]).verifier_motifs(globals(), minimum=4)

if __name__ == "__main__":
    print("Module de scoring (score_offer/fit_score). CLI : rescore_ats.py")
