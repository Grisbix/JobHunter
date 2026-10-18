"""Lexique des competences et domaines du profil : ce que scoring ET documents partagent.

Extrait de Scripts/tailor_application.py (phase 3.3). ats_match l'importait de
tailor_application, qui importait ats_match en retour : un cycle. Ce module ne depend
que du profil.
"""

import re

from jobhunter import profil as _P

# Un domaine du profil = une variante de CV + un paragraphe de parcours.
# Le DERNIER domaine est le repli.
_DOMAINES = _P.domaines()
CV_VARIANT = {d["cle"]: d.get("cv") or "" for d in _DOMAINES}
CV_VARIANT_EN = {d["cle"]: d.get("cv_en") or "" for d in _DOMAINES}


def cv_variant_key(domaine):
    """Cle de domaine du profil pour un champ `domaine` d'offre.

    Accepte la cle elle-meme, son libelle (« Finance »), ou un texte libre lu
    avec les mots d'intitule des domaines ; sinon le domaine de repli."""
    d = (domaine or "").strip()
    bas = d.lower()
    for x in _DOMAINES:
        if bas in (x["cle"].lower(), str(x.get("libelle", "")).lower()):
            return x["cle"]
    for x in _DOMAINES[:-1]:
        if _P.cherche(_P.motif(x.get("mots_titre")), d):
            return x["cle"]
    return _DOMAINES[-1]["cle"]


# ---- Lexique de competences (libelle -> synonymes a chercher dans l'offre) ----
_COMP = _P.get("competences", {}) or {}
SKILL_LEX = {lab: list(v.get("synonymes") or []) for lab, v in _COMP.items()}


# ---- moteur match keyword ----
# Les sigles COURTS doivent matcher le mot ENTIER. En sous-chaîne ils partaient en
# vrille : 'ges' (gaz à effet de serre) matchait « GEStion », 'gri' « aGRIcole »,
# 'pai' « PAIement », 'var' « VARiable ». Ici l'enjeu dépasse le scoring : ces
# libellés sont IMPRIMÉS sur le CV envoyé au recruteur.
_SHORT = 4
_RX_SKILL = {
    lab: [re.compile(r"\b" + re.escape(n.strip()) + r"\b") for n in ns if len(n.strip()) <= _SHORT]
    for lab, ns in SKILL_LEX.items()
}
_SUB_SKILL = {lab: [n for n in ns if len(n.strip()) > _SHORT] for lab, ns in SKILL_LEX.items()}


def has_skill(label, t):
    """Le libellé est-il présent dans le texte (déjà en minuscules) ?"""
    return any(n in t for n in _SUB_SKILL[label]) or any(r.search(t) for r in _RX_SKILL[label])
