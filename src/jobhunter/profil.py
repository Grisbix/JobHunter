#!/usr/bin/env python3
r"""Tout ce qui est PROPRE A LA PERSONNE, lu dans profil/profil.json.

Ancien Scripts/profil.py.

Le moteur (collecte, tri, scoring, CV, lettres) ne connait aucun metier, aucune
ville, aucun nom : il lit ce module. Pour changer de cible, on change le profil,
jamais le code.

Le fichier se cree avec `python JobHunter.pyw profil <ton_cv.pdf>`, puis
se retouche a la main. Un exemple complet (finance durable) est dans
profil/exemple_finance_esg.json.

Les listes de MOTS acceptent deux formes :
  "analyste financier"     un mot ou une expression, cherche en debut de mot
                           (« analyste » trouve aussi « analystes »)
  "re:taxonomi\\w*"        une expression reguliere, pour les cas fins
"""

import json
import os
import re
import sys
from collections.abc import Iterable
from functools import lru_cache
from pathlib import Path
from typing import Any

from jobhunter import paresseux as _paresseux
from jobhunter import racine as _racine

RACINE = _racine.racine()
# PROFIL_JOBHUNTER permet d'essayer un autre profil sans toucher au fichier.
FICHIER = Path(os.environ.get("PROFIL_JOBHUNTER") or RACINE / "profil" / "profil.json")


class ProfilAbsent(RuntimeError):
    """Aucun profil : ni fichier `profil/profil.json`, ni profil injecte."""


# Profil fourni en memoire par `utiliser` (tests, essais) ; None = le fichier.
_INJECTE: dict[str, Any] | None = None


@lru_cache(maxsize=1)
def charger() -> dict[str, Any]:
    """Le profil entier, lu une fois puis garde en memoire.

    Returns:
        Le profil injecte par `utiliser`, sinon le contenu de `FICHIER`.

    Raises:
        ProfilAbsent: aucun profil injecte et le fichier n'existe pas.
    """
    if _INJECTE is not None:
        return _INJECTE
    if not FICHIER.exists():
        raise ProfilAbsent(
            f"Profil introuvable : {FICHIER}\n"
            "Lance d'abord : python JobHunter.pyw profil <ton_cv.pdf|docx>"
        )
    with open(FICHIER, encoding="utf-8") as f:
        p: dict[str, Any] = json.load(f)
    return p


def utiliser(donnees: dict[str, Any]) -> None:
    """Remplace le profil par `donnees`, sans fichier.

    Un test construit ainsi le profil dont il a besoin. Tout ce que le moteur en
    avait tire est recalcule a la lecture suivante ; `recharger()` revient au fichier.

    Args:
        donnees: le profil complet, au format de profil.json.
    """
    global _INJECTE
    _INJECTE = donnees
    charger.cache_clear()
    _paresseux.oublier()


def recharger(fichier: Path | None = None) -> None:
    """Revient au fichier et oublie les valeurs tirees de l'ancien profil.

    Args:
        fichier: un autre fichier de profil a lire desormais ; None garde `FICHIER`.
    """
    global _INJECTE, FICHIER
    _INJECTE = None
    if fichier is not None:
        FICHIER = Path(fichier)
    charger.cache_clear()
    _paresseux.oublier()


def get(chemin: str, defaut: Any = None) -> Any:
    """Une valeur du profil par son chemin pointe.

    Args:
        chemin: cles separees par des points, par exemple « scoring.axes ».
        defaut: ce qui est rendu si une etape du chemin manque.

    Returns:
        La valeur trouvee, ou `defaut`.
    """
    v: Any = charger()
    for k in chemin.split("."):
        if not isinstance(v, dict) or k not in v:
            return defaut
        v = v[k]
    return v


# ── Identite ────────────────────────────────────────────────────────────────
def identite() -> dict[str, str]:
    """Coordonnees du candidat, sans champ manquant.

    Returns:
        nom, email, tel, linkedin, ville, et genre (« m » ou « f », pour les accords).
    """
    i = get("identite", {}) or {}
    nom = (i.get("nom_complet") or f"{i.get('prenom', '')} {i.get('nom', '')}").strip()
    return {
        "nom": nom or "Candidat",
        "email": i.get("email", ""),
        "tel": i.get("telephone", ""),
        "linkedin": i.get("linkedin", ""),
        "ville": i.get("ville", ""),
        "genre": (i.get("genre") or "m").lower()[:1],  # accords de la lettre
    }


def prefixe_fichier() -> str:
    """« Prenom_Nom » pour nommer les documents generes."""
    nom = identite()["nom"]
    import unicodedata

    s = unicodedata.normalize("NFKD", nom).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_") or "Candidat"


def accord(masculin: str, feminin: str) -> str:
    """Choisit la forme selon le genre du profil (« Diplômé » / « Diplômée »)."""
    return feminin if identite()["genre"] == "f" else masculin


# ── Motifs ──────────────────────────────────────────────────────────────────
def _fragment(mot: object, entier: bool) -> str:
    mot = str(mot)
    if mot.startswith("re:"):
        return "(?:" + mot[3:] + ")"  # regex : prise TELLE QUELLE
    # Mot : borne GAUCHE (« rse » ne doit pas trouver « diveRSE »), pas de borne
    # droite sauf `entier` — « analyste » doit trouver « analystes ».
    corps = re.escape(mot.strip()).replace(r"\ ", r"\s+")
    return r"\b" + corps + (r"\b" if entier else "")


