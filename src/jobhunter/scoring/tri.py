"""jobhunter.scoring.tri — Separe ce qui colle au profil de ce qui n'y colle pas, et purge. (ancien Scripts/tri_file.py)

POURQUOI PAS LE FIT. Le fit mesure la DENSITE DE VOCABULAIRE ESG et finance,
pas l'adequation d'un poste a un candidat junior. Mesure sur la file du
18/09/2026 (9492 offres) :

    fit 6 : « JPMorganChase — 2027 Corporate & Investment Bank, Global
             Investment Banking »          -> exactement la cible
    fit 7 : « septeo — AI Tech Lead »       -> ni junior, ni finance
    fit 7 : « talan — Data Engineer Confirme / Senior »
    fit 1 : « Coca-Cola HBC — Financial Analyst »

Trier au fit supprimerait le premier et garderait les deux suivants. Le fit
sert a CLASSER ce qui reste ; il ne sert pas a jeter.

CE QUI TRANCHE, c'est l'INTITULE et l'EXPERIENCE EXIGEE. Un intitule dit ce
qu'est le poste et a quel niveau ; l'annee d'experience dit si la porte est
ouverte. l'utilisateur sort d'un BBA avec un stage : au-dela de cinq ans exiges,
l'offre n'est pas refusable, elle est inaccessible.

QUATRE MOTIFS DE SUPPRESSION, du plus sur au plus discutable :

  lien_mort   le lien ne mene plus a rien (MORT / EXPIREE / FERMEE)
  experience  exp_requise >= 5 ans
  seniorite   l'intitule dit senior, confirme, director, head of, VP...
  metier      l'intitule designe un metier hors profil (dev, vente, RH,
              sante, logistique, restauration, enseignement...)

CE QUI N'EST JAMAIS SUPPRIME :
  - les lignes de RECHERCHE enregistrees (url_type == RECHERCHE)
  - toute offre presente dans suivi.json (candidature envoyee ou suivie)

NI `action`, NI `statut` NE PROTEGENT. Les deux ressemblent a des marques
manuelles et n'en sont pas. `action == "1"` porte sur 629 lignes, toutes
importees en juillet : AUCUN programme ne l'ecrit, et le lot contient
« Manager SAP FICO S/4HANA ». `statut == "Oui"` (523 lignes) vient du meme
import. Le vrai suivi est dans suivi.json, ecrit par _set_statut de l'app —
c'est donc lui, et lui seul, qui protege.

L'IA ET LA DATA RESTENT. Le profil les vise explicitement (axe « ia » du
scoring, competences « vibe coding », « agents IA », « Python / SQL »). On ne
supprime que l'INGENIERIE logicielle — ML engineer, data engineer, devops,
architecte — pas les postes d'analyse ou de conseil qui portent « IA ».

Run :
  python JobHunter.pyw tri                 # inspection seule, rien n'est ecrit
  python JobHunter.pyw tri --motifs        # + echantillon de 20 titres par motif
  python JobHunter.pyw tri --garde         # + echantillon de ce qui est CONSERVE
  python JobHunter.pyw tri --supprime      # ecrit, apres sauvegarde horodatee
"""

import argparse
import importlib
import re
import shutil
import sys
import time
from pathlib import Path  # noqa: F401  (annotations et appelants)

from jobhunter import racine as _racine
from jobhunter.types import Offre

HERE = _racine.scripts()
# TRANSITION (phase 3) : imports differes de modules encore dans Scripts/
# (job_sources, doublons, rejets_tri). A retirer quand ils auront rejoint le paquet.
_SCRIPTS = _racine.scripts()
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))
sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)  # type: ignore[union-attr]  # console : TextIOWrapper

QUEUE = HERE / "apply_queue.json"
SUIVI = HERE / "suivi.json"

# ── 1. SENIORITE ────────────────────────────────────────────────────────────
# Deux listes, parce que deux niveaux de certitude.
#
# DUR : le mot ne veut rien dire d'autre que « pas pour un debutant ».
#   « sr » est borne des deux cotes : sans bornes il attrape « sRisque ».
#   « vp » de meme : « vp » dans « vpn ».
_RX_SENIOR_DUR = re.compile(
    r"\b(?:senior|sr|confirm[ée]{1,2}s?|exp[ée]riment[ée]{1,2}s?"
    r"|director|directeur|directrice|head\s+of|vice[\s-]?pr[ée]sident"
    r"|vp|chief|principal|partner|associ[ée]\s+g[ée]rant)\b",
    re.I,
)

