"""The weights of the fit that the user can tune, and what they do to a whole queue.

The fit (scoring.fit.fit_detail) is made of two kinds of things:

- what the offer says, which no weight changes: how much of each axis its text covers,
  the cap set by its title, its language and the share of the core target, whether
  the title is junior, senior or set aside, the years of experience it asks for
  (`fit.Composantes`);
- the weights (`Ponderation`): one per axis, the weighted score worth 10, the junior
  bonus, the senior penalty, the penalty per years of experience asked for.

Kept apart, a change of weights is recomputed on ten thousand offers in a few
milliseconds: the "Comprendre le fit" panel shows the effect on the queue while the
user moves a slider, and writes the profile only on "Enregistrer".
"""

from __future__ import annotations

import copy
from collections import Counter
from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterable

    from jobhunter.scoring.fit import Composantes

# The defaults of scoring.fit, for a profile that does not set them.
CIBLE = 3.0
BONUS_JUNIOR = 1.0
MALUS_SENIOR = 2.0


@dataclass(frozen=True)
class Ponderation:
    """The weights of the fit that the user can tune."""

    axes: dict[str, float]
    cible: float = CIBLE
    bonus_junior: float = BONUS_JUNIOR
    malus_senior: float = MALUS_SENIOR
    # years asked for -> penalty; the highest step reached applies
    malus_experience: dict[int, float] = field(default_factory=dict)

    def malus_annees(self, annees: int) -> float:
        """The penalty for `annees` years asked for: the highest step reached."""
        paliers = sorted(self.malus_experience.items(), reverse=True)
        return next((m for seuil, m in paliers if annees >= seuil), 0.0)

    def avec(self, **changes: Any) -> Ponderation:
        """A copy with some weights changed."""
        return replace(self, **changes)


def lire(profil: dict[str, Any]) -> Ponderation:
    """The weights a profile (the JSON as a dict) sets, defaults filled in."""
    sc = profil.get("scoring") or {}
    niv = profil.get("niveau") or {}
    return Ponderation(
        axes={a: float(v.get("poids", 1.0)) for a, v in (sc.get("axes") or {}).items()},
        cible=float(sc.get("cible_score", CIBLE)),
        bonus_junior=float(niv.get("bonus_junior", BONUS_JUNIOR)),
        malus_senior=float(niv.get("malus_senior", MALUS_SENIOR)),
        malus_experience={int(k): float(v) for k, v in (niv.get("malus_experience") or {}).items()},
    )


def _nombre(v: float) -> float | int:
    """3.0 stays 3.0 for a weight; a penalty step written 1 in the profile stays 1."""
    return int(v) if float(v).is_integer() else v


def appliquer(profil: dict[str, Any], p: Ponderation) -> dict[str, Any]:
    """A copy of the profile carrying `p`.

    Only what differs is written: an unchanged default does not appear in the profile.
    """
    avant = lire(profil)
    out = copy.deepcopy(profil)
    sc = out.setdefault("scoring", {})
    niv = out.setdefault("niveau", {})
    for axe, poids in p.axes.items():
        if axe in (sc.get("axes") or {}) and avant.axes.get(axe) != poids:
            sc["axes"][axe]["poids"] = float(poids)
    if p.cible != avant.cible:
        sc["cible_score"] = float(p.cible)
    if p.bonus_junior != avant.bonus_junior:
        niv["bonus_junior"] = float(p.bonus_junior)
    if p.malus_senior != avant.malus_senior:
        niv["malus_senior"] = float(p.malus_senior)
    if p.malus_experience != avant.malus_experience:
        niv["malus_experience"] = {
            str(k): _nombre(v) for k, v in sorted(p.malus_experience.items())
        }
    if not niv:
        del out["niveau"]
    return out


def valider(p: Ponderation) -> list[str]:
    """What prevents saving, in plain words. Empty = can be saved."""
    erreurs = []
    if p.cible <= 0:
        erreurs.append("le score qui vaut 10 doit être plus grand que 0")
    if any(v < 0 for v in p.axes.values()):
        erreurs.append("un poids d'axe ne peut pas être négatif")
    if not any(v > 0 for v in p.axes.values()):
        erreurs.append("au moins un axe doit compter")
    if p.bonus_junior < 0 or p.malus_senior < 0:
        erreurs.append("bonus et malus s'écrivent sans signe moins")
    if any(v < 0 for v in p.malus_experience.values()):
        erreurs.append("un malus d'expérience ne peut pas être négatif")
    return erreurs


@dataclass(frozen=True)
class Bilan:
    """The queue's fits under some weights."""

    n: int
    moyenne: float
    haut: int  # fit >= 8
    repartition: dict[int, int]  # fit 1..10 -> number of offers


def bilan(composantes: Iterable[Composantes], p: Ponderation) -> Bilan:
    """The queue's fits under the weights `p`: mean, offers at 8 and more, distribution."""
    from jobhunter.scoring.fit import fit_entier

    fits = [fit_entier(c, p) for c in composantes]
    rep = Counter(fits)
    n = len(fits)
    return Bilan(
        n=n,
        moyenne=sum(fits) / n if n else 0.0,
        haut=sum(1 for f in fits if f >= 8),
        repartition={f: rep.get(f, 0) for f in range(1, 11)},
    )
