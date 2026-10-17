#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""job_sources.py — SCAN d'offres élargi + MERGE direct dans apply_queue.json.

Sources (toutes gratuites, sans clé) :
  1. ATS à API JSON publique : Greenhouse, Lever, Ashby, Recruitee, SmartRecruiters
     (liste de slugs finance/ESG/climate — tolère les 404, facile à étendre)
  2. LinkedIn recherche PUBLIQUE (guest API HTML, httpx, pas de login, pagination)
  3. Welcome to the Jungle recherche par mots-clés (navigateur headless + TURBO, pagination)

Chaque offre est filtrée (matches_esg_finance sur le titre), classée (classify_domaine),
scorée (fit_score avec malus expérience + ats), dédupliquée (entreprise|poste + URL)
puis MERGÉE dans apply_queue.json. Les descriptions arrivent ensuite via l'auto-enrich.

Usage :
  python job_sources.py --all            # tout : ATS + LinkedIn + WTJ → merge queue
  python job_sources.py --ats            # seulement les APIs ATS
  python job_sources.py --linkedin       # seulement recherche LinkedIn guest
  python job_sources.py --wtj            # seulement WTJ (navigateur)
  python job_sources.py --all --dry      # collecte + montre, ne merge pas
"""

import sys, json, re, time, argparse, html, datetime
from pathlib import Path
from urllib.parse import quote, unquote, urlparse

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
QUEUE = HERE / "apply_queue.json"
# Fichier PROPRE a ce programme. Il portait le meme nom que la sortie de
# scrape_jobs.py : le scan ecrasait la recolte des sites carriere, y
# compris quand il ne ramenait rien (WTJ bride -> 0 offre -> fichier vide).
FRESH = HERE / "offres_scan.json"
REJETS_TRI = HERE / "_rejets_tri.json"  # les tests le remplacent

from scrape_jobs import matches_esg_finance, classify_domaine  # filtre + classif partagés

# ── Mots-clés de recherche (LinkedIn, WTJ…) : profil.json, collecte.mots_cles ──
# sources_config.json (mots-cles edites depuis l'app) les remplace s'il en a.
import profil as _P

KEYWORDS = list(_P.get("collecte.mots_cles", []) or [])

# ── Slugs ATS publics (fintech/climate/finance FR-EU). 404 = ignoré silencieusement. ──
# Vérifiés avec probe_ats.py (les slugs qui ne répondent pas sont ignorés en 404).
# ⚠ Ne PAS ajouter "metron" en greenhouse : homonyme = société de défense US
# (Reston VA, systèmes autonomes), rien à voir avec l'efficacité énergétique FR.
ATS_SLUGS = {
    "greenhouse": [
        "sweep",
        "watershed",
        "vestiairecollective",
        "backmarket",
        "ecovadis",
        "mirakl",
        "payfit",
        "spendesk",
        "swile",
        "pigment",
        "clarityai",
        # Sonde des cabinets du 2026-10-08 : Forvis Mazars Allemagne
        # (160 offres), AlixPartners dont Paris (114).
        "forvismazars",
        "alixpartners",
    ],
    # theodo : retrouve en sondant les societes dont la page carriere renvoie 404.
    # 141 offres, dont des postes IA — l'axe vibe-coding. Le 404 de la vitrine ne
    # disait rien du flux, qui lui repond.
    "lever": [
        "greenly",
        "carbometrix",
        "sami",
        "plana",
        "descartesunderwriting",
        "shine",
        "agicap",
        "pennylane",
        "qonto",
        "theodo",
    ],
    "ashby": ["pigment", "alan", "swan", "defacto", "hero", "altruistiq", "climatiq"],
    # grantthornton = Grant Thornton France (Neuilly, 60 offres) ; meridiam =
    # leur vrai site carriere ; forvismazars = Irlande ; bakertilly = Pays-Bas.
    "recruitee": [
        "carbo",
        "vertuoza",
        "greenscope",
        "sweep",
        "tikehaucapital",
        "grantthornton",
        "meridiam",
        "forvismazars",
        "bakertilly",
    ],
    "smartrecruiters": [
        "SycomoreAssetManagement",
        "BNPParibas",
        "AXA",
        "SocieteGenerale",
        "Natixis",
        "Amundi",
        "rolandberger",
    ],
}

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# ── Registre des refus ───────────────────────────────────────────────────────
# UNE COLLECTE VIDE A DEUX CAUSES OPPOSEES : il n'y avait rien a prendre, ou on
# nous a refuse l'entree. Les deux rendaient `[]` sans un mot. Le scan pouvait
# donc etre bride de bout en bout et afficher « 0 offres » comme un jour calme —
# sur LinkedIn, qui fournit les deux tiers de la file, et sur les APIs ATS, ou
# un 404 (slug mort, normal) etait traite comme un 429 (quota, anormal).
# Indeed et Glassdoor comptaient deja leurs refus ; ces deux sources-la, non.
import collections as _collections

INCIDENTS = _collections.defaultdict(_collections.Counter)


def incidents_resume():
    """Les refus du run, en une ligne par source. Vide si tout s'est bien passe."""
    lignes = []
    for source, par_cause in sorted(INCIDENTS.items()):
        detail = ", ".join(
            f"{cause}×{n}" for cause, n in sorted(par_cause.items(), key=lambda kv: -kv[1])
        )
        lignes.append(f"  ⚠ {source} : {detail}")
    return lignes


# ── sources éditables depuis l'app (panneau 🌍 Sites d'offres) ──
SOURCES_CFG = HERE / "sources_config.json"


def _load_cfg():
    """sources_config.json — écrase les défauts :
        keywords      [mots-clés]
        ats_slugs     {ats: [slugs]}
        workday_flux  [[tenant, hote, site, nom], ...]   [] = aucun flux Workday
        autres_flux   [[type, cle, nom], ...]            [] = aucun autre ATS
    Les listes d'entreprises livrees visent la finance et l'ESG : un profil
    d'un autre metier les vide (premier_lancement.py) et ajoute les siennes."""
    global KEYWORDS, ATS_SLUGS, WORKDAY_FLUX, AUTRES_FLUX
    try:
        cfg = json.loads(SOURCES_CFG.read_text(encoding="utf-8"))
        if cfg.get("keywords"):
            KEYWORDS = cfg["keywords"]
        if "ats_slugs" in cfg:
            ATS_SLUGS = cfg["ats_slugs"] or {}
        if "workday_flux" in cfg:
            WORKDAY_FLUX = [tuple(x) for x in cfg["workday_flux"] or []]
        if "autres_flux" in cfg:
            AUTRES_FLUX = [tuple(x) for x in cfg["autres_flux"] or []]
    except Exception:
        pass


def _mk(titre, url, entreprise, location="", date="", source="", description=""):
    return {
        "titre": titre.strip(),
        "url": url,
        "entreprise": entreprise.strip(),
        "domaine": classify_domaine(titre),
        "location": location,
        "date": date,
        "source": source,
        "description": description[:30000],
        "scraped_at": time.strftime("%Y-%m-%d"),
    }


