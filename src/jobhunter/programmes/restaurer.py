#!/usr/bin/env python3
"""restaurer.py — Puts the queue back as it was in a backup: undoes a sort, an audit, a merge.

WHY. Three programs remove offers in bulk (the sort, the availability audit, the
merge's noise purge), and each takes a backup first. But nothing put a backup back:
undoing meant copying JSON files by hand, with the queue's lock ignored and the
descriptions annex forgotten. This program is the way back.

THE BACKUPS IT READS, all written by the engine itself:

    Scripts/_sauvegardes/<date>/             daily, before the pipeline's first step
    Scripts/_sauvegardes/<date>_avant_audit/ before the availability audit removes offers
    Scripts/apply_queue.json.avant_tri_*     before the sort removes offers (queue only)

THE RULES:

- Nothing is written without `--appliquer`: by default the program says which offers
  would come back and which would leave.
- The tracker (suivi.json) is NEVER restored. It is the least reconstructible data of
  the project: an old copy would erase the applications recorded since.
- An offer of the tracker stays in the queue even if the backup does not have it
  (AGENTS.md invariant: no automatic removal touches an offer applied to).
- No description is lost: each restored offer takes its text from the backup's annex,
  or failing that from the current one.
- The current state is copied first to `_sauvegardes/<date>_<time>_avant_restauration/`:
  a restoration can itself be undone with this same program.

    jobhunter restaurer --liste
    jobhunter restaurer 2026-10-19                  # what would change
    jobhunter restaurer 2026-10-19 --appliquer      # do it
"""

import argparse
import datetime
import json
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

from jobhunter.stockage import file as queue_io
from jobhunter.stockage import suivi as suivi_io

SUFFIXE_TRI = ".avant_tri_"


@dataclass
class Sauvegarde:
    """A backup of the queue that can be put back."""

    nom: str
    file: Path
    descriptions: Path | None


def _dossier() -> Path:
    # Derived from the queue's path, so that a test redirecting the queue redirects
    # the backups too.
    return Path(queue_io.CHEMIN).parent


def sauvegardes() -> list[Sauvegarde]:
    """The available backups, most recent first.

    Returns:
        One entry per backup holding a queue; the folders without one are ignored.
    """
    trouvees = []
    base = _dossier() / "_sauvegardes"
    if base.is_dir():
        for d in base.iterdir():
            f = d / "apply_queue.json"
            if d.is_dir() and f.is_file():
                desc = d / "descriptions.json"
                trouvees.append(Sauvegarde(d.name, f, desc if desc.is_file() else None))
    nom_file = Path(queue_io.CHEMIN).name
    for f in _dossier().glob(nom_file + SUFFIXE_TRI + "*"):
        trouvees.append(Sauvegarde("avant_tri_" + f.name.split(SUFFIXE_TRI, 1)[1], f, None))

    # Sort key: the timestamp carried by the name. "2026-10-19" (daily, taken before
    # everything that day) and "avant_tri_20261019_092812" become comparable.
    def quand(s):
        n = s.nom.removeprefix("avant_tri_").replace("-", "")
        return n[:8] + (n[9:15] if n[8:9] == "_" and n[9:15].isdigit() else "000000")

    return sorted(trouvees, key=quand, reverse=True)


