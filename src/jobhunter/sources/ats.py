"""Readers of the public ATS APIs (Greenhouse, Lever, Ashby...) and of the other recruiting APIs.

Part of jobhunter.sources (formerly Scripts/job_sources.py, phase 3.4).
"""

import datetime
import html
import json
import re
import time
from typing import Any
from urllib.parse import quote, unquote, urlparse

from jobhunter import log as _journal
from jobhunter.sources import common as _commun
from jobhunter.sources import workday as _workday
from jobhunter.sources.common import INCIDENTS, UA, _mk, _strip_html, title_ok

_log = _journal.journal(__name__)


# ═══════════════ 1. ATS APIs (pure httpx, no browser) — WITH descriptions ═══════════════
def _ats_ko(kind: str, slug: str, r: Any) -> bool:
    """Unusable response? And if so, should it be a concern?

    404: the slug does not exist at this ATS. It is the NORMAL case — the list is
    deliberately wide, we probe companies that are not there. Silence.
    Everything else (429 quota, 5xx failure) is a refusal: the company may have
    offers, we did not see them. It is counted, otherwise an entirely throttled scan
    looks like a scan with nothing new.
    """
    if r.status_code == 200:
        return False
    if r.status_code != 404:
        INCIDENTS[f"ats:{kind}"][f"HTTP {r.status_code}"] += 1
    return True


# The name of an ATS account is not the company's: `slug.title()` gave
# "Grantthornton", "Societegenerale", "Vestiairecollective". A badly named
# company escapes the sorting by company, the duplicate check with LinkedIn and any
# search (2026-10-08: Roland Berger "absent", 34 offers under
# "rolandberger"). The slugs missing from here keep `slug.title()`.
ATS_NOMS = {
    "backmarket": "Back Market",
    "clarityai": "Clarity AI",
    "ecovadis": "EcoVadis",
    "ibanfirst": "iBanFirst",
    "payfit": "PayFit",
    "vestiairecollective": "Vestiaire Collective",
    "forvismazars": "Forvis Mazars",
    "alixpartners": "AlixPartners",
    "descartesunderwriting": "Descartes Underwriting",
    "sfeir": "SFEIR",
    "dedale-intelligence": "Dedale Intelligence",
    "grantthornton": "Grant Thornton",
    "meridiam": "Meridiam",
    "bakertilly": "Baker Tilly",
    "tikehaucapital": "Tikehau Capital",
    "axa": "AXA",
    "amundi": "Amundi",
    "bnpparibas": "BNP Paribas",
    "societegenerale": "Société Générale",
    "sycomoreassetmanagement": "Sycomore Asset Management",
    "jobteaser": "JobTeaser",
    "rolandberger": "Roland Berger",
    "southpole": "South Pole",
    "positiongreen": "Position Green",
    "cdpworldwide": "CDP",
    "keplercheuvreux": "Kepler Cheuvreux",
    "jobs.tennaxia.com": "Tennaxia",
    "paipartners": "PAI Partners",
    "8advisory": "Eight Advisory",
    "eqtpartners": "EQT",
    "epsa": "EPSA (Ekodev)",
    "masdar": "Masdar",
    "repriskag": "RepRisk",
    "ifrsfoundation": "IFRS Foundation (ISSB)",
    "oecd": "OCDE (OECD)",
    "saintgobain": "Saint-Gobain",
}


def nom_ats(slug: str) -> str:
    """The readable company name of an ATS identifier ("rolandberger" → Roland Berger).

    Args:
        slug: the identifier of the account on the ATS.

    Returns:
        The known name, otherwise the identifier with initial capitals.
    """
    return ATS_NOMS.get(slug.lower()) or slug.title()


# Teamtailor: public RSS feed per company, place in <tt:city>/<tt:country>.
# Added on 2026-10-08 for South Pole, Indefi, Datamaran, Position Green — the
# European ESG consulting is there, and on none of the five ATS read until then.
_RX_TT_ITEM = re.compile(r"<item>(.*?)</item>", re.S)


def _tt(champ: str, item: Any) -> str:
    m = re.search(r"<" + re.escape(champ) + r">(.*?)</" + re.escape(champ) + r">", item, re.S)
    return html.unescape(m.group(1).strip()) if m else ""


