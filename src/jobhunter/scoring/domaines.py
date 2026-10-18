"""Domaine d'une offre d'apres son intitule, et le lexique LARGE du premier tamis.

Venu de Scripts/scrape_jobs.py (phase 3.4) : job_sources l'importait en tete, ce qui
liait la collecte au scraping des sites carriere ; scrape_jobs le re-exporte.
"""

import re
import sys
from typing import Any

from jobhunter import paresseux as _paresseux
from jobhunter import profil as _P

_ici = sys.modules[__name__]
# Valeurs tirees du profil : calculees a la premiere lecture, pas a l'import
# (jobhunter.paresseux). Dans ce module, on les lit par `_ici.NOM`.
_PARESSEUX: _paresseux.Fabriques = {}


def __getattr__(nom: str) -> Any:
    return _paresseux.lire(_ici, _PARESSEUX, nom)


# ── Lexique LARGE du filtre d'offres : profil.json, filtre_titre.lexique_large ──
# Liste de sous-chaines. Vide = tout passe ce premier tamis (title_ok resserre).
_PARESSEUX["ESG_FINANCE_KEYWORDS"] = lambda: (
    [k.lower() for k in (_P.get("filtre_titre.lexique_large", []) or [])]
)

DOMAINE_MAP = {
    "esg": "ESG_Finance_Durable",
    "finance": "Finance",
    "data": "Data_IA",
    "conseil": "Conseil",
    "risk": "Risk_Quant",
}

# SIGLES ET TERMES ESG QUE LA LISTE EN SOUS-CHAINES NE PEUT PAS PORTER.
#
# Mesure du 2026-09-22 : 51 offres dont l'intitule est explicitement ESG-finance
# recevaient une autre variante de CV — 45 la variante Finance/Investissement,
# 8 avec le document deja genere. « Analyste ISR » chez Malakoff (fit 10),
# « Analyste M&A / Sustainable Finance » a la SG (fit 9), « CSRD Reporting
# Analyst » chez Allianz Trade (fit 9).
#
# Deux trous distincts :
#   - la liste portait « sustainability » mais PAS « sustainable », donc
#     « Sustainable Finance » ne matchait rien ;
#   - les sigles isr et csrd manquaient tout court.
#
# Les sigles passent par une regex a FRONTIERES DE MOT, pas par la liste en
# sous-chaines : « isr » nu se retrouve au milieu d'autres mots, et ce depot a
# deja paye singapore pour « gap », diverse pour « rse » et Credit Agricole pour
# « agricol ». Les termes longs, eux, n'ont pas besoin de bornes.
_DOMAINES_RX: list[tuple[str, re.Pattern[str] | None]] | None = None


def classify_domaine(title: str) -> str:
    """Domaine de l'offre (cle d'un domaine du profil), d'apres son INTITULE.

    Le premier domaine dont un mot apparait gagne ; le DERNIER domaine du
    profil sert de repli. Le domaine decrit l'OFFRE, pas la cible : il choisit
    la variante de CV et le paragraphe de parcours de la lettre."""
    global _DOMAINES_RX
    if _DOMAINES_RX is None:
        _DOMAINES_RX = [(d["cle"], _P.motif(d.get("mots_titre"))) for d in _P.domaines()]
    t = (title or "").lower()
    for cle, rx in _DOMAINES_RX[:-1]:
        if rx is not None and rx.search(t):
            return cle
    return _DOMAINES_RX[-1][0]
    # DEFAUT NEUTRE. Il valait « ESG_Finance_Durable », si bien que 2151 offres
    # sur 2818 portaient ce domaine SANS aucun mot-clé ESG dans leur intitulé :
    # « Analyste DSI », « Financial Controller », « Business Analyst ». Elles
    # recevaient le CV ESG et, depuis les socles par domaine, une lettre qui
    # s'ouvre sur la finance durable — devant une compagnie pétrolière, ça
    # parle à côté. Le domaine doit décrire l'OFFRE, pas la cible de l'utilisateur.
    return "Finance"


def matches_esg_finance(title: str) -> bool:
    """Le titre touche-t-il au lexique ESG/Finance ? LARGE À DESSEIN.

    ⚠ Ce n'est PAS un filtre d'entrée. La liste contient « h/f », « social »,
    « data », « contrat » : « Plombier chauffagiste H/F » la passe. C'est un
    premier tamis, que `title_ok` (job_sources) resserre en exigeant un mot
    MÉTIER et en rejetant les rôles hors-cible. Pour décider si une offre
    entre, appeler `offre_retenue`, jamais cette fonction seule.
    """
    t = (title or "").lower()
    return not _ici.ESG_FINANCE_KEYWORDS or any(kw in t for kw in _ici.ESG_FINANCE_KEYWORDS)
