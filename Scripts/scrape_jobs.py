#!/usr/bin/env python3
"""
scrape_jobs.py — Scrape les offres FRAÎCHES des 65 sites carrière d'entreprises ESG/Finance.

Utilise Playwright pour naviguer sur chaque site carrière,
détecter les listes d'offres et filtrer par mots-clés ESG/Finance.

Usage:
    python scrape_jobs.py                         # Scrape tous les sites
    python scrape_jobs.py --sites 1-10            # Sites 1 à 10 seulement
    python scrape_jobs.py --domains wtj,smart     # Par nom de domaine partiel
    python scrape_jobs.py --output offres_fraiches.json
    python scrape_jobs.py --headless              # Mode headless (pas de fenêtre)
    python scrape_jobs.py --skip 10               # Sites déjà scrapés, reprendre au 11e
"""

import argparse
import json
import random
import sys
import time
from pathlib import Path

# Sortie UTF-8 OBLIGATOIRE : ce programme affiche des emojis. Dans un terminal
# Windows la console les tolere, mais des que la sortie est redirigee (tuyau,
# fichier de log, tache planifiee) Python retombe sur cp1252 et leve
# UnicodeEncodeError des la premiere ligne — le scraping mourait avant d'ouvrir
# le moindre site, sans qu'aucune offre ne soit collectee.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# Domaine d'une offre et lexique large : jobhunter.scoring.domaines (phase 3.4).
import profil as _P  # noqa: F401  (charge src/ dans sys.path)
from jobhunter.scoring.domaines import (  # noqa: E402, F401
    DOMAINE_MAP,
    ESG_FINANCE_KEYWORDS,
    classify_domaine,
    matches_esg_finance,
)

# ── JS : Extraction universelle d'offres d'emploi ──
EXTRACT_OFFERS_JS = r"""
() => {
  const jobs = [];
  const seen = new Set();
  const norm = s => (s||'').trim().replace(/\s+/g, ' ');

  // Strategy 1: structured job cards / containers
  const cardSelectors = [
    '[class*="job-listing"]', '[class*="job-card"]', '[class*="job-result"]',
    '[class*="offer-card"]', '[class*="offre-listing"]', '[class*="offre-card"]',
    '[class*="position-card"]', '[class*="vacancy-card"]',
    '[class*="posting-card"]', '[class*="career-listing"]',
    '[class*="job-list"] > li', '[class*="offre-list"] > li',
    '[class*="search-result"]', '[class*="result-item"]',
    '[data-testid*="job"]', '[data-automation*="job"]',
    'article[class*="job"]', 'li[class*="job"]', 'tr[class*="job"]',
    '[class*="opportunity"] > [class*="item"]',
    'table[class*="job"] tr:not(:first-child)',
    '[class*="poste"]:not(nav *)',
  ];
  let cards = [];
  for (const sel of cardSelectors) {
    try { cards = document.querySelectorAll(sel); if (cards.length >= 2) break; }
    catch(e) { continue; }
  }
  if (cards.length >= 2) {
    cards.forEach(card => {
      const link = card.querySelector('a[href]');
      const titleEl = card.querySelector(
        '[class*="title" i], [class*="name" i], [class*="intitule" i], ' +
        'h2, h3, h4, [class*="heading"], [class*="header"]'
      );
      const title = norm(link?.textContent || titleEl?.textContent || card.textContent?.slice(0, 200) || '');
      const url = link?.href || '';
      const locEl = card.querySelector('[class*="location" i], [class*="lieu" i], [class*="localisation" i], [class*="place" i], [class*="ville" i]');
      const dateEl = card.querySelector('time, [class*="date" i], [class*="publi" i], [class*="posted" i], [datetime*="20"]');
      // Filter out navigation, headers, footers
      if (title && url && title.length > 5 && title.length < 300 && !seen.has(url)) {
        const inNav = card.closest('nav, header, footer, [role="navigation"]');
        if (!inNav) {
          seen.add(url);
          jobs.push({
            title: title,
            url: url,
            location: norm(locEl?.textContent || ''),
            date: norm(dateEl?.textContent || dateEl?.getAttribute('datetime') || ''),
            method: 'card'
          });
        }
      }
    });
  }

  // Strategy 2: direct links with job URL patterns (fallback)
  if (jobs.length < 2) {
    const jobLinkPattern = document.querySelectorAll(
      'a[href*="/job/"]:not(nav *):not(header *):not(footer *):not([role="navigation"] *), ' +
      'a[href*="/jobs/"]:not(nav *):not(header *):not(footer *):not([role="navigation"] *), ' +
      'a[href*="/offre"]:not(nav *):not(header *):not(footer *):not([role="navigation"] *), ' +
      'a[href*="/emploi"]:not(nav *):not(header *):not(footer *):not([role="navigation"] *), ' +
      'a[href*="/posting"]:not(nav *):not(header *):not(footer *):not([role="navigation"] *), ' +
      'a[href*="/position"]:not(nav *):not(header *):not(footer *):not([role="navigation"] *), ' +
      'a[href*="/vacancy"]:not(nav *):not(header *):not(footer *):not([role="navigation"] *), ' +
      'a[href*="/opportunity"]:not(nav *):not(header *):not(footer *):not([role="navigation"] *), ' +
      'a[href*="careers"]:not(nav *):not(header *):not(footer *):not([role="navigation"] *) > [class*="title"], ' +
      'a[class*="job"]:not(nav *):not(header *):not(footer *):not([role="navigation"] *), ' +
      'a[data-testid*="job"]:not(nav *):not(header *):not(footer *)'
    );
    jobLinkPattern.forEach(a => {
      const title = norm(a.textContent || a.getAttribute('aria-label') || '');
      const url = a.href;
      const parent = a.closest('[class*="job" i], [class*="offre" i], [class*="position" i], li, tr, [class*="row"], article');
      if (title && url && title.length > 5 && title.length < 300 && !seen.has(url)) {
        const locEl = parent ? parent.querySelector('[class*="location" i], [class*="lieu" i]') : null;
        seen.add(url);
        jobs.push({
          title: title,
          url: url,
          location: norm(locEl?.textContent || ''),
          date: '',
          method: 'link'
        });
      }
    });
  }

  // Strategy 3: WTJ-specific (select elements with data-testid)
  if (jobs.length < 2) {
    const wtjLinks = document.querySelectorAll('a[data-testid*="job-card"], a[href*="/fr/companies/"][href*="/jobs/"]');
    wtjLinks.forEach(a => {
      const title = norm(a.querySelector('[class*="title"]')?.textContent || a.textContent || '');
      const url = a.href;
      if (title && url && !seen.has(url) && title.length > 5) {
        seen.add(url);
        jobs.push({title, url, location: '', date: '', method: 'wtj'});
      }
    });
  }

  return jobs;
}
"""

