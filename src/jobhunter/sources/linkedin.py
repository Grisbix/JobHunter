"""LinkedIn: the PUBLIC search (guest API), with waiting on 429.

Part of jobhunter.sources (formerly Scripts/job_sources.py, phase 3.4).

Decision: docs/adr/0004-429-wait-403-stop.md
"""

import json
import re
import time
from pathlib import Path
from typing import Any
from urllib.parse import quote

from jobhunter import log as _journal
from jobhunter.sources import common as _commun
from jobhunter.sources.common import INCIDENTS, UA, _mk, title_ok

_log = _journal.journal(__name__)


# ═══════════════ 2. LinkedIn PUBLIC search (guest, httpx, paginated) ═══════════════
_LI_CARD = re.compile(
    r'<a[^>]+class="[^"]*base-card__full-link[^"]*"[^>]+href="([^"]+)"[^>]*>.*?'
    r'<span class="sr-only">\s*(.*?)\s*</span>',
    re.S,
)

_LI_COMP = re.compile(r"base-search-card__subtitle[^>]*>.*?>([^<]+)<", re.S)

_LI_LOC = re.compile(r"job-search-card__location[^>]*>([^<]+)<", re.S)
# The card's posting date (<time class="job-search-card__listdate" datetime="…">). Not
# read until 3.17: two thirds of the queue came from LinkedIn without a publication date.
_LI_DATE = re.compile(r'<time[^>]*datetime="(\d{4}-\d{2}-\d{2})"')


def linkedin_guest_search(
    keyword: str, pages: int = 2, days: int = 7, lieu: str = "France"
) -> list[dict[str, Any]]:
    """LinkedIn guest API (HTML fragments, NO login, public reading).

    Pagination by start=0,25,50… f_TPR filters freshness (604800s=7d).

    `lieu` was hard-coded to "France". Disabling the geographic filter
    at the queue's entrance was therefore useless for this source: it only
    ASKED for French offers. A downstream filter cannot catch up on
    what an upstream request never asked for.
    """
    import html as _html

    import httpx

    out: list[dict[str, Any]] = []
    for p in range(pages):
        if _LI["stop"]:
            return out
        url = (
            "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
            f"?keywords={quote(keyword)}&location={quote(lieu)}"
            f"&f_TPR=r{days * 86400}&start={p * 25}"
        )
        try:
            r = _commun._get_borne(httpx, url, timeout=15, headers=UA)
            # A rate limit is WAITED for: same page, after the pause.
            while r.status_code == 429:
                INCIDENTS["linkedin_http"][429] += 1
                if not _li_pause_429(r):
                    _LI["stop"] = "429"
                    return out
                r = _commun._get_borne(httpx, url, timeout=15, headers=UA)
            _LI["suite_429"] = 0
            if r.status_code in (403, 999):
                # A REFUSAL stops: no more LinkedIn requests in the collection.
                INCIDENTS["linkedin_http"][r.status_code] += 1
                _LI["stop"] = str(r.status_code)
                return out
            if r.status_code != 200:
                # A REFUSAL IS NOT AN ABSENCE OF OFFERS. A silent `break` returned
                # an empty list indistinguishable from "nothing new this
                # week" — on the source that provides two thirds of the
                # queue. A fully throttled scan displayed "0 offres" and
                # passed for a calm day. We count, and main() says so.
                INCIDENTS["linkedin_http"][r.status_code] += 1
                break
            blocks = r.text.split("base-card")  # 1 card per block
            cartes = 0
            for b in blocks:
                mu = re.search(r'href="(https://[a-z]+\.linkedin\.com/jobs/view/[^"?]+)', b)
                mt = re.search(r'<span class="sr-only">\s*([^<]+?)\s*</span>', b)
                if not (mu and mt):
                    continue
                cartes += 1
                comp = _LI_COMP.search(b)
                loc = _LI_LOC.search(b)
                quand = _LI_DATE.search(b)
                titre = _html.unescape(mt.group(1)).strip()
                if title_ok(titre):
                    out.append(
                        _mk(
                            titre,
                            mu.group(1),
                            _html.unescape(comp.group(1)).strip() if comp else "LinkedIn",
                            _html.unescape(loc.group(1)).strip() if loc else "",
                            quand.group(1) if quand else "",
                            f"linkedin-search:{keyword}",
                        )
                    )
        except Exception as e:  # noqa: BLE001
            INCIDENTS["linkedin_reseau"][type(e).__name__] += 1
            break
        _dormir(LI_PAUSE)  # polite: spaces out the pages
        # A page short of 25 cards is the last one: asking for the next spent a
        # request (and LinkedIn's rate limit) on an empty answer. As JobSpy does.
        if cartes < LI_PAR_PAGE:
            break
    return out


