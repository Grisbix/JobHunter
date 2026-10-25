"""jobhunter.scoring.sorting — Separates what matches the profile from what does not, and purges.

Formerly Scripts/tri_file.py.

WHY NOT THE FIT. The fit measures the DENSITY OF ESG and finance VOCABULARY, not how
well a job suits a junior candidate. Measured on the queue of 18/09/2026 (9492 offers):

    fit 6: "JPMorganChase — 2027 Corporate & Investment Bank, Global
            Investment Banking"          -> exactly the target
    fit 7: "septeo — AI Tech Lead"       -> neither junior nor finance
    fit 7: "talan — Data Engineer Confirme / Senior"
    fit 1: "Coca-Cola HBC — Financial Analyst"

Sorting by fit would delete the first and keep the next two. The fit serves to RANK
what remains; it does not serve to throw away.

WHAT DECIDES is the TITLE and the REQUIRED EXPERIENCE. A title says what the job is
and at what level; the years of experience say whether the door is open. The user is
just out of a BBA with an internship: beyond five years required, the offer is not
refusable, it is out of reach.

FOUR DELETION REASONS, from the surest to the most debatable:

  lien_mort   the link no longer leads anywhere (MORT / EXPIREE / FERMEE)
  experience  exp_requise >= 5 years
  seniorite   the title says senior, confirmé, director, head of, VP...
  metier      the title designates a profession outside the profile (dev, sales, HR,
              health, logistics, catering, teaching...)

WHAT IS NEVER DELETED:
  - the saved SEARCH rows (url_type == RECHERCHE)
  - any offer present in suivi.json (application sent or tracked)

NEITHER `action` NOR `statut` PROTECTS. Both look like manual marks and are not.
`action == "1"` is on 629 rows, all imported in July: NO program writes it, and the
batch contains "Manager SAP FICO S/4HANA". `statut == "Oui"` (523 rows) comes from the
same import. The real tracking is in suivi.json, written by the app's _set_statut — so
it is that, and that alone, which protects.

AI AND DATA STAY. The profile explicitly targets them (the scoring's "ia" axis, skills
"vibe coding", "agents IA", "Python / SQL"). Only software ENGINEERING is deleted — ML
engineer, data engineer, devops, architect — not the analysis or consulting jobs that
carry "IA".

Run:
  python JobHunter.pyw sort                 # inspection only, nothing is written
  python JobHunter.pyw sort --motifs        # + sample of 20 titles per reason
  python JobHunter.pyw sort --garde         # + sample of what is KEPT
  python JobHunter.pyw sort --supprime      # writes, after a timestamped backup
"""

import argparse
import importlib
import re
import shutil
import sys
import time
from pathlib import Path  # noqa: F401  (annotations and callers)

from jobhunter import root as _racine
from jobhunter.types import Offre

HERE = _racine.scripts()
sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)  # type: ignore[union-attr]  # console : TextIOWrapper

QUEUE = HERE / "apply_queue.json"
SUIVI = _racine.dans(HERE, "suivi.json")

# ── 1. SENIORITE ────────────────────────────────────────────────────────────
# Two lists, because two levels of certainty.
#
# HARD: the word means nothing other than "not for a beginner".
#   "sr" is bounded on both sides: without boundaries it catches "sRisque".
#   "vp" likewise: "vp" in "vpn".
_RX_SENIOR_DUR = re.compile(
    r"\b(?:senior|sr|confirm[ée]{1,2}s?|exp[ée]riment[ée]{1,2}s?"
    r"|director|directeur|directrice|head\s+of|vice[\s-]?pr[ée]sident"
    r"|vp|chief|principal|partner|associ[ée]\s+g[ée]rant)\b",
    re.I,
)

# SOFT: the word often says seniority, but not always. Neutralised when
# the title also carries a beginner mark — "Management Trainee"
# contains "manage", "Graduate Programme Manager" is already excluded elsewhere.
#
#   "lead": "Lead Generation" is sales, not seniority. This
#   false positive was already fixed once in ats_match._RX_SENIOR_FIN; we
#   reuse the same negation here rather than rediscovering it.
#   "expert": "expert comptable" goes anyway through the profession reason.
_RX_SENIOR_MOU = re.compile(
    r"\b(?:manager|managing|lead(?!\s+(?:generation|gen)\b)|responsable"
    r"|expert[e]?s?|chef\s+de|g[ée]rant[e]?|superviseur)\b",
    re.I,
)

