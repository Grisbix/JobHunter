#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_suivi.py — une candidature enregistrée ne doit JAMAIS disparaître.

Le suivi (statut, note, date) vit dans suivi.json, indexé par « entreprise|poste ».
Il survit à tout ce qui réécrit la file — scans, régénération de documents,
re-scoring — parce que ce sont deux fichiers séparés.

Le seul point de rupture est la disparition de l'OFFRE : la trace devient alors
orpheline et invisible dans l'app. C'est arrivé pour de vrai — `linkedin_closed`
a retiré une offre Volkswagen à laquelle l'utilisateur avait postulé, parce que
LinkedIn n'acceptait plus de candidature. Or une annonce ferme presque toujours
APRÈS qu'on y a postulé : l'outil supprimait donc en priorité les offres suivies.

Run : python test_suivi.py
"""

import _profil_test  # noqa: F401  — les tests tournent sur le profil d'exemple
import sys
import json
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import queue_io
import linkedin_closed as L

PASS = FAIL = 0


def check(nom, obtenu, attendu):
    global PASS, FAIL
    if obtenu == attendu:
        PASS += 1
        print(f"  ✅ {nom}")
    else:
        FAIL += 1
        print(f"  ❌ {nom}\n       obtenu {obtenu!r}, attendu {attendu!r}")


print("\n── A. la clé du suivi est la même partout ──")
offre = {"entreprise": " Amundi ", "poste": " Analyste ESG "}
check("linkedin_closed et queue_io s'accordent", L._oid_offre(offre), queue_io.oid(offre))
check("espaces retirés", queue_io.oid(offre), "Amundi|Analyste ESG")

print("\n── B. le suivi survit à une réécriture de la file ──")
bac = Path(tempfile.mkdtemp())
vrai_q, vrai_d = queue_io.CHEMIN, queue_io.DESCRIPTIONS
queue_io.CHEMIN = bac / "apply_queue.json"
queue_io.DESCRIPTIONS = bac / "descriptions.json"
try:
    with queue_io.transaction() as q:
        q.append(
            {"entreprise": "Amundi", "poste": "Analyste ESG", "fit": 9, "description": "z" * 500}
        )
    suivi = {"Amundi|Analyste ESG": {"s": "postulé", "d": "2026-09-03"}}

    with queue_io.transaction() as q:  # scan, re-scoring, régénération…
        q[0]["fit"] = 10
        q[0]["url"] = "https://autre-source.example/offre"
    apres = queue_io.charger()
    check("l'offre garde sa clé après modification", queue_io.oid(apres[0]) in suivi, True)
    check("le suivi pointe toujours dessus", suivi[queue_io.oid(apres[0])]["s"], "postulé")
    check("la description a survécu", len(apres[0]["description"]), 500)
finally:
    queue_io.CHEMIN, queue_io.DESCRIPTIONS = vrai_q, vrai_d

print("\n── C. suppression automatique : une offre suivie est ÉPARGNÉE ──")
# Reproduit le tri de linkedin_closed : parmi les offres fermées, celles qui
# portent une candidature ne doivent pas entrer dans la liste des suppressions.
q = [
    {"entreprise": "Volkswagen", "poste": "Analyste Data"},  # suivie
    {"entreprise": "Zzz", "poste": "Analyste Quelconque"},
]  # non suivie
res = {0: L.FERME, 1: L.FERME}
suivis = {"Volkswagen|Analyste Data"}
fermes = [i for i, v in res.items() if v == L.FERME and L._oid_offre(q[i]) not in suivis]
check("l'offre suivie n'est PAS supprimée", 0 in fermes, False)
check("l'offre non suivie l'est bien", 1 in fermes, True)
check("une seule suppression", len(fermes), 1)

print("\n── C bis. deux écrivains, aucune perte (suivi_io) ──")
# L'app écrivait `self.suivi`, son instantané mémoire : un clic « postulé »
# réécrivait TOUT le fichier et effaçait ce que relances.py venait d'y mettre.
# Reproduit à l'époque : deux relances perdues, sans un mot.
import suivi_io
import jutil as _jutil

_tmp = Path(tempfile.mkdtemp()) / "suivi.json"
_jutil.jwrite(
    _tmp,
    {
        "Amundi|Analyste ESG": {"s": "postulé", "d": "2026-09-05"},
        "BNP Paribas|Analyste": {"s": "postulé", "d": "2026-09-06"},
    },
)
_instantane = suivi_io.charger(_tmp)  # ce que l'app tient en mémoire

# relances.py passe et note deux relances
suivi_io.modifier(
    lambda s: [s.__setitem__(k, dict(s[k], s="relancé", relance="2026-09-17")) for k in list(s)],
    _tmp,
)
# puis l'app pose une NOUVELLE candidature depuis son instantané périmé
suivi_io.poser("Sweep|ESG Analyst", {"s": "postulé", "d": "2026-09-17"}, _tmp)

_final = suivi_io.charger(_tmp)
check(
    "les 2 relances survivent",
    sum(1 for v in _final.values() if v.get("relance") == "2026-09-17"),
    2,
)
check("la nouvelle candidature est là", "Sweep|ESG Analyst" in _final, True)
check("3 candidatures au total", len(_final), 3)
check("l'instantané de l'app était bien périmé", len(_instantane), 2)

# une exception au milieu n'écrit rien
_avant = _tmp.read_text(encoding="utf-8")
try:
    with suivi_io.transaction(_tmp) as _s:
        _s["Zzz|Casse"] = {"s": "ne doit pas survivre"}
        raise RuntimeError("panne au milieu")
except RuntimeError:
    pass
check("exception au milieu → rien d'écrit", _tmp.read_text(encoding="utf-8"), _avant)

print("\n── D. sur les données réelles ──")
try:
    reel = json.loads((Path(__file__).resolve().parent / "suivi.json").read_text(encoding="utf-8"))
except Exception:
    reel = {}
ids = {queue_io.oid(o) for o in queue_io.charger(descriptions=False)}
# `retiree` : ligne retiree expres de la file (ex. « pas_une_offre », annonce
# fantome Amundi du 2026-10-05). L'entree reste dans le suivi, sans offre.
orphelines = [k for k in reel if k not in ids and not reel[k].get("retiree")]
check(f"{len(reel)} candidature(s), aucune orpheline", orphelines, [])

print(f"\n=== BILAN : {PASS} ✅  /  {FAIL} ❌  ({PASS}/{PASS + FAIL}) ===")
if __name__ == "__main__":
    sys.exit(1 if FAIL else 0)
