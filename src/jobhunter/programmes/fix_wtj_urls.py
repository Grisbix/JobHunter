#!/usr/bin/env python3
"""fix_wtj_urls.py — Répare les liens Welcome to the Jungle qui affichent une
erreur 404 DANS la page (route SPA invalide). Le scraper avait fabriqué des URLs
`/fr/jobs/search?q=...&refinementList[offices][]=NomEntreprise` — route inexistante
côté WTJ → 404. On les réécrit vers la vraie recherche : `/fr/jobs?query=<mots>`.

Garde les pages valides `/fr/companies/<slug>`. Réécrit `/jobs/search` et `/pages/emploi-*`.

Run : python JobHunter.pyw fix_wtj_urls            # applique
      python JobHunter.pyw fix_wtj_urls --dry      # montre sans écrire"""

import argparse
import importlib
import re
import sys
from urllib.parse import quote, urlparse

from jobhunter import racine as _racine

sys.stdout.reconfigure(encoding="utf-8")

HERE = _racine.scripts()
QUEUE = HERE / "apply_queue.json"
BASE = "https://www.welcometothejungle.com/fr/jobs?query="


def _kw(entreprise, poste):
    """Mots-clés de recherche : entreprise + poste nettoyé (sans H/F, parenthèses)."""
    poste = re.sub(r"\(.*?\)|h/f|f/h|\bh\b|\bf/h\b|—.*", " ", (poste or ""), flags=re.I)
    poste = re.sub(r"\s+", " ", poste).strip()
    q = f"{entreprise} {poste}".strip()
    return quote(q[:80])


def needs_fix(url):
    if "welcometothejungle.com" not in url:
        return False
    p = urlparse(url).path.lower()
    if "/companies/" in p:  # page entreprise WTJ = valide
        return False
    return "/jobs/search" in url or "/pages/" in p or url.rstrip("-").endswith("emploi")


def main():
    # Verrou inter-processus : ce programme reecrit la queue ENTIERE. Si un
    # autre le fait en meme temps (tache planifiee vs app), le dernier qui
    # ecrit efface le travail de l'autre.
    if not importlib.import_module("jobhunter.programmes.jutil").garder(QUEUE):
        return 3
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    q = importlib.import_module("jobhunter.stockage.file").charger(QUEUE, descriptions=False)
    n = 0
    for x in q:
        u = x.get("url") or ""
        if needs_fix(u):
            new = BASE + _kw(x.get("entreprise", ""), x.get("poste", ""))
            print(f"  {x.get('entreprise', '')[:24]:24} {u[:60]}\n     → {new}")
            if not a.dry:
                x["url"] = new
                x["url_type"] = "RECHERCHE"
                x["link_status"] = "OK"  # à revalider via recheck_dead
            n += 1
    if not a.dry:
        importlib.import_module("jobhunter.programmes.jutil").jwrite(QUEUE, q)
    print(f"\n=== {'[DRY] ' if a.dry else ''}{n} URL WTJ réparées → recherche valide ===")


if __name__ == "__main__":
    sys.exit(main())
