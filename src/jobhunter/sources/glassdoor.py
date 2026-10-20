"""Glassdoor: the search page, page 1.

Part of jobhunter.sources (formerly Scripts/job_sources.py, phase 3.4).
"""

import re
import time
from typing import Any

from jobhunter import log as _journal
from jobhunter.network import exiger_http
from jobhunter.sources import common as _commun
from jobhunter.sources.common import INCIDENTS, _lire_borne, _mk, contrat_du_titre, title_ok
from jobhunter.sources.indeed import INDEED_UA, _IndeedBride

_log = _journal.journal(__name__)


# ═══════════════ Glassdoor — the search page, page 1 ═══════════════
# Same approach as Indeed, same boundary, thinner result.
#
#   /Emploi/…SRCH_….htm   ALLOWED. robots.txt only closes the
#                         PAGINATED forms ("Disallow: /Emploi/*_IP*"), not the
#                         premiere page.
#   /graph                FORBIDDEN — "Disallow: /graph", line 145. It is
#                         the GraphQL API JobSpy uses. Its token is
#                         served to any visitor in the HTML (their
#                         _get_csrf_token reads it on a public page), so
#                         it is not a stolen credential like Indeed's iOS
#                         key — but the path is explicitly forbidden
#                         to robots, and that is enough to close it.
#   pages 2 and up        "Disallow: /Emploi/*_IP*": that is the pagination.
#                         30 cards per request, and we stop there.
#
# WHAT GLASSDOOR GIVES, AND WHAT IT DOES NOT. The page's ld+json only
# carries the title and the URL. Everything else is in the rendered HTML, located by
# `data-test` attributes (stable) and hashed CSS classes (which change
# with each deployment): so we only hook onto the data-test and class
# PREFIXES. Above all, Glassdoor publishes NO structured contract type, where
# Indeed provides one on 15 cards out of 15. The contract falls back on
# reading the title, with its known gaps. The age is relative ("30j+",
# "3j"), not a date: we only convert it when it is bounded.
GD_HOTE = "https://www.glassdoor.fr"

GD_PAUSE = 12

GD_REPOS = 45

GD_ABANDON = 6

GD_LOC_FRANCE = 86  # locId of the country; Glassdoor only exposes CITY ids

# through /ajax/, forbidden. So we search the whole of France
# and sort afterwards with zones.zone_lieu().
GD_UA = dict(INDEED_UA)

# A card starts at its title. The employer's name is BEFORE it in the
# HTML, the place and the salary AFTER: so we split on the titles and
# read on either side.
_RX_GD_TITRE = re.compile(r'<a\b[^>]*data-test="job-title"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', re.S)

_RX_GD_EMPLOYEUR = re.compile(r'compactEmployerName[^"]*"[^>]*>(.*?)</span>', re.S)

_RX_GD_LIEU = re.compile(r'data-test="emp-location"[^>]*>(.*?)</div>', re.S)

_RX_GD_SALAIRE = re.compile(r'data-test="detailSalary"[^>]*>(.*?)</div>', re.S)

_RX_GD_AGE = re.compile(r'data-test="job-age"[^>]*>(.*?)</div>', re.S)

_RX_GD_EXTRAIT = re.compile(r'jobDescriptionSnippet[^"]*"[^>]*>(.*?)</div>', re.S)


def _gd_texte(h: str) -> str:
    """Fragment HTML → texte nu."""
    import html as _h

    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", _h.unescape(h or ""))).strip()


def _gd_date(age: Any) -> str:
    """“3j” → the date three days ago. "30j+" → nothing.

    The displayed age is relative and sometimes UNBOUNDED: "30j+" covers
    31 days as well as eight months. Converting it would give a wrong date
    in the very column used to judge freshness — we prefer empty.
    """
    a = (age or "").strip().lower()
    if "+" in a:
        return ""
    m = re.match(r"^(\d+)\s*(h|j|d|min)", a)
    if not m:
        return ""
    n = int(m.group(1))
    jours = n if m.group(2) in ("j", "d") else 0
    return time.strftime("%Y-%m-%d", time.localtime(time.time() - jours * 86400))


def _gd_url(mot: str) -> str:
    """The canonical search URL. The keyword is IN the path.

    Trap checked by hand: `?sc.keyword=analyste+financier` is silently
    ignored. The page answers 200, serves 30 well-formed cards — and talks about
    "Vendeur Projets" and "Aide familial(e)". The real keyword is the one
    designated by the offsets of the file name:

        france-analyste-esg-emplois-SRCH_IL.0,6_IN86_KO7,19.htm
                                         ^^^^^      ^^^^^^
        IL.0,6  the PLACE occupies characters 0 to 6 of the slug  → "france"
        IN86    the country identifier
        KO7,19  the KEYWORD occupies characters 7 to 19      → "analyste-esg"

    Getting it wrong here breaks nothing: it fills the queue with salespeople. It is
    worse than an error, it is an invisible error.
    """
    import unicodedata

    n = unicodedata.normalize("NFD", mot.lower())
    n = "".join(c for c in n if unicodedata.category(c) != "Mn")
    n = re.sub(r"-{2,}", "-", re.sub(r"[^a-z0-9]+", "-", n)).strip("-")
    debut = len("france-")
    return (
        f"{GD_HOTE}/Emploi/france-{n}-emplois"
        f"-SRCH_IL.0,6_IN{GD_LOC_FRANCE}_KO{debut},{debut + len(n)}.htm"
    )


