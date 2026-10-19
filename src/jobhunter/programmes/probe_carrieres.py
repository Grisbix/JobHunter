#!/usr/bin/env python3
"""probe_carrieres.py — Finds the REAL career page of each site, and its ATS.

WHY. `scrape_jobs.py` guesses 14 paths per domain (`/careers`, `/jobs`,
`/recrutement`…) and stops at the first that answers. Measured on the first 11 sites:
0 offers. La Banque Postale returns 404 on the 7 paths tried, BPCE answers 200 on its 4
and displays nothing — its page is a Workday SPA. Guessing a URL says neither where the
offers are nor how to read them.

THIS PROGRAM DOES NOT GUESS FIRST, IT READS. Three passes, from the cheapest to the
most expensive:

  1. THE HOME PAGE. A corporate site carries its "Careers" link in its navigation. One
     request, and we follow the link it gives itself — the opposite of guessing.
  2. THE SITEMAP. `robots.txt` often declares a sitemap; the career URLs are in it.
     Useful when the navigation is rendered in JavaScript.
  3. THE GUESSED PATHS, as a last resort and on a wide list.

WHAT REALLY MATTERS: THE ATS BEHIND. Finding `careers.axa.com` is useless, it is an
anti-bot shop window. Finding that its offers come from `axa.wd3.myworkdayjobs.com`
is not: Workday, Greenhouse, Lever, SmartRecruiters, Ashby and Recruitee all expose a
public JSON API. That is what makes `job_sources.py` bring back 324 offers where the
DOM scraper brings back 0.

Changes NOTHING. Displays, and writes a JSON if asked.

Run:
  python JobHunter.pyw probe_carrieres
  python JobHunter.pyw probe_carrieres --json carrieres.json
  python JobHunter.pyw probe_carrieres --domaines axa,bpce      # filter
  python JobHunter.pyw probe_carrieres --sans-sitemap           # passes 1 and 3 only
"""

import argparse
import concurrent.futures as cf
import json
import re
import sys
from html import unescape
from pathlib import Path
from urllib.parse import urljoin, urlsplit

from jobhunter import racine as _racine

sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)  # type: ignore[union-attr]  # console : TextIOWrapper
HERE = _racine.scripts()


UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
}

# ── The words that designate a career section ────────────────────────────────
# Used TWICE: on a link's visible text, and on its href. One site
# says "Nous rejoindre" and points to `/recrutement`; another says "Careers" and
# points to `/en/about-us/join`. Both angles are needed not to miss.
MOTS_TEXTE = [
    "recrutement",
    "recrute",
    "carriere",
    "carrière",
    "carrieres",
    "carrières",
    "career",
    "careers",
    "emploi",
    "emplois",
    "offre d'emploi",
    "offres d'emploi",
    "nous rejoindre",
    "rejoignez-nous",
    "rejoignez nous",
    "rejoindre",
    "travailler chez",
    "travailler avec",
    "postuler",
    "candidature",
    "candidatures",
    "talent",
    "talents",
    "job",
    "jobs",
    "join us",
    "join our",
    "work with us",
    "work for us",
    "working at",
    "life at",
    "vacancies",
    "vacancy",
    "opportunities",
    "opportunités",
    "opportunites",
    "hiring",
    "recruitment",
    "nos metiers",
    "nos métiers",
    "espace candidat",
]
# On the href, we ONLY want path segments: "career" as a free
# substring would match "/careful-investing". We bound with / - _ . or end.
MOTS_HREF = [
    "recrutement",
    "recrute",
    "carriere",
    "carrieres",
    "career",
    "careers",
    "emploi",
    "emplois",
    "offres-emploi",
    "nous-rejoindre",
    "rejoignez-nous",
    "rejoindre",
    "travailler",
    "postuler",
    "candidat",
    "talent",
    "talents",
    "job",
    "jobs",
    "join-us",
    "joinus",
    "join",
    "work-with-us",
    "workwithus",
    "life-at",
    "lifeat",
    "vacancies",
    "opportunities",
    "hiring",
    "recruitment",
    "espace-candidat",
    "nos-metiers",
]
# ON WHOLE WORDS. As a free substring, "job" matches "Jobijoba" and
# "Jobijoba au service des entreprises" designated magnet.work as the
# recruiting portal. `\b` is enough: in "Jobijoba", there is indeed a
# boundary before the J but not after the b of "Job".
RX_TEXTE = re.compile(r"\b(?:" + "|".join(re.escape(m) for m in MOTS_TEXTE) + r")\b", re.I)