def _lire(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def plan(courantes, anciennes, suivies):
    """The queue after restoration, and what changes.

    Args:
        courantes: the offers of the current queue.
        anciennes: the offers of the backup.
        suivies: the identities (oid) present in the tracker.

    Returns:
        (result, come back, leave, kept): the restored list, then the identities that
        come back, those that leave, and those kept only because they are tracked.
    """
    oid = queue_io.oid
    ids_anciennes = {oid(o) for o in anciennes}
    ids_courantes = {oid(o) for o in courantes}
    gardees = [o for o in courantes if oid(o) in suivies and oid(o) not in ids_anciennes]
    resultat = list(anciennes) + gardees
    ids_resultat = {oid(o) for o in resultat}
    revenues = sorted(ids_anciennes - ids_courantes)
    parties = sorted(ids_courantes - ids_resultat)
    return resultat, revenues, parties, sorted(oid(o) for o in gardees)


def _copier_etat_actuel() -> Path:
    cible = (
        _dossier()
        / "_sauvegardes"
        / (datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S") + "_avant_restauration")
    )
    cible.mkdir(parents=True, exist_ok=True)
    for src in (Path(queue_io.CHEMIN), Path(queue_io.DESCRIPTIONS)):
        if src.is_file():
            shutil.copy2(src, cible / src.name)
    return cible


def restaurer(nom: str, appliquer: bool = False, montrer: int = 15) -> int:
    """Puts back the queue of backup `nom`. Returns the exit code."""
    choix = [s for s in sauvegardes() if s.nom == nom]
    if not choix:
        print(f"Sauvegarde inconnue : {nom}. Les sauvegardes : jobhunter restaurer --liste")
        return 2
    s = choix[0]
    anciennes = _lire(s.file)
    if not isinstance(anciennes, list):
        print(f"Sauvegarde illisible : {s.file}")
        return 2
    textes_sauvegarde = _lire(s.descriptions) if s.descriptions else None
    if not isinstance(textes_sauvegarde, dict):
        textes_sauvegarde = {}
    suivies = set(suivi_io.charger())

    if not appliquer:
        resultat, revenues, parties, gardees = plan(queue_io.charger(), anciennes, suivies)
        _bilan(s, resultat, revenues, parties, gardees, montrer)
        print("\n[INSPECTION] rien n'a été écrit. --appliquer pour restaurer.")
        return 0

    with queue_io.transaction() as offres:
        # Inside the lock: the copy is the state really replaced.
        copie = _copier_etat_actuel()
        textes = {queue_io.oid(o): o["description"] for o in offres if o.get("description")}
        resultat, revenues, parties, gardees = plan(offres, anciennes, suivies)
        for o in resultat:
            if not (o.get("description") or "").strip():
                t = textes_sauvegarde.get(queue_io.oid(o)) or textes.get(queue_io.oid(o))
                if t:
                    o["description"] = t
        offres[:] = resultat
    _bilan(s, resultat, revenues, parties, gardees, montrer)
    print(f"\nRestaurée. L'état d'avant est dans {copie.parent.name}/{copie.name}")
    print(f"(pour l'annuler : jobhunter restaurer {copie.name} --appliquer)")
    return 0


def _bilan(s, resultat, revenues, parties, gardees, montrer):
    print(f"Sauvegarde {s.nom} : {len(resultat)} offres après restauration")
    print(f"  reviennent : {len(revenues)}")
    for i in revenues[:montrer]:
        print(f"    + {i}")
    print(f"  partent    : {len(parties)}")
    for i in parties[:montrer]:
        print(f"    - {i}")
    if gardees:
        print(f"  gardées car dans le suivi : {len(gardees)}")
    print("  le suivi (suivi.json) n'est jamais restauré")


def main(argv=None) -> int:
    """Command line: `jobhunter restaurer`."""
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    ap = argparse.ArgumentParser(
        prog="jobhunter restaurer",
        description="Remet la file d'offres telle qu'elle était dans une sauvegarde.",
    )
    ap.add_argument("nom", nargs="?", help="la sauvegarde (voir --liste)")
    ap.add_argument("--liste", action="store_true", help="liste les sauvegardes")
    ap.add_argument("--appliquer", action="store_true", help="écrit (sinon : inspection)")
    a = ap.parse_args(argv)
    if a.liste or not a.nom:
        liste = sauvegardes()
        if not liste:
            print("Aucune sauvegarde.")
            return 0
        for s in liste:
            offres = _lire(s.file)
            n = len(offres) if isinstance(offres, list) else "?"
            textes = "" if s.descriptions else "  (sans fichier de descriptions)"
            print(f"  {s.nom:42} {n:>6} offres{textes}")
        return 0
    try:
        return restaurer(a.nom, a.appliquer)
    except queue_io.VerrouIndisponible as e:
        print(f"File occupée : {e}")
        return 3


if __name__ == "__main__":
    sys.exit(main())
