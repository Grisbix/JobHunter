"""Common trunk of the collection: settings, title filter, contracts, countries, offer record.

Part of jobhunter.sources (formerly Scripts/job_sources.py, phase 3.4).
"""

import json
import re
import sys
import time
from typing import Any

from jobhunter import lazy as _paresseux
from jobhunter import network as _reseau
from jobhunter import profile as _P
from jobhunter import root as _racine

# Bounded requests: jobhunter.network (phase 3.2). The old names stay here,
# they are the ones the tests replace (through the jobhunter.sources facade).

# Assignments, not `import … as`: the other sources read them here
# (`_commun._get_borne`), and strict mypy does not export an imported name.
_client_partage = _reseau.client_partage
_get_borne = _reseau.get_borne
_lire_borne = _reseau.lire_borne
_post_borne = _reseau.post_borne
_req_borne = _reseau.req_borne
from jobhunter.scoring.domains import classify_domaine, matches_esg_finance

_ici = sys.modules[__name__]
# Values taken from the profile: computed on first read, not at import
# (jobhunter.lazy). In this module, they are read through `_ici.NAME`.
_PARESSEUX: _paresseux.Fabriques = {}


def __getattr__(nom: str) -> Any:
    return _paresseux.lire(_ici, _PARESSEUX, nom)


# pythonw has no console; the desktop panels also import this module.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# The data stays in Scripts/ (root found by marker, JOBHUNTER_RACINE).
HERE = _racine.scripts()


QUEUE = HERE / "apply_queue.json"

# File SPECIFIC to this program. It used to have the same name as the output of
# scrape_jobs.py: the scan overwrote the harvest of the career sites,
# including when it brought back nothing (WTJ throttled -> 0 offers -> empty file).
FRESH = _racine.dans(HERE, "offres_scan.json")

REJETS_TRI = _racine.dans(HERE, "_rejets_tri.json")  # the tests replace it

_PARESSEUX["KEYWORDS"] = lambda: list(_P.get("collecte.mots_cles", []) or [])

# ── Public ATS slugs (fintech/climate/finance FR-EU). 404 = silently ignored. ──
# Checked with probe_ats.py (the slugs that do not answer are ignored as 404).
# ⚠ Do NOT add "metron" on greenhouse: namesake = US defence company
# (Reston VA, autonomous systems), nothing to do with French energy efficiency.
ATS_SLUGS = {
    # Checked live on 2026-10-24: 22 slugs answered 404 (the company had moved to
    # another ATS, or closed its board) and left; probe_ats found where most went.
    "greenhouse": [
        "watershed",
        "mirakl",
        # Probe of the consulting firms of 2026-10-08: Forvis Mazars Germany
        # (160 offers), AlixPartners including Paris (114).
        "forvismazars",
        "alixpartners",
        "shifttechnology",  # Shift Technology, AI for insurers (Paris)
    ],
    # theodo: found by probing the companies whose career page returns 404.
    # 141 offers, including AI jobs — the vibe-coding axis. The shop window's 404
    # said nothing about the feed, which does answer.
    "lever": [
        "agicap",
        "theodo",
        "swile",
        "pigment",
        "vestiairecollective",
        "younited",  # Younited (consumer credit): credit, risk, compliance
    ],
    "ashby": [
        "alan",
        "swan",
        "altruistiq",
        "climatiq",
        "pennylane",
        "qonto",
        "backmarket",
        "sweep",
        "finary",  # wealth management (private bankers, wealth engineers)
        "akur8",  # insurance pricing (actuaries)
    ],
    # grantthornton = Grant Thornton France (Neuilly, 60 offers); meridiam =
    # their real career site; forvismazars = Ireland; bakertilly = Netherlands.
    "recruitee": [
        "vertuoza",
        "grantthornton",
        "meridiam",
        "forvismazars",
        "bakertilly",
        "ibanfirst",  # iBanFirst (FX payments): KYC, FX sales
        "paipartners",  # PAI Partners (private equity, Paris)
    ],
    "smartrecruiters": [
        "SycomoreAssetManagement",
        "BNPParibas",
        "AXA",
        "SocieteGenerale",
        "Natixis",
        "Amundi",
        "rolandberger",
        "ecovadis",
        "capza",  # Capza (private debt and equity, Paris)
    ],
}

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# The refusal counter lives in jobhunter.network, next to the HTTP client.
INCIDENTS = _reseau.INCIDENTS


