#!/usr/bin/env python3
"""test_liens.py — Un lien de remplacement doit mener a L'ANNONCE, pas ailleurs.

Cas reels rencontres en production. Le plus couteux :
`https://www.deloitte.com/fr/fr/careers/content/job/results.htm` — une page de
RESULTATS DE RECHERCHE — a ete acceptee comme annonce et a remplace un lien
LinkedIn qui, lui, menait a l'offre precise. Deux trous a la fois :

  - RX_RECHERCHE exigeait que « results » soit suivi de « / » ou de la fin de
    chaine ; l'extension « .htm » lui echappait ;
  - RX_OFFRE acceptait « /job/<8 caracteres ou plus> », et « results.htm » en
    fait 11.

Run : python test_liens.py
"""

import _profil_test  # noqa: F401  — les tests tournent sur le profil d'exemple

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from resolve_offer_links import RX_OFFRE, RX_RECHERCHE, accepte, specificite

PASS = FAIL = 0


def check(nom, obtenu, attendu):
    global PASS, FAIL
    if obtenu == attendu:
        PASS += 1
        print(f"  ✅ {nom}")
    else:
        FAIL += 1
        print(f"  ❌ {nom}\n       obtenu {obtenu!r}, attendu {attendu!r}")


def verdict(url):
    """OFFRE seulement si le lien porte un identifiant ET n'est pas une recherche."""
    return "REJET" if (RX_RECHERCHE.search(url) or not RX_OFFRE.search(url)) else "OFFRE"


print("\n── A. pages de résultats / recherche : rejetées ──")
for u in [
    "https://www.deloitte.com/fr/fr/careers/content/job/results.htm",  # le cas reel
    "https://www.deloitte.com/fr/fr/careers/content/job/results",
    "https://x.com/jobs/search",
    "https://x.com/carriere/recherche/",
    "https://x.com/emploi/listing.html",
    "https://samse.fr/catalogsearch/result/?q=analyste",
    "https://effektiv.fr/?search_keyword=esg",
    "https://x.com/jobs?query=esg",
]:
    check(u[:62], verdict(u), "REJET")

print("\n── B. vraies annonces : acceptées ──")
for u in [
    "https://x.com/jobs/analyste-esg-h-f-12345",
    "https://x.com/offres/consultant-junior-esg-2026",
    "https://boards.greenhouse.io/sweep/jobs/4567890",
    "https://x.com/job/12345678",
    "https://jobs.lever.co/agicap/97f57bd6-c156-42cd-b67a-f770ed9a1b2c",
    "https://jobs.ashbyhq.com/alan/118f5ad8-5db5-48ec-940e-1a880b3c4d5e",
    "https://tikehaucapital.recruitee.com/o/alternant-esg-immobilier-durable",
]:
    check(u[:62], verdict(u), "OFFRE")

print("\n── C. un slug sans chiffre ni tiret n'est pas un identifiant ──")
check("/jobs/candidature (mot simple)", verdict("https://x.com/jobs/candidature"), "REJET")
check("/offres/spontanee", verdict("https://x.com/offres/spontanee"), "REJET")

print("\n── D. accepte() : garde-fous de fond ──")
ok, why = accepte(
    "https://axa-im.com",
    "https://group.bnpparibas/jobs/analyste-esg-123",
    "Analyste ESG",
    "analyste esg",
)
check("saut vers une AUTRE societe refusé", ok, False)
ok, why = accepte(
    "https://x.com",
    "https://x.com/jobs/analyste-esg-h-f-9912",
    "Analyste ESG",
    "Analyste ESG chez X",
)
check("même société + titre présent accepté", ok, True)
ok, why = accepte(
    "https://x.com",
    "https://x.com/jobs/comptable-paie-4471",
    "Analyste ESG Climat",
    "Comptable paie",
)
check("autre offre que celle attendue refusée", ok, False)
ok, why = accepte(
    "https://x.com", "https://boards.greenhouse.io/x/jobs/771122", "Analyste ESG", "Analyste ESG"
)
check("ATS connu accepté malgré le changement de domaine", ok, True)

print("\n── E. spécificité ──")
check(
    "une annonce est plus spécifique qu'une home",
    specificite("https://x.com/jobs/analyste-esg-1234") > specificite("https://x.com"),
    True,
)

print(f"\n=== BILAN : {PASS} ✅  /  {FAIL} ❌  ({PASS}/{PASS + FAIL}) ===")
if __name__ == "__main__":
    sys.exit(1 if FAIL else 0)