def _strip_html(h):
    """HTML → texte propre (descriptions APIs ATS)."""
    import html as _html

    t = _html.unescape(h or "")
    t = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", t, flags=re.S | re.I)
    t = re.sub(r"<br\s*/?>|</p>|</li>|</div>", "\n", t, flags=re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\n{3,}", "\n\n", re.sub(r"[ \t]+", " ", t)).strip()


# ── Anti-bruit : le titre doit contenir un mot-clé MÉTIER (pas juste 'intern'/'h/f'),
#    et ne pas être un rôle hors-cible (design, sales, marketing, RH…). ──
# NB : sans csr|transition|environnement|hse, de vrais postes ESG étaient jetés —
# « VIE Transition Énergétique Corporate » (Crédit Agricole) et « CSR & HR Officer »
# (ODDO BHF) passaient matches_esg_finance mais échouaient ici, faute de mot métier.
_FT = _P.get("filtre_titre", {}) or {}
# Mot METIER requis dans l'intitule (vide = pas d'exigence).
_DOMAIN_RX = _P.motif(_FT.get("metier"))
# Roles jamais voulus, quel que soit le domaine.
_HARD_NEG_RX = _P.motif(_FT.get("exclus"))
# Roles ecartes SAUF s'ils portent un marqueur de la cible secondaire
# (exemple finance durable : « Developer » non, « AI Engineer » oui).
_DEV_NEG_RX = _P.motif(_FT.get("exclus_sauf_complement"))
_NEG_TITLE_RX = _P.motif((_FT.get("exclus") or []) + (_FT.get("exclus_sauf_complement") or []))
# Marqueurs de la cible secondaire : passent meme avec un mot de _DEV_NEG_RX.
_AI_RX = _P.motif(_FT.get("complement"))


# LinkedIn etiquette « CDI » les offres d'alternance et de stage : sa metadonnee
# est fausse. L'intitule, lui, ne ment pas — « Alternance - Data Analyst » EST
# une alternance. Le titre fait donc foi quand il est explicite.
_RX_ALT = re.compile(r"\b(alternan[ct]|apprenti|apprentissage|contrat\s+pro)", re.I)
_RX_STAGE = re.compile(
    r"\b(stage|stagiaire|internship|intern|working\s+student)\b"
    r"|\bwerkstudent",
    re.I,
)
_RX_VIE_POINTE = re.compile(r"\bv\.i\.[ea]\b", re.I)
_RX_VIE_MAJ = re.compile(r"\bVIE\b(?=\s*[-–—/:|,(])")  # sans re.I : « vie » est un mot

# Garde-fou. Une frontiere de mot s'ecrit \b et se corrompt de deux facons, toutes
# deux SILENCIEUSES — le motif compile, ne leve rien, et ne matche plus jamais :
#   \x08          : un \b passe dans un heredoc shell devient un backspace
#   \\b (litteral): une "correction" du cas precedent qui echappe l'antislash
# Les deux se sont produits ici. On refuse de demarrer plutot que de laisser
# passer des offres qui auraient du etre exclues.
# (le controle lui-meme est en FIN de module : voir _verifier_motifs)


def contrats_exclus():
    """Types de contrat que l'utilisateur ne veut pas voir. Regle dans
    sources_config.json, pas en dur : il n'est pas etudiant aujourd'hui, il
    pourrait vouloir les revoir un jour. Liste vide = tout est affiche."""
    try:
        import json as _j

        return set(_j.loads(SOURCES_CFG.read_text(encoding="utf-8")).get("contrats_exclus") or [])
    except Exception:
        return set()


def pays_exclus():
    """Pays dont on ne veut plus aucune offre, par MOTIF applique au lieu.

    POURQUOI UN FILTRE ET PAS UNE PURGE. Supprimer 937 offres britanniques et
    belges de la file ne les tue pas : le scan les retrouve a la source et les
    reajoute le lendemain. C'est la meme lecon que `exclusions.py`, qui existe
    pour les refus a l'unite — ici le refus porte sur une geographie entiere.

    Regle dans sources_config.json. Liste vide = aucun pays ecarte, ce qui est
    le comportement historique.
    """
    try:
        import json as _j

        return list(_j.loads(SOURCES_CFG.read_text(encoding="utf-8")).get("pays_exclus") or [])
    except Exception:
        return []


def _est_vie(o):
    """L'offre vient-elle de Business France ?

    On regarde la SOURCE et l'URL, pas le nom de l'employeur : « ARCELORMITTAL
    FRANCE » a Bruxelles est un V.I.E, « Mirova » a Paris n'en est pas un.
    """
    return "businessfrance" in str(o.get("url") or "").lower() or str(
        o.get("source") or ""
    ).lower().startswith("vie")


def _rx_pays_exclus():
    """Le motif compile, ou None si rien n'est exclu.

    Les motifs viennent du reglage et sont assembles tels quels : c'est la
    configuration qui decide, pas le code.

    PAS DE re.I GLOBAL. Il rendrait `\\bUK\\b` insensible a la casse, et « uk »
    apparait dans des mots ordinaires. Chaque motif porte donc son propre
    `(?i:...)` quand la casse lui est indifferente : les noms de pays en sont
    pourvus, le sigle non. C'est la famille de bugs de sous-chaine deja payee
    sur sinGAPore, diveRSE et CLIMATisation, deplacee d'un cran.
    """
    motifs = pays_exclus()
    if not motifs:
        return None
    return re.compile("|".join(motifs))


# Lire le contrat dans une description demande de la PRUDENCE : le mot seul se
# trompe souvent. Mesure sur la file : « 6 mois minimum, en alternance ou en
# poste » decrit une EXPERIENCE ; « early stage a PME mature » est de l'anglais ;
# « chez un prestataire de service » decrit les CLIENTS ; « recrutement en CDI,
# en interim » enumere les services d'une agence. D'ou deux passes.
#
# PASSE 1 — le libelle structure, presque toujours juste :
#   « Type de contrat : CDI », « Contrat : Alternance », « Poste en CDI »
# Sur une fiche en TABLEAU le libelle n'a pas de deux-points :
# eFinancialCareers ecrit « Type de contrat <blancs> Stage ». La passe 1 ne
# matchait donc rien, et la passe 2 ramassait le « CDD » d'une phrase de
# boilerplate — quatre STAGES du Credit Agricole se retrouvaient etiquetes
# CDD, en tete du classement. On accepte desormais un simple blanc apres la
# forme longue « type de … » ; la forme nue « contrat » garde son
# deux-points, sinon n'importe quelle phrase contenant le mot ferait libelle.
_RX_LABEL = re.compile(
    r"type\s+de\s+(?:contrat|recrutement)s?\s*(?:de\s+travail)?\s*(?:[:\-–]|\s)\s*"
    r"|(?:contrat|recrutement)s?\s*(?:de\s+travail)?\s*[:\-–]\s*"
    r"|poste\s+(?:propos[\u00e9]\s+)?en\s+",
    re.I,
)
# valeurs acceptees juste apres ce libelle
_RX_VALEUR = re.compile(
    r"^\W{0,3}(CDI|CDD|alternance|apprentissage|stage|int[e\u00e9]rim|freelance|V\.?I\.?E|contrat \u00e0 dur\u00e9e (?:in)?d\u00e9termin\u00e9e)",
    re.I,
)

# Tous les types de contrat, pour reperer les ENUMERATIONS (voir passe 2).
_RX_TOUS_CONTRATS = re.compile(
    r"\bCDI\b|\bCDD\b|\balternance\b|\bapprentissage\b|\bstages?\b"
    r"|\bV\.?I\.?E\b|\bint[eé]rim\b|\bfreelance\b",
    re.I,
)

# PASSE 2 — mots NON AMBIGUS seulement. « stage », « alternance », « interim »,
# « prestataire » et « freelance » nus sont ecartes : ils designent aussi bien
# une phase, une experience passee ou l'activite de l'employeur.
_DESC_CONTRAT = [
    (
        "Alternance",
        re.compile(
            r"contrat d[\u2019']apprentissage|contrat de professionnalisation|\ben alternance\s+(?:de|pour|d[\u2019']une dur)",
            re.I,
        ),
    ),
    (
        "Stage",
        re.compile(
            r"convention de stage|\bstage conventionn|stage de fin d[\u2019']\u00e9tudes|\bstagiaire\b",
            re.I,
        ),
    ),
    ("V.I.E", re.compile(r"\bV\.I\.[EA]\b|volontariat international en entreprise", re.I)),
    ("CDD", re.compile(r"\bCDD\b|contrat \u00e0 dur\u00e9e d\u00e9termin\u00e9e", re.I)),
    (
        "CDI",
        re.compile(
            r"\bCDI\b|contrat \u00e0 dur\u00e9e ind\u00e9termin\u00e9e|permanent (?:contract|position)",
            re.I,
        ),
    ),
]


# UN POSTE QUI DEMANDE UN ETUDIANT EST UN STAGE (l'utilisateur, 2026-10-04). Beaucoup
# d'annonces ne disent jamais « stage » dans leur titre ni leur libelle : la
# Societe Generale ecrit « Charge de mission ESG » puis « Vous etes etudiant en
# Bac +4/5 », et l'offre sortait notee 10. Mesure sur la file : 121 descriptions.
#
# Trois familles de faux positifs, toutes rencontrees dans ces 121 :
#   - l'ALTERNATIVE : « currently pursuing (or already holding) a master's »,
#     « final-year students or recent graduates » — un diplome est accepte,
#     ce n'est pas un stage. Voir _RX_OU_DIPLOME, cherche dans la phrase.
#   - l'EXPERIENCE : « Praktika oder Werkstudententatigkeiten », « internships,
#     working student roles » — un passe demande, pas un statut. D'ou « working
#     student » / « Werkstudent » reconnus dans le TITRE seulement (_RX_STAGE).
#   - le hors-sujet : « currently pursuing certification », « for each degree
#     received or currently enrolled in » (consigne de CV d'un doctorat).
_A = "[’']"
_RX_ETUDIANT = re.compile(
    r"vous\s+[êe]tes\s+(?:actuellement\s+|aujourd" + _A + r"hui\s+)?[ée]tudiant"
    r"|[ée]tudiant(?:e|\(e\)|\.e|·e)?\s+(?:de\s+niveau\s+|en\s+)"
    r"(?:derni[èe]re\s+ann[ée]e|master|M1|M2|bac\s*\+|[ée]cole|cursus|licence|L3"
    r"|fin\s+d" + _A + r"[ée]tudes|ann[ée]e\s+de\s+c[ée]sure)"
    r"|\bann[ée]e\s+de\s+c[ée]sure|\bstage\s+de\s+c[ée]sure"
    r"|\bcurrently\s+(?:enrolled|studying|pursuing\s+(?:an?\s+|your\s+)?"
    r"(?:degree|bachelor|master|undergraduate|graduate|studies|MBA|BSc|MSc))"
    r"|\bcurrent(?:ly)?\s+(?:a\s+)?(?:university\s+)?student\b"
    r"|\b(?:penultimate|final)[- ]year\s+(?:university\s+|undergraduate\s+|master"
    + _A
    + r"?s?\s+)?(?:student|undergraduate)"
    r"|\bmust\s+be\s+(?:a\s+)?(?:current\s+)?(?:student|enrolled)"
    r"|\benrolled\s+in\s+(?:a|an|your)\s+(?:bachelor|master|degree|university|undergraduate|graduate|study)",
    re.I,
)
# Une porte ouverte aux diplomes, DANS LA MEME PHRASE, annule la demande.
_RX_OU_DIPLOME = re.compile(
    r"recent(?:ly)?\s+grad|fresh\s+grad|graduated|already\s+hold|\bor\s+hold|\bhold(?:ing)?\s+or\b"
    # Au passe : « Tu étais étudiant(e) en école… » (Mister IA, CDI junior).
    r"|\btu\s+[ée]tais\b|\bvous\s+[ée]tiez\b"
    r"|completed|possess|\breceived\b|\bor\s+(?:a\s+)?(?:recent\s+)?graduate"
    # Le diplome AVANT l'alternative : « Master's degree (or final-year student
    # status) » (L'Oreal), « Higher education or currently studying » (Sii).
    r"|(?:degree|education|Bac\s*\+\s*\d)\s*(?:\([^)]{0,20}\)\s*)?\(?\s*or\s+(?:a\s+)?(?:final|current|penultimate)"
    # « diplômé », pas « diplôme » : « en vue de l'obtention du diplôme » est une
    # demande d'etudiant, pas une porte ouverte.
    r"|jeunes?\s+dipl[ôo]m|\bdipl[ôo]m(?:é|ée|és|ées)(?!\w)|titulaire",
    re.I,
)


def demande_etudiant(desc):
    """True si l'annonce demande un candidat ENCORE ETUDIANT, sans alternative
    pour un diplome. Un tel poste est un stage, quel que soit son intitule."""
    t = str(desc or "")
    for m in _RX_ETUDIANT.finditer(t):
        # La phrase qui porte la demande : du point precedent au suivant.
        deb = max(t.rfind(".", 0, m.start()), t.rfind("\n", 0, m.start())) + 1
        fins = [i for i in (t.find(".", m.end()), t.find("\n", m.end())) if i >= 0]
        phrase = t[deb : min(fins) if fins else len(t)]
        if not _RX_OU_DIPLOME.search(phrase):
            return True
    return False


def contrat_de_la_description(desc, defaut=""):
    """Type de contrat lu dans le CORPS de l'annonce, en deux passes.

    Un contrat FAUX est pire qu'un contrat vide : la colonne sert a filtrer.
    On privilegie donc le libelle structure, et on ne retombe sur les mots-cles
    que pour ceux qui ne peuvent rien designer d'autre."""
    t = str(desc or "")
    if len(t) < 60:
        return defaut
    # Avant tout libelle : « Contrat : CDD » sur un poste reserve aux etudiants
    # reste un emploi etudiant, pas un poste pour un diplome.
    if demande_etudiant(t):
        return "Stage"
    for m in _RX_LABEL.finditer(t):
        v = _RX_VALEUR.search(t[m.end() : m.end() + 40])
        if v:
            mot = v.group(1).lower()
            if mot.startswith("cdi") or "ind" in mot:
                return "CDI"
            if mot.startswith("cdd") or "d\u00e9termin" in mot:
                return "CDD"
            if mot.startswith(("altern", "apprent")):
                return "Alternance"
            if mot.startswith("stage"):
                return "Stage"
            if mot.startswith("int"):
                return "Interim"
            if mot.startswith("free"):
                return "Freelance"
            if mot.startswith("v"):
                return "V.I.E"
    for etiquette, motif in _DESC_CONTRAT:
        m = motif.search(t)
        if not m:
            continue
        # UNE ENUMERATION N'EST PAS UNE DECLARATION. « …et d'opportunites en
        # alternance, VIE, CDD et CDI » decrit ce qui vient APRES le stage, pas
        # le contrat propose. C'est ce CDD-la qui a fait remonter quatre stages
        # du Credit Agricole en tete de liste. Quand plusieurs types se pressent
        # dans la meme phrase, aucun ne fait foi.
        autour = t[max(0, m.start() - 90) : m.end() + 90]
        if len(_RX_TOUS_CONTRATS.findall(autour)) > 1:
            continue
        return etiquette
    return defaut


# Mentions de contrat dans l'INTITULE. Les acronymes francais sont non ambigus
# des lors qu'ils sont ancres sur des frontieres de mot. « permanent » et
# « fixed term » sont les libelles anglais equivalents, courants sur LinkedIn.
# On ne retient PAS « full-time » / « temps plein » : c'est un rythme de travail,
# pas un type de contrat — un CDD peut etre a temps plein.
_TITRE_CONTRAT = [
    (
        "CDD",
        re.compile(r"\bCDD\b|contrat\s+[àa]\s+dur[ée]e\s+d[ée]termin[ée]e|\bfixed[- ]term\b", re.I),
    ),
    (
        "CDI",
        re.compile(r"\bCDI\b|contrat\s+[àa]\s+dur[ée]e\s+ind[ée]termin[ée]e|\bpermanent\b", re.I),
    ),
    ("Freelance", re.compile(r"\bfreelance\b", re.I)),
    ("Interim", re.compile(r"\bint[ée]rim\b", re.I)),
]


def contrat_du_titre(titre, source="", defaut=""):
    """Type de contrat deduit de l'intitule, sinon `defaut`.

    Ordre voulu : les contrats etudiants d'abord. Un titre « Stage puis CDI »
    designe un stage — la mention la plus engageante pour le candidat prime.
    """
    t = str(titre or "")
    # Alternance et stage AVANT V.I.E : « Stage Analyste M&A (puis VIE/CDI) »
    # est un stage, meme si le titre evoque la suite du parcours.
    if _RX_ALT.search(t):
        return "Alternance"
    if _RX_STAGE.search(t):
        return "Stage"
    if _RX_VIE_POINTE.search(t) or _RX_VIE_MAJ.search(t) or str(source or "").startswith("vie:"):
        return "V.I.E"
    for etiquette, motif in _TITRE_CONTRAT:
        if motif.search(t):
            return etiquette
    return defaut


def title_ok(t):
    """Filtre titre : mot-clé métier requis + pas un rôle hors-cible + lexique global.
    Exception IA : un titre estampillé IA passe même s'il contient « engineer »/
    « développeur », car c'est le marché visé en complément de l'ESG."""
    if not t:
        return False
    if _P.cherche(_AI_RX, t):
        return not _P.cherche(_HARD_NEG_RX, t)
    return bool(
        matches_esg_finance(t)
        and (_DOMAIN_RX is None or _DOMAIN_RX.search(t))
        and not _P.cherche(_NEG_TITLE_RX, t)
    )


# ═══════════════ 1. ATS APIs (httpx pur, pas de navigateur) — AVEC descriptions ═══════════════
def _ats_ko(kind, slug, r):
    """Réponse inutilisable ? Et si oui, faut-il s'en inquiéter ?

    404 : le slug n'existe pas chez cet ATS. C'est le cas NORMAL — la liste est
    volontairement large, on sonde des sociétés qui n'y sont pas. Silence.
    Tout le reste (429 quota, 5xx panne) est un refus : la société a peut-être
    des offres, on ne les a pas vues. Ça se compte, sinon un scan entièrement
    bridé ressemble à un scan sans nouveauté.
    """
    if r.status_code == 200:
        return False
    if r.status_code != 404:
        INCIDENTS[f"ats:{kind}"][f"HTTP {r.status_code}"] += 1
    return True


# Le nom d'un compte ATS n'est pas celui de l'entreprise : `slug.title()` donnait
# « Grantthornton », « Societegenerale », « Vestiairecollective ». Une entreprise
# mal nommee echappe au tri par entreprise, au doublon avec LinkedIn et a toute
# recherche (2026-10-08 : Roland Berger « absent », 34 offres sous
# « rolandberger »). Les slugs absents d'ici gardent `slug.title()`.
ATS_NOMS = {
    "backmarket": "Back Market",
    "clarityai": "Clarity AI",
    "ecovadis": "EcoVadis",
    "ibanfirst": "iBanFirst",
    "payfit": "PayFit",
    "vestiairecollective": "Vestiaire Collective",
    "forvismazars": "Forvis Mazars",
    "alixpartners": "AlixPartners",
    "descartesunderwriting": "Descartes Underwriting",
    "sfeir": "SFEIR",
    "dedale-intelligence": "Dedale Intelligence",
    "grantthornton": "Grant Thornton",
    "meridiam": "Meridiam",
    "bakertilly": "Baker Tilly",
    "tikehaucapital": "Tikehau Capital",
    "axa": "AXA",
    "amundi": "Amundi",
    "bnpparibas": "BNP Paribas",
    "societegenerale": "Société Générale",
    "sycomoreassetmanagement": "Sycomore Asset Management",
    "jobteaser": "JobTeaser",
    "rolandberger": "Roland Berger",
    "southpole": "South Pole",
    "positiongreen": "Position Green",
    "cdpworldwide": "CDP",
    "keplercheuvreux": "Kepler Cheuvreux",
    "jobs.tennaxia.com": "Tennaxia",
    "paipartners": "PAI Partners",
    "8advisory": "Eight Advisory",
    "eqtpartners": "EQT",
    "epsa": "EPSA (Ekodev)",
    "masdar": "Masdar",
    "repriskag": "RepRisk",
    "ifrsfoundation": "IFRS Foundation (ISSB)",
    "oecd": "OCDE (OECD)",
    "saintgobain": "Saint-Gobain",
}


def nom_ats(slug):
    return ATS_NOMS.get(slug.lower()) or slug.title()


# Teamtailor : flux RSS public par societe, lieu en <tt:city>/<tt:country>.
# Ajoute le 2026-10-08 pour South Pole, Indefi, Datamaran, Position Green — le
# conseil ESG europeen y est, et sur aucun des cinq ATS lus jusque-la.
_RX_TT_ITEM = re.compile(r"<item>(.*?)</item>", re.S)


def _tt(champ, item):
    m = re.search(r"<" + re.escape(champ) + r">(.*?)</" + re.escape(champ) + r">", item, re.S)
    return html.unescape(m.group(1).strip()) if m else ""


def fetch_ats(kind, slug):
    import httpx

    out = []
    try:
        if kind == "greenhouse":
            # ?content=true → description HTML incluse dans la liste
            r = _get_borne(
                httpx,
                f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true",
                timeout=15,
                headers=UA,
            )
            if _ats_ko(kind, slug, r):
                return []
            for j in r.json().get("jobs", []):
                out.append(
                    _mk(
                        j.get("title", ""),
                        j.get("absolute_url", ""),
                        nom_ats(slug),
                        (j.get("location") or {}).get("name", ""),
                        j.get("updated_at", "")[:10],
                        f"greenhouse:{slug}",
                        _strip_html(j.get("content", "")),
                    )
                )
        elif kind == "lever":
            r = _get_borne(
                httpx, f"https://api.lever.co/v0/postings/{slug}?mode=json", timeout=15, headers=UA
            )
            if _ats_ko(kind, slug, r):
                return []
            for j in r.json():
                out.append(
                    _mk(
                        j.get("text", ""),
                        j.get("hostedUrl", ""),
                        nom_ats(slug),
                        (j.get("categories") or {}).get("location", ""),
                        "",
                        f"lever:{slug}",
                        j.get("descriptionPlain", "") or _strip_html(j.get("description", "")),
                    )
                )
        elif kind == "ashby":
            r = _get_borne(
                httpx,
                f"https://api.ashbyhq.com/posting-api/job-board/{slug}",
                timeout=15,
                headers=UA,
            )
            if _ats_ko(kind, slug, r):
                return []
            for j in r.json().get("jobs", []):
                out.append(
                    _mk(
                        j.get("title", ""),
                        j.get("jobUrl", ""),
                        nom_ats(slug),
                        j.get("location", ""),
                        "",
                        f"ashby:{slug}",
                        _strip_html(j.get("descriptionHtml", "")),
                    )
                )
        elif kind == "recruitee":
            r = _get_borne(
                httpx, f"https://{slug}.recruitee.com/api/offers/", timeout=15, headers=UA
            )
            if _ats_ko(kind, slug, r):
                return []
            for j in r.json().get("offers", []):
                out.append(
                    _mk(
                        j.get("title", ""),
                        j.get("careers_url", ""),
                        nom_ats(slug),
                        j.get("location", ""),
                        "",
                        f"recruitee:{slug}",
                        _strip_html(j.get("description", "")),
                    )
                )
        elif kind == "teamtailor":
            # Un domaine propre (jobs.tennaxia.com) sert le meme flux.
            hote = slug if "." in slug else f"{slug}.teamtailor.com"
            r = _get_borne(httpx, f"https://{hote}/jobs.rss", timeout=15, headers=UA)
            if _ats_ko(kind, slug, r):
                return []
            for it in _RX_TT_ITEM.findall(r.text):
                lieu = ", ".join(x for x in (_tt("tt:city", it), _tt("tt:country", it)) if x)
                out.append(
                    _mk(
                        _tt("title", it),
                        _tt("link", it),
                        nom_ats(slug),
                        lieu,
                        "",
                        f"teamtailor:{slug}",
                        _strip_html(_tt("description", it)),
                    )
                )
        elif kind == "smartrecruiters":
            r = _get_borne(
                httpx,
                f"https://api.smartrecruiters.com/v1/companies/{slug}/postings?limit=100",
                timeout=15,
                headers=UA,
            )
            if _ats_ko(kind, slug, r):
                return []
            for j in r.json().get("content", []):
                o = _mk(
                    j.get("name", ""),
                    f"https://jobs.smartrecruiters.com/{slug}/{j.get('id', '')}",
                    nom_ats(slug),
                    (j.get("location") or {}).get("city", ""),
                    str(j.get("releasedDate", ""))[:10],
                    f"smartrecruiters:{slug}",
                )
                out.append(o)
        # SmartRecruiters : description via appel détail — seulement pour les titres retenus (peu)
        if kind == "smartrecruiters":
            kept = [o for o in out if title_ok(o["titre"])]
            for o in kept:
                try:
                    jid = o["url"].rstrip("/").split("/")[-1]
                    rd = _get_borne(
                        httpx,
                        f"https://api.smartrecruiters.com/v1/companies/{slug}/postings/{jid}",
                        timeout=12,
                        headers=UA,
                    )
                    if rd.status_code == 200:
                        secs = (rd.json().get("jobAd") or {}).get("sections") or {}
                        o["description"] = _strip_html(
                            " ".join(
                                str(v.get("text", "")) for v in secs.values() if isinstance(v, dict)
                            )
                        )[:30000]
                except Exception:
                    pass
                time.sleep(0.4)  # appel détail par offre : on ne mitraille pas
            # Meme garde que la sortie normale : une offre sans URL n'est pas
            # exploitable, elle ne doit pas entrer par cette branche non plus.
            return [o for o in kept if o["titre"] and o["url"]]
    except Exception as e:
        INCIDENTS[f"ats:{kind}"][type(e).__name__] += 1
        return []
    return [o for o in out if o["titre"] and o["url"] and title_ok(o["titre"])]


ATS_PAUSE = 0.5  # entre deux slugs : 40 appels d'affilee, autant les espacer


def scan_ats():
    offers = []
    for kind, slugs in ATS_SLUGS.items():
        for slug in slugs:
            got = fetch_ats(kind, slug)
            if got:
                print(f"  ✓ {kind}:{slug} → {len(got)} offres")
            offers.extend(got)
            time.sleep(ATS_PAUSE)
    offers.extend(scan_autres())
    return offers


# ═══════════════ 1 ter. Autres API publiques de recrutement ═══════════════
# Trouvees le 2026-10-08 en suivant le lien « Carrieres » des sites de ~150
# societes (probe_carrieres.sonde_site, puis les iframes/scripts de la page
# carriere). Chacune est l'API JSON/RSS que la page carriere appelle elle-meme.
#   workable   apply.workable.com/api/v1/widget/accounts/{slug}
#   pinpoint   {slug}.pinpointhq.com/postings.json
#   eightfold  {hote}/api/apply/v2/jobs?domain={domaine}&query=   (BCG)
#   sfrss      {hote}/services/rss/job/?keywords=   (SAP SuccessFactors, site carriere)
#   oracle     {hote}/hcmRestApi/.../recruitingCEJobRequisitions   (Oracle Recruiting)
# Les trois dernieres cherchent cote serveur : une requete par mot de WORKDAY_MOTS.
AUTRES_FLUX = [
    ("workable", "quantis", "Quantis"),
    ("pinpoint", "cinven", "Cinven"),
    ("eightfold", "bcg.eightfold.ai|bcg.com", "BCG"),
    ("sfrss", "careers.fitch.group", "Fitch"),
    ("sfrss", "careers.scopegroup.com", "Scope Ratings"),
    ("sfrss", "careers.ey.com", "EY"),
    ("sfrss", "jobs.ebrd.com", "BERD (EBRD)"),
    ("sfrss", "careers.capgemini.com", "Capgemini"),
    ("talentsoft", "jobs.amundi.com", "Amundi"),  # CPR AM compris
    ("talentsoft", "jobs.candriam.com", "Candriam"),
    # Phenom (resultats embarques en JSON), iCIMS (liste HTML), Cornerstone
    # (jeton anonyme de la page publique) : ajoutes le 2026-10-08.
    ("phenom", "jobs.bureauveritas.com/gb/en", "Bureau Veritas"),
    ("phenom", "careers.allianz.com/global/en", "Allianz"),
    ("phenom", "orange.jobs/fr/fr", "Orange"),
    ("avature", "totalenergies.avature.net/en_US/careers", "TotalEnergies"),
    ("avature", "talent.ecb.europa.eu/careers", "BCE (ECB)"),
    ("eightfold", "portal.careers.hsbc.com|hsbc.com", "HSBC"),
    ("talentbrew", "careers.moodys.com/en|49841", "Moody's"),
    ("peoplesoft", "erecruitment.eib.org/psc/hr/EIBJOBS/CAREERS", "BEI (EIB)"),
    ("talentbrew", "careers.ing.com/en|3121", "ING"),
    ("avature", "careers.unicredit.eu/en_GB/jobsuche", "UniCredit"),
    ("oracle", "ejqi.fa.ocs.oraclecloud.eu|CX_1001", "Danske Bank"),
    ("sfrss", "careers.gic.com.sg", "GIC"),
    ("adb", "www.adb.org/work-with-us/careers/current-opportunities", "BAD (ADB)"),
    ("gogenerali", "gogenerali.com", "Generali"),
    ("sitemap", "https://www.werkenbijabnamro.nl/sitemap.vacancy.xml|/vacature/", "ABN AMRO"),
    ("sitemap", "https://www.kbc.be/jobs/en.sitemap.xml|/jobs/en/vacancies/ID|h1", "KBC"),
    ("sfrss", "jobs.engie.com", "ENGIE"),
    ("sfrss", "jobs.atos.net", "Atos"),
    ("icims", "careers-msci.icims.com", "MSCI"),  # portail US
    ("icims", "ukcareers-msci.icims.com", "MSCI"),  # portail Europe
    ("icims", "careers-ricardo.icims.com", "Ricardo"),
    ("sitemap", "https://www.sia-partners.com/sitemap.xml|/en/career/", "Sia Partners"),
    ("sitemap", "https://carbone4.com/jobs-sitemap.xml|/en/jobs/", "Carbone 4"),
    ("csod", "afd.csod.com|5", "AFD / Proparco"),
    ("csod", "worldbankgroup.csod.com|1", "Banque mondiale / IFC"),
    # International (2026-10-08).
    ("oracle", "enlc.fa.ap1.oraclecloud.com|CX", "IFM Investors"),
    ("oracle", "ehjd.fa.em2.oraclecloud.com|fabCareers", "First Abu Dhabi Bank"),
    ("oracle", "fa-evlo-saasfaprod1.fa.ocs.oraclecloud.com|CX_1", "Emirates NBD"),
    # Vitrine en 403, ATS public a cote (2026-10-08) : PNUD sur Oracle Quantum.
    ("oracle", "estm.fa.em2.oraclecloud.com|CX_1", "PNUD (UNDP)"),
    ("jibe", "careers.se.com", "Schneider Electric"),
    ("sfrss", "careers.swissre.com", "Swiss Re"),
    ("sfrss", "careers.acwapower.com", "ACWA Power"),
    ("sfrss", "careers.isdb.org", "Banque islamique de développement"),
    # Hotes devines puis verifies (/services/rss/job/ repond), 2026-10-08.
    ("sfrss", "jobs.standardchartered.com", "Standard Chartered"),
    ("sfrss", "careers.nordea.com", "Nordea"),
    ("sfrss", "careers.nomura.com", "Nomura"),
    ("sfrss", "jobs.intesasanpaolo.com", "Intesa Sanpaolo"),
    ("sfrss", "jobs.dzbank.de", "DZ Bank"),
    ("sfrss", "careers.triodos.com", "Triodos"),
    ("sfrss", "jobs.belfius.be", "Belfius"),
    ("pinpoint", "jobs.clientearth.org", "ClientEarth"),
    ("workable", "tracker-group", "Carbon Tracker"),
    ("oracle", "icbpjb.fa.ocs.oraclecloud.com|CX_1", "Lazard"),
    ("oracle", "ekbq.fa.em2.oraclecloud.com|CX_1", "Schroders"),
]
_RX_CDATA = re.compile(r"^<!\[CDATA\[(.*)\]\]>$", re.S)
_RX_LIEU_FIN = re.compile(r"\s*\(([^()]*)\)\s*$")
_RX_TS_CAT = re.compile(r"<category>(.*?)</category>", re.S)
_RX_TS_REF = re.compile(r"^\s*\d{4}-\d+\s+-\s+")
_RX_AV_TITRE = re.compile(
    r'<h3 class="article__header__text__title[^"]*">\s*<a (?:class="link" )?href="([^"]+)">\s*([^<]+?)\s*</a>'
)
_RX_AV_PAYS = re.compile(r'list-item-jobCountry">([^<]+)<')
_RX_AV_DATE = re.compile(r'list-item-jobCreationDate">(\d{2})-(\d{2})-(\d{4})<')
# Deux themes TalentBrew : titre dans le <a> (Moody's) ou dans un <h2> a l'interieur (ING).
_RX_TB_LIEN = re.compile(
    r'href="(/[a-z-]+/job/[^"]+)"[^>]*data-job-id="\d+"[^>]*>\s*(?:<h2[^>]*>)?\s*([^<]+?)\s*<'
)
_RX_TB_LIEU = re.compile(r'job-location">([^<]+)<')
_RX_ADB_LIGNE = re.compile(
    r'<a href="(https://www\.adb\.org/careers/\d+)">([^<]+?)\s*/\s*\d+</a>(.*?)</tr>', re.S
)
_RX_ADB_LIEU = re.compile(r'field-location">\s*([^<]+?)\s*<')
_RX_ADB_DATE = re.compile(r'field-date-content"><time datetime="(\d{4}-\d{2}-\d{2})')
_RX_PS_CHAMP = re.compile(
    r"id='(SCH_JOB_TITLE|HRS_APP_JBSCH_I_HRS_JOB_OPENING_ID|SCH_OPENED|LOCATION)\$(\d+)'\s*>([^<]*)<"
)
_RX_CSOD_CTX = re.compile(r"csod\.context\s*=\s*(\{.*?\});", re.S)
_RX_ICIMS_CARTE = re.compile(r'<li class="iCIMS_JobCardItem">(.*?)</li>', re.S)
_RX_ICIMS_LIEN = re.compile(r'<a href="([^"]+/jobs/\d+/[^"]*)"[^>]*title="\d+ - ([^"]+)"')
_RX_ICIMS_LIEU = re.compile(r"Job Locations</span>\s*</dt>\s*<dd[^>]*><span\s*>\s*([^<]+)</span>")


ICIMS_PAGES = 15
SITEMAP_JOURS = 60
_RX_SM_INDEX = re.compile(r"<sitemap>\s*<loc>([^<]+)</loc>")
_RX_SM_URL = re.compile(r"<url>\s*<loc>([^<]+)</loc>(.*?)</url>", re.S)
_RX_SM_DATE = re.compile(r"<lastmod>(\d{4}-\d{2}-\d{2})")
_RX_SM_NUM = re.compile(r"\s+\d{1,2}$")
_RX_SM_ID = re.compile(r"^\d{3,}[\s/]+")
_RX_SM_H1 = re.compile(r"<h1[^>]*>(.*?)</h1>", re.S)


def _sans_cdata(s):
    m = _RX_CDATA.match(s.strip())
    return m.group(1) if m else s


def fetch_autre(kind, cle, nom):
    import httpx

    out = []
    try:
        if kind == "workable":
            r = _get_borne(
                httpx,
                f"https://apply.workable.com/api/v1/widget/accounts/{cle}",
                timeout=15,
                headers=UA,
            )
            if _ats_ko(kind, cle, r):
                return []
            for j in r.json().get("jobs", []):
                lieu = ", ".join(x for x in (j.get("city"), j.get("country")) if x)
                out.append(
                    _mk(
                        j.get("title", ""),
                        j.get("url", ""),
                        nom,
                        lieu,
                        j.get("published_on", ""),
                        f"workable:{cle}",
                    )
                )
        elif kind == "pinpoint":
            hote = cle if "." in cle else f"{cle}.pinpointhq.com"  # domaine propre accepte
            r = _get_borne(
                httpx,
                f"https://{hote}/postings.json",
                timeout=15,
                headers=UA,
                follow_redirects=True,
            )
            if _ats_ko(kind, cle, r):
                return []
            for j in r.json().get("data", []):
                out.append(
                    _mk(
                        j.get("title", ""),
                        j.get("url", ""),
                        nom,
                        (j.get("location") or {}).get("name", ""),
                        "",
                        f"pinpoint:{cle}",
                        _strip_html(j.get("description", "")),
                    )
                )
        elif kind == "sitemap":
            # Sites maison sans API, mais dont le sitemap liste chaque offre avec
            # sa date (Sia Partners, Carbone 4). Titre tire de l'adresse : leur
            # page d'offre affiche « Offres d'emploi » en <h1>, pas l'intitule.
            # « racine|chemin|h1 » : l'adresse ne porte qu'un identifiant (KBC),
            # le titre se lit alors dans le <h1> de chaque page.
            racine, chemin, *mode = cle.split("|")
            limite = (datetime.date.today() - datetime.timedelta(days=SITEMAP_JOURS)).isoformat()
            r = _get_borne(httpx, racine, timeout=20, headers=UA, follow_redirects=True)
            if _ats_ko(kind, racine, r):
                return []
            xml = [r.text]
            for enfant in _RX_SM_INDEX.findall(r.text) if "<sitemapindex" in r.text else []:
                re_ = _get_borne(
                    httpx, html.unescape(enfant), timeout=20, headers=UA, follow_redirects=True
                )
                if re_.status_code == 200:
                    xml.append(re_.text)
            vus = set()
            for x in xml:
                for loc, reste in _RX_SM_URL.findall(x):
                    loc = html.unescape(loc)
                    date = (_RX_SM_DATE.findall(reste) or [""])[0]
                    if chemin not in loc or loc in vus or (date and date < limite):
                        continue
                    vus.add(loc)
                    # Tout ce qui suit le chemin : « internship-consultant-m/f-january-2027 »
                    # contient un « / ». Le « -0 », « -1 » final est un doublon de slug.
                    slug = loc.split(chemin, 1)[1].strip("/")
                    titre = re.sub(r"[-_]+", " ", unquote(slug)).strip()
                    # « 7827/senior-esg-risk-analyst » (ABN AMRO) : l'identifiant en tete tombe.
                    titre = _RX_SM_ID.sub("", _RX_SM_NUM.sub("", titre)).capitalize()
                    if mode == ["h1"]:
                        p = _get_borne(httpx, loc, timeout=20, headers=UA, follow_redirects=True)
                        h1 = _RX_SM_H1.search(p.text) if p.status_code == 200 else None
                        if not h1:
                            continue
                        titre = html.unescape(re.sub(r"<[^>]+>", "", h1.group(1))).strip()
                        time.sleep(WORKDAY_PAUSE)
                    out.append(_mk(titre, loc, nom, "", date, f"sitemap:{urlparse(racine).netloc}"))
        elif kind == "peoplesoft":
            # PeopleSoft Fluid (BEI) : la page de recherche rendue cote serveur
            # liste toutes les offres ouvertes, champs indexes par ligne ($0, $1...).
            # Le lien de detail exige la session : il ouvre la liste, puis l'offre.
            base = f"https://{cle}/c/HRS_HRAM_FL.HRS_CG_SEARCH_FL.GBL"
            r = _get_borne(
                httpx,
                f"{base}?Page=HRS_APP_SCHJOB_FL&Action=U",
                timeout=30,
                headers=UA,
                follow_redirects=True,
            )
            if _ats_ko(kind, cle, r):
                return []
            champs = {}
            for nom_champ, i, val in _RX_PS_CHAMP.findall(r.text):
                champs.setdefault(i, {})[nom_champ] = html.unescape(val.strip())
            for i in sorted(champs, key=int):
                c = champs[i]
                ident = c.get("HRS_APP_JBSCH_I_HRS_JOB_OPENING_ID", "")
                if not c.get("SCH_JOB_TITLE") or not ident:
                    continue
                jj, mm, aa = (c.get("SCH_OPENED", "").split("/") + ["", "", ""])[:3]
                out.append(
                    _mk(
                        c["SCH_JOB_TITLE"],
                        f"{base}?Page=HRS_APP_JBPST_FL&Action=U"
                        f"&FOCUS=Applicant&SiteId=1&JobOpeningId={ident}&PostingSeq=1",
                        nom,
                        c.get("LOCATION", ""),
                        f"{aa}-{mm}-{jj}" if aa else "",
                        f"peoplesoft:{cle.split('/')[0]}",
                    )
                )
        elif kind == "gogenerali":
            # Generali (portail italien, sieges et filiales) : l'API de la page
            # repond sans jeton. Les agences (hors perimetre « direzionale ») sont
            # des postes commerciaux, exclus. Fiche : /home/job/{id}/{titre}.
            r = _get_borne(
                httpx,
                f"https://{cle}/rest-api/talent-farm-mediator/get-available-jobs-from-ats"
                f"?fromRecord=0&numRecords=1000&onlyDirectionalPerimeter=true",
                timeout=30,
                headers={**UA, "Accept": "application/json"},
            )
            if _ats_ko(kind, cle, r):
                return []
            for j in (r.json() or {}).get("response") or []:
                if not j.get("contestId") or j.get("currentStatus") != "PUBLISHED":
                    continue
                slug = re.sub(r"[^a-z0-9]+", "-", (j.get("title") or "").lower()).strip("-")
                desc = _strip_html(
                    (j.get("descriptionInternalHTML") or "")
                    + " "
                    + (j.get("internalQualificationHTML") or "")
                )
                out.append(
                    _mk(
                        j.get("title", ""),
                        f"https://{cle}/home/job/{j['contestId']}/{slug}",
                        nom,
                        j.get("primaryLocation") or "",
                        (j.get("currentStatusDate") or "")[:10],
                        f"gogenerali:{cle}",
                        desc,
                    )
                )
        elif kind == "adb":
            # Banque asiatique de developpement : tableau HTML de toutes les
            # offres ouvertes, « Intitule / reference » dans le lien.
            r = _get_borne(httpx, f"https://{cle}", timeout=30, headers=UA, follow_redirects=True)
            if _ats_ko(kind, cle, r):
                return []
            for url, titre, reste in _RX_ADB_LIGNE.findall(r.text):
                l, d = _RX_ADB_LIEU.search(reste), _RX_ADB_DATE.search(reste)
                out.append(
                    _mk(
                        html.unescape(titre),
                        url,
                        nom,
                        html.unescape(l.group(1)) if l else "",
                        d.group(1) if d else "",
                        "adb:adb.org",
                    )
                )
        elif kind == "icims":
            # Liste HTML paginee (pr=0, 1, ...), filtree ensuite par title_ok :
            # la recherche par mot-cle de l'iframe ne rend rien sans session.
            vus = set()
            for page in range(ICIMS_PAGES):
                r = _get_borne(
                    httpx,
                    f"https://{cle}/jobs/search?ss=1&in_iframe=1&pr={page}",
                    timeout=20,
                    headers=UA,
                    follow_redirects=True,
                )
                if _ats_ko(kind, cle, r):
                    break
                neufs = 0
                for carte in _RX_ICIMS_CARTE.findall(r.text):
                    m = _RX_ICIMS_LIEN.search(carte)
                    if not m or m.group(1) in vus:
                        continue
                    vus.add(m.group(1))
                    neufs += 1
                    l = _RX_ICIMS_LIEU.search(carte)
                    out.append(
                        _mk(
                            html.unescape(m.group(2)),
                            m.group(1).replace("?in_iframe=1", ""),
                            nom,
                            html.unescape(l.group(1).strip()) if l else "",
                            "",
                            f"icims:{cle}",
                        )
                    )
                if not neufs:
                    break
                time.sleep(WORKDAY_PAUSE)
        else:
            vus = set()
            for mot in WORKDAY_MOTS:
                for titre, url, lieu, date, desc in _cherche_autre(httpx, kind, cle, mot):
                    if url and url not in vus:
                        vus.add(url)
                        out.append(
                            _mk(titre, url, nom, lieu, date, f"{kind}:{cle.split('|')[0]}", desc)
                        )
                time.sleep(WORKDAY_PAUSE)
    except Exception as e:
        INCIDENTS[f"ats:{kind}"][type(e).__name__] += 1
        return []
    return [o for o in out if o["titre"] and o["url"] and title_ok(o["titre"])]


def _cherche_autre(httpx, kind, cle, mot):
    """[(titre, url, lieu, date, description)] pour un mot-cle, cote serveur."""
    if kind == "eightfold":
        hote, domaine = cle.split("|")
        r = _get_borne(
            httpx,
            f"https://{hote}/api/apply/v2/jobs?domain={domaine}&start=0&num=50&query={quote(mot)}",
            timeout=20,
            headers=UA,
        )
        if _ats_ko(kind, hote, r):
            return []
        return [
            (
                p.get("name", ""),
                p.get("canonicalPositionUrl", ""),
                p.get("location", ""),
                "",
                _strip_html(p.get("job_description", "")),
            )
            for p in r.json().get("positions", [])
        ]
    if kind == "sfrss":
        r = _get_borne(
            httpx,
            f"https://{cle}/services/rss/job/?locale=en_US&keywords={quote(mot)}",
            timeout=20,
            headers=UA,
        )
        if _ats_ko(kind, cle, r):
            return []
        res = []
        for it in _RX_TT_ITEM.findall(r.text):
            titre = _sans_cdata(_tt("title", it))
            m = _RX_LIEU_FIN.search(titre)  # « Analyst - Paris (Paris, FR) »
            lieu = m.group(1) if m else ""
            titre = _RX_LIEU_FIN.sub("", titre) if m else titre
            titre = titre[6:] if titre.startswith("Job | ") else titre  # Belfius
            res.append(
                (
                    titre,
                    _sans_cdata(_tt("link", it)),
                    lieu,
                    "",
                    _strip_html(_sans_cdata(_tt("description", it))),
                )
            )
        return res
    if kind == "talentsoft":
        # Sans Rss_Keywords le flux rend les 20 dernieres offres, tous metiers.
        r = _get_borne(
            httpx,
            f"https://{cle}/handlers/offerRss.ashx?LCID=1036&Rss_Keywords={quote(mot)}",
            timeout=20,
            headers=UA,
        )
        if _ats_ko(kind, cle, r):
            return []
        res = []
        for it in _RX_TT_ITEM.findall(r.text):
            cats = [html.unescape(c.strip()) for c in _RX_TS_CAT.findall(it)]
            titre = _RX_TS_REF.sub("", _tt("title", it))  # « 2026-116250 - Stage - ... »
            res.append(
                (
                    titre,
                    _tt("link", it),
                    cats[-1] if len(cats) >= 3 else "",
                    "",
                    _strip_html(_tt("description", it)),
                )
            )
        return res
    if kind == "phenom":
        # La page de resultats embarque ses offres en JSON (phApp.ddo), 10 par
        # page. C'est le rendu serveur que tout visiteur recoit.
        res = []
        for depart in (0, 10):
            r = _get_borne(
                httpx,
                f"https://{cle}/search-results?keywords={quote(mot)}&from={depart}",
                timeout=20,
                headers=UA,
            )
            if _ats_ko(kind, cle, r):
                break
            i = r.text.find("phApp.ddo = ")
            if i < 0:
                break
            try:
                ddo, _ = json.JSONDecoder().raw_decode(r.text[i + 12 :])
                jobs = ddo["eagerLoadRefineSearch"]["data"]["jobs"]
            except Exception:
                break
            res += [
                (
                    j.get("title", ""),
                    f"https://{cle}/job/{j.get('jobId', '')}",
                    j.get("cityStateCountry") or j.get("location") or "",
                    str(j.get("postedDate") or "")[:10],
                    j.get("descriptionTeaser") or "",
                )
                for j in jobs
                if j.get("jobId")
            ]
            if len(jobs) < 10:
                break
        return res
    if kind == "jibe":
        # Jibe (Google Cloud Talent) : la page carriere appelle /api/jobs, JSON
        # public, description comprise. Schneider Electric (2026-10-08).
        r = _get_borne(
            httpx,
            f"https://{cle}/api/jobs?page=1&keywords={quote(mot)}&sortBy=relevance&limit=50",
            timeout=20,
            headers={**UA, "Accept": "application/json"},
            follow_redirects=True,
        )
        if _ats_ko(kind, cle, r):
            return []
        res = []
        for j in (r.json() or {}).get("jobs") or []:
            d = j.get("data") or {}
            if not d.get("slug"):
                continue
            res.append(
                (
                    d.get("title", ""),
                    f"https://{cle}/jobs/{d['slug']}?lang=en-us",
                    d.get("location_name") or d.get("country") or "",
                    "",
                    _strip_html(d.get("description") or ""),
                )
            )
        return res
    if kind == "talentbrew":
        # Radancy TalentBrew : la page de recherche (mot dans le chemin) est
        # rendue cote serveur. Moody's, ING (2026-10-08). cle = « hote/langue|org ».
        base, org = cle.split("|")
        r = _get_borne(
            httpx,
            f"https://{base}/search-jobs/{quote(mot)}/{org}/1",
            timeout=20,
            headers=UA,
            follow_redirects=True,
        )
        if _ats_ko(kind, base, r):
            return []
        hote = base.split("/")[0]
        res, vus = [], set()
        for m in _RX_TB_LIEN.finditer(r.text):
            if m.group(1) in vus:
                continue
            vus.add(m.group(1))
            l = _RX_TB_LIEU.search(r.text, m.end(), m.end() + 1500)
            res.append(
                (
                    html.unescape(m.group(2).strip()),
                    f"https://{hote}{m.group(1)}",
                    html.unescape(l.group(1).strip()) if l else "",
                    "",
                    "",
                )
            )
        return res
    if kind == "avature":
        # Page de recherche rendue cote serveur, 50 cartes par page.
        r = _get_borne(
            httpx,
            f"https://{cle}/SearchJobs/?listFilterMode=1&jobRecordsPerPage=50&search={quote(mot)}",
            timeout=20,
            headers=UA,
            follow_redirects=True,
        )
        if _ats_ko(kind, cle, r):
            return []
        res = []
        for carte in r.text.split('class="article article--result"')[1:]:
            m = _RX_AV_TITRE.search(carte)
            if not m:
                continue
            pays = _RX_AV_PAYS.search(carte)
            d = _RX_AV_DATE.search(carte)
            res.append(
                (
                    html.unescape(m.group(2).strip()),
                    m.group(1),
                    html.unescape(pays.group(1).strip()) if pays else "",
                    f"{d.group(3)}-{d.group(2)}-{d.group(1)}" if d else "",
                    "",
                )
            )
        return res
    if kind == "csod":
        # Cornerstone : la page publique delivre a tout visiteur un jeton
        # anonyme, que son propre script envoie a l'API de recherche.
        hote, site = cle.split("|")
        tenant = hote.split(".")[0]
        page = _get_borne(
            httpx,
            f"https://{hote}/ux/ats/careersite/{site}/home?c={tenant}",
            timeout=20,
            headers=UA,
        )
        if _ats_ko(kind, hote, page):
            return []
        m = _RX_CSOD_CTX.search(page.text)
        ctx = json.loads(m.group(1)) if m else {}
        api = ((ctx.get("endpoints") or {}).get("cloud") or "").rstrip("/")
        if not ctx.get("token") or not api:
            return []
        r = _post_borne(
            httpx,
            f"{api}/rec-job-search/external/jobs",
            timeout=20,
            headers={
                **UA,
                "Authorization": "Bearer " + ctx["token"],
                "Content-Type": "application/json",
            },
            json={
                "careerSiteId": int(site),
                "careerSitePageId": int(site),
                "pageNumber": 1,
                "pageSize": 50,
                "cultureId": 1,
                "searchText": mot,
                "cultureName": "en-US",
                "states": [],
                "countryCodes": [],
                "cities": [],
                "placeID": "",
                "radius": None,
                "postingsWithinDays": None,
                "customFieldCheckboxKeys": [],
                "customFieldDropdowns": [],
                "customFieldRadios": [],
            },
        )
        if _ats_ko(kind, hote, r):
            return []
        res = []
        for j in ((r.json() or {}).get("data") or {}).get("requisitions") or []:
            loc = (j.get("locations") or [{}])[0]
            lieu = ", ".join(x for x in (loc.get("city"), loc.get("country")) if x)
            res.append(
                (
                    j.get("displayJobTitle", ""),
                    f"https://{hote}/ux/ats/careersite/{site}/home/requisition/"
                    f"{j.get('requisitionId', '')}?c={tenant}",
                    lieu,
                    "",
                    j.get("externalDescription") or "",
                )
            )
        return res
    if kind == "oracle":
        hote, site = cle.split("|")
        r = _get_borne(
            httpx,
            f"https://{hote}/hcmRestApi/resources/latest/recruitingCEJobRequisitions"
            f"?onlyData=true&expand=requisitionList&finder=findReqs;siteNumber={site},"
            f"limit=50,keyword={quote(mot)}",
            timeout=20,
            headers=UA,
        )
        if _ats_ko(kind, hote, r):
            return []
        items = r.json().get("items") or [{}]
        return [
            (
                j.get("Title", ""),
                f"https://{hote}/hcmUI/CandidateExperience/en/sites/{site}/job/{j.get('Id', '')}",
                j.get("PrimaryLocation", ""),
                j.get("PostedDate", ""),
                j.get("ShortDescriptionStr") or "",
            )
            for j in items[0].get("requisitionList") or []
            if j.get("Id")
        ]
    return []


# Choisir le service public : le portail des trois fonctions publiques (CDC,
# Banque de France, AMF, ACPR, ministeres...). Trouve le 2026-10-08 en cherchant
# « Caisse des Depots recrutement » : la CDC n'a pas de flux propre, ses offres
# sont la. Recherche plein texte large (22 409 resultats pour « esg »), triee
# par pertinence : deux pages par mot suffisent, title_ok fait le reste.
CSP = "https://choisirleservicepublic.gouv.fr"
CSP_MOTS = [
    "esg",
    "finance durable",
    "analyste financier",
    "finance climat",
    "analyste investissement",
    "risques financiers",
    "taxonomie",
    "extra-financier",
]
# Mesure du 2026-10-08 : 178 offres passent title_ok, dont 36 communes et 31
# intercommunalites. On ne garde que les employeurs financiers publics, ou un
# intitule franchement ESG / finance durable quel que soit l'employeur.
_RX_CSP_EMPLOYEUR = re.compile(
    r"caisse des d[ée]p[ôo]ts|\bCDC\b|banque de france|\bAMF\b|autorit[ée] des march[ée]s|"
    r"\bACPR\b|contr[ôo]le prudentiel|\bAFD\b|agence fran[cç]aise de d[ée]veloppement|"
    r"bpifrance|tr[ée]sor|\bADEME\b|banque des territoires|cour des comptes|"
    r"\bIGF\b|inspection g[ée]n[ée]rale des finances|\bDGFIP\b|finances publiques|"
    r"[ée]conomie,? des finances|\bFRR\b|fonds de r[ée]serve|\bCNP\b|"
    r"agence des participations|\bAPE\b|\bIEDOM\b|\bIEOM\b",
    re.I,
)
_RX_CSP_INTITULE = re.compile(
    # Pas « climat » seul : plans climat territoriaux, et meme « climat scolaire ».
    r"\bESG\b|\bRSE\b|finance durable|extra-?financ|taxonomie|\bISR\b|"
    r"analyste financ|analyste investissement|risques? financ|finance climat",
    re.I,
)
_RX_CSP_TITRE = re.compile(
    r'<h3 class="fr-card__title">\s*<a\s+href="([^"]+)"[^>]*>\s*([^<]+?)\s*</a>'
)
_RX_CSP_CHAMP = re.compile(r'<span class="sr-only">([^<]+?) : </span>\s*(.*?)\s*</li>', re.S)


def fetch_service_public():
    import httpx

    out, vus = [], set()
    try:
        for mot in CSP_MOTS:
            for page in (1, 2):
                url = f"{CSP}/nos-offres/filtres/mot-cles/{quote(mot)}/" + (
                    f"page/{page}/" if page > 1 else ""
                )
                r = _get_borne(httpx, url, timeout=20, headers=UA, follow_redirects=True)
                if _ats_ko("service_public", mot, r):
                    break
                # Une carte contient ses propres <li> : on decoupe sur son
                # ouverture plutot que de chercher sa fermeture.
                for carte in r.text.split('<li class="fr-col-12 item">')[1:]:
                    m = _RX_CSP_TITRE.search(carte)
                    if not m or m.group(1) in vus:
                        continue
                    vus.add(m.group(1))
                    ch = {k.strip(): _texte_brut(v) for k, v in _RX_CSP_CHAMP.findall(carte)}
                    out.append(
                        _mk(
                            html.unescape(m.group(2)),
                            m.group(1),
                            ch.get("Employeur") or "Fonction publique",
                            ch.get("Localisation", ""),
                            "",
                            "service_public",
                        )
                    )
                time.sleep(WORKDAY_PAUSE)
    except Exception as e:
        INCIDENTS["service_public"][type(e).__name__] += 1
    return [
        o
        for o in out
        if o["titre"]
        and o["url"]
        and title_ok(o["titre"])
        and (_RX_CSP_EMPLOYEUR.search(o["entreprise"]) or _RX_CSP_INTITULE.search(o["titre"]))
    ]


# Impactpool : agregateur des organisations internationales (ONU, OCDE, BEI,
# banques de developpement). robots.txt n'interdit rien. Trouve le 2026-10-08
# en cherchant ou publient les organisations dont la vitrine repond 403 :
# leur vitrine refuse, leurs offres sont ici.
IMPACTPOOL = "https://www.impactpool.org"
# Mesure du 2026-10-08 : 7 recherches a 0,6 s d'intervalle -> la 1re rend 200,
# les 6 suivantes 403. Un refus s'arrete (regle du projet) : peu de mots, une
# longue pause, et arret au premier refus — pas de nouvelle tentative.
# NON BRANCHE dans scan_autres : relance 1 min plus tard, la 1re requete rend
# deja 403 (adresse marquee). A reessayer au plus tot le 2026-11-08, a la main.
IMPACTPOOL_MOTS = ["sustainable finance", "ESG", "climate finance"]
IMPACTPOOL_PAUSE = 15
_RX_IP_CARTE = re.compile(
    r"<div class='job'>.*?<a[^>]*href=\"(/jobs/\d+)\".*?<h3[^>]*>\s*([^<]+?)\s*</h3>"
    r".*?type='bodyEmphasis'>\s*([^<]+?)\s*<.*?type='bodyEmphasis'>([^<]*)</div>",
    re.S,
)


def fetch_impactpool():
    import httpx

    out, vus = [], set()
    try:
        for mot in IMPACTPOOL_MOTS:
            r = _get_borne(
                httpx,
                f"{IMPACTPOOL}/search?q={quote(mot)}",
                timeout=20,
                headers=UA,
                follow_redirects=True,
            )
            if _ats_ko("impactpool", mot, r):
                break  # refus : on s'arrete
            for chemin, titre, org, lieu in _RX_IP_CARTE.findall(r.text):
                if chemin in vus:
                    continue
                vus.add(chemin)
                out.append(
                    _mk(
                        html.unescape(titre),
                        IMPACTPOOL + chemin,
                        html.unescape(org),
                        html.unescape(lieu.strip()),
                        "",
                        "impactpool",
                    )
                )
            time.sleep(IMPACTPOOL_PAUSE)
    except Exception as e:
        INCIDENTS["impactpool"][type(e).__name__] += 1
    return [o for o in out if o["titre"] and o["url"] and title_ok(o["titre"])]


def _texte_brut(fragment):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def scan_autres():
    offres = []
    for kind, cle, nom in AUTRES_FLUX:
        got = fetch_autre(kind, cle, nom)
        print(f"  ✓ {kind}:{cle.split('|')[0]} → {len(got)} offres")
        offres.extend(got)
        time.sleep(ATS_PAUSE)
    got = fetch_service_public()
    print(f"  ✓ choisirleservicepublic → {len(got)} offres")
    offres.extend(got)
    return offres


# ═══════════════ 1 bis. Workday — l'API publique des grands groupes ═══════════════
# POURQUOI. Les pages carriere de ces groupes sont des SPA derriere un anti-bot :
# scrape_jobs.py les ouvre et n'y lit rien (mesure : 11 sites, 0 offre). Mais
# leurs offres sont servies par Workday sur *.myworkdayjobs.com, dont l'API JSON
# est publique et non authentifiee — c'est celle que leur propre page appelle.
# On lit la source au lieu de forcer la vitrine.
#
# Les flux ci-dessous ont ete trouves par probe_carrieres.py (lien « Carrieres »
# de la page d'accueil -> hote ATS) et VERIFIES : Eiffage 2000 offres, Ardian 74,
# Lombard Odier 35. 2109 offres la ou le scraper DOM en ramene zero.
#
# DEUX LIMITES DE L'API, mesurees :
#   - `limit` plafonne a 20. Au-dela la reponse est VIDE, pas tronquee : demander
#     100 rend 0 offre. Eiffage en entier ferait donc 100 requetes.
#   - `searchText` filtre cote serveur et ramene 2000 a 70-500. Le tri est par
#     pertinence, les premieres pages portent les bonnes offres.
# D'ou la strategie : quelques mots-cles, peu de pages chacun, union et dedup.
WORKDAY_FLUX = [
    # (tenant, host, site, nom lisible)
    ("eiffage", "wd3", "Eiffage_Careers", "Eiffage"),
    ("ardian", "wd103", "ArdianCareers", "Ardian"),
    ("lombardodier", "wd3", "Lombard_Odier_Careers", "Lombard Odier"),
    # PwC, tous pays dont la France (Neuilly) : 3897 offres experimentees et
    # 1359 campus (2026-10-07). Les Big 4 n'arrivaient que par LinkedIn ; le
    # nom de site ne suit aucune forme que site_final sait deviner.
    ("pwc", "wd3", "Global_Experienced_Careers", "PwC"),
    ("pwc", "wd3", "Global_Campus_Careers", "PwC"),
    # Sonde des cabinets du 2026-10-08 (site_final.flux_workday, identite
    # verifiee sur la vitrine). Environ 70 s par flux, lus 4 a la fois
    # (scan_workday). Les flux surtout americains (RSM, Crowe, Vanguard, State
    # Street...) restent a site_final.
    ("erm", "wd3", "erm_Careers", "ERM"),
    ("juliusbaer", "wd3", "External", "Julius Baer"),
    ("robeco", "wd3", "robecoExternalCareers", "Robeco"),
    ("morningstar", "wd5", "morningstar", "Morningstar"),
    ("lseg", "wd3", "Careers", "LSEG"),
    ("fticonsulting", "wd108", "fticonsultingCareers", "FTI Consulting"),
    ("alantra", "wd3", "alantra", "Alantra"),
    ("pjtpartners", "wd1", "Careers", "PJT Partners"),
    ("santander", "wd3", "santanderCareers", "Santander"),
    ("rabobank", "wd3", "Jobs", "Rabobank"),
    ("accenture", "wd103", "accentureCareers", "Accenture"),
    # Sites dont le nom ne se devine pas : testes un a un le 2026-10-08.
    # MMC = Marsh McLennan, donc aussi Oliver Wyman et Mercer.
    ("blackrock", "wd1", "BlackRock_Professional", "BlackRock"),
    ("db", "wd3", "DBWebsite", "Deutsche Bank"),
    ("barclays", "wd3", "External_Career_Site_Barclays", "Barclays"),
    ("mmc", "wd1", "MMC", "Marsh McLennan"),
    ("spgi", "wd5", "SPGI_Careers", "S&P Global"),
    ("abrdn", "wd3", "abrdn", "abrdn"),
    ("citi", "wd5", "2", "Citi"),
    ("invesco", "wd1", "IVZ", "Invesco"),
    ("pimco", "wd1", "pimco-careers", "PIMCO"),
    ("ntrs", "wd1", "northerntrust", "Northern Trust"),
    # Trouves par le lien « Carrieres » de leur site (2026-10-08).
    ("issgovernance", "wd1", "ISScareers", "ISS"),
    ("rothschildandco", "wd3", "Rothschildandco_Lateral", "Rothschild & Co"),
    ("vontobel", "wd3", "Vontobel_External_Career", "Vontobel"),
    ("cip", "wd103", "CIP_Careers", "Copenhagen Infrastructure Partners"),
    ("aviva", "wd1", "Aviva_Investors_External", "Aviva Investors"),
    ("mgpru", "wd3", "mandgprudential", "M&G"),
    # Deloitte France : lien de sa page « rejoindre », trouve par recherche web
    # « Deloitte carriere » — la page d'accueil ne le donnait pas (556 offres).
    ("fina", "wd103", "DeloitteRecrute", "Deloitte"),
    # International, sonde du 2026-10-08 (lien « Careers » de ~130 sites) :
    # Asie, Canada. Les flux surtout americains restent a site_final.
    ("dbs", "wd3", "DBS_Careers", "DBS"),
    ("aia", "wd3", "External", "AIA"),
    ("prudential", "wd3", "prudential", "Prudential / Eastspring"),
    ("hkex", "wd3", "HKEXCareerPage", "HKEX"),
    ("cdpq", "wd10", "CDPQ", "CDPQ"),
    ("otppb", "wd3", "OntarioTeachers_Careers", "Ontario Teachers' Pension Plan"),
    ("investpsp", "wd3", "PSP_Careers", "PSP Investments"),
    ("bci", "wd10", "BCI_Careers", "BCI"),
    ("td", "wd3", "TD_Bank_Careers", "TD"),
    ("desjardins", "wd10", "Desjardins", "Desjardins"),
    # Employeurs a fit >= 8 qui n'arrivaient que par LinkedIn (2026-10-08).
    ("onepoint", "wd3", "OnepointFR", "Onepoint"),
    ("bdf", "wd103", "recrutement-banque-de-France", "Banque de France"),
    ("ayvens", "wd3", "AyvensCareers", "Ayvens"),
    ("airliquidehr", "wd3", "AirLiquideExternalCareer", "Air Liquide"),
    # Vitrine en 403, flux Workday public trouve par le nom (2026-10-08).
    ("brookfield", "wd5", "brookfield", "Brookfield"),
    # Portails « JS seul » : le site vitrine renvoie a ces flux (2026-10-08)
    ("ocbc", "wd102", "External", "OCBC"),
    ("bis", "wd3", "External", "BRI (BIS)"),
]
# Court a dessein. Les 55 mots-cles de KEYWORDS viseraient LinkedIn, pas un flux
# d'entreprise ou l'on cherche un METIER dans un catalogue deja restreint.
WORKDAY_MOTS = [
    "ESG",
    "durable",
    "sustainability",
    "finance",
    "analyste",
    "analyst",
    "climat",
    "risque",
]
WORKDAY_PAGES = 2  # pages de 20 par mot-cle
WORKDAY_PAUSE = 0.6
WORKDAY_DETAILS = 25  # fiches detaillees par flux, au plus
WORKDAY_PARALLELE = 6  # flux lus en meme temps (un tenant = un site) ; 42 flux au 2026-10-08


def _workday_detail(httpx, base, tenant, site, chemin):
    """La fiche d'une offre : description, date reelle, pays, temps de travail."""
    try:
        r = _post_borne(
            httpx,
            f"{base}/wday/cxs/{tenant}/{site}{chemin}",
            timeout=15,
            headers={**UA, "Accept": "application/json"},
        )
        if r.status_code != 200:
            r = _get_borne(
                httpx,
                f"{base}/wday/cxs/{tenant}/{site}{chemin}",
                timeout=15,
                headers={**UA, "Accept": "application/json"},
            )
        if r.status_code != 200:
            return {}
        ji = (r.json() or {}).get("jobPostingInfo") or {}
    except Exception:
        return {}
    pays = (ji.get("country") or {}).get("descriptor") or ""
    return {
        "description": _strip_html(ji.get("jobDescription") or "")[:30000],
        "date": str(ji.get("startDate") or "")[:10],
        "location": ji.get("location") or "",
        "pays": pays,
        # « Full time » / « Part time » est un temps de travail, pas un contrat :
        # on ne le laisse pas remplir la colonne `contrat`, qui sert a filtrer.
        "temps": ji.get("timeType") or "",
    }


def fetch_workday(tenant, host, site, nom):
    """Les offres d'un flux Workday qui passent title_ok, descriptions comprises."""
    import httpx

    base = f"https://{tenant}.{host}.myworkdayjobs.com"
    vus, retenues = set(), []
    try:
        for mot in WORKDAY_MOTS:
            for page in range(WORKDAY_PAGES):
                r = _post_borne(
                    httpx,
                    f"{base}/wday/cxs/{tenant}/{site}/jobs",
                    json={"appliedFacets": {}, "limit": 20, "offset": page * 20, "searchText": mot},
                    timeout=20,
                    headers={
                        **UA,
                        "Accept": "application/json",
                        "Content-Type": "application/json",
                    },
                )
                if r.status_code != 200:
                    INCIDENTS[f"workday:{tenant}"][f"HTTP {r.status_code}"] += 1
                    break
                postes = (r.json() or {}).get("jobPostings") or []
                if not postes:
                    break
                for j in postes:
                    chemin = j.get("externalPath") or ""
                    if not chemin or chemin in vus:
                        continue
                    vus.add(chemin)
                    titre = (j.get("title") or "").strip()
                    if titre and title_ok(titre):
                        retenues.append((titre, chemin, j.get("locationsText") or ""))
                time.sleep(WORKDAY_PAUSE)
    except Exception as e:
        INCIDENTS[f"workday:{tenant}"][type(e).__name__] += 1

    out = []
    for titre, chemin, lieu in retenues[:WORKDAY_DETAILS]:
        d = _workday_detail(httpx, base, tenant, site, chemin)
        # Le PAYS est servi en clair par l'API. C'est plus sur que de deviner
        # depuis un nom de ville, et en_france() sait lire « France ».
        lieu_final = ", ".join(x for x in (d.get("location") or lieu, d.get("pays")) if x)
        o = _mk(
            titre,
            f"{base}/{site}{chemin}",
            nom,
            lieu_final,
            d.get("date", ""),
            f"workday:{tenant}",
            d.get("description", ""),
        )
        out.append(o)
        time.sleep(WORKDAY_PAUSE)
    # Les offres sans fiche detaillee entrent quand meme : le titre et le lien
    # suffisent a les faire exister, l'auto-enrichissement fera le reste.
    for titre, chemin, lieu in retenues[WORKDAY_DETAILS:]:
        out.append(_mk(titre, f"{base}/{site}{chemin}", nom, lieu, "", f"workday:{tenant}"))
    return [o for o in out if o["titre"] and o["url"]]


def scan_workday():
    """Les flux en parallele, WORKDAY_PARALLELE a la fois. Chaque tenant est un
    site distinct : la pause par flux tient toujours, aucun n'est sollicite plus
    vite qu'avant. En serie, 27 flux a ~70 s depassaient le plafond de 30 min
    de la passe 1a (2026-10-08)."""
    import concurrent.futures as cf

    offres = []
    with cf.ThreadPoolExecutor(max_workers=WORKDAY_PARALLELE) as ex:
        futs = [(f[0], ex.submit(fetch_workday, *f)) for f in WORKDAY_FLUX]
        for tenant, fut in futs:
            got = fut.result()
            print(f"  ✓ workday:{tenant} → {len(got)} offres retenues")
            offres.extend(got)
    return offres


# ═══════════════ 2. LinkedIn recherche PUBLIQUE (guest, httpx, paginé) ═══════════════
_LI_CARD = re.compile(
    r'<a[^>]+class="[^"]*base-card__full-link[^"]*"[^>]+href="([^"]+)"[^>]*>.*?'
    r'<span class="sr-only">\s*(.*?)\s*</span>',
    re.S,
)
_LI_COMP = re.compile(r"base-search-card__subtitle[^>]*>.*?>([^<]+)<", re.S)
_LI_LOC = re.compile(r"job-search-card__location[^>]*>([^<]+)<", re.S)


def linkedin_guest_search(keyword, pages=2, days=7, lieu="France"):
    """API guest LinkedIn (HTML fragments, AUCUN login, lecture publique).
    Pagination par start=0,25,50… f_TPR filtre fraîcheur (604800s=7j).

    `lieu` etait code en dur sur « France ». Desactiver le filtre geographique
    a l'entree de la file ne servait donc a rien pour cette source : elle ne
    DEMANDAIT que des offres francaises. Un filtre en aval ne peut pas rattraper
    ce qu'une requete en amont n'a jamais demande."""
    import httpx, html as _html

    out = []
    for p in range(pages):
        if _LI["stop"]:
            return out
        url = (
            "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
            f"?keywords={quote(keyword)}&location={quote(lieu)}"
            f"&f_TPR=r{days * 86400}&start={p * 25}"
        )
        try:
            r = _get_borne(httpx, url, timeout=15, headers=UA)
            # Une limite de debit s'ATTEND : meme page, apres la pause.
            while r.status_code == 429:
                INCIDENTS["linkedin_http"][429] += 1
                if not _li_pause_429(r):
                    _LI["stop"] = "429"
                    return out
                r = _get_borne(httpx, url, timeout=15, headers=UA)
            _LI["suite_429"] = 0
            if r.status_code in (403, 999):
                # Un REFUS s'arrete : plus aucune requete LinkedIn de la collecte.
                INCIDENTS["linkedin_http"][r.status_code] += 1
                _LI["stop"] = str(r.status_code)
                return out
            if r.status_code != 200:
                # UN REFUS N'EST PAS UNE ABSENCE D'OFFRES. `break` muet rendait
                # une liste vide indistinguable de « rien de neuf cette
                # semaine » — sur la source qui fournit les deux tiers de la
                # file. Un scan entierement bride affichait « 0 offres » et
                # passait pour une journee calme. On compte, et main() le dit.
                INCIDENTS["linkedin_http"][r.status_code] += 1
                break
            blocks = r.text.split("base-card")  # 1 carte par bloc
            for b in blocks:
                mu = re.search(r'href="(https://[a-z]+\.linkedin\.com/jobs/view/[^"?]+)', b)
                mt = re.search(r'<span class="sr-only">\s*([^<]+?)\s*</span>', b)
                if not (mu and mt):
                    continue
                comp = _LI_COMP.search(b)
                loc = _LI_LOC.search(b)
                titre = _html.unescape(mt.group(1)).strip()
                if title_ok(titre):
                    out.append(
                        _mk(
                            titre,
                            mu.group(1),
                            _html.unescape(comp.group(1)).strip() if comp else "LinkedIn",
                            _html.unescape(loc.group(1)).strip() if loc else "",
                            "",
                            f"linkedin-search:{keyword}",
                        )
                    )
        except Exception as e:
            INCIDENTS["linkedin_reseau"][type(e).__name__] += 1
            break
        _dormir(LI_PAUSE)  # poli : espace les pages
    return out


# LIMITE DE DEBIT LINKEDIN. Mesure du 2026-10-17 : a 1,2 s entre pages, l'API
# invite repond 429 des la premiere poignee de requetes — 13 mots-cles sur 14
# coupes en 32 s. Le code faisait `break` : page perdue, mot-cle suivant, 429 a
# nouveau. Du 13 au 16/10, la collecte LinkedIn est tombee de 200-640 offres
# par jour a 0-28, sans rien de visible hors du compteur d'incidents.
# Regle du projet : un 429 dit « reviens plus tard » — on espace davantage, on
# attend (Retry-After, sinon 60 s doublees jusqu'a 240), on reprend la MEME
# page. 403/999 sont des refus : arret immediat, aucune reprise.
#
# DUREE MAXIMALE DE LA PASSE, pas budget d'attente. Mesure du 17/10 avec un
# budget de 900 s d'attente : 184 offres (101 neuves) au lieu de 96, mais
# arret a 10 mots-cles sur 14, France seule — « Worldwide » n'aurait rien eu.
# La passe LinkedIn du pipeline est tuee a 3600 s, et une passe tuee perd TOUTE
# sa collecte (fusion en fin de passe) : on s'arrete proprement a 45 min.
LI_PAUSE = 3.0
LI_ATTENTES = (60, 120, 240)
LI_DUREE_MAX = 2700
_LI = {"stop": None, "attendu": 0.0, "suite_429": 0, "debut": 0.0}
_dormir = time.sleep  # les tests le remplacent
_horloge = time.monotonic  # idem


def _li_ecoule():
    return _horloge() - _LI["debut"]


def _li_pause_429(r):
    """Attend avant de redemander apres un 429. False si la passe n'a plus le temps."""
    ra = (getattr(r, "headers", None) or {}).get("Retry-After", "")
    n = _LI["suite_429"]
    pause = int(ra) if str(ra).isdigit() else LI_ATTENTES[min(n, len(LI_ATTENTES) - 1)]
    pause = min(pause, max(LI_ATTENTES))
    if _li_ecoule() + pause > LI_DUREE_MAX:
        return False
    print(f"  ⏳ linkedin : limite de débit (429), pause {pause} s puis reprise")
    _dormir(pause)
    _LI["attendu"] += pause
    _LI["suite_429"] = n + 1
    return True


# POURQUOI PLUS DE LISTE DE PAYS. Le critere n'est pas le pays, c'est la
# langue que l'annonce demande — et un pays ne la dit pas. Mesure du
# 2026-09-22 : la recherche publique LinkedIn accepte le lieu « Worldwide », et
# elle pagine en profondeur.
#
#   lieu=""            -> retombe sur les ETATS-UNIS (Oxnard, Indianapolis…)
#   lieu="Worldwide"   ->  2 pages : 17 offres, 12 pays
#                         10 pages : 78 offres, 37 pays
#
# Enumerer seize pays coutait 1 760 requetes pour seize pays. « Worldwide » en
# profondeur en coute 550 pour trente-sept et plus. Strictement meilleur.
#
# La France reste interrogee a part : c'est la que l'utilisateur vit, et une requete
# mondiale y noie les offres locales sous le volume indien et americain.
#
# Le dictionnaire donne la PROFONDEUR par lieu. Une liste simple reste acceptee
# et utilise alors la profondeur passee en argument.
LIEUX_MONDE = {"France": 3, "Worldwide": 12}


def scan_linkedin(pages=2, days=7, lieux=None):
    """days = fenetre de fraicheur LinkedIn (f_TPR). Le defaut de 7 jours suffit
    au scan quotidien, mais il rend invisibles les offres plus anciennes jamais
    captees : passer --days 31 pour rattraper un mois entier.

    `lieux` : les zones interrogees. En recherche mondiale on ne peut pas se
    contenter de retirer le filtre d'entree — il faut DEMANDER les autres pays.
    """
    if lieux is None:
        lieux = LIEUX_MONDE if MONDE else ["France"]
    # Un dict donne la profondeur par lieu, une liste garde celle de l'argument.
    profondeur = dict(lieux) if isinstance(lieux, dict) else {x: pages for x in lieux}
    offers, seen = [], set()
    _LI.update(stop=None, attendu=0.0, suite_429=0, debut=_horloge())
    for lieu in profondeur:
        n_lieu = 0
        for kw in KEYWORDS:
            if not _LI["stop"] and _li_ecoule() >= LI_DUREE_MAX:
                _LI["stop"] = "durée"
            if _LI["stop"]:
                break
            got = linkedin_guest_search(kw, pages=profondeur[lieu], days=days, lieu=lieu)
            new = [o for o in got if o["url"] not in seen]
            seen.update(o["url"] for o in new)
            n_lieu += len(new)
            if new and len(profondeur) == 1:
                print(f"  ✓ linkedin «{kw}» → {len(new)} offres")
            offers.extend(new)
        if len(profondeur) > 1:
            print(f"  ✓ linkedin {lieu} → {n_lieu} offres")
    if _LI["stop"] in ("429", "durée"):
        print(
            f"  ⚠ linkedin : durée maximale atteinte ({_li_ecoule():.0f} s, dont "
            f"{_LI['attendu']:.0f} s d'attente sur 429) — la suite à la prochaine collecte"
        )
    elif _LI["stop"]:
        print(f"  ⚠ linkedin : refus HTTP {_LI['stop']}, collecte LinkedIn arrêtée")
    return offers


# ═══════════════ 3. Welcome to the Jungle — sitemap public ═══════════════
_WTJ_JS = r"""
() => {
  const out=[]; const seen=new Set();
  document.querySelectorAll('a[href*="/fr/companies/"][href*="/jobs/"]').forEach(a=>{
    const t=(a.innerText||'').trim().split('\n')[0];
    if(!t||t.length<6||seen.has(a.href))return;
    seen.add(a.href);
    const card=a.closest('li,article,[class*="card"]')||a.parentElement;
    const txt=(card?card.innerText:'').split('\n').map(s=>s.trim()).filter(Boolean);
    out.push({title:t,url:a.href,company:txt[1]||'',location:txt.find(s=>/paris|lyon|bordeaux|remote|télétravail|france/i.test(s))||''});
  });
  return out;
}"""


def _wtj_429(pg):
    """WTJ nous bride-t-il ? Lisible MEME quand la navigation a echoue : la page
    d'erreur porte « Too Many Requests » alors que robust_goto rend ok=False."""
    try:
        return "too many requests" in pg.evaluate("document.body.innerText.slice(0,200)").lower()
    except Exception:
        return False


WTJ_SITEMAP = "https://www.welcometothejungle.com/sitemaps/index.xml.gz"
# Mesure : le challenge CloudFront de WTJ tombe apres ~3 minutes (202, 202, 200
# a 60 s d'intervalle). Attendre rapporte donc quelques fiches de plus par
# passe ; s'arreter au premier 202 en rendait zero.
WTJ_REPOS = 200  # secondes d'attente quand le mur tombe
WTJ_PATIENCE = 2  # nombre maximum d'attentes par passe
# 2 et non plus 6 (2026-10-02) : six attentes de 200 s faisaient 20 min d'immobilite
# dans une passe bornee a 60, pour un mur qui retombait aussitot la plupart du temps.


def _wtj_fiche(url, client):
    """JobPosting d'une fiche WTJ, ou None. Meme balisage que eFinancialCareers :
    un <script type="application/ld+json"> destine a Google.

    Leve `Bloque` sur 202/429 : c'est le challenge anti-bot de CloudFront, il
    vaut pour l'IP entiere et insister ne sert a rien. Surtout, 202 est un code
    de SUCCES — le confondre avec une page vide ferait passer le mur pour une
    fiche sans description."""
    from wtj_desc import UA as _WUA, Bloque

    try:
        r = _get_borne(client, url, headers=_WUA, timeout=30)
    except Exception:
        return None
    if r.status_code in (202, 429):
        raise Bloque(r.status_code)
    if r.status_code != 200:
        return None
    for bloc in re.findall(
        r'<script type="application/ld\+json"[^>]*>(.*?)</script>', r.text, re.S
    ):
        try:
            o = json.loads(bloc)
        except Exception:
            continue
        if isinstance(o, dict) and o.get("@type") == "JobPosting":
            return o
    return None


def scan_wtj(pages=2):
    """Offres Welcome to the Jungle, via le SITEMAP declare dans robots.txt.

    L'ANCIENNE VERSION VISAIT UNE ROUTE INTERDITE, ET MORTE. Elle construisait
    des URL `/fr/jobs?query=<mots>`. Or le robots.txt de WTJ porte, noir sur
    blanc :

        disallow: */jobs?query=*
        Disallow: /*?

    C'est exactement ce qu'on demandait. Et depuis, WTJ a retire la recherche
    libre : `/fr/jobs?query=…` ignore le parametre et sert une page de
    presentation de leur produit « matching », la vraie recherche etant passee
    derriere une authentification (`/fr/authenticate/signin?redirect=/fr/jobs`).
    Le scan ne pouvait donc plus rien rendre — d'ou les 429 a repetition et les
    « 0 offre » silencieux.

    LA VOIE OUVERTE. Le meme robots.txt declare un sitemap :
        Sitemap: https://www.welcometothejungle.com/sitemaps/index.xml.gz
    Neuf fichiers `job-listings.N.xml.gz`, 88 000 annonces, 60 000 en francais.
    Les pages `/fr/companies/<slug>/jobs/<slug>` ne sont interdites nulle part.

    LE DEBIT RESTE BRIDE. Apres quelques fiches, CloudFront bascule l'IP sur un
    challenge et repond 202 avec un corps vide (voir wtj_desc.py, meme mur). On
    lit donc peu de fiches par passe, on s'arrete des le premier 202, et on
    garde ce qui est lu. `pages` est conserve pour la compatibilite des
    appelants et sert de plafond : pages * 5 fiches.
    """
    import httpx
    import gzip
    from wtj_desc import Bloque, UA as _WUA

    _EX = contrats_exclus()
    offers = []

    def _lire(client, url):
        r = _get_borne(client, url, headers=_WUA, timeout=90)
        if r.status_code != 200:
            return ""
        b = r.content
        if b[:2] == b"\x1f\x8b":
            b = gzip.decompress(b)
        return b.decode("utf-8", "replace")

    with httpx.Client(follow_redirects=True) as client:
        try:
            idx = _lire(client, WTJ_SITEMAP)
        except Exception as e:
            print(f"  ~ WTJ : sitemap injoignable ({type(e).__name__})")
            return offers
        fichiers = [l for l in re.findall(r"<loc>([^<]+)</loc>", idx) if "job-listings" in l]
        if not fichiers:
            print("  ~ WTJ : aucun sitemap d'offres dans l'index")
            return offers

        cibles = []
        for f in fichiers:
            try:
                t = _lire(client, f)
            except Exception:
                continue
            for l in re.findall(r"<loc>([^<]+)</loc>", t):
                if "/fr/companies/" not in l or "/jobs/" not in l:
                    continue
                # Le slug porte l'intitule, en minuscules et sans accents : il
                # sert au PRE-FILTRE. Le vrai titre vient du ld+json de la fiche.
                approx = l.split("/jobs/")[-1].replace("-", " ")
                if contrat_du_titre(approx) in _EX:
                    continue
                if _RX_EFC_ESG.search(approx):
                    cibles.append(l)

        # On ne relit pas ce qui est deja en file : chaque fiche coute une
        # requete sur un debit tres limite.
        import queue_io

        connues = {
            _norm_url(x.get("url"))
            for x in queue_io.charger(QUEUE, descriptions=False)
            if x.get("url")
        }
        neuves = [u for u in cibles if _norm_url(u) not in connues]
        plafond = max(1, pages) * 5
        print(
            f"  WTJ : {len(cibles)} offres ESG au sitemap, {len(neuves)} nouvelles "
            f"— {min(len(neuves), plafond)} lue(s) cette passe (le reste au prochain scan)"
        )

        # PATIENCE. Le mur de WTJ n'est pas definitif : mesure a la seconde, il
        # tombe apres ~3 minutes. S'arreter au premier 202 rendait 0 offre a
        # chaque passe alors qu'attendre en donne quelques-unes de plus. On
        # attend donc, un nombre limite de fois, et on rend la main ensuite.
        # Ce n'est pas un contournement : on ralentit, on ne force rien.
        etat = {"attentes": 0}

        def _fiche_patiente(url):
            """JobPosting, ou None si WTJ nous ferme la porte pour de bon.

            Rend None UNIQUEMENT quand la patience est epuisee : l'appelant sait
            alors qu'il doit arreter la source, pas seulement sauter une fiche.
            """
            while True:
                try:
                    return _wtj_fiche(url, client) or {}
                except Bloque as e:
                    if etat["attentes"] >= WTJ_PATIENCE:
                        print(f"  ~ {e} — arret WTJ apres {etat['attentes']} attente(s).")
                        return None
                    etat["attentes"] += 1
                    print(f"  ~ {e} — pause {WTJ_REPOS} s ({etat['attentes']}/{WTJ_PATIENCE})…")
                    time.sleep(WTJ_REPOS)

        for u in neuves[:plafond]:
            jp = _fiche_patiente(u)
            if jp is None:  # mur durable : on rend la main
                break
            if not jp:  # fiche illisible : on passe a la suivante
                continue
            # UNE SEULE REQUETE PAR OFFRE. La description et l'intitule vivent
            # dans le MEME bloc ld+json : les chercher par deux appels separes
            # doublait la consommation d'un quota deja minuscule — le mur
            # tombait deux fois plus vite, pour rien.
            d = _strip_html(str(jp.get("description") or ""))
            if len(d) < 200:
                continue
            titre = str(jp.get("title") or "").strip()
            lieu = _efc_lieu(jp)
            if not titre or not title_ok(titre) or contrat_du_titre(titre) in _EX:
                continue
            if not en_france(lieu):
                continue
            soc = (jp.get("hiringOrganization") or {}).get("name") or "Welcome to the Jungle"
            offers.append(
                _mk(titre, u, soc, lieu, str(jp.get("datePosted") or "")[:10], "wtj-sitemap", d)
            )
    print(f"  \u2713 Welcome to the Jungle \u2192 {len(offers)} offres (avec description)")
    return offers


# ═══════════════ 8. eFinancialCareers — sitemap PUBLIC declare dans robots.txt ═══
# POURQUOI. Site d'emploi 100 % finance, francais, exactement le marche de l'utilisateur.
# Il etait deja connu de _SITES_EMPLOI (rang 2) mais JAMAIS scanne : les 5 entrees
# de la file etaient des pages de categorie ramassees ailleurs, sans description.
#
# CE QUE robots.txt AUTORISE (verifie le 2026-09-04). `/search` est interdit a
# `User-agent: *` — on n'y touche pas. En revanche le fichier DECLARE lui-meme
# le sitemap des offres recentes :
#     Sitemap: https://www.efinancialcareers.fr/sitemap-secure/latestjobs/xml
# C'est la voie d'acces que le site publie pour etre indexe : 8100 offres, et
# les pages d'offres ne sont pas interdites. `crawl-delay: 10` est respecte.
#
# Chaque fiche porte un <script type="application/ld+json"> de type JobPosting
# avec intitule, societe, lieu, date et description complete (~10 000 car.).
EFC_SITEMAP = "https://www.efinancialcareers.fr/sitemap-secure/latestjobs/xml"
EFC_DELAI = 10  # crawl-delay annonce par robots.txt — ne pas baisser
# LES AUTRES SITES DU MEME EDITEUR (verifie le 2026-09-24) : meme robots.txt,
# meme sitemap declare, meme crawl-delay 10, meme ld+json. 48 000 offres de
# plus, dont 93 intitules ESG absents de la file. Seul le .fr etait lu.
EFC_SITES = ("fr", "com", "co.uk", "de", "ch", "nl", "lu", "ie", "sg")


def _efc_sitemap(site):
    return f"https://www.efinancialcareers.{site}/sitemap-secure/latestjobs/xml"


EFC_UA = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    )
}