def incidents_resume() -> list[str]:
    """The run's refusals, one line per source. Empty if everything went well."""
    return INCIDENTS.resume()


# ── sources editable from the app (🌍 Job sites panel) ──
SOURCES_CFG = HERE / "sources_config.json"


def _load_cfg() -> None:
    """sources_config.json — overrides the defaults: keywords      [keywords] ats_slugs     {ats: [slugs]} workday_flux  [[tenant, host, site, name], ...]   [] = no Workday feed autres_flux   [[type, key, name], ...]            [] = no other ATS. The shipped company lists target finance and ESG: a profile in another profession empties them (first_launch.py) and adds its own."""
    global KEYWORDS, ATS_SLUGS, WORKDAY_FLUX, AUTRES_FLUX
    from jobhunter.sources import company_lists

    # From the shipped lists each time: a second call (the web panels reload) used to
    # keep what the first one had set when a key had since left the file.
    ATS_SLUGS = {k: list(v) for k, v in DEFAUTS_FLUX[0].items()}
    WORKDAY_FLUX, AUTRES_FLUX = list(DEFAUTS_FLUX[1]), list(DEFAUTS_FLUX[2])
    try:
        cfg = json.loads(SOURCES_CFG.read_text(encoding="utf-8"))
        if cfg.get("keywords"):
            KEYWORDS = cfg["keywords"]  # type: ignore[name-defined]  # valeur paresseuse (_PARESSEUX)
        # Ticked company lists (3.32): hand-added feeds plus each list's.
        if (effectifs := company_lists.flux_effectifs(cfg)) is not None:
            ATS_SLUGS, WORKDAY_FLUX, AUTRES_FLUX = effectifs
            return
        if "ats_slugs" in cfg:
            ATS_SLUGS = cfg["ats_slugs"] or {}
        if "workday_flux" in cfg:
            WORKDAY_FLUX = [tuple(x) for x in cfg["workday_flux"] or []]
        if "autres_flux" in cfg:
            AUTRES_FLUX = [tuple(x) for x in cfg["autres_flux"] or []]
    except Exception:
        pass


def _mk(
    titre: str,
    url: str,
    entreprise: str,
    location: str = "",
    date: str = "",
    source: str = "",
    description: str = "",
) -> dict[str, Any]:
    titre, entreprise = _ligne(titre), _ligne(entreprise)
    return {
        "titre": titre,
        "url": url,
        "entreprise": entreprise,
        "domaine": classify_domaine(titre),
        "location": location,
        "date": date,
        "source": source,
        "description": description[:30000],
        "scraped_at": time.strftime("%Y-%m-%d"),
    }


def _ligne(s: str | None) -> str:
    """A title or a company name on one clean line.

    Entities decoded ("AT&amp;T"), tags removed ("<b>France</b>"), line breaks and
    repeated spaces folded. A source that sent them raw put them as is in the table, the
    letter's subject and the file names (break-ui, 2026-10-25).
    """
    import html as _html

    t = re.sub(r"<[^>]*>", " ", _html.unescape(s or ""))
    return " ".join(t.split())