# ── JS : Détecter le type de page + compter offres ──
PAGE_ANALYZE_OFFERS_JS = r"""
() => {
  const txt = (document.body ? document.body.innerText : '').slice(0, 30000).toLowerCase();
  const jobLinks = [...document.querySelectorAll(
    'a[href*="/job/"], a[href*="/jobs/"], a[href*="/offre"], a[href*="/emploi"], ' +
    'a[href*="/posting"], a[href*="/position"], a[href*="/vacancy"], ' +
    'a[href*="/opportunity"], a[href*="/careers/"]'
  )].filter(a => {
    const r = a.getBoundingClientRect();
    return r.width > 0 && r.height > 0;
  });
  const hasList = document.querySelector(
    '[class*="job-listing"], [class*="job-list"], [class*="job-result"], ' +
    '[class*="offre-list"], [class*="search-result"], ' +
    '[role="listbox"] [class*="option"], [data-testid*="job"]'
  );
  const careersTxt = ['carrière', 'career', 'jobs', 'offres', 'recrutement', 'postuler', 'apply'];
  const isCareers = careersTxt.some(k => txt.includes(k)) || txt.includes('carri') || txt.includes('nous rejoindre');
  const jobCount = jobLinks.length;
  const cards = document.querySelectorAll('[class*="job-card" i], [class*="offre-card" i]').length;
  return {
    isJobPage: jobCount >= 2 || cards >= 2 || !!hasList,
    isCareers: isCareers,
    jobLinks: jobCount,
    cards: cards,
    title: document.title
  };
}
"""


# ── robots.txt ───────────────────────────────────────────────────────────────
# Ce programme DEVINE des chemins : 14 candidats (/careers, /jobs, /recrutement…)
# sur 65 domaines. C'est exactement le comportement qu'un robots.txt sert a
# cadrer, et c'etait le seul collecteur a ne pas le lire — job_sources documente
# le sien site par site, avec la date de verification. Ici les domaines sont trop
# nombreux pour etre commentes a la main : on demande au serveur.
#
# Un robots.txt absent, illisible ou injoignable vaut AUTORISATION : c'est la
# regle usuelle, et l'inverse ferait disparaitre des sites en silence au premier
# incident reseau.
_ROBOTS_CACHE = {}
# On se nomme. Aucun site ne porte de regle « JobHunter » aujourd'hui, et
# robotparser retombe alors sur le bloc « User-agent: * » — celui qui nous
# gouverne. Mais si un site en ajoute une un jour, elle sera respectee, ce que
# demander « * » en dur n'aurait pas permis.
ROBOTS_UA = "JobHunter"


def robots_autorise(url: str) -> bool:
    """Le robots.txt de ce domaine autorise-t-il `url` ? Un cache par hote."""
    from urllib import robotparser
    from urllib.parse import urlsplit

    try:
        s = urlsplit(url)
        hote = f"{s.scheme}://{s.netloc}"
    except Exception:
        return True
    rp = _ROBOTS_CACHE.get(hote)
    if rp is None:
        rp = robotparser.RobotFileParser()
        rp.set_url(hote + "/robots.txt")
        try:
            rp.read()
        except Exception:
            rp = False  # injoignable : on n'y revient pas, et on passe
        _ROBOTS_CACHE[hote] = rp
    if rp is False:
        return True
    try:
        return rp.can_fetch(ROBOTS_UA, url)
    except Exception:
        return True