def fetch_ats(kind: str, slug: str) -> list[dict[str, Any]]:
    """The offers of an account on a public ATS (Greenhouse, Lever, Ashby, Recruitee…).

    Args:
        kind: the type of ATS.
        slug: the identifier of the account.

    Returns:
        The offers with title and URL filled in; [] on refusal or failure (counted
        in INCIDENTS).
    """
    import httpx

    out = []
    try:
        if kind == "greenhouse":
            # ?content=true → HTML description included in the list
            r = _commun._get_borne(
                httpx,
                f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true",
                timeout=15,
                headers=UA,
            )
            if _ats_ko(kind, slug, r):
                return []
            for j in r.json().get("jobs", []):
                out.append(
                    _mk(
                        j.get("title", ""),
                        j.get("absolute_url", ""),
                        nom_ats(slug),
                        (j.get("location") or {}).get("name", ""),
                        j.get("updated_at", "")[:10],
                        f"greenhouse:{slug}",
                        _strip_html(j.get("content", "")),
                    )
                )
        elif kind == "lever":
            # Lever hosts some companies in its European region: their feed
            # returns 404 on api.lever.co and answers on api.eu.lever.co.
            r = _commun._get_borne(
                httpx, f"https://api.lever.co/v0/postings/{slug}?mode=json", timeout=15, headers=UA
            )
            if getattr(r, "status_code", 0) == 404:
                r = _commun._get_borne(
                    httpx,
                    f"https://api.eu.lever.co/v0/postings/{slug}?mode=json",
                    timeout=15,
                    headers=UA,
                )
            if _ats_ko(kind, slug, r):
                return []
            for j in r.json():
                out.append(
                    _mk(
                        j.get("text", ""),
                        j.get("hostedUrl", ""),
                        nom_ats(slug),
                        (j.get("categories") or {}).get("location", ""),
                        "",
                        f"lever:{slug}",
                        j.get("descriptionPlain", "") or _strip_html(j.get("description", "")),
                    )
                )
        elif kind == "ashby":
            r = _commun._get_borne(
                httpx,
                f"https://api.ashbyhq.com/posting-api/job-board/{slug}",
                timeout=15,
                headers=UA,
            )
            if _ats_ko(kind, slug, r):
                return []
            for j in r.json().get("jobs", []):
                out.append(
                    _mk(
                        j.get("title", ""),
                        j.get("jobUrl", ""),
                        nom_ats(slug),
                        j.get("location", ""),
                        "",
                        f"ashby:{slug}",
                        _strip_html(j.get("descriptionHtml", "")),
                    )
                )
        elif kind == "recruitee":
            r = _commun._get_borne(
                httpx, f"https://{slug}.recruitee.com/api/offers/", timeout=15, headers=UA
            )
            if _ats_ko(kind, slug, r):
                return []
            for j in r.json().get("offers", []):
                out.append(
                    _mk(
                        j.get("title", ""),
                        j.get("careers_url", ""),
                        nom_ats(slug),
                        j.get("location", ""),
                        "",
                        f"recruitee:{slug}",
                        _strip_html(j.get("description", "")),
                    )
                )
        elif kind == "teamtailor":
            # A domain of its own (jobs.tennaxia.com) serves the same feed.
            hote = slug if "." in slug else f"{slug}.teamtailor.com"
            r = _commun._get_borne(httpx, f"https://{hote}/jobs.rss", timeout=15, headers=UA)
            if _ats_ko(kind, slug, r):
                return []
            for it in _RX_TT_ITEM.findall(r.text):
                lieu = ", ".join(x for x in (_tt("tt:city", it), _tt("tt:country", it)) if x)
                out.append(
                    _mk(
                        _tt("title", it),
                        _tt("link", it),
                        nom_ats(slug),
                        lieu,
                        "",
                        f"teamtailor:{slug}",
                        _strip_html(_tt("description", it)),
                    )
                )
        elif kind == "smartrecruiters":
            r = _commun._get_borne(
                httpx,
                f"https://api.smartrecruiters.com/v1/companies/{slug}/postings?limit=100",
                timeout=15,
                headers=UA,
            )
            if _ats_ko(kind, slug, r):
                return []
            for j in r.json().get("content", []):
                o = _mk(
                    j.get("name", ""),
                    f"https://jobs.smartrecruiters.com/{slug}/{j.get('id', '')}",
                    nom_ats(slug),
                    (j.get("location") or {}).get("city", ""),
                    str(j.get("releasedDate", ""))[:10],
                    f"smartrecruiters:{slug}",
                )
                out.append(o)
        # SmartRecruiters: description through a detail call — only for the titles kept (few)
        if kind == "smartrecruiters":
            kept = [o for o in out if title_ok(o["titre"])]
            for o in kept:
                try:
                    jid = o["url"].rstrip("/").split("/")[-1]
                    rd = _commun._get_borne(
                        httpx,
                        f"https://api.smartrecruiters.com/v1/companies/{slug}/postings/{jid}",
                        timeout=12,
                        headers=UA,
                    )
                    if rd.status_code == 200:
                        secs = (rd.json().get("jobAd") or {}).get("sections") or {}
                        o["description"] = _strip_html(
                            " ".join(
                                str(v.get("text", "")) for v in secs.values() if isinstance(v, dict)
                            )
                        )[:30000]
                except Exception:
                    pass
                time.sleep(0.4)  # detail call per offer: we do not machine-gun
            # Same guard as the normal output: an offer without a URL is not
            # usable, it must not get in through this branch either.
            return [o for o in kept if o["titre"] and o["url"]]
    except Exception as e:
        INCIDENTS[f"ats:{kind}"][type(e).__name__] += 1
        return []
    return [o for o in out if o["titre"] and o["url"] and title_ok(o["titre"])]


ATS_PAUSE = 0.5  # between two slugs: 40 calls in a row, better space them out


