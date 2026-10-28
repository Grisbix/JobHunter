#!/usr/bin/env python3
"""enrich_homepages.py — Finds the home page URL of companies WITHOUT an offer URL.
Guesses the domain from the name (slug + .com/.fr) and VALIDATES over HTTP (200, consistent host).
Writes Scripts/homepages.json {company: url}. build_queue uses it as a fallback
(url_type=HOMEPAGE, canal=auto) → the runner navigates home → goto_careers → offer.

Run: python JobHunter.pyw enrich_homepages        (all the companies without a URL in the queue)
     python JobHunter.pyw enrich_homepages --force (revalidates even those already cached)
"""

import concurrent.futures as cf
import importlib
import json
import re
import sys
import unicodedata

import httpx

from jobhunter import root as _racine

sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]  # console : TextIOWrapper

SCRIPTS = _racine.scripts()
QUEUE = SCRIPTS / "apply_queue.json"
CACHE = SCRIPTS / "homepages.json"
UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
}

# legal/generic tokens to remove from the slug
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
    """Deliberately MORE aggressive than jutil.sans_accent: here we build domain name
    slugs, so any non-ASCII character must DISAPPEAR, not only lose its accent. It
    is not a duplicate to factor out."""
    return unicodedata.normalize("NFD", s or "").encode("ascii", "ignore").decode()


def slugs(name):
    """Generates slug variants from the company name."""
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
    # dedup keeping the order
    seen, out = set(), []
    for u in urls:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out[:12]


def valid(url, name):
    """URL valid if: answers (<400) AND the host matches the name AND the page shows a
    'careers' signal (link/text). The signal avoids accepting a generic domain (e.g.
    simc.com by chance) that is not the right employer."""
    try:
        r = httpx.get(url, headers=UA, timeout=8, follow_redirects=True)
        if r.status_code >= 400:
            return None
        host = _ascii(str(r.url)).lower()
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
        # note: NO "careers visible" guard — too many corporate sites load
        # the careers link in JS (Schneider/Allianz false negatives). The runner (goto_careers
        # + sitemap + robots) finds the careers section itself.
        return str(r.url).rstrip("/")
    except Exception:
        return None


# aggregators / directories to ignore in the search results (not the homepage)
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
            r = httpx.post(ep, data={"q": query}, headers=UA, timeout=10)
            if r.status_code >= 400:
                continue
            for m in re.findall(r'href="(https?://[^"]+)"', r.text):
                u = m
                if "duckduckgo.com/l/?uddg=" in u:  # DDG redirect link -> extracts the real URL
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
    """Search engine: 1st non-aggregator result whose host matches the name."""
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
        # loose fallback: accepts the 1st clean result even without a strict host match
    for q in (f"{name} site officiel",):
        for u in _ddg_results(q)[:5]:
            try:
                host = _ascii(u).lower()
                if any(t[:5] in host for t in toks):
                    rr = httpx.get(u, headers=UA, timeout=8, follow_redirects=True)
                    if rr.status_code < 400:
                        return str(rr.url).rstrip("/")
            except Exception:
                continue
    return None


def resolve(name):
    # 1) devinette de domaine (rapide)
    for u in candidates(name):
        got = valid(u, name)
        if got:
            return name, got
    # 2) search engine (complex names/acronyms)
    got = search_homepage(name)
    return name, got


def main():
    # Inter-process lock: this program rewrites the ENTIRE queue. If
    # another one does it at the same time (scheduled task vs app), the last one
    # to write erases the other's work.
    if not importlib.import_module("jobhunter.programs.util").garder(QUEUE):
        return 3
    force = "--force" in sys.argv
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    Q = importlib.import_module("jobhunter.storage.queue").charger(QUEUE, descriptions=False)
    need = []
    for o in Q:
        if (o.get("url") or "").startswith("http"):
            continue
        # Filtered on priorite == "stage", which mixed a CONTRACT TYPE
        # with a priority. The type now lives in `contrat`, the only field
        # that tells the truth (LinkedIn labels work-study contracts "CDI").
        if str(o.get("contrat") or "") in ("Stage", "Alternance"):
            continue
        ent = (o.get("entreprise") or "").strip()
        if ent and ent not in need and (force or ent not in cache):
            need.append(ent)
    print(f"{len(need)} entreprises à résoudre (cache: {len(cache)})")
    found = 0
    with cf.ThreadPoolExecutor(max_workers=12) as ex:
        for name, url in ex.map(resolve, need):
            # NEVER overwrite a homepage already found (e.g. manual WebSearch) with None
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
