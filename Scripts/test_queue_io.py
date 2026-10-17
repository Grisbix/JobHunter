#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_queue_io.py — accès concurrent à la file (queue_io).

Ce module existe pour rendre impossible l'oubli du verrou. Les tests vérifient
donc surtout ce qui doit ARRIVER quand deux programmes se marchent dessus.

Run : python test_queue_io.py
"""

import _profil_test  # noqa: F401  — les tests tournent sur le profil d'exemple
import sys
import json
import subprocess
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import queue_io
import jutil

PASS = FAIL = 0


def check(nom, obtenu, attendu):
    global PASS, FAIL
    if obtenu == attendu:
        PASS += 1
        print(f"  ✅ {nom}")
    else:
        FAIL += 1
        print(f"  ❌ {nom}\n       obtenu {obtenu!r}, attendu {attendu!r}")


tmp = Path(tempfile.mkdtemp()) / "q.json"
tmp.write_text(json.dumps([{"entreprise": "A", "fit": 1}]), encoding="utf-8")

print("\n── A. lecture et écriture ──")
check("charger", queue_io.charger(tmp), [{"entreprise": "A", "fit": 1}])
check("fichier absent → liste vide", queue_io.charger(tmp.parent / "rien.json"), [])

with queue_io.transaction(tmp) as offres:
    offres[0]["fit"] = 9
check("transaction écrit", queue_io.charger(tmp)[0]["fit"], 9)

print("\n── B. le verrou est bien pris pendant le bloc ──")
SONDE = (
    "import sys, pathlib; sys.path.insert(0, r'%s'); import jutil;"
    "print(jutil.prendre_verrou(pathlib.Path(r'%s'), attente=2, bavard=False))"
    % (str(Path(__file__).resolve().parent), str(tmp))
)


def autre_processus():
    r = subprocess.run([sys.executable, "-c", SONDE], capture_output=True, text=True)
    return r.stdout.strip()


with queue_io.transaction(tmp) as offres:
    check("autre processus bloqué PENDANT", autre_processus(), "False")
check("autre processus passe APRÈS", autre_processus(), "True")
jutil.rendre_verrou(tmp)  # la sonde a laissé le verrou derriere elle

print("\n── C. une exception n'écrit rien ──")
avant = queue_io.charger(tmp)
try:
    with queue_io.transaction(tmp) as offres:
        offres.append({"entreprise": "NE DOIT PAS ETRE ECRIT"})
        raise ValueError("boum")
except ValueError:
    pass
check("file inchangée après exception", queue_io.charger(tmp), avant)
check("verrou relâché malgré l'exception", autre_processus(), "True")
jutil.rendre_verrou(tmp)

print("\n── D. relecture fraîche DANS le verrou ──")
# Un autre programme ecrit pendant qu'on ne tient pas encore le verrou : la
# transaction doit repartir de SON etat, pas d'une copie perimee.
perime = queue_io.charger(tmp)
tmp.write_text(json.dumps([{"entreprise": "ECRIT_PAR_UN_AUTRE", "fit": 5}]), encoding="utf-8")
with queue_io.transaction(tmp) as offres:
    check(
        "la transaction voit l'état FRAIS, pas le périmé",
        offres[0]["entreprise"],
        "ECRIT_PAR_UN_AUTRE",
    )
    offres[0]["fit"] = 7
check(
    "le travail de l'autre n'est pas effacé",
    queue_io.charger(tmp)[0]["entreprise"],
    "ECRIT_PAR_UN_AUTRE",
)
check("notre modification est bien là", queue_io.charger(tmp)[0]["fit"], 7)

print("\n── E. modifier() ──")
n = queue_io.modifier(lambda offres: len(offres), chemin=tmp)
check("renvoie la valeur de fn", n, 1)

print("\n── F. le nom du module ne masque pas la stdlib ──")
import queue as stdlib_queue

check("`import queue` reste la file d'attente standard", hasattr(stdlib_queue, "Queue"), True)

print("\n── G. descriptions dans un fichier annexe ──")
# On travaille sur les VRAIS chemins du module : la séparation ne s'applique
# qu'à apply_queue.json, pas à un fichier de test quelconque.
vrai_q, vrai_d = queue_io.CHEMIN, queue_io.DESCRIPTIONS
bac = Path(tempfile.mkdtemp())
queue_io.CHEMIN = bac / "apply_queue.json"
queue_io.DESCRIPTIONS = bac / "descriptions.json"
try:
    with queue_io.transaction() as offres:
        offres.extend(
            [
                {
                    "entreprise": "Amundi",
                    "poste": "Analyste ESG",
                    "fit": 9,
                    "description": "x" * 4000,
                },
                {"entreprise": "BNP", "poste": "Analyste Risque", "fit": 7, "description": ""},
            ]
        )
    brut = json.loads(queue_io.CHEMIN.read_text(encoding="utf-8"))
    check("la file ne contient PLUS les descriptions", any("description" in o for o in brut), False)
    check(
        "le fichier annexe les contient",
        len(json.loads(queue_io.DESCRIPTIONS.read_text(encoding="utf-8"))),
        1,
    )
    check(
        "la file pèse moins que les descriptions",
        queue_io.CHEMIN.stat().st_size < queue_io.DESCRIPTIONS.stat().st_size,
        True,
    )

    relu = queue_io.charger()
    check("charger() les RÉINJECTE", len(relu[0]["description"]), 4000)
    check("une description vide n'est pas stockée", relu[1].get("description", ""), "")

    with queue_io.transaction() as offres:  # aller-retour : rien ne se perd
        offres[0]["fit"] = 10
    r2 = queue_io.charger()
    check("aller-retour conserve la description", len(r2[0]["description"]), 4000)
    check("aller-retour conserve la modification", r2[0]["fit"], 10)

    with queue_io.transaction() as offres:  # offre supprimée
        del offres[0]
    check(
        "description orpheline purgée",
        json.loads(queue_io.DESCRIPTIONS.read_text(encoding="utf-8")),
        {},
    )

    check(
        "descriptions=False n'injecte rien",
        "description" in queue_io.charger(descriptions=False)[0],
        False,
    )

    # LE CHEMIN DANGEREUX : ecrire sans avoir lu le fichier annexe. Si la purge
    # des orphelines s'appliquait la, elle ne verrait AUCUNE description vivante
    # et effacerait tout. Deux offres, une seule decrite, pour le prouver.
    with queue_io.transaction() as offres:
        offres.append(
            {"entreprise": "Mirova", "poste": "Analyste", "fit": 8, "description": "y" * 3000}
        )
    # à ce stade la file contient BNP (sans description) puis Mirova (avec)
    avant_desc = json.loads(queue_io.DESCRIPTIONS.read_text(encoding="utf-8"))
    check("1 description en place (BNP n'en a pas)", len(avant_desc), 1)
    with queue_io.transaction(descriptions=False) as offres:
        offres[0]["fit"] = 3  # on ne touche a aucune description
    apres_desc = json.loads(queue_io.DESCRIPTIONS.read_text(encoding="utf-8"))
    check("écriture SANS descriptions n'efface rien", apres_desc, avant_desc)
    check("le champ modifié est bien écrit", queue_io.charger()[0]["fit"], 3)
    check("la description de Mirova survit", len(queue_io.charger()[1]["description"]), 3000)
finally:
    queue_io.CHEMIN, queue_io.DESCRIPTIONS = vrai_q, vrai_d

print(f"\n=== BILAN : {PASS} ✅  /  {FAIL} ❌  ({PASS}/{PASS + FAIL}) ===")
if __name__ == "__main__":
    sys.exit(1 if FAIL else 0)
