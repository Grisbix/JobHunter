"""Indeed: the results page, and nothing else.

Part of jobhunter.sources (formerly Scripts/job_sources.py, phase 3.4).
"""

import json
import re
import sys
import time
from typing import Any, NoReturn
from urllib.parse import quote

from jobhunter import lazy as _paresseux
from jobhunter import log as _journal
from jobhunter.network import exiger_http
from jobhunter.scoring import zones as _zones
from jobhunter.sources import common as _commun
from jobhunter.sources.common import (
    HERE,
    INCIDENTS,
    _lire_borne,
    _mk,
    _strip_html,
    contrat_du_titre,
    title_ok,
)

_log = _journal.journal(__name__)


_ici = sys.modules[__name__]
# Values taken from the profile: computed on first read, not at import
# (jobhunter.lazy). In this module, they are read through `_ici.NAME`.
_PARESSEUX: _paresseux.Fabriques = {}


def __getattr__(nom: str) -> Any:
    return _paresseux.lire(_ici, _PARESSEUX, nom)


# ═══════════════ Indeed — the RESULTS PAGE, and nothing else ═══════════════
# What we read and what we do not. The boundary is not technical, it
# is deliberate, and it deserves to be written in black and white:
#
#   /jobs?q=…&l=…   ALLOWED. The "User-agent: *" block of robots.txt starts
#                   with "Allow: /"; of its 468 Disallow lines, none
#                   targets the search. Only the COUNTRY paths are closed
#                   (/jobs/FR/, /jobs/CA/…), which is not the same URL.
#   /viewjob?jk=…   FORBIDDEN — "Disallow: /viewjob?", line 170. We
#                   NEVER fetch it. The URL is stored so that the user
#                   opens it themselves in their browser: storing a link
#                   is not crawling.
#   page 2 and up   &start=10 answers 307 to secure.indeed.com/auth, with
#                   "branding=page-two-signin". It is a LOGIN wall,
#                   not an anti-bot. We stop at page 1, i.e. 15 cards
#                   per request, and the volume comes from the number of requests.
#
# The mobile API apis.indeed.com/graphql serves all that without any of these
# limits — full description included. It requires a key extracted from
# Indeed's iOS application (that is what JobSpy does, 4300 stars). That
# key is not ours: we do not use it. It is not a technical
# impossibility, it is a choice, and it is the only gap between them and us.
#
# DESIGN CONSEQUENCE. Indeed is a DISCOVERY source, not a
# file source. The snippet is 140 to 165 characters where fit_score works on
# the whole posting. rang_source ranks it 1 (aggregator): as soon as another
# source publishes the same posting, its link takes the place back. What Indeed
# brings and the others give us badly is the FRAME — contract type
# (15/15 of the cards measured), REAL publication date, remote work,
# salary. Three fields where the queue is almost empty today.
INDEED_HOTE = "https://fr.indeed.com"

# No crawl-delay announced in robots.txt, but a very real throttling — and
# one that does NOT respond to the pace. Measured, six identical requests each time:
#
#   pause 15 s :  403 403 403 200 200 200   → 3 refus
#   pause 25 s :  200 403 403 403 403 403   → 5 refus
#
# Slowing down improves nothing: it is not a rate, it is a sliding quota per
# address, which fills up and drains. No Retry-After header.
#
# THE QUOTA DRAINS FOR THE DAY, NOT FOR THE MINUTE. Log of the day
# of 17/09, same machine:
#
#   1st pass, 28 requests    → 61 offers, about half refused
#   2e passe (16 requetes)   → 2 reponses, 14 refus
#   3rd pass, 110 requests   → 0 offers, gave up at the 6th request
#
# Between the 2nd and the 3rd, two hours of waiting refilled nothing. Pulling on an
# empty quota only keeps it empty, and each refusal costs 45 s of rest
# plus two requests.
#
# HENCE THE BUDGET. A pass stops at INDEED_BUDGET requests, and it does not
# take up the same keywords again: it starts where the previous one
# stopped. 55 keywords x 2 cities = 110 pairs, i.e. about five days to
# go round — which suits offers that live several weeks.
INDEED_PAUSE = 12  # enough not to weigh, no point going slower