def _strip_html(h: str) -> str:
    """HTML → texte propre (descriptions APIs ATS)."""
    import html as _html

    t = _html.unescape(h or "")
    t = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", t, flags=re.S | re.I)
    t = re.sub(r"<br\s*/?>|</p>|</li>|</div>", "\n", t, flags=re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\n{3,}", "\n\n", re.sub(r"[ \t]+", " ", t)).strip()


# ── Anti-noise: the title must contain a PROFESSION keyword (not just 'intern'/'h/f'),
#    and not be an off-target role (design, sales, marketing, HR…). ──
# NB: without csr|transition|environnement|hse, real ESG jobs were thrown away —
# "VIE Transition Énergétique Corporate" (Crédit Agricole) and "CSR & HR Officer"
# (ODDO BHF) passed matches_esg_finance but failed here, for lack of a profession word.
_PARESSEUX["_FT"] = lambda: _P.get("filtre_titre", {}) or {}

# PROFESSION word required in the title (empty = no requirement).
_PARESSEUX["_DOMAIN_RX"] = lambda: _P.motif(_ici._FT.get("metier"))

# Roles never wanted, whatever the domain.
_PARESSEUX["_HARD_NEG_RX"] = lambda: _P.motif(_ici._FT.get("exclus"))

# Roles set aside UNLESS they carry a marker of the secondary target
# (exemple finance durable : « Developer » non, « AI Engineer » oui).
_PARESSEUX["_DEV_NEG_RX"] = lambda: _P.motif(_ici._FT.get("exclus_sauf_complement"))

_PARESSEUX["_NEG_TITLE_RX"] = lambda: _P.motif(
    (_ici._FT.get("exclus") or []) + (_ici._FT.get("exclus_sauf_complement") or [])
)

# Markers of the secondary target: they pass even with a word of _DEV_NEG_RX.
_PARESSEUX["_AI_RX"] = lambda: _P.motif(_ici._FT.get("complement"))

# LinkedIn labels work-study and internship offers "CDI": its metadata
# is wrong. The title, on the other hand, does not lie — "Alternance - Data Analyst" IS
# a work-study contract. So the title is authoritative when it is explicit.
_RX_ALT = re.compile(r"\b(alternan[ct]|apprenti|apprentissage|contrat\s+pro)", re.I)

_RX_STAGE = re.compile(
    r"\b(stage|stagiaire|internship|intern|working\s+student)\b"
    r"|\bwerkstudent",
    re.I,
)

_RX_VIE_POINTE = re.compile(r"\bv\.i\.[ea]\b", re.I)

_RX_VIE_MAJ = re.compile(r"\bVIE\b(?=\s*[-–—/:|,(])")  # without re.I: "vie" is a word

# Safeguard. A word boundary is written \b and gets corrupted in two ways, both
# SILENT — the pattern compiles, raises nothing, and never matches again:
#   \x08          : a \b passed through a shell heredoc becomes a backspace
#   \\b (literal) : a "fix" of the previous case that escapes the backslash
# Both happened here. We refuse to start rather than let through
# offers that should have been excluded.
# (the check itself is at the END of the module: see _verifier_motifs)


def contrats_exclus() -> set[str]:
    """Contract types the user does not want to see.

    Set in sources_config.json, not hard-coded: they are not a student today, they
    might want to see them again some day. Empty list = everything is displayed.
    """
    try:
        import json as _j

        return set(_j.loads(SOURCES_CFG.read_text(encoding="utf-8")).get("contrats_exclus") or [])
    except Exception:
        return set()


def pays_exclus() -> list[str]:
    """Countries from which no offer is wanted any more, by PATTERN applied to the place.

    WHY A FILTER AND NOT A PURGE. Deleting 937 British and Belgian offers from the
    queue does not kill them: the scan finds them again at the source and re-adds them
    the next day. It is the same lesson as `exclusions.py`, which exists for one-off
    refusals — here the refusal covers an entire geography.

    Set in sources_config.json. Empty list = no country set aside, which is the
    historical behaviour.
    """
    try:
        import json as _j

        return list(_j.loads(SOURCES_CFG.read_text(encoding="utf-8")).get("pays_exclus") or [])
    except Exception:
        return []


def _est_vie(o: Any) -> bool:
    """Does the offer come from Business France?

    We look at the SOURCE and the URL, not at the employer's name: "ARCELORMITTAL
    FRANCE" in Brussels is a V.I.E, "Mirova" in Paris is not one.
    """
    return "businessfrance" in str(o.get("url") or "").lower() or str(
        o.get("source") or ""
    ).lower().startswith("vie")


def _rx_pays_exclus() -> re.Pattern[str] | None:
    r"""The compiled pattern, or None if nothing is excluded.

    The patterns come from the setting and are assembled as they are: it is the
    configuration that decides, not the code.

    NO GLOBAL re.I. It would make `\\bUK\\b` case-insensitive, and "uk" appears in
    ordinary words. Each pattern therefore carries its own `(?i:...)` when case does
    not matter to it: the country names have one, the acronym does not. It is the
    family of substring bugs already paid for on sinGAPore, diveRSE and
    CLIMATisation, moved one notch.
    """
    motifs = pays_exclus()
    if not motifs:
        return None
    return re.compile("|".join(motifs))


# Reading the contract in a description requires CAUTION: the word alone is
# often wrong. Measured on the queue: "6 mois minimum, en alternance ou en
# poste" describes an EXPERIENCE; "early stage a PME mature" is English;
# "chez un prestataire de service" describes the CLIENTS; "recrutement en CDI,
# en interim" lists an agency's services. Hence two passes.
#
# PASS 1 — the structured label, almost always right:
#   "Type de contrat : CDI", "Contrat : Alternance", "Poste en CDI"
# On a posting laid out as a TABLE the label has no colon:
# eFinancialCareers writes "Type de contrat <blanks> Stage". Pass 1
# therefore matched nothing, and pass 2 picked up the "CDD" of a
# boilerplate sentence — four Credit Agricole INTERNSHIPS ended up labelled
# CDD, at the top of the ranking. We now accept a simple blank after the
# long form "type de …"; the bare form "contrat" keeps its
# colon, otherwise any sentence containing the word would act as a label.
_RX_LABEL = re.compile(
    r"type\s+de\s+(?:contrat|recrutement)s?\s*(?:de\s+travail)?\s*(?:[:\-–]|\s)\s*"
    r"|(?:contrat|recrutement)s?\s*(?:de\s+travail)?\s*[:\-–]\s*"
    r"|poste\s+(?:propos[\u00e9]\s+)?en\s+",
    re.I,
)

# values accepted just after that label
_RX_VALEUR = re.compile(
    r"^\W{0,3}(CDI|CDD|alternance|apprentissage|stage|int[e\u00e9]rim|freelance|V\.?I\.?E|contrat \u00e0 dur\u00e9e (?:in)?d\u00e9termin\u00e9e)",
    re.I,
)

# All the contract types, to spot the ENUMERATIONS (see pass 2).
_RX_TOUS_CONTRATS = re.compile(
    r"\bCDI\b|\bCDD\b|\balternance\b|\bapprentissage\b|\bstages?\b"
    r"|\bV\.?I\.?E\b|\bint[eé]rim\b|\bfreelance\b",
    re.I,
)

# PASSE 2 — mots NON AMBIGUS seulement. « stage », « alternance », « interim »,
# Bare "prestataire" and "freelance" are set aside: they designate just as well
# a phase, a past experience or the employer's activity.
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

# A JOB THAT ASKS FOR A STUDENT IS AN INTERNSHIP (the user, 2026-10-04). Many
# postings never say "stage" in their title or their label: the
# Societe Generale writes "Charge de mission ESG" then "Vous etes etudiant en
# Bac +4/5", and the offer came out scored 10. Measured on the queue: 121 descriptions.
#
# Three families of false positives, all met in those 121:
#   - l'ALTERNATIVE : « currently pursuing (or already holding) a master's »,
#     "final-year students or recent graduates" — a graduate is accepted,
#     it is not an internship. See _RX_OU_DIPLOME, searched in the sentence.
#   - l'EXPERIENCE : « Praktika oder Werkstudententatigkeiten », « internships,
#     working student roles" — a past asked for, not a status. Hence "working
#     student" / "Werkstudent" recognised in the TITLE only (_RX_STAGE).
#   - the off-topic: "currently pursuing certification", "for each degree
#     received or currently enrolled in" (CV instruction of a doctorate).
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

# A door open to graduates, IN THE SAME SENTENCE, cancels the request.
_RX_OU_DIPLOME = re.compile(
    r"recent(?:ly)?\s+grad|fresh\s+grad|graduated|already\s+hold|\bor\s+hold|\bhold(?:ing)?\s+or\b"
    # In the past tense: "Tu étais étudiant(e) en école…" (Mister IA, junior CDI).
    r"|\btu\s+[ée]tais\b|\bvous\s+[ée]tiez\b"
    r"|completed|possess|\breceived\b|\bor\s+(?:a\s+)?(?:recent\s+)?graduate"
    # The degree BEFORE the alternative: "Master's degree (or final-year student
    # status) » (L'Oreal), « Higher education or currently studying » (Sii).
    r"|(?:degree|education|Bac\s*\+\s*\d)\s*(?:\([^)]{0,20}\)\s*)?\(?\s*or\s+(?:a\s+)?(?:final|current|penultimate)"
    # "diplômé", not "diplôme": "en vue de l'obtention du diplôme" is a
    # request for a student, not an open door.
    r"|jeunes?\s+dipl[ôo]m|\bdipl[ôo]m(?:é|ée|és|ées)(?!\w)|titulaire",
    re.I,
)


def demande_etudiant(desc: str | None) -> bool:
    """True if the posting asks for a candidate STILL A STUDENT, without an alternative for a graduate.

    Such a job is an internship, whatever its title.
    """
    t = str(desc or "")
    for m in _RX_ETUDIANT.finditer(t):
        # The sentence that carries the request: from the previous full stop to the next one.
        deb = max(t.rfind(".", 0, m.start()), t.rfind("\n", 0, m.start())) + 1
        fins = [i for i in (t.find(".", m.end()), t.find("\n", m.end())) if i >= 0]
        phrase = t[deb : min(fins) if fins else len(t)]
        if not _RX_OU_DIPLOME.search(phrase):
            return True
    return False


def contrat_de_la_description(desc: str, defaut: str = "") -> str:
    """Contract type read in the posting's BODY, in two passes.

    A WRONG contract is worse than an empty contract: the column serves to filter.
    So we favour the structured label, and only fall back on the keywords for those
    that cannot designate anything else.
    """
    t = str(desc or "")
    if len(t) < 60:
        return defaut
    # Before any label: "Contrat : CDD" on a job reserved for students
    # stays a student job, not a job for a graduate.
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
        trouve = motif.search(t)
        if not trouve:
            continue
        # AN ENUMERATION IS NOT A DECLARATION. "…et d'opportunites en
        # alternance, VIE, CDD et CDI" describes what comes AFTER the internship, not
        # the contract offered. It is that CDD which brought four Credit Agricole
        # internships to the top of the list. When several types crowd
        # into the same sentence, none is authoritative.
        autour = t[max(0, trouve.start() - 90) : trouve.end() + 90]
        if len(_RX_TOUS_CONTRATS.findall(autour)) > 1:
            continue
        return etiquette
    return defaut


# Contract mentions in the TITLE. The French acronyms are unambiguous
# as long as they are anchored on word boundaries. "permanent" and
# "fixed term" are the equivalent English labels, common on LinkedIn.
# We do NOT keep "full-time" / "temps plein": it is a working pattern,
# not a contract type — a CDD can be full-time.
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
    # Unpaid: "Full-Stack Web Developer | Remote Volunteer" came first (fit 10) for a
    # junior developer (2026-10-24). The V.I.E ("volontariat international") is
    # recognised before this list.
    ("Bénévolat", re.compile(r"\bb[ée]n[ée]vol\w*|\bvolunteer\w*", re.I)),
]