_SEP = r"[/\-_.?=&]"
RX_HREF = re.compile(
    r"(?:^|" + _SEP + r")(" + "|".join(re.escape(m) for m in MOTS_HREF) + r")(?:" + _SEP + r"|$)",
    re.I,
)

# ── The guessed paths, PASS 3 ────────────────────────────────────────────────
# Much wider than scrape_jobs' 14, and with the language prefixes
# that were missing (`/fr/`, `/fr-fr/`, `/en/`).
CHEMINS = [
    "/recrutement",
    "/recrutements",
    "/carriere",
    "/carrieres",
    "/carrières",
    "/career",
    "/careers",
    "/emploi",
    "/emplois",
    "/offres",
    "/offres-emploi",
    "/nos-offres",
    "/nous-rejoindre",
    "/rejoignez-nous",
    "/rejoindre",
    "/travailler-chez-nous",
    "/talents",
    "/talent",
    "/jobs",
    "/job",
    "/join-us",
    "/work-with-us",
    "/vacancies",
    "/opportunities",
    "/espace-candidat",
    "/nos-metiers",
    "/postuler",
    "/about/careers",
    "/about-us/careers",
    "/company/careers",
    "/group/careers",
    "/a-propos/carrieres",
    "/notre-groupe/carrieres",
    "/fr/carrieres",
    "/fr/recrutement",
    "/fr/emploi",
    "/fr/nous-rejoindre",
    "/fr-fr/careers",
    "/fr-fr/carrieres",
    "/en/careers",
    "/en/jobs",
    "/en/join-us",
    "/careers/jobs",
    "/careers/search",
    "/search/jobs",
    "/job-search",
]

# ── The ATS, and why we look for them ────────────────────────────────────────
# Each exposes a public JSON API. Finding a company's ATS means
# being able to read its offers cleanly instead of scraping a rendered page.
ATS = {
    "myworkdayjobs.com": "Workday",
    "workday.com": "Workday",
    "boards.greenhouse.io": "Greenhouse",
    "greenhouse.io": "Greenhouse",
    "jobs.lever.co": "Lever",
    "lever.co": "Lever",
    "jobs.ashbyhq.com": "Ashby",
    "ashbyhq.com": "Ashby",
    "smartrecruiters.com": "SmartRecruiters",
    "recruitee.com": "Recruitee",
    "teamtailor.com": "Teamtailor",
    "workable.com": "Workable",
    "personio.": "Personio",
    "icims.com": "iCIMS",
    "taleo.net": "Taleo",
    "successfactors.com": "SuccessFactors",
    "successfactors.eu": "SuccessFactors",
    "avature.net": "Avature",
    "talent-soft.com": "TalentSoft",
    "talentsoft.com": "TalentSoft",
    "flatchr.io": "Flatchr",
    "softy.pro": "Softy",
    "breezy.hr": "Breezy",
    "welcometothejungle.com": "Welcome to the Jungle",
    "cornerstoneondemand.com": "Cornerstone",
    "csod.com": "Cornerstone",
    "eightfold.ai": "Eightfold",
    "phenompeople.com": "Phenom",
    "jobvite.com": "Jobvite",
    "bamboohr.com": "BambooHR",
    "jobteaser.com": "JobTeaser",
    "beetween.": "Beetween",
    "digitalrecruiters.com": "DigitalRecruiters",
}

