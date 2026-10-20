#!/usr/bin/env python3
r"""Everything SPECIFIC TO THE PERSON, read from profil/profil.json.

Formerly Scripts/profil.py.

The engine (collection, sorting, scoring, CV, letters) knows no profession, no city,
no name: it reads this module. To change target, one changes the profile, never the
code.

The file is created with `python JobHunter.pyw profile <your_cv.pdf>`, then edited by
hand. A complete example (sustainable finance) is in profil/exemple_finance_esg.json.

WORD lists accept two forms:
  "analyste financier"     a word or a phrase, searched at the start of a word
                           ("analyste" also finds "analystes")
  "re:taxonomi\\w*"        a regular expression, for the fine cases
"""

import json
import os
import re
import sys
from collections.abc import Iterable
from functools import lru_cache
from pathlib import Path
from typing import Any

from jobhunter import lazy as _paresseux
from jobhunter import root as _racine

RACINE = _racine.racine()
# PROFIL_JOBHUNTER allows trying another profile without touching the file.
FICHIER = Path(os.environ.get("PROFIL_JOBHUNTER") or RACINE / "profil" / "profil.json")


class ProfilAbsent(RuntimeError):
    """No profile: neither a `profil/profil.json` file nor an injected profile."""


# Profile provided in memory by `utiliser` (tests, trials); None = the file.
_INJECTE: dict[str, Any] | None = None


@lru_cache(maxsize=1)
def charger() -> dict[str, Any]:
    """The whole profile, read once then kept in memory.

    Returns:
        The profile injected by `utiliser`, otherwise the content of `FICHIER`.

    Raises:
        ProfilAbsent: no injected profile and the file does not exist.
    """
    if _INJECTE is not None:
        return _INJECTE
    if not FICHIER.exists():
        raise ProfilAbsent(
            f"Profil introuvable : {FICHIER}\n"
            "Lance d'abord : python JobHunter.pyw profile <ton_cv.pdf|docx>"
        )
    with open(FICHIER, encoding="utf-8") as f:
        p: dict[str, Any] = json.load(f)
    return p


def utiliser(donnees: dict[str, Any]) -> None:
    """Replaces the profile with `donnees`, without a file.

    A test thus builds the profile it needs. Everything the engine had derived from it
    is recomputed at the next read; `recharger()` goes back to the file.

    Args:
        donnees: the complete profile, in the profil.json format.
    """
    global _INJECTE
    _INJECTE = donnees
    charger.cache_clear()
    _paresseux.oublier()


def recharger(fichier: Path | None = None) -> None:
    """Goes back to the file and forgets the values derived from the old profile.

    Args:
        fichier: another profile file to read from now on; None keeps `FICHIER`.
    """
    global _INJECTE, FICHIER
    _INJECTE = None
    if fichier is not None:
        FICHIER = Path(fichier)
    charger.cache_clear()
    _paresseux.oublier()


def get(chemin: str, defaut: Any = None) -> Any:
    """A profile value by its dotted path.

    Args:
        chemin: keys separated by dots, for example "scoring.axes".
        defaut: what is returned if a step of the path is missing.

    Returns:
        The value found, or `defaut`.
    """
    v: Any = charger()
    for k in chemin.split("."):
        if not isinstance(v, dict) or k not in v:
            return defaut
        v = v[k]
    return v


# ── Identite ────────────────────────────────────────────────────────────────
def identite() -> dict[str, str]:
    """The candidate's contact details, without a missing field.

    Returns:
        nom, email, tel, linkedin, ville, and genre ("m" or "f", for agreements).
    """
    i = get("identite", {}) or {}
    nom = (i.get("nom_complet") or f"{i.get('prenom', '')} {i.get('nom', '')}").strip()
    return {
        "nom": nom or "Candidat",
        "email": i.get("email", ""),
        "tel": i.get("telephone", ""),
        "linkedin": i.get("linkedin", ""),
        "ville": i.get("ville", ""),
        "genre": (i.get("genre") or "m").lower()[:1],  # the letter's agreements
    }


def prefixe_fichier() -> str:
    """The "Prenom_Nom" prefix that names the generated documents."""
    nom = identite()["nom"]
    import unicodedata

    s = unicodedata.normalize("NFKD", nom).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_") or "Candidat"


def accord(masculin: str, feminin: str) -> str:
    """Chooses the form according to the profile's gender ("Diplômé" / "Diplômée")."""
    return feminin if identite()["genre"] == "f" else masculin


# ── Motifs ──────────────────────────────────────────────────────────────────
def _fragment(mot: object, entier: bool) -> str:
    mot = str(mot)
    if mot.startswith("re:"):
        return "(?:" + mot[3:] + ")"  # regex : prise TELLE QUELLE
    # Word: LEFT boundary ("rse" must not find "diveRSE"), no boundary
    # droite sauf `entier` — « analyste » doit trouver « analystes ».
    corps = re.escape(mot.strip()).replace(r"\ ", r"\s+")
    return r"\b" + corps + (r"\b" if entier else "")


def motif(mots: Iterable[object] | None, entier: bool = False) -> re.Pattern[str] | None:
    """A compiled regex that finds one of the `mots`.

    Args:
        mots: words, phrases or regexes prefixed with "re:" (taken as they are).
        entier: also bounds the words on the right — short acronyms: "rse" must not
            find "RSEau".

    Returns:
        The regex, case-insensitive, or None if the list is empty.
    """
    mots = [m for m in (mots or []) if str(m).strip()]
    if not mots:
        return None
    return re.compile("|".join(_fragment(m, entier) for m in mots), re.I)


def cherche(rx: re.Pattern[str] | None, texte: str | None) -> bool:
    """True if `rx` exists and finds something in `texte` (None = empty text)."""
    return bool(rx and rx.search(texte or ""))


# ── Domains: CV variants and background paragraphs ──────────────────────────
def domaines() -> list[dict[str, Any]]:
    """The profile's domains, in order.

    The first one with a word appearing in the title wins; the LAST one serves as
    the fallback.

    Returns:
        The domains, or a single "General" domain if the profile has none.
    """
    d: list[dict[str, Any]] = get("domaines", []) or []
    if not d:
        d = [{"cle": "General", "libelle": "Général", "mots_titre": [], "cv": ""}]
    return d


def domaine_par_cle(cle: str) -> dict[str, Any]:
    """The domain with key `cle`, or the fallback domain (the last one)."""
    for d in domaines():
        if d.get("cle") == cle:
            return d
    return domaines()[-1]


# ── Application forms (apply_runner, web_nav) ────────────────────────────────
# Field names met on career sites, per profile key. Generic.
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
    """The form-filling profile: identity + "formulaire" section.

    NEVER a password: project rule, no program handles one — the password fields
    stay the user's.
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
