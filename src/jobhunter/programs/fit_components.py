"""What the fit of each offer in the queue is made of, as JSON on stdout.

For the "Comprendre le fit" panel: the components that no weight changes
(scoring.fit.Composantes) are read once, here, in a separate process — ten thousand
texts take a few seconds, which would freeze the window. The panel then recomputes the
queue's fits for each change of weights (scoring.weights.bilan) without reading a text.

Same text as rescore_ats: title, missions, required profile, description.
"""

import json
import sys
from typing import Any

from jobhunter.scoring import fit as _fit
from jobhunter.storage import queue as queue_io

CHAMPS = ("poste", "missions", "profil", "description")


def texte(o: Any) -> str:
    return " ".join(str(o.get(k) or "") for k in CHAMPS)


def ligne(c: _fit.Composantes, axes: list[str]) -> list:
    # Not rounded: a fit at x.5 would round the other way.
    return [
        [c.axes.get(a, 0.0) for a in axes],
        c.plafond,
        c.junior,
        c.senior,
        c.ecarte,
        c.annees,
    ]


def depuis_ligne(r: list, axes: list[str]) -> _fit.Composantes:
    v, plafond, junior, senior, ecarte, annees = r
    return _fit.Composantes(dict(zip(axes, v)), plafond, junior, senior, ecarte, annees)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    axes = list(_fit.AXES)
    lignes = []
    for o in queue_io.charger():
        try:
            c = _fit.composantes(texte(o), o.get("poste", ""))
        except Exception:  # nosec B112 : one unreadable offer does not stop the panel
            continue
        lignes.append(ligne(c, axes))
    json.dump({"axes": axes, "lignes": lignes}, sys.stdout, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
