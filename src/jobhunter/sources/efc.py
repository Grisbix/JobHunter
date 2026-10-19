"""eFinancialCareers: the public sitemap declared in robots.txt.

Part of jobhunter.sources (formerly Scripts/job_sources.py, phase 3.4).
"""

import json
import re
import time
from typing import Any
from urllib.parse import unquote, urlparse

from jobhunter import journal as _journal
from jobhunter.sources import commun as _commun
from jobhunter.sources.commun import (
    INCIDENTS,
    _mk,
    _norm_url,
    _strip_html,
    contrat_du_titre,
    en_france,
    title_ok,
)

_log = _journal.journal(__name__)


# ═══════════════ 8. eFinancialCareers — PUBLIC sitemap declared in robots.txt ═══
# WHY. A 100 % finance job site, French, exactly the user's market.
# It was already known to _SITES_EMPLOI (rank 2) but NEVER scanned: the 5 entries
# in the queue were category pages picked up elsewhere, without description.
#
# WHAT robots.txt ALLOWS (checked on 2026-09-04). `/search` is forbidden to
# `User-agent: *` — we do not touch it. On the other hand the file itself DECLARES
# the sitemap of recent offers:
#     Sitemap: https://www.efinancialcareers.fr/sitemap-secure/latestjobs/xml
# It is the access path the site publishes to be indexed: 8100 offers, and
# the offer pages are not forbidden. `crawl-delay: 10` is respected.
#
# Each posting carries a <script type="application/ld+json"> of type JobPosting
# with title, company, place, date and full description (~10,000 chars).
EFC_SITEMAP = "https://www.efinancialcareers.fr/sitemap-secure/latestjobs/xml"

EFC_DELAI = 10  # crawl-delay announced by robots.txt — do not lower

# THE OTHER SITES OF THE SAME PUBLISHER (checked on 2026-09-24): same robots.txt,
# same declared sitemap, same crawl-delay 10, same ld+json. 48,000 more
# offers, including 93 ESG titles missing from the queue. Only the .fr was read.
EFC_SITES = ("fr", "com", "co.uk", "de", "ch", "nl", "lu", "ie", "sg")


def _efc_sitemap(site: str) -> str:
    return f"https://www.efinancialcareers.{site}/sitemap-secure/latestjobs/xml"


EFC_UA = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    )
}

# The URLs have the form /emploi-<Country>-<City>-<Title>.id<N>. The city may
# contain hyphens ("Levallois-Perret"), so we do NOT try to
# separate it from the title: splitting at the first hyphen gave city "Levallois" and
# title "Perret-Responsable Projets IA". The city+title block only serves the
# PRE-FILTER; the exact fields come from the posting's ld+json.
_RX_EFC_SLUG = re.compile(r"/(?:emploi|jobs)-[^-]+-(.+)\.id(\d+)$")

# Strict ESG filter. `responsab` was removed after measurement: it let in
# 581 titles, almost all of them unrelated "Responsable …".
#
# The \b are ESSENTIAL: without them "RSE" matches any word that
# contains these three letters. Same family of bug as _TITRE_CONTRAT and
# _RX_STAGE, where a \b lost while writing had made the pattern inoperative.
# "climat" explicitly excludes "climatisation": two technician jobs
# in Air-conditioning zones came up in the measurement.
_RX_EFC_ESG = re.compile(
    r"\bESG\b|\bRSE\b|\bSFDR\b|\bCSRD\b|extra.?financi|durabilit"
    r"|d[ée]veloppement durable|sustainab|climat(?!isation)|carbone|taxonomie"
    r"|impact invest|finance verte|green finance|transition [ée]nerg"
    r"|stewardship|responsible invest|net.zero|biodiversit",
    re.I,
)

# Programmes jeunes diplomes.
_RX_EFC_GRAD = re.compile(
    r"\bgraduate\b|jeune[s]? dipl|\bearly career\b|trainee program"
    r"|young (?:graduate|talent)",
    re.I,
)

# The V.I.E is searched WITHOUT re.I, and that is essential: case-insensitive "vie"
# lets in all of life insurance ("assurance vie"), which weighs heavily on a site
# finance (« Gestionnaire Assurance Vie », « Middle office Assurance Vie »…).
# In capitals, the acronym is not confused with anything.
_RX_EFC_VIE = re.compile(r"\bV\.?I\.?E\b")


