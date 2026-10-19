"""Statuts de candidature depuis les courriels : propositions validées une à une (G4).

    jobhunter statuts-mail --mbox Takeout/Mail/Tous.mbox
    jobhunter statuts-mail --eml chemin/vers/dossier
    jobhunter statuts-mail --gmail [--jours 60]     # API Gmail, lecture seule
    jobhunter statuts-mail ... --liste               # montre, n'écrit rien

Pour chaque proposition : o = appliquer, n = ignorer, q = arrêter. Une proposition
acceptée écrit le statut, la date du courriel et le courriel cité (`courriel` : de,
sujet, date) dans le suivi, sous verrou et sur l'état relu ; la note et le reste de
l'entrée sont gardés. Voir jobhunter.courriels pour la lecture et ses garanties.
"""

import argparse
import datetime
import sys
from collections.abc import Callable, Iterable
from pathlib import Path

from jobhunter import racine as _racine
from jobhunter.courriels import lecture, statuts
from jobhunter.stockage import suivi as suivi_io
from jobhunter.types import Candidature, CourrielStatut, Suivi


def appliquer(p: statuts.Proposition, chemin: Path | None = None, attente: float = 30) -> bool:
    """Écrit la proposition si elle fait toujours avancer la candidature (état relu)."""

    def _f(s: Suivi) -> bool:
        rec: Candidature = dict(s.get(p.oid) or {})  # type: ignore[assignment]  # copie
        actuel = str(rec.get("s") or "")
        if actuel not in statuts._RANG or statuts._RANG[p.propose] <= statuts._RANG[actuel]:
            return False  # le suivi a bougé depuis la proposition
        rec["s"] = p.propose
        rec["d"] = p.le or datetime.date.today().isoformat()
        rec["courriel"] = CourrielStatut(de=p.de, sujet=p.sujet, le=p.le)
        s[p.oid] = rec
        return True

    return suivi_io.modifier(_f, chemin, attente=attente)


def courriels(a: argparse.Namespace) -> Iterable[lecture.Courriel]:
    if a.mbox:
        return lecture.depuis_mbox(Path(a.mbox))
    if a.eml:
        return lecture.depuis_eml(Path(a.eml))
    return lecture.depuis_gmail(_racine.scripts(), jours=a.jours)


def valider(
    props: list[statuts.Proposition],
    demander: Callable[[str], str] = input,
    chemin: Path | None = None,
) -> int:
    """Demande o/n/q pour chaque proposition ; rend le nombre de statuts écrits."""
    ecrits = 0
    for i, p in enumerate(props, 1):
        print(f"\n[{i}/{len(props)}] {p.oid}")
        print(f"  {p.actuel or '(sans statut)'} → {p.propose}   « {p.raison} »")
        print(f"  {p.le}  {p.de}")
        print(f"  {p.sujet}")
        r = demander("  Appliquer ? [o/n/q] ").strip().lower()
        if r == "q":
            break
        if r == "o":
            if appliquer(p, chemin):
                ecrits += 1
                print("  ✓ écrit")
            else:
                print("  = le suivi a changé entre-temps : rien écrit")
    return ecrits


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    ap = argparse.ArgumentParser(description="Statuts de candidature depuis les courriels.")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--mbox", help="un fichier .mbox (Google Takeout)")
    src.add_argument("--eml", help="un dossier de fichiers .eml")
    src.add_argument("--gmail", action="store_true", help="l'API Gmail, en lecture seule")
    ap.add_argument("--jours", type=int, default=60, help="ancienneté maximale (Gmail)")
    ap.add_argument(
        "--liste", action="store_true", help="montrer les propositions sans rien écrire"
    )
    a = ap.parse_args(argv)
    try:
        tous = list(courriels(a))
    except (FileNotFoundError, ImportError, PermissionError) as e:
        if isinstance(e, ImportError):
            print('! Lecture Gmail : installe d\'abord pip install "jobhunter[gmail]".')
        else:
            print(f"! {e}")
        return 1
    suivi = suivi_io.charger()
    props = statuts.propositions(tous, suivi)
    print(f"{len(tous)} courriel(s) lus, {len(props)} statut(s) à proposer.")
    if a.liste or not props:
        for p in props:
            print(f"  {p.le}  {p.oid} : {p.actuel or '—'} → {p.propose}  « {p.raison} »")
        return 0
    n = valider(props)
    print(f"\n{n} statut(s) écrit(s) dans le suivi.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