def contrat_du_titre(titre: str, source: str = "", defaut: str = "") -> str:
    """Contract type deduced from the title, otherwise `defaut`.

    Intended order: the student contracts first. A title "Stage puis CDI" designates
    an internship — the mention most binding for the candidate prevails.
    """
    t = str(titre or "")
    # Work-study and internship BEFORE V.I.E: "Stage Analyste M&A (puis VIE/CDI)"
    # is an internship, even if the title mentions the next step of the path.
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


def title_ok(t: str) -> bool:
    """Title filter: profession keyword required + not an off-target role + global lexicon.

    AI exception: a title stamped AI passes even if it contains "engineer"/
    "développeur", because it is the market targeted as a complement to ESG.
    """
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
# Found on 2026-10-08 by following the "Careers" link of the sites of ~150
# companies (probe_carrieres.sonde_site, then the iframes/scripts of the career
# page). Each is the JSON/RSS API that the career page calls itself.
#   workable   apply.workable.com/api/v1/widget/accounts/{slug}
#   pinpoint   {slug}.pinpointhq.com/postings.json
#   eightfold  {hote}/api/apply/v2/jobs?domain={domaine}&query=   (BCG)
#   sfrss      {hote}/services/rss/job/?keywords=   (SAP SuccessFactors, site carriere)
#   oracle     {hote}/hcmRestApi/.../recruitingCEJobRequisitions   (Oracle Recruiting)
# The last three search server side: one request per word of WORKDAY_MOTS.
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
    # Phenom (results embedded as JSON), iCIMS (HTML list), Cornerstone
    # (anonymous token of the public page): added on 2026-10-08.
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
    # Shop window in 403, public ATS next to it (2026-10-08): UNDP on Oracle Quantum.
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

