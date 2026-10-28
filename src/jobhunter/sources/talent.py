"""Talent.com : agregateur.

Partie de jobhunter.sources (ancien Scripts/job_sources.py, phase 3.4).
"""

import datetime
import re
import time
from typing import Any

from jobhunter import links as _liens
from jobhunter import log as _journal
from jobhunter.sources import common as _commun
from jobhunter.sources.common import UA, _mk, title_ok

_log = _journal.journal(__name__)


# ═══════════════ 6. Talent.com — aggregator (replaces the Indeed coverage) ══════
# Indeed is INACCESSIBLE: Cloudflare blocks at the IP/TLS fingerprint level, including
# in a real window with patchright+stealth (tested). Bypassing an anti-bot
# protection is out of the question; Talent.com aggregates a comparable pool and exposes
# clean schema.org JSON-LD, with the DESCRIPTION included (it is missing for 755
# offers in the queue, almost all of which come from Indeed).
#
# Cost: 1 search request + 1 per offer kept. The title_ok filter is
# applied BEFORE fetching the detail, so as not to pay for the off-topic ones.
TALENT_SEARCH = "https://fr.talent.com/jobs?k={kw}&l=France"

_TALENT_LINK_RX = re.compile(r'href="(/view\?id=\d+)"')


def _talent_detail(httpx: Any, url: str) -> Any:
    """(title, company, place, date, description) from the JobPosting JSON-LD."""
    import html as _html
    import json as _json

    try:
        r = _commun._get_borne(httpx, url, headers=UA, follow_redirects=True)
        if r.status_code != 200:
            return None
    except Exception:
        return None
    for b in re.findall(r'<script type="application/ld\+json">(.*?)</script>', r.text, re.S):
        try:
            d = _json.loads(b)
        except Exception:
            continue
        nodes = d.get("@graph") if isinstance(d, dict) and "@graph" in d else [d]
        for n in nodes or []:
            if not (isinstance(n, dict) and n.get("@type") == "JobPosting"):
                continue
            loc = ""
            jl = n.get("jobLocation")
            if isinstance(jl, dict):
                loc = str(((jl.get("address") or {}).get("addressLocality")) or "")
            desc = re.sub(r"<[^>]+>", " ", str(n.get("description") or ""))
            desc = re.sub(r"\s+", " ", _html.unescape(desc)).strip()
            return (
                str(n.get("title") or "").strip(),
                str((n.get("hiringOrganization") or {}).get("name") or "").strip(),
                loc,
                str(n.get("datePosted") or "")[:10],
                desc,
            )
    return None


def fetch_talent(max_days: int = 60, per_kw: int = 20) -> list[dict[str, Any]]:
    """Talent.com offers for each keyword.

    max_days sets aside old postings: the site serves offers more than a year old (seen
    : datePosted 2025-06).
    """
    from urllib.parse import quote as _q

    import httpx

    today = datetime.date.today()
    out, seen = [], set()
    # OFFERS ALREADY IN THE QUEUE ARE NOT RELOADED. Each posting costs a
    # request, and the collection reloaded the same ones every day: 30 min for
    # Talent alone on 30/09, in a pass capped at 60. Their description is
    # already there; only a new offer deserves its posting.
    try:
        from jobhunter.storage import queue as queue_io

        seen = {
            str(o.get("url") or "")
            for o in queue_io.charger(descriptions=False)
            if _liens.sur_site(o.get("url"), "talent.com")
        }
    except Exception:
        seen = set()
    connues = len(seen)
    for kw in _commun.KEYWORDS:
        try:
            r = _commun._get_borne(
                httpx, TALENT_SEARCH.format(kw=_q(kw)), headers=UA, follow_redirects=True
            )
            if r.status_code != 200:
                continue
        except Exception:
            continue
        links = list(dict.fromkeys(_TALENT_LINK_RX.findall(r.text)))[:per_kw]
        got = 0
        for href in links:
            u = "https://fr.talent.com" + href
            if u in seen:
                continue
            seen.add(u)
            d = _talent_detail(httpx, u)
            if not d:
                continue
            titre, ent, loc, date, desc = d
            if not title_ok(titre):
                continue
            if date:
                try:
                    if (today - datetime.date.fromisoformat(date)).days > max_days:
                        continue
                except Exception:
                    pass
            out.append(_mk(titre, u, ent or "Talent.com", loc, date, f"talent:{kw}", desc))
            got += 1
        if got:
            _log.info(f"  ✓ talent «{kw}» → {got} offres")
        time.sleep(0.5)
    _log.info(f"  Talent : {connues} offres deja dans la file, fiches non rechargees")
    return out


def scan_talent() -> list[dict[str, Any]]:
    """Talent.com collection (outside --all since 2026-10-03), announced in the log.

    Returns:
        The offers, with description.
    """
    o = fetch_talent()
    _log.info(f"  ✓ Talent.com → {len(o)} offres (avec description)")
    return o
