#!/usr/bin/env python3
"""homepages_linkedin.py — Trouve le site des entreprises dont l'offre n'est
connue que par LinkedIn.

POURQUOI. 62 % de la file pointe sur LinkedIn. La promotion d'URL
(job_sources.rang_source) ne se declenche que si un AUTRE canal retrouve
l'annonce — or il n'existe presque aucun doublon inter-sites. Pour aller
chercher l'annonce chez l'employeur, il faut d'abord savoir ou il habite.

`enrich_homepages.py` fait ce travail mais ne cible que les offres SANS URL.
Celles-ci en ont une (LinkedIn), donc il les ignorait.

Alimente homepages.json, que consomme ensuite offres_depuis_site.py (etape 2).

Run :
  python JobHunter.pyw homepages_linkedin --dry            # compte, n'ecrit rien
  python JobHunter.pyw homepages_linkedin --fit 8          # entreprises des offres fit >= 8
  python JobHunter.pyw homepages_linkedin --fit 0          # toutes
"""

import argparse
import concurrent.futures as cf
import json
import sys

from jobhunter import racine as _racine

HERE = _racine.scripts()

sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

from jobhunter.programmes import enrich_homepages as E
from jobhunter.sources import rang_source
from jobhunter.stockage import file as queue_io

CACHE = HERE / "homepages.json"

# Pages qui repondent 200 mais ne sont PAS le site de l'entreprise : controles
# anti-bot, parkings de domaine, raccourcisseurs. « Manutan » renvoyait ainsi
# validate.perfdrive.com — accepter ca polluerait le cache d'URL inutilisables.
REJET = (
    "perfdrive.com",
    "captcha",
    "cloudflare",
    "datadome",
    "incapsula",
    "sucuri",
    "distil",
    "bot-check",
    "godaddy.com",
    "sedoparking",
    "afternic.com",
    "bit.ly",
    "tinyurl",
    "linkedin.com",
    "facebook.com",
)


def utilisable(url):
    u = (url or "").lower()
    return bool(u.startswith("http")) and not any(r in u for r in REJET)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    ap.add_argument(
        "--fit",
        type=int,
        default=8,
        help="ne traiter que les entreprises ayant une offre a ce fit ou plus",
    )
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()

    q = queue_io.charger(descriptions=False)
    ents = sorted(
        {
            (o.get("entreprise") or "").strip()
            for o in q
            if rang_source(o.get("url")) == 0
            and (o.get("fit") or 0) >= a.fit
            and (o.get("entreprise") or "").strip()
        }
    )

    try:
        cache = json.loads(CACHE.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        cache = {}
    a_faire = [e for e in ents if e not in cache]
    if a.limit:
        a_faire = a_faire[: a.limit]
    print(
        f"{len(ents)} entreprise(s) LinkedIn a fit >= {a.fit} — "
        f"{len(ents) - len(a_faire)} deja connues, {len(a_faire)} a chercher"
    )
    if a.dry or not a_faire:
        return 0

    def _ecrire():
        CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")

    trouve = rejete = 0
    with cf.ThreadPoolExecutor(max_workers=a.workers) as ex:
        for n, (nom, url) in enumerate(ex.map(E.resolve, a_faire), 1):
            if utilisable(url):
                cache[nom] = url
                trouve += 1
            elif url:
                rejete += 1
                print(f"  ~ {nom[:30]:32} rejete : {str(url)[:50]}")
            # Sauvegarde INCREMENTALE. N'ecrire qu'a la fin faisait tout perdre
            # des qu'un run etait interrompu : 232 recherches reseau jetees.
            if n % 25 == 0:
                _ecrire()
                print(f"  … {n}/{len(a_faire)}  ({trouve} trouves)")

    _ecrire()
    print(
        f"\n{trouve} site(s) trouve(s), {rejete} rejete(s) (page anti-bot ou parking), "
        f"{len(a_faire) - trouve - rejete} introuvable(s)"
    )
    print(f"homepages.json : {len(cache)} entrees")
    return 0


if __name__ == "__main__":
    sys.exit(main())
