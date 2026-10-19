"""Le dossier d'une offre est-il prêt à partir ? Contrôle des fichiers FINAUX.

Le CV et la lettre ont été générés ; ce module regarde ce qui partira vraiment : les PDF
référencés par l'offre. Un dossier n'est « prêt » que si aucun problème n'est trouvé :

- chaque pièce existe, s'ouvre et contient du texte (un PDF sans texte est souvent une
  image, que les ATS lisent mal) ;
- le CV tient sur UNE page, la lettre aussi ;
- les coordonnées du profil y figurent : nom, courriel, téléphone ;
- aucun gabarit n'est resté non rempli (« [nom du poste] », « {entreprise} », « XXX »…).

Ce qu'il ne vérifie PAS : la justesse des phrases. Les faits du CV automatique viennent
de la banque validée (CV/Faits.json) ; un texte sur mesure reste sous la responsabilité de
son auteur.
"""

import re
import unicodedata
from pathlib import Path
from typing import Any

from jobhunter import liens
from jobhunter import profil as _profil

PIECES = (("cv", "CV"), ("lettre", "lettre"))

# Gabarits non remplis : crochets en capitales ou « nom du poste », accolades de format,
# marqueurs de brouillon. Sensible à la casse, sauf « nom du poste » et « lorem ipsum » :
# avec re.I sur tout le motif, « crochets en capitales » prenait n'importe quel texte
# entre crochets — dont l'intitulé « Green Finance Analyst [Open to internal and external
# applicants] » de l'ONU, signalé à tort comme gabarit oublié (vu le 19/10/2026).
_RX_GABARIT = re.compile(
    r"\[(?i:nom du poste)\]|\[[A-ZÉÈ][A-ZÉÈ _'-]{2,}\]|\{[a-z_]{3,}\}|<(?:DATE|NOM|POSTE)>"
    r"|\bXXX+\b|(?i:lorem ipsum)"
)


def _plat(texte: str) -> str:
    """Minuscules, sans accents ni espaces multiples : pour chercher un nom ou un courriel."""
    t = unicodedata.normalize("NFKD", texte).encode("ascii", "ignore").decode().lower()
    return " ".join(t.split())


def piece_finale(chemin: Path | None) -> Path | None:
    """La pièce qui partira vraiment : le PDF dérivé d'un .docx, s'il existe et est à jour.

    22 offres pointaient sur la lettre .docx alors que son PDF existait à côté : le
    programme de candidature aurait joint le .docx. Le PDF n'est préféré que s'il n'est
    pas plus ancien que le .docx (sinon il ne reflète pas la dernière retouche).

    Args:
        chemin: le fichier référencé par l'offre, ou None.

    Returns:
        Le PDF à jour s'il existe, sinon `chemin` tel quel.
    """
    if chemin is None or chemin.suffix.lower() != ".docx":
        return chemin
    pdf = chemin.with_suffix(".pdf")
    try:
        if pdf.exists() and pdf.stat().st_mtime >= chemin.stat().st_mtime:
            return pdf
    except OSError:
        pass
    return chemin


def lire_pdf(chemin: Path) -> tuple[str, int] | None:
    """(texte, nombre de pages) d'un PDF, ou None s'il ne s'ouvre pas."""
    try:
        import fitz

        with fitz.open(str(chemin)) as doc:
            texte = "\n".join(page.get_text() for page in doc)
            return texte, int(doc.page_count)
    except Exception:
        return None


def controler_piece(chemin: Path | None, nom: str, identite: dict[str, str]) -> list[str]:
    """Problèmes d'une pièce du dossier (vide = rien à redire).

    Args:
        chemin: le fichier référencé par l'offre, ou None.
        nom: « CV » ou « lettre », pour les messages.
        identite: les coordonnées du profil (`profil.identite()`).

    Returns:
        Les problèmes, en phrases courtes.
    """
    if chemin is None:
        return [f"{nom} absent"]
    if not chemin.exists():
        return [f"{nom} introuvable : {chemin.name}"]
    if chemin.suffix.lower() != ".pdf":
        if chemin.with_suffix(".pdf").exists():
            return [
                f"{nom} : le PDF est plus ancien que le .docx ({chemin.name}) — relancer sync_docs"
            ]
        return [f"{nom} n'est pas un PDF : {chemin.name}"]
    lu = lire_pdf(chemin)
    if lu is None:
        return [f"{nom} illisible (PDF abîmé)"]
    texte, pages = lu
    problemes = []
    if len(texte.strip()) < 200:
        return [f"{nom} sans texte lisible (image ?)"]
    if pages > 1:
        problemes.append(f"{nom} de {pages} pages")
    plat = _plat(texte)
    chiffres = re.sub(r"\D", "", texte)
    nom_candidat = _plat(identite.get("nom", ""))
    if nom_candidat and nom_candidat != "candidat" and nom_candidat not in plat:
        problemes.append(f"{nom} : nom du candidat absent")
    email = (identite.get("email") or "").strip().lower()
    if email and email not in plat.replace(" ", ""):
        problemes.append(f"{nom} : courriel absent")
    tel = re.sub(r"\D", "", identite.get("tel") or "")[-9:]
    if len(tel) == 9 and tel not in chiffres:
        problemes.append(f"{nom} : téléphone absent")
    gabarit = _RX_GABARIT.search(texte)
    if gabarit:
        problemes.append(f"{nom} : gabarit non rempli « {gabarit.group(0)} »")
    return problemes


def controler_dossier(offre: Any, identite: dict[str, str] | None = None) -> list[str]:
    """Problèmes du dossier d'une offre : CV et lettre. Vide = dossier prêt.

    Args:
        offre: l'offre (champs `cv` et `lettre` : liens file:/// ou chemins).
        identite: les coordonnées ; None = celles du profil.

    Returns:
        Les problèmes des deux pièces, en phrases courtes.
    """
    ident = identite if identite is not None else _profil.identite()
    problemes: list[str] = []
    for cle, nom in PIECES:
        problemes += controler_piece(piece_finale(liens.chemin_de(offre.get(cle))), nom, ident)
    return problemes