def scan_ats() -> list[dict[str, Any]]:
    """Collects all the ATS accounts of the configuration.

    Returns:
        The offers of all the accounts.
    """
    from jobhunter.sources import feeds as _flux

    offers = []
    suspendus = _flux.suspendus()
    for kind, slugs in _commun.ATS_SLUGS.items():
        for slug in slugs:
            ident = _flux.cle(kind, slug)
            if ident in suspendus:
                continue  # suspended in the Companies panel: kept, not collected
            avant = _flux.instantane(f"ats:{kind}")
            got = fetch_ats(kind, slug)
            _flux.noter(ident, len(got), _flux.nouveaux(f"ats:{kind}", avant))
            if got:
                _log.info(f"  ✓ {kind}:{slug} → {len(got)} offres")
            offers.extend(got)
            time.sleep(ATS_PAUSE)
    offers.extend(scan_autres())
    return offers


_RX_CDATA = re.compile(r"^<!\[CDATA\[(.*)\]\]>$", re.S)

_RX_LIEU_FIN = re.compile(r"\s*\(([^()]*)\)\s*$")

_RX_TS_CAT = re.compile(r"<category>(.*?)</category>", re.S)

_RX_TS_REF = re.compile(r"^\s*\d{4}-\d+\s+-\s+")

_RX_AV_TITRE = re.compile(
    r'<h3 class="article__header__text__title[^"]*">\s*<a (?:class="link" )?href="([^"]+)">\s*([^<]+?)\s*</a>'
)

_RX_AV_PAYS = re.compile(r'list-item-jobCountry">([^<]+)<')

_RX_AV_DATE = re.compile(r'list-item-jobCreationDate">(\d{2})-(\d{2})-(\d{4})<')

# Two TalentBrew themes: title in the <a> (Moody's) or in an <h2> inside it (ING).
_RX_TB_LIEN = re.compile(
    r'href="(/[a-z-]+/job/[^"]+)"[^>]*data-job-id="\d+"[^>]*>\s*(?:<h2[^>]*>)?\s*([^<]+?)\s*<'
)

_RX_TB_LIEU = re.compile(r'job-location">([^<]+)<')

_RX_ADB_LIGNE = re.compile(
    r'<a href="(https://www\.adb\.org/careers/\d+)">([^<]+?)\s*/\s*\d+</a>(.*?)</tr>', re.S
)

_RX_ADB_LIEU = re.compile(r'field-location">\s*([^<]+?)\s*<')

_RX_ADB_DATE = re.compile(r'field-date-content"><time datetime="(\d{4}-\d{2}-\d{2})')

_RX_PS_CHAMP = re.compile(
    r"id='(SCH_JOB_TITLE|HRS_APP_JBSCH_I_HRS_JOB_OPENING_ID|SCH_OPENED|LOCATION)\$(\d+)'\s*>([^<]*)<"
)

_RX_CSOD_CTX = re.compile(r"csod\.context\s*=\s*(\{.*?\});", re.S)

_RX_ICIMS_CARTE = re.compile(r'<li class="iCIMS_JobCardItem">(.*?)</li>', re.S)

_RX_ICIMS_LIEN = re.compile(r'<a href="([^"]+/jobs/\d+/[^"]*)"[^>]*title="\d+ - ([^"]+)"')

_RX_ICIMS_LIEU = re.compile(r"Job Locations</span>\s*</dt>\s*<dd[^>]*><span\s*>\s*([^<]+)</span>")

ICIMS_PAGES = 15

SITEMAP_JOURS = 60

_RX_SM_INDEX = re.compile(r"<sitemap>\s*<loc>([^<]+)</loc>")

_RX_SM_URL = re.compile(r"<url>\s*<loc>([^<]+)</loc>(.*?)</url>", re.S)

_RX_SM_DATE = re.compile(r"<lastmod>(\d{4}-\d{2}-\d{2})")

_RX_SM_NUM = re.compile(r"\s+\d{1,2}$")

_RX_SM_ID = re.compile(r"^\d{3,}[\s/]+")

_RX_SM_H1 = re.compile(r"<h1[^>]*>(.*?)</h1>", re.S)


def _sans_cdata(s: str) -> str:
    m = _RX_CDATA.match(s.strip())
    return m.group(1) if m else s