def motif(mots: Iterable[object] | None, entier: bool = False) -> re.Pattern[str] | None:
    """Une regex compilee qui trouve l'un des `mots`.

    Args:
        mots: mots, expressions ou regex prefixees par « re: » (prises telles quelles).
        entier: borne aussi a droite les mots — sigles courts : « rse » ne doit pas
            trouver « RSEau ».

    Returns:
        La regex, insensible a la casse, ou None si la liste est vide.
    """
    mots = [m for m in (mots or []) if str(m).strip()]
    if not mots:
        return None
    return re.compile("|".join(_fragment(m, entier) for m in mots), re.I)


def cherche(rx: re.Pattern[str] | None, texte: str | None) -> bool:
    """Vrai si `rx` existe et trouve quelque chose dans `texte` (None = texte vide)."""
    return bool(rx and rx.search(texte or ""))


# ── Domaines : variantes de CV et paragraphes de parcours ──────────────────
def domaines() -> list[dict[str, Any]]:
    """Les domaines du profil, dans l'ordre.

    Le premier dont un mot apparait dans l'intitule gagne ; le DERNIER sert de repli.

    Returns:
        Les domaines, ou un domaine « General » unique si le profil n'en a pas.
    """
    d: list[dict[str, Any]] = get("domaines", []) or []
    if not d:
        d = [{"cle": "General", "libelle": "Général", "mots_titre": [], "cv": ""}]
    return d


def domaine_par_cle(cle: str) -> dict[str, Any]:
    """Le domaine de cle `cle`, ou le domaine de repli (le dernier)."""
    for d in domaines():
        if d.get("cle") == cle:
            return d
    return domaines()[-1]


# ── Formulaires de candidature (apply_runner, web_nav) ──────────────────────
# Noms de champs rencontres sur les sites carriere, par cle du profil. Generiques.
ALIAS_CHAMPS = {
    "prenom": [
        "prenom",
        "first_name",
        "firstname",
        "givenname",
        "given_name",
        "first-name",
        "prenom_candidat",
        "txtprenom",
    ],
    "nom": [
        "nom",
        "last_name",
        "lastname",
        "surname",
        "familyname",
        "family_name",
        "last-name",
        "nom de famille",
        "nom_candidat",
        "txtnom",
    ],
    "email": [
        "email",
        "e-mail",
        "courriel",
        "mail",
        "e_mail",
        "identifiant",
        "username",
        "login",
        "email_address",
        "user_email",
        "txtemail",
        "candidate_email",
    ],
    "tel": [
        "tel",
        "telephone",
        "phone",
        "portable",
        "mobile",
        "numero",
        "phone_number",
        "txttel",
        "telephone_portable",
        "mobile_phone",
        "cell_phone",
    ],
    "linkedin": ["linkedin", "linkedin_url", "linkedin_profile", "url_linkedin"],
    "ville": ["ville", "city", "localite", "commune", "town", "municipality"],
    "cp": ["cp", "codepostal", "code_postal", "zip", "zipcode", "postal_code", "zip_code"],
    "pays": ["pays", "country", "nationalite"],
    "adresse": ["adresse", "address", "postal_address", "rue"],
    "disponibilite": [
        "disponibilite",
        "availability",
        "start_date",
        "date_debut",
        "available_from",
        "starting_date",
        "notice_period",
        "preavis",
    ],
    "salaire_souhaite": [
        "salaire",
        "salary",
        "pretentions",
        "remuneration",
        "expected_salary",
        "salary_expectation",
        "wage",
        "desired_salary",
        "annual_salary",
    ],
    "message": [
        "message",
        "motivation",
        "cover_letter",
        "lettre",
        "cover",
        "about_you",
        "commentaire",
        "additional_info",
        "notes",
        "pourquoi",
        "presentation",
    ],
}
_CHAMPS_FORMULAIRE = (
    "tel_local",
    "cp",
    "pays",
    "adresse",
    "disponibilite",
    "salaire_souhaite",
    "mobilite",
    "permis",
    "nationalite",
    "date_naissance",
    "site_web",
    "github",
    "niveau_etudes",
    "dernier_poste",
    "langues",
    "competences",
    "message",
)


def formulaire() -> dict[str, Any]:
    """Le profil de remplissage des formulaires : identite + section « formulaire ».

    JAMAIS de mot de passe : regle du projet, aucun programme n'en manipule — les
    champs mot de passe restent a l'utilisateur.
    """
    i = get("identite", {}) or {}
    f = get("formulaire", {}) or {}
    ident = identite()
    out: dict[str, Any] = {
        "full": ident["nom"],
        "prenom": i.get("prenom", ""),
        "nom": i.get("nom", ""),
        "email": ident["email"],
        "tel": ident["tel"],
        "linkedin": ident["linkedin"],
        "ville": ident["ville"],
    }
    for k in _CHAMPS_FORMULAIRE:
        out[k] = f.get(k, "")
    out["field_aliases"] = {**ALIAS_CHAMPS, **(f.get("field_aliases") or {})}
    out.pop("password", None)
    return out


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]  # console : TextIOWrapper
    try:
        p = charger()
    except ProfilAbsent as e:
        print(e)
        sys.exit(1)
    print(f"Profil : {FICHIER}")
    print(
        f"  {identite()['nom']} · {len(domaines())} domaine(s) · "
        f"{len(get('competences', {}) or {})} competence(s) · "
        f"{len(get('collecte.mots_cles', []) or [])} mot(s)-cle(s) de collecte"
    )