# "RESPONSABLE" IS TWO WORDS. The noun designates a head of department — "Responsable
# Tresorerie", to throw away. The adjective qualifies an approach — "Conseiller en
# Epargne Responsable", which is exactly the target, and which the
# seniority filter deleted. "Investissement responsable" is a standard term of the
# trade: the case is rare in today's queue (1 offer) but comes back at each
# scan.
#
# A negation in `_RX_SENIOR_MOU` would require a variable-width lookbehind,
# which Python refuses. So we remove the adjectival use from the title BEFORE
# looking for seniority — same method as `_sans_marque` in
# tailor_application, which erases "Credit Agricole" before counting the agricultural.
#
# No final \b on "responsable": it must see "responsables" in the plural.
_RX_RESP_ADJ = re.compile(
    r"\b(?:[eé]pargnes?|investissements?|financements?|finance|placements?|gestion"
    r"|achats?|approvisionnements?|consommation|croissance|entreprises?|num[eé]rique"
    r"|innovation|cha[iî]ne|tourisme|voyages?|marketing|communication)"
    r"\s+responsables?",
    re.I,
)


def _sans_resp_adjectif(titre: str | None) -> str:
    """The title stripped of its adjective "responsable", for the seniority test."""
    return _RX_RESP_ADJ.sub(" ", titre or "")


# Beginner marks. They neutralise the SOFT list, never the HARD list.
#
# NO FINAL \b on the stems. "alternan[ct]\b" did NOT see
# "Alternance": after "alternanc" comes "e", hence no word boundary.
# "Alternance – Chef de Projet IA & Data" went out as a seniority job.
# It is the same defect as the final \b of _RX_DURABLE, fixed this morning in
# tailor_application. The short acronyms, on the other hand, KEEP their boundaries: "jr"
# without a right boundary would catch "jrXXX", "vie" would catch "vieillissement".
_RX_JUNIOR = re.compile(
    r"\b(?:jr|intern|stage|entry[\s-]level|v\.?i\.?e)\b"
    r"|\b(?:junior|graduate|trainee|stagiaire|internship"
    r"|alternan|apprenti|d[ée]butant|jeunes?\s+dipl[oô]m"
    r"|young\s+(?:graduate|talent|professional)|assistant)\w*",
    re.I,
)