def load_domains(domains_path: str) -> list[dict]:
    """Charge les sites carrière depuis unique_domains.txt (65 hôtes distincts)."""
    entries = []
    for i, line in enumerate(Path(domains_path).read_text(encoding="utf-8").strip().split("\n")):
        line = line.strip()
        if not line:
            continue
        # Support both "N|URL" and bare URL formats
        num = i + 1
        if "|" in line:
            tete, url = line.split("|", 1)
            # HONORER LE NUMERO. Il etait lu puis jete, et chaque entree
            # renumerotee par sa position. `--domains wtj` ecrit un fichier
            # temporaire « N|url » avec les numeros d'origine : en le relisant,
            # le site 57 redevenait le site 1, et `--sites` combine a `--domains`
            # ne designait plus rien de ce que l'affichage annoncait.
            if tete.strip().isdigit():
                num = int(tete.strip())
        else:
            url = line
        url = url.strip()
        if not url.startswith("http"):
            continue
        domain = url.replace("https://", "").replace("http://", "").split("/")[0]
        entries.append({"num": num, "url": url.rstrip("/"), "domain": domain})
    return entries


def build_job_urls(entry: dict) -> list[str]:
    """Génère des URLs candidates pour trouver les offres d'emploi."""
    base = entry["url"]
    domain = entry["domain"]
    urls = [base]

    # ── ATS-specific URL patterns ──
    # SmartRecruiters: need company path
    if "smartrecruiters" in domain:
        # Try known companies on SmartRecruiters
        smart_companies = [
            "SycomoreAssetManagement",
            "BNPParibas",
            "AXA",
            "SocieteGenerale",
            "Natixis",
            "BNPParibas/GlobalMarkets",
        ]
        for comp in smart_companies:
            urls.append(f"https://careers.smartrecruiters.com/{comp}")
            urls.append(f"https://jobs.smartrecruiters.com/{comp}/jobs")
        return urls  # Only smartrecruiters URLs

    # WTJ: use search URLs directly
    if "welcometothejungle" in domain:
        wtj_searches = [
            "https://www.welcometothejungle.com/fr/jobs?q=esg&sort=mostRecent",
            "https://www.welcometothejungle.com/fr/jobs?q=analyste+esg&sort=mostRecent",
            "https://www.welcometothejungle.com/fr/jobs?q=finance+durable&sort=mostRecent",
            "https://www.welcometothejungle.com/fr/jobs?q=data&sort=mostRecent",
            "https://www.welcometothejungle.com/fr/jobs?q=risk&sort=mostRecent",
        ]
        urls.extend(wtj_searches)
        return urls  # Only WTJ search URLs

    # Breezy: use /jobs path
    if "breezy.hr" in domain:
        urls.append(base + "/jobs")
        return urls

    # TalentSoft: already has direct job pages
    if "talent-soft" in domain:
        urls.append(base + "/recherche")
        urls.append(base + "/offre-de-emploi")
        return urls

    # Générer des chemins carrière courants pour sites corporate
    careers_paths = [
        "/careers",
        "/careers/jobs",
        "/jobs",
        "/about/careers",
        "/carrieres",
        "/carrières",
        "/nous-rejoindre",
        "/recrutement",
        "/offres",
        "/offres-emploi",
        "/fr/careers",
        "/en/careers",
        "/job-search",
        "/search/jobs",
    ]

    # URLs existantes déjà carrière
    career_domains = {"jobs.", "careers.", "recrutement.", "talents.", "career."}
    if any(domain.startswith(p) for p in career_domains):
        urls.append(base + "/jobs")
        urls.append(base + "/search")
        urls.append(base + "/search/jobs")
    else:
        # Site corporate — ajouter les chemins carrière
        for p in careers_paths:
            urls.append(base + p)

    return urls


