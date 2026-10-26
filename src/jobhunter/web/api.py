"""What the web interface shows, computed from the queue and the applications.

Pure functions over plain lists and dicts, so the tests need neither a window nor files;
`Api` only loads the data through `storage` and hands the result to the page.
"""

from __future__ import annotations

import re
import webbrowser
from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import date, datetime
from typing import Any

# Statuses of an application still waiting for an answer (same as the follow-ups).
EN_ATTENTE = ("postulé", "relancé")
# Entries of the follow-up file that are not applications (offer set aside).
ECARTEES = ("mauvaise", "pas intéressé", "expiré")
# A follow-up is due after this many days (the J+7 template).
JOURS_RELANCE = 7
_RX_SCAN = re.compile(r"^Scan (\d{4}-\d{2}-\d{2})$")


def _fit(o: dict[str, Any], champ: str = "fit") -> float:
    try:
        return float(o.get(champ) or 0)
    except (TypeError, ValueError):
        return 0.0


def _oid(o: dict[str, Any]) -> str:
    return f"{(o.get('entreprise') or '').strip()}|{(o.get('poste') or '').strip()}"


def _date(texte: Any) -> date | None:
    try:
        return datetime.strptime(str(texte or ""), "%Y-%m-%d").date()
    except ValueError:
        return None


def tableau(
    offres: Sequence[Any],
    suivi: Mapping[str, Any],
    aujourd_hui: date | None = None,
) -> dict[str, Any]:
    """Everything the home screen draws, as JSON-ready data."""
    jour = aujourd_hui or date.today()
    par_oid = {_oid(o): o for o in offres}
    postulees = [k for k, v in suivi.items() if v.get("s") in EN_ATTENTE]

    # New offers per morning scan, the last seven scans.
    scans = Counter(m.group(1) for o in offres if (m := _RX_SCAN.match(str(o.get("statut") or ""))))
    derniers = sorted(scans)[-7:]
    collecte = [{"jour": j, "n": scans[j]} for j in derniers]

    a_traiter = [o for o in offres if _RX_SCAN.match(str(o.get("statut") or ""))]
    meilleures = sorted(a_traiter, key=lambda o: (-_fit(o), -_fit(o, "fit_fin")))[:5]

    relances: list[dict[str, Any]] = []
    for k in postulees:
        d = _date(suivi[k].get("d"))
        if d and (jour - d).days >= JOURS_RELANCE:
            entreprise, _, poste = k.partition("|")
            relances.append({"entreprise": entreprise, "poste": poste, "jours": (jour - d).days})
    relances.sort(key=lambda r: -r["jours"])

    zones = Counter(str(o.get("zone") or "inconnu") for o in offres if _fit(o) >= 7)
    total_zones = sum(zones.values()) or 1

    candidatures = []
    for k, v in suivi.items():
        if not v.get("s") or v.get("retiree") or v["s"] in ECARTEES:
            continue
        o = par_oid.get(k, {})
        entreprise, _, poste = k.partition("|")
        candidatures.append(
            {
                "entreprise": entreprise,
                "poste": poste,
                "statut": v["s"],
                "date": v.get("d") or "",
                "fit": _fit(o) if o else None,
            }
        )
    candidatures.sort(key=lambda c: c["date"], reverse=True)

    return {
        "stats": {
            "file": len(offres),
            "neuf": sum(1 for o in a_traiter if _fit(o) >= 9),
            "postulees": len(postulees),
        },
        "collecte": collecte,
        "meilleures": [
            {
                "poste": o.get("poste") or "",
                "entreprise": o.get("entreprise") or "",
                "lieu": o.get("localisation") or "",
                "fit": _fit(o),
                "url": o.get("url") or "",
            }
            for o in meilleures
        ],
        "relances": relances[:4],
        "zones": [
            {"zone": z, "n": n, "pct": round(100 * n / total_zones)}
            for z, n in zones.most_common(3)
        ],
        "candidatures": candidatures[:6],
    }


class Api:
    """Methods the page calls through `window.pywebview.api`."""

    def tableau(self) -> dict[str, Any]:
        """The home screen data, from the real queue and applications."""
        from jobhunter.storage import applications, queue

        return tableau(queue.charger(descriptions=False), applications.charger())

    def ouvrir(self, url: str) -> bool:
        """Opens an offer in the default browser; only web links."""
        if not re.match(r"^https?://", url or ""):
            return False
        return webbrowser.open(url)
