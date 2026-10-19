"""V.I.E / V.I.A : Business France (civiweb).

Partie de jobhunter.sources (ancien Scripts/job_sources.py, phase 3.4)."""

import re
import time
from typing import Any

from jobhunter import journal as _journal
from jobhunter.sources import commun as _commun
from jobhunter.sources.commun import UA, _mk, title_ok

_log = _journal.journal(__name__)


# ═══════════════ 4. V.I.E / V.I.A — Business France (civiweb) ═══════════════
# Le site mon-vie-via est une SPA Nuxt : le HTML brut est une coquille vide, mais
# sa config publique (window.__NUXT__.config) livre l'endpoint et une clé d'API
# expédiée à TOUT visiteur. Elle ne donne accès qu'aux offres PUBLIQUES, les mêmes
# que la page affiche sans compte — pas de login, pas de données personnelles.
# En-tête attendu : x-api-key (Authorization et apikey renvoient 401).
VIE_API = "https://civiweb-api-prd.azurewebsites.net/api/Offers/search"

VIE_SITE = "https://mon-vie-via.businessfrance.fr/offres/recherche"

VIE_BASE = "https://mon-vie-via.businessfrance.fr"

_VIE_KEY_FALLBACK = "l+KwpoLPiXlsjxNT/NQ2iOFz8+iuygxAODs9FeAEWYM="


def _vie_key() -> str:
    """Clé lue en direct dans la config publique du site ; le fallback évite de
    tout casser si la page change, mais une clé figée finira par tourner.

    Deux pièges vérifiés :
      - la clé est échappée dans le HTML (`\\u002F` pour `/`) → à décoder, sinon 401 ;
      - « API_KEY » matche aussi GMAPS_API_KEY (clé Google Maps) → ancrer le nom.
    """
    import httpx

    try:
        r = _commun._get_borne(httpx, VIE_SITE, timeout=15, headers=UA, follow_redirects=True)
        m = re.search(r'(?:^|[^_A-Z])API_KEY\s*:\s*"([^"]{20,})"', r.text)
        if m:
            k = m.group(1).encode().decode("unicode_escape")
            if k.endswith("="):  # la clé civiweb est du base64
                return k
    except Exception:
        pass
    return _VIE_KEY_FALLBACK


def fetch_vie(limit: int = 1000) -> list[dict[str, Any]]:
    """Offres V.I.E/V.I.A. Intérêt pour un profil junior : contrat 12-24 mois,
    indemnité nette, et beaucoup de postes finance/ESG en filiale à l'étranger."""
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
            # Lien PROFOND vers l'offre. `{VIE_SITE}?id=<id>` menait a la page de
            # RECHERCHE generique : le bouton Postuler n'ouvrait pas l'offre.
            # Le site lui-meme pointe vers /offres/<id> (verifie : la page rend
            # bien l'offre et son bouton POSTULER).
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
    o = fetch_vie()
    _log.info(f"  ✓ V.I.E/V.I.A Business France → {len(o)} offres (après filtre métier)")
    return o