def fetch_autre(kind: str, cle: str, nom: str) -> list[dict[str, Any]]:
    """The offers of another public feed (Workable, Pinpoint, Eightfold, Teamtailor…).

    Args:
        kind: the type of feed.
        cle: the identifier of the account (and its parameters).
        nom: the company name to display.

    Returns:
        The offers with title and URL filled in.
    """
    import httpx

    out = []
    try:
        if kind == "workable":
            r = _commun._get_borne(
                httpx,
                f"https://apply.workable.com/api/v1/widget/accounts/{cle}",
                timeout=15,
                headers=UA,
            )
            if _ats_ko(kind, cle, r):
                return []
            for j in r.json().get("jobs", []):
                lieu = ", ".join(x for x in (j.get("city"), j.get("country")) if x)
                out.append(
                    _mk(
                        j.get("title", ""),
                        j.get("url", ""),
                        nom,
                        lieu,
                        j.get("published_on", ""),
                        f"workable:{cle}",
                    )
                )
        elif kind == "pinpoint":
            hote = cle if "." in cle else f"{cle}.pinpointhq.com"  # domaine propre accepte
            r = _commun._get_borne(
                httpx,
                f"https://{hote}/postings.json",
                timeout=15,
                headers=UA,
                follow_redirects=True,
            )
            if _ats_ko(kind, cle, r):
                return []
            for j in r.json().get("data", []):
                out.append(
                    _mk(
                        j.get("title", ""),
                        j.get("url", ""),
                        nom,
                        (j.get("location") or {}).get("name", ""),
                        "",
                        f"pinpoint:{cle}",
                        _strip_html(j.get("description", "")),
                    )
                )
        elif kind == "sitemap":
            # In-house sites without an API, but whose sitemap lists each offer with
            # its date (Sia Partners, Carbone 4). Title drawn from the address: their
            # offer page displays "Offres d'emploi" in <h1>, not the title.
            # "root|path|h1": the address only carries an identifier (KBC),
            # the title is then read in the <h1> of each page.
            racine, chemin, *mode = cle.split("|")
            limite = (datetime.date.today() - datetime.timedelta(days=SITEMAP_JOURS)).isoformat()
            r = _commun._get_borne(httpx, racine, timeout=20, headers=UA, follow_redirects=True)
            if _ats_ko(kind, racine, r):
                return []
            xml = [r.text]
            for enfant in _RX_SM_INDEX.findall(r.text) if "<sitemapindex" in r.text else []:
                re_ = _commun._get_borne(
                    httpx, html.unescape(enfant), timeout=20, headers=UA, follow_redirects=True
                )
                if re_.status_code == 200:
                    xml.append(re_.text)
            vus = set()
            for x in xml:
                for loc, reste in _RX_SM_URL.findall(x):
                    loc = html.unescape(loc)
                    date = (_RX_SM_DATE.findall(reste) or [""])[0]
                    if chemin not in loc or loc in vus or (date and date < limite):
                        continue
                    vus.add(loc)
                    # Everything that follows the path: "internship-consultant-m/f-january-2027"
                    # contains a "/". The final "-0", "-1" is a slug duplicate.
                    slug = loc.split(chemin, 1)[1].strip("/")
                    titre = re.sub(r"[-_]+", " ", unquote(slug)).strip()
                    # "7827/senior-esg-risk-analyst" (ABN AMRO): the leading identifier drops.
                    titre = _RX_SM_ID.sub("", _RX_SM_NUM.sub("", titre)).capitalize()
                    if mode == ["h1"]:
                        p = _commun._get_borne(
                            httpx, loc, timeout=20, headers=UA, follow_redirects=True
                        )
                        h1 = _RX_SM_H1.search(p.text) if p.status_code == 200 else None
                        if not h1:
                            continue
                        titre = html.unescape(re.sub(r"<[^>]+>", "", h1.group(1))).strip()
                        time.sleep(_workday.WORKDAY_PAUSE)
                    out.append(_mk(titre, loc, nom, "", date, f"sitemap:{urlparse(racine).netloc}"))
        elif kind == "peoplesoft":
            # PeopleSoft Fluid (EIB): the server-rendered search page
            # lists all the open offers, fields indexed by row ($0, $1...).
            # The detail link requires the session: it opens the list, then the offer.
            base = f"https://{cle}/c/HRS_HRAM_FL.HRS_CG_SEARCH_FL.GBL"
            r = _commun._get_borne(
                httpx,
                f"{base}?Page=HRS_APP_SCHJOB_FL&Action=U",
                timeout=30,
                headers=UA,
                follow_redirects=True,
            )
            if _ats_ko(kind, cle, r):
                return []
            champs: dict[str, Any] = {}
            for nom_champ, i, val in _RX_PS_CHAMP.findall(r.text):
                champs.setdefault(i, {})[nom_champ] = html.unescape(val.strip())
            for i in sorted(champs, key=int):
                c = champs[i]
                ident = c.get("HRS_APP_JBSCH_I_HRS_JOB_OPENING_ID", "")
                if not c.get("SCH_JOB_TITLE") or not ident:
                    continue
                jj, mm, aa = (c.get("SCH_OPENED", "").split("/") + ["", "", ""])[:3]
                out.append(
                    _mk(
                        c["SCH_JOB_TITLE"],
                        f"{base}?Page=HRS_APP_JBPST_FL&Action=U"
                        f"&FOCUS=Applicant&SiteId=1&JobOpeningId={ident}&PostingSeq=1",
                        nom,
                        c.get("LOCATION", ""),
                        f"{aa}-{mm}-{jj}" if aa else "",
                        f"peoplesoft:{cle.split('/')[0]}",
                    )
                )
        elif kind == "gogenerali":
            # Generali (Italian portal, headquarters and subsidiaries): the page's API
            # answers without a token. The agencies (outside the "direzionale" scope) are
            # sales jobs, excluded. Posting: /home/job/{id}/{title}.
            r = _commun._get_borne(
                httpx,
                f"https://{cle}/rest-api/talent-farm-mediator/get-available-jobs-from-ats"
                f"?fromRecord=0&numRecords=1000&onlyDirectionalPerimeter=true",
                timeout=30,
                headers={**UA, "Accept": "application/json"},
            )
            if _ats_ko(kind, cle, r):
                return []
            for j in (r.json() or {}).get("response") or []:
                if not j.get("contestId") or j.get("currentStatus") != "PUBLISHED":
                    continue
                slug = re.sub(r"[^a-z0-9]+", "-", (j.get("title") or "").lower()).strip("-")
                desc = _strip_html(
                    (j.get("descriptionInternalHTML") or "")
                    + " "
                    + (j.get("internalQualificationHTML") or "")
                )
                out.append(
                    _mk(
                        j.get("title", ""),
                        f"https://{cle}/home/job/{j['contestId']}/{slug}",
                        nom,
                        j.get("primaryLocation") or "",
                        (j.get("currentStatusDate") or "")[:10],
                        f"gogenerali:{cle}",
                        desc,
                    )
                )
        elif kind == "adb":
            # Asian Development Bank: HTML table of all the
            # open offers, "Title / reference" in the link.
            r = _commun._get_borne(
                httpx, f"https://{cle}", timeout=30, headers=UA, follow_redirects=True
            )
            if _ats_ko(kind, cle, r):
                return []
            for url, titre, reste in _RX_ADB_LIGNE.findall(r.text):
                l, d = _RX_ADB_LIEU.search(reste), _RX_ADB_DATE.search(reste)
                out.append(
                    _mk(
                        html.unescape(titre),
                        url,
                        nom,
                        html.unescape(l.group(1)) if l else "",
                        d.group(1) if d else "",
                        "adb:adb.org",
                    )
                )
        elif kind == "icims":
            # Paginated HTML list (pr=0, 1, ...), then filtered by title_ok:
            # the iframe's keyword search returns nothing without a session.
            vus = set()
            for page in range(ICIMS_PAGES):
                r = _commun._get_borne(
                    httpx,
                    f"https://{cle}/jobs/search?ss=1&in_iframe=1&pr={page}",
                    timeout=20,
                    headers=UA,
                    follow_redirects=True,
                )
                if _ats_ko(kind, cle, r):
                    break
                neufs = 0
                for carte in _RX_ICIMS_CARTE.findall(r.text):
                    m = _RX_ICIMS_LIEN.search(carte)
                    if not m or m.group(1) in vus:
                        continue
                    vus.add(m.group(1))
                    neufs += 1
                    l = _RX_ICIMS_LIEU.search(carte)
                    out.append(
                        _mk(
                            html.unescape(m.group(2)),
                            m.group(1).replace("?in_iframe=1", ""),
                            nom,
                            html.unescape(l.group(1).strip()) if l else "",
                            "",
                            f"icims:{cle}",
                        )
                    )
                if not neufs:
                    break
                time.sleep(_workday.WORKDAY_PAUSE)
        else:
            vus = set()
            for mot in _workday.WORKDAY_MOTS:
                for titre, url, lieu, date, desc in _cherche_autre(httpx, kind, cle, mot):
                    if url and url not in vus:
                        vus.add(url)
                        out.append(
                            _mk(titre, url, nom, lieu, date, f"{kind}:{cle.split('|')[0]}", desc)
                        )
                time.sleep(_workday.WORKDAY_PAUSE)
    except Exception as e:
        INCIDENTS[f"ats:{kind}"][type(e).__name__] += 1
        return []
    return [o for o in out if o["titre"] and o["url"] and title_ok(o["titre"])]