INDEED_BUDGET = 20  # requests per pass; beyond that the quota is dry

INDEED_ETAT = HERE / ".indeed_rotation"  # where the previous pass stopped

INDEED_REPOS = 45  # rest after a refusal, before the only second chance

# Since 04/10: 403/challenge refusal = immediate stop; 429 quota = one
# bounded retry, then stop. The Cloudflare challenge was observed for real.
# Search places: the profile's priority sectors (zones.py).
_PARESSEUX["INDEED_LIEUX"] = lambda: (
    [s["libelle"] for s in _zones.SECTEURS_PRIORITAIRES] or ["France"]
)

# We present ourselves for what we are. Measured, the three cases:
#   « JobHunter/1.0 … »   → 200, 1 108 971 o
#   aucun UA (Python-urllib) → 403
#   a Chrome UA           → 200
# Indeed refuses the library's DEFAULT agent, not robots: a plain
# name is enough. No need to disguise ourselves as a browser, so we do not.
INDEED_UA = {
    "User-Agent": "JobHunter/1.0 (recherche d'emploi personnelle)",
    "Accept-Language": "fr-FR,fr;q=0.9",
}

_RX_INDEED_BLOB = re.compile(r'providerData\["mosaic-provider-jobcards"\]\s*=\s*')

# "Temps plein" and "Temps partiel" are working times, not
# contracts: letting them through would fill the `contrat` column with values that
# are useless for filtering. They are ignored, and a card that carries
# only them leaves without a contract — "non precise" stays an honest answer.
_INDEED_CONTRAT = {
    "cdi": "CDI",
    "cdd": "CDD",
    "stage": "Stage",
    "alternance": "Alternance",
    "apprentissage": "Alternance",
    "freelance": "Freelance",
    "independant": "Freelance",
    "interim": "Interim",
    "temporaire": "Interim",
}


class _IndeedBride(Exception):
    """Indeed throttled after a second chance.

    We stop the pass and KEEP what was read: an interrupted pass is better
    than a lost pass, and the next scan will take up the remaining keywords.
    """


def _json_objet(texte: str, depart: int) -> str:
    r"""The complete JSON object that starts at the `depart` brace.

    A non-greedy expression (\\{.*?\\};) would stop at the first "};"
    met, including inside a string. Indeed's blob is 54 kB
    and contains description HTML: we count the braces, skipping what
    is between quotes.
    """
    prof = 0
    chaine = False
    echap = False
    for i in range(depart, len(texte)):
        c = texte[i]
        if chaine:
            if echap:
                echap = False
            elif c == "\\":
                echap = True
            elif c == '"':
                chaine = False
            continue
        if c == '"':
            chaine = True
        elif c == "{":
            prof += 1
        elif c == "}":
            prof -= 1
            if prof == 0:
                return texte[depart : i + 1]
    return ""


class _IndeedBloque(Exception):
    """Refus explicite, connexion requise ou réponse inexploitable : arrêt."""


INDEED_REQUETES = 0