# ═══════════════ 1 bis. Workday — the public API of large groups ═══════════════
# WHY. The career pages of these groups are SPAs behind an anti-bot:
# scrape_jobs.py opens them and reads nothing there (measured: 11 sites, 0 offers). But
# their offers are served by Workday on *.myworkdayjobs.com, whose JSON API
# is public and unauthenticated — it is the one their own page calls.
# We read the source instead of forcing the shop window.
#
# The feeds below were found by probe_carrieres.py ("Careers" link
# of the home page -> ATS host) and VERIFIED: Eiffage 2000 offers, Ardian 74,
# Lombard Odier 35. 2109 offers where the DOM scraper brings back zero.
#
# TWO LIMITS OF THE API, measured:
#   - `limit` caps at 20. Beyond that the response is EMPTY, not truncated: asking
#     for 100 returns 0 offers. All of Eiffage would therefore take 100 requests.
#   - `searchText` filters server side and brings 2000 down to 70-500. The sort is by
#     relevance, the first pages carry the good offers.
# Hence the strategy: a few keywords, few pages each, union and dedup.
WORKDAY_FLUX = [
    # (tenant, host, site, nom lisible)
    ("eiffage", "wd3", "Eiffage_Careers", "Eiffage"),
    ("ardian", "wd103", "ArdianCareers", "Ardian"),
    ("lombardodier", "wd3", "Lombard_Odier_Careers", "Lombard Odier"),
    # PwC, all countries including France (Neuilly): 3897 experienced offers and
    # 1359 campus ones (2026-10-07). The Big 4 only came through LinkedIn; the
    # site name follows no form that site_final can guess.
    ("pwc", "wd3", "Global_Experienced_Careers", "PwC"),
    ("pwc", "wd3", "Global_Campus_Careers", "PwC"),
    # Probe of the consulting firms of 2026-10-08 (site_final.flux_workday, identity
    # verified on the shop window). About 70 s per feed, read 4 at a time
    # (scan_workday). The mostly American feeds (RSM, Crowe, Vanguard, State
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
    # Sites whose name cannot be guessed: tested one by one on 2026-10-08.
    # MMC = Marsh McLennan, hence also Oliver Wyman and Mercer.
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
    # Found through the "Careers" link of their site (2026-10-08).
    ("issgovernance", "wd1", "ISScareers", "ISS"),
    ("rothschildandco", "wd3", "Rothschildandco_Lateral", "Rothschild & Co"),
    ("vontobel", "wd3", "Vontobel_External_Career", "Vontobel"),
    ("cip", "wd103", "CIP_Careers", "Copenhagen Infrastructure Partners"),
    ("aviva", "wd1", "Aviva_Investors_External", "Aviva Investors"),
    ("mgpru", "wd3", "mandgprudential", "M&G"),
    # Deloitte France: link from its "join us" page, found by web search
    # "Deloitte carriere" — the home page did not give it (556 offers).
    ("fina", "wd103", "DeloitteRecrute", "Deloitte"),
    # International, probe of 2026-10-08 ("Careers" link of ~130 sites):
    # Asia, Canada. The mostly American feeds stay with site_final.
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
    # Employers with fit >= 8 that only came through LinkedIn (2026-10-08).
    ("onepoint", "wd3", "OnepointFR", "Onepoint"),
    ("bdf", "wd103", "recrutement-banque-de-France", "Banque de France"),
    ("ayvens", "wd3", "AyvensCareers", "Ayvens"),
    ("airliquidehr", "wd3", "AirLiquideExternalCareer", "Air Liquide"),
    # Shop window in 403, public Workday feed found by name (2026-10-08).
    ("brookfield", "wd5", "brookfield", "Brookfield"),
    # "JS only" portals: the shop-window site points to these feeds (2026-10-08)
    ("ocbc", "wd102", "External", "OCBC"),
    ("bis", "wd3", "External", "BRI (BIS)"),
]

