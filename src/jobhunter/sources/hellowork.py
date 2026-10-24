"""HelloWork: the job-category pages, then the offer pages. Outside `--all`.

Part of jobhunter.sources. Tried on 2026-10-24 at the owner's request (AGENTS.md,
"Sites to try"): HelloWork's terms (art. 8.2) forbid automated extraction, a risk
the owner accepts for personal use. What robots.txt allows is all that is read:

- `/fr-fr/emploi/index-categorie.html`, then `index-domaine_<x>.html`: the list of
  HelloWork's job names ("analyste-isr", "analyste-financier"…), kept in
  `_hellowork_metiers.json` and read again every 30 days (about 65 pages).
- `/fr-fr/emploi/metier_<job>.html`: the category pages of the jobs whose name passes
  the profile's title filter, plus the profile keywords that are job names; their
  first 20 offers each. Pagination and search take a `?`, which robots.txt
  disallows: not used.
- `/fr-fr/emplois/<id>.html`: the offer, with a JobPosting ld+json block.

The declared sitemap (`/fr-fr/horizon.xml`) answers 403 behind Cloudflare: not used.

The card's title is filtered first (profile title filter), then at most `limite`
new offers are opened, one at a time, with a pause. A refusal (403, 429, a Cloudflare
page) stops the pass and is counted in INCIDENTS; no workaround is tried.
"""

import datetime
import html
import json
import re
import time
import unicodedata
from typing import Any

from jobhunter import log as _journal
from jobhunter import root as _racine
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

BASE = "https://www.hellowork.com"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
HELLOWORK_PAUSE = 2.0  # seconds between two pages
HELLOWORK_METIERS = 15  # category pages read per pass at most
METIERS_JOURS = 30  # age of the job-name list before it is read again
METIERS_FICHIER = "_hellowork_metiers.json"

# The offer card of a category page: link, then "Title - Company" in its title attribute.
_RX_CARTE = re.compile(r'href="(/fr-fr/emplois/\d+\.html)"\s+title="([^"]*)"')
# The page writes the type as `application/ld&#x2B;json`: the "+" is HTML-escaped.
_RX_LDJSON = re.compile(
    r'<script[^>]*type="application/ld(?:\+|&#x2B;|&#43;)json"[^>]*>(.*?)</script>', re.S
)
_RX_SLUG = re.compile(r"[^a-z0-9]+")
_RX_DOMAINE = re.compile(r'href="/fr-fr/emploi/(index-domaine_[\w-]+\.html)"')
_RX_METIER = re.compile(r'href="/fr-fr/emploi/metier_([\w-]+)\.html"')


class Refus(Exception):
    """HelloWork refused a page: the pass stops."""


def slug_metier(mot: str) -> str:
    """The job slug of HelloWork's category pages: "Analyste ESG" -> "analyste-esg"."""
    t = unicodedata.normalize("NFKD", mot.lower()).encode("ascii", "ignore").decode()
    return _RX_SLUG.sub("-", t).strip("-")


def cartes(texte: str) -> list[tuple[str, str]]:
    """(offer URL, card title) of a category page, without duplicates."""
    vues: set[str] = set()
    sortie = []
    for chemin, titre in _RX_CARTE.findall(texte):
        url = BASE + chemin
        if url in vues:
            continue
        vues.add(url)
        # "Title - Company": the company is after the last " - ".
        sortie.append((url, html.unescape(titre).rsplit(" - ", 1)[0].strip()))
    return sortie


def fiche(texte: str) -> dict[str, Any] | None:
    """The JobPosting of an offer page, or None."""
    for bloc in _RX_LDJSON.findall(texte):
        try:
            o = json.loads(bloc)
        except ValueError:
            continue
        for x in o if isinstance(o, list) else [o]:
            if isinstance(x, dict) and x.get("@type") == "JobPosting":
                return x
    return None


def metiers_de_page(texte: str) -> list[str]:
    """The job names linked from an index page, in order, without duplicates."""
    return list(dict.fromkeys(_RX_METIER.findall(texte)))


def _metiers(client: Any) -> list[str]:
    """HelloWork's job names: from the local list, read again when it is 30 days old."""
    chemin = _racine.dans(_commun.HERE, METIERS_FICHIER)
    limite = (datetime.date.today() - datetime.timedelta(days=METIERS_JOURS)).isoformat()
    try:
        d = json.loads(chemin.read_text(encoding="utf-8"))
        if str(d.get("le", "")) >= limite and d.get("metiers"):
            return list(d["metiers"])
    except (OSError, ValueError, AttributeError):
        pass
    r = _lire(client, f"{BASE}/fr-fr/emploi/index-categorie.html")
    metiers = metiers_de_page(r.text) if r is not None else []
    for page in dict.fromkeys(_RX_DOMAINE.findall(r.text if r is not None else "")):
        time.sleep(HELLOWORK_PAUSE)
        rp = _lire(client, f"{BASE}/fr-fr/emploi/{page}")
        if rp is not None:
            metiers += metiers_de_page(rp.text)
    metiers = list(dict.fromkeys(metiers))
    if metiers:
        try:
            chemin.write_text(
                json.dumps({"le": datetime.date.today().isoformat(), "metiers": metiers}),
                encoding="utf-8",
            )
        except OSError:
            pass
    return metiers


