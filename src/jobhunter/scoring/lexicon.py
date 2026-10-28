"""Lexicon of the profile's skills and domains: what scoring AND documents share.

Extracted from Scripts/tailor_application.py (phase 3.3). ats_match imported it from
tailor_application, which imported ats_match in return: a cycle. This module only
depends on the profile.
"""

import re
import sys
from typing import Any

from jobhunter import lazy as _paresseux
from jobhunter import profile as _P

_ici = sys.modules[__name__]
# Values taken from the profile: computed on first read, not at import
# (jobhunter.lazy). In this module, they are read through `_ici.NAME`.
_PARESSEUX: _paresseux.Fabriques = {}


def __getattr__(nom: str) -> Any:
    return _paresseux.lire(_ici, _PARESSEUX, nom)


# A profile domain = a CV variant + a background paragraph.
# The LAST domain is the fallback.
_PARESSEUX["_DOMAINES"] = lambda: _P.domaines()
_PARESSEUX["CV_VARIANT"] = lambda: ({d["cle"]: d.get("cv") or "" for d in _ici._DOMAINES})
_PARESSEUX["CV_VARIANT_EN"] = lambda: ({d["cle"]: d.get("cv_en") or "" for d in _ici._DOMAINES})


def cv_variant_key(domaine: str | None) -> str:
    """Profile domain key for an offer's `domaine` field.

    Accepts the key itself, its label ("Finance"), or a free text read with the
    domains' title words; otherwise the fallback domain.
    """
    d = (domaine or "").strip()
    bas = d.lower()
    for x in _ici._DOMAINES:
        if bas in (x["cle"].lower(), str(x.get("libelle", "")).lower()):
            return str(x["cle"])
    for x in _ici._DOMAINES[:-1]:
        if _P.cherche(_P.motif(x.get("mots_titre")), d):
            return str(x["cle"])
    return str(_ici._DOMAINES[-1]["cle"])


# ---- Skills lexicon (label -> synonyms to look for in the offer) ----
_PARESSEUX["_COMP"] = lambda: _P.get("competences", {}) or {}
_PARESSEUX["SKILL_LEX"] = lambda: (
    {lab: list(v.get("synonymes") or []) for lab, v in _ici._COMP.items()}
)


# ---- moteur match keyword ----
# SHORT acronyms must match the WHOLE word. As substrings they went
# haywire: 'ges' (greenhouse gases) matched "GEStion", 'gri' "aGRIcole",
# 'pai' "PAIement", 'var' "VARiable". Here the stake goes beyond the scoring: these
# labels are PRINTED on the CV sent to the recruiter.
_SHORT = 4
# Each short name keeps its text: the regex runs only when the name is in the text at
# all (a whole-word match implies a substring). Rescoring a queue of 11 754 offers spent
# 44 s in 1.3 million regex searches, almost all for absent names (2026-10-28).
_PARESSEUX["_RX_SKILL"] = lambda: (
    {
        lab: [
            (n.strip(), re.compile(r"\b" + re.escape(n.strip()) + r"\b"))
            for n in ns
            if len(n.strip()) <= _SHORT
        ]
        for lab, ns in _ici.SKILL_LEX.items()
    }
)
_PARESSEUX["_SUB_SKILL"] = lambda: (
    {lab: [n for n in ns if len(n.strip()) > _SHORT] for lab, ns in _ici.SKILL_LEX.items()}
)
# Every (label, name, regex or None) in one flat list: skills_present walks it once
# instead of one generator per label (17 s of the same rescoring).
_PARESSEUX["_PAIRES_SKILL"] = lambda: [
    *((lab, n, None) for lab, ns in _ici._SUB_SKILL.items() for n in ns),
    *((lab, n, r) for lab, rs in _ici._RX_SKILL.items() for n, r in rs),
]


def contient(noms: list[str], t: str) -> bool:
    """Is one of these synonyms in the text (lowercase)? Same rule as has_skill."""
    for n in noms:
        n = n.strip().lower()
        if n and (re.search(r"\b" + re.escape(n) + r"\b", t) if len(n) <= _SHORT else n in t):
            return True
    return False


# The last texts read: scoring one offer asks for the same text three times (its
# components, its tie-break, its reasons). Emptied when the lexicon is rebuilt.
_VUS: dict[str, frozenset[str]] = {}
_VUS_DE: list[object] = [None]


def skills_present(t: str) -> set[str]:
    """The labels present in the text (already lowercase): has_skill for every label."""
    paires = _ici._PAIRES_SKILL
    if _VUS_DE[0] is not paires:
        _VUS.clear()
        _VUS_DE[0] = paires
    vu = _VUS.get(t)
    if vu is None:
        vu = frozenset(lab for lab, n, r in paires if n in t and (r is None or r.search(t)))
        if len(_VUS) >= 8:
            _VUS.clear()
        _VUS[t] = vu
    return set(vu)


def has_skill(label: str, t: str) -> bool:
    """Is the label present in the text (already lowercase)?"""
    return any(n in t for n in _ici._SUB_SKILL[label]) or any(
        n in t and r.search(t) for n, r in _ici._RX_SKILL[label]
    )
