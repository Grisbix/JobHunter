#!/usr/bin/env python3
"""enrich_homepages.py — Trouve l'URL page d'accueil des entreprises SANS URL offre.
Devine le domaine depuis le nom (slug + .com/.fr) et VALIDE par HTTP (200, host cohérent).
Écrit Scripts/homepages.json {entreprise: url}. build_queue l'utilise en fallback
(url_type=HOMEPAGE, canal=auto) → le runner navigue home → goto_careers → offre.

Run: python enrich_homepages.py        (toutes les entreprises sans URL du queue)
     python enrich_homepages.py --force (revalide même celles déjà en cache)
"""

import concurrent.futures as cf
import importlib
import json
import re
import sys
import unicodedata

import requests

from jobhunter import racine as _racine

sys.stdout.reconfigure(encoding="utf-8")

SCRIPTS = _racine.scripts()
QUEUE = SCRIPTS / "apply_queue.json"
CACHE = SCRIPTS / "homepages.json"
UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
}

# tokens juridiques/génériques à retirer du slug
STOP = {
    "sa",
    "sas",
    "sarl",
    "sasu",
    "eurl",
    "gie",
    "group",
    "groupe",
    "holding",
    "solutions",
    "solution",
    "services",
    "service",
    "france",
    "international",
    "the",
    "and",
    "co",
    "compagnie",
    "cie",
    "se",
    "ag",
    "gmbh",
    "ltd",
    "llc",
    "partners",
    "capital",
    "management",
    "asset",
    "investment",
    "investments",
}


def _ascii(s):
    """Volontairement PLUS agressif que jutil.sans_accent : ici on fabrique des
    slugs de nom de domaine, donc tout caractere non-ASCII doit DISPARAITRE, pas
    seulement perdre son accent. Ce n'est pas un doublon a factoriser."""
    return unicodedata.normalize("NFD", s or "").encode("ascii", "ignore").decode()


def slugs(name):
    """Génère des variantes de slug depuis le nom d'entreprise."""
    base = _ascii(name).lower()
    base = re.sub(r"[^a-z0-9 ]", " ", base)
    toks = [t for t in base.split() if t and t not in STOP]
    if not toks:
        toks = [t for t in base.split() if t]
    if not toks:
        return []
    joined = "".join(toks)
    hyph = "-".join(toks)
    first = toks[0]
    out = []
    for s in (joined, hyph, first):
        if s and s not in out:
            out.append(s)
    return out


def candidates(name):
    urls = []
    for s in slugs(name):
        for tld in ("com", "fr", "io", "co"):
            for pre in ("https://www.", "https://"):
                urls.append(f"{pre}{s}.{tld}")
    # dédup en gardant l'ordre
    seen, out = set(), []
    for u in urls:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out[:12]


def valid(url, name):
    """URL valide si : répond (<400) ET host recoupe le nom ET la page montre un
    signal 'carrières' (lien/texte). Le signal évite d'accepter un domaine générique
    (ex: simc.com au hasard) qui n'est pas le bon employeur."""
    try:
        r = requests.get(url, headers=UA, timeout=8, allow_redirects=True)
        if r.status_code >= 400:
            return None
        host = _ascii(r.url).lower()
        toks = [
            t
            for t in re.sub(r"[^a-z0-9 ]", " ", _ascii(name).lower()).split()
            if len(t) > 3 and t not in STOP
        ]
        host_match = any(t in host for t in toks) if toks else False
        if not host_match:
            first = (
                re.sub(r"[^a-z0-9]", "", _ascii(name).lower().split()[0]) if name.split() else ""
            )
            host_match = bool(first and len(first) >= 3 and first in host)
        if not host_match:
            return None
        # note : PAS de garde "carrières visible" — trop de sites corporate chargent
        # le lien carrières en JS (faux négatifs Schneider/Allianz). Le runner (goto_careers
        # + sitemap + robots) trouve la section carrières lui-même.
        return r.url.rstrip("/")
    except Exception:
        return None