def choisir_metiers(metiers: list[str], mots: list[str]) -> list[str]:
    """The job names to read, the closest to the profile's keywords first.

    Each keyword word (3 letters or more) weighs 1 / the number of keywords that use it:
    "isr" or "carbone" (one keyword) outweighs "analyste" (twenty). A job name scores the
    weights of the words it shares; the keywords that are job names come first, then the
    names that pass the title filter, best score first. Without it the 15 pages read were
    whatever the title filter let through first (measured: accounting assistants, then
    "analyste-isr" in 69th place, for a sustainable-finance profile).
    """
    connus = set(metiers)
    exacts = [m for m in (slug_metier(x) for x in mots) if m in connus]
    usages: dict[str, int] = {}
    for x in mots:
        for j in set(slug_metier(x).split("-")):
            if len(j) >= 3:
                usages[j] = usages.get(j, 0) + 1

    def proximite(m: str) -> float:
        return sum(1 / usages[j] for j in set(m.split("-")) if j in usages)

    autres = [m for m in metiers if proximite(m) and title_ok(m.replace("-", " "))]
    autres.sort(key=proximite, reverse=True)  # stable: HelloWork's order among equals
    return list(dict.fromkeys(exacts + autres))


def _lire(client: Any, url: str) -> Any:
    """The page, None when it does not exist; raises Refus on a refusal of entry."""
    r = _commun._get_borne(client, url, headers=UA, timeout=30)
    if r.status_code in (404, 410):
        return None
    if r.status_code != 200 or "cf-error-details" in r.text[:20000]:
        INCIDENTS.noter("hellowork", f"HTTP {r.status_code}")
        raise Refus(r.status_code)
    return r


def scan_hellowork(limite: int = 30) -> list[dict[str, Any]]:
    """HelloWork offers of the profile's keywords that pass its filters, description included."""
    import httpx

    _EX = _commun.contrats_exclus()
    offers: list[dict[str, Any]] = []
    from jobhunter.storage import queue as queue_io

    connues = {
        _norm_url(x.get("url"))
        for x in queue_io.charger(_commun.QUEUE, descriptions=False)
        if x.get("url")
    }
    cibles: dict[str, str] = {}
    with httpx.Client(follow_redirects=True) as client:
        try:
            metiers = choisir_metiers(_metiers(client), list(_commun.KEYWORDS))
            _log.info(f"  HelloWork : {len(metiers)} métier(s) au filtre du titre")
            for m in metiers[:HELLOWORK_METIERS]:
                r = _lire(client, f"{BASE}/fr-fr/emploi/metier_{m}.html")
                time.sleep(HELLOWORK_PAUSE)
                if r is None:
                    continue  # no category page for this keyword
                for url, titre in cartes(r.text):
                    if (
                        title_ok(titre)
                        and contrat_du_titre(titre) not in _EX
                        and _norm_url(url) not in connues
                    ):
                        cibles.setdefault(url, titre)
            _log.info(
                f"  HelloWork : {len(cibles)} offres nouvelles au filtre du titre "
                f"— {min(len(cibles), limite)} lue(s) cette passe"
            )
            for url in list(cibles)[:limite]:
                r = _lire(client, url)
                time.sleep(HELLOWORK_PAUSE)
                jp = fiche(r.text) if r is not None else None
                if not jp:
                    continue
                titre = html.unescape(str(jp.get("title") or "")).strip()
                lieu = _efc_lieu(jp)
                if not titre or not title_ok(titre) or contrat_du_titre(titre) in _EX:
                    continue
                if not en_france(lieu):
                    continue
                soc = (jp.get("hiringOrganization") or {}).get("name") or "HelloWork"
                d = _strip_html(str(jp.get("description") or ""))
                quand = str(jp.get("datePosted") or "")[:10]
                offers.append(_mk(titre, url, str(soc), lieu, quand, "hellowork", d))
        except Refus as e:
            _log.info(f"  ~ HelloWork : refus (HTTP {e}) — arrêt de la passe, sans contournement")
        except Exception as e:
            INCIDENTS.noter("hellowork", type(e).__name__)
            _log.info(f"  ~ HelloWork : {type(e).__name__} — arrêt de la passe")
    _log.info(f"  ✓ HelloWork → {len(offers)} offres (avec description)")
    return offers