RX_LIEN = re.compile(r"<a\b[^>]*?href\s*=\s*[\"']([^\"'>]+)[\"'][^>]*>(.*?)</a>", re.I | re.S)
RX_BALISE = re.compile(r"<[^>]+>")

# Social networks and aggregators: "eFinancialCareers sur Twitter" carries
# "career" in its label and led straight to twitter.com. They are
# never the company's offers, it is its communication.
HOTES_IGNORES = (
    "twitter.com",
    "x.com",
    "facebook.com",
    "instagram.com",
    "youtube.com",
    "linkedin.com",
    "tiktok.com",
    "pinterest.",
    "wechat",
    "weibo.",
    "t.me",
    "whatsapp.",
)

# A navigation label is SHORT: "Carrières", "Nous rejoindre".
# Beyond that, we are reading page body — "Diversité, équité et inclusion La
# diversité des talents, des…" passed a CSR page off as a job
# portal. A long text is only kept if the href confirms.
LIBELLE_MAX = 40


def _texte(html_fragment):
    return re.sub(r"\s+", " ", unescape(RX_BALISE.sub(" ", html_fragment or ""))).strip()


def ats_de(url):
    """Which ATS serves this URL? '' if none is recognised."""
    u = (url or "").lower()
    for cle, nom in ATS.items():
        if cle in u:
            return nom
    return ""


def _get(client, url, timeout=15):
    try:
        r = client.get(url, timeout=timeout, headers=UA, follow_redirects=True)
        return r
    except Exception:
        return None


def liens_ats(html, base):
    """ALL the links of the page that point to a known ATS.

    A separate pass, and not a filter on `liens_carriere`: an ATS link does not
    necessarily carry a career word. "Voir nos offres" →
    `axa.wd3.myworkdayjobs.com/AXA` has neither "career" nor "recrutement", neither
    in its text nor in its href (`myworkdayjobs` does not contain "jobs" on a
    boundary). By looking for the ATS only in the links already kept, we threw the
    find away before looking at it.
    """
    vus, sortie = set(), []
    for href, dedans in RX_LIEN.findall(html or ""):
        href = unescape(href.strip())
        if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue
        url = urljoin(base, href)
        nom = ats_de(url)
        if nom and url not in vus:
            vus.add(url)
            sortie.append((url, _texte(dedans)[:80], nom))
    return sortie


def liens_carriere(html, base):
    """The links of the page that lead to a career section.

    Returns a list [(url, text, why)] sorted: a link recognised by ITS TEXT is better
    than a link recognised by its href — the text is what the site displays to a
    human, the href may be a passing word.
    """
    vus, sortie = set(), []
    for href, dedans in RX_LIEN.findall(html or ""):
        href = unescape(href.strip())
        if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue
        txt = _texte(dedans)[:80]
        par_href = bool(RX_HREF.search(href))
        # The text only counts if it looks like a navigation label.
        par_texte = bool(RX_TEXTE.search(txt)) and len(txt) <= LIBELLE_MAX
        if not (par_texte or par_href):
            continue
        url = urljoin(base, href)
        if url in vus or any(h in url.lower() for h in HOTES_IGNORES):
            continue
        vus.add(url)
        sortie.append((url, txt, "texte" if par_texte else "href"))
    sortie.sort(key=lambda x: (x[2] != "texte", len(x[0])))
    return sortie


def sitemaps_de(client, racine):
    """Les sitemaps déclarés dans robots.txt."""
    r = _get(client, racine.rstrip("/") + "/robots.txt", timeout=10)
    if not r or r.status_code != 200:
        return []
    return re.findall(r"(?im)^\s*sitemap:\s*(\S+)", r.text)[:3]


