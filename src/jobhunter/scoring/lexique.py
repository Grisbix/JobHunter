"""Lexique des competences et domaines du profil : ce que scoring ET documents partagent.

Extrait de Scripts/tailor_application.py (phase 3.3). ats_match l'importait de
tailor_application, qui importait ats_match en retour : un cycle. Ce module ne depend
que du profil.
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


# Un domaine du profil = une variante de CV + un paragraphe de parcours.
# Le DERNIER domaine est le repli.
_PARESSEUX["_DOMAINES"] = lambda: _P.domaines()
_PARESSEUX["CV_VARIANT"] = lambda: ({d["cle"]: d.get("cv") or "" for d in _ici._DOMAINES})
_PARESSEUX["CV_VARIANT_EN"] = lambda: ({d["cle"]: d.get("cv_en") or "" for d in _ici._DOMAINES})


def cv_variant_key(domaine: str | None) -> str:
    """Cle de domaine du profil pour un champ `domaine` d'offre.

    Accepte la cle elle-meme, son libelle (« Finance »), ou un texte libre lu
    avec les mots d'intitule des domaines ; sinon le domaine de repli.
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


# ---- Lexique de competences (libelle -> synonymes a chercher dans l'offre) ----
_PARESSEUX["_COMP"] = lambda: _P.get("competences", {}) or {}
_PARESSEUX["SKILL_LEX"] = lambda: (
    {lab: list(v.get("synonymes") or []) for lab, v in _ici._COMP.items()}
)


# ---- moteur match keyword ----
# Les sigles COURTS doivent matcher le mot ENTIER. En sous-chaîne ils partaient en
# vrille : 'ges' (gaz à effet de serre) matchait « GEStion », 'gri' « aGRIcole »,
# 'pai' « PAIement », 'var' « VARiable ». Ici l'enjeu dépasse le scoring : ces
# libellés sont IMPRIMÉS sur le CV envoyé au recruteur.
_SHORT = 4
_PARESSEUX["_RX_SKILL"] = lambda: (
    {
        lab: [
            re.compile(r"\b" + re.escape(n.strip()) + r"\b") for n in ns if len(n.strip()) <= _SHORT
        ]
        for lab, ns in _ici.SKILL_LEX.items()
    }
)
_PARESSEUX["_SUB_SKILL"] = lambda: (
    {lab: [n for n in ns if len(n.strip()) > _SHORT] for lab, ns in _ici.SKILL_LEX.items()}
)


def has_skill(label: str, t: str) -> bool:
    """Le libellé est-il présent dans le texte (déjà en minuscules) ?"""
    return any(n in t for n in _ici._SUB_SKILL[label]) or any(
        r.search(t) for r in _ici._RX_SKILL[label]
    )