# ── 2. METIERS HORS PROFIL ──────────────────────────────────────────────────
# A dictionary pattern -> family, to be able to say WHY an offer leaves
# and check each family separately. Each pattern was re-read against the
# substring trap, which produced eight bugs on this project:
# « sinGAPore », « diveRSE », « CLIMATisation », « transVERSE », « POWER
# Platform", "BP in BPCE". Everything is bounded.
_METIERS_CATALOGUE = {  # all the known families
    # QUANT AND DATA ENGINEERING: off target even with "ESG" in the title
    # (the user, 2026-10-05). "Analyste Climate Finance / ESG Quant" or "ESG
    # Data Engineer" came out at fit 10: the word ESG triggered the rescue, while
    # the profession stays quantitative computation or data plumbing.
    # Hence their place in _METIERS_DURS. "quantity" (surveyor) and
    # "quantification" are not taken: only the forms of the profession.
    "quant": re.compile(r"\b(?:quants?|quantitati(?:ve|ves|f|fs)|structur(?:er|eur)s?)\b", re.I),
    "ingenierie_data": re.compile(
        r"\b(?:data\s+engineer(?:ing|s)?|big\s+data\s+engineer|analytics\s+engineer"
        r"|data\s+platform\s+engineer|ing[ée]nieure?\s+(?:data|donn[ée]es|big\s+data)"
        r"|ingenier[oa]\s+de\s+datos|engenheir[oa]\s+de\s+dados)\b",
        re.I,
    ),
    # Software engineering and infrastructure. Data ANALYSIS stays (see
    # _RX_DATA_GARDE below); it is the DEVELOPER profession that leaves.
    "informatique": re.compile(
        r"\b(?:d[ée]veloppeur|d[ée]veloppeuse|developer|dev\s+(?:back|front|full)"
        # "AI engineer" is NO LONGER rejected on the title (the user, 2026-10-05):
        # it is the tooling required that decides, see OUTILS_MAX below.
        r"|software\s+engineer"
        r"|ing[ée]nieur\s+(?:logiciel|informatique|syst[eè]me|r[ée]seau|cloud"
        r"|d[ée]veloppement|[ée]tude|data|donn[ée]es)"
        r"|back[\s-]?end|front[\s-]?end|full[\s-]?stack|devops|mlops|sre\b"
        r"|architecte|architect|administrateur\s+(?:syst[eè]me|r[ée]seau|base)"
        r"|cybers[ée]curit[ée]|cyber\s?security|soc\s+analyst|pentest"
        r"|machine\s+learning\s+engineer|ml\s+engineer"
        r"|research\s+scientist|data\s+engineer|data\s+architect"
        r"|site\s+reliability|qa\s+engineer|testeur|test\s+engineer"
        r"|technicien\s+(?:informatique|support|helpdesk)|support\s+technique"
        r"|scrum\s+master|product\s+owner|tech\s+lead"
        r"|sap\b|salesforce|servicenow|sharepoint|oracle\s+erp"
        r"|webmaster|int[ée]grateur\s+web|ui\s?/?\s?ux|designer)\b",
        re.I,
    ),
    # Sales. "commercial" alone is too wide — "banque commerciale",
    # "immobilier commercial", "credit commercial" are finance. So we
    # ONLY take the forms where it designates the person.
    #
    # "business development" is NOT taken alone EITHER. Of the first twenty
    # matches of the pattern, seven were "Business Development
    # Analyst" — at TotalEnergies Singapore (fit 8), at Telco OI's CEO Office
    # (fit 9), in a graduate programme at Sibelco. It is a strategic analysis
    # job, not a sales job. Only the sales DEVELOPER and its explicit
    # titles leave.
    #
    # "negociateur" left the list: it designates the estate agent,
    # but also the MARKET DEALER — "Negociateur Credit" at Natixis
    # Investment Managers is a trading desk, not an agency.
    "vente": re.compile(
        r"\b(?:(?:attach[ée]|ing[ée]nieur|conseiller|conseill[eè]re|charg[ée]|d[ée]l[ée]gu[ée])"
        r"\s*\(?e?\)?\s*commercial"
        r"|commercial[e]?\s*\(?(?:h/?f|f/?h)\)?\s*$|business\s+developer"
        r"|business\s+development\s+(?:representative|manager|executive|intern)"
        r"|sales\b|vendeur|vendeuse|t[ée]l[ée]vente"
        r"|account\s+(?:manager|executive)|key\s+account|caissier|caissi[eè]re"
        r"|h[oô]te\s+de\s+caisse|conseiller\s+de\s+vente|retail\s+advisor"
        r"|courtier)\b",
        re.I,
    ),
    "marketing": re.compile(
        r"\b(?:marketing|community\s+manager|social\s+media|seo\b|sea\b|growth\s+hack"
        r"|brand\s+(?:manager|content)|content\s+(?:manager|writer)|r[ée]dacteur"
        r"|graphiste|infographiste|motion\s+design)\b",
        re.I,
    ),
    "rh": re.compile(
        r"\b(?:ressources\s+humaines|rh\b|human\s+resources|hr\b|recruteur|recruteuse"
        r"|recruiter|recrutement|talent\s+acquisition|gestionnaire\s+de\s+paie"
        r"|payroll|charg[ée]\s*\(?e?\)?\s*de\s+formation|people\s+partner)\b",
        re.I,
    ),
    "juridique": re.compile(
        r"\b(?:juriste|avocat[e]?|legal\s+counsel|paralegal|notaire|greffier"
        r"|huissier|contract\s+manager)\b",
        re.I,
    ),
    "sante": re.compile(
        r"\b(?:infirmi[eè]r[e]?|m[ée]decin|pharmacien[ne]?|aide[\s-]soignant[e]?"
        r"|kin[ée]sith[ée]rapeute|dentiste|sage[\s-]femme|auxiliaire\s+de\s+(?:vie|pu[ée]ri)"
        r"|ergoth[ée]rapeute|psychologue|v[ée]t[ée]rinaire|nurse|physician"
        r"|clinical\s+(?:research|trial)|pharmacovigilance)\b",
        re.I,
    ),
    "industrie": re.compile(
        r"\b(?:op[ée]rateur\s+de\s+production|agent\s+de\s+production|ouvrier"
        r"|m[ée]canicien[ne]?|[ée]lectricien[ne]?|soudeur|chaudronnier|usineur"
        r"|technicien\s+de\s+maintenance|agent\s+de\s+maintenance|monteur"
        r"|conducteur\s+de\s+(?:ligne|travaux|machine)|cariste|magasinier"
        r"|pr[ée]parateur\s+de\s+commande|manutentionnaire|chauffeur|livreur"
        r"|agent\s+d'entretien|agent\s+de\s+propret[ée]|gardien|agent\s+de\s+s[ée]curit[ée]"
        r"|plombier|ma[çc]on|peintre|menuisier|couvreur|carrossier"
        r"|dessinateur|projeteur|ing[ée]nieur\s+(?:m[ée]canique|proc[ée]d[ée]|mat[ée]riaux|structure|civil|calcul)"
        r"|pilote\s+de\s+ligne|steward|h[oô]tesse\s+de\s+l'air|personnel\s+navigant"
        r"|technicien\s+a[ée]ronautique|m[ée]canicien\s+avion)\b",
        re.I,
    ),
    "restauration": re.compile(
        r"\b(?:serveur|serveuse|cuisinier|cuisini[eè]re|commis\s+de\s+cuisine"
        r"|chef\s+de\s+(?:rang|partie)|boulanger|p[aâ]tissier|boucher|barman|barista"
        r"|[ée]quipier|employ[ée]\s+(?:polyvalent|de\s+restauration)|plongeur"
        r"|r[ée]ceptionniste|femme\s+de\s+chambre|gouvernant[e]?)\b",
        re.I,
    ),
    # ONLY the academic titles, and they CANNOT be rescued: a
    # post-doctorate "AI for Sustainable Energy" ticks all the ESG keywords
    # and stays out of reach for a BBA. "formateur", "animateur" and
    # "educateur" left this list — they are context words, not
    # professions: "Comptable ECF - Cabinet Formateur" describes a firm,
    # "Animateur securite environnement" is an HSE job.
    "enseignement": re.compile(
        r"\b(?:professeur|enseignant[e]?|instituteur|ma[iî]tre\s+de\s+conf[ée]rence"
        r"|teacher|lecturer|post[\s-]?doc|post[\s-]?doctora\w*|doctorant[e]?"
        r"|phd\s+(?:student|candidate)|th[eè]se\s+(?:cifre|de\s+doctorat)"
        r"|offre\s+de\s+th[eè]se)\b",
        re.I,
    ),
    "administratif": re.compile(
        r"\b(?:secr[ée]taire|standardiste|assistant[e]?\s+(?:administratif|administrative|de\s+direction)"
        r"|agent\s+administratif|op[ée]rateur\s+de\s+saisie|archiviste"
        r"|charg[ée]\s*\(?e?\)?\s*de\s+client[eè]le|service\s+client|customer\s+(?:service|success|support)"
        r"|t[ée]l[ée]conseiller|h[oô]te\s+d'accueil)\b",
        re.I,
    ),
    "logistique": re.compile(
        r"\b(?:supply\s+chain|logisti(?:que|cs)|approvisionn|transit|douane"
        r"|ordonnancement|planificateur\s+(?:industriel|de\s+production)"
        r"|acheteur|acheteuse|buyer|procurement|category\s+manager)\b",
        re.I,
    ),
}

