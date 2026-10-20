"""Welcome to the Jungle: the public sitemap.

Part of jobhunter.sources (formerly Scripts/job_sources.py, phase 3.4).
"""

import json
import re
import time
from typing import Any

from jobhunter import log as _journal
from jobhunter.sources import common as _commun
from jobhunter.sources.common import (
    _mk,
    _norm_url,
    _strip_html,
    contrat_du_titre,
    en_france,
    title_ok,
)
from jobhunter.sources.efc import _RX_EFC_ESG, _efc_lieu

_log = _journal.journal(__name__)


# ═══════════════ 3. Welcome to the Jungle — sitemap public ═══════════════
_WTJ_JS = r"""
() => {
  const out=[]; const seen=new Set();
  document.querySelectorAll('a[href*="/fr/companies/"][href*="/jobs/"]').forEach(a=>{
    const t=(a.innerText||'').trim().split('\n')[0];
    if(!t||t.length<6||seen.has(a.href))return;
    seen.add(a.href);
    const card=a.closest('li,article,[class*="card"]')||a.parentElement;
    const txt=(card?card.innerText:'').split('\n').map(s=>s.trim()).filter(Boolean);
    out.push({title:t,url:a.href,company:txt[1]||'',location:txt.find(s=>/paris|lyon|bordeaux|remote|télétravail|france/i.test(s))||''});
  });
  return out;
}"""


def _wtj_429(pg: Any) -> bool:
    """Is WTJ throttling us? Readable EVEN when navigation failed: the error page carries "Too Many Requests" while robust_goto returns ok=False."""
    try:
        return "too many requests" in pg.evaluate("document.body.innerText.slice(0,200)").lower()
    except Exception:
        return False


WTJ_SITEMAP = "https://www.welcometothejungle.com/sitemaps/index.xml.gz"

# Measured: WTJ's CloudFront challenge drops after ~3 minutes (202, 202, 200
# at 60 s intervals). Waiting therefore brings a few more postings per
# pass; stopping at the first 202 brought zero.
WTJ_REPOS = 200  # seconds of waiting when the wall goes up

WTJ_PATIENCE = 2  # maximum number of waits per pass

# 2 and no longer 6 (2026-10-02): six waits of 200 s made 20 min of idleness
# in a pass capped at 60, for a wall that most of the time came straight back down.


def _wtj_fiche(url: str, client: Any) -> dict[str, Any] | None:
    """JobPosting of a WTJ posting, or None.

    Same markup as eFinancialCareers: a <script type="application/ld+json"> meant
    for Google.

    Raises `Bloque` on 202/429: it is CloudFront's anti-bot challenge, it
    applies to the whole IP and insisting is useless. Above all, 202 is a SUCCESS
    code — mistaking it for an empty page would pass the wall off as a
    posting without description.
    """
    from jobhunter.programs.wtj_desc import UA as _WUA
    from jobhunter.programs.wtj_desc import Bloque

    try:
        r = _commun._get_borne(client, url, headers=_WUA, timeout=30)
    except Exception:
        return None
    if r.status_code in (202, 429):
        raise Bloque(r.status_code)
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


