#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_relances.py — les brouillons de la semaine sont prêts, rien n'est envoyé.

La tâche Windows `Relances` (lundi) lance `relances.py --brouillons`. Ces cas
vérifient, sans réseau ni fichier réel : un brouillon par relance due, le bon
modèle (J+7 la première fois, J+10 après une relance), aucun brouillon retouché
à la main n'est écrasé, et le bilan dit clairement que rien n'est envoyé.

Run : python test_relances.py
"""
import _profil_test  # noqa: F401  — les tests tournent sur le profil d'exemple
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import relances as R

PASS = FAIL = 0


def check(nom, obtenu, attendu):
    global PASS, FAIL
    if obtenu == attendu:
        PASS += 1
        print(f"  ✅ {nom}")
    else:
        FAIL += 1
        print(f"  ❌ {nom}\n       obtenu {obtenu!r}, attendu {attendu!r}")


A = {"entreprise": "Amundi", "poste": "Analyste ESG"}
B = {"entreprise": "Covéa Finance", "poste": "Analyste PAI"}
lst = [(A, "postulé", "2026-09-20", 18), (B, "relancé", "2026-09-27", 11)]

print("\n── A. brouillons écrits ──")
with tempfile.TemporaryDirectory() as t:
    bilan = R.preparer_brouillons(lst, dossier=t)
    fa, fb = R.chemin_brouillon(A, 7, t), R.chemin_brouillon(B, 10, t)
    check("première relance : modèle J+7", fa.exists(), True)
    check("déjà relancée : modèle J+10", fb.exists(), True)
    check("pas de J+7 pour une candidature déjà relancée", R.chemin_brouillon(B, 7, t).exists(), False)
    check("le brouillon nomme l'entreprise et le poste",
          "Analyste ESG chez Amundi" in fa.read_text(encoding="utf-8"), True)
    check("J+10 = dernière relance", "dernière relance" in fb.read_text(encoding="utf-8"), True)

    print("\n── B. un brouillon retouché n'est pas écrasé ──")
    fa.write_text("version retouchée", encoding="utf-8")
    bilan2 = R.preparer_brouillons(lst, dossier=t)
    check("retouche conservée", fa.read_text(encoding="utf-8"), "version retouchée")
    check("bilan : déjà prêt", "déjà prêt" in bilan2, True)

print("\n── C. bilan ──")
check("dit que rien n'est envoyé", "rien n'est envoyé" in bilan, True)
check("compte les relances", "**2 candidature(s)**" in bilan, True)
check("donne la commande de marquage", "--mark" in bilan, True)
check("liste vide : message clair", "Rien à relancer" in R.preparer_brouillons([], dossier="."), True)

print(f"\n=== BILAN : {PASS} ✅  /  {FAIL} ❌  ({PASS}/{PASS + FAIL}) ===")
sys.exit(1 if FAIL else 0)
