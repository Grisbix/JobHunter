#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_metriques_hebdo.py — le bilan du lundi compte ce qui existe vraiment.

L'ancien bilan (script Hermes) lisait des sources disparues et affichait des
zéros sans erreur. Ces cas vérifient les comptes sur des données construites,
sans réseau ni fichier réel : dates aux deux formats du suivi, entrées sans
date, seuil de relance, journaux du pipeline et jours sans run.

Run : python test_metriques_hebdo.py
"""

import _profil_test  # noqa: F401  — les tests tournent sur le profil d'exemple
import sys
import tempfile
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import metriques_hebdo as M

PASS = FAIL = 0


def check(nom, obtenu, attendu):
    global PASS, FAIL
    if obtenu == attendu:
        PASS += 1
        print(f"  ✅ {nom}")
    else:
        FAIL += 1
        print(f"  ❌ {nom}\n       obtenu {obtenu!r}, attendu {attendu!r}")


AUJ = date(2026, 10, 12)

print("\n── A. dates du suivi ──")
check("ISO", M.lire_date("2026-10-07", AUJ), date(2026, 10, 7))
check("jj/mm de cette année", M.lire_date("04/09", AUJ), date(2026, 9, 4))
check("jj/mm dans le futur = l'an passé", M.lire_date("20/12", AUJ), date(2025, 12, 20))
check("vide", M.lire_date("", AUJ), None)
check("None", M.lire_date(None, AUJ), None)
check("illisible", M.lire_date("bientôt", AUJ), None)

print("\n── B. comptes des candidatures ──")
suivi = {
    "A|Analyste": {"s": "postulé", "d": "2026-10-10"},  # cette semaine
    "B|Chargé": {"s": "postulé", "d": "2026-09-20"},  # à relancer (22 j)
    "C|Consultant": {"s": "relancé", "d": "2026-10-01"},  # à relancer (11 j)
    "D|Data": {"s": "postulé", "d": ""},  # sans date
    "E|Entretien": {"s": "entretien", "d": "2026-10-05"},  # réponse < 30 j
    "F|Refus": {"s": "refus", "d": "2026-08-01"},  # réponse > 30 j
    "G|Mauvaise": {"s": "mauvaise", "d": "2026-10-11"},  # pas envoyée
    "H|Rien": {"n": "note seule"},  # sans statut
    "I|Vide": None,
}
b = M.bilan_suivi(suivi, AUJ)
check("envoyées sur 7 jours", b["envoyees_periode"], 1)
check("en attente (postulé + relancé)", b["en_attente"], 4)
check("réponses sur 30 jours", b["reponses_30j"], 1)
check("envoyées au total", b["envoyees_total"], 6)
check("taux de réponse cumulé", b["taux_reponse"], 2 / 6)
check("sans date comptée à part", b["sans_date"], 1)
check("à relancer, plus vieille d'abord", b["a_relancer"], [("B|Chargé", 22), ("C|Consultant", 11)])
check("une « mauvaise » n'est pas une candidature", b["statuts"]["mauvaise"], 1)
check("entrée sans statut comptée", b["statuts"]["(aucun)"], 2)
check(
    "statut en majuscules reconnu",
    M.bilan_suivi({"X|Y": {"s": "Postulé", "d": "2026-10-11"}}, AUJ)["envoyees_periode"],
    1,
)
check("suivi vide : pas de division par zéro", M.bilan_suivi({}, AUJ)["taux_reponse"], None)

print("\n── C. journaux du pipeline ──")
with tempfile.TemporaryDirectory() as t:
    t = Path(t)
    (t / "pipeline_2026-10-10_1200.log").write_text(
        "Merge : +8 nouvelles, 0 enrichies\nMerge [DRY] : +3 nouvelles\n", encoding="utf-8"
    )
    (t / "pipeline_2026-10-11_0900.log").write_text("Merge : +2 nouvelles\n", encoding="utf-8")
    (t / "pipeline_2026-10-11_1800.log").write_text("Merge : +5 nouvelles\n", encoding="utf-8")
    (t / "pipeline_2026-10-01_1200.log").write_text("Merge : +99 nouvelles\n", encoding="utf-8")
    (t / "scan_manuel_2026-10-11_1605.log").write_text("Merge : +50 nouvelles\n", encoding="utf-8")
    p = M.bilan_pipeline(t, AUJ)
    check("somme des fusions d'un journal", p["par_jour"][date(2026, 10, 10)], 11)
    check("deux runs le même jour additionnés", p["par_jour"][date(2026, 10, 11)], 7)
    check("journal hors période ignoré", date(2026, 10, 1) in p["par_jour"], False)
    check("journal d'un autre programme ignoré", p["total"], 18)
    check("jours sans run signalés", len(p["jours_sans_run"]), 5)
    check("aujourd'hui sans run signalé", date(2026, 10, 12) in p["jours_sans_run"], True)

print("\n── D. rapport ──")
r = M.rapport(b, p, AUJ)
check("les relances apparaissent", "B — Chargé (22 j)" in r, True)
check("l'absence de date est dite", "1 candidature(s) sans date" in r, True)
check("les jours sans pipeline sont dits", "Pas de journal du pipeline" in r, True)

print(f"\n=== BILAN : {PASS} ✅  /  {FAIL} ❌  ({PASS}/{PASS + FAIL}) ===")
sys.exit(1 if FAIL else 0)