def scan_wtj(pages: int = 2) -> list[dict[str, Any]]:
    """Welcome to the Jungle offers, through the SITEMAP declared in robots.txt.

    THE OLD VERSION TARGETED A FORBIDDEN, AND DEAD, ROUTE. It built
    `/fr/jobs?query=<words>` URLs. Yet WTJ's robots.txt says, in black and
    white:

        disallow: */jobs?query=*
        Disallow: /*?

    That is exactly what we were asking for. And since then, WTJ has removed free
    search: `/fr/jobs?query=…` ignores the parameter and serves a page
    presenting their "matching" product, the real search having moved
    behind an authentication (`/fr/authenticate/signin?redirect=/fr/jobs`).
    The scan could therefore no longer return anything — hence the repeated 429s and the
    silent "0 offre".

    THE OPEN PATH. The same robots.txt declares a sitemap:
        Sitemap: https://www.welcometothejungle.com/sitemaps/index.xml.gz
    Nine `job-listings.N.xml.gz` files, 88,000 postings, 60,000 in French.
    The `/fr/companies/<slug>/jobs/<slug>` pages are forbidden nowhere.

    THE RATE STAYS THROTTLED. After a few postings, CloudFront switches the IP to a
    challenge and answers 202 with an empty body (see wtj_desc.py, same wall). So we
    read few postings per pass, stop at the first 202, and
    keep what was read. `pages` is kept for the callers' compatibility
    and serves as a cap: pages * 5 postings.
    """
    import gzip

    import httpx

    from jobhunter.programs.wtj_desc import UA as _WUA
    from jobhunter.programs.wtj_desc import Bloque

    _EX = _commun.contrats_exclus()
    offers: list[dict[str, Any]] = []

    def _lire(client: Any, url: str) -> str:
        r = _commun._get_borne(client, url, headers=_WUA, timeout=90)
        if r.status_code != 200:
            return ""
        b: bytes = r.content
        if b[:2] == b"\x1f\x8b":
            b = gzip.decompress(b)
        return b.decode("utf-8", "replace")

    with httpx.Client(follow_redirects=True) as client:
        try:
            idx = _lire(client, WTJ_SITEMAP)
        except Exception as e:
            _log.info(f"  ~ WTJ : sitemap injoignable ({type(e).__name__})")
            return offers
        fichiers = [l for l in re.findall(r"<loc>([^<]+)</loc>", idx) if "job-listings" in l]
        if not fichiers:
            _log.info("  ~ WTJ : aucun sitemap d'offres dans l'index")
            return offers

        cibles = []
        for f in fichiers:
            try:
                t = _lire(client, f)
            except Exception:
                continue
            for l in re.findall(r"<loc>([^<]+)</loc>", t):
                if "/fr/companies/" not in l or "/jobs/" not in l:
                    continue
                # The slug carries the title, lowercase and without accents: it
                # serves the PRE-FILTER. The real title comes from the posting's ld+json.
                approx = l.split("/jobs/")[-1].replace("-", " ")
                if contrat_du_titre(approx) in _EX:
                    continue
                if _RX_EFC_ESG.search(approx):
                    cibles.append(l)

        # We do not read again what is already in the queue: each posting costs a
        # request on a very limited rate.
        from jobhunter.storage import queue as queue_io

        connues = {
            _norm_url(x.get("url"))
            for x in queue_io.charger(_commun.QUEUE, descriptions=False)
            if x.get("url")
        }
        neuves = [u for u in cibles if _norm_url(u) not in connues]
        plafond = max(1, pages) * 5
        _log.info(
            f"  WTJ : {len(cibles)} offres ESG au sitemap, {len(neuves)} nouvelles "
            f"— {min(len(neuves), plafond)} lue(s) cette passe (le reste au prochain scan)"
        )

        # PATIENCE. WTJ's wall is not final: measured to the second, it
        # drops after ~3 minutes. Stopping at the first 202 returned 0 offers on
        # each pass whereas waiting gives a few more. So we
        # wait, a limited number of times, and hand back afterwards.
        # It is not a workaround: we slow down, we force nothing.
        etat = {"attentes": 0}

        def _fiche_patiente(url: str) -> Any:
            """JobPosting, or None if WTJ shuts the door on us for good.

            Returns None ONLY when patience is exhausted: the caller then knows
            it must stop the source, not just skip a posting.
            """
            while True:
                try:
                    return _wtj_fiche(url, client) or {}
                except Bloque as e:
                    if etat["attentes"] >= WTJ_PATIENCE:
                        _log.info(f"  ~ {e} — arret WTJ apres {etat['attentes']} attente(s).")
                        return None
                    etat["attentes"] += 1
                    _log.info(f"  ~ {e} — pause {WTJ_REPOS} s ({etat['attentes']}/{WTJ_PATIENCE})…")
                    time.sleep(WTJ_REPOS)

        for u in neuves[:plafond]:
            jp = _fiche_patiente(u)
            if jp is None:  # lasting wall: we hand back
                break
            if not jp:  # unreadable posting: move on to the next one
                continue
            # ONE SINGLE REQUEST PER OFFER. The description and the title live
            # in the SAME ld+json block: fetching them with two separate calls
            # doubled the consumption of an already tiny quota — the wall
            # went up twice as fast, for nothing.
            d = _strip_html(str(jp.get("description") or ""))
            if len(d) < 200:
                continue
            titre = str(jp.get("title") or "").strip()
            lieu = _efc_lieu(jp)
            if not titre or not title_ok(titre) or contrat_du_titre(titre) in _EX:
                continue
            if not en_france(lieu):
                continue
            soc = (jp.get("hiringOrganization") or {}).get("name") or "Welcome to the Jungle"
            offers.append(
                _mk(titre, u, soc, lieu, str(jp.get("datePosted") or "")[:10], "wtj-sitemap", d)
            )
    _log.info(f"  \u2713 Welcome to the Jungle \u2192 {len(offers)} offres (avec description)")
    return offers
