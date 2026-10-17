#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""offres_depuis_site.py — Retrouve l'annonce sur le site de l'EMPLOYEUR pour les
offres connues seulement par LinkedIn.

POURQUOI. 62 % de la file pointe sur LinkedIn. La promotion d'URL de
`job_sources` ne se declenche que si un autre canal retrouve l'annonce — or il
n'existe presque aucun doublon inter-sites. Il faut donc aller la chercher.

`resolve_offer_links.py` fait ce travail mais part de l'URL EXISTANTE, et ne
retient que les liens qui ressemblent deja a une page d'accueil : une URL
LinkedIn (`/jobs/view/slug-123456`) a des segments et des chiffres, elle n'etait
jamais ciblee. Ici on part du site de l'entreprise, lu dans homepages.json
(alimente par homepages_linkedin.py, etape 1).

Toute la logique d'acceptation est REUTILISEE de resolve_offer_links : meme
societe ou ATS connu, identifiant d'offre dans l'URL, deux mots du titre presents.
La recopier aurait produit deux regles qui divergent.

L'URL LinkedIn est conservee dans `url_linkedin` : rien n'est perdu, et le suivi
des candidatures n'est pas concerne (sa cle est « entreprise|poste », pas l'URL).

CAPTCHA : jamais contourne. Une page protegee est notee et sautee.

Run :
  python offres_depuis_site.py --dry --fit 8
  python offres_depuis_site.py --fit 8 --limit 50