# agrégateurs / annuaires à ignorer dans les résultats de recherche (pas la homepage)
_AGG = re.compile(
    r"(linkedin|wikipedia|societe\.com|pappers|verif\.com|infogreffe|"
    r"facebook|twitter|x\.com|instagram|youtube|indeed|glassdoor|"
    r"welcometothejungle|hellowork|figaro|bfmtv|lesechos|usinenouvelle|"
    r"bloomberg|zoominfo|dnb\.com|manageo|kompass|europages|score3|"
    r"bodacc|journal-officiel|google\.|bing\.|duckduckgo)",
    re.I,
)


def _ddg_results(query):
    """Résultats DuckDuckGo HTML (sans clé API). Retour liste d'URLs."""
    from urllib.parse import parse_qs, unquote, urlparse

    urls = []
    for ep in ("https://html.duckduckgo.com/html/", "https://lite.duckduckgo.com/lite/"):
        try:
            r = requests.post(ep, data={"q": query}, headers=UA, timeout=10)
            if r.status_code >= 400:
                continue
            for m in re.findall(r'href="(https?://[^"]+)"', r.text):
                u = m
                if "duckduckgo.com/l/?uddg=" in u:  # lien redirect DDG -> extrait la vraie URL
                    qs = parse_qs(urlparse(u).query)
                    if "uddg" in qs:
                        u = unquote(qs["uddg"][0])
                if u.startswith("http") and not _AGG.search(u):
                    urls.append(u)
            if urls:
                break
        except Exception:
            continue
    return urls


def search_homepage(name):
    """Recherche moteur : 1er résultat non-agrégateur dont le host recoupe le nom."""
    toks = [
        t
        for t in re.sub(r"[^a-z0-9 ]", " ", _ascii(name).lower()).split()
        if len(t) > 2 and t not in STOP
    ]
    for q in (f"{name} site officiel", f"{name} recrutement carrières", f'"{name}" entreprise'):
        for u in _ddg_results(q)[:8]:
            got = valid(u, name)  # revalide (HTTP + host-match)
            if got:
                return got
        # fallback souple : accepte le 1er résultat propre même sans host-match strict
    for q in (f"{name} site officiel",):
        for u in _ddg_results(q)[:5]:
            try:
                host = _ascii(u).lower()
                if any(t[:5] in host for t in toks):
                    rr = requests.get(u, headers=UA, timeout=8, allow_redirects=True)
                    if rr.status_code < 400:
                        return rr.url.rstrip("/")
            except Exception:
                continue
    return None


def resolve(name):
    # 1) devinette de domaine (rapide)
    for u in candidates(name):
        got = valid(u, name)
        if got:
            return name, got
    # 2) recherche moteur (les noms complexes/acronymes)
    got = search_homepage(name)
    return name, got


def main():
    # Verrou inter-processus : ce programme reecrit la queue ENTIERE. Si un
    # autre le fait en meme temps (tache planifiee vs app), le dernier qui
    # ecrit efface le travail de l'autre.
    if not importlib.import_module("jobhunter.programmes.jutil").garder(QUEUE):
        return 3
    force = "--force" in sys.argv
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    Q = importlib.import_module("jobhunter.stockage.file").charger(QUEUE, descriptions=False)
    need = []
    for o in Q:
        if (o.get("url") or "").startswith("http"):
            continue
        # Filtrait sur priorite == "stage", qui melangeait un TYPE DE CONTRAT
        # avec une priorite. Le type vit maintenant dans `contrat`, seul champ
        # qui dise la verite (LinkedIn etiquette « CDI » les alternances).
        if str(o.get("contrat") or "") in ("Stage", "Alternance"):
            continue
        ent = (o.get("entreprise") or "").strip()
        if ent and ent not in need and (force or ent not in cache):
            need.append(ent)
    print(f"{len(need)} entreprises à résoudre (cache: {len(cache)})")
    found = 0
    with cf.ThreadPoolExecutor(max_workers=12) as ex:
        for name, url in ex.map(resolve, need):
            # ne JAMAIS écraser une homepage déjà trouvée (ex: WebSearch manuel) par None
            if url or not cache.get(name):
                cache[name] = url
            if url:
                found += 1
                print(f"  ✅ {name[:35]:35} → {url}")
            else:
                print(f"  ❌ {name[:35]:35} → introuvable")
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
    tot = sum(1 for v in cache.values() if v)
    print(
        f"\n{found}/{len(need)} trouvées cette passe · cache total {tot} homepages · → {CACHE.name}"
    )


if __name__ == "__main__":
    sys.exit(main())