def _indeed_cartes(mot: str, lieu: str) -> list[Any]:
    """Reads the public page; tells refusal, quota and valid empty response apart."""
    import urllib.error
    import urllib.request
    from email.utils import parsedate_to_datetime

    global INDEED_REQUETES
    url = f"{INDEED_HOTE}/jobs?q={quote(mot)}&l={quote(lieu)}"

    def bloque(raison: str) -> NoReturn:
        INCIDENTS["indeed"][raison] += 1
        raise _IndeedBloque(raison)

    for essai in (1, 2):
        try:
            INDEED_REQUETES += 1
            with urllib.request.urlopen(  # nosec B310: scheme checked by exiger_http
                urllib.request.Request(exiger_http(url), headers=INDEED_UA), timeout=25
            ) as f:
                if "secure.indeed.com" in f.geturl():
                    bloque("connexion requise")
                if f.headers.get("cf-mitigated", "").lower() == "challenge":
                    bloque("challenge anti-bot")
                texte = _lire_borne(f).decode("utf-8", "replace")
            break
        except _IndeedBloque:
            raise
        except urllib.error.HTTPError as e:
            code = e.code
            retry_after = e.headers.get("Retry-After") if e.headers else None
            e.close()
            if code in (401, 403):
                bloque(f"HTTP {code}")
            INCIDENTS["indeed"][f"HTTP {code}"] += 1
            if code != 429:
                raise _IndeedBloque(f"HTTP {code}")
            attente: float = INDEED_REPOS
            if retry_after:
                try:
                    attente = max(0, int(retry_after))
                except ValueError:
                    try:
                        attente = max(
                            0, parsedate_to_datetime(retry_after).timestamp() - time.time()
                        )
                    except (TypeError, ValueError, OverflowError):
                        pass
            # Never retry before a Retry-After greater than the budget.
            if essai == 2 or attente > 300:
                raise _IndeedBride(429)
            _log.warning(f"    ~ {mot} / {lieu} : HTTP 429, repos {attente:g} s")
            time.sleep(attente)
        except Exception as e:
            bloque(type(e).__name__)
    if re.search(r"<title[^>]*>[^<]*(?:security check|just a moment|captcha)", texte, re.I):
        bloque("challenge anti-bot")
    m = _RX_INDEED_BLOB.search(texte)
    if not m:
        bloque("format de page non reconnu")
    brut = _json_objet(texte, texte.find("{", m.end()))
    try:
        d = json.loads(brut)
        resultats: list[Any] = d["metaData"]["mosaicProviderJobCardsModel"]["results"]
        if not isinstance(resultats, list) or any(not isinstance(c, dict) for c in resultats):
            raise ValueError("results doit être une liste de cartes")
    except (ValueError, TypeError, KeyError):
        bloque("format des offres non reconnu")
    return resultats


def _indeed_contrat(job_types: Any) -> str:
    """['Temps plein', 'CDI'] → 'CDI'. Rien de reconnu → ''."""
    import unicodedata

    for t in job_types or []:
        n = unicodedata.normalize("NFD", str(t).lower())
        n = "".join(c for c in n if unicodedata.category(c) != "Mn").strip()
        if n in _INDEED_CONTRAT:
            return _INDEED_CONTRAT[n]
    return ""


def _indeed_date(ms: int) -> str:
    """Epoch in milliseconds → 'YYYY-MM-DD'. It is the REAL publication date.

    It is better than the scan date: the queue carries 2634 offers dated
    the same day, the one on which we saw them. A value outside reasonable bounds
    is rejected rather than converted to 1970.
    """
    try:
        s = float(ms) / 1000.0
    except Exception:
        return ""
    if not (946684800 < s < time.time() + 86400):  # between 2000 and tomorrow
        return ""
    return time.strftime("%Y-%m-%d", time.localtime(s))