# LINKEDIN RATE LIMIT. Measurement of 2026-10-17: at 1.2 s between pages, the guest
# API answers 429 from the first handful of requests — 13 keywords out of 14
# cut in 32 s. The code did `break`: page lost, next keyword, 429
# again. From 13 to 16/10, the LinkedIn collection fell from 200-640 offers
# per day to 0-28, with nothing visible outside the incident counter.
# Project rule: a 429 says "come back later" — we space out more, we
# wait (Retry-After, otherwise 60 s doubled up to 240), we resume the SAME
# page. 403/999 are refusals: immediate stop, no resumption.
#
# MAXIMUM DURATION OF THE PASS, not a waiting budget. Measurement of 17/10 with a
# waiting budget of 900 s: 184 offers (101 new) instead of 96, but
# stopped at 10 keywords out of 14, France only — "Worldwide" would have had nothing.
# The pipeline's LinkedIn pass is killed at 3600 s, and a killed pass loses ALL
# its collection (merge at the end of the pass): we stop cleanly at 45 min.
LI_PAUSE = 3.0
LI_PAR_PAGE = 25  # cards per page of the guest search

LI_ATTENTES = (60, 120, 240)

LI_DUREE_MAX = 2700

# THE CURSOR (3.79). Every pass started again at the first keyword, in France: the
# 45 min ran out in the same place each day, and the last keywords and "Worldwide"
# were almost never asked (the message said "la suite à la prochaine collecte", which
# was not true). The pass now starts at the (place, keyword) where the previous one
# stopped, and goes round. Several short passes in the day (`--linkedin-minutes`)
# then cover everything, with the rate limit recovering in between.
CURSEUR = "_linkedin_cursor.json"

_LI: dict[str, Any] = {
    "stop": None,
    "attendu": 0.0,
    "suite_429": 0,
    "debut": 0.0,
    "duree_max": LI_DUREE_MAX,
}

_dormir = time.sleep  # the tests replace it

_horloge = time.monotonic  # idem


def _li_ecoule() -> float:
    debut: float = _LI["debut"]
    return _horloge() - debut


def _li_pause_429(r: Any) -> bool:
    """Waits before asking again after a 429. False if the pass has no time left."""
    ra = (getattr(r, "headers", None) or {}).get("Retry-After", "")
    n = _LI["suite_429"]
    pause = int(ra) if str(ra).isdigit() else LI_ATTENTES[min(n, len(LI_ATTENTES) - 1)]
    pause = min(pause, max(LI_ATTENTES))
    if _li_ecoule() + pause > _LI["duree_max"]:
        return False
    _log.warning(f"  ⏳ linkedin : limite de débit (429), pause {pause} s puis reprise")
    _dormir(pause)
    _LI["attendu"] += pause
    _LI["suite_429"] = n + 1
    return True


# WHY NO MORE LIST OF COUNTRIES. The criterion is not the country, it is the
# language the posting asks for — and a country does not say it. Measurement of
# 2026-09-22: LinkedIn's public search accepts the place "Worldwide", and
# it paginates deep.
#
#   lieu=""            -> falls back on the UNITED STATES (Oxnard, Indianapolis…)
#   lieu="Worldwide"   ->  2 pages: 17 offers, 12 countries
#                         10 pages: 78 offers, 37 countries
#
# Enumerating sixteen countries cost 1,760 requests for sixteen countries. "Worldwide" in
# depth costs 550 for thirty-seven and more. Strictly better.
#
# France is still queried separately: it is where the user lives, and a worldwide
# request drowns the local offers there under the Indian and American volume.
#
# The dictionary gives the DEPTH per place. A plain list is still accepted
# and then uses the depth passed as an argument.
LIEUX_MONDE = {"France": 3, "Worldwide": 12}


def lieux_par_defaut() -> dict[str, int]:
    """The home country (`pays` in the profile) in depth, then the world."""
    from jobhunter.sources import countries as _pays

    return {_pays.nom(): LIEUX_MONDE["France"], "Worldwide": LIEUX_MONDE["Worldwide"]}


def _fichier() -> Path | None:
    """Where the cursor is kept: the data folder; None without one (nothing kept)."""
    from jobhunter import root as _racine

    try:
        return _racine.dans(_racine.scripts(), CURSEUR)
    except RuntimeError:
        return None