# The engine's lists as shipped, before sources_config.json replaces them: the "finance"
# company list (sources.company_lists), and the base _load_cfg starts again from.
DEFAUTS_FLUX: tuple[dict[str, list[str]], list[tuple[str, ...]], list[tuple[str, ...]]] = (
    {k: list(v) for k, v in ATS_SLUGS.items()},
    list(WORKDAY_FLUX),
    list(AUTRES_FLUX),
)

# Tracking parameters: present or not depending on where the link comes from, they do
# NOT change the offer. Without removing them, dedup by exact URL does not work
# as soon as one pastes a LinkedIn link (…/jobs/view/123?refId=X&trackingId=Y) already
# present in the queue → duplicate.
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


def _norm_url(u: str | None) -> str:
    """URL dedup key: host without www, path without a final /, tracking params removed and the rest sorted.

    The real identifiers (?jk=, ?id=) stay.
    """
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
    if host.endswith("linkedin.com"):  # fr./be./lu. linkedin = same site
        host = "linkedin.com"
    qs = [(k, v) for k, v in parse_qsl(s.query) if k.lower() not in _URL_JUNK]
    tail = "?" + urlencode(sorted(qs)) if qs else ""
    return host + s.path.rstrip("/") + tail


# ── Filtre geographique ──────────────────────────────────────────────────────
# An ATS feed carries the company's name, not its country. "Forvis Mazars" on
# greenhouse is the GERMAN entity ("Einstieg als", "Rechtsanwalt") and on
# recruitee the IRISH entity: zero jobs in France out of 19. The identity
# check cannot see it — the name is the same. Only the PLACE decides.
#
# The user lives in Gironde. An offer in Hanoi or Dresden has no business getting in.
_RX_FR = re.compile(
    r"\bfr\b|france|paris|lyon|lille|nantes|bordeaux|toulouse|marseille|nice"
    r"|rennes|strasbourg|montpellier|grenoble|rouen|reims|dijon|angers|tours"
    r"|clermont|orleans|metz|nancy|caen|brest|limoges|amiens|perpignan|besancon"
    r"|le mans|saint.etienne|toulon|villeurbanne|nimes|aix.en.provence"
    r"|ile.de.france|hauts.de.seine|gironde|remote|teletravail|t[ée]l[ée]travail"
    r"|hybrid|anywhere"
    # THE DEPARTMENT NUMBER. APEC writes "Nanterre - 92",
    # "Issy-les-Moulineaux - 92", "Marseille 01 - 13". None of these cities
    # was in the list above, and the fallback rule refused any place
    # of more than one word: 341 offers out of 653 thus left as foreign,
    # including all of La Défense — the heart of French financial employment.
    # An isolated two-digit number, or 2A/2B, or a three-digit overseas code,
    # is only written that way in France. The range goes up to 98x:
    # stopped at 976, it left "Noumea - 98" out, New Caledonia
    # being 988 — like Wallis 986 and Polynesia 987.
    r"|(?:^|[\s,;-])(?:0[1-9]|[1-8]\d|9[0-5]|2[AB]|9[78]\d?)(?:$|[\s,;-])",
    re.I,
)