# ── WHAT STAYS DESPITE A PROFESSION REASON ───────────────────────────────────
# Three real titles that the patterns above wrongly caught:
#   "Analyste RH et controle de gestion sociale"  -> the core is the control
#   « Sustainable Procurement Analyst »             -> achats responsables, ESG
#   "Business Analyst Finance"                    -> "business" is not
#                                                      « business developer »
# The rule: a title that carries an ESG marker or a CLEAR finance profession
# is not thrown away because of an isolated profession word.
# TWO GROUPS, because two opposite boundary behaviours.
#
#   The ACRONYMS keep both boundaries. "rse" without a right boundary matches
#   "diveRSE", "esg" would match "esgXXX" — it is the family of bugs that
#   already gave "sinGAPore", "CLIMATisation" and "BP in BPCE".
#   The STEMS lose the right boundary, otherwise they do not see their own
#   flexions : « sustainab\b » rate « Sustainability », « durabilit\b » rate
#   "durabilite". Two fit-10 offers thus left under the "logistique" reason
#   — "Trainee Sustainability & Strategic Regulatory" at PwC and "Working
#   Student Sustainable Procurement » chez Sika.
from typing import Any

from jobhunter import lazy as _paresseux
from jobhunter import profile as _P

_ici = sys.modules[__name__]
# Values taken from the profile: computed on first read, not at import
# (jobhunter.lazy). In this module, they are read through `_ici.NAME`.
_PARESSEUX: _paresseux.Fabriques = {}