def _cherche_autre(httpx: Any, kind: str, cle: str, mot: str) -> list[Any]:
    """[(title, url, place, date, description)] for a keyword, server side."""
    if kind == "eightfold":
        hote, domaine = cle.split("|")
        r = _commun._get_borne(
            httpx,
            f"https://{hote}/api/apply/v2/jobs?domain={domaine}&start=0&num=50&query={quote(mot)}",
            timeout=20,
            headers=UA,
        )
        if _ats_ko(kind, hote, r):
            return []
        return [
            (
                p.get("name", ""),
                p.get("canonicalPositionUrl", ""),
                p.get("location", ""),
                "",
                _strip_html(p.get("job_description", "")),
            )
            for p in r.json().get("positions", [])
        ]
    if kind == "sfrss":
        r = _commun._get_borne(
            httpx,
            f"https://{cle}/services/rss/job/?locale=en_US&keywords={quote(mot)}",
            timeout=20,
            headers=UA,
        )
        if _ats_ko(kind, cle, r):
            return []
        res = []
        for it in _RX_TT_ITEM.findall(r.text):
            titre = _sans_cdata(_tt("title", it))
            m = _RX_LIEU_FIN.search(titre)  # « Analyst - Paris (Paris, FR) »
            lieu = m.group(1) if m else ""
            titre = _RX_LIEU_FIN.sub("", titre) if m else titre
            titre = titre[6:] if titre.startswith("Job | ") else titre  # Belfius
            res.append(
                (
                    titre,
                    _sans_cdata(_tt("link", it)),
                    lieu,
                    "",
                    _strip_html(_sans_cdata(_tt("description", it))),
                )
            )
        return res
    if kind == "talentsoft":
        # Without Rss_Keywords the feed returns the last 20 offers, all professions.
        r = _commun._get_borne(
            httpx,
            f"https://{cle}/handlers/offerRss.ashx?LCID=1036&Rss_Keywords={quote(mot)}",
            timeout=20,
            headers=UA,
        )
        if _ats_ko(kind, cle, r):
            return []
        res = []
        for it in _RX_TT_ITEM.findall(r.text):
            cats = [html.unescape(c.strip()) for c in _RX_TS_CAT.findall(it)]
            titre = _RX_TS_REF.sub("", _tt("title", it))  # « 2026-116250 - Stage - ... »
            res.append(
                (
                    titre,
                    _tt("link", it),
                    cats[-1] if len(cats) >= 3 else "",
                    "",
                    _strip_html(_tt("description", it)),
                )
            )
        return res
    if kind == "phenom":
        # The results page embeds its offers as JSON (phApp.ddo), 10 per
        # page. It is the server render that every visitor receives.
        res = []
        for depart in (0, 10):
            r = _commun._get_borne(
                httpx,
                f"https://{cle}/search-results?keywords={quote(mot)}&from={depart}",
                timeout=20,
                headers=UA,
            )
            if _ats_ko(kind, cle, r):
                break
            i = r.text.find("phApp.ddo = ")
            if i < 0:
                break
            try:
                ddo, _ = json.JSONDecoder().raw_decode(r.text[i + 12 :])
                jobs = ddo["eagerLoadRefineSearch"]["data"]["jobs"]
            except Exception:
                break
            res += [
                (
                    j.get("title", ""),
                    f"https://{cle}/job/{j.get('jobId', '')}",
                    j.get("cityStateCountry") or j.get("location") or "",
                    str(j.get("postedDate") or "")[:10],
                    j.get("descriptionTeaser") or "",
                )
                for j in jobs
                if j.get("jobId")
            ]
            if len(jobs) < 10:
                break
        return res
    if kind == "jibe":
        # Jibe (Google Cloud Talent): the career page calls /api/jobs, JSON
        # public, description comprise. Schneider Electric (2026-10-08).
        r = _commun._get_borne(
            httpx,
            f"https://{cle}/api/jobs?page=1&keywords={quote(mot)}&sortBy=relevance&limit=50",
            timeout=20,
            headers={**UA, "Accept": "application/json"},
            follow_redirects=True,
        )
        if _ats_ko(kind, cle, r):
            return []
        res = []
        for j in (r.json() or {}).get("jobs") or []:
            d = j.get("data") or {}
            if not d.get("slug"):
                continue
            res.append(
                (
                    d.get("title", ""),
                    f"https://{cle}/jobs/{d['slug']}?lang=en-us",
                    d.get("location_name") or d.get("country") or "",
                    "",
                    _strip_html(d.get("description") or ""),
                )
            )
        return res
    if kind == "talentbrew":
        # Radancy TalentBrew: the search page (word in the path) is
        # rendue cote serveur. Moody's, ING (2026-10-08). cle = « hote/langue|org ».
        base, org = cle.split("|")
        r = _commun._get_borne(
            httpx,
            f"https://{base}/search-jobs/{quote(mot)}/{org}/1",
            timeout=20,
            headers=UA,
            follow_redirects=True,
        )
        if _ats_ko(kind, base, r):
            return []
        hote = base.split("/")[0]
        res, vus = [], set()
        for m in _RX_TB_LIEN.finditer(r.text):
            if m.group(1) in vus:
                continue
            vus.add(m.group(1))
            l = _RX_TB_LIEU.search(r.text, m.end(), m.end() + 1500)
            res.append(
                (
                    html.unescape(m.group(2).strip()),
                    f"https://{hote}{m.group(1)}",
                    html.unescape(l.group(1).strip()) if l else "",
                    "",
                    "",
                )
            )
        return res
    if kind == "avature":
        # Server-rendered search page, 50 cards per page.
        r = _commun._get_borne(
            httpx,
            f"https://{cle}/SearchJobs/?listFilterMode=1&jobRecordsPerPage=50&search={quote(mot)}",
            timeout=20,
            headers=UA,
            follow_redirects=True,
        )
        if _ats_ko(kind, cle, r):
            return []
        res = []
        for carte in r.text.split('class="article article--result"')[1:]:
            m = _RX_AV_TITRE.search(carte)
            if not m:
                continue
            pays = _RX_AV_PAYS.search(carte)
            d = _RX_AV_DATE.search(carte)
            res.append(
                (
                    html.unescape(m.group(2).strip()),
                    m.group(1),
                    html.unescape(pays.group(1).strip()) if pays else "",
                    f"{d.group(3)}-{d.group(2)}-{d.group(1)}" if d else "",
                    "",
                )
            )
        return res
    if kind == "csod":
        # Cornerstone: the public page delivers to every visitor an anonymous
        # token, which its own script sends to the search API.
        hote, site = cle.split("|")
        tenant = hote.split(".")[0]
        page = _commun._get_borne(
            httpx,
            f"https://{hote}/ux/ats/careersite/{site}/home?c={tenant}",
            timeout=20,
            headers=UA,
        )
        if _ats_ko(kind, hote, page):
            return []
        m = _RX_CSOD_CTX.search(page.text)
        ctx = json.loads(m.group(1)) if m else {}
        api = ((ctx.get("endpoints") or {}).get("cloud") or "").rstrip("/")
        if not ctx.get("token") or not api:
            return []
        r = _commun._post_borne(
            httpx,
            f"{api}/rec-job-search/external/jobs",
            timeout=20,
            headers={
                **UA,
                "Authorization": "Bearer " + ctx["token"],
                "Content-Type": "application/json",
            },
            json={
                "careerSiteId": int(site),
                "careerSitePageId": int(site),
                "pageNumber": 1,
                "pageSize": 50,
                "cultureId": 1,
                "searchText": mot,
                "cultureName": "en-US",
                "states": [],
                "countryCodes": [],
                "cities": [],
                "placeID": "",
                "radius": None,
                "postingsWithinDays": None,
                "customFieldCheckboxKeys": [],
                "customFieldDropdowns": [],
                "customFieldRadios": [],
            },
        )
        if _ats_ko(kind, hote, r):
            return []
        res = []
        for j in ((r.json() or {}).get("data") or {}).get("requisitions") or []:
            loc = (j.get("locations") or [{}])[0]
            lieu = ", ".join(x for x in (loc.get("city"), loc.get("country")) if x)
            res.append(
                (
                    j.get("displayJobTitle", ""),
                    f"https://{hote}/ux/ats/careersite/{site}/home/requisition/"
                    f"{j.get('requisitionId', '')}?c={tenant}",
                    lieu,
                    "",
                    j.get("externalDescription") or "",
                )
            )
        return res
    if kind == "oracle":
        hote, site = cle.split("|")
        r = _commun._get_borne(
            httpx,
            f"https://{hote}/hcmRestApi/resources/latest/recruitingCEJobRequisitions"
            f"?onlyData=true&expand=requisitionList&finder=findReqs;siteNumber={site},"
            f"limit=50,keyword={quote(mot)}",
            timeout=20,
            headers=UA,
        )
        if _ats_ko(kind, hote, r):
            return []
        items = r.json().get("items") or [{}]
        return [
            (
                j.get("Title", ""),
                f"https://{hote}/hcmUI/CandidateExperience/en/sites/{site}/job/{j.get('Id', '')}",
                j.get("PrimaryLocation", ""),
                j.get("PostedDate", ""),
                j.get("ShortDescriptionStr") or "",
            )
            for j in items[0].get("requisitionList") or []
            if j.get("Id")
        ]
    return []


