"""FIR / French SIF: 100 % SRI-ESG offers.

Part of jobhunter.sources (formerly Scripts/job_sources.py, phase 3.4).
"""

import re
from typing import Any

from jobhunter import log as _journal
from jobhunter.sources import common as _commun
from jobhunter.sources.common import UA, _mk, title_ok

_log = _journal.journal(__name__)


# ═══════════════ 5. FIR / French SIF — 100 % SRI-ESG offers ═══════════════
# Forum pour l'Investissement Responsable: a board of exclusively SRI/ESG offers.
# Unmatched density (LinkedIn brings ~15 % relevant, here it is 100 %).
# ⚠ Only the offers present in the HTML are read (~5). The tabs per
# category (jobs / work-study / internships) load in JS and /jobs_categories/<c>/
# returns 404; the WordPress REST API is closed (wp-json -> 404). A browser
# scraping would get the rest, at the cost of launching Chromium.
FIR_URL = "https://www.frenchsif.org/isr_esg/emplois-et-stages/"


def fetch_fir() -> list[dict[str, Any]]:
    """The offers of FIR / French SIF (100 % SRI-ESG finance).

    Returns:
        The offers; [] if the page could not be read.
    """
    import html as _html

    import httpx

    try:
        r = _commun._get_borne(httpx, FIR_URL, timeout=25, headers=UA, follow_redirects=True)
        if r.status_code != 200:
            _log.info(f"  ✗ FIR http {r.status_code}")
            return []
    except Exception as e:
        _log.info(f"  ✗ FIR {type(e).__name__}")
        return []
    out = []
    for a in re.split(r'<article class="loop post-', r.text)[1:]:
        mu = re.search(r'href="(https://www\.frenchsif\.org/isr_esg/emploi-stage/[^"]+)"', a)
        mt = re.search(r'<span class="entry-title">(.*?)</span>', a, re.S)
        if not (mu and mt):
            continue
        titre = _html.unescape(re.sub(r"<[^>]+>", " ", mt.group(1))).strip()
        titre = re.sub(r"\s+", " ", titre)
        loc = re.search(r"Localisation\s*:?</strong>\s*([^<.]{2,40})", a)
        # The contract prefixes the title ("CDI – Analyste ESG"). We keep it: it
        # carries useful info (work-study/internship = junior target).
        txt = _html.unescape(re.sub(r"<[^>]+>", " ", a))
        txt = re.sub(r"\s+", " ", txt).strip()[:8000]
        if not title_ok(titre):
            continue
        out.append(
            _mk(
                titre,
                mu.group(1),
                "FIR (French SIF)",
                (loc.group(1).strip() if loc else ""),
                "",
                "fir",
                txt,
            )
        )
    return out


def scan_fir() -> list[dict[str, Any]]:
    """FIR / French SIF collection, announced in the log.

    Returns:
        The offers.
    """
    o = fetch_fir()
    _log.info(f"  ✓ FIR / French SIF → {len(o)} offres (100 % ISR-ESG)")
    return o