# Les URL ont la forme /emploi-<Pays>-<Ville>-<Titre>.id<N>. La ville peut
# contenir des tirets (« Levallois-Perret »), donc on ne cherche PAS a la
# separer du titre : decouper au premier tiret donnait ville « Levallois » et
# titre « Perret-Responsable Projets IA ». Le bloc ville+titre sert seulement au
# PRE-FILTRE ; les champs exacts viennent du ld+json de la fiche.
_RX_EFC_SLUG = re.compile(r"/(?:emploi|jobs)-[^-]+-(.+)\.id(\d+)$")

# Filtre ESG strict. `responsab` a ete retire apres mesure : il faisait entrer
# 581 titres dont la quasi-totalite etaient des « Responsable … » sans rapport.
#
# Les \b sont INDISPENSABLES : sans eux « RSE » matche n'importe quel mot qui
# contient ces trois lettres. Meme famille de bug que _TITRE_CONTRAT et
# _RX_STAGE, ou un \b perdu a l'ecriture avait rendu le motif inoperant.
# « climat » exclut explicitement « climatisation » : deux postes de technicien
# de zone Climatisation etaient remontes a la mesure.
_RX_EFC_ESG = re.compile(
    r"\bESG\b|\bRSE\b|\bSFDR\b|\bCSRD\b|extra.?financi|durabilit"
    r"|d[ée]veloppement durable|sustainab|climat(?!isation)|carbone|taxonomie"
    r"|impact invest|finance verte|green finance|transition [ée]nerg"
    r"|stewardship|responsible invest|net.zero|biodiversit",
    re.I,
)