# Choisir le service public: the portal of the three French civil services (CDC,
# Banque de France, AMF, ACPR, ministries...). Found on 2026-10-08 while searching
# "Caisse des Depots recrutement": the CDC has no feed of its own, its offers
# are there. Wide full-text search (22,409 results for "esg"), sorted
# by relevance: two pages per word are enough, title_ok does the rest.
CSP = "https://choisirleservicepublic.gouv.fr"

CSP_MOTS = [
    "esg",
    "finance durable",
    "analyste financier",
    "finance climat",
    "analyste investissement",
    "risques financiers",
    "taxonomie",
    "extra-financier",
]

# Measured on 2026-10-08: 178 offers pass title_ok, including 36 municipalities and 31
# inter-municipal bodies. We only keep public financial employers, or a
# frankly ESG / sustainable finance title whatever the employer.
_RX_CSP_EMPLOYEUR = re.compile(
    r"caisse des d[ée]p[ôo]ts|\bCDC\b|banque de france|\bAMF\b|autorit[ée] des march[ée]s|"
    r"\bACPR\b|contr[ôo]le prudentiel|\bAFD\b|agence fran[cç]aise de d[ée]veloppement|"
    r"bpifrance|tr[ée]sor|\bADEME\b|banque des territoires|cour des comptes|"
    r"\bIGF\b|inspection g[ée]n[ée]rale des finances|\bDGFIP\b|finances publiques|"
    r"[ée]conomie,? des finances|\bFRR\b|fonds de r[ée]serve|\bCNP\b|"
    r"agence des participations|\bAPE\b|\bIEDOM\b|\bIEOM\b",
    re.I,
)