def _gd_cartes(mot: str) -> list[Any]:
    """The cards of page 1 for a keyword, the whole of France."""
    import urllib.error
    import urllib.request

    url = _gd_url(mot)
    texte = ""
    for essai in (1, 2):
        try:
            with urllib.request.urlopen(  # nosec B310: scheme checked by exiger_http
                urllib.request.Request(exiger_http(url), headers=GD_UA), timeout=25
            ) as f:
                texte = _lire_borne(f).decode("utf-8", "replace")
            break
        except urllib.error.HTTPError as e:
            # A 403 gets NO second chance: it is a refusal of entry, not
            # a rate limit. On 2026-10-07, the 45 s rest then the
            # new attempt were paid on each of the 37 keywords
            # reached, and the step was killed at 40 min (same on 2026-10-03).
            if e.code == 429 and essai == 1:
                attente = int(e.headers.get("Retry-After") or GD_REPOS)
                _log.info(f"    ~ {mot} : HTTP {e.code}, repos {attente} s")
                time.sleep(min(attente, 300))
                continue
            _log.info(f"    ! {mot} : HTTP {e.code}")
            INCIDENTS["glassdoor"][f"HTTP {e.code}"] += 1
            if e.code in (403, 429):
                raise _IndeedBride(e.code)
            return []
        except Exception as e:
            _log.info(f"    ! {mot} : {type(e).__name__}")
            return []

    return _gd_parse(texte)


def _gd_parse(texte: str) -> list[Any]:
    """HTML of the search page → cards.

    Separate from the network so it can be tested on a saved page, without a request.
    """
    titres = list(_RX_GD_TITRE.finditer(texte))
    cartes = []
    for n, m in enumerate(titres):
        avant = texte[(titres[n - 1].end() if n else 0) : m.start()]
        apres = texte[m.end() : (titres[n + 1].start() if n + 1 < len(titres) else len(texte))]
        emp = _RX_GD_EMPLOYEUR.findall(avant)
        lieu = _RX_GD_LIEU.search(apres)
        sal = _RX_GD_SALAIRE.search(apres)
        age = _RX_GD_AGE.search(apres)
        ext = _RX_GD_EXTRAIT.search(apres)
        cartes.append(
            {
                "url": m.group(1),
                "titre": _gd_texte(m.group(2)),
                # The last name found BEFORE the title is this card's:
                # the earlier ones belong to the previous cards.
                "entreprise": _gd_texte(emp[-1]) if emp else "",
                "lieu": _gd_texte(lieu.group(1)) if lieu else "",
                "salaire": _gd_texte(sal.group(1)) if sal else "",
                "age": _gd_texte(age.group(1)) if age else "",
                "extrait": _gd_texte(ext.group(1)) if ext else "",
            }
        )
    return cartes


def scan_glassdoor(
    mots: list[str] | None = None, pause: float | None = None
) -> list[dict[str, Any]]:
    """Page 1 of the Glassdoor search, the whole of France, one pass per keyword.

    30 cards at most per request. The zone is judged afterwards on the card's
    place, since a city cannot be targeted: the city identifiers
    can only be obtained through /ajax/, forbidden to robots.
    """
    mots = mots or _commun.KEYWORDS
    pause = GD_PAUSE if pause is None else pause
    _EX = _commun.contrats_exclus()
    offers: list[dict[str, Any]] = []
    vus: set[str] = set()
    refus = refuses = 0
    _log.info(
        f"  Glassdoor : {len(mots)} mots-cles ({pause} s entre chaque, "
        f"~{len(mots) * pause // 60} min)"
    )
    for i, mot in enumerate(mots):
        if i:
            time.sleep(pause)
        try:
            cartes = _gd_cartes(mot)
            refus = 0
        except _IndeedBride as e:
            refuses += 1
            # REFUSAL OF ENTRY: we stop at the first one. A single 403 is enough because
            # it is never isolated — on 2026-10-07, 37 words out of 37 got
            # it, the new attempt only passing 7 times — and
            # each extra request prolongs the exclusion. The cost
            # of a chance 403: Glassdoor's remaining words, for one day.
            if e.args and e.args[0] == 403:
                _log.warning(
                    f"  ⏸ Glassdoor : refus d'entree (HTTP 403) — source fermee "
                    f"pour aujourd'hui, pas d'insistance, {len(offers)} offres "
                    f"conservees"
                )
                break
            refus += 1
            if refus >= GD_ABANDON:
                _log.warning(
                    f"  ⏸ Glassdoor : {refus} refus d'affilee (HTTP {e}) — passe "
                    f"arretee, {len(offers)} offres conservees"
                )
                break
            # Refusals ALTERNATING with successes: the in-a-row counter
            # reset to zero, and each word paid 45 s of rest. On
            # 2026-10-07, the pass was cut at 40 min by the timer, and WTJ,
            # which comes after, collected nothing.
            if refuses >= 2 * GD_ABANDON:
                _log.warning(
                    f"  ⏸ Glassdoor : {refuses} refus sur {i + 1} mots-cles — passe "
                    f"arretee, {len(offers)} offres conservees"
                )
                break
            continue
        for c in cartes:
            u = c["url"].split("?")[0]
            if not u or u in vus:
                continue
            vus.add(u)
            titre = c["titre"]
            if not titre or not title_ok(titre):
                continue
            # Glassdoor publishes no contract type: the title is all
            # we have, and it is silent one time in two. It is the main step back
            # compared to Indeed, better to write it than to discover it.
            ctr = contrat_du_titre(titre)
            if ctr in _EX:
                continue
            o = _mk(
                titre,
                c["url"],
                c["entreprise"] or "Glassdoor",
                c["lieu"],
                _gd_date(c["age"]),
                "glassdoor",
                c["extrait"],
            )
            o["contrat"] = ctr
            o["salaire"] = c["salaire"]
            o["desc_partielle"] = True
            offers.append(o)
    _log.warning(
        f"  ✓ Glassdoor → {len(offers)} offres ({refuses} requetes refusees) — "
        f"description = extrait, pas de contrat structure"
    )
    return offers