# Countries explicitly ELSEWHERE: the place is filled in and does not talk about France.
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

# American state at the end of a place: "Reston, VA", "Aurora, CO". Without this pattern
# they passed for France — neither code was in the list of
# countries, and an unrecognised place was accepted by default.
_RX_ETAT_US = re.compile(
    r",\s*(AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|MA|MD|ME|MI"
    r"|MN|MO|MS|MT|NC|ND|NE|NH|NJ|NM|NV|NY|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VA"
    r"|VT|WA|WI|WV|WY|DC)\b"
)

# WORLDWIDE SEARCH. The geographic filter is a CHOICE, not a law: it
# set aside 179 offers in the scan of 8 September alone. When the user wants to search
# everywhere, we do NOT disable it by changing each caller — there are
# several — but here, at the source. `zones.py` then stores
# these offers in a separate "international" zone, so that they do not
# mix with the French targets.
# DEFAULT: we keep the whole world. The user decided on 17/09 — the offers
# outside France are wanted. The scan ALREADY ASKED LinkedIn for eight countries
# (LIEUX_MONDE) to throw seven of them away at merge, and its own more recent
# programs, scan_graduate and scan_secteurs, both set `J.MONDE = True`.
# The opposite default was the last place not to follow.
# `zones.py` stores these offers in a separate "international" zone, so
# that they do not mix with the French targets on display.
# `--france` restricts when the opposite is wanted.
MONDE = True


def en_france(lieu: str | None) -> bool:
    """Is the job in France (or remote)?

    Always returns True when MONDE is active: the worldwide search no longer filters
    on the place.

    An EMPTY place passes: many French postings fill in none, and refusing on a lack
    of information would set aside real offers.

    A FILLED-IN place that talks neither about France nor about a known country also
    passed, by default. It was too permissive: "Mexico City", "Reston, VA" and
    "Aurora, CO" got in. An explicit place must now carry a French signal or stay
    very short ("fr", a postcode, an isolated city name that could not be classified).
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
    # Explicit, unrecognised place: we only accept it if it is too short to
    # designate a foreign country ("33", "Sud-Ouest"). A "Mexico City" or a
    # "Reston, VA" has a comma or several words: we refuse.
    return not ("," in t or len(t.split()) > 1)