def extract_company_name(entry: dict) -> str:
    """Extrait un nom lisible d'entreprise depuis le domaine."""
    domain = entry["domain"]
    known = {
        "axa-im.com": "AXA IM",
        "jobs.smartrecruiters.com": "SmartRecruiters",
        "labanquepostale.fr": "La Banque Postale",
        "recrutement.bpce.fr": "BPCE",
        "rafp.fr": "RAFP",
        "careers.axa.com": "AXA",
        "dassault-aviation.com": "Dassault Aviation",
        "eiffage.com": "Eiffage",
        "rejoindre-ey.com": "EY",
        "careers.bpce.fr": "BPCE",
        "banquepopulaire.fr": "Banque Populaire",
        "credit-agricole.fr": "Crédit Agricole",
        # Ces deux-la ont change d'hote ; sans entree, le repli decoupait le
        # domaine et produisait « Rejoindre » et « Caissedesdepots-recrute ».
        "rejoindre.credit-agricole.com": "Crédit Agricole",
        "caissedesdepots-recrute.fr": "Caisse des Dépôts",
        "tikehaucapital.com": "Tikehau Capital",
        "eurazeo.com": "Eurazeo",
        "ey.com": "EY",
        "caissedesdepots.fr": "Caisse des Dépôts",
        "missionhandicap.fr": "Mission Handicap",
        "meeschaert.com": "Meeschaert",
        "welcometothejungle.com": "Welcome to the Jungle",
        "ca-cib.com": "Crédit Agricole CIB",
        "recrutement.natixis.com": "Natixis",
        "robeco.com": "Robeco",
        "dedale-intelligence.com": "Dédale Intelligence",
        "sipios.com": "Sipios",
        "glassdoor.fr": "Glassdoor",
        "careers.societegenerale.com": "Société Générale",
        "wizbii.com": "Wizbii",
        "efinancialcareers.fr": "eFinancialCareers",
        "jobs.careers.altios.com": "Altios",
        "group.pictet": "Pictet",
        "coveafinance-recrute.talent-soft.com": "Covéa Finance",
        "jobijoba.com": "Jobijoba",
        "carbon4finance.com": "Carbon4 Finance",
        "group.bnpparibas": "BNP Paribas",
        "ubs.com": "UBS",
        "im.natixis.com": "Natixis IM",
        "largilliere-finance.com": "Largillière Finance",
        "talents.bpifrance.fr": "Bpifrance",
        "carbon4finance.breezy.hr": "Carbon4 Finance",
        "karmen.breezy.hr": "Karmen",
        "engagement-jeunes.com": "Engagement Jeunes",
        "swissre.com": "Swiss Re",
        "jobs.amundi.com": "Amundi",
        "bain.com": "Bain & Company",
        "oliverwyman.com": "Oliver Wyman",
        "zurich.com": "Zurich",
        "swisslife-am.com": "Swiss Life AM",
        "careers.bnpparibas.com": "BNP Paribas",
        "ardian.com": "Ardian",
        "paipartners.com": "PAI Partners",
        "apax.com": "Apax",
        "carlyle.com": "Carlyle",
        "kkr.com": "KKR",
        "kearney.com": "Kearney",
        "quilvest.com": "Quilvest",
        "allianzgi.com": "Allianz GI",
        "mckinsey.com": "McKinsey",
        "bcg.com": "BCG",
        "sweep.net": "Sweep",
        "greenly.earth": "Greenly",
        "juliusbaer.com": "Julius Baer",
        "lombardodier.com": "Lombard Odier",
        "careers.lu.bnpparibas.com": "BNP Paribas Luxembourg",
        "candriam.com": "Candriam",
        "bgl.lu": "BGL BNP Paribas",
        "bil.com": "BIL",
        "linkfinance.fr": "Link Finance",
        "apec.fr": "APEC",
    }
    # SUR UNE FRONTIERE DE LABEL, pas n'importe ou dans la chaine. `k in domain`
    # traitait le domaine comme du texte : « ey.com » est une sous-chaine de
    # « mckins-ey.com » et de « kearn-ey.com », et les offres de McKinsey comme
    # celles de Kearney entraient dans la file au nom d'EY — mauvaise societe sur
    # le CV, la lettre et le suivi. Un nom de domaine se lit par labels separes
    # par des points : on exige donc que la cle soit le domaine, ou qu'elle le
    # termine apres un point.
    d = domain.lower()
    # les cles les plus longues d'abord : « careers.bpce.fr » doit gagner sur
    # « bpce.fr », sinon l'ordre du dictionnaire decide au hasard.
    for k, v in sorted(known.items(), key=lambda kv: -len(kv[0])):
        kl = k.lower()
        if d == kl or d.endswith("." + kl):
            return v
    # Fallback: extraire du domaine
    parts = domain.replace("www.", "").split(".")
    if parts[0] in ("jobs", "careers", "recrutement", "talents", "career"):
        return parts[1].capitalize() if len(parts) > 2 else parts[0].capitalize()
    return parts[0].capitalize()


def offre_retenue(titre: str) -> bool:
    """LE filtre d'entrée : lexique large + mot métier + pas de rôle hors-cible.

    `matches_esg_finance` etait le seul filtre de ce programme. Comme « h/f »
    est dans son lexique et que presque toute annonce francaise le porte, il
    laissait passer boucher, plombier et serveur. `title_ok` corrige ca depuis
    juillet dans job_sources, mais n'avait jamais ete branche ici.

    Import TARDIF : la collecte est lourde a charger, et inutile a qui
    n'appelle pas ce filtre.
    Repli sur le tamis large si job_sources est indisponible — mieux vaut trop
    d'offres que pas de scan du tout.
    """
    if not titre:
        return False
    try:
        from jobhunter.sources.commun import title_ok
    except Exception:
        return matches_esg_finance(titre)
    return title_ok(titre)