# MOU : le mot dit souvent la seniorite, mais pas toujours. Neutralise quand
# l'intitule porte par ailleurs une marque de debutant — « Management Trainee »
# contient « manage », « Graduate Programme Manager » est deja exclu ailleurs.
#
#   « lead » : « Lead Generation » est du commercial, pas de la seniorite. Ce
#   faux positif a deja ete corrige une fois dans ats_match._RX_SENIOR_FIN ; on
#   reprend la meme negation ici plutot que de la redecouvrir.
#   « expert » : « expert comptable » part de toute facon par le motif metier.
_RX_SENIOR_MOU = re.compile(
    r"\b(?:manager|managing|lead(?!\s+(?:generation|gen)\b)|responsable"
    r"|expert[e]?s?|chef\s+de|g[ée]rant[e]?|superviseur)\b",
    re.I,
)

# « RESPONSABLE » EST DEUX MOTS. Le nom designe un chef de service — « Responsable
# Tresorerie », a jeter. L'adjectif qualifie une demarche — « Conseiller en
# Epargne Responsable », qui est exactement la cible, et que le filtre de
# seniorite supprimait. « Investissement responsable » est un terme standard du
# metier : le cas est rare dans la file du jour (1 offre) mais revient a chaque
# scan.
#
# Une negation dans `_RX_SENIOR_MOU` demanderait un lookbehind de largeur
# variable, que Python refuse. On retire donc l'emploi adjectival du titre AVANT
# de chercher la seniorite — meme procede que `_sans_marque` dans
# tailor_application, qui efface « Credit Agricole » avant de compter l'agricole.
#
# Pas de \b final sur « responsable » : il doit voir « responsables » au pluriel.
_RX_RESP_ADJ = re.compile(
    r"\b(?:[eé]pargnes?|investissements?|financements?|finance|placements?|gestion"
    r"|achats?|approvisionnements?|consommation|croissance|entreprises?|num[eé]rique"
    r"|innovation|cha[iî]ne|tourisme|voyages?|marketing|communication)"
    r"\s+responsables?",
    re.I,
)


def _sans_resp_adjectif(titre: str | None) -> str:
    """Le titre prive de ses « responsable » adjectifs, pour le test de seniorite."""
    return _RX_RESP_ADJ.sub(" ", titre or "")


# Marques de debutant. Neutralisent la liste MOU, jamais la liste DUR.
#
# PAS DE \b FINAL sur les radicaux. « alternan[ct]\b » ne voyait PAS
# « Alternance » : apres « alternanc » vient « e », donc pas de frontiere de mot.
# « Alternance – Chef de Projet IA & Data » partait comme poste de seniorite.
# C'est le meme defaut que le \b final de _RX_DURABLE, corrige ce matin dans
# tailor_application. Les sigles courts, eux, GARDENT leurs bornes : « jr »
# sans borne droite attraperait « jrXXX », « vie » attraperait « vieillissement ».
_RX_JUNIOR = re.compile(
    r"\b(?:jr|intern|stage|entry[\s-]level|v\.?i\.?e)\b"
    r"|\b(?:junior|graduate|trainee|stagiaire|internship"
    r"|alternan|apprenti|d[ée]butant|jeunes?\s+dipl[oô]m"
    r"|young\s+(?:graduate|talent|professional)|assistant)\w*",
    re.I,
)

