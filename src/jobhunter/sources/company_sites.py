"""The offers of the companies already seen, read on their own career sites.

The user, 2026-10-27: « un outil qui cherche les offres des sites carrière des
entreprises stockées », then « améliore la recherche de sites d'entreprises ». The
register of companies seen (storage.companies, some 5,000 names) keeps every company
a collection met; this source asks each of them, a slice per run, what it has open
now, by the first way that works:

1. **its recruiting tool's public API** (Greenhouse, Workday…), when an offer link
   gave the tool — the register's, or one this source learned before;
2. **freehire** (sources.freehire), which reads 470,000 companies' career sites: its
   company search, then the company's open jobs. Its search is fuzzy (« Mirova »
   answers « Mirvac »), so only a company whose name is the same, or the same
   followed by more words (« Amundi Ireland Limited »), is kept. Its job links are
   the company's own: the tool they show is learned, and the next run reads that
   tool directly;
3. **the tool guessed from the name**: the tenant « amundi » in the user's Workday
   directory (sources.discovery, from Common Crawl), then the account « amundi » asked
   of Greenhouse, Lever, Ashby, SmartRecruiters and Recruitee, one request each. Kept
   only if it has open offers and, where the tool says whose account it is, under the
   same name;
4. **its career page**: one of its offer pages already in the queue, read once, for
   the link or frame of the tool behind it.

Followed companies are skipped (their feed is collected anyway). A company is asked
again after `DELAI` days, doubled each time it had nothing (7, 14, 28, then 56 days);
each run takes the `PAR_PASSE` least recently asked, the most recently seen first.
What was asked when, and the tools learned, are kept in `_company_sites.json`, next
to the queue. The freehire requests count against its daily quota. At the end of the
run, the followed feeds dead for 60 days are suspended (sources.feeds.suspendre_morts).

Polite by design: the project names itself, one request at a time with a pause; a
refusal stops the way that met it for the run. Nothing is bypassed.
"""

from __future__ import annotations

import json
import re
import time
import unicodedata
from datetime import date, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from jobhunter import log as _journal
from jobhunter.sources import common as _commun
from jobhunter.sources.aggregators import AGREG_PAUSE, _agreg_offre, _Garde, _quota_atteint
from jobhunter.sources.common import INCIDENTS
from jobhunter.storage.atomic import ecrire_json

_log = _journal.journal(__name__)

NOM_ETAT = "_company_sites.json"
PAR_PASSE = 150
DELAI = 7  # days before a company is asked again; doubled for each empty answer
PAR_ENTREPRISE = 50  # open jobs read per company (freehire's maximum page)
ENTITES = 3  # freehire companies kept per name (« Amundi », « Amundi Ireland »…)
DEVINES = 40  # companies whose tool is guessed per run (≤ 8 requests each)
PAGES = 30  # career pages read per run
UA = {"User-Agent": "Grisbix/JobHunter (+https://github.com/Grisbix/JobHunter)"}

# Job boards and aggregators: their pages are not the company's career site.
_PAS_LE_SITE = (
    "linkedin.",
    "indeed.",
    "welcometothejungle.",
    "apec.fr",
    "francetravail.",
    "pole-emploi.",
    "hellowork.",
    "glassdoor.",
    "jooble.",
    "adzuna.",
    "efinancialcareers.",
    "europa.eu",
    "jobteaser.",
    "monster.",
    "cadremploi.",
    "freehire.",
    "talent.com",
    "jobijoba.",
    "meteojob.",
    "mon-vie-via.",
    "civiweb.",
    "arbeitsagentur.",
    "stepstone.",
    "google.",
)
_RX_LIEN = re.compile(r"""https?://[^\s"'<>\\]+""")


def chemin_etat() -> Path:
    """When each company was last asked, and the tools learned, next to the queue."""
    return Path(_commun.QUEUE).parent / NOM_ETAT


