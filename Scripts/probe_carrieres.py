#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""probe_carrieres.py — Trouve la VRAIE page carrière de chaque site, et son ATS.

POURQUOI. `scrape_jobs.py` devine 14 chemins par domaine (`/careers`, `/jobs`,
`/recrutement`…) et s'arrête au premier qui répond. Mesuré sur les 11 premiers
sites : 0 offre. La Banque Postale renvoie 404 sur les 7 chemins essayés, BPCE
répond 200 sur les 4 siens et n'affiche rien — sa page est une SPA Workday.
Deviner une URL ne dit ni où sont les offres, ni comment les lire.

CE PROGRAMME NE DEVINE PAS D'ABORD, IL LIT. Trois passes, de la moins chère à
la plus chère :

  1. LA PAGE D'ACCUEIL. Un site corporate porte son lien « Carrières » dans sa
     navigation. Une requête, et on suit le lien qu'il donne lui-même — c'est
     l'inverse de deviner.
  2. LE SITEMAP. `robots.txt` déclare souvent un sitemap ; les URL carrière y
     figurent. Utile quand la navigation est rendue en JavaScript.
  3. LES CHEMINS DEVINÉS, en dernier recours et sur une liste large.

CE QUI COMPTE VRAIMENT : L'ATS DERRIÈRE. Trouver `careers.axa.com` ne sert à
rien, c'est une vitrine anti-bot. Trouver que ses offres viennent de
`axa.wd3.myworkdayjobs.com`, si : Workday, Greenhouse, Lever, SmartRecruiters,
Ashby et Recruitee exposent tous une API JSON publique. C'est ce qui fait que
`job_sources.py` ramène 324 offres là où le scraper DOM en ramène 0.

Ne modifie RIEN. Affiche, et écrit un JSON si on le demande.

Run :
  python probe_carrieres.py
  python probe_carrieres.py --json carrieres.json
  python probe_carrieres.py --domaines axa,bpce      # filtre
  python probe_carrieres.py --sans-sitemap           # passes 1 et 3 seulement
