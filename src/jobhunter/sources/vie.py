"""V.I.E / V.I.A : Business France (civiweb).

Partie de jobhunter.sources (ancien Scripts/job_sources.py, phase 3.4).
"""

import re
import time
from typing import Any

from jobhunter import log as _journal
from jobhunter.sources import common as _commun
from jobhunter.sources.common import UA, _mk, title_ok

_log = _journal.journal(__name__)


# ═══════════════ 4. V.I.E / V.I.A — Business France (civiweb) ═══════════════
# The mon-vie-via site is a Nuxt SPA: the raw HTML is an empty shell, but
# its public config (window.__NUXT__.config) delivers the endpoint and an API key
# shipped to EVERY visitor. It only gives access to the PUBLIC offers, the same ones
# the page displays without an account — no login, no personal data.
# Expected header: x-api-key (Authorization and apikey return 401).
VIE_API = "https://civiweb-api-prd.azurewebsites.net/api/Offers/search"

VIE_SITE = "https://mon-vie-via.businessfrance.fr/offres/recherche"

VIE_BASE = "https://mon-vie-via.businessfrance.fr"

_VIE_KEY_FALLBACK = "l+KwpoLPiXlsjxNT/NQ2iOFz8+iuygxAODs9FeAEWYM="


def _vie_key() -> str:
    r"""Key read live in the site's public config; the fallback avoids breaking everything if the page changes, but a frozen key will end up rotating.

    Two traps checked:
      - the key is escaped in the HTML (`\\u002F` for `/`) → to be decoded, otherwise 401;
      - "API_KEY" also matches GMAPS_API_KEY (Google Maps key) → anchor the name.
    """
    import httpx

    try:
        r = _commun._get_borne(httpx, VIE_SITE, timeout=15, headers=UA, follow_redirects=True)
        m = re.search(r'(?:^|[^_A-Z])API_KEY\s*:\s*"([^"]{20,})"', r.text)
        if m:
            k = m.group(1).encode().decode("unicode_escape")
            if k.endswith("="):  # the civiweb key is base64
                return k
    except Exception:
        pass
    return _VIE_KEY_FALLBACK


def fetch_vie(limit: int = 1000) -> list[dict[str, Any]]:
    """V.I.E/V.I.A offers.

    Interest for a junior profile: 12-24 month contract, net allowance, and many
    finance/ESG jobs in a subsidiary abroad.
    """
    import httpx

    key = _vie_key()
    H = {**UA, "Content-Type": "application/json", "Accept": "application/json", "x-api-key": key}
    out: list[dict[str, Any]] = []
    skip = 0
    while len(out) < limit:
        try:
            r = _commun._post_borne(
                httpx, VIE_API, json={"limit": 100, "skip": skip}, timeout=30, headers=H
            )
            if r.status_code != 200:
                _log.info(f"  ✗ VIE http {r.status_code} (clé rotée ? relancer probe)")
                break
            d = r.json()
        except Exception as e:
            _log.info(f"  ✗ VIE {type(e).__name__}")
            break
        res = d.get("result") or []
        if not res:
            break
        for x in res:
            titre = str(x.get("missionTitle") or "").strip()
            if not title_ok(titre):
                continue
            pays = str(x.get("countryName") or "")
            ville = str(x.get("cityName") or "")
            ind = x.get("indemnite") or 0
            dur = x.get("missionDuration") or ""
            desc = "\n".join(
                filter(
                    None,
                    [
                        str(x.get("missionDescription") or ""),
                        "PROFIL : " + str(x.get("missionProfile") or ""),
                        f"[{x.get('missionType') or 'VIE'} · {dur} mois · indemnité {int(ind)} EUR/mois]",
                    ],
                )
            )
            # DEEP link to the offer. `{VIE_SITE}?id=<id>` led to the generic
            # SEARCH page: the Apply button did not open the offer.
            # The site itself points to /offres/<id> (checked: the page does render
            # the offer and its POSTULER button).
            out.append(
                _mk(
                    titre,
                    f"{VIE_BASE}/offres/{x.get('id')}",
                    str(x.get("organizationName") or "").strip() or "VIE",
                    f"{ville} ({pays})".strip(),
                    str(x.get("startBroadcastDate") or "")[:10],
                    f"vie:{x.get('reference') or x.get('id')}",
                    desc,
                )
            )
        skip += 100
        if skip >= (d.get("count") or 0):
            break
        time.sleep(0.3)
    return out


def scan_vie() -> list[dict[str, Any]]:
    """Collects Business France's V.I.E and V.I.A, filtered by profession.

    Returns:
        The offers.
    """
    o = fetch_vie()
    _log.info(f"  ✓ V.I.E/V.I.A Business France → {len(o)} offres (après filtre métier)")
    return o
