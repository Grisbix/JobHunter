#!/usr/bin/env python3
"""jobhunter.stockage.suivi — Le seul chemin d'accès à `suivi.json` (ancien Scripts/suivi_io.py).

POURQUOI CE FICHIER EXISTE. `suivi.json` garde les CANDIDATURES : ce à quoi
l'utilisateur a postulé, quand, et où ça en est. C'est la donnée la moins
reconstituable du projet — une offre perdue, le scan la retrouve demain ;
une candidature perdue ne revient jamais.

Elle était pourtant le seul fichier important écrit SANS verrou, par deux
programmes à la fois : l'app (`_jwrite(SUIVI, self.suivi)`) et `relances.py`.
Et l'app n'écrivait pas une modification — elle réécrivait tout son dictionnaire
en mémoire, chargé au dernier rafraîchissement. D'où cette perte, reproduite :

    disque au depart : 3 candidatures
    app en memoire   : 3 candidatures
    relances.py ecrit: 2 relances notees
    l'app ecrit      : 1 nouvelle candidature
    → relances perdues : 2

Un clic « postulé » sur une offre effaçait deux relances sur d'autres, sans un
mot. `apply_queue.json` avait `queue_io` pour exactement ça depuis longtemps ;
`suivi.json`, rien.

MODE D'EMPLOI. Ne jamais écrire le fichier en direct. Passer par `modifier` :

    import suivi_io
    def poser(s):
        s["Amundi|Analyste ESG"] = {"s": "postulé", "d": "2026-09-17"}
    suivi_io.modifier(poser)

`modifier` prend le verrou, RELIT le disque à l'intérieur, applique la fonction
sur cet état frais, puis écrit. Ce qu'un autre programme a écrit entre-temps est
donc conservé. Une exception dans la fonction annule l'écriture.

`charger()` pour la lecture seule.
"""

import json
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path

from jobhunter import racine
from jobhunter.stockage import atomique, verrou
from jobhunter.types import Candidature, Chemin, Suivi

CHEMIN = racine.scripts() / "suivi.json"


class VerrouIndisponible(RuntimeError):
    """Un autre programme modifie le suivi et ne l'a pas relâché à temps."""


def charger(chemin: Chemin | None = None) -> Suivi:
    """Le suivi, en lecture.

    Args:
        chemin: le fichier ; None = `Scripts/suivi.json` du dossier des données.

    Returns:
        Les candidatures par identité d'offre ; dict vide si le fichier manque
        ou est illisible.
    """
    p = Path(chemin or CHEMIN)
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return d if isinstance(d, dict) else {}


@contextmanager
def transaction(chemin: Chemin | None = None, attente: float = 30) -> Iterator[Suivi]:
    """Verrou + relecture fraîche + écriture atomique à la sortie du bloc.

    `attente` courte : les appelants sont interactifs (un clic dans l'app) ou
    brefs (`relances.py`). Mieux vaut dire « réessaie » que figer la fenêtre.

    Args:
        chemin: le fichier ; None = celui du dossier des données.
        attente: secondes d'attente du verrou.

    Yields:
        Le suivi fraîchement relu, à modifier en place.

    Raises:
        VerrouIndisponible: un autre programme garde le suivi plus de `attente` s.
    """
    p = Path(chemin or CHEMIN)
    # `prendre_verrou` est reentrant, `rendre_verrou` ne l'est PAS : il libere
    # pour de bon. Si l'appelant tenait deja le verrou, on ne le lui retire pas.
    a_nous = not verrou.tenu(p)
    if a_nous and not verrou.prendre_verrou(p, attente=attente):
        raise VerrouIndisponible(
            f"{p.name} est modifié par un autre programme (attente {attente}s dépassée)"
        )
    try:
        suivi = charger(p)
        yield suivi
        atomique.ecrire_json(p, suivi)  # atteint seulement si le bloc n'a pas levé
    finally:
        if a_nous:
            verrou.rendre_verrou(p)


def modifier[T](fn: Callable[[Suivi], T], chemin: Chemin | None = None, attente: float = 30) -> T:
    """`fn(suivi)` sous verrou, sur l'état FRAÎCHEMENT relu.

    Args:
        fn: la transformation.
        chemin: le fichier ; None = celui du dossier des données.
        attente: secondes d'attente du verrou.

    Returns:
        Ce que `fn` renvoie.

    Raises:
        VerrouIndisponible: un autre programme garde le suivi trop longtemps.
    """
    with transaction(chemin, attente=attente) as suivi:
        return fn(suivi)


def poser(
    oid: str, rec: Candidature | None, chemin: Chemin | None = None, attente: float = 30
) -> None:
    """Écrit (ou efface, si `rec` est vide) l'entrée d'une candidature.

    `attente` : à raccourcir quand l'appelant est une interface. Tkinter est
    mono-fil — attendre 30 s dans un gestionnaire de clic fige la fenêtre
    entière, et l'utilisateur croit l'app plantée. Mieux vaut rendre la main
    vite et afficher « réessaie ».

    Args:
        oid: l'identité de l'offre (`queue_io.oid`).
        rec: la candidature ; vide ou None efface l'entrée.
        chemin: le fichier ; None = celui du dossier des données.
        attente: secondes d'attente du verrou.

    Raises:
        VerrouIndisponible: un autre programme garde le suivi trop longtemps.
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
