"""Tronc commun de la collecte : reglages, filtre d'intitule, contrats, pays, fiche d'offre.

Partie de jobhunter.sources (ancien Scripts/job_sources.py, phase 3.4)."""

import json
import re
import sys
import time
from typing import Any

from jobhunter import paresseux as _paresseux
from jobhunter import profil as _P
from jobhunter import racine as _racine
from jobhunter import reseau as _reseau

# Requetes bornees : jobhunter.reseau (phase 3.2). Les anciens noms restent ici,
# ce sont eux que les tests remplacent (via la facade jobhunter.sources).
from jobhunter.reseau import client_partage as _client_partage  # noqa: F401
from jobhunter.reseau import get_borne as _get_borne  # noqa: F401
from jobhunter.reseau import lire_borne as _lire_borne  # noqa: F401
from jobhunter.reseau import post_borne as _post_borne  # noqa: F401
from jobhunter.reseau import req_borne as _req_borne  # noqa: F401
from jobhunter.scoring.domaines import classify_domaine, matches_esg_finance

_ici = sys.modules[__name__]
# Valeurs tirees du profil : calculees a la premiere lecture, pas a l'import
# (jobhunter.paresseux). Dans ce module, on les lit par `_ici.NOM`.
_PARESSEUX: _paresseux.Fabriques = {}


def __getattr__(nom: str) -> Any:
    return _paresseux.lire(_ici, _PARESSEUX, nom)


sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]  # console : TextIOWrapper

# Les donnees restent dans Scripts/ (racine trouvee par marqueur, JOBHUNTER_RACINE).
HERE = _racine.scripts()

# TRANSITION (phase 3) : imports differes de modules encore dans Scripts/
# (exclusions, rejets_tri, wtj_desc). A retirer quand ils auront rejoint le paquet.
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

QUEUE = HERE / "apply_queue.json"

# Fichier PROPRE a ce programme. Il portait le meme nom que la sortie de
# scrape_jobs.py : le scan ecrasait la recolte des sites carriere, y
# compris quand il ne ramenait rien (WTJ bride -> 0 offre -> fichier vide).
FRESH = HERE / "offres_scan.json"

REJETS_TRI = HERE / "_rejets_tri.json"  # les tests le remplacent

_PARESSEUX["KEYWORDS"] = lambda: list(_P.get("collecte.mots_cles", []) or [])

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

# Le compteur des refus vit dans jobhunter.reseau, a cote du client HTTP.
INCIDENTS = _reseau.INCIDENTS


def incidents_resume():
    """Les refus du run, en une ligne par source. Vide si tout s'est bien passe."""
    return INCIDENTS.resume()


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
_PARESSEUX["_FT"] = lambda: _P.get("filtre_titre", {}) or {}

# Mot METIER requis dans l'intitule (vide = pas d'exigence).
_PARESSEUX["_DOMAIN_RX"] = lambda: _P.motif(_ici._FT.get("metier"))

# Roles jamais voulus, quel que soit le domaine.
_PARESSEUX["_HARD_NEG_RX"] = lambda: _P.motif(_ici._FT.get("exclus"))

# Roles ecartes SAUF s'ils portent un marqueur de la cible secondaire
# (exemple finance durable : « Developer » non, « AI Engineer » oui).
_PARESSEUX["_DEV_NEG_RX"] = lambda: _P.motif(_ici._FT.get("exclus_sauf_complement"))

_PARESSEUX["_NEG_TITLE_RX"] = lambda: _P.motif(
    (_ici._FT.get("exclus") or []) + (_ici._FT.get("exclus_sauf_complement") or [])
)

# Marqueurs de la cible secondaire : passent meme avec un mot de _DEV_NEG_RX.
_PARESSEUX["_AI_RX"] = lambda: _P.motif(_ici._FT.get("complement"))

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


def demande_etudiant(desc: str | None) -> bool:
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
    if _P.cherche(_ici._AI_RX, t):
        return not _P.cherche(_ici._HARD_NEG_RX, t)
    return bool(
        matches_esg_finance(t)
        and (_ici._DOMAIN_RX is None or _ici._DOMAIN_RX.search(t))
        and not _P.cherche(_ici._NEG_TITLE_RX, t)
    )


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
    from urllib.parse import parse_qsl, urlencode, urlsplit

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
