"""Where the ranking disagrees with the user's own choices, and which setting would help.

`scoring.evaluation` says HOW WELL the ranking orders the judged offers (AUC). This
says WHERE it goes wrong and tries the settings of `scoring.ranking` that could fix
it, on the same judgements:

- by contract, domain and zone: how many offers judged relevant and useless, and
  their mean rank. "V.I.E: 9 relevant, 1 useless, mean rank 6.9" says the user wants
  V.I.E. offers the fit puts low;
- for each contract, the bonus (0.25 to 1.5) that raises the AUC most, kept only if
  the gain survives resampling: the lower bound of its 90 % interval above zero.
  With a few dozen judgements, a gain that does not pass that bar is noise, and
  following it would teach the ranking the accidents of a sample.

Nothing is changed: the result is a suggestion for the profile's `classement`
section, which the user writes (or not).
"""

import random
from collections.abc import Callable, Iterable, Mapping
from typing import Any

from jobhunter.scoring.evaluation import auc, jugements
from jobhunter.scoring.ranking import rang, reglages

PAS = (0.25, 0.5, 1.0, 1.5)


def _juges(
    offres: Iterable[Mapping[str, Any]],
    suivi: Mapping[str, Mapping[str, Any]],
    oid: Callable[[Any], str],
) -> list[tuple[Mapping[str, Any], bool]]:
    j = jugements(suivi)
    return [(o, j[oid(o)]) for o in offres if oid(o) in j]


def par_valeur(
    juges: list[tuple[Mapping[str, Any], bool]], champ: str, r: Mapping[str, Any] | None = None
) -> list[tuple[str, int, int, float]]:
    """[(value, relevant, useless, mean rank)] of a field, most judged first."""
    r = r or reglages()
    g: dict[str, list[float]] = {}
    for o, pertinent in juges:
        v = str(o.get(champ) or "—").strip() or "—"
        e = g.setdefault(v, [0, 0, 0.0])
        e[0 if pertinent else 1] += 1
        e[2] += rang(o, r)
    return sorted(
        ((v, int(p), int(u), s / (p + u)) for v, (p, u, s) in g.items()),
        key=lambda x: (-(x[1] + x[2]), x[0]),
    )


def gain(
    juges: list[tuple[Mapping[str, Any], bool]],
    avant: Mapping[str, Any],
    apres: Mapping[str, Any],
    tirages: int = 400,
    graine: int = 0,
) -> tuple[float, float, float] | None:
    """(AUC gain, 90 % interval low, high) of `apres` over `avant`, paired resampling."""
    pos = [o for o, p in juges if p]
    neg = [o for o, p in juges if not p]
    if not pos or not neg:
        return None

    def d(ps: list[Any], ns: list[Any]) -> float:
        a = auc([rang(o, apres) for o in ps], [rang(o, apres) for o in ns]) or 0.0
        b = auc([rang(o, avant) for o in ps], [rang(o, avant) for o in ns]) or 0.0
        return a - b

    alea = random.Random(graine)
    valeurs = sorted(
        d([alea.choice(pos) for _ in pos], [alea.choice(neg) for _ in neg]) for _ in range(tirages)
    )
    return d(pos, neg), valeurs[int(0.05 * tirages)], valeurs[int(0.95 * tirages) - 1]


def suggestions(
    juges: list[tuple[Mapping[str, Any], bool]], r: Mapping[str, Any] | None = None
) -> list[dict[str, Any]]:
    """The best bonus of each contract with three relevant offers or more.

    With its AUC gain, the gain's 90 % interval, and `fiable` (the low bound above zero).
    """
    r = dict(r or reglages())
    out = []
    for contrat, p, _u, _m in par_valeur(juges, "contrat", r):
        if p < 3:
            continue  # too few relevant offers to learn anything about this contract
        base = float(r["bonus_contrat"].get(contrat, 0.0))
        meilleur: dict[str, Any] | None = None
        for pas in PAS:
            essai = {**r, "bonus_contrat": {**r["bonus_contrat"], contrat: base + pas}}
            g = gain(juges, r, essai)
            if g and (meilleur is None or g[0] > meilleur["gain"]):
                meilleur = {
                    "contrat": contrat,
                    "bonus": base + pas,
                    "gain": g[0],
                    "bas": g[1],
                    "haut": g[2],
                }
        if meilleur and meilleur["gain"] > 0:
            meilleur["fiable"] = meilleur["bas"] > 0
            out.append(meilleur)
    return sorted(out, key=lambda x: -x["gain"])


def analyser(
    offres: Iterable[Mapping[str, Any]],
    suivi: Mapping[str, Mapping[str, Any]],
    oid: Callable[[Any], str],
    champs: Iterable[str] = ("contrat", "domaine", "zone"),
) -> dict[str, Any]:
    """{juges, par: {field: par_valeur}, suggestions} for `jobhunter evaluation --analyse`."""
    r = reglages()
    juges = _juges(offres, suivi, oid)
    return {
        "juges": len(juges),
        "par": {c: par_valeur(juges, c, r) for c in champs},
        "suggestions": suggestions(juges, r),
    }