_RX_CSP_INTITULE = re.compile(
    # Not "climat" alone: territorial climate plans, and even "climat scolaire".
    r"\bESG\b|\bRSE\b|finance durable|extra-?financ|taxonomie|\bISR\b|"
    r"analyste financ|analyste investissement|risques? financ|finance climat",
    re.I,
)

_RX_CSP_TITRE = re.compile(
    r'<h3 class="fr-card__title">\s*<a\s+href="([^"]+)"[^>]*>\s*([^<]+?)\s*</a>'
)

_RX_CSP_CHAMP = re.compile(r'<span class="sr-only">([^<]+?) : </span>\s*(.*?)\s*</li>', re.S)


def fetch_service_public() -> list[dict[str, Any]]:
    """Choisir le service public collection, by keywords.

    Returns:
        The offers, without duplicates.
    """
    import httpx

    out, vus = [], set()
    try:
        for mot in CSP_MOTS:
            for page in (1, 2):
                url = f"{CSP}/nos-offres/filtres/mot-cles/{quote(mot)}/" + (
                    f"page/{page}/" if page > 1 else ""
                )
                r = _commun._get_borne(httpx, url, timeout=20, headers=UA, follow_redirects=True)
                if _ats_ko("service_public", mot, r):
                    break
                # A card contains its own <li>: we cut on its
                # opening rather than looking for its closing.
                for carte in r.text.split('<li class="fr-col-12 item">')[1:]:
                    m = _RX_CSP_TITRE.search(carte)
                    if not m or m.group(1) in vus:
                        continue
                    vus.add(m.group(1))
                    ch = {k.strip(): _texte_brut(v) for k, v in _RX_CSP_CHAMP.findall(carte)}
                    out.append(
                        _mk(
                            html.unescape(m.group(2)),
                            m.group(1),
                            ch.get("Employeur") or "Fonction publique",
                            ch.get("Localisation", ""),
                            "",
                            "service_public",
                        )
                    )
                time.sleep(_workday.WORKDAY_PAUSE)
    except Exception as e:
        INCIDENTS["service_public"][type(e).__name__] += 1
    return [
        o
        for o in out
        if o["titre"]
        and o["url"]
        and title_ok(o["titre"])
        and (_RX_CSP_EMPLOYEUR.search(o["entreprise"]) or _RX_CSP_INTITULE.search(o["titre"]))
    ]


