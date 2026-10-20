#!/usr/bin/env python3
"""jobhunter.storage.applications — The only access path to `suivi.json` (formerly Scripts/suivi_io.py).

WHY THIS FILE EXISTS. `suivi.json` keeps the APPLICATIONS: what
the user applied to, when, and where it stands. It is the least
reconstructible data of the project — a lost offer, the scan finds it again tomorrow;
a lost application never comes back.

Yet it was the only important file written WITHOUT a lock, by two
programs at once: the app (`_jwrite(SUIVI, self.suivi)`) and `follow_ups.py`.
And the app did not write a change — it rewrote its whole in-memory dictionary,
loaded at the last refresh. Hence this loss, reproduced:

    disk at start    : 3 applications
    app in memory    : 3 applications
    relances.py wrote: 2 follow-ups recorded
    the app writes   : 1 new application
    → follow-ups lost: 2

One "postulé" click on an offer erased two follow-ups on others, without a
word. `apply_queue.json` had had `queue_io` for exactly that for a long time;
`suivi.json`, nothing.

HOW TO USE. Never write the file directly. Go through `modifier`:

    import suivi_io
    def poser(s):
        s["Amundi|Analyste ESG"] = {"s": "postulé", "d": "2026-09-17"}
    suivi_io.modifier(poser)

`modifier` takes the lock, REREADS the disk inside, applies the function
on this fresh state, then writes. What another program wrote in the meantime is
therefore kept. An exception in the function cancels the write.

`charger()` for read-only access.

Decision: docs/adr/0002-three-files-three-contracts.md
"""

import datetime
import json
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path

from jobhunter import root as racine
from jobhunter.storage import atomic as atomique
from jobhunter.storage import data_format as _format
from jobhunter.storage import lock as verrou
from jobhunter.types import Candidature, Chemin, Preuve, Suivi

CHEMIN = racine.dans(racine.scripts(), "suivi.json")


class VerrouIndisponible(RuntimeError):
    """Another program is modifying the tracker and did not release it in time."""


def charger(chemin: Chemin | None = None) -> Suivi:
    """The tracker, read only.

    Args:
        chemin: the file; None = `Scripts/suivi.json` of the data folder.

    Returns:
        The applications by offer identity; empty dict if the file is missing
        or unreadable.
    """
    try:
        return _lire(Path(chemin or CHEMIN))
    except SuiviIllisible:
        return {}


class SuiviIllisible(RuntimeError):
    """The tracker file exists but cannot be read: we refuse to write over it."""


def _lire(p: Path) -> Suivi:
    """The tracker; {} if the file does not exist; SuiviIllisible if it exists but cannot be read.

    A write NEVER starts from a failed read. `charger` returned {} for a
    missing file as for a truncated JSON; the transaction then wrote that {}
    plus the new application, and all the others disappeared (audit of
    19/10/2026). The tracker is the least reconstructible data of the project.
    """
    try:
        brut = p.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {}
    except OSError as e:
        raise SuiviIllisible(
            f"{p.name} inaccessible ({type(e).__name__}) : rien n'est écrit"
        ) from e
    try:
        d = json.loads(brut)
    except ValueError as e:
        raise SuiviIllisible(
            f"{p.name} illisible (JSON invalide) : rien n'est écrit. Restaurer la dernière "
            "version (git, ou Scripts/_sauvegardes/) avant de continuer."
        ) from e
    if not isinstance(d, dict):
        raise SuiviIllisible(f"{p.name} : un objet JSON était attendu ; rien n'est écrit.")
    return d


