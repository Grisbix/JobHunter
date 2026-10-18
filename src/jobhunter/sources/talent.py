"""Talent.com : agregateur.

Partie de jobhunter.sources (ancien Scripts/job_sources.py, phase 3.4)."""

import datetime
import re
import time

from jobhunter import journal as _journal
from jobhunter.sources import commun as _commun
from jobhunter.sources.commun import UA, _mk, title_ok

_log = _journal.journal(__name__)


# ═══════════════ 6. Talent.com — agregateur (remplace la couverture Indeed) ══════
# Indeed est INACCESSIBLE : Cloudflare bloque au niveau IP/empreinte TLS, y compris
# en fenetre reelle avec patchright+stealth (teste). Contourner une protection
# anti-bot est hors de question ; Talent.com agrege un vivier comparable et expose
# du JSON-LD schema.org propre, avec la DESCRIPTION incluse (elle manque a 755
# offres de la queue, dont la quasi-totalite vient d'Indeed).
#
# Cout : 1 requete de recherche + 1 par offre retenue. Le filtre title_ok est
# applique AVANT d'aller chercher le detail, pour ne pas payer les hors-sujet.
TALENT_SEARCH = "https://fr.talent.com/jobs?k={kw}&l=France"

_TALENT_LINK_RX = re.compile(r'href="(/view\?id=\d+)"')


def _talent_detail(httpx, url):
    """(titre, entreprise, lieu, date, description) depuis le JSON-LD JobPosting."""
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
        for n in nodes:
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


def fetch_talent(max_days=60, per_kw=20):
    """Offres Talent.com pour chaque mot-cle. max_days ecarte les annonces
    anciennes : le site sert des offres de plus d'un an (vu : datePosted 2025-06)."""
    from urllib.parse import quote as _q

    import httpx

    today = datetime.date.today()
    out, seen = [], set()
    # LES OFFRES DEJA DANS LA FILE NE SONT PAS RECHARGEES. Chaque fiche coute une
    # requete, et la collecte rechargeait tous les jours les memes : 30 min pour
    # Talent seul le 30/09, dans une passe bornee a 60. Leur description est
    # deja la ; seule une offre nouvelle merite sa fiche.
    try:
        from jobhunter.stockage import file as queue_io

        seen = {
            str(o.get("url") or "")
            for o in queue_io.charger(descriptions=False)
            if "talent.com" in str(o.get("url") or "")
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


def scan_talent():
    o = fetch_talent()
    _log.info(f"  ✓ Talent.com → {len(o)} offres (avec description)")
    return o