# Programmes jeunes diplomes.
_RX_EFC_GRAD = re.compile(
    r"\bgraduate\b|jeune[s]? dipl|\bearly career\b|trainee program"
    r"|young (?:graduate|talent)",
    re.I,
)
# Le V.I.E se cherche SANS re.I, et c'est indispensable : « vie » insensible a
# la casse fait entrer toute l'assurance vie, qui pese lourd sur un site
# finance (« Gestionnaire Assurance Vie », « Middle office Assurance Vie »…).
# En majuscules, l'acronyme ne se confond avec rien.
_RX_EFC_VIE = re.compile(r"\bV\.?I\.?E\b")


def _est_graduate(titre):
    """Programme jeune diplome ou V.I.E ?"""
    return bool(_RX_EFC_GRAD.search(titre) or _RX_EFC_VIE.search(titre))


# ── LE FILTRE PAR METIER, et pourquoi pas par secteur ──────────────────────
#
# eFinancialCareers EST le site d'emploi de la banque et de la gestion
# d'actifs : 8478 offres au sitemap, dont 32 seulement etaient en file. C'est
# de loin la plus grosse source non exploitee, et elle est sanctionnee
# (sitemap declare, crawl-delay 10 s).
#
# Premier essai : filtrer par SECTEUR. Echec — le slug du sitemap ne porte que
# l'intitule, pas l'employeur. « power » y trouvait « Power Platform »,
# « energie » y trouvait « Consultant transformation numerique Energie ». On
# remontait des missions de conseil, pas des postes chez un energeticien.
#
# On filtre donc sur le METIER de l'utilisateur. Mesure du 17/09 sur les 8478 :
#   7208 hors metier, 217 contrat exclu, 184 trop senior, 869 A LIRE.
#
# 869 fiches a 10 s font 144 minutes. Inutile de tenir un index de rotation :
# scan_efc ecarte deja les URL presentes en file, donc chaque passe avance
# d'elle-meme dans le reste.
_RX_EFC_METIER = re.compile(
    r"analyst|analyste|contr[oô]le de gestion|controlling|FP&A"
    r"|gestion de portefeuille|g[eé]rant|risk|risque|cr[eé]dit|credit"
    r"|valoris|valuation|M&A|corporate finance|private equity"
    r"|\bESG\b|\bISR\b|\bRSE\b|extra.?financ|durab|climat(?!isation)|carbon"
    r"|\bCSRD\b|\bSFDR\b|graduate|jeune dipl|junior|reporting",
    re.I,
)

# Postes hors de portee d'un profil sorti d'ecole. Les ecarter AVANT de payer
# 10 s de lecture : c'est le tri le moins cher qu'on puisse faire.
_RX_EFC_SENIOR = re.compile(
    r"senior|directeur|director|head of|responsable|manager|principal"
    r"|associate director|\bVP\b|expert|chef de",
    re.I,
)


def _est_metier(titre):
    """Intitule compatible avec le profil, et pas deja trop senior ?"""
    return bool(_RX_EFC_METIER.search(titre)) and not _RX_EFC_SENIOR.search(titre)


def _efc_urls(client, site="fr"):
    """(url, titre approximatif) de chaque offre du sitemap. Une seule requete."""
    r = _get_borne(client, _efc_sitemap(site), headers=EFC_UA, timeout=60)
    if r.status_code != 200:
        print(f"  ~ eFC .{site} : sitemap injoignable (statut {r.status_code})")
        INCIDENTS[f"efc:{site}"][f"HTTP {r.status_code}"] += 1
        return []
    out = []
    for loc in re.findall(r"<loc>([^<]+)</loc>", r.text):
        m = _RX_EFC_SLUG.search(loc)
        if m:
            out.append((loc, unquote(m.group(1)).replace("_", " ").strip()))
    return out


def _efc_fiche(url, client):
    """JobPosting de la fiche, ou None. Ne leve jamais."""
    try:
        r = _get_borne(client, url, headers=EFC_UA, timeout=30)
    except Exception:
        return None
    if r.status_code != 200:
        return None
    for bloc in re.findall(
        r'<script type="application/ld\+json"[^>]*>(.*?)</script>', r.text, re.S
    ):
        try:
            o = json.loads(bloc)
        except Exception:
            continue
        if isinstance(o, dict) and o.get("@type") == "JobPosting":
            return o
    return None


def _efc_lieu(jp):
    """Ville du JobPosting. jobLocation peut etre un objet ou une liste."""
    loc = jp.get("jobLocation")
    if isinstance(loc, list):
        loc = loc[0] if loc else None
    if not isinstance(loc, dict):
        return ""
    ad = loc.get("address") or {}
    return " ".join(
        str(ad.get(k) or "") for k in ("addressLocality", "addressRegion", "addressCountry")
    ).strip()


def scan_efc(limit=40, filtre="esg", sites=("fr",)):
    """Offres eFinancialCareers, description comprise.

    filtre :
      "esg"      — intitules qui parlent d'ESG (43 sur 8100) ;
      "graduate" — programmes jeunes diplomes et V.I.E ;
      "metier"   — les intitules compatibles avec le profil, seniors ecartes :
                   869 sur 8478 a la mesure du 17/09. C'est le gisement des
                   banques et de la gestion d'actifs, eFC etant leur site
                   d'emploi. Chaque passe avance dans le reste, les URL deja
                   en file etant ecartees ;
      "tout"     — tout ce que title_ok retient, soit ~2400 titres : a 10 s la
                   fiche c'est presque 7 h, pour un fit calcule sur des postes
                   bancaires generiques.
    """
    import httpx

    _EX = contrats_exclus()
    offers = []
    with httpx.Client(follow_redirects=True) as client:
        # Une offre publiee sur deux sites porte le meme identifiant : on ne la
        # lit qu'une fois.
        toutes, ids = [], set()
        for i, site in enumerate(sites):
            if i:
                time.sleep(EFC_DELAI)  # crawl-delay, sitemaps compris
            for url, approx in _efc_urls(client, site):
                m = _RX_EFC_SLUG.search(url)
                if m and m.group(2) in ids:
                    continue
                if m:
                    ids.add(m.group(2))
                toutes.append((url, approx))
        cibles = []
        for url, approx in toutes:
            if contrat_du_titre(approx) in _EX:
                continue
            if filtre == "esg":
                if not _RX_EFC_ESG.search(approx):
                    continue
            elif filtre == "graduate":
                if not _est_graduate(approx):
                    continue
            elif filtre == "metier":
                if not _est_metier(approx):
                    continue
            elif not title_ok(approx):
                continue
            cibles.append(url)
        # Fiches DEJA en file : ne pas les relire. A 10 s chacune, une seconde
        # passe repayait tout le temps de la premiere pour n'apporter que ce que
        # merge_into_queue aurait de toute facon deduplique.
        import queue_io

        connues = {_norm_url(x.get("url")) for x in queue_io.charger(QUEUE) if x.get("url")}
        neuves = [u for u in cibles if _norm_url(u) not in connues]
        deja = len(cibles) - len(neuves)
        # A TOUR DE ROLE entre les sites. Pris dans l'ordre des sitemaps, les
        # `limit` places allaient toutes au .fr, lu en premier : a l'essai, 8
        # fiches sur 8 etaient parisiennes et l'etranger n'etait jamais atteint.
        par_site = {}
        for u in neuves:
            par_site.setdefault(urlparse(u).netloc, []).append(u)
        alterne = []
        while any(par_site.values()):
            for lst in par_site.values():
                if lst:
                    alterne.append(lst.pop(0))
        cibles = alterne[:limit]
        print(
            f"  eFC : {len(toutes)} offres au sitemap → {len(cibles)} a lire "
            f"({deja} deja en file) "
            f"({EFC_DELAI} s entre chaque, {len(cibles) * EFC_DELAI // 60} min)"
        )
        for n, url in enumerate(cibles, 1):
            if n > 1:
                time.sleep(EFC_DELAI)  # crawl-delay: 10
            jp = _efc_fiche(url, client)
            if not jp:
                continue
            # Le ld+json porte des entites HTML dans le titre : sans unescape,
            # « Originateur &laquo; Sustainable banking » finissait tel quel dans
            # l'objet de la lettre. _strip_html ne s'applique qu'a la description.
            titre = __import__("html").unescape(str(jp.get("title") or ""))
            # eFC suffixe le titre du lieu et du mode de travail :
            # « … | Paris, FR | Hybride ». On ne garde que l'intitule.
            titre = re.sub(r"\s*\|.*$", "", titre).strip()
            lieu = _efc_lieu(jp)
            # Le titre exact du ld+json est plus fiable que le slug : on refait
            # les deux filtres dessus avant de garder l'offre.
            if not titre or not title_ok(titre) or contrat_du_titre(titre) in _EX:
                continue
            if not en_france(lieu):
                continue
            soc = (jp.get("hiringOrganization") or {}).get("name") or "eFinancialCareers"
            offers.append(
                _mk(
                    titre,
                    url,
                    soc,
                    lieu,
                    str(jp.get("datePosted") or "")[:10],
                    "efinancialcareers",
                    _strip_html(str(jp.get("description") or "")),
                )
            )
            if n % 10 == 0:
                print(f"    … {n}/{len(cibles)} ({len(offers)} retenues)")
    print(f"  ✓ eFinancialCareers → {len(offers)} offres (avec description)")
    return offers