@contextmanager
def transaction(chemin: Chemin | None = None, attente: float = 30) -> Iterator[Suivi]:
    """Lock + fresh reread + atomic write on leaving the block.

    Short `attente`: the callers are interactive (a click in the app) or
    brief (`follow_ups.py`). Better to say "try again" than to freeze the window.

    Args:
        chemin: the file; None = the one of the data folder.
        attente: seconds to wait for the lock.

    Yields:
        The freshly reread tracker, to modify in place.

    Raises:
        VerrouIndisponible: another program holds the tracker for more than `attente` s.
        SuiviIllisible: the file exists but cannot be read; it is left as is.
    """
    p = Path(chemin or CHEMIN)
    # `prendre_verrou` is reentrant, `rendre_verrou` is NOT: it releases
    # for good. If the caller already held the lock, we do not take it away from it.
    a_nous = not verrou.tenu(p)
    if a_nous and not verrou.prendre_verrou(p, attente=attente):
        raise VerrouIndisponible(
            f"{p.name} est modifié par un autre programme (attente {attente}s dépassée)"
        )
    try:
        suivi = _lire(p)  # raises SuiviIllisible rather than starting from {}
        _format.verifier_ecriture(p.parent)  # never over a newer JobHunter's data
        yield suivi
        atomique.ecrire_json(p, suivi)  # reached only if the block did not raise
    finally:
        if a_nous:
            verrou.rendre_verrou(p)


def modifier[T](fn: Callable[[Suivi], T], chemin: Chemin | None = None, attente: float = 30) -> T:
    """`fn(suivi)` under lock, on the FRESHLY reread state.

    Args:
        fn: the transformation.
        chemin: the file; None = the one of the data folder.
        attente: seconds to wait for the lock.

    Returns:
        What `fn` returns.

    Raises:
        VerrouIndisponible: another program holds the tracker too long.
    """
    with transaction(chemin, attente=attente) as suivi:
        return fn(suivi)


def poser(
    oid: str, rec: Candidature | None, chemin: Chemin | None = None, attente: float = 30
) -> None:
    """Writes (or erases, if `rec` is empty) the entry of an application.

    `attente`: to shorten when the caller is an interface. Tkinter is
    single-threaded — waiting 30 s in a click handler freezes the whole
    window, and the user thinks the app has crashed. Better to hand back
    quickly and display "try again".

    Args:
        oid: the offer's identity (`queue_io.oid`).
        rec: the application; empty or None erases the entry.
        chemin: the file; None = the one of the data folder.
        attente: seconds to wait for the lock.

    Raises:
        VerrouIndisponible: another program holds the tracker too long.
    """

    def _f(s: Suivi) -> None:
        if rec:
            s[oid] = rec
        else:
            s.pop(oid, None)

    return modifier(_f, chemin, attente=attente)


if __name__ == "__main__":
    import sys

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]  # console : TextIOWrapper
    s = charger()
    print(f"{len(s)} candidature(s) dans {CHEMIN.name}")
    for k, v in sorted(s.items())[:10]:
        print(f"  {k[:52]:52s} {v}")


# Statuses that come AFTER sending: declaring the sending does not move them back.
_APRES_ENVOI = ("relancé", "entretien", "refus")


def declarer_envoi(
    oid: str,
    envoi: str,
    preuve: Preuve | None = None,
    chemin: Chemin | None = None,
    attente: float = 30,
) -> Candidature:
    """Records an application sent by the user, with the state of its proof.

    A single write: status "postulé" (unless it is already further along: followed up,
    interview, refusal), today's date if the status changes, `envoi` and `preuve`. The note
    and the other fields of the reread entry are kept; a declaration without proof never
    replaces a proof already observed.

    Args:
        oid: the offer's identity (`queue_io.oid`).
        envoi: "confirmé", "incertain" or "déclaré" (ADR 0009).
        preuve: what the page displayed; None for a mere declaration.
        chemin: the file; None = the one of the data folder.
        attente: seconds to wait for the lock.

    Returns:
        The entry as written.

    Raises:
        VerrouIndisponible: another program holds the tracker too long.

    Decision: docs/adr/0009-proof-distinct-from-declaration.md
    """

    def _f(s: Suivi) -> Candidature:
        rec: Candidature = dict(s.get(oid) or {})  # type: ignore[assignment]  # copy of a Candidature
        if rec.get("s") not in ("postulé", *_APRES_ENVOI):
            rec["s"] = "postulé"
            rec["d"] = datetime.date.today().isoformat()
        rec.setdefault("d", datetime.date.today().isoformat())
        if preuve:
            rec["envoi"] = envoi
            rec["preuve"] = preuve
        else:  # mere declaration: never erases a proof already observed
            rec.setdefault("envoi", envoi)
        s[oid] = rec
        return rec

    return modifier(_f, chemin, attente)
