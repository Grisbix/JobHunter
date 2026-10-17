#!/usr/bin/env python3
"""chemins.py — Le seul endroit qui decide ou vivent les documents generes.

ETAT DEPUIS LE 20/09/2026 : tout le projet vit dans C:/Recherche_emploi, hors
de OneDrive, et les documents sont dans l'arbre du projet. `chemins.json`
n'existe pas, et la resolution retombe donc sur la racine. Ce module ne
DEPLACE plus rien ; il garde l'indirection.

POURQUOI LA GARDER. Onze programmes construisaient `ROOT / "CV" / "Par_offre"`
chacun de leur cote, plus trois dans l'app. Sortir ce dossier de OneDrive a
demande onze modifications coherentes. La prochaine fois — un disque qui se
remplit, un dossier partage, un second PC — ce sera une ligne.

    1. Scripts/chemins.json, s'il existe   -> ce qu'il dit
    2. sinon la racine du projet
    3. le dossier est cree au besoin

Le fichier de reglage n'est PAS suivi par git : ce qu'il decrit est vrai d'une
machine, pas d'un projet. Sur un second PC sans ce fichier, tout fonctionne
depuis la racine.

CE QUI EST DEPLACABLE ET CE QUI NE L'EST PAS. Par_offre est une SORTIE :
16 093 fichiers que `regenere_docs.py` reconstruit depuis la file et les
modeles. Modeles, Relances et Messages sont des ENTREES ecrites a la main,
1,5 Mo au total, que rien ne regenere — elles restent ancrees a la racine.

    from chemins import CV_PAR_OFFRE, LT_PAR_OFFRE
"""

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

# Reglage de machine. Absent = comportement historique.
CONFIG = HERE / "chemins.json"

# Ou `deplace_docs.py` propose d'aller quand on ressort les documents de
# l'arbre : hors du depot, et sur un disque qu'on choisit. Ce n'est qu'un
# defaut d'argument — rien ne l'utilise tant qu'on ne deplace pas.
DEFAUT_AILLEURS = Path("D:/Recherche_emploi_documents")


def _base():
    """Racine des documents generes. Jamais d'exception : a defaut, la racine du projet."""
    try:
        cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
        p = (cfg.get("documents") or "").strip()
        if p:
            return Path(p)
    except (FileNotFoundError, ValueError, OSError):
        pass
    return ROOT


BASE = _base()

# ── Genere, volumineux, deplacable ──────────────────────────────────────────
CV_PAR_OFFRE = BASE / "CV" / "Par_offre"
LT_PAR_OFFRE = BASE / "Lettres" / "Par_offre"

# ── Ecrit a la main, minuscule, RESTE dans OneDrive ─────────────────────────
# Ancres sur ROOT et non sur BASE : deplacer les modeles n'economiserait rien
# et les sortirait de la sauvegarde. C'est l'inverse de ce qu'on cherche.
CV_MODELES = ROOT / "CV" / "Modèles"
LT_RELANCES = ROOT / "Lettres" / "Relances"
LT_MESSAGES = ROOT / "Lettres" / "Messages"

# Corps de lettre ecrits a la main pour UNE offre. Le gabarit generique sert
# 5374 annonces et ne peut rien dire de precis sur aucune ; quand une offre
# merite qu'on la travaille — un envoi direct a deux recruteurs nommes, par
# exemple — le corps se redige ici et `tailor_letter` le prend a la place du
# sien. L'en-tete, la date, l'objet, la formule d'appel et la cloture restent
# generes : ce sont eux qui savent nommer le destinataire et accorder la
# reprise.
#
# ENTREE, donc ancre sur ROOT et jamais touche par regenere_docs.py.
LT_SUR_MESURE = ROOT / "Lettres" / "Sur_mesure"

# Retouches de CV pour UNE offre : meme principe que la lettre. Sans ce dossier,
# une retouche se faisait dans CV/Par_offre — une SORTIE, que regenere_docs.py
# reconstruit entierement : elle disparaissait a la regeneration suivante.
CV_SUR_MESURE = ROOT / "CV" / "Sur_mesure"


def preparer():
    """Cree les dossiers de sortie. Appele par les programmes qui ecrivent."""
    for d in (CV_PAR_OFFRE, LT_PAR_OFFRE):
        d.mkdir(parents=True, exist_ok=True)
    return CV_PAR_OFFRE, LT_PAR_OFFRE


def deplace():  # pragma: no cover - outil d'administration, voir deplace_docs.py
    raise NotImplementedError("le deplacement se fait par deplace_docs.py")


if __name__ == "__main__":
    import sys

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    etat = f"chemins.json → {BASE}" if CONFIG.exists() else "defaut : la racine du projet"
    print(f"source du reglage : {etat}")
    for nom, p in (
        ("CV/Par_offre", CV_PAR_OFFRE),
        ("Lettres/Par_offre", LT_PAR_OFFRE),
        ("CV/Modeles", CV_MODELES),
        ("Lettres/Relances", LT_RELANCES),
        ("Lettres/Messages", LT_MESSAGES),
        ("Lettres/Sur_mesure", LT_SUR_MESURE),
        ("CV/Sur_mesure", CV_SUR_MESURE),
    ):
        n = len(list(p.glob("*"))) if p.exists() else 0
        print(f"  {nom:20} {'✓' if p.exists() else '✗'} {n:6} fichiers  {p}")
