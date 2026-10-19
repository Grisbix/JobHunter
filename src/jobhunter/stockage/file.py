#!/usr/bin/env python3
"""jobhunter.stockage.file — single access to apply_queue.json (formerly Scripts/queue_io.py).

WHY THIS MODULE. Fourteen programs write the queue, and each reimplemented
the same sequence: take the lock, reread the disk, modify, write
atomically, release. Only one forgot it — the app — and it was a potential
data loss. A sequence copied fourteen times always ends up diverging.

    from queue_io import transaction, charger

    offres = charger()                     # read only, no lock

    with transaction() as offres:          # lock + fresh reread
        for o in offres:
            o["fit"] = 10
    # leaving the block: atomic write, then lock released

FILE NAME. Above all not `queue.py`: `queue` is a standard library module,
`Scripts/` is in sys.path, and JobHunter.pyw does `import queue`.
Shadowing it would break the application.

Decision: docs/adr/0002-three-files-three-contracts.md
"""

import json
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path

from jobhunter import racine
from jobhunter.stockage import atomique, verrou
from jobhunter.types import Chemin, Offre

HERE = racine.scripts()
CHEMIN = HERE / "apply_queue.json"

# ── Descriptions kept apart ──────────────────────────────────────────────────────
# The descriptions weighed 8.3 MB of the queue's 11.6 MB, i.e. 64 %. Yet the 13
# programs that modify ONE offer rewrote the WHOLE file: 142 ms per
# cycle, most of it copying texts nobody had touched.
# So they live in an annex file, indexed by offer.
#
# The separation is INVISIBLE to callers: `charger` reinjects the
# `description` field, writing takes it out. None of the 22 uses of `o["description"]`
# n'a eu besoin de changer.
DESCRIPTIONS = HERE / "descriptions.json"


def oid(offre: Offre) -> str:
    """Stable identifier of an offer: "entreprise|poste".

    Unique over the 2613 real offers (checked), and already the app's convention.
    Above all NOT the URL: it changes when a better-ranked duplicate promotes it.

    Args:
        offre: an offer of the queue.

    Returns:
        "entreprise|poste", as written in the offer.
    """
    return f"{(offre.get('entreprise') or '').strip()}|{(offre.get('poste') or '').strip()}"


def _lire_descriptions() -> dict[str, str]:
    try:
        textes: dict[str, str] = json.loads(DESCRIPTIONS.read_text(encoding="utf-8"))
        return textes
    except (FileNotFoundError, ValueError):
        return {}


def _est_la_file(p: Chemin) -> bool:
    """Does `p` designate THE queue (the one whose descriptions live apart)?

    Compares the RESOLVED paths: `Path("apply_queue.json")` run from Scripts/
    is not equal to CHEMIN (absolute). Compared as is, it lost the 11,710
    descriptions on reading, and `sauver` would have rewritten them into the queue.
    """
    try:
        return Path(p).resolve() == Path(CHEMIN).resolve()
    except OSError:
        return False


