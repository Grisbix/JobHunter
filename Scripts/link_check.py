# -*- coding: utf-8 -*-
"""Vérification d'URLs d'offres (live/dead/soft-404). Module : quick_check/batch_check (queue_tools mark).
Détecte les SOFT-404 : page renvoie HTTP 200 mais affiche 'offre expirée / poste pourvu / page introuvable'."""
import requests, concurrent.futures as cf, collections, re, sys
from urllib.parse import urlparse
sys.stdout.reconfigure(encoding="utf-8")

# Phrases "offre morte" malgré HTTP 200 (FR/EN/DE) — soft 404 / expirée / pourvue
SOFT_DEAD_RX = re.compile(
    r"(page (introuvable|non trouv[eé]e|indisponible|n'existe (plus|pas))"
    r"|erreur 404|404 (not found|error|page)|not found"
    r"|cette (offre|annonce) (n'existe plus|a expir[eé]|n'est plus (disponible|active))"
    r"|offre (expir[eé]e|pourvue|clotur[eé]e|termin[eé]e|d[eé]sactiv[eé]e|supprim[eé]e|non disponible)"
    r"|poste (pourvu|d[eé]j[aà] pourvu|non disponible)"
    r"|annonce (expir[eé]e|supprim[eé]e|d[eé]sactiv[eé]e)"
    r"|recrutement (clos|termin[eé]|clotur[eé])"
    r"|(no longer|not) (accepting|available|active)|position (filled|closed|no longer)"
    r"|this (job|position|vacancy|offer) (is|has) (closed|expired|filled|no longer)"
    r"|job (not found|expired|closed|no longer available)|vacancy (closed|expired|filled)"
    r"|offre d'emploi introuvable|aucune offre|oops|page indisponible"
    r"|diese stelle (ist nicht|existiert nicht)|nicht mehr verf[üu]gbar|stellenangebot.*(abgelaufen|nicht gefunden))",
    re.I)

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"}

def is_live(st):
    return isinstance(st, int) and st < 400

def check(u):
    """Retour (url, status, soft) : status HTTP ou nom d'exception ;
    soft = phrase 'offre morte' détectée dans le corps malgré 200, sinon None."""
    try:
        r = requests.get(u, headers=UA, timeout=12, allow_redirects=True)
        soft = None
        if r.status_code < 400:
            body = (r.text or "")[:60000]
            # titre <title> + début du body (là où vivent les messages 404/expiré)
            m = re.search(r"<title[^>]*>(.*?)</title>", body, re.I | re.S)
            title = m.group(1) if m else ""
            scan = (title + " " + re.sub(r"<[^>]+>", " ", body))[:20000]
            hit = SOFT_DEAD_RX.search(scan)
            if hit:
                soft = hit.group(0)[:40]
        return u, r.status_code, soft
    except Exception as e:
        return u, type(e).__name__, None


# ── Intégration pipeline : check rapide d'une URL (HTTP HEAD) ──────────
# Appelable depuis batch_comptes.py / run_pipeline.py avant goto.

def quick_check(url: str, timeout: float = 8.0) -> dict:
    """Vérifie rapidement si une URL semble vivante (HEAD + fallback GET).
    Retour {live: bool, status, soft_dead: str|None, note: str}.
    Ne bloque pas le pipeline si réseau lent (timeout court)."""
    try:
        # HEAD d'abord (léger)
        r = requests.head(url, headers=UA, timeout=timeout, allow_redirects=True)
        if r.status_code >= 500:
            # HEAD peut être refusé — tenter GET
            r = requests.get(url, headers=UA, timeout=timeout, allow_redirects=True)
        status = r.status_code
    except requests.exceptions.Timeout:
        return {"live": False, "status": 0, "soft_dead": None, "note": "timeout"}
    except requests.exceptions.ConnectionError:
        return {"live": False, "status": 0, "soft_dead": None, "note": "connection_error"}
    except Exception as e:
        return {"live": False, "status": 0, "soft_dead": None, "note": type(e).__name__}

    if status >= 500:
        return {"live": False, "status": status, "soft_dead": None, "note": f"HTTP {status}"}
    if status == 404 or status == 410:
        return {"live": False, "status": status, "soft_dead": None, "note": f"HTTP {status}"}
    if status in (429, 403):
        return {"live": True, "status": status, "soft_dead": None, "note": "anti-bot (probablement vivant)"}

    # Soft-404 check sur le body (seulement si 200-299)
    soft = None
    if 200 <= status < 300:
        try:
            body = (r.text or "")[:60000]
            m = re.search(r"<title[^>]*>(.*?)</title>", body, re.I | re.S)
            title = m.group(1) if m else ""
            scan = (title + " " + re.sub(r"<[^>]+>", " ", body))[:20000]
            hit = SOFT_DEAD_RX.search(scan)
            if hit:
                soft = hit.group(0)[:40]
        except Exception:
            pass

    if soft:
        return {"live": False, "status": status, "soft_dead": soft, "note": "soft-404: " + soft}
    return {"live": True, "status": status, "soft_dead": None, "note": "ok"}


def batch_check(urls: list, max_workers: int = 12) -> dict:
    """Vérifie un lot d'URLs en parallèle. Retour {url: result}."""
    import concurrent.futures as cf
    results = {}
    with cf.ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(quick_check, u): u for u in urls}
        for fut in cf.as_completed(futures):
            url = futures[fut]
            try:
                results[url] = fut.result()
            except Exception as e:
                results[url] = {"live": False, "status": 0, "soft_dead": None, "note": str(e)}
    return results


if __name__ == "__main__":
    print("Module (quick_check/batch_check). Utilisé par queue_tools mark.")
