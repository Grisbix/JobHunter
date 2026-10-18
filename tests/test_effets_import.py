"""Charger le moteur n'ecrit rien, ne sort pas sur le reseau, et ne lit aucun fichier.

Phase 4 du plan. Mesure faite par un crochet d'audit (`sys.addaudithook`) dans un
processus neuf qui importe TOUS les modules de `jobhunter`. Avant : trois dossiers de
sortie crees a l'import (CV/Par_offre, Lettres/Par_offre, Lettres/Messages) ; ils le
sont maintenant au moment d'ecrire. Le profil et `Scripts/chemins.json` etaient lus
au chargement ; ce qui en est tire se calcule a la premiere lecture
(`jobhunter.paresseux`).
"""

import json
import os
import subprocess
import sys
import textwrap

from conftest import EXEMPLE, SRC

SONDE = textwrap.dedent(
    """
    import importlib, json, os, pkgutil, sys
    ev = {"ecritures": [], "reseau": [], "lectures": set()}
    def crochet(nom, args):
        if nom in ("os.mkdir", "os.rename", "os.replace", "os.remove", "shutil.rmtree"):
            if ".coverage" not in os.fsdecode(args[0]) and "__pycache__" not in os.fsdecode(args[0]):
                ev["ecritures"].append(f"{nom} {args[0]}")
        elif nom in ("socket.connect", "socket.getaddrinfo", "socket.sendto", "urllib.Request"):
            ev["reseau"].append(nom)
        elif nom == "open" and isinstance(args[0], (str, bytes, os.PathLike)):
            p = os.fsdecode(args[0])
            if isinstance(args[1], str) and any(c in args[1] for c in "wax+"):
                ev["ecritures"].append(f"open {p}")
            elif not p.endswith((".py", ".pyc", ".pyd", ".dll", ".so", ".pth")) \
                    and "__pycache__" not in p and "site-packages" not in p \
                    and os.path.isfile(p) \
                    and os.path.realpath(p).startswith(os.path.realpath(sys.argv[1])):
                ev["lectures"].add(os.path.relpath(p, sys.argv[1]).replace(os.sep, "/"))
    sys.addaudithook(crochet)
    import jobhunter
    for m in pkgutil.walk_packages(jobhunter.__path__, "jobhunter."):
        # les programmes (jobhunter.programmes) sont des commandes, pas le moteur
        if not m.name.endswith("__main__") and ".programmes" not in m.name:
            importlib.import_module(m.name)
    ev["lectures"] = sorted(ev["lectures"])
    print(json.dumps(ev))
    """
)


def _mesure():
    # Sans la couverture de pytest-cov : elle ecrirait ses .coverage.* dans ce processus.
    env = {k: v for k, v in os.environ.items() if not k.startswith(("COV_", "COVERAGE"))}
    # Le bytecode (__pycache__) est l'affaire de Python, pas du moteur.
    env.update(PYTHONPATH=str(SRC), PROFIL_JOBHUNTER=str(EXEMPLE), PYTHONDONTWRITEBYTECODE="1")
    env.pop("JOBHUNTER_RACINE", None)
    r = subprocess.run(
        [sys.executable, "-c", SONDE, str(SRC.parent)], env=env, capture_output=True, text=True
    )
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout.strip().splitlines()[-1])


MESURE = _mesure()


def test_aucune_ecriture_a_l_import():
    assert MESURE["ecritures"] == []


def test_aucun_reseau_a_l_import():
    assert MESURE["reseau"] == []


def test_aucune_lecture_a_l_import():
    assert MESURE["lectures"] == []