# ═══════════════ 9. EURES — le portail d'emploi OFFICIEL de l'Union europeenne ═══
# POURQUOI. 96 % des offres etrangeres de la file venaient de la seule recherche
# LinkedIn « Worldwide », plafonnee a 12 pages par mot-cle et noyee sous le
# volume indien et americain. EURES agrege les services publics de l'emploi des
# 30 pays de l'EEE, description comprise, en JSON.
#
# CE QUI EST AUTORISE (verifie le 2026-09-24). robots.txt de europa.eu ne ferme
# ni /eures/api/ ni /eures/portal/, et declare `crawl-delay: 10`, respecte ici.
# L'API est celle que le portail public appelle lui-meme, sans authentification.
#
# PIEGE : la recherche est LARGE. « ESG analyst » rend 255 000 resultats sur une
# semaine : le mot-cle est cherche dans la description, et les « ESG » des
# achats industriels allemands remontent. Le classement BEST_MATCH met les bons
# en tete ; on ne lit donc qu'une page par mot-cle, et l'intitule doit passer
# le filtre metier d'eFC (analyste, risque, ESG… et pas senior).
EURES_URL = "https://europa.eu/eures/api/jv-searchengine/public/jv-search/search"
EURES_FICHE = "https://europa.eu/eures/portal/jv-se/jv-details/{}?lang=en"
EURES_DELAI = 10  # crawl-delay de europa.eu — ne pas baisser
EURES_MOTS = [
    "ESG analyst",
    "sustainable finance",
    "sustainability analyst",
    "climate risk analyst",
    "green bonds",
    "impact investing",
    "responsible investment",
    "graduate programme sustainability",
]
# Codes pays EURES -> nom anglais, que zones.py reconnait.
_EURES_PAYS = {
    "AT": "Austria",
    "BE": "Belgium",
    "BG": "Bulgaria",
    "HR": "Croatia",
    "CY": "Cyprus",
    "CZ": "Czech Republic",
    "DK": "Denmark",
    "EE": "Estonia",
    "FI": "Finland",
    "FR": "France",
    "DE": "Germany",
    "GR": "Greece",
    "EL": "Greece",
    "HU": "Hungary",
    "IS": "Iceland",
    "IE": "Ireland",
    "IT": "Italy",
    "LV": "Latvia",
    "LI": "Liechtenstein",
    "LT": "Lithuania",
    "LU": "Luxembourg",
    "MT": "Malta",
    "NL": "Netherlands",
    "NO": "Norway",
    "PL": "Poland",
    "PT": "Portugal",
    "RO": "Romania",
    "SK": "Slovakia",
    "SI": "Slovenia",
    "ES": "Spain",
    "SE": "Sweden",
    "CH": "Switzerland",
}
# En allemand, « ESG » est aussi le verre de securite (Einscheiben-
# Sicherheitsglas) : « Produktionsmitarbeiter ESG-Herstellung » remontait.
_RX_EURES_VERRE = re.compile(r"\bESG-?(?:fertigung|herstellung|glas)|einscheiben", re.I)
# Metiers hors cible que « sustainability » fait remonter chez EURES — achats,
# ingenierie, commerce, HSE, direction — mesures le 2026-09-24. fit_score les
# note 9 ou 10 (le mot suffit a lever le plafond ESG) : il faut donc les
# ecarter ICI, un filtre sur le fit ne les retiendrait pas.
_RX_EURES_HORS = re.compile(
    r"procurement|einkauf|beschaffung|engineer|ingenieur|vertrieb|\bsales\b"
    r"|leiter|leitung|\blead\b|\bhse\b|\bqhse\b|athlete|bioeng|produktion"
    r"|circular economy",
    re.I,
)
# Employeur masque par l'annonceur : on ne l'invente pas.
_RX_EURES_ANONYME = re.compile(
    r"siehe beschreibung|confidential|non renseign|not specified|anonym|see description"
    r"|voir (?:la )?description|^\W*$",
    re.I,
)


def _eures_corps(mot, page, par_page):
    return {
        "resultsPerPage": par_page,
        "page": page,
        "sortSearch": "BEST_MATCH",
        "keywords": [{"keyword": mot, "specificSearchCode": "EVERYWHERE"}],
        "publicationPeriod": "LAST_WEEK",
        "occupationUris": [],
        "skillUris": [],
        "requiredExperienceCodes": [],
        "positionScheduleCodes": [],
        "sectorCodes": [],
        "educationAndQualificationLevelCodes": [],
        "positionOfferingCodes": [],
        "locationCodes": [],
        "euresFlagCodes": [],
        "otherBenefitsCodes": [],
        "requiredLanguages": [],
        "minNumberPost": None,
        "sessionId": "jobhunter",
    }


def _eures_offre(j, _EX):
    """Une annonce EURES -> offre, ou None si l'intitule ne convient pas."""
    titre = __import__("html").unescape(str(j.get("title") or "")).strip()
    # FILTRE STRICT, mesure le 2026-09-24. Avec le seul filtre metier d'eFC,
    # 55 des 61 offres retenues etaient des « Data Analyst » ou « Business
    # Analyst » allemands generiques, notees 1 ou 2 : le mot-cle est cherche
    # dans la DESCRIPTION. On exige donc que l'INTITULE parle d'ESG ou de
    # durabilite, ou qu'il s'agisse d'un programme jeunes diplomes.
    if not titre or not title_ok(titre) or _RX_EFC_SENIOR.search(titre):
        return None
    if not (_RX_EFC_ESG.search(titre) or _est_graduate(titre)) or _RX_EURES_VERRE.search(titre):
        return None
    if _RX_EURES_HORS.search(titre):
        return None
    if contrat_du_titre(titre) in _EX:
        return None
    loc = j.get("locationMap") or {}
    code = next(iter(loc), "") if isinstance(loc, dict) else ""
    lieu = _EURES_PAYS.get(code.upper(), code)
    soc = str((j.get("employer") or {}).get("name") or "").strip()
    if _RX_EURES_ANONYME.search(soc):
        soc = "Employeur non précisé (EURES)"
    date = ""
    try:
        date = time.strftime("%Y-%m-%d", time.gmtime(int(j.get("creationDate")) / 1000))
    except Exception:
        pass
    return _mk(
        titre,
        EURES_FICHE.format(j.get("id")),
        soc,
        lieu,
        date,
        "eures",
        _strip_html(str(j.get("description") or "")),
    )


def scan_eures(pages=1, par_page=50, mots=None):
    """Offres EURES de la derniere semaine, une page par mot-cle par defaut."""
    import httpx

    _EX = contrats_exclus()
    offers, vus = [], set()
    n_req = 0
    with httpx.Client(follow_redirects=True) as client:
        for mot in mots or EURES_MOTS:
            for page in range(1, pages + 1):
                if n_req:
                    time.sleep(EURES_DELAI)  # crawl-delay: 10
                n_req += 1
                try:
                    r = _post_borne(
                        client,
                        EURES_URL,
                        json=_eures_corps(mot, page, par_page),
                        headers={
                            **UA,
                            "Content-Type": "application/json",
                            "Accept": "application/json",
                        },
                        timeout=40,
                    )
                except Exception as e:
                    INCIDENTS["eures"][type(e).__name__] += 1
                    break
                if r.status_code != 200:
                    INCIDENTS["eures"][f"HTTP {r.status_code}"] += 1
                    break
                jvs = (r.json() or {}).get("jvs") or []
                garde = 0
                for j in jvs:
                    if j.get("id") in vus:
                        continue
                    vus.add(j.get("id"))
                    o = _eures_offre(j, _EX)
                    if o:
                        offers.append(o)
                        garde += 1
                print(f"    « {mot} » p{page} : {len(jvs)} lues, {garde} retenues")
                if len(jvs) < par_page:
                    break
    print(f"  ✓ EURES → {len(offers)} offres (avec description)")
    return offers


# ═══════════════ Indeed — la PAGE DE RÉSULTATS, et rien d'autre ═══════════════
# Ce qu'on lit et ce qu'on ne lit pas. La frontiere n'est pas technique, elle
# est deliberee, et elle merite d'etre ecrite noir sur blanc :
#
#   /jobs?q=…&l=…   AUTORISE. Le bloc « User-agent: * » du robots.txt commence
#                   par « Allow: / » ; sur ses 468 lignes de Disallow, aucune ne
#                   vise la recherche. Seuls les chemins PAYS sont fermes
#                   (/jobs/FR/, /jobs/CA/…), ce qui n'est pas la meme URL.
#   /viewjob?jk=…   INTERDIT — « Disallow: /viewjob? », ligne 170. On ne va
#                   JAMAIS la chercher. L'URL est stockee pour que l'utilisateur
#                   l'ouvre lui-meme dans son navigateur : stocker un lien
#                   n'est pas le crawler.
#   page 2 et +     &start=10 repond 307 vers secure.indeed.com/auth, avec
#                   « branding=page-two-signin ». C'est un mur de CONNEXION,
#                   pas un anti-bot. On s'arrete a la page 1, soit 15 cartes
#                   par requete, et le volume vient du nombre de requetes.
#
# L'API mobile apis.indeed.com/graphql sert tout cela sans aucune de ces
# limites — description entiere comprise. Elle exige une cle extraite de
# l'application iOS d'Indeed (c'est ce que fait JobSpy, 4300 etoiles). Cette
# cle n'est pas la notre : on ne s'en sert pas. Ce n'est pas une impossibilite
# technique, c'est un choix, et c'est le seul ecart entre eux et nous.
#
# CONSEQUENCE DE CONCEPTION. Indeed est une source de DECOUVERTE, pas de
# dossier. Le snippet fait 140 a 165 caracteres la ou fit_score travaille sur
# l'annonce entiere. rang_source la classe 1 (agregateur) : des qu'une autre
# source publie la meme annonce, son lien reprend la place. Ce qu'Indeed
# apporte et que les autres nous donnent mal, c'est le CADRE — type de contrat
# (15/15 des cartes mesurees), date de publication REELLE, teletravail,
# salaire. Trois champs ou la file est aujourd'hui presque vide.
INDEED_HOTE = "https://fr.indeed.com"
# Aucun crawl-delay annonce dans le robots.txt, mais un bridage bien reel — et
# qui ne repond PAS a la cadence. Mesure, six requetes identiques a chaque fois :
#
#   pause 15 s :  403 403 403 200 200 200   → 3 refus
#   pause 25 s :  200 403 403 403 403 403   → 5 refus
#
# Ralentir n'ameliore rien : ce n'est pas un debit, c'est un quota glissant par
# adresse, qui se remplit et se vide. Aucun en-tete Retry-After.
#
# LE QUOTA SE VIDE POUR LA JOURNEE, PAS POUR LA MINUTE. Journal de la journee
# du 17/09, meme machine :
#
#   1re passe, 28 requetes   → 61 offres, environ la moitie refusee
#   2e passe (16 requetes)   → 2 reponses, 14 refus
#   3e passe, 110 requetes   → 0 offre, abandon des la 6e requete
#
# Entre la 2e et la 3e, deux heures d'attente n'ont rien rempli. Tirer sur un
# quota vide ne fait que le garder vide, et chaque refus coute 45 s de repos
# plus deux requetes.
#
# D'OU LE BUDGET. Une passe s'arrete a INDEED_BUDGET requetes, et elle ne
# reprend pas les memes mots-cles : elle repart la ou la precedente s'est
# arretee. 55 mots-cles x 2 villes = 110 couples, soit environ cinq jours pour
# faire le tour — ce qui convient a des offres qui vivent plusieurs semaines.
INDEED_PAUSE = 12  # assez pour ne pas peser, inutile d'aller plus lent
INDEED_BUDGET = 20  # requetes par passe ; au-dela le quota est a sec
INDEED_ETAT = HERE / ".indeed_rotation"  # ou la passe precedente s'est arretee
INDEED_REPOS = 45  # repos apres un refus, avant la seule seconde chance
# Depuis le 04/10 : refus 403/challenge = arrêt immédiat ; quota 429 = un
# réessai borné, puis arrêt. Le challenge Cloudflare a été observé en réel.
# Lieux de recherche : les secteurs prioritaires du profil (zones.py).
INDEED_LIEUX = [s["libelle"] for s in __import__("zones").SECTEURS_PRIORITAIRES] or ["France"]
# On se presente pour ce qu'on est. Mesure faite, les trois cas :
#   « JobHunter/1.0 … »   → 200, 1 108 971 o
#   aucun UA (Python-urllib) → 403
#   un UA Chrome          → 200
# Indeed refuse l'agent par DEFAUT de la bibliotheque, pas les robots : un nom
# franc suffit. Inutile de se deguiser en navigateur, on ne le fait donc pas.
INDEED_UA = {
    "User-Agent": "JobHunter/1.0 (recherche d'emploi personnelle)",
    "Accept-Language": "fr-FR,fr;q=0.9",
}
_RX_INDEED_BLOB = re.compile(r'providerData\["mosaic-provider-jobcards"\]\s*=\s*')

# « Temps plein » et « Temps partiel » sont des temps de travail, pas des
# contrats : les laisser passer remplirait la colonne `contrat` de valeurs qui
# ne servent a rien pour filtrer. Ils sont ignores, et une carte qui ne porte
# qu'eux repart sans contrat — « non precise » reste une reponse honnete.
_INDEED_CONTRAT = {
    "cdi": "CDI",
    "cdd": "CDD",
    "stage": "Stage",
    "alternance": "Alternance",
    "apprentissage": "Alternance",
    "freelance": "Freelance",
    "independant": "Freelance",
    "interim": "Interim",
    "temporaire": "Interim",
}


class _IndeedBride(Exception):
    """Indeed bride apres une seconde chance. On arrete la passe et on GARDE ce
    qui a ete lu : une passe interrompue vaut mieux qu'une passe perdue, et le
    scan suivant reprendra les mots-cles restants."""


def _json_objet(texte, depart):
    """L'objet JSON complet qui commence a l'accolade `depart`.

    Une expression non gourmande (\\{.*?\\};) s'arreterait au premier « }; »
    rencontre, y compris a l'interieur d'une chaine. Le blob d'Indeed fait 54 ko
    et contient du HTML de description : on compte les accolades en sautant ce
    qui est entre guillemets.
    """
    prof = 0
    chaine = False
    echap = False
    for i in range(depart, len(texte)):
        c = texte[i]
        if chaine:
            if echap:
                echap = False
            elif c == "\\":
                echap = True
            elif c == '"':
                chaine = False
            continue
        if c == '"':
            chaine = True
        elif c == "{":
            prof += 1
        elif c == "}":
            prof -= 1
            if prof == 0:
                return texte[depart : i + 1]
    return ""


class _IndeedBloque(Exception):
    """Refus explicite, connexion requise ou réponse inexploitable : arrêt."""


INDEED_REQUETES = 0


def _indeed_cartes(mot, lieu):
    """Lit la page publique ; distingue refus, quota et réponse vide valide."""
    import urllib.request, urllib.error
    from email.utils import parsedate_to_datetime

    global INDEED_REQUETES
    url = f"{INDEED_HOTE}/jobs?q={quote(mot)}&l={quote(lieu)}"

    def bloque(raison):
        INCIDENTS["indeed"][raison] += 1
        raise _IndeedBloque(raison)

    for essai in (1, 2):
        try:
            INDEED_REQUETES += 1
            with urllib.request.urlopen(
                urllib.request.Request(url, headers=INDEED_UA), timeout=25
            ) as f:
                if "secure.indeed.com" in f.geturl():
                    bloque("connexion requise")
                if f.headers.get("cf-mitigated", "").lower() == "challenge":
                    bloque("challenge anti-bot")
                texte = _lire_borne(f).decode("utf-8", "replace")
            break
        except _IndeedBloque:
            raise
        except urllib.error.HTTPError as e:
            code = e.code
            retry_after = e.headers.get("Retry-After") if e.headers else None
            e.close()
            if code in (401, 403):
                bloque(f"HTTP {code}")
            INCIDENTS["indeed"][f"HTTP {code}"] += 1
            if code != 429:
                raise _IndeedBloque(f"HTTP {code}")
            attente = INDEED_REPOS
            if retry_after:
                try:
                    attente = max(0, int(retry_after))
                except ValueError:
                    try:
                        attente = max(
                            0, parsedate_to_datetime(retry_after).timestamp() - time.time()
                        )
                    except (TypeError, ValueError, OverflowError):
                        pass
            # Ne jamais réessayer avant un Retry-After supérieur au budget.
            if essai == 2 or attente > 300:
                raise _IndeedBride(429)
            print(f"    ~ {mot} / {lieu} : HTTP 429, repos {attente:g} s")
            time.sleep(attente)
        except Exception as e:
            bloque(type(e).__name__)
    if re.search(r"<title[^>]*>[^<]*(?:security check|just a moment|captcha)", texte, re.I):
        bloque("challenge anti-bot")
    m = _RX_INDEED_BLOB.search(texte)
    if not m:
        bloque("format de page non reconnu")
    brut = _json_objet(texte, texte.find("{", m.end()))
    try:
        d = json.loads(brut)
        resultats = d["metaData"]["mosaicProviderJobCardsModel"]["results"]
        if not isinstance(resultats, list) or any(not isinstance(c, dict) for c in resultats):
            raise ValueError("results doit être une liste de cartes")
    except (ValueError, TypeError, KeyError):
        bloque("format des offres non reconnu")
    return resultats


def _indeed_contrat(job_types):
    """['Temps plein', 'CDI'] → 'CDI'. Rien de reconnu → ''."""
    import unicodedata

    for t in job_types or []:
        n = unicodedata.normalize("NFD", str(t).lower())
        n = "".join(c for c in n if unicodedata.category(c) != "Mn").strip()
        if n in _INDEED_CONTRAT:
            return _INDEED_CONTRAT[n]
    return ""


def _indeed_date(ms):
    """Epoch en millisecondes → 'AAAA-MM-JJ'. C'est la VRAIE date de parution.

    Elle vaut mieux que la date de scan : la file porte 2634 offres datees du
    meme jour, celui ou on les a vues. Une valeur hors des bornes raisonnables
    est rejetee plutot que convertie en 1970.
    """
    try:
        s = float(ms) / 1000.0
    except Exception:
        return ""
    if not (946684800 < s < time.time() + 86400):  # entre 2000 et demain
        return ""
    return time.strftime("%Y-%m-%d", time.localtime(s))


def scan_indeed(mots=None, lieux=None, pause=None, *, persist=True):
    """Page 1 des resultats Indeed, pour chaque couple (mot-cle, lieu).

    15 cartes au maximum par requete — c'est le mur de connexion de la page 2
    qui fixe ce plafond, pas nous. Le rendement vient donc du produit
    mots-cles x lieux.

    La passe ne traite qu'une TRANCHE de ce produit, INDEED_BUDGET couples, et
    reprend la ou la precedente s'est arretee. Le quota d'Indeed se vide pour
    la journee : une passe qui tente les 110 couples n'en obtient pas plus
    qu'une qui en tente 20, elle perd seulement une heure en repos inutiles.
    """
    mots = mots or KEYWORDS
    lieux = lieux or INDEED_LIEUX
    pause = INDEED_PAUSE if pause is None else pause
    _EX = contrats_exclus()
    offers = []
    vus = set()

    # Tous les couples, a plat : la rotation porte sur le COUPLE, pas sur le
    # mot-cle. Sinon une passe de 20 requetes couvrirait 10 mots-cles sur deux
    # villes, et la tranche suivante repartirait sur les memes villes.
    couples = [(m, l) for m in mots for l in lieux]
    depart = 0
    try:
        depart = int(INDEED_ETAT.read_text(encoding="utf-8").strip()) % len(couples)
    except Exception:
        pass
    tranche = [
        couples[(depart + i) % len(couples)] for i in range(min(INDEED_BUDGET, len(couples)))
    ]
    print(
        f"  Indeed : {len(tranche)} couples sur {len(couples)} "
        f"(depuis le n° {depart + 1}, {pause} s entre chaque, "
        f"~{len(tranche) * pause // 60} min)"
    )

    fait = 0
    debut_http = INDEED_REQUETES
    bloque_raison = ""
    bride = False
    for mot, lieu in tranche:
        if fait:
            time.sleep(pause)
        fait += 1
        try:
            cartes = _indeed_cartes(mot, lieu)
        except _IndeedBloque as e:
            bloque_raison = str(e)
            print(f"  Indeed : source indisponible ({e}) — arrêt sans réessai")
            break
        except _IndeedBride as e:
            bride = True
            print(f"  Indeed : quota HTTP {e} — arrêt de la passe")
            break
        for c in cartes:
            jk = c.get("jobkey")
            if not jk or jk in vus:
                continue
            vus.add(jk)
            # Indeed marque lui-meme les annonces mortes. C'est
            # exactement ce que audit_fraicheur.py va chercher a la
            # main, offre par offre : ici c'est donne.
            if c.get("expired"):
                continue
            titre = (c.get("title") or c.get("displayTitle") or "").strip()
            if not titre or not title_ok(titre):
                continue
            ctr = _indeed_contrat(c.get("jobTypes"))
            if (ctr or contrat_du_titre(titre)) in _EX:
                continue
            o = _mk(
                titre,
                f"{INDEED_HOTE}/viewjob?jk={jk}",
                (c.get("company") or "").strip() or "Indeed",
                c.get("formattedLocation") or lieu,
                _indeed_date(c.get("pubDate")),
                "indeed",
                _strip_html(c.get("snippet") or ""),
            )
            o["contrat"] = ctr
            o["teletravail"] = (c.get("remoteWorkModel") or {}).get("text") or ""
            o["salaire"] = (c.get("salarySnippet") or {}).get("text") or ""
            # Le snippet n'est PAS l'annonce : 160 caracteres contre
            # plusieurs milliers. Sans ce drapeau, la promotion d'URL
            # ecraserait une description complete deja en file par ce
            # resume. Voir merge_into_queue.
            o["desc_partielle"] = True
            offers.append(o)
        if fait % 10 == 0:
            print(f"    … {fait}/{len(tranche)} ({len(offers)} retenues)")

    # OU REPRENDRE DEMAIN. On avance de ce qui a ete REELLEMENT tente, pas du
    # budget : une passe arretee au 6e refus n'a couvert que six couples, et
    # repartir vingt plus loin sauterait quatorze mots-cles qui n'ont jamais
    # ete essayes. Un quota vide ne doit pas creuser de trou dans la liste.
    try:
        if persist:
            INDEED_ETAT.write_text(str((depart + fait) % len(couples)), encoding="utf-8")
    except Exception:
        pass

    etat = "indisponible" if bloque_raison else "quota atteint" if bride else "terminé"
    print(
        f"  Indeed [{etat}] : {len(offers)} offres, {fait} couples, "
        f"{INDEED_REQUETES - debut_http} tentatives HTTP"
    )
    if bride:
        print(
            f"    reprise au couple n° {(depart + fait) % len(couples) + 1} "
            f"sur {len(couples)} a la prochaine passe"
        )
    return offers


# ═══════════════ APEC — le remplacant d'Indeed ═══════════════
#
# POURQUOI. Indeed a rendu 0 offre le 17/09 : 184 requetes en un apres-midi ont
# epuise la tolerance, et douze sondes etalees sur cinq heures n'ont pas obtenu
# une seule reponse. Il fallait une source qui couvre le meme besoin — le
# marche francais large, avec contrat, date de parution et salaire.
#
# L'APEC est le site d'emploi des CADRES en France, et c'est la route la plus
# propre rencontree dans ce projet :
#
#   robots.txt        309 octets, AUCUN Disallow pour « User-agent: * »
#   sitemap declare   sitemap_offres_search_engine.xml.gz, dedie aux offres
#   API               cms/webservices/rechercheOffre, sans cle ni compte
#
# CE QU'ELLE DONNE, EXACTEMENT. Une requete rend 50 offres d'un coup, chacune
# avec un extrait de 283 caracteres — mesure : min 283, median 283, max 283,
# c'est une troncature nette. Plus long que les 160 d'Indeed et les 159 de
# Glassdoor, mais ce n'est PAS l'annonce entiere : j'avais ecrit le contraire
# ici avant de mesurer.
#
# La fiche complete n'est pas accessible : l'API de detail
# (cms/webservices/offre/...) repond 401, et la page HTML est une coquille
# Angular de 53 ko sans une ligne de l'annonce, ni ld+json. On s'arrete donc a
# l'extrait — le lien, lui, s'ouvre normalement dans le navigateur de l'utilisateur.
#
# En revanche, et c'est ce qui la rend precieuse : la date de publication est
# horodatee, le salaire est en clair (« A partir de 50 k€ brut annuel », 23 sur
# 23 renseignes a la mesure), et `indicateurFaibleCandidature` signale les
# offres peu concurrencees — personne d'autre ne publie cela.
#
# Le sitemap, lui, ne liste que 1288 URL de RECHERCHE par fonction et secteur,
# pas les offres. C'est l'API qui sert, et le sitemap qui atteste qu'elle est
# faite pour etre lue.
APEC_API = "https://www.apec.fr/cms/webservices/rechercheOffre"
APEC_FICHE = "https://www.apec.fr/candidat/recherche-emploi.html/emploi/detail-offre/"
APEC_PAUSE = 2  # aucun crawl-delay annonce ; on reste courtois
APEC_PAR_PAGE = 50