"""
import argparse
import concurrent.futures as cf
import json
import re
import sys
from html import unescape
from pathlib import Path
from urllib.parse import urljoin, urlsplit

sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
      "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8"}

# ── Les mots qui désignent une section carrière ──────────────────────────────
# Servent DEUX fois : sur le texte visible d'un lien, et sur son href. Un site
# dit « Nous rejoindre » et pointe `/recrutement` ; un autre dit « Careers » et
# pointe `/en/about-us/join`. Il faut les deux angles pour ne pas rater.
MOTS_TEXTE = [
    "recrutement", "recrute", "carriere", "carrière", "carrieres", "carrières",
    "career", "careers", "emploi", "emplois", "offre d'emploi", "offres d'emploi",
    "nous rejoindre", "rejoignez-nous", "rejoignez nous", "rejoindre",
    "travailler chez", "travailler avec", "postuler", "candidature", "candidatures",
    "talent", "talents", "job", "jobs", "join us", "join our", "work with us",
    "work for us", "working at", "life at", "vacancies", "vacancy",
    "opportunities", "opportunités", "opportunites", "hiring", "recruitment",
    "nos metiers", "nos métiers", "espace candidat",
]
# Sur le href, on ne veut QUE des segments de chemin : « career » comme
# sous-chaîne libre matcherait « /careful-investing ». On borne par / - _ . ou fin.
MOTS_HREF = [
    "recrutement", "recrute", "carriere", "carrieres", "career", "careers",
    "emploi", "emplois", "offres-emploi", "nous-rejoindre", "rejoignez-nous",
    "rejoindre", "travailler", "postuler", "candidat", "talent", "talents",
    "job", "jobs", "join-us", "joinus", "join", "work-with-us", "workwithus",
    "life-at", "lifeat", "vacancies", "opportunities", "hiring", "recruitment",
    "espace-candidat", "nos-metiers",
]
# SUR DES MOTS ENTIERS. En sous-chaîne libre, « job » matche « Jobijoba » et
# « Jobijoba au service des entreprises » désignait magnet.work comme le
# portail de recrutement. `\b` suffit : dans « Jobijoba », il y a bien une
# frontière avant le J mais pas après le b de « Job ».
RX_TEXTE = re.compile(r"\b(?:" + "|".join(re.escape(m) for m in MOTS_TEXTE) + r")\b", re.I)

_SEP = r"[/\-_.?=&]"
RX_HREF = re.compile(
    r"(?:^|" + _SEP + r")(" + "|".join(re.escape(m) for m in MOTS_HREF) + r")(?:" + _SEP + r"|$)",
    re.I)

# ── Les chemins devinés, PASSE 3 ─────────────────────────────────────────────
# Beaucoup plus large que les 14 de scrape_jobs, et avec les préfixes de langue
# qui manquaient (`/fr/`, `/fr-fr/`, `/en/`).
CHEMINS = [
    "/recrutement", "/recrutements", "/carriere", "/carrieres", "/carrières",
    "/career", "/careers", "/emploi", "/emplois", "/offres", "/offres-emploi",
    "/nos-offres", "/nous-rejoindre", "/rejoignez-nous", "/rejoindre",
    "/travailler-chez-nous", "/talents", "/talent", "/jobs", "/job",
    "/join-us", "/work-with-us", "/vacancies", "/opportunities",
    "/espace-candidat", "/nos-metiers", "/postuler",
    "/about/careers", "/about-us/careers", "/company/careers", "/group/careers",
    "/a-propos/carrieres", "/notre-groupe/carrieres",
    "/fr/carrieres", "/fr/recrutement", "/fr/emploi", "/fr/nous-rejoindre",
    "/fr-fr/careers", "/fr-fr/carrieres",
    "/en/careers", "/en/jobs", "/en/join-us",
    "/careers/jobs", "/careers/search", "/search/jobs", "/job-search",
]

# ── Les ATS, et pourquoi on les cherche ──────────────────────────────────────
# Chacun expose une API JSON publique. Trouver l'ATS d'une société, c'est
# pouvoir lire ses offres proprement au lieu de gratter une page rendue.
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

# Réseaux sociaux et agrégateurs : « eFinancialCareers sur Twitter » porte
# « career » dans son libellé et menait tout droit à twitter.com. Ce ne sont
# jamais les offres de la société, c'est sa communication.
HOTES_IGNORES = ("twitter.com", "x.com", "facebook.com", "instagram.com",
                 "youtube.com", "linkedin.com", "tiktok.com", "pinterest.",
                 "wechat", "weibo.", "t.me", "whatsapp.")

# Un libellé de navigation est COURT : « Carrières », « Nous rejoindre ».
# Au-delà, on lit du corps de page — « Diversité, équité et inclusion La
# diversité des talents, des… » a fait passer une page RSE pour un portail
# d'emploi. Un texte long n'est retenu que si le href confirme.
LIBELLE_MAX = 40


def _texte(html_fragment):
    return re.sub(r"\s+", " ", unescape(RX_BALISE.sub(" ", html_fragment or ""))).strip()


def ats_de(url):
    """Quel ATS sert cette URL ? '' si aucun reconnu."""
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
    """TOUS les liens de la page qui pointent vers un ATS connu.

    Passe à part, et pas un filtre sur `liens_carriere` : un lien d'ATS ne
    porte pas forcément de mot carrière. « Voir nos offres » →
    `axa.wd3.myworkdayjobs.com/AXA` n'a ni « career » ni « recrutement », ni
    dans son texte ni dans son href (`myworkdayjobs` ne contient pas « jobs »
    sur une frontière). En cherchant l'ATS dans les seuls liens déjà retenus,
    on jetait la trouvaille avant de la regarder.
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
    """Les liens de la page qui mènent vers une section carrière.

    Rend une liste [(url, texte, pourquoi)] triée : un lien reconnu par SON
    TEXTE vaut mieux qu'un lien reconnu par son href — le texte est ce que le
    site affiche à un humain, le href peut être un mot de passage.
    """
    vus, sortie = set(), []
    for href, dedans in RX_LIEN.findall(html or ""):
        href = unescape(href.strip())
        if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue
        txt = _texte(dedans)[:80]
        par_href = bool(RX_HREF.search(href))
        # Le texte ne compte que s'il ressemble a un libelle de navigation.
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
    # les plus courtes d'abord : « /carrieres » avant « /carrieres/offre/1234 »
    return sorted(set(trouve), key=len)[:15]