def _est_graduate(titre: str) -> bool:
    """Graduate programme or V.I.E?"""
    return bool(_RX_EFC_GRAD.search(titre) or _RX_EFC_VIE.search(titre))


# ── THE FILTER BY PROFESSION, and why not by sector ──────────────────────
#
# eFinancialCareers IS the job site of banking and asset
# management: 8478 offers in the sitemap, only 32 of which were in the queue. It is
# by far the biggest untapped source, and it is penalised
# (sitemap declare, crawl-delay 10 s).
#
# First try: filter by SECTOR. Failure — the sitemap slug only carries
# the title, not the employer. "power" found "Power Platform" there,
# "energie" found "Consultant transformation numerique Energie". We
# brought back consulting assignments, not jobs at an energy company.
#
# So we filter on the user's PROFESSION. Measurement of 17/09 on the 8478:
#   7208 hors metier, 217 contrat exclu, 184 trop senior, 869 A LIRE.
#
# 869 postings at 10 s make 144 minutes. No need to keep a rotation index:
# scan_efc already sets aside the URLs present in the queue, so each pass moves
# on by itself through the rest.
_RX_EFC_METIER = re.compile(
    r"analyst|analyste|contr[oô]le de gestion|controlling|FP&A"
    r"|gestion de portefeuille|g[eé]rant|risk|risque|cr[eé]dit|credit"
    r"|valoris|valuation|M&A|corporate finance|private equity"
    r"|\bESG\b|\bISR\b|\bRSE\b|extra.?financ|durab|climat(?!isation)|carbon"
    r"|\bCSRD\b|\bSFDR\b|graduate|jeune dipl|junior|reporting",
    re.I,
)

# Jobs out of reach of a fresh-graduate profile. Set them aside BEFORE paying
# 10 s of reading: it is the cheapest sort we can make.
_RX_EFC_SENIOR = re.compile(
    r"senior|directeur|director|head of|responsable|manager|principal"
    r"|associate director|\bVP\b|expert|chef de",
    re.I,
)


def _est_metier(titre: str) -> bool:
    """Title compatible with the profile, and not already too senior?"""
    return bool(_RX_EFC_METIER.search(titre)) and not _RX_EFC_SENIOR.search(titre)


def _efc_urls(client: Any, site: str = "fr") -> list[tuple[Any, str]]:
    """(url, approximate title) of each offer of the sitemap. A single request."""
    r = _commun._get_borne(client, _efc_sitemap(site), headers=EFC_UA, timeout=60)
    if r.status_code != 200:
        _log.info(f"  ~ eFC .{site} : sitemap injoignable (statut {r.status_code})")
        INCIDENTS[f"efc:{site}"][f"HTTP {r.status_code}"] += 1
        return []
    out = []
    for loc in re.findall(r"<loc>([^<]+)</loc>", r.text):
        m = _RX_EFC_SLUG.search(loc)
        if m:
            out.append((loc, unquote(m.group(1)).replace("_", " ").strip()))
    return out


def _efc_fiche(url: str, client: Any) -> dict[str, Any] | None:
    """JobPosting of the posting, or None. Never raises."""
    try:
        r = _commun._get_borne(client, url, headers=EFC_UA, timeout=30)
    except Exception:
        return None
    if r.status_code != 200:
        return None
    for bloc in re.findall(
        r'<script type="application/ld\+json"[^>]*>(.*?)</script>', r.text, re.S
    ):
        try:
            o = json.loads(bloc)
        except Exception:
            continue
        if isinstance(o, dict) and o.get("@type") == "JobPosting":
            return o
    return None


def _efc_lieu(jp: Any) -> str:
    """City of the JobPosting. jobLocation may be an object or a list."""
    loc = jp.get("jobLocation")
    if isinstance(loc, list):
        loc = loc[0] if loc else None
    if not isinstance(loc, dict):
        return ""
    ad = loc.get("address") or {}
    return " ".join(
        str(ad.get(k) or "") for k in ("addressLocality", "addressRegion", "addressCountry")
    ).strip()