# LES CODES DE CONTRAT, ETABLIS PAR RECOUPEMENT — pas devines. L'API rend un
# identifiant de referentiel sans libelle. On a donc croise le code avec les
# titres qui nomment le contrat en clair, sur sept requetes :
#
#   101888   303 offres, 3 titres explicites, TOUS « CDI »
#   101887    30 offres, 6 titres explicites, TOUS « CDD »
#   597137     2 offres, 2 titres explicites, TOUS « Alternance »
#   101889    21 offres, AUCUN titre explicite  -> non mappe
#
# Aucun code ne se partage entre deux contrats. Les codes sans preuve restent
# dehors : mieux vaut « non precise » qu'une colonne fausse — c'est elle qui
# sert a filtrer, et quatre stages du Credit Agricole etiquetes CDD avaient
# deja remonte en tete du classement.
#
# Ce mapping n'intervient qu'en DERNIER RECOURS : un titre qui dit « CDD 8
# mois » l'emporte toujours sur le code.
_APEC_CONTRAT = {101888: "CDI", 101887: "CDD", 597137: "Alternance"}

# REFUS D'AFFILEE AU-DELA DESQUELS ON ARRETE. L'APEC est derriere DataDome : le
# 2026-10-02 au soir, apres ~540 requetes d'un audit de liens, ses 55 recherches
# ont toutes rendu 403. Insister sur les 52 suivantes ne rapporte rien et
# prolonge la mise a l'ecart. Trois refus d'affilee : la source est fermee
# pour aujourd'hui.
APEC_ABANDON = 3


