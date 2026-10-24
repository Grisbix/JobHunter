"""Jobs that make sense (jobs.makesense.org): the public sitemap.

Part of jobhunter.sources. A board of impact jobs (environment, social economy,
CSR, climate). robots.txt allows the offer pages and declares the sitemap; no
search page, no API, no session.

Two steps, like Welcome to the Jungle: the sitemap lists every offer with its date
and a slug "<company>-<title>-<id>"; the profile's title filter runs on that slug
(pre-filter), then each retained offer is read once — its page carries a
JobPosting ld+json block (exact title, company, place, date, description). A page
weighs about 1 MB, so a pass reads at most `limite` new offers; the rest comes
at the next collection.
"""

import datetime
import html
import json
import re
import time
from typing import Any

from jobhunter import log as _journal
from jobhunter.sources import common as _commun
from jobhunter.sources.common import (
    INCIDENTS,
    _mk,
    _norm_url,
    _strip_html,
    contrat_du_titre,
    en_france,
    title_ok,
)
from jobhunter.sources.efc import _efc_lieu

_log = _journal.journal(__name__)

MAKESENSE_SITEMAP = "https://jobs.makesense.org/sitemap-jobs.xml"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
MAKESENSE_JOURS = 45  # an offer whose sitemap date is older is not read
MAKESENSE_PAUSE = 1.0  # seconds between two offer pages

_RX_URL = re.compile(r"<url>\s*<loc>([^<]+)</loc>\s*(?:<lastmod>([^<]+)</lastmod>)?")
_RX_LDJSON = re.compile(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', re.S)
# The slug ends with the offer's identifier: 20 letters and digits after a dash.
_RX_ID = re.compile(r"-[A-Za-z0-9]{20}$")


def entrees(xml: str, depuis: str) -> list[tuple[str, str]]:
    """(url, date) of the French offer pages of the sitemap, dated `depuis` or later."""
    vues: set[str] = set()
    sortie = []
    for loc, date in _RX_URL.findall(xml):
        loc = html.unescape(loc.strip())
        if "/fr/jobs/" not in loc or loc in vues or (date and date < depuis):
            continue
        vues.add(loc)
        sortie.append((loc, date))
    return sortie


def texte_du_slug(url: str) -> str:
    """The "company title" text of the address, identifier removed: what the pre-filter reads."""
    slug = url.rstrip("/").rsplit("/", 1)[-1]
    return _RX_ID.sub("", slug).replace("-", " ")


def fiche(texte: str) -> dict[str, Any] | None:
    """The JobPosting of an offer page, or None."""
    for bloc in _RX_LDJSON.findall(texte):
        try:
            o = json.loads(bloc)
        except ValueError:
            continue
        if isinstance(o, dict) and o.get("@type") == "JobPosting":
            return o
    return None


def scan_makesense(limite: int = 30) -> list[dict[str, Any]]:
    """Offers of jobs.makesense.org that pass the profile's filters, description included."""
    import httpx

    _EX = _commun.contrats_exclus()
    offers: list[dict[str, Any]] = []
    depuis = (datetime.date.today() - datetime.timedelta(days=MAKESENSE_JOURS)).isoformat()
    with httpx.Client(follow_redirects=True) as client:
        try:
            r = _commun._get_borne(client, MAKESENSE_SITEMAP, headers=UA, timeout=90)
        except Exception as e:
            INCIDENTS.noter("makesense", type(e).__name__)
            _log.info(f"  ~ makesense : sitemap injoignable ({type(e).__name__})")
            return offers
        if r.status_code != 200:
            INCIDENTS.noter("makesense", f"HTTP {r.status_code}")
            _log.info(f"  ~ makesense : sitemap HTTP {r.status_code}")
            return offers
        cibles = [
            (u, d)
            for u, d in entrees(r.text, depuis)
            if title_ok(texte_du_slug(u)) and contrat_du_titre(texte_du_slug(u)) not in _EX
        ]
        # An offer already in the queue is not read again: each page weighs ~1 MB.
        from jobhunter.storage import queue as queue_io

        connues = {
            _norm_url(x.get("url"))
            for x in queue_io.charger(_commun.QUEUE, descriptions=False)
            if x.get("url")
        }
        neuves = [(u, d) for u, d in cibles if _norm_url(u) not in connues]
        neuves.sort(key=lambda x: x[1], reverse=True)  # the most recent first
        _log.info(
            f"  makesense : {len(cibles)} offres au filtre du titre, {len(neuves)} nouvelles "
            f"— {min(len(neuves), limite)} lue(s) cette passe (le reste au prochain scan)"
        )
        for u, date in neuves[:limite]:
            try:
                p = _commun._get_borne(client, u, headers=UA, timeout=30)
            except Exception:
                continue
            if p.status_code in (403, 429):
                INCIDENTS.noter("makesense", f"HTTP {p.status_code}")
                _log.info(f"  ~ makesense : HTTP {p.status_code} — arrêt de la passe")
                break
            jp = fiche(p.text) if p.status_code == 200 else None
            time.sleep(MAKESENSE_PAUSE)
            if not jp:
                continue
            titre = html.unescape(str(jp.get("title") or "")).strip()
            lieu = _efc_lieu(jp)
            if not titre or not title_ok(titre) or contrat_du_titre(titre) in _EX:
                continue
            if not en_france(lieu):
                continue
            soc = (jp.get("hiringOrganization") or {}).get("name") or "makesense"
            d = _strip_html(str(jp.get("description") or ""))
            quand = str(jp.get("datePosted") or date or "")[:10]
            offers.append(_mk(titre, u, str(soc), lieu, quand, "makesense", d))
    _log.info(f"  ✓ Jobs that make sense → {len(offers)} offres (avec description)")
    return offers