def sonde_site(entree, faire_sitemap=True):
    """Les trois passes sur un site. Rend un dict de résultat."""
    import httpx
    from scrape_jobs import extract_company_name, robots_autorise
    racine = entree["url"]
    res = {
        "num": entree["num"], "entreprise": extract_company_name(entree),
        "domaine": entree["domain"], "racine": racine,
        "carriere": "", "via": "", "libelle": "", "ats": "",
        "ats_urls": [], "candidats": [], "note": "",
    }
    with httpx.Client(headers=UA, follow_redirects=True) as client:
        # ── passe 1 : la page d'accueil dit où elle recrute ──
        r = _get(client, racine, timeout=20)
        if r is None:
            res["note"] = "injoignable"
            return res
        if r.status_code >= 400:
            res["note"] = f"HTTP {r.status_code}"
        arrivee = str(r.url)
        if urlsplit(arrivee).netloc.lower().lstrip("www.") != \
                urlsplit(racine).netloc.lower().lstrip("www."):
            res["note"] = (res["note"] + " ; " if res["note"] else "") + f"redirige → {arrivee}"

        html = r.text or "" if r.status_code < 400 else ""
        # Un lien qui pointe DIRECTEMENT sur un ATS est le jackpot : c'est la
        # source, pas la vitrine. On le cherche parmi TOUS les liens.
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
            # la page carrière elle-même pointe-t-elle vers un ATS ?
            rc = _get(client, url, timeout=20)
            if rc is not None and rc.status_code < 400:
                dedans = liens_ats(rc.text or "", str(rc.url))
                # l'URL finale elle-meme peut etre l'ATS (la page carriere
                # redirige souvent droit sur le portail)
                if ats_de(str(rc.url)):
                    dedans.insert(0, (str(rc.url), "", ats_de(str(rc.url))))
                if dedans:
                    res["ats"] = dedans[0][2]
                    res["ats_urls"] = [u for u, _, _ in dedans[:5]]
                    res["via"] += "→ATS"
            return res

        # ── passe 2 : le sitemap déclaré ──
        if faire_sitemap:
            sm = urls_carriere_sitemap(client, sitemaps_de(client, racine))
            if sm:
                res.update(carriere=sm[0], via="sitemap")
                res["candidats"] = sm[:8]
                # ats ET ats_urls ensemble : les renseigner separement laissait
                # un ATS annonce sans une seule URL pour le joindre.
                urls_ats = [u for u in sm if ats_de(u)]
                if urls_ats:
                    res["ats"] = ats_de(urls_ats[0])
                    res["ats_urls"] = urls_ats[:5]
                return res

        # ── passe 3 : les chemins devinés, en dernier ──
        for chemin in CHEMINS:
            u = racine.rstrip("/") + chemin
            if not robots_autorise(u):
                continue
            rr = _get(client, u, timeout=10)
            if rr is None or rr.status_code != 200 or len(rr.text or "") <= 800:
                continue
            # SOFT-404. Beaucoup de sites rendent 200 sur n'importe quoi et
            # servent leur accueil. `ubs.com/global/en/careers.html/recrutement`
            # repondait 200 — une URL qui ne peut pas exister. Si le chemin
            # demande n'est plus dans l'URL finale, on n'a pas trouve la page,
            # on s'est fait rediriger.
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

    from scrape_jobs import load_domains
    entrees = load_domains(str(HERE / "unique_domains.txt"))
    if a.domaines:
        f = [x.strip().lower() for x in a.domaines.split(",") if x.strip()]
        entrees = [e for e in entrees if any(x in e["domain"].lower() for x in f)]
    print(f"🔍 {len(entrees)} sites — accueil, puis sitemap, puis chemins devinés\n")

    with cf.ThreadPoolExecutor(max_workers=a.fils) as ex:
        res = list(ex.map(lambda e: sonde_site(e, not a.sans_sitemap), entrees))
    res.sort(key=lambda r: r["num"])

    # ON ECRIT AVANT D'AFFICHER. Une IndexError dans une f-string de mise en
    # page a deja jete une collecte de cinq minutes sur 65 sites : le travail
    # etait fait, il n'en restait rien. Le fichier d'abord, la forme ensuite.
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

    print(f"\n{'='*70}")
    print(f"ATS identifié {len(avec_ats)}/{len(res)} · page seule {len(avec_page)} · rien {len(sans)}")
    compte = {}
    for r in avec_ats:
        compte[r["ats"]] = compte.get(r["ats"], 0) + 1
    if compte:
        print("Par ATS : " + ", ".join(f"{k} ×{v}" for k, v in
                                       sorted(compte.items(), key=lambda kv: -kv[1])))
    if a.json:
        print(f"→ {a.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