def lire_etat() -> dict[str, Any]:
    """{"demandes": {company: {"le", "offres", "vides"}}, "flux": {company: feed}}.

    Before 3.44 the file was {company: date}: read as asks.
    """
    try:
        d = json.loads(chemin_etat().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        d = {}
    if not isinstance(d, dict):
        d = {}
    if "demandes" not in d and "flux" not in d:
        d = {"demandes": {k: {"le": v} for k, v in d.items() if isinstance(v, str)}, "flux": {}}
    d.setdefault("demandes", {})
    d.setdefault("flux", {})
    return d


def _plat(texte: object) -> str:
    t = unicodedata.normalize("NFKD", str(texte or "").casefold())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^\w]+", " ", t).split())


def meme_entreprise(cible: str, nom: str) -> bool:
    """« Amundi » is « AMUNDI », « Amundi Ireland Limited »; not « Mirvac » for « Mirova »."""
    a, b = _plat(cible), _plat(nom)
    return bool(a) and (b == a or b.startswith(a + " "))


def _suivis() -> tuple[set[tuple[str, str]], set[str]]:
    """The feeds followed, as (tool, key) — Workday by its tenant."""
    _commun._load_cfg()
    flux = {(o, str(s).lower()) for o, slugs in _commun.ATS_SLUGS.items() for s in slugs}
    flux |= {("workday", str(x[0]).lower()) for x in _commun.WORKDAY_FLUX}
    flux |= {(str(x[0]), str(x[1]).lower()) for x in _commun.AUTRES_FLUX}
    noms = {_plat(x[3]) for x in _commun.WORKDAY_FLUX if len(x) > 3}
    noms |= {_plat(x[2]) for x in _commun.AUTRES_FLUX if len(x) > 2}
    return flux, noms


def _demande(v: Any) -> tuple[str, int]:
    """(last asked, empty answers in a row) of an ask, the old form (a date) included."""
    if isinstance(v, str):
        return v, 0
    if isinstance(v, dict):
        return str(v.get("le") or ""), int(v.get("vides") or 0)
    return "", 0


def delai(vides: int) -> int:
    """Days before asking again: 7, then 14, 28, 56 after empty answers."""
    return int(DELAI * 2 ** min(max(vides, 0), 3))


