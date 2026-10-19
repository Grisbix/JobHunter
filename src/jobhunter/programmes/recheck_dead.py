#!/usr/bin/env python3
"""recheck_dead.py — Détecte les SOFT-404 rendus en JS (page HTTP 200 mais corps
« 404 / offre pourvue / expirée / no longer accepting ») que le check statique
(link_check via requests) rate — anti-bot ou contenu React.

Ouvre chaque URL dans un vrai navigateur, lance le détecteur `dead` de web_nav
(analyze → kind=='dead'), et écrit link_status dans apply_queue.json :
  - MORT     : navigation impossible (goto échoue)
  - EXPIREE  : page vivante mais message offre morte / 0 offre
  - OK       : offre bien présente

Run :
  python JobHunter.pyw recheck_dead --status ANTI-BOT,OK --limit 60      # cible les suspects
  python JobHunter.pyw recheck_dead --canal auto                          # offres auto
  python JobHunter.pyw recheck_dead --dry                                 # montre sans écrire
"""

import argparse
import datetime
import importlib
import re
import sys
import time

from jobhunter import racine as _racine
from jobhunter.navigation.navigateur import lancer as _lancer

# line_buffering : sinon rien ne sort quand la sortie est redirigée (run en fond = aveugle)
sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)  # type: ignore[union-attr]  # console : TextIOWrapper

HERE = _racine.scripts()
QUEUE = HERE / "apply_queue.json"
UA_H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


# ── Voie RAPIDE LinkedIn : l'API guest dit si l'offre est fermee ──────────────
# En navigateur, une offre LinkedIn renvoie kind=login (mur de connexion) et
# passe donc pour vivante, quoi qu'il arrive : le recheck ne prouvait RIEN sur
# LinkedIn, qui represente pourtant l'essentiel de la queue. L'API guest, elle,
# ajoute la classe CSS `closed-job` + « No longer accepting applications » quand
# le poste est ferme. Verifie sur des temoins : 7 offres/8 declarees mortes la
# veille par le navigateur portent le marqueur, aucune des vivantes.
# Bonus : ~0,3 s par lien en httpx contre ~7 s en navigateur.
# Deux formats coexistent : /jobs/view/<id> (liens colles a la main) et
# /jobs/view/<intitule>-at-<societe>-<id> (liens de la recherche guest, soit
# la quasi-totalite de la queue). Ne matcher que le premier ratait 1001
# offres LinkedIn sur 1001.
_LI_ID_RX = re.compile(r"/jobs/view/(?:[^/?#]*?-)?(\d{6,})(?:[/?#]|$)")
_LI_CLOSED_RX = re.compile(r"closed-job|no longer accepting applications", re.I)


def linkedin_fast(url):
    """(link_status, note) pour une URL d'offre LinkedIn, sans navigateur.
    Retourne None si l'URL n'est pas une offre LinkedIn ou si le check echoue,
    pour laisser la main a la voie navigateur."""
    m = _LI_ID_RX.search(url or "")
    if not m:
        return None
    import httpx

    try:
        r = httpx.get(
            f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{m.group(1)}",
            timeout=15,
            headers=UA_H,
            follow_redirects=True,
        )
    except Exception:
        return None
    if r.status_code == 404:
        return "EXPIREE", "guest 404 (offre retiree)"
    if r.status_code != 200 or len(r.text) < 400:
        return None  # indetermine -> navigateur
    if _LI_CLOSED_RX.search(r.text):
        return "EXPIREE", "guest: no longer accepting"
    return "OK", "guest: offre ouverte"


def classify(page, url):
    """Retour (link_status, note). Utilise robust_goto + analyze (détecteur dead partagé)."""
    from jobhunter.navigation import analyze, dismiss_cookies, robust_goto

    g = robust_goto(page, url, tries=2)
    if not g.get("ok"):
        return "MORT", g.get("note", "goto_fail")
    try:
        dismiss_cookies(page)
    except Exception:
        pass
    time.sleep(1.0)
    a = analyze(page)
    if a.get("captcha") or a.get("blocked"):
        return None, "captcha/blocked (indéterminé)"  # None = ne pas changer
    if a.get("dead") or a.get("kind") == "dead":
        return "EXPIREE", "soft-404 (page morte / 0 offre)"
    return "OK", "vivante (kind=%s)" % a.get("kind", "?")