def charger(chemin: Chemin | None = None, descriptions: bool = True) -> list[Offre]:
    """The offers, READ ONLY, descriptions reinjected.

    No lock: since writes are atomic (tmp + os.replace), a read
    never sees a half-written file. Do not use if you intend to
    rewrite — see `transaction`.

    `descriptions=False` avoids reading the annex file when it is not
    needed: that is where the time saving is.

    Args:
        chemin: the queue to read; None = `Scripts/apply_queue.json` of the data folder.
        descriptions: reinject the postings' text (annex file).

    Returns:
        The offers; an empty list if the file is missing.
    """
    p = Path(chemin or CHEMIN)
    try:
        offres: list[Offre] = json.loads(p.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return []
    if descriptions and _est_la_file(p):
        textes = _lire_descriptions()
        if textes:
            for o in offres:
                if not (o.get("description") or "").strip():
                    t = textes.get(oid(o))
                    if t:
                        o["description"] = t
    return offres


def sauver(
    offres: list[Offre], chemin: Chemin | None = None, _avant: dict[str, str] | None = None
) -> None:
    """Atomic write, WITHOUT lock.

    Reserved for cases where the caller already holds the lock. When in doubt, use
    `transaction`. The postings' text goes into the annex file, which is only
    rewritten if it changed.

    Args:
        offres: all the offers; their `description` field is removed then put back.
        chemin: the queue to write; None = the one of the data folder.
        _avant: the descriptions already read by the caller. `transaction` passes
            them on — without that, `sauver` reread the 8.8 MB that `charger` had just
            read, 63 ms thrown away at each write.
    """
    p = Path(chemin or CHEMIN)
    if not _est_la_file(p):  # test file: no separation
        atomique.ecrire_json(p, offres)
        return

    # THREE STEPS, so that no failure loses a description still
    # in use. 1) the annex receives the new texts, WITHOUT removing anything; 2) the
    # queue is published; 3) only then are the orphans purged. A failure
    # between two steps only leaves orphans, harmless. The previous order
    # (purge then queue) lost the description of a removed offer if writing
    # the queue then failed: the queue kept the offer, the annex no longer had its
    # text (audit of 19/10/2026). Two atomic files do not make a
    # transaction; this order stands in for one.
    avant = _lire_descriptions() if _avant is None else _avant
    textes = dict(avant)
    vivants = set()
    for o in offres:
        cle_o = oid(o)
        vivants.add(cle_o)
        t = (o.pop("description", "") or "").strip()
        if t:
            textes[cle_o] = t
    purgees = textes
    if _avant is None or avant:
        # purge of the orphans. Skipped when the caller did not read the annex
        # file (transaction descriptions=False): we could not tell
        # "orphan" from "not loaded", and we would erase everything.
        purgees = {k: v for k, v in textes.items() if k in vivants}

    # WRITE ONLY WHAT CHANGED. Systematically rewriting the 8.8 MB of
    # descriptions cost 230 ms per transaction — more expensive than the old
    # single file. Yet almost all writes touch NO
    # description: they change a fit, a status, a URL. The purge, for its part,
    # only happens when offers leave the queue.
    try:
        if textes != avant:
            atomique.ecrire_json(DESCRIPTIONS, textes)  # 1) ajouts seulement
        atomique.ecrire_json(p, offres)  # 2) the queue
        if purgees != textes:
            atomique.ecrire_json(DESCRIPTIONS, purgees)  # 3) purge
    finally:
        for o in offres:  # the caller keeps its complete object, even after a failure
            texte = textes.get(oid(o))
            if texte:
                o["description"] = texte


class VerrouIndisponible(RuntimeError):
    """Un autre programme modifie la file et ne l'a pas relâchée à temps."""


@contextmanager
def transaction(
    chemin: Chemin | None = None,
    attente: float = 180,
    relire: bool = True,
    descriptions: bool = True,
) -> Iterator[list[Offre]]:
    """Lock + fresh reread + atomic write on leaving the block.

    `relire`: rereads the disk INSIDE the lock. That is the essential point.
    Loading the queue then taking the lock leaves a window during which another
    program writes — we would then start from a stale state and
    erase its work.

    An exception in the block CANCELS the write: better to write nothing
    than to write a half-transformed state.

    `descriptions=False`: does NOT read the annex file (8.8 MB, 63 ms) and
    leaves it as is. That is where the speed gain is — for programs that
    change a fit, a status or a URL without touching the postings' text.
    The offers will then have no `description` field, and orphan descriptions
    are not purged: that is the job of a complete write.

    Args:
        chemin: the queue; None = the one of the data folder.
        attente: seconds to wait for the lock.
        relire: reread the disk once the lock is taken (keep true).
        descriptions: also read and rewrite the postings' text.

    Yields:
        The list of offers, to modify in place.

    Raises:
        VerrouIndisponible: another program holds the queue for more than `attente` s.
    """
    p = Path(chemin or CHEMIN)
    # `prendre_verrou` is reentrant, `rendre_verrou` is NOT: it releases for
    # good. A nested transaction released its caller's lock, which carried on
    # without it (audit of 19/10/2026). Like `suivi.transaction`: we only release the
    # lock we took.
    a_nous = not verrou.tenu(p)
    if a_nous and not verrou.prendre_verrou(p, attente=attente):
        raise VerrouIndisponible(
            f"{p.name} est modifié par un autre programme (attente {attente}s dépassée)"
        )
    try:
        # A single read of the descriptions for the whole transaction: it
        # serves to reinject them on entry, THEN to know on exit whether they
        # changed. Rereading them in sauver cost 63 ms for nothing.
        textes = _lire_descriptions() if (relire and descriptions and _est_la_file(p)) else {}
        offres = charger(p, descriptions=False) if relire else []
        if textes:
            for o in offres:
                if not (o.get("description") or "").strip():
                    t = textes.get(oid(o))
                    if t:
                        o["description"] = t
        yield offres
        sauver(offres, p, _avant=textes)  # reached only if the block did not raise
    finally:
        if a_nous:
            verrou.rendre_verrou(p)


def modifier[T](
    fn: Callable[[list[Offre]], T], chemin: Chemin | None = None, attente: float = 180
) -> T:
    """`fn(offres)` under lock. Returns what `fn` returns.

    Sugar for programs that only have one transformation to apply:

        n = modifier(lambda offres: sum(1 for o in offres if o.pop("vieux", None)))

    Args:
        fn: the transformation, applied to the freshly reread list.
        chemin: the queue; None = the one of the data folder.
        attente: seconds to wait for the lock.

    Returns:
        What `fn` returns.

    Raises:
        VerrouIndisponible: another program holds the queue too long.
    """
    with transaction(chemin, attente=attente) as offres:
        return fn(offres)


if __name__ == "__main__":
    q = charger()
    print(f"{len(q)} offres dans {CHEMIN.name}")