def __getattr__(nom: str) -> Any:
    return _paresseux.lire(_ici, _PARESSEUX, nom)


_PARESSEUX["_TRI"] = lambda: _P.get("tri", {}) or {}
# Words of the TARGET that rescue a title from a family set aside (profile,
# tri.sauvetage): "Sustainable Procurement" stays for a sustainability profile.
_PARESSEUX["_RX_SAUVETAGE"] = lambda: _P.motif(_ici._TRI.get("sauvetage"))

# FAMILIES THAT THE RESCUE DOES NOT CATCH. An ESG word in the title does not
# make the job accessible: a post-doctorate "AI for Sustainable Energy"
# requires a doctorate, an "Analyse environnementale en salle blanche" requires
# an engineering degree, a care job requires a state diploma. The
# rescue serves not to throw away a FINANCE job because of a context word; it
# does not serve to open closed professions.
_PARESSEUX["_METIERS_DURS"] = lambda: set(_ici._TRI.get("metiers_durs", []) or [])
# Families REMOVED for this profile (tri.metiers_exclus); the catalogue
# _METIERS_CATALOGUE above stays the library. Missing from the profile = all.
_PARESSEUX["_EXCLUS"] = lambda: _ici._TRI.get("metiers_exclus")
_PARESSEUX["_METIERS"] = lambda: (
    dict(_METIERS_CATALOGUE)
    if _ici._EXCLUS is None
    else {k: v for k, v in _METIERS_CATALOGUE.items() if k in set(_ici._EXCLUS)}
)

# ── 2 bis. TROP D'OUTILS DE DEVELOPPEMENT ───────────────────────────────────
# "Keep AI engineer, but when too many technical tools are needed to code,
# delete" (the user, 2026-10-05). The title is not enough: a "Consultant
# Business & AI Insights » chez Deloitte demande Databricks, Snowflake,
# Kubernetes and CI/CD; an "AI Analyst" may only ask for Python.
#
# We count FAMILIES of engineer tools in the description. Not counted:
# Python, SQL, Excel, VBA, Power BI, Tableau, R (analyst tools, those
# of the profile) nor git (too common). AWS, GCP and Azure are only ONE family:
# "AWS, GCP ou Azure" is an alternative, not three requirements.
# Measured on the queue (7336 offers): threshold 4 -> 189 offers, 2 of them at fit >= 9
# ("ESG Data Engineer", a "Data & AI Solutions Analyst" that asks for FastAPI,
# Postgres, CI/CD and the cloud). Threshold 3 took 313, including real
# analysis jobs that cite one cloud and two databases.
_OUTILS = {
    "spark": r"\b(?:py)?spark\b",
    "hadoop": r"\bhadoop\b",
    "kafka": r"\bkafka\b",
    "airflow": r"\bairflow\b",
    "dbt": r"\bdbt\b",
    "databricks": r"\bdatabricks\b",
    "snowflake": r"\bsnowflake\b",
    "kubernetes": r"\bkubernetes\b|\bk8s\b",
    "terraform": r"\bterraform\b",
    "cicd": r"\bci\s*/\s*cd\b",
    "jenkins": r"\bjenkins\b",
    "scala": r"\bscala\b",
    "java": r"\bjava\b(?!\s*script)",
    "csharp": r"\bc#",
    "golang": r"\bgolang\b",
    "rust": r"\brust\b",
    "typescript": r"\btypescript\b",
    "javascript": r"\bjavascript\b",
    "react": r"\breact(?:\.js|js)?\b",
    "node": r"\bnode\.?js\b",
    "fastapi": r"\bfastapi\b",
    "django": r"\bdjango\b",
    "flask": r"\bflask\b",
    "tensorflow": r"\btensorflow\b",
    "pytorch": r"\bpytorch\b",
    "keras": r"\bkeras\b",
    "mlflow": r"\bmlflow\b",
    "kubeflow": r"\bkubeflow\b",
    "langchain": r"\blangchain\b",
    "huggingface": r"\bhugging\s*face\b",
    "cloud": r"\baws\b|\bgcp\b|google\s+cloud|\bazure\b",
    "sagemaker": r"\bsagemaker\b",
    "bigquery": r"\bbigquery\b",
    "redshift": r"\bredshift\b",
    "postgres": r"\bpostgre(?:s|sql)\b",
    "mongodb": r"\bmongo(?:db)?\b",
    "nosql": r"\bnosql\b",
    "elastic": r"\belasticsearch\b",
    "linux": r"\blinux\b",
    "microservices": r"\bmicro-?services\b",
    "graphql": r"\bgraphql\b",
    "matlab": r"\bmatlab\b",
    "kdb": r"\bkdb\b",
    # THE C LANGUAGE (the user, 2026-10-05: "juste C et d'autres termes techniques
    # pour le code"). The letter alone is not enough: \bC\b matches "C'est",
    # "catégorie C", "Pôle C". We only recognise it announced as a language
    # ("langage C") or in a list of languages ("Python, C", "C/C++").
    # C and C++ are only ONE family: "C/C++" is one skill, not two.
    "c": r"\bc\+\+"
    r"|\b(?:langage|language|programming\s+in|programmation\s+en)\s+C\b(?![+#'’])"
    r"|\b(?:python|java|rust|fortran|go|matlab|julia|c\+\+|c#)\s*[,/]\s*C\b(?![+#'’])"
    r"|\bC\s*[,/]\s*(?:c\+\+|c#|python|java|rust|fortran|assemb)",
    "fortran": r"\bfortran\b",
    "assembleur": r"\bassembl(?:eur|y\s+language|er)\b",
    "embarque": r"\b(?:embedded\s+(?:software|systems?|c)|logiciel\s+embarqu|syst[eè]mes?\s+embarqu|firmware|rtos)\b",
    "hdl": r"\b(?:vhdl|verilog|fpga)\b",
    "perl": r"\bperl\b",
    "php": r"\bphp\b",
    # SWIFT is first of all the payment network in finance: the language only counts
    # next to Kotlin, iOS or Objective-C.
    "ruby": r"\bruby\b",
    "swift": r"\bswiftui\b|\bswift\s*(?:,|/|et|and|ou|or)\s*(?:kotlin|objective|ios)"
    r"|\b(?:kotlin|ios|objective-c)\s*(?:,|/|et|and|ou|or)\s*swift\b",
    "kotlin": r"\bkotlin\b",
    "dotnet": r"(?<!\w)\.net\b|\bdotnet\b|\basp\.net\b",
    "spring": r"\bspring\s+(?:boot|framework)\b",
    "angular": r"\bangular(?:js)?\b",
    "vue": r"\bvue\.?js\b",
    "ansible": r"\bansible\b",
    "openshift": r"\bopenshift\b",
    "shell": r"\b(?:bash|shell\s+script\w*|powershell)\b",
}
_RX_OUTILS = {k: re.compile(v, re.I) for k, v in _OUTILS.items()}
_PARESSEUX["OUTILS_MAX"] = lambda: int(_ici._TRI.get("outils_max", 4) or 0)  # 0 = no limit