def a_demander(
    reg: dict[str, dict[str, Any]],
    etat: dict[str, Any],
    jour: str,
    n: int = PAR_PASSE,
    appris: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """The register's companies to ask this run: not followed, not asked too recently.

    Args:
        reg: the register of companies seen (storage.companies).
        etat: {company: ask} (`lire_etat()["demandes"]`; a date is the old form).
        jour: today, ISO.
        n: how many to ask.
        appris: the feeds learned by earlier runs, {company: feed}.

    Never asked first, then the least recently asked; on a tie, the most recently seen.
    """
    flux_suivis, noms_suivis = _suivis()
    appris = appris or {}
    aujourd_hui = date.fromisoformat(jour)
    candidates = []
    for k, e in reg.items():
        fl = e.get("flux") or appris.get(k) or {}
        if fl:
            c = fl.get("cle")
            ident = (fl.get("outil"), str(c[0] if isinstance(c, list) else c).lower())
            if ident in flux_suivis:
                continue
        if _plat(e.get("nom") or k) in noms_suivis:
            continue
        vu, vides = _demande(etat.get(k))
        if vu and vu > (aujourd_hui - timedelta(days=delai(vides))).isoformat():
            continue
        candidates.append((vu, "" if not e.get("derniere_vue") else e["derniere_vue"], k, e))
    candidates.sort(key=lambda x: (x[0], _inverse(x[1])))
    return [{**e, "_cle": k} for _, _, k, e in candidates[:n]]


def _inverse(jour: str) -> str:
    """Sorts dates newest first inside an ascending sort."""
    return "".join(chr(0x10FFFF - ord(c)) for c in jour)


def _flux(url: str) -> dict[str, Any] | None:
    """The feed an address shows, as the register keeps it; None if no known tool."""
    from jobhunter import inventory

    trouve = inventory.flux_depuis_url(url)
    if not trouve:
        return None
    outil, ident = trouve
    return {"outil": outil, "cle": list(ident) if isinstance(ident, tuple) else ident, "url": url}


def _par_flux(e: dict[str, Any], fl: dict[str, Any] | None = None) -> list[dict[str, Any]] | None:
    """The company's offers by its tool's API; None if its tool cannot be read here."""
    from jobhunter.inventory import AUTRES_OUTILS
    from jobhunter.sources import ats as _ats
    from jobhunter.sources import workday as _workday

    fl = fl or e.get("flux") or {}
    outil, cle = fl.get("outil"), fl.get("cle")
    nom = str(e.get("nom") or "")
    if outil == "workday" and isinstance(cle, list) and len(cle) == 3:
        return _workday.fetch_workday(cle[0], cle[1], cle[2], nom)
    if outil in AUTRES_OUTILS and isinstance(cle, str):
        return _ats.fetch_autre(outil, cle, nom)
    if outil and isinstance(cle, str):
        return _ats.fetch_ats(outil, cle)
    return None


def _par_freehire(
    httpx: Any, e: dict[str, Any], garde: Any, ex: Any
) -> tuple[list[dict[str, Any]] | None, dict[str, Any] | None]:
    """(the company's open jobs in freehire under its exact name, the tool they show).

    The jobs are None if freehire was not asked (quota, refusal).
    """
    from jobhunter.sources import freehire as _fh

    nom = str(e.get("nom") or "")
    if garde.fini or _quota_atteint("freehire"):
        return None, None
    r = _commun._get_borne(
        httpx,
        _fh.API.replace("/jobs/search", "/companies"),
        timeout=25,
        headers=_fh.UA,
        params={"q": nom, "limit": 10},
    )
    if not garde.reponse(r):
        return None, None
    slugs = [
        str(c.get("slug"))
        for c in (r.json() or {}).get("data") or []
        if c.get("slug") and c.get("job_count") and meme_entreprise(nom, str(c.get("name") or ""))
    ][:ENTITES]
    out: list[dict[str, Any]] = []
    appris = None
    for slug in slugs:
        if garde.fini or _quota_atteint("freehire"):
            break
        time.sleep(AGREG_PAUSE)
        r = _commun._get_borne(
            httpx,
            _fh.API.replace("/jobs/search", f"/companies/{slug}"),
            timeout=25,
            headers=_fh.UA,
            params={"limit": PAR_ENTREPRISE},
        )
        if not garde.reponse(r):
            continue
        for j in ((r.json() or {}).get("data") or {}).get("jobs") or []:
            lien = _fh.lien_d_origine(str(j.get("url") or ""))
            appris = appris or _flux(lien)  # before the title filter: any job shows it
            o = _agreg_offre(
                j.get("title"),
                lien,
                nom,
                j.get("location"),
                j.get("posted_at") or j.get("created_at"),
                f"sites-carrieres:{j.get('source') or 'freehire'}",
                j.get("description"),
                None,
                ex,
            )
            if o:
                out.append(o)
    return out, appris


# ── The tool guessed from the name ───────────────────────────────────────────────
OUTILS_DEVINES = ("greenhouse", "lever", "ashby", "smartrecruiters", "recruitee")


def comptes_possibles(nom: str) -> list[str]:
    """« Société Générale » → ["societegenerale", "societe-generale"]; short names none.

    A guessed account must be the whole name: « axa » or « ey » would be anyone's.
    """
    mots = _plat(nom).replace("_", " ").split()
    colle = "".join(mots)
    if len(colle) < 5:
        return []
    return list(dict.fromkeys([colle, "-".join(mots)]))


def _essai(httpx: Any, outil: str, compte: str, nom: str) -> int:
    """Open offers of `compte` on `outil` if it is this company's account, else 0."""
    from jobhunter.sources import discovery

    if outil == "greenhouse":  # the board names its company
        r = _commun._get_borne(
            httpx, f"https://boards-api.greenhouse.io/v1/boards/{compte}", timeout=15, headers=UA
        )
        if r.status_code != 200 or not meme_entreprise(nom, str((r.json() or {}).get("name"))):
            return 0
    if outil == "smartrecruiters":  # each posting names its company
        r = _commun._get_borne(
            httpx,
            f"https://api.smartrecruiters.com/v1/companies/{compte}/postings?limit=1",
            timeout=15,
            headers=UA,
        )
        if r.status_code != 200:
            return 0
        d = r.json() or {}
        postes = d.get("content") or []
        if not postes or not meme_entreprise(
            nom, str((postes[0].get("company") or {}).get("name"))
        ):
            return 0
        return int(d.get("totalFound") or 0)
    return discovery.offres_ouvertes((outil, compte)) or 0


def annuaire_workday() -> dict[str, list[tuple[str, str, str]]]:
    """{tenant: its career sites} from the user's Workday directory (sources.discovery)."""
    from jobhunter.sources import discovery

    out: dict[str, list[tuple[str, str, str]]] = {}
    for s in discovery.charger_annuaire()["sites"]:
        if isinstance(s, list) and len(s) == 3:
            out.setdefault(str(s[0]).lower(), []).append((str(s[0]), str(s[1]), str(s[2])))
    return out


def deviner(
    httpx: Any, nom: str, workday: dict[str, list[tuple[str, str, str]]] | None = None
) -> dict[str, Any] | None:
    """The company's account on a tool read by API, guessed from its name; None if none.

    Args:
        httpx: the httpx module.
        nom: the company's name.
        workday: the Workday directory by tenant (`annuaire_workday()`): a tenant that is
            the whole name, with open offers, is the company's.
    """
    from jobhunter import inventory
    from jobhunter.sources import discovery

    for compte in comptes_possibles(nom):
        for t, wd, site in (workday or {}).get(compte.replace("-", ""), [])[:3]:
            time.sleep(AGREG_PAUSE / 2)
            if (discovery.offres_ouvertes(("workday", (t, wd, site))) or 0) > 0:
                url = f"https://{t}.{wd}.myworkdayjobs.com/{site}"
                return {"outil": "workday", "cle": [t, wd, site], "url": url, "par": "nom"}
        for outil in OUTILS_DEVINES:
            if outil == "recruitee" and "-" in compte:
                continue  # one guess is enough for a host name
            time.sleep(AGREG_PAUSE / 2)
            try:
                n = _essai(httpx, outil, compte, nom)
            except Exception as x:
                INCIDENTS["sites-carrieres"][type(x).__name__] += 1
                continue
            if n > 0:
                url = inventory.URL_FLUX.get(outil, "").format(compte)
                return {"outil": outil, "cle": compte, "url": url, "par": "nom"}
    return None


# ── The career page behind an offer ─────────────────────────────────────────────
def page_de_l_entreprise(url: str) -> bool:
    """An offer address on the company's own site, not a job board's nor a known tool's."""
    hote = urlparse(url).netloc.lower()
    return bool(hote) and not any(x in hote for x in _PAS_LE_SITE) and _flux(url) is None


def outil_dans_la_page(html: str) -> dict[str, Any] | None:
    """The first tool read by API that a career page links to or frames."""
    for lien in _RX_LIEN.findall(html or ""):
        f = _flux(lien.replace("&amp;", "&"))
        if f:
            return {**f, "par": "page"}
    return None


def lire_la_page(httpx: Any, url: str) -> dict[str, Any] | None:
    """The tool behind a career page, by reading it once; None if none or unreachable."""
    try:
        r = _commun._get_borne(httpx, url, timeout=15, headers=UA, follow_redirects=True)
    except Exception as x:
        INCIDENTS["sites-carrieres"][type(x).__name__] += 1
        return None
    if r.status_code != 200:
        return None
    return outil_dans_la_page(str(getattr(r, "text", "") or ""))


def _pages_par_entreprise() -> dict[str, list[str]]:
    """{company: its offer addresses on its own site}, from the queue."""
    from jobhunter.storage import companies
    from jobhunter.storage import queue as queue_io

    out: dict[str, list[str]] = {}
    try:
        file = queue_io.charger(_commun.QUEUE, descriptions=False)
    except Exception:
        return out
    for o in file:
        u = str(o.get("url") or "")
        if u.startswith("http") and page_de_l_entreprise(u):
            out.setdefault(companies.cle(o.get("entreprise")), []).append(u)
    return out


def scan_company_sites(n: int = PAR_PASSE) -> list[dict[str, Any]]:
    """Asks `n` companies of the register what they have open now.

    Returns:
        Their offers that pass the title filter.
    """
    import httpx

    from jobhunter import root
    from jobhunter.sources import feeds
    from jobhunter.storage import companies

    jour = date.today().isoformat()
    reg = companies.charger(_commun.QUEUE)
    etat = lire_etat()
    demandes, appris = etat["demandes"], etat["flux"]
    lot = a_demander(reg, demandes, jour, n, appris)
    pages = _pages_par_entreprise() if lot else {}
    workday = annuaire_workday() if lot else {}
    ex = _commun.contrats_exclus()
    garde = _Garde("freehire")
    out: list[dict[str, Any]] = []
    vu = {"outil": 0, "freehire": 0, "nom": 0, "page": 0, "appris": 0}
    devines = lues = 0
    for i, e in enumerate(lot):
        k = e["_cle"]
        if i:
            time.sleep(AGREG_PAUSE)
        try:
            fl = e.get("flux") or appris.get(k)
            offres = _par_flux(e, fl) if fl else None
            if offres is not None:
                vu["outil"] += 1
            else:
                offres, fl_fh = _par_freehire(httpx, e, garde, ex)
                if fl_fh and k not in appris:
                    appris[k] = {**fl_fh, "par": "freehire"}
                    vu["appris"] += 1
                if offres:
                    vu["freehire"] += 1
                if offres is not None and not offres and k not in appris:
                    # Nothing in freehire: guess its tool, else read its own page.
                    trouve = None
                    if devines < DEVINES:
                        devines += 1
                        trouve = deviner(httpx, str(e.get("nom") or k), workday)
                    if trouve is None and lues < PAGES and pages.get(k):
                        lues += 1
                        trouve = lire_la_page(httpx, pages[k][0])
                    if trouve:
                        appris[k] = trouve
                        vu[trouve["par"]] += 1
                        offres = _par_flux(e, trouve) or []
                if offres is None:
                    continue  # not asked (quota, refusal): asked again next run
            outil = (fl or appris.get(k) or {}).get("outil", "")
            for o in offres:
                if not str(o.get("source") or "").startswith("sites-carrieres:"):
                    o["source"] = f"sites-carrieres:{outil}"
        except Exception as x:
            INCIDENTS["sites-carrieres"][type(x).__name__] += 1
            continue
        out.extend(offres)
        _, vides = _demande(demandes.get(k))
        demandes[k] = {"le": jour, "offres": len(offres), "vides": 0 if offres else vides + 1}
    ecrire_json(chemin_etat(), {"demandes": demandes, "flux": appris})
    morts = feeds.suspendre_morts(_commun.SOURCES_CFG, root.scripts() / feeds.FICHIER)
    _log.info(
        f"  ✓ sites carrières → {len(out)} offres ({vu['outil']} entreprises par leur outil, "
        f"{vu['freehire']} par freehire ; outils appris : {vu['appris']} par freehire, "
        f"{vu['nom']} par le nom, {vu['page']} par leur page ; "
        f"{sum(k not in demandes for k in reg)} jamais demandées)"
    )
    if morts:
        _log.info(
            f"  ⏸ {len(morts)} flux suivis morts depuis {feeds.MORT_JOURS} j, suspendus : "
            + ", ".join(sorted(morts))
        )
    return out