# Impactpool: aggregator of international organisations (UN, OECD, EIB,
# development banks). robots.txt forbids nothing. Found on 2026-10-08
# while looking where the organisations whose shop window answers 403 publish:
# their shop window refuses, their offers are here.
IMPACTPOOL = "https://www.impactpool.org"

# Measured on 2026-10-08: 7 searches 0.6 s apart -> the 1st returns 200,
# the next 6 403. A refusal stops (project rule): few words, a
# long pause, and stop at the first refusal — no new attempt.
# NOT WIRED into scan_autres: run again 1 min later, the 1st request already
# returns 403 (address flagged). To try again on 2026-11-08 at the earliest, by hand.
IMPACTPOOL_MOTS = ["sustainable finance", "ESG", "climate finance"]

IMPACTPOOL_PAUSE = 15

_RX_IP_CARTE = re.compile(
    r"<div class='job'>.*?<a[^>]*href=\"(/jobs/\d+)\".*?<h3[^>]*>\s*([^<]+?)\s*</h3>"
    r".*?type='bodyEmphasis'>\s*([^<]+?)\s*<.*?type='bodyEmphasis'>([^<]*)</div>",
    re.S,
)


def fetch_impactpool() -> list[dict[str, Any]]:
    """Impactpool collection (international organisations), by keywords.

    Returns:
        The offers, without duplicates.
    """
    import httpx

    out, vus = [], set()
    try:
        for mot in IMPACTPOOL_MOTS:
            r = _commun._get_borne(
                httpx,
                f"{IMPACTPOOL}/search?q={quote(mot)}",
                timeout=20,
                headers=UA,
                follow_redirects=True,
            )
            if _ats_ko("impactpool", mot, r):
                break  # refusal: we stop
            for chemin, titre, org, lieu in _RX_IP_CARTE.findall(r.text):
                if chemin in vus:
                    continue
                vus.add(chemin)
                out.append(
                    _mk(
                        html.unescape(titre),
                        IMPACTPOOL + chemin,
                        html.unescape(org),
                        html.unescape(lieu.strip()),
                        "",
                        "impactpool",
                    )
                )
            time.sleep(IMPACTPOOL_PAUSE)
    except Exception as e:
        INCIDENTS["impactpool"][type(e).__name__] += 1
    return [o for o in out if o["titre"] and o["url"] and title_ok(o["titre"])]


def _texte_brut(fragment: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def scan_autres() -> list[dict[str, Any]]:
    """Collects all the "other feeds" of the configuration.

    Returns:
        The offers of all the feeds.
    """
    from jobhunter.sources import feeds as _flux

    offres = []
    suspendus = _flux.suspendus()
    for kind, cle, nom in _commun.AUTRES_FLUX:
        ident = _flux.cle(kind, cle)
        if ident in suspendus:
            continue
        avant = _flux.instantane(f"ats:{kind}")
        got = fetch_autre(kind, cle, nom)
        _flux.noter(ident, len(got), _flux.nouveaux(f"ats:{kind}", avant))
        _log.info(f"  ✓ {kind}:{cle.split('|')[0]} → {len(got)} offres")
        offres.extend(got)
        time.sleep(ATS_PAUSE)
    got = fetch_service_public()
    _log.info(f"  ✓ choisirleservicepublic → {len(got)} offres")
    offres.extend(got)
    return offres