def outils_techniques(desc: str | None) -> set[str]:
    """Families of engineer tools cited in the description."""
    t = str(desc or "")
    return {k for k, rx in _RX_OUTILS.items() if rx.search(t)}


# ── 3. EXPERIENCE ───────────────────────────────────────────────────────────
# Five years. Below that, a junior application can hold its own; above, the posting
# asks for a background that does not exist yet.
_PARESSEUX["EXP_MAX"] = lambda: int(_P.get("niveau.experience_max", 5) or 99)
_PARESSEUX["_SENIORITE"] = lambda: bool(_ici._TRI.get("retirer_seniors", True))
_PARESSEUX["_ETUDIANT"] = lambda: bool(_ici._TRI.get("retirer_etudiants", True))
# The person's own job, when its title carries a seniority word ("Chef de rayon",
# "Responsable logistique"): written by first_launch, it is never removed as senior.
_PARESSEUX["_RX_PROPRE_METIER"] = lambda: _P.motif(_ici._TRI.get("seniorite_sauf"))

# ── 4. LIENS MORTS ──────────────────────────────────────────────────────────
# ANTI-BOT is NOT a dead link: it is a page that could not be read, not
# an offer that no longer exists. 312 offers are in this case; throwing them away would
# lose live offers because of a reading failure.
LIENS_MORTS = {"MORT", "EXPIREE", "FERMEE"}


