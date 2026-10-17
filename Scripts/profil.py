#!/usr/bin/env python3
"""profil.py — tout ce qui est PROPRE A LA PERSONNE, lu dans profil/profil.json.

Le moteur (collecte, tri, scoring, CV, lettres) ne connait aucun metier, aucune
ville, aucun nom : il lit ce module. Pour changer de cible, on change le profil,
jamais le code.

Le fichier se cree avec `python Scripts/premier_lancement.py <ton_cv.pdf>`, puis
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
from functools import lru_cache
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
# PROFIL_JOBHUNTER permet d'essayer un autre profil sans toucher au fichier.
FICHIER = Path(os.environ.get("PROFIL_JOBHUNTER") or RACINE / "profil" / "profil.json")


class ProfilAbsent(RuntimeError):
    pass


@lru_cache(maxsize=1)
def charger():
    if not FICHIER.exists():
        raise ProfilAbsent(
            f"Profil introuvable : {FICHIER}\n"
            "Lance d'abord : python Scripts/premier_lancement.py <ton_cv.pdf|docx>"
        )
    with open(FICHIER, encoding="utf-8") as f:
        p = json.load(f)
    return p


def get(chemin, defaut=None):
    """get("scoring.axes") -> valeur, ou `defaut` si une etape manque."""
    v = charger()
    for k in chemin.split("."):
        if not isinstance(v, dict) or k not in v:
            return defaut
        v = v[k]
    return v


# ── Identite ────────────────────────────────────────────────────────────────
def identite():
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


def prefixe_fichier():
    """« Prenom_Nom » pour nommer les documents generes."""
    nom = identite()["nom"]
    import unicodedata

    s = unicodedata.normalize("NFKD", nom).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_") or "Candidat"


def accord(masculin, feminin):
    """Choisit la forme selon le genre du profil (« Diplômé » / « Diplômée »)."""
    return feminin if identite()["genre"] == "f" else masculin


# ── Motifs ──────────────────────────────────────────────────────────────────
def _fragment(mot, entier):
    mot = str(mot)
    if mot.startswith("re:"):
        return "(?:" + mot[3:] + ")"  # regex : prise TELLE QUELLE
    # Mot : borne GAUCHE (« rse » ne doit pas trouver « diveRSE »), pas de borne
    # droite sauf `entier` — « analyste » doit trouver « analystes ».
    corps = re.escape(mot.strip()).replace(r"\ ", r"\s+")
    return r"\b" + corps + (r"\b" if entier else "")


def motif(mots, entier=False):
    """Une regex compilee qui trouve l'un des `mots`, ou None si la liste est vide.

    `entier=True` borne aussi a droite les MOTS (sigles courts : « rse » ne doit
    pas trouver « RSEau »). Les entrees « re:… » ne sont jamais modifiees."""
    mots = [m for m in (mots or []) if str(m).strip()]
    if not mots:
        return None
    return re.compile("|".join(_fragment(m, entier) for m in mots), re.I)


def cherche(rx, texte):
    return bool(rx and rx.search(texte or ""))


# ── Domaines : variantes de CV et paragraphes de parcours ──────────────────
def domaines():
    """Liste ordonnee de domaines. Le premier dont un mot apparait dans
    l'intitule gagne ; le DERNIER sert de repli."""
    d = get("domaines", []) or []
    if not d:
        d = [{"cle": "General", "libelle": "Général", "mots_titre": [], "cv": ""}]
    return d


def domaine_par_cle(cle):
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


def formulaire():
    """Le profil de remplissage des formulaires : identite + section
    « formulaire » du profil. JAMAIS de mot de passe : regle du projet, aucun
    programme n'en manipule — les champs mot de passe restent a l'utilisateur."""
    i = get("identite", {}) or {}
    f = get("formulaire", {}) or {}
    ident = identite()
    out = {
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
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
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