def scrape_site(page, entry: dict, timeout_ms: int = 20000) -> list[dict]:
    """Scrape un site pour en extraire les offres d'emploi."""
    import httpx

    site_name = extract_company_name(entry)
    offers = []
    candidate_urls = build_job_urls(entry)
    domain = entry["domain"]

    # ── SmartRecruiters API-based extraction ──
    if "smartrecruiters" in domain:
        # Try SmartRecruiters public API for known companies
        smart_companies_api = [
            ("Sycomore Asset Management", "SycomoreAssetManagement"),
            ("AXA", "AXA"),
            ("BNP Paribas", "BNPParibas"),
            ("Societe Generale", "SocieteGenerale"),
            ("Natixis", "Natixis"),
        ]
        for company_name, slug in smart_companies_api:
            try:
                api_url = f"https://api.smartrecruiters.com/v1/companies/{slug}/postings?limit=50"
                resp = httpx.get(api_url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
                if resp.status_code == 200:
                    data = resp.json()
                    for job in data.get("content", []):
                        title = job.get("name", "")
                        job_url = f"https://jobs.smartrecruiters.com/{slug}/{job.get('id', '')}"
                        if title and offre_retenue(title):
                            offers.append(
                                {
                                    "titre": title,
                                    "url": job_url,
                                    "entreprise": company_name,
                                    "domaine": classify_domaine(title),
                                    "location": job.get("location", {}).get("city", ""),
                                    "date": job.get("publicationDate", ""),
                                    "source": entry["url"],
                                    "scraped_at": time.strftime(
                                        "%Y-%m-%dT%H:%M:%SZ", time.gmtime()
                                    ),
                                }
                            )
                    print(
                        f"  ✓ {len([x for x in data.get('content', []) if offre_retenue(x.get('name', ''))])} offres ESG/Finance sur {company_name} (API SmartRecruiters)"
                    )
                else:
                    print(f"  ~ API SmartRecruiters {slug}: HTTP {resp.status_code}")
            except Exception as e:
                print(f"  ~ API SmartRecruiters {slug}: {type(e).__name__}")
        if offers:
            return offers

    # ── WTJ: Use company pages (more reliable than search) ──
    if "welcometothejungle" in domain:
        # WTJ company pages (known ESG/Finance companies)
        wtj_companies = [
            "axa",
            "ey",
            "bnp-paribas",
            "societe-generale",
            "credit-agricole",
            "natixis",
            "amundi",
            "caisse-des-depots",
            "bpce",
            "banque-populaire",
            "robeco",
            "candriam",
            "allianz",
            "swiss-life",
            "pictet",
            "bpi-france",
            "eurazeo",
            "tikehau-capital",
            "ardian",
            "oliver-wyman",
            "bain-and-company",
            "mckinsey",
            "bcg",
            "deloitte",
            "kpmg",
            "pwc",
            "kearney",
        ]
        for slug in wtj_companies:
            company_url = f"https://www.welcometothejungle.com/fr/companies/{slug}/jobs"
            total_before = len(offers)
            try:
                page.goto(company_url, timeout=timeout_ms, wait_until="domcontentloaded")
                time.sleep(2)

                # Dismiss cookies
                try:
                    from web_nav import COOKIE_JS

                    page.evaluate(COOKIE_JS)
                    time.sleep(0.5)
                except Exception:
                    pass

                # Wait for job content
                page.wait_for_timeout(3000)

                # Extract jobs using console API
                wtj_extract_js = r"""
                () => {
                    const jobs = [];
                    const seen = new Set();
                    // WTJ job cards on company pages
                    const links = document.querySelectorAll(
                        'a[href*="/fr/companies/"][href*="/jobs/"]'
                    );
                    links.forEach(a => {
                        const title = (a.textContent || '').trim();
                        const url = a.href;
                        if (title && url && title.length > 5 && !seen.has(url)) {
                            // Find location
                            const container = a.closest('[class*="card"]') || a.parentElement;
                            const loc = container?.querySelector('[class*="location"]')?.textContent?.trim() || '';
                            seen.add(url);
                            jobs.push({title, url, location: loc, date: '', method: 'wtj-company'});
                        }
                    });
                    return jobs;
                }
                """
                js_offers = page.evaluate(wtj_extract_js)
                for o in js_offers:
                    title = o.get("title", "").strip()
                    lien = o.get("url", "").strip()
                    if title and lien and offre_retenue(title):
                        offers.append(
                            {
                                "titre": title,
                                "url": lien,
                                "entreprise": slug.replace("-", " ").title(),
                                "domaine": classify_domaine(title),
                                "location": o.get("location", ""),
                                "date": o.get("date", ""),
                                "source": entry["url"],
                                "scraped_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                            }
                        )
                offer_count = len(offers) - total_before
                total_count = len(js_offers)
                print(f"  ~ {slug}: {total_count} offres, {offer_count} ESG/Finance")
            except Exception as e:
                print(f"  ~ WTJ {slug}: {type(e).__name__}")
                continue
        return offers

    # ── Breezy: browser-based extraction ──
    if "breezy.hr" in domain:
        for url in candidate_urls:
            try:
                page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")
                time.sleep(2)
                try:
                    from web_nav import COOKIE_JS

                    page.evaluate(COOKIE_JS)
                except Exception:
                    pass
                page.wait_for_timeout(2000)
                js_offers = page.evaluate(EXTRACT_OFFERS_JS)
                for o in js_offers:
                    title = o.get("title", "").strip()
                    lien = o.get("url", "").strip()
                    if title and lien and offre_retenue(title):
                        offers.append(
                            {
                                "titre": title,
                                "url": lien,
                                "entreprise": site_name,
                                "domaine": classify_domaine(title),
                                "location": o.get("location", ""),
                                "date": o.get("date", ""),
                                "source": entry["url"],
                                "scraped_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                            }
                        )
                if offers:
                    print(f"  ✓ {len(offers)} offres ESG/Finance Breezy")
                    break
            except Exception as e:
                print(f"  ! Breezy {url}: {type(e).__name__}")
                continue
        return offers

    # ── TalentSoft: API-based extraction ──
    if "talent-soft" in domain:
        try:
            # Use httpx to fetch JSON data from TalentSoft API
            for url in candidate_urls:
                try:
                    page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")
                    time.sleep(2)
                    try:
                        from web_nav import COOKIE_JS

                        page.evaluate(COOKIE_JS)
                    except Exception:
                        pass
                    page.wait_for_timeout(2000)

                    # Extract offers from page (TalentSoft renders jobs server-side)
                    js_offers = page.evaluate(EXTRACT_OFFERS_JS)
                    for o in js_offers:
                        title = o.get("title", "").strip()
                        lien = o.get("url", "").strip()
                        if title and lien and offre_retenue(title):
                            offers.append(
                                {
                                    "titre": title,
                                    "url": lien,
                                    "entreprise": site_name,
                                    "domaine": classify_domaine(title),
                                    "location": o.get("location", ""),
                                    "date": o.get("date", ""),
                                    "source": entry["url"],
                                    "scraped_at": time.strftime(
                                        "%Y-%m-%dT%H:%M:%SZ", time.gmtime()
                                    ),
                                }
                            )
                    if offers:
                        print(f"  ✓ {len(offers)} offres ESG/Finance TalentSoft")
                        break
                except Exception as e:
                    continue
        except Exception as e:
            print(f"  ! TalentSoft: {e}")
        return offers

    # ── Generic scraper for corporate sites ──
    visited = set()
    for url in candidate_urls:
        if url in visited:
            continue
        visited.add(url)
        # Chemin DEVINE : c'est ici que robots.txt compte le plus. Un site peut
        # ouvrir sa racine et fermer /search ou /job-search — on ne l'apprend
        # qu'en le lisant. Le cache rend ce test gratuit apres le 1er appel.
        if not robots_autorise(url):
            continue
        try:
            # Navigation
            page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")
            time.sleep(random.uniform(1.0, 2.5))

            # Cookie dismiss (via web_nav.COOKIE_JS si dispo)
            try:
                from web_nav import COOKIE_JS

                page.evaluate(COOKIE_JS)
                time.sleep(0.5)
            except Exception:
                pass

            # Analyser la page
            info = page.evaluate(PAGE_ANALYZE_OFFERS_JS)
            if info.get("isJobPage") or info.get("jobLinks", 0) >= 2 or info.get("cards", 0) >= 2:
                # Try standard extraction
                js_offers = page.evaluate(EXTRACT_OFFERS_JS)
                if js_offers:
                    print(f"  ~ {len(js_offers)} offres brutes sur {url.split('/')[2]}")
                for o in js_offers:
                    title = o.get("title", "").strip()
                    lien = o.get("url", "").strip()
                    if title and lien and offre_retenue(title):
                        offers.append(
                            {
                                "titre": title,
                                "url": lien,
                                "entreprise": site_name,
                                "domaine": classify_domaine(title),
                                "location": o.get("location", ""),
                                "date": o.get("date", ""),
                                "source": entry["url"],
                                "scraped_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                            }
                        )
                if offers:
                    print(f"  ✓ {len(offers)} offres ESG/Finance trouvées sur {url.split('/')[2]}")
                    break  # Found offers on this URL, stop trying others
            else:
                job_links = info.get("jobLinks", 0)
                if job_links > 0:
                    pass  # Some links found but not enough to qualify as job page
        except Exception as e:
            continue

    # ── Fallback: try to find careers section from homepage ──
    if not offers:
        try:
            from web_nav import goto_careers

            page.goto(entry["url"], timeout=timeout_ms, wait_until="domcontentloaded")
            time.sleep(1)
            try:
                from web_nav import COOKIE_JS

                page.evaluate(COOKIE_JS)
            except Exception:
                pass
            careers = goto_careers(page)
            if careers.get("clicked"):
                print(f"  🧭 Carrières trouvées: {careers.get('label', '?')}")
                time.sleep(2)
                js_offers = page.evaluate(EXTRACT_OFFERS_JS)
                for o in js_offers:
                    title = o.get("title", "").strip()
                    lien = o.get("url", "").strip()
                    if title and lien and offre_retenue(title):
                        offers.append(
                            {
                                "titre": title,
                                "url": lien,
                                "entreprise": site_name,
                                "domaine": classify_domaine(title),
                                "location": o.get("location", ""),
                                "date": o.get("date", ""),
                                "source": entry["url"],
                                "scraped_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                            }
                        )
                if offers:
                    print(f"  ✓ {len(offers)} offres ESG/Finance (via careers)")
        except Exception as e:
            pass

    return offers


def scrape_all_sites(
    domains_file: str,
    output_file: str,
    headless: bool = True,
    stealth: bool = False,
    site_range: tuple = None,
    skip: int = 0,
    max_sites: int = 0,
):
    """Scrape tous les sites et sauvegarde les offres fraîches."""
    entries = load_domains(domains_file)
    print(f"📋 {len(entries)} sites chargés depuis {domains_file}")

    if site_range:
        start, end = site_range
        entries = [e for e in entries if start <= e["num"] <= end]
        print(f"🔍 Filtre sites {start}–{end} → {len(entries)} sites")
    if skip:
        entries = entries[skip:]
        print(f"⏩ Skip {skip} → démarre au site #{entries[0]['num']}")
    if max_sites:
        entries = entries[:max_sites]
        print(f"🔢 Max {max_sites} sites")

    all_offers = []

    # Load existing offers if resuming
    output_path = Path(output_file)
    if output_path.exists() and skip > 0:
        try:
            existing = json.loads(output_path.read_text(encoding="utf-8"))
            all_offers = existing
            print(f"📂 Repris {len(all_offers)} offres existantes")
        except Exception:
            pass

    # Choisir le moteur
    # Playwright standard, navigateur annonce comme automatise : aucun
    # deguisement (moteur furtif, faux user-agent, navigator.webdriver masque).
    from playwright.sync_api import sync_playwright

    engine = "playwright"

    print(f"🚀 Moteur: {engine} (headless={headless})")
    print("=" * 70)

    with sync_playwright() as p:
        browser_type = p.chromium
        browser = browser_type.launch(headless=headless)
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()
        # TURBO : bloque images/polices/pubs → scan 2-5× plus rapide (texte suffit)
        try:
            from web_nav import block_resources

            block_resources(context, images=False)
        except Exception:
            pass

        total_offers = 0
        try:
            for i, entry in enumerate(entries):
                site_name = extract_company_name(entry)
                print(f"\n[{entry['num']}/{i + 1}/{len(entries)}] {site_name} — {entry['url']}")
                if not robots_autorise(entry["url"]):
                    print(f"  🚫 robots.txt interdit le scan de {entry['domain']} — ignoré")
                    continue
                try:
                    offers = scrape_site(page, entry)
                    if offers:
                        total_offers += len(offers)
                        all_offers.extend(offers)
                        # Sauvegarde progressive. jwrite ecrit a cote puis
                        # bascule : un write_text direct laissait un fichier
                        # tronque si le scan mourait pendant l'ecriture, et
                        # c'est le fichier de REPRISE (--skip) qu'on perdait.
                        __import__("jutil").jwrite(output_path, all_offers)
                        print(f"  ✅ {len(offers)} offres ESG/Finance — total: {total_offers}")
                    else:
                        print("  ⚠️ Aucune offre ESG/Finance trouvée")
                except Exception as e:
                    print(f"  ❌ Erreur site: {type(e).__name__}: {str(e)[:100]}")
                # Pause entre les sites
                time.sleep(random.uniform(1.0, 3.0))
        finally:
            # Ctrl-C ou plantage : sans ce finally, le Chromium restait en vie
            # et un scan relance en empilait un de plus a chaque fois.
            try:
                browser.close()
            except Exception:
                pass

    # Sauvegarde finale
    # Déduplication
    seen_urls = set()
    unique_offers = []
    for o in all_offers:
        u = o.get("url", "")
        if u not in seen_urls:
            seen_urls.add(u)
            unique_offers.append(o)

    __import__("jutil").jwrite(output_path, unique_offers)

    # Stats
    domaines = {}
    entreprises = {}
    for o in unique_offers:
        d = o.get("domaine", "unknown")
        domaines[d] = domaines.get(d, 0) + 1
        e = o.get("entreprise", "?")
        entreprises[e] = entreprises.get(e, 0) + 1

    print("\n" + "=" * 70)
    print("✅ SCRAPING TERMINÉ")
    print(f"📊 {len(unique_offers)} offres uniques (sur {len(all_offers)} total brut)")
    print(f"🏢 {len(entreprises)} entreprises avec offres")
    print("\n📈 Par domaine:")
    for d, c in sorted(domaines.items(), key=lambda x: -x[1]):
        print(f"   {d}: {c}")
    print(f"\n📁 Sauvegardé: {output_path.resolve()}")
    return unique_offers


def merger(offres, dry=False):
    """Fait entrer la récolte dans apply_queue.json.

    SANS CECI, LE PROGRAMME NE SERT A RIEN. Il ecrivait `offres_fraiches.json`,
    qu'AUCUN autre programme ne lisait : les sites carriere etaient scrapes
    depuis des mois et leurs offres n'atteignaient jamais la file. Le probleme
    avait ete repere (00_MASTER, 12/07) et regle une fois A LA MAIN — jamais en
    code. Le bouton « Scrape les sites » de l'app tournait donc dans le vide.

    On passe par `job_sources.merge_into_queue` plutot que d'ecrire la file
    ici : c'est lui qui tient la deduplication, l'arbitrage de source, le filtre
    geographique, les exclusions et le scoring. Le format produit par
    `scrape_site` est deja le sien (titre/url/entreprise/domaine/location/date).
    """
    if not offres:
        print("→ rien à fusionner.")
        return None
    from job_sources import merge_into_queue

    r = merge_into_queue(offres, dry=dry)
    print(
        f"\n🔗 Merge {'[DRY] ' if dry else ''}: +{r['added']} nouvelles, "
        f"{r['updated']} enrichies, {r['promus']} liens promus, "
        f"{r['hors_zone']} hors de France, {r['ecartees']} écartées à la main, "
        f"{r['purged']} bruits purgés — {r['total']} offres en file"
    )
    return r


def main():
    parser = argparse.ArgumentParser(
        description="Scrape les offres fraîches des sites carrière ESG/Finance"
    )
    parser.add_argument("--sites", type=str, default=None, help="Plage de sites ex: 1-10, 20-30")
    parser.add_argument(
        "--domains",
        type=str,
        default=None,
        help="Filtre par nom de domaine (séparé par des virgules)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="offres_fraiches.json",
        help="Fichier de sortie (défaut: offres_fraiches.json)",
    )
    parser.add_argument(
        "--headless", action="store_true", default=True, help="Mode headless (pas de fenêtre)"
    )
    parser.add_argument(
        "--no-headless",
        action="store_false",
        dest="headless",
        help="Afficher la fenêtre du navigateur",
    )
    # Le mode furtif est retire ; les deux options restent acceptees, sans effet.
    parser.add_argument("--stealth", action="store_true", help="sans effet (retire)")
    parser.add_argument("--no-stealth", action="store_false", dest="stealth", help="sans effet")
    parser.add_argument("--skip", type=int, default=0, help="Nombre de sites à sauter (reprise)")
    parser.add_argument("--max", type=int, default=0, help="Nombre max de sites à scraper")
    parser.add_argument(
        "--domains-file", type=str, default=None, help="Chemin vers unique_domains.txt"
    )
    parser.add_argument(
        "--no-merge",
        action="store_false",
        dest="merge",
        help="Scraper sans faire entrer les offres dans la file",
    )
    parser.add_argument(
        "--dry", action="store_true", help="Montre ce que le merge ferait, sans écrire la file"
    )
    args = parser.parse_args()

    # Déterminer le chemin du fichier domaines
    scripts_dir = Path(__file__).resolve().parent
    if args.domains_file:
        domains_file = Path(args.domains_file)
    else:
        # Chercher dans Scripts/ ou parent
        candidates = [
            scripts_dir / "unique_domains.txt",
            scripts_dir.parent / "Scripts" / "unique_domains.txt",
        ]
        domains_file = None
        for c in candidates:
            if c.exists():
                domains_file = c
                break
        if not domains_file:
            print("❌ unique_domains.txt introuvable")
            sys.exit(1)

    # Plage de sites
    site_range = None
    if args.sites:
        try:
            parts = args.sites.split("-")
            site_range = (int(parts[0]), int(parts[1]))
        except (ValueError, IndexError):
            print(f"❌ Format plage invalide: {args.sites} (ex: 1-10)")
            sys.exit(1)

    # Filtre domaines
    if args.domains:
        filters = [d.strip().lower() for d in args.domains.split(",")]
        entries = load_domains(str(domains_file))
        entries = [
            e
            for e in entries
            if any(f in e["domain"].lower() or f in e["url"].lower() for f in filters)
        ]
        print(f"🔍 Filtre domaines: {args.domains} → {len(entries)} sites")
        if not entries:
            print("❌ Aucun site trouvé")
            sys.exit(1)
        # Sauvegarde temporaire pour le scraper
        temp_domains = scripts_dir / "_temp_filtered_domains.txt"
        temp_domains.write_text(
            "\n".join(f"{e['num']}|{e['url']}" for e in entries), encoding="utf-8"
        )
        domains_file = temp_domains

    max_sites = args.max or 0
    if args.domains and args.max == 0:
        max_sites = 0  # no limit when filtering by domain

    output_path = scripts_dir / args.output

    offres = scrape_all_sites(
        domains_file=str(domains_file),
        output_file=str(output_path),
        headless=args.headless,
        stealth=args.stealth,
        site_range=site_range,
        skip=args.skip,
        max_sites=max_sites,
    )

    # Nettoyer fichier temporaire
    temp_file = scripts_dir / "_temp_filtered_domains.txt"
    if temp_file.exists():
        temp_file.unlink()

    if args.merge:
        merger(offres, dry=args.dry)


if __name__ == "__main__":
    main()