def _apec_page(mot, debut):
    """Une page de resultats APEC. Liste vide en cas de refus."""
    import urllib.request, urllib.error

    corps = json.dumps(
        {
            "motsCles": mot,
            "pagination": {"range": APEC_PAR_PAGE, "startIndex": debut},
            "sorts": [{"type": "DATE", "direction": "DESCENDING"}],
            "activeFiltre": True,
        }
    ).encode("utf-8")
    tetes = dict(UA)
    tetes["Content-Type"] = "application/json"
    tetes["Accept"] = "application/json"
    try:
        r = urllib.request.Request(APEC_API, data=corps, headers=tetes, method="POST")
        with urllib.request.urlopen(r, timeout=30) as f:
            d = json.loads(_lire_borne(f).decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        print(f"    ! {mot} : HTTP {e.code}")
        INCIDENTS["apec"][f"HTTP {e.code}"] += 1
        return None, 0
    except Exception as e:
        print(f"    ! {mot} : {type(e).__name__}")
        return [], 0
    return d.get("resultats") or [], d.get("totalCount") or 0


def scan_apec(mots=None, pages=2):
    """Offres APEC : titre, societe, lieu, date, salaire, extrait de 283 car.

    `pages` : pages de 50 par mot-cle. Une page coute UNE requete, d'ou le
    meilleur rendement de toutes nos sources — mais l'extrait reste un extrait,
    et les offres partent avec `desc_partielle` pour que la promotion d'URL ne
    remplace jamais une annonce complete par ces 283 caracteres.
    """
    mots = mots or KEYWORDS
    _EX = contrats_exclus()
    offers, vus = [], set()
    print(
        f"  APEC : {len(mots)} mots-cles x {pages} page(s) de {APEC_PAR_PAGE} "
        f"({APEC_PAUSE} s entre chaque)"
    )
    fait = refus = 0
    for mot in mots:
        if refus >= APEC_ABANDON:
            print(
                f"  ⏸ APEC : {refus} refus d'affilee — source fermee pour aujourd'hui, "
                f"pas d'insistance"
            )
            break
        for p in range(pages):
            if fait:
                time.sleep(APEC_PAUSE)
            fait += 1
            res, total = _apec_page(mot, p * APEC_PAR_PAGE)
            if res is None:
                refus += 1
                break
            refus = 0
            if not res:
                break
            for o in res:
                num = o.get("numeroOffre") or o.get("id")
                if not num or num in vus:
                    continue
                vus.add(num)
                titre = (o.get("intitule") or "").strip()
                if not titre or not title_ok(titre):
                    continue
                desc = _strip_html(o.get("texteOffre") or "")
                # Le titre d'abord, puis l'extrait, puis le code de l'APEC.
                # Dans cet ordre : un titre qui dit « CDD 8 mois » est plus sur
                # qu'un identifiant de referentiel, et 283 caracteres ne
                # suffisent pas a trancher — 583 offres sur 654 sortaient en
                # « non precise » avant que le code ne soit exploite.
                ctr = (
                    contrat_du_titre(titre)
                    or contrat_de_la_description(desc, "")
                    or _APEC_CONTRAT.get(o.get("typeContrat"), "")
                )
                if ctr in _EX:
                    continue
                x = _mk(
                    titre,
                    APEC_FICHE + str(num),
                    (o.get("nomCommercial") or "APEC").strip(),
                    o.get("lieuTexte") or "",
                    str(o.get("datePublication") or "")[:10],
                    "apec",
                    desc,
                )
                x["contrat"] = ctr
                x["salaire"] = (o.get("salaireTexte") or "").strip()
                # 283 caracteres ne sont pas une annonce : sans ce drapeau, la
                # promotion d'URL remplacerait une description complete par cet
                # extrait. Meme garde que pour Indeed et Glassdoor.
                x["desc_partielle"] = True
                # Peu de candidats : l'APEC est seule a le publier, et c'est
                # exactement ce qui fait la difference sur une candidature.
                if o.get("indicateurFaibleCandidature"):
                    x["peu_de_candidats"] = True
                offers.append(x)
            if len(res) < APEC_PAR_PAGE:
                break
    rares = sum(1 for x in offers if x.get("peu_de_candidats"))
    print(
        f"  ✓ APEC → {len(offers)} offres sur {fait} requetes "
        f"(extrait de 283 car., {rares} a faible candidature)"
    )
    return offers


# ═══════════════ Glassdoor — la page de recherche, page 1 ═══════════════
# Meme demarche qu'Indeed, meme frontiere, resultat plus maigre.
#
#   /Emploi/…SRCH_….htm   AUTORISE. Le robots.txt ne ferme que les formes
#                         PAGINEES (« Disallow: /Emploi/*_IP* »), pas la
#                         premiere page.
#   /graph                INTERDIT — « Disallow: /graph », ligne 145. C'est
#                         l'API GraphQL qu'utilise JobSpy. Son jeton, lui, est
#                         servi a tout visiteur dans le HTML (leur
#                         _get_csrf_token le lit sur une page publique), donc
#                         ce n'est pas un identifiant vole comme la cle iOS
#                         d'Indeed — mais le chemin est explicitement interdit
#                         aux robots, et cela suffit a le fermer.
#   pages 2 et +          « Disallow: /Emploi/*_IP* » : c'est la pagination.
#                         30 cartes par requete, et on s'arrete la.
#
# CE QUE GLASSDOOR DONNE, ET CE QU'IL NE DONNE PAS. Le ld+json de la page ne
# porte que le titre et l'URL. Tout le reste est dans le HTML rendu, repere par
# des attributs `data-test` (stables) et des classes CSS hachees (qui changent
# a chaque deploiement) : on n'accroche donc que les data-test et des PREFIXES
# de classe. Surtout, Glassdoor ne publie AUCUN type de contrat structure, la
# ou Indeed en fournit un sur 15 cartes sur 15. Le contrat retombe sur la
# lecture du titre, avec ses trous connus. L'anciennete est relative (« 30j+ »,
# « 3j »), pas une date : on ne la convertit que lorsqu'elle est bornee.
GD_HOTE = "https://www.glassdoor.fr"
GD_PAUSE = 12
GD_REPOS = 45
GD_ABANDON = 6
GD_LOC_FRANCE = 86  # locId du pays ; Glassdoor n'expose les id de VILLE
# que par /ajax/, interdit. On cherche donc France
# entiere et on trie ensuite avec zones.zone_lieu().
GD_UA = dict(INDEED_UA)

# Une carte commence a son intitule. Le nom de l'employeur est AVANT dans le
# HTML, le lieu et le salaire APRES : on decoupe donc sur les intitules et on
# lit de part et d'autre.
_RX_GD_TITRE = re.compile(r'<a\b[^>]*data-test="job-title"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', re.S)
_RX_GD_EMPLOYEUR = re.compile(r'compactEmployerName[^"]*"[^>]*>(.*?)</span>', re.S)
_RX_GD_LIEU = re.compile(r'data-test="emp-location"[^>]*>(.*?)</div>', re.S)
_RX_GD_SALAIRE = re.compile(r'data-test="detailSalary"[^>]*>(.*?)</div>', re.S)
_RX_GD_AGE = re.compile(r'data-test="job-age"[^>]*>(.*?)</div>', re.S)
_RX_GD_EXTRAIT = re.compile(r'jobDescriptionSnippet[^"]*"[^>]*>(.*?)</div>', re.S)


def _gd_texte(h):
    """Fragment HTML → texte nu."""
    import html as _h

    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", _h.unescape(h or ""))).strip()


def _gd_date(age):
    """« 3j » → la date d'il y a trois jours. « 30j+ » → rien.

    L'anciennete affichee est relative et parfois NON BORNEE : « 30j+ » couvre
    aussi bien 31 jours que huit mois. La convertir donnerait une date fausse
    dans la colonne meme qui sert a juger de la fraicheur — on prefere le vide.
    """
    a = (age or "").strip().lower()
    if "+" in a:
        return ""
    m = re.match(r"^(\d+)\s*(h|j|d|min)", a)
    if not m:
        return ""
    n = int(m.group(1))
    jours = n if m.group(2) in ("j", "d") else 0
    return time.strftime("%Y-%m-%d", time.localtime(time.time() - jours * 86400))


def _gd_url(mot):
    """L'URL canonique de recherche. Le mot-cle est DANS le chemin.

    Piege verifie a la main : `?sc.keyword=analyste+financier` est ignore en
    silence. La page repond 200, sert 30 cartes bien formees — et parle de
    « Vendeur Projets » et d'« Aide familial(e) ». Le mot-cle reel est celui
    que designent les offsets du nom de fichier :

        france-analyste-esg-emplois-SRCH_IL.0,6_IN86_KO7,19.htm
                                         ^^^^^      ^^^^^^
        IL.0,6  le LIEU occupe les caracteres 0 a 6 du slug  → « france »
        IN86    l'identifiant de pays
        KO7,19  le MOT-CLE occupe les caracteres 7 a 19      → « analyste-esg »

    Se tromper ici ne casse rien : ca remplit la file de commerciaux. C'est
    pire qu'une erreur, c'est une erreur invisible.
    """
    import unicodedata

    n = unicodedata.normalize("NFD", mot.lower())
    n = "".join(c for c in n if unicodedata.category(c) != "Mn")
    n = re.sub(r"-{2,}", "-", re.sub(r"[^a-z0-9]+", "-", n)).strip("-")
    debut = len("france-")
    return (
        f"{GD_HOTE}/Emploi/france-{n}-emplois"
        f"-SRCH_IL.0,6_IN{GD_LOC_FRANCE}_KO{debut},{debut + len(n)}.htm"
    )


def _gd_cartes(mot):
    """Les cartes de la page 1 pour un mot-cle, France entiere."""
    import urllib.request, urllib.error

    url = _gd_url(mot)
    texte = ""
    for essai in (1, 2):
        try:
            with urllib.request.urlopen(
                urllib.request.Request(url, headers=GD_UA), timeout=25
            ) as f:
                texte = _lire_borne(f).decode("utf-8", "replace")
            break
        except urllib.error.HTTPError as e:
            # Un 403 n'a PAS de seconde chance : c'est un refus d'entree, pas
            # une limite de debit. Le 2026-10-07, le repos de 45 s puis la
            # nouvelle tentative ont ete payes sur chacun des 37 mots-cles
            # atteints, et l'etape a ete tuee a 40 min (idem le 2026-10-03).
            if e.code == 429 and essai == 1:
                attente = int(e.headers.get("Retry-After") or GD_REPOS)
                print(f"    ~ {mot} : HTTP {e.code}, repos {attente} s")
                time.sleep(min(attente, 300))
                continue
            print(f"    ! {mot} : HTTP {e.code}")
            INCIDENTS["glassdoor"][f"HTTP {e.code}"] += 1
            if e.code in (403, 429):
                raise _IndeedBride(e.code)
            return []
        except Exception as e:
            print(f"    ! {mot} : {type(e).__name__}")
            return []

    return _gd_parse(texte)


def _gd_parse(texte):
    """HTML de la page de recherche → cartes. Separe du reseau pour etre
    testable sur une page enregistree, sans requete."""
    titres = list(_RX_GD_TITRE.finditer(texte))
    cartes = []
    for n, m in enumerate(titres):
        avant = texte[(titres[n - 1].end() if n else 0) : m.start()]
        apres = texte[m.end() : (titres[n + 1].start() if n + 1 < len(titres) else len(texte))]
        emp = _RX_GD_EMPLOYEUR.findall(avant)
        lieu = _RX_GD_LIEU.search(apres)
        sal = _RX_GD_SALAIRE.search(apres)
        age = _RX_GD_AGE.search(apres)
        ext = _RX_GD_EXTRAIT.search(apres)
        cartes.append(
            {
                "url": m.group(1),
                "titre": _gd_texte(m.group(2)),
                # Le dernier nom trouve AVANT l'intitule est celui de cette carte :
                # les precedents appartiennent aux cartes d'avant.
                "entreprise": _gd_texte(emp[-1]) if emp else "",
                "lieu": _gd_texte(lieu.group(1)) if lieu else "",
                "salaire": _gd_texte(sal.group(1)) if sal else "",
                "age": _gd_texte(age.group(1)) if age else "",
                "extrait": _gd_texte(ext.group(1)) if ext else "",
            }
        )
    return cartes


def scan_glassdoor(mots=None, pause=None):
    """Page 1 de la recherche Glassdoor, France entiere, un passage par mot-cle.

    30 cartes au maximum par requete. La zone est jugee apres coup sur le lieu
    de la carte, faute de pouvoir cibler une ville : les identifiants de ville
    ne s'obtiennent que par /ajax/, interdit aux robots.
    """
    mots = mots or KEYWORDS
    pause = GD_PAUSE if pause is None else pause
    _EX = contrats_exclus()
    offers, vus = [], set()
    refus = refuses = 0
    print(
        f"  Glassdoor : {len(mots)} mots-cles ({pause} s entre chaque, "
        f"~{len(mots) * pause // 60} min)"
    )
    for i, mot in enumerate(mots):
        if i:
            time.sleep(pause)
        try:
            cartes = _gd_cartes(mot)
            refus = 0
        except _IndeedBride as e:
            refuses += 1
            # REFUS D'ENTREE : on s'arrete au premier. Un seul 403 suffit parce
            # qu'il n'est jamais isole — le 2026-10-07, 37 mots sur 37 l'ont
            # recu, la nouvelle tentative ne passant que 7 fois — et
            # que chaque requete de plus prolonge la mise a l'ecart. Le cout
            # d'un 403 fortuit : les mots restants de Glassdoor, pour un jour.
            if e.args and e.args[0] == 403:
                print(
                    f"  ⏸ Glassdoor : refus d'entree (HTTP 403) — source fermee "
                    f"pour aujourd'hui, pas d'insistance, {len(offers)} offres "
                    f"conservees"
                )
                break
            refus += 1
            if refus >= GD_ABANDON:
                print(
                    f"  ⏸ Glassdoor : {refus} refus d'affilee (HTTP {e}) — passe "
                    f"arretee, {len(offers)} offres conservees"
                )
                break
            # Refus EN ALTERNANCE avec des succes : le compteur d'affilee se
            # remettait a zero, et chaque mot payait 45 s de repos. Le
            # 2026-10-07, la passe a ete coupee a 40 min par la minuterie, et WTJ,
            # qui passe apres, n'a rien collecte.
            if refuses >= 2 * GD_ABANDON:
                print(
                    f"  ⏸ Glassdoor : {refuses} refus sur {i + 1} mots-cles — passe "
                    f"arretee, {len(offers)} offres conservees"
                )
                break
            continue
        for c in cartes:
            u = c["url"].split("?")[0]
            if not u or u in vus:
                continue
            vus.add(u)
            titre = c["titre"]
            if not titre or not title_ok(titre):
                continue
            # Glassdoor ne publie pas de type de contrat : le titre est tout ce
            # qu'on a, et il se tait une fois sur deux. C'est le recul principal
            # par rapport a Indeed, il vaut mieux l'ecrire que le decouvrir.
            ctr = contrat_du_titre(titre)
            if ctr in _EX:
                continue
            o = _mk(
                titre,
                c["url"],
                c["entreprise"] or "Glassdoor",
                c["lieu"],
                _gd_date(c["age"]),
                "glassdoor",
                c["extrait"],
            )
            o["contrat"] = ctr
            o["salaire"] = c["salaire"]
            o["desc_partielle"] = True
            offers.append(o)
    print(
        f"  ✓ Glassdoor → {len(offers)} offres ({refuses} requetes refusees) — "
        f"description = extrait, pas de contrat structure"
    )
    return offers


# ═══════════════ MERGE → apply_queue.json (dédup + scoring) ═══════════════
from jutil import cle as _norm  # meme semantique qu'avant : minuscules + blancs,
# accents CONSERVES (cle de deduplication de la queue)


# Paramètres de tracking : présents ou non selon d'où vient le lien, ils ne
# changent PAS l'offre. Sans les retirer, la dédup par URL exacte est inopérante
# dès qu'on colle un lien LinkedIn (…/jobs/view/123?refId=X&trackingId=Y) déjà
# présent en queue → doublon.
_URL_JUNK = {
    "refid",
    "trackingid",
    "trk",
    "origin",
    "position",
    "pagenum",
    "eblc",
    "recommended",
    "src",
    "source",
    "savedsearchid",
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_content",
    "utm_term",
}


def _norm_url(u):
    """Clé de dédup d'URL : hôte sans www, chemin sans / final, params de
    tracking retirés et reste trié. Les vrais identifiants (?jk=, ?id=) restent."""
    from urllib.parse import urlsplit, parse_qsl, urlencode

    u = (u or "").strip()
    if not u:
        return ""
    try:
        s = urlsplit(u)
    except Exception:
        return u.lower()
    host = s.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    if host.endswith("linkedin.com"):  # fr./be./lu. linkedin = même site
        host = "linkedin.com"
    qs = [(k, v) for k, v in parse_qsl(s.query) if k.lower() not in _URL_JUNK]
    tail = "?" + urlencode(sorted(qs)) if qs else ""
    return host + s.path.rstrip("/") + tail


# ── Qualite de la source d'une URL ──────────────────────────────────────────
# Une meme annonce paraît souvent sur LinkedIn ET sur un vrai site d'emploi
# (« Consultant(e) Junior ESG » chez Oderis : LinkedIn + Welcome to the Jungle).
# LinkedIn est le PIRE des deux : la page est derriere un mur de connexion, la
# description est illisible sans compte, et postuler renvoie de toute facon vers
# le site d'origine. On garde donc l'URL la mieux classee.
_AGREGATEURS = (
    "indeed.",
    "talent.com",
    "jobijoba",
    "optioncarriere",
    "jooble",
    "neuvoo",
    "glassdoor",
    "meteojob",
    "keljob",
    "cadremploi",
)
_SITES_EMPLOI = (
    "welcometothejungle",
    "efinancialcareers",
    "linkfinance",
    "apec.fr",
    "francetravail",
    "pole-emploi",
    "businessfrance",
    "hellowork",
    "monster.",
)
_ATS = (
    "greenhouse.io",
    "lever.co",
    "ashbyhq",
    "recruitee.com",
    "smartrecruiters",
    "myworkdayjobs",
    "workday",
    "taleo",
    "successfactors",
    "teamtailor",
    "workable.com",
    "personio",
    "icims.com",
    "avature",
    "flatchr",
    "softy.pro",
)


def rang_source(url):
    """Qualite de la source, du pire au meilleur. Sert a arbitrer les doublons.

    0 LinkedIn      mur de connexion, description illisible, redirige ailleurs
    1 agregateur    Indeed, Talent, Jobijoba : copie d'une annonce d'ailleurs
    2 site d'emploi WTJ, APEC, France Travail : annonce de premiere main
    3 ATS / site entreprise : la source, celle ou la candidature arrive
    """
    u = (url or "").lower()
    if not u:
        return -1
    if "linkedin.com" in u:
        return 0
    if any(k in u for k in _AGREGATEURS):
        return 1
    if any(k in u for k in _ATS):
        return 3
    if any(k in u for k in _SITES_EMPLOI):
        return 2
    return 3  # domaine d'entreprise : c'est la source


# ── Filtre geographique ──────────────────────────────────────────────────────
# Un flux ATS porte le nom de la societe, pas son pays. « Forvis Mazars » sur
# greenhouse est l'entite ALLEMANDE (« Einstieg als », « Rechtsanwalt ») et sur
# recruitee l'entite IRLANDAISE : zero poste en France sur 19. La verification
# d'identite ne peut pas le voir — le nom est le meme. Seul le LIEU tranche.
#
# l'utilisateur habite en Gironde. Une offre a Hanoi ou Dresde n'a pas a entrer.
_RX_FR = re.compile(
    r"\bfr\b|france|paris|lyon|lille|nantes|bordeaux|toulouse|marseille|nice"
    r"|rennes|strasbourg|montpellier|grenoble|rouen|reims|dijon|angers|tours"
    r"|clermont|orleans|metz|nancy|caen|brest|limoges|amiens|perpignan|besancon"
    r"|le mans|saint.etienne|toulon|villeurbanne|nimes|aix.en.provence"
    r"|ile.de.france|hauts.de.seine|gironde|remote|teletravail|t[ée]l[ée]travail"
    r"|hybrid|anywhere"
    # LE NUMERO DE DEPARTEMENT. L'APEC ecrit « Nanterre - 92 »,
    # « Issy-les-Moulineaux - 92 », « Marseille 01 - 13 ». Aucune de ces villes
    # n'etait dans la liste ci-dessus, et la regle de repli refusait tout lieu
    # de plus d'un mot : 341 offres sur 653 partaient donc comme etrangeres,
    # dont toute La Defense — le coeur de l'emploi financier francais.
    # Un numero a deux chiffres isole, ou 2A/2B, ou un code d'outre-mer a trois
    # chiffres, ne s'ecrit comme cela qu'en France. La plage monte a 98x :
    # arretee a 976, elle laissait « Noumea - 98 » dehors, la Nouvelle-Caledonie
    # etant 988 — comme Wallis 986 et la Polynesie 987.
    r"|(?:^|[\s,;-])(?:0[1-9]|[1-8]\d|9[0-5]|2[AB]|9[78]\d?)(?:$|[\s,;-])",
    re.I,
)
# Pays explicitement AILLEURS : le lieu est renseigne et ne parle pas de France.
_RX_ETRANGER = re.compile(
    r"\b(de|be|lu|es|it|uk|gb|us|ca|ch|nl|pl|ro|pt|ie|dk|se|no|fi|at|cz|gr|tr"
    r"|ma|tn|sn|cn|jp|sg|in|au|nz|br|ar|cl|mx|py|uy|hk|ae|za|vn|ph|id|th)\b"
    r"|deutschland|germany|berlin|munich|m[üu]nchen|frankfurt|hamburg|d[üu]sseldorf"
    r"|dresden|k[öo]ln|stuttgart|ireland|dublin|cork|belgi|bruxelles|brussels"
    r"|luxembourg|espa[ñn]a|madrid|barcelona|italia|milano|roma|london|manchester"
    r"|new york|san francisco|washington|toronto|casablanca|hanoi|cebu|davao"
    r"|philippines|tokyo|singapore|amsterdam|lisboa|warsaw|bucharest|z[üu]rich"
    r"|geneve|gen[èe]ve|hong kong|cape town|sydney|melbourne",
    re.I,
)


# Etat americain en fin de lieu : « Reston, VA », « Aurora, CO ». Sans ce motif
# ils passaient pour la France — aucun des deux codes n'etait dans la liste des
# pays, et un lieu non reconnu etait accepte par defaut.
_RX_ETAT_US = re.compile(
    r",\s*(AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|MA|MD|ME|MI"
    r"|MN|MO|MS|MT|NC|ND|NE|NH|NJ|NM|NV|NY|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VA"
    r"|VT|WA|WI|WV|WY|DC)\b"
)


# RECHERCHE MONDIALE. Le filtre geographique est un CHOIX, pas une loi : il a
# ecarte 179 offres au seul scan du 8 septembre. Quand l'utilisateur veut chercher
# partout, on ne le desactive PAS en modifiant chaque appelant — il y en a
# quatre, dont un dans probe_ats_esg — mais ici, a la source. `zones.py` range
# ensuite ces offres dans une zone « international » a part, pour qu'elles ne
# se melangent pas a ses cibles francaises.
# DEFAUT : on garde le monde entier. l'utilisateur a tranche le 17/09 — les offres
# hors de France sont voulues. Le scan DEMANDAIT deja huit pays a LinkedIn
# (LIEUX_MONDE) pour en jeter sept au merge, et ses propres programmes plus
# recents, scan_graduate et scan_secteurs, posent tous deux `J.MONDE = True`.
# Le defaut inverse etait le dernier endroit a ne pas suivre.
# `zones.py` range ces offres dans une zone « international » a part, pour
# qu'elles ne se melangent pas aux cibles francaises a l'affichage.
# `--france` restreint quand il veut le contraire.
MONDE = True


def en_france(lieu):
    """Le poste est-il en France (ou a distance) ?

    Rend toujours True quand MONDE est actif : la recherche mondiale ne filtre
    plus sur le lieu.

    Un lieu VIDE passe : beaucoup d'annonces francaises n'en renseignent aucun,
    et refuser sur une absence d'information ecarterait de vraies offres.

    Un lieu RENSEIGNE qui ne parle ni de France ni d'un pays connu passait aussi,
    par defaut. C'etait trop permissif : « Mexico City », « Reston, VA » et
    « Aurora, CO » entraient. Un lieu explicite doit desormais porter un signal
    francais ou rester tres court (« fr », un code postal, un nom de ville isole
    qu'on ne saurait pas classer).
    """
    if MONDE:
        return True
    t = str(lieu or "").strip()
    if not t:
        return True
    if _RX_FR.search(t):
        return True
    if _RX_ETAT_US.search(t) or _RX_ETRANGER.search(t):
        return False
    # Lieu explicite, non reconnu : on ne l'accepte que s'il est trop court pour
    # designer un pays etranger (« 33 », « Sud-Ouest »). Un « Mexico City » ou un
    # « Reston, VA » comporte une virgule ou plusieurs mots : on refuse.
    return not ("," in t or len(t.split()) > 1)


def merge_into_queue(fresh, dry=False, attente=180):
    """Fusionne `fresh` dans la file. Lecture-modification-ECRITURE : sous verrou.

    `main()` prend deja le verrou pour tout le processus (`jutil.garder`), et
    c'est le chemin normal. Mais cette fonction s'appelle aussi seule — depuis
    les tests, depuis l'app, depuis un autre programme — et elle s'executait
    alors a decouvert : relire la file, la transformer, puis la reecrire en
    entier sans verrou efface ce qu'un autre programme a ecrit entre-temps.
    On le prend si personne ne le tient, et on ne rend QUE ce qu'on a pris.
    """
    from ats_match import fit_detail, score_offer
    import queue_io, jutil

    a_nous = not dry and not jutil.tenu(QUEUE)
    if a_nous and not jutil.prendre_verrou(QUEUE, attente=attente):
        raise queue_io.VerrouIndisponible(
            f"{QUEUE.name} est modifié par un autre programme — rien n'a été fusionné."
        )
    try:
        return _merge_into_queue(fresh, dry, fit_detail, score_offer, queue_io)
    finally:
        if a_nous:
            jutil.rendre_verrou(QUEUE)


def _merge_into_queue(fresh, dry, fit_detail, score_offer, queue_io):
    # QUEUE explicite : les tests remplacent cette constante par un fichier
    # jetable. Sans elle, charger() lirait la vraie file.
    q = queue_io.charger(QUEUE)  # descriptions reinjectees depuis descriptions.json
    # PURGE bruit : rows 'Scan' déjà mergées dont le titre échoue le nouveau filtre anti-bruit
    before = len(q)
    q = [
        x
        for x in q
        if not (str(x.get("statut", "")).startswith("Scan ") and not title_ok(x.get("poste", "")))
    ]
    purged = before - len(q)
    idx = {_norm(x.get("entreprise", "")) + "|" + _norm(x.get("poste", "")): x for x in q}
    have_url = {_norm_url(x.get("url")) for x in q if x.get("url")}
    par_url = {_norm_url(x.get("url")): x for x in q if x.get("url")}
    today = time.strftime("%Y-%m-%d")
    added = updated = promus = hors_zone = pays_ecartes = 0
    _EXCLUS = contrats_exclus()
    _RX_PAYS = _rx_pays_exclus()
    # Offres ECARTEES a la main. Supprimer une offre ne la tue pas : le scan la
    # retrouve a la source et la reajoute le lendemain. Le refus doit tenir.
    import exclusions as _exc

    _REFUSEES = _exc.charger()
    # Offres RETIREES PAR LE TRI. Le tri juge sur la description, que la collecte
    # n'a pas encore : sans cette memoire, 1157 offres retirees a midi revenaient
    # le soir comme nouvelles (2026-10-05). Voir rejets_tri.py.
    import rejets_tri as _rej

    _REJ_TRI = _rej.charger(REJETS_TRI)
    ecartees = rejetees_tri = 0
    for o in fresh:
        # Hors de France : on n'ajoute pas. Voir en_france() — un flux ATS porte
        # le nom de la societe, pas son pays.
        if not en_france(o.get("location")):
            hors_zone += 1
            continue
        # PAYS ECARTES. Voir pays_exclus() : une purge de la file ne tient pas,
        # le scan reajoute le lendemain ce qu'on a supprime la veille.
        #
        # LES V.I.E EN SONT EXEMPTS. Le refus du Royaume-Uni et de la Belgique
        # vise les employeurs LOCAUX ; un V.I.E reste un contrat francais, paye
        # en euros, encadre par Business France, dans une filiale d'un groupe
        # francais. Mesure du 2026-09-22 : le filtre ecartait 35 V.I.E, dont
        # ArcelorMittal Bruxelles « Environment & CO2 data » et Bostik Stafford
        # « Sustainability data », toutes deux a fit 10. La Belgique est meme le
        # premier pays V.I.E, avec 32 offres sur 143.
        if _RX_PAYS and not _est_vie(o) and _RX_PAYS.search(str(o.get("location") or "")):
            pays_ecartes += 1
            continue
        # Meme cle que queue_io.oid : « entreprise|poste », non normalisee.
        if f"{o['entreprise'].strip()}|{o['titre'].strip()}" in _REFUSEES:
            ecartees += 1
            continue
        key = _norm(o["entreprise"]) + "|" + _norm(o["titre"])
        if key not in idx and f"{o['entreprise'].strip()}|{o['titre'].strip()}" in _REJ_TRI:
            rejetees_tri += 1
            continue
        desc = (o.get("description") or "").strip()
        if key in idx or _norm_url(o["url"]) in have_url:
            # déjà en queue : si on a maintenant une description et pas elle → enrichit + re-score
            x = idx.get(key)
            # PROMOTION D'URL. La meme annonce arrive de plusieurs sources ; la
            # premiere vue gagnait, au hasard de l'ordre des scans. Si celle-ci
            # vient d'une meilleure source, elle remplace l'ancienne : on garde
            # le lien ou l'utilisateur peut lire l'offre ET postuler.
            if x is not None and rang_source(o.get("url")) > rang_source(x.get("url")):
                x["url"] = o["url"]
                x["source"] = o.get("source", x.get("source", ""))
                u_ = o["url"].lower()
                x["canal"] = (
                    "manuel"
                    if ("linkedin.com" in u_ or "indeed." in u_ or "welcometothejungle" in u_)
                    else "auto"
                )
                x["site_kind"] = "board" if x["canal"] == "manuel" else "entreprise"
                x["link_status"] = "OK"
                have_url.add(_norm_url(o["url"]))
                promus += 1
                # La description SUIT le lien. Deux sources publient la meme
                # annonce mais pas le meme texte : LinkedIn sert la prose, le
                # site d'origine y ajoute le cadre (contrat, diplome, niveau
                # d'experience). CNP « EXPERT INVESTISSEMENT RESPONSABLE » en
                # est l'exemple : la version LinkedIn ne dit rien du niveau,
                # celle d'eFinancialCareers exige « Plus de 10 ans ». L'offre
                # est restee a fit 10 avec exp_requise = 0 — le detecteur
                # d'experience marche, il n'avait simplement jamais lu la
                # phrase. Sans ce remplacement, promouvoir le lien laissait le
                # texte de la source la moins informative.
                #
                # MAIS une source peut etre meilleure pour le LIEN et moins
                # bonne pour le TEXTE. Indeed en est le cas : son lien vaut
                # mieux que celui de LinkedIn, alors qu'elle ne livre qu'un
                # resume de 160 caracteres. Sans cette garde, promouvoir le
                # lien detruisait une annonce complete pour la remplacer par
                # trois lignes, et fit_score rescorait sur ce qui restait.
                if desc and o.get("desc_partielle") and (x.get("description") or "").strip():
                    desc = ""
                if desc:
                    x["description"] = desc
                    x["fit"], x["exp_requise"], x["fit_fin"] = fit_detail(
                        f"{x.get('poste', '')} {desc}", x.get("poste", "")
                    )
            if x is not None and desc and not (x.get("description") or "").strip():
                x["description"] = desc
                x["fit"], x["exp_requise"], x["fit_fin"] = fit_detail(
                    f"{x.get('poste', '')} {desc}", x.get("poste", "")
                )
                try:
                    x["ats_pct"] = score_offer(
                        dict(
                            role=x.get("poste", ""),
                            missions=desc,
                            profil="",
                            domaine=x.get("domaine", ""),
                        )
                    ).get("pct")
                except Exception:
                    pass
                updated += 1
            # LE CADRE — contrat, teletravail, salaire, date de parution. Une
            # source peut etre mediocre pour le texte et excellente pour ces
            # champs-la : Indeed les sert structures (15/15 des cartes portent
            # un type de contrat) quand nos autres sources obligent a les
            # deviner dans la prose. On ne REMPLACE jamais une valeur posee, on
            # ne comble que les trous — et « non precise » est un trou, c'est
            # ce que le detecteur ecrit quand il n'a rien trouve.
            # VU_LE : la derniere fois qu'une source a de nouveau servi l'offre.
            # Pour APEC, Glassdoor, Indeed, la page de l'offre refuse les robots
            # et ne peut pas dire si l'offre vit encore ; le canal qui l'a
            # trouvee, lui, la ressert tant qu'elle est en ligne. audit_dispo
            # s'en sert pour retirer ce que sa source a cesse de publier.
            # Rattachement par URL aussi : un doublon reconnu au lien seul
            # (meme annonce, intitule retouche) doit compter comme revu.
            if x is None:
                x = par_url.get(_norm_url(o["url"]))
            if x is not None:
                x["vu_le"] = today
            if x is not None:
                if o.get("contrat") and (x.get("contrat") or "") in ("", "non precise"):
                    x["contrat"] = o["contrat"]
                for champ in ("teletravail", "salaire", "date_publication"):
                    v = o.get("date" if champ == "date_publication" else champ)
                    if v and not str(x.get(champ) or "").strip():
                        x[champ] = v
            continue
        have_url.add(_norm_url(o["url"]))
        u = o["url"].lower()
        canal = (
            "manuel"
            if ("linkedin.com" in u or "indeed." in u or "welcometothejungle" in u)
            else "auto"
        )
        # Contrat exclu : on n'ajoute meme pas. l'utilisateur n'est pas etudiant ;
        # inutile de faire entrer des alternances et des stages pour les
        # masquer ensuite a l'affichage.
        # Un contrat ANNONCE par la source passe avant tout ce qu'on pourrait
        # lire dans le titre ou la prose : Indeed publie `jobTypes` en clair,
        # la deduction n'a plus lieu d'etre.
        _ctr = o.get("contrat") or contrat_du_titre(o["titre"], o.get("source", ""))
        # Le titre ne dit rien dans 45 % des cas : la description, si. On ne
        # DEDUIT jamais un contrat absent — « non precise » est une reponse.
        # Un resume de 160 caracteres ne suffit pas a trancher : on ne l'y
        # cherche pas.
        if not _ctr and not o.get("desc_partielle"):
            _ctr = contrat_de_la_description(desc, "non precise")
        _ctr = _ctr or "non precise"
        if _ctr in _EXCLUS:
            continue
        # scoring sur titre + DESCRIPTION (les APIs ATS la fournissent au scan)
        fit, yrs, fin = fit_detail(f"{o['titre']} {desc}", o["titre"])
        try:
            ats = score_offer(
                dict(role=o["titre"], missions=desc, profil="", domaine=o["domaine"])
            ).get("pct")
        except Exception:
            ats = None
        ligne = {
            "entreprise": o["entreprise"],
            "poste": o["titre"],
            "domaine": o["domaine"],
            "statut": f"Scan {today}",
            "url": o["url"],
            "cv": None,
            "lettre": None,
            "rh": None,
            "cv_variant": None,
            "url_type": "OFFRE_DIRECTE",
            "site_kind": "board" if canal == "manuel" else "entreprise",
            "fit": fit,
            "fit_fin": fin,
            "exp_requise": yrs,
            "action": "",
            "contrat": _ctr,
            # Lieu de l'INTITULE s'il nomme une ville etrangere (zones.lieu_effectif) :
            # Talent et Glassdoor donnent parfois le siege, « Paris », a un V.I.E New York.
            "localisation": __import__("zones").lieu_effectif(
                o.get("location", ""), o.get("titre", "")
            ),
            # Zone geographique, calculee a l'ajout : sans ca, chaque nouvelle
            # offre arriverait sans zone et la colonne de l'app se remplirait de
            # trous jusqu'au prochain passage de zones.py.
            "zone": __import__("zones").zone_lieu(
                __import__("zones").lieu_effectif(o.get("location", ""), o.get("titre", ""))
            ),
            "teletravail": o.get("teletravail", ""),
            "salaire": o.get("salaire", ""),
            "profil": "",
            "pourquoi": "",
            "process": o.get("date") or today,
            # `process` melange depuis toujours la date de parution et celle du
            # scan : sur 5911 offres, 2634 portent le meme jour, celui ou on les
            # a vues. Impossible d'y distinguer l'une de l'autre apres coup, on
            # ne va donc pas l'ecraser. La date CERTAINE va dans son propre
            # champ, vide quand la source ne la donne pas.
            "date_publication": o.get("date") or "",
            "source": o.get("source", ""),
            "missions": "",
            "skills_match": 0,
            "ats_pct": ats,
            "canal": canal,
            "is_stage": False,
            "priorite": "prio" if fit >= 7 else "normal",
            "link_status": "OK",
            "description": desc,
            "vu_le": today,
        }
        q.append(ligne)
        # INDEXER LA LIGNE, PAS L'OFFRE BRUTE. `idx[key] = o` rangeait le dict
        # du scan, alors que la file recoit un dict DIFFERENT : toute promotion
        # d'URL ou description arrivant plus tard dans le MEME lot s'ecrivait
        # sur l'orphelin. Le compteur annoncait « promus: 1 » et la file gardait
        # le lien LinkedIn et sa description vide. C'est le cas NORMAL — un
        # `--all` enchaine ATS, LinkedIn, WTJ, eFC et Indeed sur la meme annonce.
        idx[key] = ligne
        par_url[_norm_url(o["url"])] = ligne
        added += 1
    if not dry:
        __import__("jutil").jwrite(QUEUE, q)
    return dict(
        added=added,
        updated=updated,
        promus=promus,
        purged=purged,
        hors_zone=hors_zone,
        ecartees=ecartees,
        rejetees_tri=rejetees_tri,
        pays_ecartes=pays_ecartes,
        total=len(q),
    )


# ═══════════════ 4. V.I.E / V.I.A — Business France (civiweb) ═══════════════
# Le site mon-vie-via est une SPA Nuxt : le HTML brut est une coquille vide, mais
# sa config publique (window.__NUXT__.config) livre l'endpoint et une clé d'API
# expédiée à TOUT visiteur. Elle ne donne accès qu'aux offres PUBLIQUES, les mêmes
# que la page affiche sans compte — pas de login, pas de données personnelles.
# En-tête attendu : x-api-key (Authorization et apikey renvoient 401).
VIE_API = "https://civiweb-api-prd.azurewebsites.net/api/Offers/search"
VIE_SITE = "https://mon-vie-via.businessfrance.fr/offres/recherche"
VIE_BASE = "https://mon-vie-via.businessfrance.fr"
_VIE_KEY_FALLBACK = "l+KwpoLPiXlsjxNT/NQ2iOFz8+iuygxAODs9FeAEWYM="


def _vie_key():
    """Clé lue en direct dans la config publique du site ; le fallback évite de
    tout casser si la page change, mais une clé figée finira par tourner.

    Deux pièges vérifiés :
      - la clé est échappée dans le HTML (`\\u002F` pour `/`) → à décoder, sinon 401 ;
      - « API_KEY » matche aussi GMAPS_API_KEY (clé Google Maps) → ancrer le nom.
    """
    import httpx

    try:
        r = _get_borne(httpx, VIE_SITE, timeout=15, headers=UA, follow_redirects=True)
        m = re.search(r'(?:^|[^_A-Z])API_KEY\s*:\s*"([^"]{20,})"', r.text)
        if m:
            k = m.group(1).encode().decode("unicode_escape")
            if k.endswith("="):  # la clé civiweb est du base64
                return k
    except Exception:
        pass
    return _VIE_KEY_FALLBACK


def fetch_vie(limit=1000):
    """Offres V.I.E/V.I.A. Intérêt pour un profil junior : contrat 12-24 mois,
    indemnité nette, et beaucoup de postes finance/ESG en filiale à l'étranger."""
    import httpx

    key = _vie_key()
    H = {**UA, "Content-Type": "application/json", "Accept": "application/json", "x-api-key": key}
    out, skip = [], 0
    while len(out) < limit:
        try:
            r = _post_borne(
                httpx, VIE_API, json={"limit": 100, "skip": skip}, timeout=30, headers=H
            )
            if r.status_code != 200:
                print(f"  ✗ VIE http {r.status_code} (clé rotée ? relancer probe)")
                break
            d = r.json()
        except Exception as e:
            print(f"  ✗ VIE {type(e).__name__}")
            break
        res = d.get("result") or []
        if not res:
            break
        for x in res:
            titre = str(x.get("missionTitle") or "").strip()
            if not title_ok(titre):
                continue
            pays = str(x.get("countryName") or "")
            ville = str(x.get("cityName") or "")
            ind = x.get("indemnite") or 0
            dur = x.get("missionDuration") or ""
            desc = "\n".join(
                filter(
                    None,
                    [
                        str(x.get("missionDescription") or ""),
                        "PROFIL : " + str(x.get("missionProfile") or ""),
                        f"[{x.get('missionType') or 'VIE'} · {dur} mois · indemnité {int(ind)} EUR/mois]",
                    ],
                )
            )
            # Lien PROFOND vers l'offre. `{VIE_SITE}?id=<id>` menait a la page de
            # RECHERCHE generique : le bouton Postuler n'ouvrait pas l'offre.
            # Le site lui-meme pointe vers /offres/<id> (verifie : la page rend
            # bien l'offre et son bouton POSTULER).
            out.append(
                _mk(
                    titre,
                    f"{VIE_BASE}/offres/{x.get('id')}",
                    str(x.get("organizationName") or "").strip() or "VIE",
                    f"{ville} ({pays})".strip(),
                    str(x.get("startBroadcastDate") or "")[:10],
                    f"vie:{x.get('reference') or x.get('id')}",
                    desc,
                )
            )
        skip += 100
        if skip >= (d.get("count") or 0):
            break
        time.sleep(0.3)
    return out


def scan_vie():
    o = fetch_vie()
    print(f"  ✓ V.I.E/V.I.A Business France → {len(o)} offres (après filtre métier)")
    return o


# ═══════════════ 5. FIR / French SIF — offres 100 % ISR-ESG ═══════════════
# Forum pour l'Investissement Responsable : tableau d'offres exclusivement ISR/ESG.
# Densite sans equivalent (LinkedIn ramene ~15 % de pertinent, ici c'est 100 %).
# ⚠ Seules les offres presentes dans le HTML sont lues (~5). Les onglets par
# categorie (emplois / alternance / stages) chargent en JS et /jobs_categories/<c>/
# renvoie 404 ; l'API REST WordPress est fermee (wp-json -> 404). Un scraping
# navigateur recupererait le reste, au prix d'un lancement de Chromium.
FIR_URL = "https://www.frenchsif.org/isr_esg/emplois-et-stages/"


def fetch_fir():
    import httpx, html as _html

    try:
        r = _get_borne(httpx, FIR_URL, timeout=25, headers=UA, follow_redirects=True)
        if r.status_code != 200:
            print(f"  ✗ FIR http {r.status_code}")
            return []
    except Exception as e:
        print(f"  ✗ FIR {type(e).__name__}")
        return []
    out = []
    for a in re.split(r'<article class="loop post-', r.text)[1:]:
        mu = re.search(r'href="(https://www\.frenchsif\.org/isr_esg/emploi-stage/[^"]+)"', a)
        mt = re.search(r'<span class="entry-title">(.*?)</span>', a, re.S)
        if not (mu and mt):
            continue
        titre = _html.unescape(re.sub(r"<[^>]+>", " ", mt.group(1))).strip()
        titre = re.sub(r"\s+", " ", titre)
        loc = re.search(r"Localisation\s*:?</strong>\s*([^<.]{2,40})", a)
        # Le contrat prefixe l'intitule (« CDI – Analyste ESG »). On le garde : il
        # porte une info utile (alternance/stage = cible junior).
        txt = _html.unescape(re.sub(r"<[^>]+>", " ", a))
        txt = re.sub(r"\s+", " ", txt).strip()[:8000]
        if not title_ok(titre):
            continue
        out.append(
            _mk(
                titre,
                mu.group(1),
                "FIR (French SIF)",
                (loc.group(1).strip() if loc else ""),
                "",
                "fir",
                txt,
            )
        )
    return out


def scan_fir():
    o = fetch_fir()
    print(f"  ✓ FIR / French SIF → {len(o)} offres (100 % ISR-ESG)")
    return o


# ═══════════════ 6. Talent.com — agregateur (remplace la couverture Indeed) ══════
# Indeed est INACCESSIBLE : Cloudflare bloque au niveau IP/empreinte TLS, y compris
# en fenetre reelle avec patchright+stealth (teste). Contourner une protection
# anti-bot est hors de question ; Talent.com agrege un vivier comparable et expose
# du JSON-LD schema.org propre, avec la DESCRIPTION incluse (elle manque a 755
# offres de la queue, dont la quasi-totalite vient d'Indeed).
#
# Cout : 1 requete de recherche + 1 par offre retenue. Le filtre title_ok est
# applique AVANT d'aller chercher le detail, pour ne pas payer les hors-sujet.
TALENT_SEARCH = "https://fr.talent.com/jobs?k={kw}&l=France"
_TALENT_LINK_RX = re.compile(r'href="(/view\?id=\d+)"')


_CLIENT_PARTAGE = None


def _client_partage():
    """Un httpx.Client unique, qui GARDE SES CONNEXIONS OUVERTES.

    POURQUOI. Appeler `httpx.get` rouvre une connexion TLS a chaque requete.
    Mesure le 2026-10-02 : 4 appels SmartRecruiters en 13,7 s par le module,
    4,5 s par un client ; Workday 14,3 s contre 5,4. Sur une collecte de
    plusieurs centaines d'appels, c'etait l'essentiel du temps : talan seul
    prenait 8 min (69 fiches), chaque flux Workday 6 a 8 — et la passe a
    depassait ses 60 min avant d'atteindre LinkedIn."""
    global _CLIENT_PARTAGE
    if _CLIENT_PARTAGE is None:
        import httpx as _hx

        _CLIENT_PARTAGE = _hx.Client(
            limits=_hx.Limits(max_connections=20, max_keepalive_connections=20)
        )
    return _CLIENT_PARTAGE


def _req_borne(envoi, methode, url, total=None, max_octets=20_000_000, **kw):
    """Requete httpx avec une duree TOTALE maximale. Rend une vraie httpx.Response.

    `envoi` : le module httpx ou un httpx.Client — les deux ont `.stream()`.
    `total` : par defaut trois fois le delai par operation, 60 s au moins.

    Voir `_get_borne` pour le pourquoi. Generalisee le 2026-09-23 a toutes les
    sources : la premiere version ne protegeait que Talent.com, et rendait un
    objet sans `.json()`, ce qui interdisait de l'employer ailleurs.

    La Response est reconstruite SANS content-encoding : `iter_bytes` a deja
    decompresse le corps, et le laisser annonce gzip ferait decompresser deux
    fois."""
    import httpx as _hx

    if envoi is _hx:  # le module : pas de connexion reutilisee
        envoi = _client_partage()
    kw.setdefault("timeout", 20)
    t = kw["timeout"] if isinstance(kw["timeout"], (int, float)) else 20
    total = total or max(60, 3 * t)
    debut = time.time()
    with envoi.stream(methode, url, **kw) as r:
        blocs, taille = [], 0
        for bloc in r.iter_bytes():
            blocs.append(bloc)
            taille += len(bloc)
            if time.time() - debut > total:
                raise _hx.TimeoutException(f"plus de {total:.0f} s pour {url}")
            if taille > max_octets:
                raise _hx.TimeoutException(f"plus de {max_octets} octets pour {url}")
        tetes = [
            (k, v)
            for k, v in r.headers.multi_items()
            if k.lower() not in ("content-encoding", "content-length", "transfer-encoding")
        ]
        return _hx.Response(
            r.status_code, headers=tetes, content=b"".join(blocs), request=r.request
        )


def _post_borne(envoi, url, **kw):
    return _req_borne(envoi, "POST", url, **kw)


def _lire_borne(f, total=60, max_octets=20_000_000):
    """`f.read()` d'un urlopen, mais borne en duree TOTALE.

    `urlopen(timeout=25)` borne chaque operation de socket, exactement comme
    httpx : un serveur qui distille ses octets le tient indefiniment."""
    debut, blocs, taille = time.time(), [], 0
    # read1, PAS read(n) : read(65536) attend que les 64 Ko soient arrives avant
    # de rendre la main, donc la duree n'etait controlee qu'a la toute fin —
    # mesure : un serveur a un octet toutes les 0,3 s tenait la lecture 60 s
    # malgre total=3. read1 rend ce qui est deja la.
    lire = getattr(f, "read1", f.read)
    while True:
        bloc = lire(65536)
        if not bloc:
            return b"".join(blocs)
        blocs.append(bloc)
        taille += len(bloc)
        if time.time() - debut > total or taille > max_octets:
            raise TimeoutError(f"lecture de plus de {total} s ou {max_octets} octets")


def _get_borne(envoi, url, **kw):
    """GET avec une duree TOTALE maximale. Rend une vraie httpx.Response.

    POURQUOI. `timeout=20` dans httpx borne CHAQUE operation — connexion,
    lecture d'un paquet — pas la requete entiere. Un serveur qui envoie un
    octet toutes les 19 secondes garde donc la connexion ouverte pour toujours.
    Le 2026-09-22 a 22h49, le scan planifie s'est bloque ainsi sur fr.talent.com
    (3.175.86.19, CloudFront) : 12 h 25 de connexion etablie, 149 s de CPU, le
    verrou de la file tenu tout du long, et le delai de 90 min du pipeline, qui
    devait le tuer, n'a rien tue.

    Ici le temps ecoule est verifie a chaque paquet recu : au pire, total + 20 s.
    Leve httpx.TimeoutException au-dela, comme un delai ordinaire — les appelants
    qui attrapent deja `Exception` n'ont rien a changer."""
    return _req_borne(envoi, "GET", url, **kw)


def _talent_detail(httpx, url):
    """(titre, entreprise, lieu, date, description) depuis le JSON-LD JobPosting."""
    import json as _json, html as _html

    try:
        r = _get_borne(httpx, url, headers=UA, follow_redirects=True)
        if r.status_code != 200:
            return None
    except Exception:
        return None
    for b in re.findall(r'<script type="application/ld\+json">(.*?)</script>', r.text, re.S):
        try:
            d = _json.loads(b)
        except Exception:
            continue
        nodes = d.get("@graph") if isinstance(d, dict) and "@graph" in d else [d]
        for n in nodes:
            if not (isinstance(n, dict) and n.get("@type") == "JobPosting"):
                continue
            loc = ""
            jl = n.get("jobLocation")
            if isinstance(jl, dict):
                loc = str(((jl.get("address") or {}).get("addressLocality")) or "")
            desc = re.sub(r"<[^>]+>", " ", str(n.get("description") or ""))
            desc = re.sub(r"\s+", " ", _html.unescape(desc)).strip()
            return (
                str(n.get("title") or "").strip(),
                str((n.get("hiringOrganization") or {}).get("name") or "").strip(),
                loc,
                str(n.get("datePosted") or "")[:10],
                desc,
            )
    return None


def fetch_talent(max_days=60, per_kw=20):
    """Offres Talent.com pour chaque mot-cle. max_days ecarte les annonces
    anciennes : le site sert des offres de plus d'un an (vu : datePosted 2025-06)."""
    import httpx, datetime
    from urllib.parse import quote as _q

    today = datetime.date.today()
    out, seen = [], set()
    # LES OFFRES DEJA DANS LA FILE NE SONT PAS RECHARGEES. Chaque fiche coute une
    # requete, et la collecte rechargeait tous les jours les memes : 30 min pour
    # Talent seul le 30/09, dans une passe bornee a 60. Leur description est
    # deja la ; seule une offre nouvelle merite sa fiche.
    try:
        import queue_io

        seen = {
            str(o.get("url") or "")
            for o in queue_io.charger(descriptions=False)
            if "talent.com" in str(o.get("url") or "")
        }
    except Exception:
        seen = set()
    connues = len(seen)
    for kw in KEYWORDS:
        try:
            r = _get_borne(
                httpx, TALENT_SEARCH.format(kw=_q(kw)), headers=UA, follow_redirects=True
            )
            if r.status_code != 200:
                continue
        except Exception:
            continue
        links = list(dict.fromkeys(_TALENT_LINK_RX.findall(r.text)))[:per_kw]
        got = 0
        for href in links:
            u = "https://fr.talent.com" + href
            if u in seen:
                continue
            seen.add(u)
            d = _talent_detail(httpx, u)
            if not d:
                continue
            titre, ent, loc, date, desc = d
            if not title_ok(titre):
                continue
            if date:
                try:
                    if (today - datetime.date.fromisoformat(date)).days > max_days:
                        continue
                except Exception:
                    pass
            out.append(_mk(titre, u, ent or "Talent.com", loc, date, f"talent:{kw}", desc))
            got += 1
        if got:
            print(f"  ✓ talent «{kw}» → {got} offres")
        time.sleep(0.5)
    print(f"  Talent : {connues} offres deja dans la file, fiches non rechargees")
    return out


def scan_talent():
    o = fetch_talent()
    print(f"  ✓ Talent.com → {len(o)} offres (avec description)")
    return o


# ═══════════════ 7. France Travail — API OFFICIELLE (identifiants requis) ═══════
# Ex-Pole emploi : le plus gros gisement d'offres en France, API publique, gratuite,
# legale. Couvre tres largement ce qu'Indeed agrege, sans aucun contournement.
#
# ⚠ IDENTIFIANTS A CREER PAR L'UTILISATEUR (je ne cree pas de comptes) :
#   1. https://francetravail.io  ->  creer un compte, puis une application
#   2. souscrire a l'API « Offres d'emploi v2 »
#   3. copier client_id / client_secret dans Scripts/francetravail.json :
#        {"client_id": "...", "client_secret": "..."}
#      (fichier ignore par git : il contient un secret)
# Sans ce fichier, la source se desactive silencieusement.
FT_CFG = HERE / "francetravail.json"
FT_TOKEN_URL = (
    "https://entreprise.francetravail.fr/connexion/oauth2/access_token?realm=%2Fpartenaire"
)
FT_SEARCH = "https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search"


def _ft_token():
    import httpx, json as _json

    if not FT_CFG.exists():
        return None
    try:
        c = _json.loads(FT_CFG.read_text(encoding="utf-8"))
        r = _post_borne(
            httpx,
            FT_TOKEN_URL,
            timeout=20,
            data={
                "grant_type": "client_credentials",
                "client_id": c["client_id"],
                "client_secret": c["client_secret"],
                "scope": "api_offresdemploiv2 o2dsoffre",
            },
        )
        if r.status_code != 200:
            print(f"  ✗ France Travail token http {r.status_code} — verifie les identifiants")
            return None
        return r.json().get("access_token")
    except Exception as e:
        print(f"  ✗ France Travail token {type(e).__name__}")
        return None


def fetch_france_travail(par_mot=50):
    import httpx

    tok = _ft_token()
    if not tok:
        return []
    H = {**UA, "Authorization": f"Bearer {tok}", "Accept": "application/json"}
    out, seen = [], set()
    for kw in KEYWORDS:
        try:
            r = _get_borne(
                httpx,
                FT_SEARCH,
                timeout=25,
                headers=H,
                params={"motsCles": kw, "range": f"0-{par_mot - 1}"},
            )
            # 204 = aucun resultat, 206 = resultat partiel (pagination) : les deux OK
            if r.status_code not in (200, 206):
                continue
            res = r.json().get("resultats") or []
        except Exception:
            continue
        got = 0
        for j in res:
            u = (j.get("origineOffre") or {}).get(
                "urlOrigine"
            ) or f"https://candidat.francetravail.fr/offres/recherche/detail/{j.get('id')}"
            if u in seen:
                continue
            titre = str(j.get("intitule") or "").strip()
            if not title_ok(titre):
                continue
            seen.add(u)
            lieu = str((j.get("lieuTravail") or {}).get("libelle") or "")
            desc = str(j.get("description") or "")
            out.append(
                _mk(
                    titre,
                    u,
                    str((j.get("entreprise") or {}).get("nom") or "France Travail"),
                    lieu,
                    str(j.get("dateCreation") or "")[:10],
                    f"francetravail:{kw}",
                    desc,
                )
            )
            got += 1
        if got:
            print(f"  ✓ france-travail «{kw}» → {got} offres")
        time.sleep(0.3)
    return out


def scan_france_travail():
    o = fetch_france_travail()
    if not o and not FT_CFG.exists():
        print("  · France Travail ignore (Scripts/francetravail.json absent — voir le commentaire)")
    else:
        print(f"  ✓ France Travail → {len(o)} offres")
    return o


# ═══════════════ 8. Adzuna et Jooble — agregateurs, API officielles (cle requise) ═══
# POURQUOI. Indeed refuse tout depuis le 24/09 (403 a la premiere requete) et
# l'APEC est derriere DataDome depuis le 02/10. Adzuna et Jooble agregent les
# memes viviers — et beaucoup de petits sites — par une API officielle, avec
# une cle gratuite. Ce ne sont pas des sources nouvelles : ce sont des voies
# d'acces LEGITIMES a ce qu'Indeed ne laisse plus voir.
#
# ⚠ CLES A CREER PAR L'UTILISATEUR (je ne cree pas de comptes) :
#   Adzuna : https://developer.adzuna.com -> Scripts/adzuna.json
#            {"app_id": "...", "app_key": "..."}
#   Jooble : https://jooble.org/api/about -> Scripts/jooble.json
#            {"key": "..."}
# Fichiers ignores par git. Sans eux, la source se desactive en le disant.
#
# LA CLE NE S'AFFICHE JAMAIS. Adzuna la porte dans l'URL, Jooble dans le
# chemin : un message d'exception httpx contient l'URL. On n'imprime donc que
# le TYPE de l'exception, jamais son texte.
#
# LIMITES. Descriptions = extraits (desc_partielle : une meilleure source les
# remplace a la fusion). Liens = pages de redirection de l'agregateur, que la
# promotion d'URL remplace quand le vrai site arrive par une autre source.
ADZUNA_CFG = HERE / "adzuna.json"
JOOBLE_CFG = HERE / "jooble.json"
ADZUNA_API = "https://api.adzuna.com/v1/api/jobs/{pays}/search/1"
JOOBLE_API = "https://jooble.org/api/{cle}"
# Peu de mots, choisis : le quota gratuit d'Adzuna se compte en appels par jour,
# et un mot-cle x un pays = un appel. 12 + 6 x 7 = 54 appels par passe.
AGREG_MOTS_FR = [
    "analyste ESG",
    "finance durable",
    "investissement responsable",
    "ISR",
    "analyste financier junior",
    "analyste crédit",
    "risque climatique",
    "reporting extra-financier",
    "CSRD",
    "SFDR",
    "analyste private equity",
    "transition énergétique analyste",
]
AGREG_MOTS_EN = [
    "ESG analyst",
    "sustainable finance",
    "sustainability analyst",
    "responsible investment",
    "climate risk analyst",
    "graduate finance",
]
ADZUNA_PAYS = ("gb", "es", "de", "nl", "be", "ch", "it")
AGREG_PAUSE = 1.0
AGREG_ABANDON = 3  # refus d'entree d'affilee (cle refusee, blocage)
AGREG_REPOS_429 = 60  # une limite de debit s'attend ; deux fois au plus


def _cle(chemin, *champs):
    """Les champs du fichier de cle, ou None. Ne leve jamais, n'affiche rien de la cle."""
    import json as _json

    if not chemin.exists():
        return None
    try:
        c = _json.loads(chemin.read_text(encoding="utf-8"))
        return tuple(str(c[k]) for k in champs)
    except Exception as e:
        print(f"  ✗ {chemin.name} illisible ({type(e).__name__}) — attendu : {', '.join(champs)}")
        return None


class _Garde:
    """Compte les refus d'une source : 429 -> pause puis reprise, refus d'entree -> arret."""

    def __init__(self, nom):
        self.nom, self.refus, self.repos, self.fini = nom, 0, 0, False

    def reponse(self, r):
        """True si la reponse est exploitable. Gere pauses et abandon."""
        if r.status_code == 429:
            INCIDENTS[self.nom]["HTTP 429"] += 1
            if self.repos >= 2:
                print(f"  ⏸ {self.nom} : limite de debit persistante — arret de la source")
                self.fini = True
                return False
            self.repos += 1
            print(f"  ⏸ {self.nom} : limite de debit (429) — pause {AGREG_REPOS_429} s")
            time.sleep(AGREG_REPOS_429)
            return False
        if r.status_code in (401, 403):
            INCIDENTS[self.nom][f"HTTP {r.status_code}"] += 1
            self.refus += 1
            if self.refus >= AGREG_ABANDON:
                print(
                    f"  ⏸ {self.nom} : {self.refus} refus d'affilee (HTTP {r.status_code}) — "
                    f"cle refusee ou acces bloque, arret de la source"
                )
                self.fini = True
            return False
        if r.status_code != 200:
            INCIDENTS[self.nom][f"HTTP {r.status_code}"] += 1
            return False
        self.refus = 0
        return True


_ADZUNA_CONTRAT = {"permanent": "CDI", "contract": "CDD"}


def _agreg_offre(titre, url, entreprise, lieu, date, source, extrait, contrat, _EX):
    titre = (titre or "").strip()
    if not titre or not url or not title_ok(titre):
        return None
    ctr = contrat_du_titre(titre) or contrat or ""
    if ctr and ctr in _EX:
        return None
    o = _mk(
        titre,
        url,
        entreprise or source.split(":")[0].title(),
        lieu or "",
        str(date or "")[:10],
        source,
        _strip_html(extrait or ""),
    )
    o["desc_partielle"] = True
    if ctr:
        o["contrat"] = ctr
    return o


def scan_adzuna():
    import httpx

    cle = _cle(ADZUNA_CFG, "app_id", "app_key")
    if not cle:
        print("  · Adzuna ignore (Scripts/adzuna.json absent — voir le commentaire)")
        return []
    app_id, app_key = cle
    _EX = contrats_exclus()
    garde, out, vus = _Garde("adzuna"), [], set()
    requetes = [("fr", m) for m in AGREG_MOTS_FR] + [
        (p, m) for p in ADZUNA_PAYS for m in AGREG_MOTS_EN
    ]
    faites = 0
    for pays, mot in requetes:
        if garde.fini:
            break
        if faites:
            time.sleep(AGREG_PAUSE)
        faites += 1
        try:
            r = _get_borne(
                httpx,
                ADZUNA_API.format(pays=pays),
                timeout=25,
                headers=UA,
                params={
                    "app_id": app_id,
                    "app_key": app_key,
                    "what": mot,
                    "results_per_page": 50,
                    "max_days_old": 30,
                    "content-type": "application/json",
                },
            )
        except Exception as e:
            INCIDENTS["adzuna"][type(e).__name__] += 1
            continue
        if not garde.reponse(r):
            continue
        try:
            res = r.json().get("results") or []
        except ValueError:
            continue
        for j in res:
            u = j.get("redirect_url") or ""
            if not u or u in vus:
                continue
            vus.add(u)
            o = _agreg_offre(
                j.get("title"),
                u,
                (j.get("company") or {}).get("display_name"),
                (j.get("location") or {}).get("display_name"),
                j.get("created"),
                f"adzuna:{pays}",
                j.get("description"),
                _ADZUNA_CONTRAT.get(j.get("contract_type") or ""),
                _EX,
            )
            if o:
                out.append(o)
    print(f"  ✓ Adzuna → {len(out)} offres sur {faites} requetes (extraits, liens Adzuna)")
    return out


def scan_jooble():
    import httpx

    cle = _cle(JOOBLE_CFG, "key")
    if not cle:
        print("  · Jooble ignore (Scripts/jooble.json absent — voir le commentaire)")
        return []
    _EX = contrats_exclus()
    garde, out, vus = _Garde("jooble"), [], set()
    faites = 0
    for mot in AGREG_MOTS_FR:
        if garde.fini:
            break
        if faites:
            time.sleep(AGREG_PAUSE)
        faites += 1
        try:
            r = _post_borne(
                httpx,
                JOOBLE_API.format(cle=cle[0]),
                timeout=25,
                headers={**UA, "Content-Type": "application/json"},
                json={"keywords": mot, "location": "France", "page": "1"},
            )
        except Exception as e:
            INCIDENTS["jooble"][type(e).__name__] += 1
            continue
        if not garde.reponse(r):
            continue
        try:
            res = r.json().get("jobs") or []
        except ValueError:
            continue
        for j in res:
            u = j.get("link") or ""
            if not u or u in vus:
                continue
            vus.add(u)
            typ = str(j.get("type") or "")
            ctr = "CDI" if "CDI" in typ else "CDD" if "CDD" in typ else ""
            o = _agreg_offre(
                j.get("title"),
                u,
                j.get("company"),
                j.get("location"),
                j.get("updated"),
                "jooble",
                j.get("snippet"),
                ctr,
                _EX,
            )
            if o:
                out.append(o)
    print(f"  ✓ Jooble → {len(out)} offres sur {faites} requetes (extraits, liens Jooble)")
    return out


def main():
    _load_cfg()  # sources éditées depuis l'app
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--ats", action="store_true")
    ap.add_argument(
        "--workday",
        action="store_true",
        help="flux Workday publics (Eiffage, Ardian, Lombard Odier)",
    )
    ap.add_argument("--linkedin", action="store_true")
    ap.add_argument("--wtj", action="store_true")
    ap.add_argument("--vie", action="store_true")
    ap.add_argument("--fir", action="store_true")
    ap.add_argument("--talent", action="store_true")
    ap.add_argument(
        "--indeed",
        action="store_true",
        help="Indeed : page 1 des resultats (15 offres par requete)",
    )
    ap.add_argument(
        "--indeed-lieux",
        default=",".join(INDEED_LIEUX),
        help="villes Indeed, separees par des virgules",
    )
    ap.add_argument(
        "--glassdoor",
        action="store_true",
        help="Glassdoor : page 1 de la recherche (30 offres par mot-cle)",
    )
    ap.add_argument(
        "--apec", action="store_true", help="APEC : API publique, description entiere dans la liste"
    )
    ap.add_argument("--ft", action="store_true", help="France Travail (API officielle)")
    ap.add_argument(
        "--adzuna",
        action="store_true",
        help="Adzuna (API officielle, cle dans Scripts/adzuna.json)",
    )
    ap.add_argument(
        "--jooble",
        action="store_true",
        help="Jooble (API officielle, cle dans Scripts/jooble.json)",
    )
    ap.add_argument(
        "--efc", action="store_true", help="eFinancialCareers (sitemap public, crawl-delay 10 s)"
    )
    ap.add_argument(
        "--efc-graduate", action="store_true", help="eFC : programmes jeunes diplomes et V.I.E"
    )
    ap.add_argument(
        "--efc-tout", action="store_true", help="eFC sans le filtre ESG : ~2400 titres, tres long"
    )
    ap.add_argument(
        "--efc-metier",
        action="store_true",
        help="eFC : intitules compatibles avec le profil (869 sur 8478)",
    )
    ap.add_argument(
        "--efc-sites",
        default="fr",
        help="sites eFC a lire : fr, com, co.uk, de, ch, nl, lu, ie, sg "
        "(separes par des virgules) ou « monde » pour les neuf",
    )
    ap.add_argument(
        "--eures",
        action="store_true",
        help="EURES, portail officiel de l'UE (API publique, crawl-delay 10 s)",
    )
    ap.add_argument(
        "--efc-limite",
        type=int,
        default=40,
        help="nombre de fiches eFC lues par passe (10 s chacune)",
    )
    ap.add_argument("--pages", type=int, default=2)
    ap.add_argument(
        "--days", type=int, default=7, help="fraicheur LinkedIn en jours (31 = rattraper un mois)"
    )
    ap.add_argument("--dry", action="store_true")
    ap.add_argument(
        "--monde",
        action="store_true",
        help="sans effet, c'est le defaut (garde pour compatibilite)",
    )
    ap.add_argument(
        "--france",
        action="store_true",
        help="ne garder QUE les offres en France (annule le defaut mondial)",
    )
    ap.add_argument(
        "--fusion-seule",
        action="store_true",
        help="refusionne le dernier scan (offres_scan.json) sans rien collecter",
    )
    a = ap.parse_args()

    # DEUX VERROUS, DEUX ROLES. Il n'y en avait qu'un, sur la FILE, pris au
    # demarrage et garde toute la collecte — plus d'une heure en --all. Le
    # 2026-09-22 au soir, le scan planifie a ainsi bloque une purge deja
    # verifiee pendant toute sa duree, alors qu'il n'ecrit dans la file qu'a la
    # toute fin. Ce verrou jouait en fait deux roles :
    #
    #   1. proteger la file — c'est le travail de merge_into_queue, qui prend
    #      lui-meme le verrou et relit la file A L'INTERIEUR. Quelques secondes.
    #   2. empecher deux scans en parallele — ils se partageraient le quota des
    #      sources et s'ecraseraient mutuellement offres_scan.json.
    #
    # Le role 2 passe sur un verrou a part, pose sur offres_scan.json. La file
    # reste libre pendant la collecte.
    #
    # APRES argparse, et pas avant : `--help` et `--dry`, qui n'ecrivent rien,
    # ne doivent rien bloquer.
    import jutil

    if not a.dry and not jutil.garder(FRESH):
        return 3

    if a.fusion_seule:
        return _fusionner(json.loads(FRESH.read_text(encoding="utf-8")), a.dry)
    if a.france:
        globals()["MONDE"] = False
        print("── recherche restreinte à la FRANCE ──")
    # --efc et --efc-tout comptent comme une source demandee. Sans eux dans
    # cette liste, `--efc` seul retombait sur a.all = True et relancait TOUT le
    # scan quotidien avant d'arriver a eFC.
    if not (
        a.all
        or a.ats
        or a.workday
        or a.linkedin
        or a.wtj
        or a.vie
        or a.fir
        or a.talent
        or a.ft
        or a.efc
        or a.efc_tout
        or a.efc_graduate
        or a.efc_metier
        or a.indeed
        or a.glassdoor
        or a.apec
        or a.eures
        or a.adzuna
        or a.jooble
    ):
        a.all = True

    fresh = []
    if a.all or a.ats:
        print("── ATS APIs (greenhouse/lever/ashby/recruitee/smartrecruiters) ──")
        fresh += scan_ats()
    if a.all or a.workday:
        print("── Workday (API publique des grands groupes) ──")
        fresh += scan_workday()
    if a.all or a.linkedin:
        print("── LinkedIn recherche publique (guest) ──")
        fresh += scan_linkedin(pages=a.pages, days=a.days)
    if a.all or a.vie:
        print("── V.I.E / V.I.A (Business France) ──")
        fresh += scan_vie()
    if a.all or a.fir:
        print("── FIR / French SIF (100 % ISR-ESG) ──")
        fresh += scan_fir()
    # TALENT ET INDEED HORS DE --all (2026-10-03). Talent : 0 offre en 30 min le
    # 30/09, 3 le 27/09. Indeed : 403 a la premiere requete depuis le 24/09.
    # Ils restent lancables a la main (--talent, --indeed) pour verifier s'ils
    # reviennent ; Adzuna et Jooble couvrent le meme vivier par une API.
    if a.talent:
        print("── Talent.com (agrégateur) ──")
        fresh += scan_talent()
    if a.indeed:
        print("── Indeed (page 1 des résultats — voir le commentaire de scan_indeed) ──")
        fresh += scan_indeed(
            lieux=[v.strip() for v in a.indeed_lieux.split(",") if v.strip()], persist=not a.dry
        )
    if a.all or a.apec:
        print("── APEC (API publique, annonce entière dans la liste) ──")
        fresh += scan_apec()
    if a.all or a.glassdoor:
        print("── Glassdoor (page 1 de la recherche, France entière) ──")
        fresh += scan_glassdoor()
    # eFC dans --all, mais BORNE : filtre ESG, les neuf sites, 30 fiches au
    # plus (les fiches deja en file sont sautees, donc chaque jour avance dans
    # le reste). Neuf sitemaps + 30 fiches a 10 s font ~6 min. Les filtres
    # larges (--efc-metier, --efc-tout) restent a lancer a part, par passes.
    if a.all or a.efc or a.efc_tout or a.efc_graduate or a.efc_metier:
        filtre = (
            "tout"
            if a.efc_tout
            else "graduate"
            if a.efc_graduate
            else "metier"
            if a.efc_metier
            else "esg"
        )
        sites = (
            EFC_SITES
            if (a.all and not a.efc) or a.efc_sites == "monde"
            else tuple(x.strip() for x in a.efc_sites.split(",") if x.strip())
        )
        limite = 30 if (a.all and not a.efc) else a.efc_limite
        print(
            f"── eFinancialCareers ({filtre}, {len(sites)} site(s), sitemap public, crawl-delay 10 s) ──"
        )
        fresh += scan_efc(limit=limite, filtre=filtre, sites=sites)
    if a.all or a.eures:
        print("── EURES (portail officiel UE, API publique, crawl-delay 10 s) ──")
        fresh += scan_eures()
    if a.all or a.ft:
        print("── France Travail (API officielle) ──")
        fresh += scan_france_travail()
    if a.all or a.adzuna:
        print("── Adzuna (API officielle, France + 7 pays) ──")
        fresh += scan_adzuna()
    if a.all or a.jooble:
        print("── Jooble (API officielle) ──")
        fresh += scan_jooble()
    if a.all or a.wtj:
        print("── Welcome to the Jungle (sitemap public, débit bridé) ──")
        fresh += scan_wtj(pages=a.pages)

    # dédup interne du scan
    seen, uniq = set(), []
    for o in fresh:
        k = _norm(o["entreprise"]) + "|" + _norm(o["titre"])
        if k in seen:
            continue
        seen.add(k)
        uniq.append(o)
    # --dry n'ecrit RIEN, pas meme le scan : il ne tient pas le verrou de
    # offres_scan.json, et l'ecraser pendant qu'un vrai scan le detient ruinait
    # le `--fusion-seule` de ce dernier. Vu le 2026-09-23 sur un --apec --dry.
    if not a.dry:
        FRESH.write_text(json.dumps(uniq, ensure_ascii=False, indent=1), encoding="utf-8")
    print(
        f"\nScan : {len(uniq)} offres uniques"
        + (" (non ecrit : --dry)" if a.dry else f" (→ {FRESH.name})")
    )

    # LES REFUS, AVANT LE BILAN. Sans ca, un scan bride de bout en bout affiche
    # le meme « 0 offres » qu'une journee sans nouveaute, et on relance — ce qui
    # est exactement ce qu'il ne faut pas faire face a un quota.
    refus = incidents_resume()
    if refus:
        print("\nRefus rencontrés (une collecte vide peut venir de là) :")
        for l in refus:
            print(l)

    code = _fusionner(uniq, a.dry)
    # La fusion reste prioritaire ; une source Indeed dégradée n'est pas un succès.
    return code or (4 if a.indeed and INCIDENTS.get("indeed") else 0)


def _fusionner(uniq, dry):
    """Fusionne le scan dans la file. Rend un code de sortie.

    Le verrou de la file n'est pris QU'ICI. Si un autre programme l'occupe, on
    attend jusqu'a 30 minutes : ce qui precede a coute une heure de reseau, et
    abandonner au bout de 3 minutes, comme par defaut, le jetterait. Si
    l'attente echoue quand meme, rien n'est perdu — le scan est deja dans
    offres_scan.json, et `--fusion-seule` le refusionne sans rien recollecter."""
    import queue_io

    try:
        r = merge_into_queue(uniq, dry=dry, attente=1800)
    except queue_io.VerrouIndisponible as e:
        print(f"! {e}")
        print(
            f"  Le scan est conserve dans {FRESH.name} : "
            f"`python job_sources.py --fusion-seule` le fusionnera."
        )
        return 3
    print(
        f"Merge {'[DRY] ' if dry else ''}: +{r['added']} nouvelles, {r['updated']} enrichies (desc), "
        f"{r['promus']} liens promus (LinkedIn -> vrai site), "
        f"{r['hors_zone']} hors de France, "
        f"{r['ecartees']} écartées à la main, {r.get('rejetees_tri', 0)} déjà rejetées par le tri, "
        f"{r['pays_ecartes']} pays écartés, "
        f"{r['purged']} bruits purgés — {r['total']} total"
    )
    if r["added"] and not dry:
        print("→ re-score + descriptions manquantes : automatiques au prochain lancement de l'app.")
    return 0


# Garde-fou, execute en FIN de module. Il etait place en haut, juste apres les
# premiers motifs : globals() ne contenait alors qu'une partie d'entre eux, et
# _RX_ETAT_US — defini 500 lignes plus bas, et justement corrompu — n'a jamais
# ete controle. Un verificateur qui ne voit pas ce qu'il verifie est pire que
# pas de verificateur : il rassure.
def _verifier_motifs():
    # TOUTE regex compilee du module, quel que soit son nom. Le controle ne
    # regardait que le prefixe `_RX_` et laissait donc passer _DOMAIN_RX,
    # _HARD_NEG_RX, _DEV_NEG_RX, _NEG_TITLE_RX, _AI_RX et _TALENT_LINK_RX —
    # c'est-a-dire exactement les motifs de title_ok, le filtre qui decide ce
    # qui entre dans la file. Trois portent des \b (`csr\b`, `hse\b`, `e&s\b`,
    # `commercial\b`, `paie\b`, `\bia\b`, `nlp\b`). Un garde-fou qui ne couvre
    # pas le code le plus expose ne garde rien.
    vus = 0
    for _n, _rx in list(globals().items()):
        if not isinstance(_rx, re.Pattern) or not isinstance(_rx.pattern, str):
            continue
        vus += 1
        assert "\x08" not in _rx.pattern, f"{_n} : backspace au lieu de \\b"
        assert "\\\\b" not in _rx.pattern, f"{_n} : antislash litteral au lieu de \\b"
    # Le module en compte 27. Si ce nombre s'effondre, c'est que la selection
    # ci-dessus ne trouve plus rien — une panne muette de plus.
    assert vus >= 20, f"_verifier_motifs ne voit que {vus} motifs : selection cassee"


_verifier_motifs()

if __name__ == "__main__":
    sys.exit(main())
