#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_titres.py — Nettoyage de l'intitulé de poste (tailor_application.titre_poste).

Cas tirés des VRAIS titres trouvés dans apply_queue.json, pas inventés.

Garde aussi contre un piège rencontré trois fois : un « \\b » mangé par un heredoc
devient le caractère backspace \\x08 ; le motif ne matche alors plus jamais, sans
lever la moindre erreur. On vérifie donc les motifs eux-mêmes, pas seulement leurs effets.

Run : python test_titres.py
"""

import _profil_test  # noqa: F401  — les tests tournent sur le profil d'exemple
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import tailor_application as T

PASS = FAIL = 0


def check(nom, cond, got=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✅ {nom}")
    else:
        FAIL += 1
        print(f"  ❌ {nom}  (obtenu : {got!r})")


def objet(role):
    t = T.titre_poste(role)
    return f"Candidature au poste {T._de(t)}" if t else "Candidature spontanée"


print("\n── A. motifs non corrompus ──")
for n in [x for x in dir(T) if x.startswith("RX_")]:
    rx = getattr(T, n)
    if hasattr(rx, "pattern"):
        check(f"{n} sans backspace littéral", "\x08" not in rx.pattern, rx.pattern[:40])

print("\n── B. mention de genre retirée ──")
for src in [
    "Analyste ESG (H/F)",
    "ACTUAIRE (F/H)",
    "Actuaire (h/f)",
    "Junior Analyste ESG Mode - (H/F/X)",
    "Consultant junior H/F",
]:
    r = T.titre_poste(src)
    check(f"{src!r} → sans H/F", not T.RX_GENRE.search(r), r)

print("\n── C. type de contrat retiré ──")
for src in [
    "Analyste Quantitatif ESG (H/F) CDI",
    "Adjoint Risque Clients (F/H) - CDD",
    "CDD - Junior Analyste ESG Mode",
    "Intern Analyst - 6 months - Product Specialist",
]:
    r = T.titre_poste(src)
    check(f"{src!r} → sans contrat", not T.RX_CONTRAT.search(r), r)

print("\n── D. traits d'union INTERNES préservés ──")
check(
    "LCB-FT reste soudé",
    T.titre_poste("Analyste LCB-FT CDD 3 mois H/F") == "Analyste LCB-FT",
    T.titre_poste("Analyste LCB-FT CDD 3 mois H/F"),
)
check(
    "H2-Power reste soudé",
    "H2-Power" in T.titre_poste("Junior Finance Controller - OPmobility H2-Power"),
    T.titre_poste("Junior Finance Controller - OPmobility H2-Power"),
)

print("\n── E. élision ──")
check(
    "voyelle → d'",
    objet("Analyste ESG") == "Candidature au poste d'Analyste ESG",
    objet("Analyste ESG"),
)
check(
    "consonne → de",
    objet("Chargé de mission ESG").startswith("Candidature au poste de Chargé"),
    objet("Chargé de mission ESG"),
)
check("h aspiré → de (pas d')", T._de("Hollande") == "de Hollande", T._de("Hollande"))
check("y → de (pas d')", T._de("Yves Rocher") == "de Yves Rocher", T._de("Yves Rocher"))

print("\n── F. titre inutilisable → formule neutre ──")
for src in ["Mérignac : 2 rue du Golf 33700 MÉRIGNAC", "", "   ", "H/F"]:
    check(f"{src!r} → candidature spontanée", objet(src) == "Candidature spontanée", objet(src))

print("\n── G. longueur bornée, coupe sur un mot entier ──")
long_ = (
    "2027 Corporate & Investment Bank - Global Investment Banking Analyst Program "
    "- Off-Cycle Internship - Zurich"
)
r = T.titre_poste(long_)
# Borne portee de 70 a 80 : « Consultant, Climate Change and Sustainability
# Services Financial Services - Geneva » etait coupe a « … Services
# Financial », qui inverse le nom du departement et ne veut plus rien dire.
check("≤ 80 caractères", len(r) <= 80, len(r))
check("ne finit pas au milieu d'un mot", long_.startswith(r) or r in long_.replace("  ", " "), r)
check("pas de ponctuation orpheline en fin", not r.endswith((" -", ",", ";", ":", "|", "-")), r)

print("\n── H. idempotence : re-nettoyer ne doit RIEN changer ──")
# Piège réel : titre_poste normalise « DAF – Finance » (tiret long) en
# « DAF - Finance ». Si RX_GENRE accepte des lettres NON isolées, la passe
# suivante y voit « F - F » et produit « DA inance ». refresh_letters.py étant
# conçu pour être relancé, la corruption se serait propagée à chaque exécution.
for src in [
    "Bras droit DAF – Finance & Processus F/H - GAYA",
    "Directeur DAF - Finance",
    "Analyste ESG (H/F)",
    "Analyste - M&A - F/H",
    "Responsable RH - Formation F/H",
]:
    une = T.titre_poste(src)
    check(f"{src[:44]} stable", T.titre_poste(une), une)
check(
    "« DAF - Finance » survit intact",
    T.titre_poste("Bras droit DAF – Finance & Processus F/H - GAYA"),
    "Bras droit DAF - Finance & Processus - GAYA",
)

print("\n── I. mentions de genre à trois lettres ──")
check(
    "F/W retiré",
    T.titre_poste("Market Risk Analyst Counterparty F/W"),
    "Market Risk Analyst Counterparty",
)
check("F/M/X retiré", T.titre_poste("Analyst F/M/X"), "Analyst")

print("\n── J. référence d'annonce retirée ──")
r = T.titre_poste("Administrative Officer (P-2), TA, 364 days, #00137324, Education Cannot Wait")
check("le #id disparaît", "#" not in r, r)
check("pas de virgules doublées", ", ," not in r and ",," not in r, r)

print(f"\n=== BILAN : {PASS} ✅  /  {FAIL} ❌  ({PASS}/{PASS + FAIL}) ===")
# sys.exit au niveau module TERMINE l'interpreteur de qui importe ce
# fichier. Sous garde, il ne s'applique qu'a une execution directe.
if __name__ == "__main__":
    sys.exit(1 if FAIL else 0)
