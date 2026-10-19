"""Does the ranking put at the top the offers the user judges good?

Part of jobhunter.scoring. The reference set already exists in the tracking: an offer
one applied to (or is about to apply to) was judged relevant; an offer marked
"mauvaise" or "pas intéressé" was judged useless. The ranking is the engine's:
`fit_fin` (the decimal fit), failing that `fit`.

Measures:

AUC             probability that a relevant offer is scored higher than a useless
                offer (0.5 = random, 1 = perfect), with an interval by resampling:
                with a few dozen judgements, the figure moves, and that must be known
                before comparing two versions.
precision@N     share of relevant ones among the N best scored, N = number of relevant ones.

It is the reference figure before any scoring variant (roadmap C1).
"""

import random
import re
from collections.abc import Iterable, Mapping
from typing import Any

PERTINENT = ("postulé", "relancé", "entretien", "refus", "à postuler")
INUTILE = ("mauvaise", "pas intéressé")
# "mauvaise" was also used for a FACT, before the "expiré" status existed: job
# filled, page without an offer, seen too late. The ranking cannot foresee it: these
# offers do not count as scoring errors.
_RX_FAIT = re.compile(r"pourvu|pas d'offre|trop tard|expir|ferm[ée]|plus en ligne", re.I)


def jugements(suivi: Mapping[str, Mapping[str, Any]]) -> dict[str, bool]:
    """The judged offers, according to their tracking status.

    Args:
        suivi: the tracking, indexed by offer identity.

    Returns:
        {identity: True if judged relevant, False if useless}; the other statuses
        (expiré, à vérifier…) say nothing about relevance and are ignored, like a
        "mauvaise" whose note states a fact (filled, page without an offer, too late).
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
    """Probability that a positive score exceeds a negative score (tie = 1/2).

    Returns:
        The AUC, or None if positives or negatives are missing.
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
    """Evaluates the ranking of the judged offers still present in the queue.

    Args:
        offres: the queue.
        suivi: the tracking.
        oid: the identity function of an offer (`queue_io.oid`).

    Returns:
        {pertinentes, inutiles, auc, intervalle, precision, pires}; `pires` gives the
        best-scored useless offers and the worst-scored relevant ones, where the
        ranking is most wrong.
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