def scan_efc(
    limit: int = 40, filtre: str = "esg", sites: tuple[str, ...] = ("fr",)
) -> list[dict[str, Any]]:
    """EFinancialCareers offers, description included.

    filtre:
      "esg"      — titles that talk about ESG (43 out of 8100);
      "graduate" — graduate programmes and V.I.E;
      "metier"   — the titles compatible with the profile, seniors set aside:
                   869 out of 8478 in the measurement of 17/09. It is the deposit of
                   banks and asset management, eFC being their job
                   site. Each pass moves on through the rest, the URLs already
                   in the queue being set aside;
      "tout"     — everything title_ok keeps, i.e. ~2400 titles: at 10 s per
                   posting that is almost 7 h, for a fit computed on generic
                   banking jobs.
    """
    import httpx

    _EX = _commun.contrats_exclus()
    offers = []
    with httpx.Client(follow_redirects=True) as client:
        # An offer published on two sites carries the same identifier: we only
        # read it once.
        toutes, ids = [], set()
        for i, site in enumerate(sites):
            if i:
                time.sleep(EFC_DELAI)  # crawl-delay, sitemaps compris
            for url, approx in _efc_urls(client, site):
                m = _RX_EFC_SLUG.search(url)
                if m and m.group(2) in ids:
                    continue
                if m:
                    ids.add(m.group(2))
                toutes.append((url, approx))
        cibles = []
        for url, approx in toutes:
            if contrat_du_titre(approx) in _EX:
                continue
            if filtre == "esg":
                if not _RX_EFC_ESG.search(approx):
                    continue
            elif filtre == "graduate":
                if not _est_graduate(approx):
                    continue
            elif filtre == "metier":
                if not _est_metier(approx):
                    continue
            elif not title_ok(approx):
                continue
            cibles.append(url)
        # Postings ALREADY in the queue: do not read them again. At 10 s each, a second
        # pass paid again the whole time of the first only to bring what
        # merge_into_queue aurait de toute facon deduplique.
        from jobhunter.stockage import file as queue_io

        connues = {_norm_url(x.get("url")) for x in queue_io.charger(_commun.QUEUE) if x.get("url")}
        neuves = [u for u in cibles if _norm_url(u) not in connues]
        deja = len(cibles) - len(neuves)
        # IN TURN between the sites. Taken in the order of the sitemaps, the
        # `limit` places all went to the .fr, read first: in the trial, 8
        # postings out of 8 were in Paris and abroad was never reached.
        par_site: dict[str, Any] = {}
        for u in neuves:
            par_site.setdefault(urlparse(u).netloc, []).append(u)
        alterne = []
        while any(par_site.values()):
            for lst in par_site.values():
                if lst:
                    alterne.append(lst.pop(0))
        cibles = alterne[:limit]
        _log.info(
            f"  eFC : {len(toutes)} offres au sitemap → {len(cibles)} a lire "
            f"({deja} deja en file) "
            f"({EFC_DELAI} s entre chaque, {len(cibles) * EFC_DELAI // 60} min)"
        )
        for n, url in enumerate(cibles, 1):
            if n > 1:
                time.sleep(EFC_DELAI)  # crawl-delay: 10
            jp = _efc_fiche(url, client)
            if not jp:
                continue
            # The ld+json carries HTML entities in the title: without unescape,
            # "Originateur &laquo; Sustainable banking" ended up as is in
            # the subject of the letter. _strip_html only applies to the description.
            titre = __import__("html").unescape(str(jp.get("title") or ""))
            # eFC suffixes the title with the place and the work mode:
            # "… | Paris, FR | Hybride". We only keep the title.
            titre = re.sub(r"\s*\|.*$", "", titre).strip()
            lieu = _efc_lieu(jp)
            # The exact title of the ld+json is more reliable than the slug: we redo
            # both filters on it before keeping the offer.
            if not titre or not title_ok(titre) or contrat_du_titre(titre) in _EX:
                continue
            if not en_france(lieu):
                continue
            soc = (jp.get("hiringOrganization") or {}).get("name") or "eFinancialCareers"
            offers.append(
                _mk(
                    titre,
                    url,
                    soc,
                    lieu,
                    str(jp.get("datePosted") or "")[:10],
                    "efinancialcareers",
                    _strip_html(str(jp.get("description") or "")),
                )
            )
            if n % 10 == 0:
                _log.info(f"    … {n}/{len(cibles)} ({len(offers)} retenues)")
    _log.info(f"  ✓ eFinancialCareers → {len(offers)} offres (avec description)")
    return offers
