"""Domain of an offer from its title, and the WIDE lexicon of the first sieve.

Came from Scripts/scrape_jobs.py (phase 3.4): job_sources imported it at the top, which
tied the collection to the scraping of career sites; scrape_jobs re-exports it.
"""

import re
import sys
from typing import Any

from jobhunter import paresseux as _paresseux
from jobhunter import profil as _P

_ici = sys.modules[__name__]
# Values taken from the profile: computed on first read, not at import
# (jobhunter.paresseux). In this module, they are read through `_ici.NAME`.
_PARESSEUX: _paresseux.Fabriques = {}


def __getattr__(nom: str) -> Any:
    return _paresseux.lire(_ici, _PARESSEUX, nom)


# ── WIDE lexicon of the offer filter: profil.json, filtre_titre.lexique_large ──
# List of substrings. Empty = everything passes this first sieve (title_ok tightens).
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

# ESG ACRONYMS AND TERMS THAT THE SUBSTRING LIST CANNOT CARRY.
#
# Measured on 2026-09-22: 51 offers whose title is explicitly ESG-finance
# received another CV variant — 45 the Finance/Investissement variant,
# 8 with the document already generated. "Analyste ISR" at Malakoff (fit 10),
# "Analyste M&A / Sustainable Finance" at SG (fit 9), "CSRD Reporting
# Analyst » chez Allianz Trade (fit 9).
#
# Two distinct holes:
#   - the list carried "sustainability" but NOT "sustainable", so
#     "Sustainable Finance" matched nothing;
#   - the acronyms isr and csrd were simply missing.
#
# The acronyms go through a regex with WORD BOUNDARIES, not through the substring
# list: a bare "isr" turns up in the middle of other words, and this repository has
# already paid singapore for "gap", diverse for "rse" and Credit Agricole for
# "agricol". The long terms, on the other hand, do not need boundaries.
_DOMAINES_RX: list[tuple[str, re.Pattern[str] | None]] | None = None


def classify_domaine(title: str) -> str:
    """Domain of the offer (key of a profile domain), from its TITLE.

    The first domain one of whose words appears wins; the LAST domain of the profile
    serves as fallback. The domain describes the OFFER, not the target: it picks the CV
    variant and the background paragraph of the letter.
    """
    global _DOMAINES_RX
    if _DOMAINES_RX is None:
        _DOMAINES_RX = [(d["cle"], _P.motif(d.get("mots_titre"))) for d in _P.domaines()]
    t = (title or "").lower()
    for cle, rx in _DOMAINES_RX[:-1]:
        if rx is not None and rx.search(t):
            return cle
    return _DOMAINES_RX[-1][0]
    # NEUTRAL DEFAULT. It used to be "ESG_Finance_Durable", so that 2151 offers
    # out of 2818 carried this domain WITHOUT any ESG keyword in their title:
    # « Analyste DSI », « Financial Controller », « Business Analyst ». Elles
    # received the ESG CV and, since the per-domain bases, a letter that
    # opens on sustainable finance — in front of an oil company, it
    # misses the point. The domain must describe the OFFER, not the user's target.
    return "Finance"


def matches_esg_finance(title: str) -> bool:
    """Does the title touch the ESG/Finance lexicon? WIDE ON PURPOSE.

    ⚠ It is NOT an entry filter. The list contains "h/f", "social", "data",
    "contrat": "Plombier chauffagiste H/F" passes it. It is a first sieve, which
    `title_ok` (job_sources) tightens by requiring a PROFESSION word and rejecting
    off-target roles. To decide whether an offer gets in, call `offre_retenue`, never
    this function alone.
    """
    t = (title or "").lower()
    return not _ici.ESG_FINANCE_KEYWORDS or any(kw in t for kw in _ici.ESG_FINANCE_KEYWORDS)