def urls_carriere_sitemap(client, sitemaps):
    """Les URL d'un sitemap qui portent un mot carrière. Un seul niveau
    d'index : un sitemap d'index renvoie vers d'autres sitemaps, on suit le
    premier qui a l'air carrière plutôt que de tout aspirer."""
    trouve = []
    for sm in sitemaps:
        r = _get(client, sm, timeout=15)
        if not r or r.status_code != 200:
            continue
        urls = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", r.text)
        fils = [u for u in urls if u.endswith((".xml", ".xml.gz")) and RX_HREF.search(u)]
        for f in fils[:2]:
            rf = _get(client, f, timeout=15)
            if rf and rf.status_code == 200:
                urls += re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", rf.text)
        trouve += [u for u in urls if RX_HREF.search(u)]
        if trouve:
            break
    # the shortest first: "/carrieres" before "/carrieres/offre/1234"
    return sorted(set(trouve), key=len)[:15]


def sonde_site(entree, faire_sitemap=True):
    """Les trois passes sur un site. Rend un dict de résultat."""
    import httpx

    from jobhunter.programmes.scrape_jobs import extract_company_name, robots_autorise

    racine = entree["url"]
    res = {
        "num": entree["num"],
        "entreprise": extract_company_name(entree),
        "domaine": entree["domain"],
        "racine": racine,
        "carriere": "",
        "via": "",
        "libelle": "",
        "ats": "",
        "ats_urls": [],
        "candidats": [],
        "note": "",
    }
    with httpx.Client(headers=UA, follow_redirects=True) as client:
        # ── pass 1: the home page says where it recruits ──
        r = _get(client, racine, timeout=20)
        if r is None:
            res["note"] = "injoignable"
            return res
        if r.status_code >= 400:
            res["note"] = f"HTTP {r.status_code}"
        arrivee = str(r.url)
        if urlsplit(arrivee).netloc.lower().lstrip("www.") != urlsplit(
            racine
        ).netloc.lower().lstrip("www."):
            res["note"] = (res["note"] + " ; " if res["note"] else "") + f"redirige → {arrivee}"

        html = r.text or "" if r.status_code < 400 else ""
        # A link that points DIRECTLY to an ATS is the jackpot: it is the
        # source, not the shop window. We look for it among ALL the links.
        direct = liens_ats(html, arrivee)
        if direct:
            url, txt, nom = direct[0]
            res.update(carriere=url, via="accueil→ATS", libelle=txt, ats=nom)
            res["ats_urls"] = [u for u, _, _ in direct[:5]]
            return res
        liens = liens_carriere(html, arrivee)
        if liens:
            url, txt, pourquoi = liens[0]
            res.update(carriere=url, via=f"accueil ({pourquoi})", libelle=txt)
            res["candidats"] = [u for u, _, _ in liens[:8]]
            # does the career page itself point to an ATS?
            rc = _get(client, url, timeout=20)
            if rc is not None and rc.status_code < 400:
                dedans = liens_ats(rc.text or "", str(rc.url))
                # the final URL itself may be the ATS (the career page
                # often redirects straight to the portal)
                if ats_de(str(rc.url)):
                    dedans.insert(0, (str(rc.url), "", ats_de(str(rc.url))))
                if dedans:
                    res["ats"] = dedans[0][2]
                    res["ats_urls"] = [u for u, _, _ in dedans[:5]]
                    res["via"] += "→ATS"
            return res

        # ── pass 2: the declared sitemap ──
        if faire_sitemap:
            sm = urls_carriere_sitemap(client, sitemaps_de(client, racine))
            if sm:
                res.update(carriere=sm[0], via="sitemap")
                res["candidats"] = sm[:8]
                # ats AND ats_urls together: filling them separately left
                # an announced ATS without a single URL to reach it.
                urls_ats = [u for u in sm if ats_de(u)]
                if urls_ats:
                    res["ats"] = ats_de(urls_ats[0])
                    res["ats_urls"] = urls_ats[:5]
                return res

        # ── pass 3: the guessed paths, last ──
        for chemin in CHEMINS:
            u = racine.rstrip("/") + chemin
            if not robots_autorise(u):
                continue
            rr = _get(client, u, timeout=10)
            if rr is None or rr.status_code != 200 or len(rr.text or "") <= 800:
                continue
            # SOFT-404. Many sites return 200 on anything and
            # serve their home page. `ubs.com/global/en/careers.html/recrutement`
            # answered 200 — a URL that cannot exist. If the requested path
            # is no longer in the final URL, we did not find the page,
            # we got redirected.
            final = str(rr.url).lower().rstrip("/")
            dernier = chemin.strip("/").split("/")[-1].lower()
            if dernier not in final:
                continue
            res.update(carriere=str(rr.url), via="chemin deviné")
            res["ats"] = ats_de(str(rr.url))
            if res["ats"]:
                res["ats_urls"] = [str(rr.url)]
            return res
    if not res["note"]:
        res["note"] = "rien trouvé"
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--domaines", help="filtre, séparé par des virgules")
    ap.add_argument("--json", help="écrit le résultat complet dans ce fichier")
    ap.add_argument("--sans-sitemap", action="store_true", help="saute la passe 2")
    ap.add_argument("--fils", type=int, default=8, help="requêtes en parallèle")
    a = ap.parse_args()

    from jobhunter.programmes.scrape_jobs import load_domains

    entrees = load_domains(str(HERE / "unique_domains.txt"))
    if a.domaines:
        f = [x.strip().lower() for x in a.domaines.split(",") if x.strip()]
        entrees = [e for e in entrees if any(x in e["domain"].lower() for x in f)]
    print(f"🔍 {len(entrees)} sites — accueil, puis sitemap, puis chemins devinés\n")

    with cf.ThreadPoolExecutor(max_workers=a.fils) as ex:
        res = list(ex.map(lambda e: sonde_site(e, not a.sans_sitemap), entrees))
    res.sort(key=lambda r: r["num"])

    # WE WRITE BEFORE DISPLAYING. An IndexError in a formatting f-string
    # already threw away a five-minute collection over 65 sites: the work
    # was done, nothing was left of it. The file first, the form afterwards.
    if a.json:
        Path(a.json).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")

    avec_ats = [r for r in res if r["ats"]]
    avec_page = [r for r in res if r["carriere"] and not r["ats"]]
    sans = [r for r in res if not r["carriere"]]

    print(f"── ATS identifié : {len(avec_ats)} ── (API JSON lisible, la bonne source)")
    for r in avec_ats:
        lien = (r["ats_urls"] or [r["carriere"]] or [""])[0]
        print(f"  #{r['num']:2d} {r['entreprise']:24s} {r['ats']:18s} {lien[:70]}")
    print(f"\n── page carrière trouvée, ATS inconnu : {len(avec_page)} ──")
    for r in avec_page:
        print(f"  #{r['num']:2d} {r['entreprise']:24s} [{r['via']:16s}] {r['carriere'][:62]}")
        if r["libelle"]:
            print(f"      lien : « {r['libelle'][:60]} »")
    print(f"\n── rien trouvé : {len(sans)} ──")
    for r in sans:
        print(f"  #{r['num']:2d} {r['entreprise']:24s} {r['note']}")

    print(f"\n{'=' * 70}")
    print(
        f"ATS identifié {len(avec_ats)}/{len(res)} · page seule {len(avec_page)} · rien {len(sans)}"
    )
    compte = {}
    for r in avec_ats:
        compte[r["ats"]] = compte.get(r["ats"], 0) + 1
    if compte:
        print(
            "Par ATS : "
            + ", ".join(f"{k} ×{v}" for k, v in sorted(compte.items(), key=lambda kv: -kv[1]))
        )
    if a.json:
        print(f"→ {a.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