# ── 2. METIERS HORS PROFIL ──────────────────────────────────────────────────
# Un dictionnaire motif -> famille, pour pouvoir dire POURQUOI une offre part
# et verifier chaque famille separement. Chaque motif a ete relu contre le
# piege des sous-chaines, qui a produit huit bugs sur ce projet :
# « sinGAPore », « diveRSE », « CLIMATisation », « transVERSE », « POWER
# Platform », « BP dans BPCE ». Tout est borne.
_METIERS_CATALOGUE = {  # toutes les familles connues
    # QUANT ET INGENIERIE DATA : hors cible meme avec « ESG » dans le titre
    # (l'utilisateur, 2026-10-05). « Analyste Climate Finance / ESG Quant » ou « ESG
    # Data Engineer » sortaient a fit 10 : le mot ESG levait le sauvetage, alors
    # que le metier reste du calcul quantitatif ou de la tuyauterie de donnees.
    # D'ou leur place dans _METIERS_DURS. « quantity » (surveyor) et
    # « quantification » ne sont pas pris : seules les formes du metier.
    "quant": re.compile(r"\b(?:quants?|quantitati(?:ve|ves|f|fs)|structur(?:er|eur)s?)\b", re.I),
    "ingenierie_data": re.compile(
        r"\b(?:data\s+engineer(?:ing|s)?|big\s+data\s+engineer|analytics\s+engineer"
        r"|data\s+platform\s+engineer|ing[ée]nieure?\s+(?:data|donn[ée]es|big\s+data)"
        r"|ingenier[oa]\s+de\s+datos|engenheir[oa]\s+de\s+dados)\b",
        re.I,
    ),
    # Ingenierie logicielle et infrastructure. L'ANALYSE data reste (voir plus
    # bas _RX_DATA_GARDE) ; c'est le metier de DEVELOPPEUR qui part.
    "informatique": re.compile(
        r"\b(?:d[ée]veloppeur|d[ée]veloppeuse|developer|dev\s+(?:back|front|full)"
        # « AI engineer » n'est PLUS rejete sur le titre (l'utilisateur, 2026-10-05) :
        # c'est l'outillage exige qui tranche, voir OUTILS_MAX plus bas.
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
    # Vente. « commercial » seul est trop large — « banque commerciale »,
    # « immobilier commercial », « credit commercial » sont de la finance. On
    # ne prend donc QUE les formes ou il designe la personne.
    #
    # « business development » NON PLUS n'est pas pris seul. Sur les vingt
    # premieres prises du motif, sept etaient des « Business Development
    # Analyst » — chez TotalEnergies Singapour (fit 8), au CEO Office de Telco OI
    # (fit 9), en graduate programme chez Sibelco. C'est un poste d'analyse
    # strategique, pas un poste de vendeur. Seuls partent le DEVELOPPEUR
    # commercial et ses titres explicites.
    #
    # « negociateur » est parti de la liste : il designe l'agent immobilier,
    # mais aussi le NEGOCIATEUR DE MARCHE — « Negociateur Credit » chez Natixis
    # Investment Managers est une table de trading, pas une agence.
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
    # SEULEMENT les titres academiques, et ils ne sont PAS rattrapables : un
    # post-doctorat « AI for Sustainable Energy » coche tous les mots-cles ESG
    # et reste inaccessible a un BBA. « formateur », « animateur » et
    # « educateur » ont quitte cette liste — ce sont des mots de contexte, pas
    # des metiers : « Comptable ECF - Cabinet Formateur » decrit un cabinet,
    # « Animateur securite environnement » est un poste HSE.
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

# ── CE QUI RESTE MALGRE UN MOTIF METIER ─────────────────────────────────────
# Trois intitules reels que les motifs ci-dessus attrapaient a tort :
#   « Analyste RH et controle de gestion sociale »  -> le cœur est le controle
#   « Sustainable Procurement Analyst »             -> achats responsables, ESG
#   « Business Analyst Finance »                    -> « business » n'est pas
#                                                      « business developer »
# La regle : un intitule qui porte un marqueur ESG ou un metier finance FRANC
# n'est pas jete par un mot de metier isole.
# DEUX GROUPES, parce que deux comportements de bornes opposes.
#
#   Les SIGLES gardent leurs deux bornes. « rse » sans borne droite matche
#   « diveRSE », « esg » matcherait « esgXXX » — c'est la famille de bugs qui
#   a deja donne « sinGAPore », « CLIMATisation » et « BP dans BPCE ».
#   Les RADICAUX perdent la borne droite, sinon ils ne voient pas leurs propres
#   flexions : « sustainab\b » rate « Sustainability », « durabilit\b » rate
#   « durabilite ». Deux offres a fit 10 partaient ainsi au motif « logistique »
#   — « Trainee Sustainability & Strategic Regulatory » chez PwC et « Working
#   Student Sustainable Procurement » chez Sika.
from typing import Any

from jobhunter import paresseux as _paresseux
from jobhunter import profil as _P

_ici = sys.modules[__name__]
# Valeurs tirees du profil : calculees a la premiere lecture, pas a l'import
# (jobhunter.paresseux). Dans ce module, on les lit par `_ici.NOM`.
_PARESSEUX: _paresseux.Fabriques = {}


def __getattr__(nom: str) -> Any:
    return _paresseux.lire(_ici, _PARESSEUX, nom)


_PARESSEUX["_TRI"] = lambda: _P.get("tri", {}) or {}
# Mots de la CIBLE qui sauvent un intitule d'une famille ecartee (profil,
# tri.sauvetage) : « Sustainable Procurement » reste pour un profil durable.
_PARESSEUX["_RX_SAUVETAGE"] = lambda: _P.motif(_ici._TRI.get("sauvetage"))

# FAMILLES QUE LE SAUVETAGE NE RATTRAPE PAS. Un mot ESG dans l'intitule ne
# rend pas le poste accessible : un post-doctorat « AI for Sustainable Energy »
# demande un doctorat, une « Analyse environnementale en salle blanche » demande
# un diplome d'ingenieur, un poste de soignant demande un diplome d'Etat. Le
# sauvetage sert a ne pas jeter un poste de FINANCE sur un mot de contexte ; il
# ne sert pas a ouvrir des metiers fermes.
_PARESSEUX["_METIERS_DURS"] = lambda: set(_ici._TRI.get("metiers_durs", []) or [])
# Familles RETIREES pour ce profil (tri.metiers_exclus) ; le catalogue
# _METIERS_CATALOGUE ci-dessus reste la bibliotheque. Absent du profil = toutes.
_PARESSEUX["_EXCLUS"] = lambda: _ici._TRI.get("metiers_exclus")
_PARESSEUX["_METIERS"] = lambda: (
    dict(_METIERS_CATALOGUE)
    if _ici._EXCLUS is None
    else {k: v for k, v in _METIERS_CATALOGUE.items() if k in set(_ici._EXCLUS)}
)

# ── 2 bis. TROP D'OUTILS DE DEVELOPPEMENT ───────────────────────────────────
# « Garde AI engineer, mais quand il faut trop d'outils techniques pour coder,
# supprime » (l'utilisateur, 2026-10-05). L'intitule ne suffit pas : « Consultant
# Business & AI Insights » chez Deloitte demande Databricks, Snowflake,
# Kubernetes et CI/CD ; un « AI Analyst » peut ne demander que Python.
#
# On compte des FAMILLES d'outils d'ingenieur dans la description. Ne comptent
# pas : Python, SQL, Excel, VBA, Power BI, Tableau, R (outils d'analyste, ceux
# du profil) ni git (trop banal). AWS, GCP et Azure ne font qu'UNE famille :
# « AWS, GCP ou Azure » est une alternative, pas trois exigences.
# Mesure sur la file (7336 offres) : seuil 4 -> 189 offres, dont 2 a fit >= 9
# (« ESG Data Engineer », un « Data & AI Solutions Analyst » qui demande FastAPI,
# Postgres, CI/CD et le cloud). Seuil 3 en prenait 313, dont de vrais postes
# d'analyse qui citent un cloud et deux bases.
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
    # LE LANGAGE C (l'utilisateur, 2026-10-05 : « juste C et d'autres termes techniques
    # pour le code »). La lettre seule ne suffit pas : \bC\b matche « C'est »,
    # « catégorie C », « Pôle C ». On ne le reconnait qu'annonce comme langage
    # (« langage C ») ou dans une liste de langages (« Python, C », « C/C++ »).
    # C et C++ ne font qu'UNE famille : « C/C++ » est une competence, pas deux.
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
    # SWIFT est d'abord le reseau de paiement en finance : le langage ne compte
    # qu'a cote de Kotlin, iOS ou Objective-C.
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
_PARESSEUX["OUTILS_MAX"] = lambda: int(_ici._TRI.get("outils_max", 4) or 0)  # 0 = pas de limite


def outils_techniques(desc: str | None) -> set[str]:
    """Familles d'outils d'ingenieur citees dans la description."""
    t = str(desc or "")
    return {k for k, rx in _RX_OUTILS.items() if rx.search(t)}


# ── 3. EXPERIENCE ───────────────────────────────────────────────────────────
# Cinq ans. En dessous, une candidature junior se defend ; au-dessus, l'annonce
# demande un parcours qui n'existe pas encore.
_PARESSEUX["EXP_MAX"] = lambda: int(_P.get("niveau.experience_max", 5) or 99)
_PARESSEUX["_SENIORITE"] = lambda: bool(_ici._TRI.get("retirer_seniors", True))
_PARESSEUX["_ETUDIANT"] = lambda: bool(_ici._TRI.get("retirer_etudiants", True))

# ── 4. LIENS MORTS ──────────────────────────────────────────────────────────
# ANTI-BOT n'est PAS un lien mort : c'est une page qu'on n'a pas pu lire, pas
# une offre qui n'existe plus. 312 offres sont dans ce cas ; les jeter ferait
# perdre des offres vivantes pour un defaut de lecture.
LIENS_MORTS = {"MORT", "EXPIREE", "FERMEE"}


# ── 5. CE QUI N'EST PAS UNE OFFRE ───────────────────────────────────────────
# L'import de juillet a laisse des lignes qui ne menent a aucune annonce : une
# page d'accueil (« ecocert.com/fr-FR/home »), un portail carriere generique
# (« careers.societegenerale.com »), une page de RECHERCHE (« indeed.com/q-…-
# emplois »), ou rien du tout. « Amundi — Analyste ESG / Sustainable Product /
# Climate », fit 10, n'avait meme pas d'URL : seulement un lien de recherche de
# recruteurs dans le champ rh, et des champs remplis a la main (« #1 EU AM… »).
# l'utilisateur, le 2026-10-05 : « n'existe pas ». Mesure : 34 lignes.
# Le suivi les protege toujours (une candidature y est notee meme sans lien).
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
    """Motif si la ligne ne mene a aucune annonce precise, sinon None."""
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
    """Motif de suppression, ou None si l'offre est conservee."""
    if _oid(o) in proteges:
        return None
    # AVANT la garde RECHERCHE : les trois lignes RECHERCHE de la file n'avaient
    # pas d'URL du tout, la garde protegeait des lignes vides.
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

    # Une annonce qui demande un candidat ENCORE etudiant n'est pas pour un
    # diplome, quel que soit le contrat affiche : Euronext « VIE - ESG &
    # Sustainable Finance Analyst » veut un « final or penultimate year
    # student » (l'utilisateur, 2026-10-07). Le contrat venu de l'intitule (V.I.E)
    # passait avant la description, l'offre restait a fit 10.
    from jobhunter.sources.commun import demande_etudiant

    if _ici._ETUDIANT and demande_etudiant(o.get("description")):
        return "etudiant"

    if _ici._SENIORITE and _RX_SENIOR_DUR.search(titre):
        return "seniorite"
    if (
        _ici._SENIORITE
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
    ap = argparse.ArgumentParser()
    ap.add_argument("--supprime", action="store_true", help="ecrit la file purgee")
    ap.add_argument("--motifs", action="store_true", help="echantillon par motif")
    ap.add_argument("--garde", action="store_true", help="echantillon de ce qui reste")
    ap.add_argument("--echantillon", type=int, default=20)
    a = ap.parse_args()

    q = importlib.import_module("jobhunter.stockage.file").charger(
        QUEUE
    )  # descriptions : outils_techniques les lit
    proteges = (
        set(importlib.import_module("jobhunter.stockage.suivi").charger(SUIVI))
        if SUIVI.exists()
        else set()
    )

    garde: list[tuple[str | None, Offre]] = []
    jette: list[tuple[str | None, Offre]] = []
    for o in q:
        m = motif(o, proteges)
        (jette if m else garde).append((m, o))
    # Doublons parmi ce qui reste : meme annonce sous deux intitules ou dans
    # deux langues (doublons.py). Apres les motifs, pour ne garder que des
    # offres qui survivent de toute facon.
    from jobhunter.programmes import doublons

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
    # UNE PAR JOUR DEPUIS QUE LE PIPELINE TRIE. 9 Mo chacune, sans fin : on garde
    # les cinq dernieres. Le nom porte l'horodatage, donc l'ordre alphabetique
    # est l'ordre chronologique.
    for vieille in sorted(QUEUE.parent.glob(QUEUE.name + ".avant_tri_*"))[:-5]:
        try:
            vieille.unlink()
        except OSError:
            pass

    from jobhunter.stockage import file as queue_io

    # LE MOTIF EST RECALCULE ICI, dans le verrou, sur la file RELUE. Les objets
    # de l'inspection viennent d'une autre lecture : leur identite Python ne dit
    # rien de ceux-ci, et un `id(o)` d'un lot ne retrouverait rien dans l'autre.
    # transaction() purge d'elle-meme les descriptions devenues orphelines.
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
            # Les rangs se renumerotent : « n » sert d'identifiant d'affichage dans
            # l'app, et des trous de plusieurs milliers n'aident personne.
            for i, o in enumerate(file, 1):
                o["n"] = i
            restant = len(file)
    except queue_io.VerrouIndisponible as e:
        # Convention du projet : file occupee = code 3, rien de modifie. Sans
        # ceci, un traceback et un code 1 — le pipeline ne distinguait pas
        # « quelqu'un ecrit » de « le tri a plante ».
        print(f"! {e}")
        return 3
    print(f"file purgee : {avant} → {restant} offres ({avant - restant} supprimees)")
    # La collecte ne doit pas les reprendre demain : voir rejets_tri.py.
    from jobhunter.programmes import rejets_tri

    n = rejets_tri.ajouter(retires)
    print(f"rejets memorises : {n} (la collecte les ignore {rejets_tri.DUREE_JOURS} jours)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
