"""Collecte d'offres : une source par module, fusion directe dans apply_queue.json.

Ancien Scripts/job_sources.py (4 855 lignes), decoupe en phase 3.4 du plan :

commun         reglages (mots-cles, slugs, flux), filtre d'intitule, contrats, pays, `_mk`
ats            API publiques d'ATS (Greenhouse, Lever, Ashby...) et autres API de recrutement
workday        Workday
linkedin       recherche publique LinkedIn (API invite), attente sur 429
wtj, efc       Welcome to the Jungle, eFinancialCareers (sitemaps publics)
eures          portail europeen
indeed, apec, glassdoor   pages de resultats, arret net sur refus
vie, fir, talent, francetravail, agregateurs   V.I.E, FIR, Talent.com, France Travail, Adzuna/Jooble
fusion         fusion dans la file : dedoublonnage, promotion d'URL, scoring
cli            la ligne de commande (`python -m jobhunter.sources` ou Scripts/job_sources.py)

FACADE (jobhunter._facade). `import jobhunter.sources` (et donc `import job_sources`) donne un module qui
voit TOUS les noms des sous-modules, comme l'ancien fichier unique : `js.title_ok`,
`js.scan_linkedin`, `js.MONDE`. Une affectation (`js.KEYWORDS = [...]`, un monkeypatch)
part dans le sous-module qui POSSEDE le nom ; les autres le lisent par `_commun.KEYWORDS`,
jamais par copie. Sans ce routage, un test qui remplace `_get_borne` laisserait la
collecte sortir sur le vrai reseau.
"""

import re

from jobhunter import _facade

_SOUS_MODULES = (
    "commun",
    "ats",
    "workday",
    "linkedin",
    "wtj",
    "efc",
    "eures",
    "indeed",
    "apec",
    "glassdoor",
    "fusion",
    "vie",
    "fir",
    "talent",
    "francetravail",
    "agregateurs",
    "cli",
)
_MODULES = _facade.installer(__name__, _SOUS_MODULES)


def _motifs():
    """Toutes les regex compilees des sous-modules : {(module, nom): motif}."""
    return {
        (m.__name__.rsplit(".", 1)[1], n): v
        for m in _MODULES
        for n, v in vars(m).items()
        if isinstance(v, re.Pattern) and isinstance(v.pattern, str)
    }


def _verifier_motifs():
    # TOUTE regex compilee de la collecte, quel que soit son nom et son sous-module.
    # Le controle ne regardait autrefois que le prefixe `_RX_` et laissait passer
    # _DOMAIN_RX, _HARD_NEG_RX, _AI_RX... — exactement les motifs de title_ok, le filtre
    # qui decide ce qui entre dans la file. Un garde-fou qui ne couvre pas le code le
    # plus expose ne garde rien.
    vus = 0
    for (_m, _n), _rx in _motifs().items():
        vus += 1
        assert "\x08" not in _rx.pattern, f"{_m}.{_n} : backspace au lieu de \\b"
        assert "\\\\b" not in _rx.pattern, f"{_m}.{_n} : antislash litteral au lieu de \\b"
    # La collecte en compte 27. Si ce nombre s'effondre, la selection ci-dessus ne
    # trouve plus rien — une panne muette de plus.
    assert vus >= 20, f"_verifier_motifs ne voit que {vus} motifs : selection cassee"


_verifier_motifs()