def _lire_curseur() -> tuple[str, str] | None:
    f = _fichier()
    try:
        d = json.loads(f.read_text(encoding="utf-8")) if f else None
    except (OSError, ValueError):
        return None
    if isinstance(d, dict) and isinstance(d.get("lieu"), str) and isinstance(d.get("mot"), str):
        return d["lieu"], d["mot"]
    return None


def _ecrire_curseur(paire: tuple[str, str] | None) -> None:
    """The pair to start with next time; None: the round is complete, start again."""
    from jobhunter.storage import atomic

    f = _fichier()
    if f is None:
        return
    try:
        if paire is None:
            f.unlink(missing_ok=True)
        else:
            atomic.ecrire_json(
                f, {"lieu": paire[0], "mot": paire[1], "le": time.strftime("%Y-%m-%d %H:%M")}
            )
    except OSError as e:
        _log.warning(f"  ⚠ linkedin : curseur non enregistré ({e})")


def scan_linkedin(
    pages: int = 2,
    days: int = 7,
    lieux: list[str] | dict[str, int] | None = None,
    duree_max: float | None = None,
) -> list[dict[str, Any]]:
    """Days = LinkedIn freshness window (f_TPR).

    The default of 7 days is enough for the daily scan, but it makes invisible the older
    offers never caught: pass --days 31 to catch up a whole month.

    `lieux`: the zones queried. In a worldwide search we cannot just
    remove the entrance filter — the other countries must be ASKED for.

    `duree_max`: the pass's length in seconds (LI_DUREE_MAX by default). The pass starts
    where the previous one stopped (CURSEUR) and goes round the (place, keyword) pairs.
    """
    if lieux is None:
        from jobhunter.sources import countries as _pays

        lieux = lieux_par_defaut() if _commun.MONDE else [_pays.nom(), *_commun.LIEUX_EN_PLUS]
    # A dict gives the depth per place, a list keeps the argument's.
    profondeur = dict(lieux) if isinstance(lieux, dict) else {x: pages for x in lieux}
    offers: list[dict[str, Any]] = []
    seen: set[str] = set()
    _LI.update(
        stop=None,
        attendu=0.0,
        suite_429=0,
        debut=_horloge(),
        duree_max=LI_DUREE_MAX if duree_max is None else duree_max,
    )
    paires = [(lieu, kw) for lieu in profondeur for kw in _commun.KEYWORDS]
    depart = _lire_curseur()
    i0 = paires.index(depart) if depart in paires else 0
    if i0:
        _log.info(f"  ↻ linkedin : reprise à {paires[i0][0]} «{paires[i0][1]}»")
    par_lieu: dict[str, int] = {}
    suivante: tuple[str, str] | None = None
    for k in range(len(paires)):
        lieu, kw = paires[(i0 + k) % len(paires)]
        if not _LI["stop"] and _li_ecoule() >= _LI["duree_max"]:
            _LI["stop"] = "durée"
        if _LI["stop"]:
            suivante = suivante or (lieu, kw)
            break
        got = linkedin_guest_search(kw, pages=profondeur[lieu], days=days, lieu=lieu)
        if _LI["stop"] and suivante is None:
            suivante = (lieu, kw)  # cut inside its pages: asked again next time
        new = [o for o in got if o["url"] not in seen]
        seen.update(o["url"] for o in new)
        par_lieu[lieu] = par_lieu.get(lieu, 0) + len(new)
        if new and len(profondeur) == 1:
            _log.info(f"  ✓ linkedin «{kw}» → {len(new)} offres")
        offers.extend(new)
    if len(profondeur) > 1:
        for lieu, n in par_lieu.items():
            _log.info(f"  ✓ linkedin {lieu} → {n} offres")
    _ecrire_curseur(suivante)
    if _LI["stop"] in ("429", "durée"):
        fait = len(paires) if suivante is None else (paires.index(suivante) - i0) % len(paires)
        _log.warning(
            f"  ⚠ linkedin : durée maximale atteinte ({_li_ecoule():.0f} s, dont "
            f"{_LI['attendu']:.0f} s d'attente sur 429), {fait}/{len(paires)} recherches"
            " — la prochaine collecte reprend là"
        )
    elif _LI["stop"]:
        _log.warning(f"  ⚠ linkedin : refus HTTP {_LI['stop']}, collecte LinkedIn arrêtée")
    return offers
