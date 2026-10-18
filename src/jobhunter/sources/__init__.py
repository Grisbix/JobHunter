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

FACADE. `import jobhunter.sources` (et donc `import job_sources`) donne un module qui
voit TOUS les noms des sous-modules, comme l'ancien fichier unique : `js.title_ok`,
`js.scan_linkedin`, `js.MONDE`. Une affectation (`js.KEYWORDS = [...]`, un monkeypatch)
part dans le sous-module qui POSSEDE le nom ; les autres le lisent par `_commun.KEYWORDS`,
jamais par copie. Sans ce routage, un test qui remplace `_get_borne` laisserait la
collecte sortir sur le vrai reseau.
"""

import importlib
import re
import sys
import types

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
_MODULES = [importlib.import_module(f"{__name__}.{m}") for m in _SOUS_MODULES]


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


# Les liaisons d'origine de chaque sous-module : `unittest.mock.patch` sort par un
# `delattr` sur la facade (le nom n'est pas dans SON dict) ; on remet alors la valeur
# d'origine au lieu d'effacer la fonction du sous-module.
_ORIGINE = {m: dict(vars(m)) for m in _MODULES}


def _proprietaires(nom):
    """Sous-modules ou `nom` est lie. Le proprietaire (celui qui le DEFINIT) en tete."""
    tenants = [m for m in _MODULES if nom in vars(m) or nom in _ORIGINE[m]]
    tenants.sort(key=lambda m: getattr(_ORIGINE[m].get(nom), "__module__", None) != m.__name__)
    return tenants


class _Facade(types.ModuleType):
    def __getattr__(self, nom):
        for m in _MODULES:
            if nom in vars(m):
                return vars(m)[nom]
        raise AttributeError(f"module {self.__name__!r} has no attribute {nom!r}")

    def __setattr__(self, nom, valeur):
        tenants = [] if nom.startswith("__") or nom in _SOUS_MODULES else _proprietaires(nom)
        if not tenants:
            super().__setattr__(nom, valeur)
            return
        # Tous les sous-modules qui lient le nom : le proprietaire, et ceux qui l'ont
        # importe tel quel (une fonction utilitaire, un compteur) — un remplacement doit
        # valoir partout ou la collecte le lit.
        for m in tenants:
            setattr(m, nom, valeur)

    def __delattr__(self, nom):
        if nom in vars(self):
            super().__delattr__(nom)
            return
        tenants = _proprietaires(nom)
        if not tenants:
            raise AttributeError(nom)
        for m in tenants:
            if nom in _ORIGINE[m]:
                setattr(m, nom, _ORIGINE[m][nom])
            else:
                delattr(m, nom)

    def __dir__(self):
        return sorted(set(super().__dir__()).union(*(vars(m) for m in _MODULES)))


sys.modules[__name__].__class__ = _Facade