def scan_indeed(
    mots: list[str] | None = None,
    lieux: list[str] | None = None,
    pause: float | None = None,
    *,
    persist: bool = True,
) -> list[dict[str, Any]]:
    """Page 1 of Indeed results, for each (keyword, place) pair.

    15 cards at most per request — it is the login wall of page 2
    that sets this cap, not us. The yield therefore comes from the product
    keywords x places.

    The pass only handles a SLICE of this product, INDEED_BUDGET pairs, and
    resumes where the previous one stopped. Indeed's quota drains for
    the day: a pass that tries the 110 pairs gets no more
    than one that tries 20, it only loses an hour in useless rests.
    """
    mots = mots or _commun.KEYWORDS
    lieux = lieux or _ici.INDEED_LIEUX
    pause = INDEED_PAUSE if pause is None else pause
    _EX = _commun.contrats_exclus()
    offers = []
    vus = set()

    # All the pairs, flat: the rotation is on the PAIR, not on the
    # keyword. Otherwise a pass of 20 requests would cover 10 keywords on two
    # cities, and the next slice would start again on the same cities.
    couples = [(m, l) for m in mots for l in lieux]
    depart = 0
    try:
        depart = int(INDEED_ETAT.read_text(encoding="utf-8").strip()) % len(couples)
    except Exception:
        pass
    tranche = [
        couples[(depart + i) % len(couples)] for i in range(min(INDEED_BUDGET, len(couples)))
    ]
    _log.info(
        f"  Indeed : {len(tranche)} couples sur {len(couples)} "
        f"(depuis le n° {depart + 1}, {pause} s entre chaque, "
        f"~{len(tranche) * pause // 60} min)"
    )

    fait = 0
    debut_http = INDEED_REQUETES
    bloque_raison = ""
    bride = False
    for mot, lieu in tranche:
        if fait:
            time.sleep(pause)
        fait += 1
        try:
            cartes = _indeed_cartes(mot, lieu)
        except _IndeedBloque as e:
            bloque_raison = str(e)
            _log.info(f"  Indeed : source indisponible ({e}) — arrêt sans réessai")
            break
        except _IndeedBride as e:
            bride = True
            _log.info(f"  Indeed : quota HTTP {e} — arrêt de la passe")
            break
        for c in cartes:
            jk = c.get("jobkey")
            if not jk or jk in vus:
                continue
            vus.add(jk)
            # Indeed itself marks dead postings. That is
            # exactly what the availability check goes looking for,
            # offer by offer: here it is given.
            if c.get("expired"):
                continue
            titre = (c.get("title") or c.get("displayTitle") or "").strip()
            if not titre or not title_ok(titre):
                continue
            ctr = _indeed_contrat(c.get("jobTypes"))
            if (ctr or contrat_du_titre(titre)) in _EX:
                continue
            o = _mk(
                titre,
                f"{INDEED_HOTE}/viewjob?jk={jk}",
                (c.get("company") or "").strip() or "Indeed",
                c.get("formattedLocation") or lieu,
                _indeed_date(c.get("pubDate")),
                "indeed",
                _strip_html(c.get("snippet") or ""),
            )
            o["contrat"] = ctr
            o["teletravail"] = (c.get("remoteWorkModel") or {}).get("text") or ""
            o["salaire"] = (c.get("salarySnippet") or {}).get("text") or ""
            # The snippet is NOT the posting: 160 characters against
            # several thousand. Without this flag, URL promotion
            # would overwrite a full description already in the queue with this
            # resume. Voir merge_into_queue.
            o["desc_partielle"] = True
            offers.append(o)
        if fait % 10 == 0:
            _log.info(f"    … {fait}/{len(tranche)} ({len(offers)} retenues)")

    # WHERE TO RESUME TOMORROW. We advance by what was REALLY tried, not by the
    # budget: a pass stopped at the 6th refusal only covered six pairs, and
    # starting twenty further on would skip fourteen keywords that were never
    # tried. An empty quota must not dig a hole in the list.
    try:
        if persist:
            INDEED_ETAT.write_text(str((depart + fait) % len(couples)), encoding="utf-8")
    except Exception:
        pass

    etat = "indisponible" if bloque_raison else "quota atteint" if bride else "terminé"
    _log.info(
        f"  Indeed [{etat}] : {len(offers)} offres, {fait} couples, "
        f"{INDEED_REQUETES - debut_http} tentatives HTTP"
    )
    if bride:
        _log.info(
            f"    reprise au couple n° {(depart + fait) % len(couples) + 1} "
            f"sur {len(couples)} a la prochaine passe"
        )
    return offers
