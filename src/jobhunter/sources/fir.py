"""FIR / French SIF : offres 100 % ISR-ESG.

Partie de jobhunter.sources (ancien Scripts/job_sources.py, phase 3.4)."""

import re

from jobhunter import journal as _journal
from jobhunter.sources import commun as _commun
from jobhunter.sources.commun import UA, _mk, title_ok

_log = _journal.journal(__name__)


# ═══════════════ 5. FIR / French SIF — offres 100 % ISR-ESG ═══════════════
# Forum pour l'Investissement Responsable : tableau d'offres exclusivement ISR/ESG.
# Densite sans equivalent (LinkedIn ramene ~15 % de pertinent, ici c'est 100 %).
# ⚠ Seules les offres presentes dans le HTML sont lues (~5). Les onglets par
# categorie (emplois / alternance / stages) chargent en JS et /jobs_categories/<c>/
# renvoie 404 ; l'API REST WordPress est fermee (wp-json -> 404). Un scraping
# navigateur recupererait le reste, au prix d'un lancement de Chromium.
FIR_URL = "https://www.frenchsif.org/isr_esg/emplois-et-stages/"


def fetch_fir():
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
        # Le contrat prefixe l'intitule (« CDI – Analyste ESG »). On le garde : il
        # porte une info utile (alternance/stage = cible junior).
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


def scan_fir():
    o = fetch_fir()
    _log.info(f"  ✓ FIR / French SIF → {len(o)} offres (100 % ISR-ESG)")
    return o
