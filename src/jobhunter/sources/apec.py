"""APEC.

Partie de jobhunter.sources (ancien Scripts/job_sources.py, phase 3.4).
"""

import json
import time
from typing import Any

from jobhunter import log as _journal
from jobhunter.network import exiger_http
from jobhunter.sources import common as _commun
from jobhunter.sources.common import (
    INCIDENTS,
    UA,
    _lire_borne,
    _mk,
    _strip_html,
    contrat_de_la_description,
    contrat_du_titre,
    title_ok,
)

_log = _journal.journal(__name__)


# ═══════════════ APEC — Indeed's replacement ═══════════════
#
# WHY. Indeed returned 0 offers on 17/09: 184 requests in one afternoon
# exhausted the tolerance, and twelve probes spread over five hours did not get
# a single answer. A source covering the same need was needed — the
# wide French market, with contract, publication date and salary.
#
# APEC is France's job site for MANAGERS AND PROFESSIONALS, and it is the cleanest
# route met in this project:
#
#   robots.txt        309 bytes, NO Disallow for "User-agent: *"
#   declared sitemap  sitemap_offres_search_engine.xml.gz, dedicated to the offers
#   API               cms/webservices/rechercheOffre, without a key or an account
#
# WHAT IT GIVES, EXACTLY. A request returns 50 offers at once, each
# with an excerpt of 283 characters — measured: min 283, median 283, max 283,
# it is a clean truncation. Longer than Indeed's 160 and
# Glassdoor's 159, but it is NOT the whole posting: I had written the opposite
# here before measuring.
#
# The full posting is not accessible: the detail API
# (cms/webservices/offre/...) answers 401, and the HTML page is a 53 KB
# Angular shell without a line of the posting, nor ld+json. So we stop at
# the excerpt — the link, for its part, opens normally in the user's browser.
#
# On the other hand, and it is what makes it precious: the publication date is
# timestamped, the salary is in plain text ("A partir de 50 k€ brut annuel", 23 out of
# 23 filled in when measured), and `indicateurFaibleCandidature` flags the
# offers with little competition — nobody else publishes that.
#
# The sitemap only lists 1288 SEARCH URLs by function and sector,
# not the offers. It is the API that serves, and the sitemap that attests it is
# made to be read.
APEC_API = "https://www.apec.fr/cms/webservices/rechercheOffre"

APEC_FICHE = "https://www.apec.fr/candidat/recherche-emploi.html/emploi/detail-offre/"

APEC_PAUSE = 2  # no crawl-delay announced; we stay courteous

APEC_PAR_PAGE = 50

# THE CONTRACT CODES, ESTABLISHED BY CROSS-CHECKING — not guessed. The API returns a
# reference identifier without a label. So we crossed the code with the
# titles that name the contract in plain text, over seven requests:
#
#   101888   303 offers, 3 explicit titles, ALL "CDI"
#   101887    30 offers, 6 explicit titles, ALL "CDD"
#   597137     2 offers, 2 explicit titles, ALL "Alternance"
#   101889    21 offers, NO explicit title     -> not mapped
#
# No code is shared between two contracts. The codes without proof stay
# out: better "non précisé" than a wrong column — it is the one that
# serves to filter, and four Credit Agricole internships labelled CDD had
# already risen to the top of the ranking.
#
# This mapping only comes in as a LAST RESORT: a title that says "CDD 8
# mois" always wins over the code.
_APEC_CONTRAT = {101888: "CDI", 101887: "CDD", 597137: "Alternance"}

# REFUSALS IN A ROW BEYOND WHICH WE STOP. APEC is behind DataDome: on the
# evening of 2026-10-02, after ~540 requests from a link audit, its 55 searches
# all returned 403. Insisting on the next 52 brings nothing and
# prolongs the exclusion. Three refusals in a row: the source is closed
# for today.
APEC_ABANDON = 3


