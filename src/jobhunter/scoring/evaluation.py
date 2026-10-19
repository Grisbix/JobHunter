"""Le classement range-t-il en tête les offres que l'utilisateur juge bonnes ?

Partie de jobhunter.scoring. Le jeu de référence existe déjà dans le suivi : une offre à
laquelle on a postulé (ou qu'on s'apprête à postuler) a été jugée pertinente ; une offre
marquée « mauvaise » ou « pas intéressé » a été jugée inutile. Le classement est celui du
moteur : `fit_fin` (le fit décimal), à défaut `fit`.

Mesures :

AUC             probabilité qu'une offre pertinente soit mieux notée qu'une offre
                inutile (0,5 = au hasard, 1 = parfait), avec un intervalle par
                rééchantillonnage : avec quelques dizaines de jugements, le chiffre
                bouge, et il faut le savoir avant de comparer deux versions.
précision@N     part de pertinentes parmi les N mieux notées, N = nombre de pertinentes.

C'est le chiffre de référence avant toute variante du scoring (feuille de route C1).
"""

import random
import re
from collections.abc import Iterable, Mapping
from typing import Any

PERTINENT = ("postulé", "relancé", "entretien", "refus", "à postuler")
INUTILE = ("mauvaise", "pas intéressé")
# « mauvaise » a aussi servi pour un FAIT, avant que le statut « expiré » existe : poste
# pourvu, page sans offre, vu trop tard. Le classement ne peut pas le prévoir : ces
# offres ne comptent pas comme des erreurs de notation.
_RX_FAIT = re.compile(r"pourvu|pas d'offre|trop tard|expir|ferm[ée]|plus en ligne", re.I)


def jugements(suivi: Mapping[str, Mapping[str, Any]]) -> dict[str, bool]:
    """Les offres jugées, d'après leur statut de suivi.

    Args:
        suivi: le suivi, indexé par identité d'offre.

    Returns:
        {identité: True si jugée pertinente, False si inutile} ; les autres statuts
        (expiré, à vérifier…) ne disent rien de la pertinence et sont ignorés, comme une
        « mauvaise » dont la note dit un fait (pourvu, page sans offre, trop tard).
    """
    sortie = {}
    for oid, c in suivi.items():
        s = str(c.get("s") or "")
        if s in PERTINENT:
            sortie[oid] = True
        elif s in INUTILE and not _RX_FAIT.search(str(c.get("n") or "")):
            sortie[oid] = False
    return sortie


def note(offre: Mapping[str, Any]) -> float:
    """La note de classement d'une offre : `fit_fin`, à défaut `fit`, à défaut 0."""
    for cle in ("fit_fin", "fit"):
        v = offre.get(cle)
        if isinstance(v, (int, float)):
            return float(v)
    return 0.0


def auc(positives: list[float], negatives: list[float]) -> float | None:
    """Probabilité qu'une note positive dépasse une note négative (égalité = 1/2).

    Returns:
        L'AUC, ou None s'il manque des positives ou des négatives.
    """
    if not positives or not negatives:
        return None
    gagne = sum(1.0 if p > n else 0.5 if p == n else 0.0 for p in positives for n in negatives)
    return gagne / (len(positives) * len(negatives))


def precision_n(notes: Iterable[tuple[float, bool]]) -> float | None:
    """Part de pertinentes parmi les N mieux notées, N = nombre de pertinentes."""
    liste = sorted(notes, key=lambda x: -x[0])
    n = sum(1 for _, pertinent in liste if pertinent)
    if not n:
        return None
    return sum(1 for _, pertinent in liste[:n] if pertinent) / n


def intervalle(
    positives: list[float], negatives: list[float], tirages: int = 500, graine: int = 0
) -> tuple[float, float] | None:
    """Intervalle à 90 % de l'AUC par rééchantillonnage (reproductible : graine fixe)."""
    if not positives or not negatives:
        return None
    alea = random.Random(graine)
    valeurs = []
    for _ in range(tirages):
        p = [alea.choice(positives) for _ in positives]
        n = [alea.choice(negatives) for _ in negatives]
        valeurs.append(auc(p, n) or 0.0)
    valeurs.sort()
    return valeurs[int(0.05 * tirages)], valeurs[int(0.95 * tirages) - 1]


def evaluer(
    offres: Iterable[Mapping[str, Any]],
    suivi: Mapping[str, Mapping[str, Any]],
    oid: Any,
) -> dict[str, Any]:
    """Évalue le classement des offres jugées encore présentes dans la file.

    Args:
        offres: la file.
        suivi: le suivi.
        oid: la fonction d'identité d'une offre (`queue_io.oid`).

    Returns:
        {pertinentes, inutiles, auc, intervalle, precision, pires} ; `pires` donne les
        inutiles les mieux notées et les pertinentes les moins bien notées, là où le
        classement se trompe le plus.
    """
    juges = jugements(suivi)
    notes: list[tuple[float, bool, Mapping[str, Any]]] = [
        (note(o), juges[oid(o)], o) for o in offres if oid(o) in juges
    ]
    pos = [n for n, j, _ in notes if j]
    neg = [n for n, j, _ in notes if not j]
    inutiles_hautes = sorted((x for x in notes if not x[1]), key=lambda x: -x[0])[:5]
    pertinentes_basses = sorted((x for x in notes if x[1]), key=lambda x: x[0])[:5]
    return {
        "pertinentes": len(pos),
        "inutiles": len(neg),
        "auc": auc(pos, neg),
        "intervalle": intervalle(pos, neg),
        "precision": precision_n((n, j) for n, j, _ in notes),
        "pires": {
            "inutiles_hautes": [
                (n, o.get("entreprise"), o.get("poste")) for n, _, o in inutiles_hautes
            ],
            "pertinentes_basses": [
                (n, o.get("entreprise"), o.get("poste")) for n, _, o in pertinentes_basses
            ],
        },
    }
