"""Workday : l'API publique des grands groupes.

Partie de jobhunter.sources (ancien Scripts/job_sources.py, phase 3.4).
"""

import time
from typing import Any

from jobhunter import journal as _journal
from jobhunter.sources import commun as _commun
from jobhunter.sources.commun import INCIDENTS, UA, _mk, _strip_html, title_ok

_log = _journal.journal(__name__)


# Court a dessein. Les 55 mots-cles de KEYWORDS viseraient LinkedIn, pas un flux
# d'entreprise ou l'on cherche un METIER dans un catalogue deja restreint.
WORKDAY_MOTS = [
    "ESG",
    "durable",
    "sustainability",
    "finance",
    "analyste",
    "analyst",
    "climat",
    "risque",
]

WORKDAY_PAGES = 2  # pages de 20 par mot-cle

WORKDAY_PAUSE = 0.6

WORKDAY_DETAILS = 25  # fiches detaillees par flux, au plus

WORKDAY_PARALLELE = 6  # flux lus en meme temps (un tenant = un site) ; 42 flux au 2026-10-08


def _workday_detail(httpx: Any, base: str, tenant: str, site: str, chemin: str) -> dict[str, Any]:
    """La fiche d'une offre : description, date reelle, pays, temps de travail."""
    try:
        r = _commun._post_borne(
            httpx,
            f"{base}/wday/cxs/{tenant}/{site}{chemin}",
            timeout=15,
            headers={**UA, "Accept": "application/json"},
        )
        if r.status_code != 200:
            r = _commun._get_borne(
                httpx,
                f"{base}/wday/cxs/{tenant}/{site}{chemin}",
                timeout=15,
                headers={**UA, "Accept": "application/json"},
            )
        if r.status_code != 200:
            return {}
        ji = (r.json() or {}).get("jobPostingInfo") or {}
    except Exception:
        return {}
    pays = (ji.get("country") or {}).get("descriptor") or ""
    return {
        "description": _strip_html(ji.get("jobDescription") or "")[:30000],
        "date": str(ji.get("startDate") or "")[:10],
        "location": ji.get("location") or "",
        "pays": pays,
        # « Full time » / « Part time » est un temps de travail, pas un contrat :
        # on ne le laisse pas remplir la colonne `contrat`, qui sert a filtrer.
        "temps": ji.get("timeType") or "",
    }


def fetch_workday(tenant: str, host: str, site: str, nom: str) -> list[dict[str, Any]]:
    """Les offres d'un flux Workday qui passent title_ok, descriptions comprises."""
    import httpx

    base = f"https://{tenant}.{host}.myworkdayjobs.com"
    vus, retenues = set(), []
    try:
        for mot in WORKDAY_MOTS:
            for page in range(WORKDAY_PAGES):
                r = _commun._post_borne(
                    httpx,
                    f"{base}/wday/cxs/{tenant}/{site}/jobs",
                    json={"appliedFacets": {}, "limit": 20, "offset": page * 20, "searchText": mot},
                    timeout=20,
                    headers={
                        **UA,
                        "Accept": "application/json",
                        "Content-Type": "application/json",
                    },
                )
                if r.status_code != 200:
                    INCIDENTS[f"workday:{tenant}"][f"HTTP {r.status_code}"] += 1
                    break
                postes = (r.json() or {}).get("jobPostings") or []
                if not postes:
                    break
                for j in postes:
                    chemin = j.get("externalPath") or ""
                    if not chemin or chemin in vus:
                        continue
                    vus.add(chemin)
                    titre = (j.get("title") or "").strip()
                    if titre and title_ok(titre):
                        retenues.append((titre, chemin, j.get("locationsText") or ""))
                time.sleep(WORKDAY_PAUSE)
    except Exception as e:
        INCIDENTS[f"workday:{tenant}"][type(e).__name__] += 1

    out = []
    for titre, chemin, lieu in retenues[:WORKDAY_DETAILS]:
        d = _workday_detail(httpx, base, tenant, site, chemin)
        # Le PAYS est servi en clair par l'API. C'est plus sur que de deviner
        # depuis un nom de ville, et en_france() sait lire « France ».
        lieu_final = ", ".join(x for x in (d.get("location") or lieu, d.get("pays")) if x)
        o = _mk(
            titre,
            f"{base}/{site}{chemin}",
            nom,
            lieu_final,
            d.get("date", ""),
            f"workday:{tenant}",
            d.get("description", ""),
        )
        out.append(o)
        time.sleep(WORKDAY_PAUSE)
    # Les offres sans fiche detaillee entrent quand meme : le titre et le lien
    # suffisent a les faire exister, l'auto-enrichissement fera le reste.
    for titre, chemin, lieu in retenues[WORKDAY_DETAILS:]:
        out.append(_mk(titre, f"{base}/{site}{chemin}", nom, lieu, "", f"workday:{tenant}"))
    return [o for o in out if o["titre"] and o["url"]]


def scan_workday() -> list[dict[str, Any]]:
    """Les flux en parallele, WORKDAY_PARALLELE a la fois.

    Chaque tenant est un site distinct : la pause par flux tient toujours, aucun n'est
    sollicite plus vite qu'avant. En serie, 27 flux a ~70 s depassaient le plafond de 30
    min de la passe 1a (2026-10-08).
    """
    import concurrent.futures as cf

    offres = []
    with cf.ThreadPoolExecutor(max_workers=WORKDAY_PARALLELE) as ex:
        futs = [(f[0], ex.submit(fetch_workday, *f)) for f in _commun.WORKDAY_FLUX]
        for tenant, fut in futs:
            got = fut.result()
            _log.info(f"  ✓ workday:{tenant} → {len(got)} offres retenues")
            offres.extend(got)
    return offres
