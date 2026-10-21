"""The state of the morning collection, readable without the log.

The daily pipeline writes `_derniere_collecte.json` in the data folder when it starts
and when it ends: start, end, exit code, run identifier, log, last success. The
application reads it and says in one line whether the collection is fresh, running,
failed or missed, with a button to start it again.

Why. On 21 October 2026 the scheduled task did not even start (its start-in folder had
been renamed): no log, no error anywhere the user looks, and the table simply stopped
receiving offers. Finding out took a person reading the Task Scheduler. A collection
that did not happen must be as visible as one that failed.
"""

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jobhunter import root as _racine

FICHIER = "_derniere_collecte.json"
RETARD_H = 26  # a daily collection, plus two hours of slack
FORMAT = "%Y-%m-%d %H:%M:%S"


def _chemin(chemin: Path | None = None) -> Path | None:
    if chemin is not None:
        return chemin
    try:
        return _racine.scripts() / FICHIER
    except RuntimeError:
        return None


def lire(chemin: Path | None = None) -> dict[str, Any]:
    """The last recorded state; {} when there is none or it is unreadable."""
    p = _chemin(chemin)
    try:
        d = json.loads(p.read_text(encoding="utf-8")) if p else {}
    except (OSError, ValueError):
        return {}
    return d if isinstance(d, dict) else {}


def _ecrire(d: dict[str, Any], chemin: Path | None = None) -> None:
    p = _chemin(chemin)
    if p is None:
        return
    try:
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(p)
    except OSError:
        pass  # the collection itself must never fail on its status line


def debut(execution: str, journal: str = "", chemin: Path | None = None) -> None:
    """The pipeline starts: running, with its PID (a crash leaves it to be detected)."""
    d = lire(chemin)
    d.update(
        etat="en_cours",
        debut=time.strftime(FORMAT),
        debut_epoch=time.time(),
        fin=None,
        code=None,
        pid=os.getpid(),
        execution=execution,
        journal=journal,
    )
    _ecrire(d, chemin)


def fin(code: int, erreurs: list[str] | None = None, chemin: Path | None = None) -> None:
    """The pipeline reached its end: the collection happened, whatever its code.

    Code 1 only says that one step failed (a source refused, a folder to review) —
    eight mornings out of ten in October 2026. That is a finished collection with
    `erreurs` (the names of the failed steps), not a failure.
    """
    d = lire(chemin)
    maintenant = time.strftime(FORMAT)
    d.update(etat="ok", fin=maintenant, code=code, erreurs=list(erreurs or []))
    d["dernier_succes"] = maintenant
    _ecrire(d, chemin)


def plantage(erreur: str, chemin: Path | None = None) -> None:
    """The pipeline stopped on an exception: nothing after it ran."""
    d = lire(chemin)
    d.update(etat="echec", fin=time.strftime(FORMAT), code=None, erreurs=[erreur])
    _ecrire(d, chemin)


@dataclass(frozen=True)
class Diagnostic:
    """niveau: "ok", "en_cours", "retard" (nothing recent) or "echec"."""

    niveau: str
    texte: str

    @property
    def a_relancer(self) -> bool:
        """Missed or stopped: the application offers to start the collection."""
        return self.niveau in ("retard", "echec")


def _ident(s: str) -> str:
    return s


def _quand(s: str | None, maintenant: float, tr: Any = _ident) -> str:
    """« aujourd'hui 08:04 », « hier 08:04 » or « 19/10 08:04 »."""
    try:
        t = time.mktime(time.strptime(s or "", FORMAT))
    except ValueError:
        return "?"
    jour = time.localtime(t)
    auj = time.localtime(maintenant)
    heure = time.strftime("%H:%M", jour)
    if jour.tm_yday == auj.tm_yday and jour.tm_year == auj.tm_year:
        return str(tr("aujourd'hui {a}")).format(a=heure)
    hier = time.localtime(maintenant - 86400)
    if jour.tm_yday == hier.tm_yday and jour.tm_year == hier.tm_year:
        return str(tr("hier {a}")).format(a=heure)
    return time.strftime("%d/%m %H:%M", jour)


def _age_h(s: str | None, maintenant: float) -> float | None:
    try:
        return (maintenant - time.mktime(time.strptime(s or "", FORMAT))) / 3600
    except ValueError:
        return None


def diagnostic(
    etat: dict[str, Any] | None = None,
    maintenant: float | None = None,
    vivant: Any = None,
    tr: Any = _ident,
) -> Diagnostic:
    """One line on the collection, for the application.

    `vivant(pid, depuis)` tells whether the recorded process still runs (tests pass
    their own; by default the lock module's, which knows that Windows recycles PIDs).
    `tr` translates the sentence templates (the application passes its language's).
    """
    d = lire() if etat is None else etat
    t = time.time() if maintenant is None else maintenant
    if vivant is None:
        from jobhunter.storage.lock import _pid_vivant as vivant

    def q(s: str | None) -> str:
        return _quand(s, t, tr)

    def f(modele: str, **v: str) -> str:
        return str(tr(modele)).format(**v)

    succes = d.get("dernier_succes")
    depuis = f("dernière réussie : {a}", a=q(succes)) if succes else f("aucune réussie")
    if d.get("etat") == "en_cours":
        if vivant(d.get("pid"), d.get("debut_epoch")):
            return Diagnostic("en_cours", f("Collecte en cours depuis {a}", a=q(d.get("debut"))))
        return Diagnostic(
            "echec", f("Collecte interrompue ({a}) — {b}", a=q(d.get("debut")), b=depuis)
        )
    if d.get("etat") == "echec":
        age = _age_h(d.get("fin"), t)
        if age is not None and age < RETARD_H:
            quoi = ", ".join(d.get("erreurs") or []) or "?"
            return Diagnostic(
                "echec",
                f("Collecte arrêtée ({a} : {b}) — {c}", a=q(d.get("fin")), b=quoi, c=depuis),
            )
    age = _age_h(succes, t)
    if age is None:
        return Diagnostic("retard", f("Aucune collecte du matin enregistrée"))
    if age >= RETARD_H:
        return Diagnostic("retard", f("Pas de collecte depuis {a}", a=q(succes)))
    texte = f("Collecte du matin : {a} ✓", a=q(succes))
    if d.get("erreurs") and d.get("etat") == "ok":
        texte += f(" · en erreur : {a}", a=", ".join(d["erreurs"]))
    return Diagnostic("ok", texte)