# ── 5. WHAT IS NOT AN OFFER ─────────────────────────────────────────────────
# The July import left rows that lead to no posting: a
# home page ("ecocert.com/fr-FR/home"), a generic careers portal
# ("careers.societegenerale.com"), a SEARCH page ("indeed.com/q-…-
# emplois"), or nothing at all. "Amundi — Analyste ESG / Sustainable Product /
# Climate", fit 10, did not even have a URL: only a recruiter search link
# in the rh field, and fields filled by hand ("#1 EU AM…").
# The user, on 2026-10-05: "n'existe pas". Measured: 34 rows.
# The tracking still protects them (an application is noted there even without a link).
_RX_PORTAIL = re.compile(
    r"^/?(?:[a-z]{2}(?:-[a-z]{2})?/)?(?:home|accueil|careers?|carrieres?(?:/recrutement)?"
    r"|jobs?|emplois?|offres?|recrutement|join-us|why-join-us|nous-rejoindre)?/?$",
    re.I,
)
_RX_PAGE_RECHERCHE = re.compile(
    r"indeed\.[a-z.]+/q-|indeed\.[a-z.]+/jobs\?|linkedin\.com/jobs/[a-z0-9-]+-emplois"
    r"|linkedin\.com/jobs/search|linkedin\.com/search/|glassdoor\.[a-z.]+/emploi/.*srch"
    r"|welcometothejungle\.com/[a-z]{2}/jobs(?:\?|$)|/jobs/search",
    re.I,
)


def pas_une_offre(o: Offre) -> str | None:
    """Reason if the row leads to no specific posting, otherwise None."""
    from urllib.parse import urlsplit

    u = (o.get("url") or "").strip()
    if not u.startswith("http"):
        return "pas_une_offre:sans_lien"
    if _RX_PAGE_RECHERCHE.search(u):
        return "pas_une_offre:recherche"
    s = urlsplit(u)
    if "smartrecruiters.com" in s.netloc and s.path.strip("/").count("/") == 0:
        return "pas_une_offre:portail"
    if _RX_PORTAIL.match(s.path or "/") and not s.query:
        return "pas_une_offre:accueil_ou_portail"
    return None


def _oid(o: Offre) -> str:
    return f"{(o.get('entreprise') or '').strip()}|{(o.get('poste') or '').strip()}"


def motif(o: Offre, proteges: set[str]) -> str | None:
    """Deletion reason, or None if the offer is kept."""
    if _oid(o) in proteges:
        return None
    # BEFORE the SEARCH guard: the three SEARCH rows of the queue had
    # no URL at all, the guard protected empty rows.
    m = pas_une_offre(o)
    if m:
        return m
    if (o.get("url_type") or "") == "RECHERCHE":
        return None

    titre = o.get("poste") or ""

    if (o.get("link_status") or "") in LIENS_MORTS:
        return "lien_mort"

    exp = o.get("exp_requise")
    if isinstance(exp, int) and exp >= _ici.EXP_MAX:
        return "experience"

    # A posting that asks for a candidate STILL a student is not for a
    # graduate, whatever contract is shown: Euronext "VIE - ESG &
    # Sustainable Finance Analyst" wants a "final or penultimate year
    # student" (the user, 2026-10-07). The contract taken from the title (V.I.E)
    # came before the description, the offer stayed at fit 10.
    from jobhunter.sources.common import demande_etudiant

    if _ici._ETUDIANT and demande_etudiant(o.get("description")):
        return "etudiant"

    propre = _P.cherche(_ici._RX_PROPRE_METIER, titre)
    if _ici._SENIORITE and not propre and _RX_SENIOR_DUR.search(titre):
        return "seniorite"
    if (
        _ici._SENIORITE
        and not propre
        and _RX_SENIOR_MOU.search(_sans_resp_adjectif(titre))
        and not _RX_JUNIOR.search(titre)
    ):
        return "seniorite"

    sauve = _P.cherche(_ici._RX_SAUVETAGE, titre)
    for famille, rx in _ici._METIERS.items():
        if rx.search(titre) and (famille in _ici._METIERS_DURS or not sauve):
            return f"metier:{famille}"
    if _ici.OUTILS_MAX and len(outils_techniques(o.get("description"))) >= _ici.OUTILS_MAX:
        return "outils_techniques"
    return None


