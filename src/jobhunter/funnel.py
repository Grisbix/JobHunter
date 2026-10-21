"""From sending to answer: how many applications got a response, how fast, and where.

Read from the tracking's status history `h` ([[date, status], ...], written by
storage.applications since 3.15). An entry older than the history has only its last
status and date: it still counts as sent or answered, but gives no delay.

Pure functions: the app's Statistics panel and the weekly report both call `entonnoir`.
"""

import datetime
import statistics
from collections.abc import Callable, Iterable, Mapping
from typing import Any

ENVOYEES = ("postulé", "relancé", "entretien", "refus")
REPONSES = ("entretien", "refus")
SILENCE_JOURS = 30  # sent this long ago and no answer: count it as silence


def _jour(texte: Any) -> datetime.date | None:
    try:
        return datetime.date.fromisoformat(str(texte)[:10])
    except ValueError:
        return None


def historique(rec: Mapping[str, Any]) -> list[tuple[datetime.date | None, str]]:
    """[(date, status)] of an entry, oldest first; its last status alone when it has no `h`."""
    h = rec.get("h")
    if isinstance(h, list) and h:
        return [(_jour(d), str(s)) for d, s in h if s]
    s = str(rec.get("s") or "")
    return [(_jour(rec.get("d")), s)] if s else []


def envoi(rec: Mapping[str, Any]) -> datetime.date | None:
    """The day the application left: its first "postulé"; None if never sent or undated."""
    h = historique(rec)
    for d, s in h:
        if s == "postulé":
            return d
    # Sent before the history existed: "relancé" or an answer, without the day of sending.
    return None


def reponse(rec: Mapping[str, Any]) -> tuple[datetime.date | None, str] | None:
    """(day, status) of the first answer (interview or refusal); None if none yet."""
    for d, s in historique(rec):
        if s in REPONSES:
            return d, s
    return None


def entonnoir(
    suivi: Mapping[str, Mapping[str, Any]],
    offres: Mapping[str, Mapping[str, Any]] | None = None,
    jour: datetime.date | None = None,
    par: Iterable[str] = ("contrat", "domaine", "canal"),
    libelle: Callable[[str, Any], str] | None = None,
) -> dict[str, Any]:
    """The applications sent, answered, and how fast.

    Args:
        suivi: the tracking, by offer identity.
        offres: the queue by identity, to split by contract, domain, channel.
        jour: today (tests).
        par: the offer fields to split by.
        libelle: names a field's value (default: the value, "—" if empty).

    Returns:
        {envoyees, reponses, entretiens, refus, taux, delai_median, delais, silence,
         par: {field: [(value, sent, answered, interviews)]}}
    """
    jour = jour or datetime.date.today()
    offres = offres or {}
    nom = libelle or (lambda _champ, v: str(v or "—").strip() or "—")
    out: dict[str, Any] = {"envoyees": 0, "reponses": 0, "entretiens": 0, "refus": 0}
    delais: list[int] = []
    silence = 0
    groupes: dict[str, dict[str, list[int]]] = {c: {} for c in par}
    for oid, rec in suivi.items():
        if not isinstance(rec, Mapping):
            continue
        statuts = {s for _, s in historique(rec)}
        if not statuts & set(ENVOYEES):
            continue
        out["envoyees"] += 1
        r = reponse(rec)
        d_env = envoi(rec)
        if r:
            out["reponses"] += 1
            out["entretiens" if r[1] == "entretien" else "refus"] += 1
            if d_env and r[0] and r[0] >= d_env:
                delais.append((r[0] - d_env).days)
        elif d_env and (jour - d_env).days >= SILENCE_JOURS:
            silence += 1
        o = offres.get(oid) or {}
        for champ in par:
            g = groupes[champ].setdefault(nom(champ, o.get(champ)), [0, 0, 0])
            g[0] += 1
            if r:
                g[1] += 1
                g[2] += r[1] == "entretien"
    out["taux"] = out["reponses"] / out["envoyees"] if out["envoyees"] else None
    out["delais"] = sorted(delais)
    out["delai_median"] = statistics.median(delais) if delais else None
    out["silence"] = silence
    out["par"] = {
        c: sorted(((v, *n) for v, n in g.items()), key=lambda x: (-x[1], x[0]))
        for c, g in groupes.items()
    }
    return out