"""

import sys
import re
import json
import argparse
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

import queue_io
from job_sources import rang_source
from resolve_offer_links import accepte, specificite, PROFIL

HOMEPAGES = HERE / "homepages.json"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--fit", type=int, default=8)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--headed", action="store_true")
    ap.add_argument(
        "--une-par-entreprise",
        action="store_true",
        help="une seule offre par societe : echantillon representatif",
    )
    ap.add_argument("--every", type=int, default=10, help="point de reprise tous les N")
    a = ap.parse_args()

    try:
        homes = json.loads(HOMEPAGES.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        homes = {}

    q = queue_io.charger(descriptions=False)
    cibles = [
        o
        for o in q
        if rang_source(o.get("url")) == 0
        and (o.get("fit") or 0) >= a.fit
        and (o.get("entreprise") or "").strip() in homes
    ]
    if a.une_par_entreprise:
        # Un echantillon domine par une seule societe ne mesure que celle-la :
        # 7 des 12 premieres cibles etaient Deloitte.
        vues, uniq = set(), []
        for o in cibles:
            e = (o.get("entreprise") or "").strip()
            if e not in vues:
                vues.add(e)
                uniq.append(o)
        cibles = uniq
    if a.limit:
        cibles = cibles[: a.limit]

    total_li = sum(1 for o in q if rang_source(o.get("url")) == 0 and (o.get("fit") or 0) >= a.fit)
    print(
        f"{total_li} offre(s) LinkedIn a fit >= {a.fit} — "
        f"{len(cibles)} avec un site d'entreprise connu"
    )
    if a.dry or not cibles:
        for o in cibles[:10]:
            print(f"  {o['entreprise'][:26]:28} {homes[o['entreprise'].strip()][:44]}")
        if a.dry:
            print("[DRY] rien n'a ete ecrit.")
        return 0

    from web_nav import get_sync_playwright, find_offer, dismiss_cookies, analyze, goto_careers

    sp, eng = get_sync_playwright("auto")
    PROFIL.mkdir(parents=True, exist_ok=True)
    resolus = captcha = echecs = 0

    with sp() as p:

        def lance():
            c = p.chromium.launch_persistent_context(
                user_data_dir=str(PROFIL),
                channel="chrome",
                headless=not a.headed,
                args=["--no-first-run", "--no-default-browser-check"],
                no_viewport=True,
                timeout=90000,
            )
            c.set_default_timeout(12000)
            c.set_default_navigation_timeout(25000)
            return c, (c.pages[0] if c.pages else c.new_page())

        ctx, page = lance()
        try:
            for i, o in enumerate(cibles, 1):
                ent = str(o.get("entreprise") or "").strip()
                role = str(o.get("poste") or "")
                depart = homes[ent]
                note = ""
                try:
                    page.goto(depart, timeout=25000, wait_until="domcontentloaded")
                    dismiss_cookies(page)
                    x = analyze(page)
                    if x.get("captcha") or x.get("blocked"):
                        captcha += 1
                        print(f"  [{i}/{len(cibles)}] BLOQUE   {ent[:26]:28}{depart[:40]}")
                        continue
                    goto_careers(page)  # on part d'une home : viser les carrieres
                    dismiss_cookies(page)
                    find_offer(page, role_hint=role, max_tries=1)
                    arrivee = page.url
                except Exception as e:
                    arrivee, note = depart, type(e).__name__
                    if "Closed" in note or "crash" in str(e).lower():
                        try:
                            ctx.close()
                        except Exception:
                            pass
                        try:
                            ctx, page = lance()
                            note += " (navigateur relance)"
                        except Exception:
                            print("  ✖ relance impossible — arret")
                            break

                ok, pourquoi = False, note or "aucune offre atteinte"
                if arrivee != depart and specificite(arrivee) > specificite(depart):
                    try:
                        texte = page.inner_text("body")[:20000]
                    except Exception:
                        texte = ""
                    ok, pourquoi = accepte(depart, arrivee, role, texte)

                # LE LIEN RETENU DOIT ETRE VIVANT, ET PARLER DU BON POSTE.
                # Mesure faite sur les 6 premieres resolutions : Sopra Steria
                # rendait un 404, et Theodo pointait sur « Consultant SDLC & IA
                # Agentique » alors que l'offre est « CTO Data & AI ». Deux sur
                # six etaient donc FAUSSES. Remplacer un lien LinkedIn qui
                # fonctionne par un lien mort ou trompeur est pire que ne rien
                # faire — l'offre disparait du radar sans que rien ne l'annonce.
                if ok:
                    titre_page = ""
                    try:
                        rep = page.goto(arrivee, timeout=20000, wait_until="domcontentloaded")
                        if rep is not None and rep.status >= 400:
                            ok, pourquoi = False, f"lien mort (http {rep.status})"
                        else:
                            titre_page = (page.title() or "").lower()
                    except Exception:
                        ok, pourquoi = False, "lien injoignable"
                    if ok and titre_page:
                        mots = [m for m in re.findall(r"[a-zA-ZÀ-ÿ]{4,}", role.lower())][:6]
                        if mots and sum(1 for m in mots if m in titre_page) == 0:
                            ok, pourquoi = False, "le titre de la page ne parle pas du poste"

                if ok:
                    resolus += 1
                    print(f"  [{i}/{len(cibles)}] RESOLU   {ent[:26]:28}{arrivee[:58]}")
                    o.setdefault("url_linkedin", o.get("url"))
                    o["url"] = arrivee
                    o["url_type"] = "OFFRE_DIRECTE"
                    o["canal"] = "auto"
                    o["site_kind"] = "entreprise"
                # PAS de repli « portail carrieres » ici. resolve_offer_links
                # l'accepte parce qu'il remplace une URL DEJA generique — un nom
                # de societe sans annonce. Ici on remplacerait un lien LinkedIn
                # qui mene a l'annonce PRECISE par un tableau de resultats : ce
                # serait une regression, pas une amelioration.
                else:
                    echecs += 1
                    print(f"  [{i}/{len(cibles)}] refuse   {ent[:26]:28}{pourquoi[:44]}")

                if a.every and i % a.every == 0:
                    _ecrire(q)
                    print(f"      … point de reprise ({resolus} resolus)")
        finally:
            try:
                ctx.close()
            except Exception:
                pass

    _ecrire(q)
    print(
        f"\n{resolus} annonce(s) directe(s) · {echecs} sans resultat · "
        f"{captcha} page(s) protegee(s)"
    )
    return 0


def _ecrire(q):
    """Ecriture sous verrou. Les points de reprise comptent : une session de
    navigation dure des heures et peut etre interrompue."""
    try:
        with queue_io.transaction(descriptions=False) as fichier:
            par_cle = {queue_io.oid(o): o for o in q}
            for o in fichier:
                maj = par_cle.get(queue_io.oid(o))
                if maj and maj.get("url") != o.get("url"):
                    for k in ("url", "url_type", "canal", "site_kind", "url_linkedin"):
                        if k in maj:
                            o[k] = maj[k]
    except queue_io.VerrouIndisponible as e:
        print(f"  ! {e} — modifications gardees en memoire, reessai au prochain point")


if __name__ == "__main__":
    sys.exit(main())