def main() -> int:
    """Command line: sorting of the queue (inspection, or purge with --supprime)."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--supprime", action="store_true", help="ecrit la file purgee")
    ap.add_argument("--motifs", action="store_true", help="echantillon par motif")
    ap.add_argument("--garde", action="store_true", help="echantillon de ce qui reste")
    ap.add_argument("--echantillon", type=int, default=20)
    a = ap.parse_args()

    q = importlib.import_module("jobhunter.storage.queue").charger(
        QUEUE
    )  # descriptions: outils_techniques reads them
    proteges = (
        set(importlib.import_module("jobhunter.storage.applications").charger(SUIVI))
        if SUIVI.exists()
        else set()
    )

    garde: list[tuple[str | None, Offre]] = []
    jette: list[tuple[str | None, Offre]] = []
    for o in q:
        m = motif(o, proteges)
        (jette if m else garde).append((m, o))
    # Duplicates among what remains: same posting under two titles or in
    # two languages (doublons.py). After the reasons, so as to keep only
    # offers that survive anyway.
    from jobhunter.programs import duplicates as doublons

    dbl = doublons.doublons([o for _, o in garde], proteges)
    jette += [("doublon", o) for _, o in garde if _oid(o) in dbl]
    garde = [(m, o) for m, o in garde if _oid(o) not in dbl]

    import collections

    cnt = collections.Counter(m for m, _ in jette)
    print(f"file : {len(q)} offres")
    print(f"  conservees : {len(garde)}")
    print(f"  supprimees : {len(jette)}\n")
    for m, n in cnt.most_common():
        print(f"    {m:24} {n:5}")

    if a.motifs:
        for m in [x for x, _ in cnt.most_common()]:
            lot = [o for mm, o in jette if mm == m]
            print(f"\n── {m} ({len(lot)}) ──")
            for o in lot[: a.echantillon]:
                print(
                    f"   fit {o.get('fit'):>2} exp {str(o.get('exp_requise')):>2}  "
                    f"{(o.get('entreprise') or '')[:22]:24}{(o.get('poste') or '')[:58]}"
                )

    if a.garde:
        reste = [o for _, o in garde]
        reste.sort(key=lambda o: -(o.get("fit") or 0))
        print("\n── conservees, du meilleur fit au moins bon ──")
        for o in reste[: a.echantillon]:
            print(
                f"   fit {o.get('fit'):>2}  {(o.get('entreprise') or '')[:22]:24}"
                f"{(o.get('poste') or '')[:58]}"
            )
        print("   ...")
        for o in reste[-a.echantillon :]:
            print(
                f"   fit {o.get('fit'):>2}  {(o.get('entreprise') or '')[:22]:24}"
                f"{(o.get('poste') or '')[:58]}"
            )

    if not a.supprime:
        print("\n[INSPECTION] rien n'a ete ecrit. --supprime pour purger.")
        return 0

    sauv = QUEUE.with_suffix(f".json.avant_tri_{time.strftime('%Y%m%d_%H%M%S')}")
    shutil.copy2(QUEUE, sauv)
    print(f"\nsauvegarde : {sauv.name}")
    # ONE PER DAY SINCE THE PIPELINE SORTS. 9 MB each, endlessly: we keep
    # the last five. The name carries the timestamp, so alphabetical order
    # is chronological order.
    for vieille in sorted(QUEUE.parent.glob(QUEUE.name + ".avant_tri_*"))[:-5]:
        try:
            vieille.unlink()
        except OSError:
            pass

    from jobhunter.storage import queue as queue_io

    # THE REASON IS RECOMPUTED HERE, inside the lock, on the RE-READ queue. The objects
    # of the inspection come from another read: their Python identity says
    # nothing about these, and an `id(o)` of one batch would find nothing in the other.
    # transaction() purges on its own the descriptions that became orphaned.
    try:
        with queue_io.transaction() as file:
            avant = len(file)
            retires = {}
            gardes = []
            for o in file:
                m = motif(o, proteges)
                if m:
                    retires[queue_io.oid(o)] = m
                else:
                    gardes.append(o)
            dbl = doublons.doublons(gardes, proteges)
            retires.update(dbl)
            file[:] = [o for o in gardes if queue_io.oid(o) not in dbl]
            # The ranks are renumbered: "n" serves as a display identifier in
            # the app, and gaps of several thousand help nobody.
            for i, o in enumerate(file, 1):
                o["n"] = i
            restant = len(file)
    except queue_io.VerrouIndisponible as e:
        # Project convention: queue busy = code 3, nothing changed. Without
        # this, a traceback and code 1 — the pipeline could not tell
        # "someone is writing" from "the sorting crashed".
        print(f"! {e}")
        return 3
    print(f"file purgee : {avant} → {restant} offres ({avant - restant} supprimees)")
    # The collection must not take them back tomorrow: see rejets_tri.py.
    from jobhunter.programs import sort_rejections as rejets_tri

    n = rejets_tri.ajouter(retires)
    print(f"rejets memorises : {n} (la collecte les ignore {rejets_tri.DUREE_JOURS} jours)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