def _apec_page(mot: str, debut: int) -> tuple[Any, int]:
    """An APEC results page. Empty list on refusal."""
    import urllib.error
    import urllib.request

    corps = json.dumps(
        {
            "motsCles": mot,
            "pagination": {"range": APEC_PAR_PAGE, "startIndex": debut},
            "sorts": [{"type": "DATE", "direction": "DESCENDING"}],
            "activeFiltre": True,
        }
    ).encode("utf-8")
    tetes = dict(UA)
    tetes["Content-Type"] = "application/json"
    tetes["Accept"] = "application/json"
    try:
        r = urllib.request.Request(exiger_http(APEC_API), data=corps, headers=tetes, method="POST")
        with urllib.request.urlopen(r, timeout=30) as f:  # nosec B310 : scheme checked by exiger_http
            d = json.loads(_lire_borne(f).decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        _log.info(f"    ! {mot} : HTTP {e.code}")
        INCIDENTS["apec"][f"HTTP {e.code}"] += 1
        return None, 0
    except Exception as e:
        _log.info(f"    ! {mot} : {type(e).__name__}")
        return [], 0
    return d.get("resultats") or [], d.get("totalCount") or 0


def scan_apec(mots: list[str] | None = None, pages: int = 2) -> list[dict[str, Any]]:
    """APEC offers: title, company, place, date, salary, 283-character excerpt.

    `pages`: pages of 50 per keyword. A page costs ONE request, hence the best yield
    of all our sources — but the excerpt stays an excerpt, and the offers go with
    `desc_partielle` so that URL promotion never replaces a complete posting with
    these 283 characters.
    """
    mots = mots or _commun.KEYWORDS
    _EX = _commun.contrats_exclus()
    offers, vus = [], set()
    _log.info(
        f"  APEC : {len(mots)} mots-cles x {pages} page(s) de {APEC_PAR_PAGE} "
        f"({APEC_PAUSE} s entre chaque)"
    )
    fait = refus = 0
    for mot in mots:
        if refus >= APEC_ABANDON:
            _log.warning(
                f"  ⏸ APEC : {refus} refus d'affilee — source fermee pour aujourd'hui, "
                f"pas d'insistance"
            )
            break
        for p in range(pages):
            if fait:
                time.sleep(APEC_PAUSE)
            fait += 1
            res, total = _apec_page(mot, p * APEC_PAR_PAGE)
            if res is None:
                refus += 1
                break
            refus = 0
            if not res:
                break
            for o in res:
                num = o.get("numeroOffre") or o.get("id")
                if not num or num in vus:
                    continue
                vus.add(num)
                titre = (o.get("intitule") or "").strip()
                if not titre or not title_ok(titre):
                    continue
                desc = _strip_html(o.get("texteOffre") or "")
                # The title first, then the excerpt, then APEC's code.
                # In this order: a title that says "CDD 8 mois" is surer
                # than a reference identifier, and 283 characters are not
                # enough to decide — 583 offers out of 654 came out as
                # "non précisé" before the code was used.
                ctr = (
                    contrat_du_titre(titre)
                    or contrat_de_la_description(desc, "")
                    or _APEC_CONTRAT.get(o.get("typeContrat"), "")
                )
                if ctr in _EX:
                    continue
                x = _mk(
                    titre,
                    APEC_FICHE + str(num),
                    (o.get("nomCommercial") or "APEC").strip(),
                    o.get("lieuTexte") or "",
                    str(o.get("datePublication") or "")[:10],
                    "apec",
                    desc,
                )
                x["contrat"] = ctr
                x["salaire"] = (o.get("salaireTexte") or "").strip()
                # 283 characters are not a posting: without this flag, the
                # URL promotion would replace a complete description with this
                # excerpt. Same guard as for Indeed and Glassdoor.
                x["desc_partielle"] = True
                # Few candidates: APEC is the only one to publish it, and it is
                # exactly what makes the difference on an application.
                if o.get("indicateurFaibleCandidature"):
                    x["peu_de_candidats"] = True
                offers.append(x)
            if len(res) < APEC_PAR_PAGE:
                break
    rares = sum(1 for x in offers if x.get("peu_de_candidats"))
    _log.info(
        f"  ✓ APEC → {len(offers)} offres sur {fait} requetes "
        f"(extrait de 283 car., {rares} a faible candidature)"
    )
    return offers