def main():
    # Verrou inter-processus : ce programme reecrit la queue ENTIERE. Si un
    # autre le fait en meme temps (tache planifiee vs app), le dernier qui
    # ecrit efface le travail de l'autre.
    if not importlib.import_module("jobhunter.programmes.jutil").garder(QUEUE):
        return 3
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--status", default="ANTI-BOT,OK", help="link_status à revérifier (CSV). Déf: ANTI-BOT,OK"
    )
    ap.add_argument("--canal", default=None, choices=["auto", "manuel", "linkedin", "all"])
    ap.add_argument("--limit", type=int, default=80)
    ap.add_argument("--dry", action="store_true")
    ap.add_argument(
        "--no-fast",
        action="store_true",
        help="desactive la voie rapide LinkedIn (tout en navigateur)",
    )
    ap.add_argument(
        "--every", type=int, default=25, help="sauvegarde tous les N liens (checkpoint)"
    )
    ap.add_argument(
        "--fresh-days",
        type=int,
        default=7,
        help="ignore les offres déjà vérifiées depuis moins de N jours (reprise par lots)",
    )
    ap.add_argument(
        "--recycle", type=int, default=40, help="recrée l'onglet tous les N liens (fuite mémoire)"
    )
    a = ap.parse_args()

    q = importlib.import_module("jobhunter.stockage.file").charger(QUEUE, descriptions=False)
    want = {s.strip().upper() for s in a.status.split(",") if s.strip()}
    today = datetime.date.today()
    targets = []
    for x in q:
        if not str(x.get("url") or "").startswith("http"):
            continue
        # reprise : saute ce qui a été vérifié récemment (permet de lancer par lots)
        chk = str(x.get("ls_check") or "")
        if chk and a.fresh_days > 0:
            try:
                if (today - datetime.date.fromisoformat(chk)).days < a.fresh_days:
                    continue
            except Exception:
                pass
        if a.canal == "linkedin":
            if "linkedin.com" not in x["url"]:
                continue
        elif a.canal and a.canal != "all" and x.get("canal") != a.canal:
            continue
        if want and (x.get("link_status") or "OK").upper() not in want:
            continue
        targets.append(x)  # pas de coupe ici : on trie AVANT de plafonner
    if not targets:
        print("Aucune offre à revérifier (filtre trop strict ?).")
        return
    # LinkedIn d'abord : voie rapide httpx, fiable et ~20x plus rapide. Sinon les
    # pages carrières (souvent « indéterminé ») passent devant et un incident
    # navigateur empêche d'atteindre le gros du lot.
    if not a.no_fast:
        targets.sort(key=lambda x: 0 if _LI_ID_RX.search(str(x.get("url") or "")) else 1)
    # Le plafond s'applique APRES le tri : sinon il coupe en tete de queue, ou
    # dominent les pages carrieres, et les offres LinkedIn ne sont jamais atteintes.
    targets = targets[: a.limit]
    print(f"{len(targets)} offre(s) à revérifier en navigateur (status={sorted(want)})…")

    from playwright.sync_api import sync_playwright

    eng = "playwright"
    counts = {}
    with sync_playwright() as p:

        def launch():
            """(ctx, page) neufs. Rappelé si le navigateur meurt en cours de lot."""
            b = _lancer(p.chromium, headless=True)
            pg = b.new_page()
            c = pg.context  # gardé : pg.context est inutilisable après pg.close()
            try:
                from jobhunter.navigation import block_resources

                block_resources(c, images=False)
            except Exception:
                pass
            return c, pg

        ctx, page = launch()
        t0 = time.time()
        dead_run = 0  # échecs consécutifs
        for i, x in enumerate(targets, 1):
            url = x["url"]
            # LinkedIn d'abord : httpx suffit et tranche vraiment (le navigateur
            # bute sur le mur de connexion et repond « vivante » quoi qu'il arrive).
            fast = linkedin_fast(url) if not a.no_fast else None
            if fast:
                new, note = fast
            else:
                try:
                    new, note = classify(page, url)
                except Exception as e:  # un lien qui explose ne tue pas le lot
                    new, note = None, f"erreur: {type(e).__name__}"
                    # navigateur mort -> le relancer, sinon tout le reste défile en erreur
                    if "TargetClosed" in type(e).__name__ or "Closed" in str(e):
                        try:
                            ctx.close()
                        except Exception:
                            pass
                        try:
                            ctx, page = launch()
                            note += " (navigateur relancé)"
                        except Exception as e2:
                            print(f"  ✖ relance navigateur impossible : {e2}")
                            break
            old = x.get("link_status")
            # ls_check SEULEMENT si le check a vraiment abouti : sinon la reprise
            # sauterait des offres jamais vérifiées.
            if not a.dry and new:
                x["ls_check"] = today.isoformat()
            # Garde-fou : ne compte que les ECHECS DURS (exception, navigateur mort).
            # Un « captcha/blocked » est un resultat INDETERMINE normal sur les pages
            # carrieres — le compter arretait le lot des la 15e page protegee, avant
            # meme d'atteindre les offres LinkedIn.
            dead_run = dead_run + 1 if str(note).startswith("erreur:") else 0
            if dead_run >= 15:
                print(f"  ✖ {dead_run} échecs d'affilée — arrêt (relance plus tard, reprise auto)")
                break
            if new and new != old:
                counts[f"{old}→{new}"] = counts.get(f"{old}→{new}", 0) + 1
                if not a.dry:
                    x["link_status"] = new
                flag = "✏️" if not a.dry else "·"
                print(
                    f"  [{i}/{len(targets)}] {flag} {new:8} {x.get('entreprise', '')[:28]:28} — {note}"
                )
            else:
                print(
                    f"  [{i}/{len(targets)}] = {old or 'OK':8} {x.get('entreprise', '')[:28]:28} — {note}"
                )
            # checkpoint : ne jamais perdre le lot si ça plante/on coupe
            if not a.dry and a.every > 0 and i % a.every == 0:
                importlib.import_module("jobhunter.programmes.jutil").jwrite(QUEUE, q)
                rate = (time.time() - t0) / i
                print(
                    f"  ── checkpoint {i}/{len(targets)} — {rate:.1f}s/lien, "
                    f"reste ~{rate * (len(targets) - i) / 60:.0f} min"
                )
            # onglet recyclé : sinon la mémoire enfle (2,7 Go observés sur un lot de 1452)
            if a.recycle > 0 and i % a.recycle == 0:
                try:
                    # ORDRE CRITIQUE : ouvrir la nouvelle page AVANT de fermer l'ancienne.
                    # Fermer la dernière page du contexte arrête le navigateur (TargetClosedError).
                    old_page = page
                    page = ctx.new_page()
                    old_page.close()
                except Exception:
                    pass
        try:
            ctx.close()
        except Exception:
            pass

    if not a.dry:
        importlib.import_module("jobhunter.programmes.jutil").jwrite(QUEUE, q)
    print(f"\n=== {'[DRY] ' if a.dry else ''}changements: {counts or 'aucun'} ===")


if __name__ == "__main__":
    sys.exit(main())
