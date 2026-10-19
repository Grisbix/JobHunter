"""Welcome to the Jungle : le sitemap public.

Partie de jobhunter.sources (ancien Scripts/job_sources.py, phase 3.4).
"""

import json
import re
import time
from typing import Any

from jobhunter import journal as _journal
from jobhunter.sources import commun as _commun
from jobhunter.sources.commun import (
    _mk,
    _norm_url,
    _strip_html,
    contrat_du_titre,
    en_france,
    title_ok,
)
from jobhunter.sources.efc import _RX_EFC_ESG, _efc_lieu

_log = _journal.journal(__name__)


# ═══════════════ 3. Welcome to the Jungle — sitemap public ═══════════════
_WTJ_JS = r"""
() => {
  const out=[]; const seen=new Set();
  document.querySelectorAll('a[href*="/fr/companies/"][href*="/jobs/"]').forEach(a=>{
    const t=(a.innerText||'').trim().split('\n')[0];
    if(!t||t.length<6||seen.has(a.href))return;
    seen.add(a.href);
    const card=a.closest('li,article,[class*="card"]')||a.parentElement;
    const txt=(card?card.innerText:'').split('\n').map(s=>s.trim()).filter(Boolean);
    out.push({title:t,url:a.href,company:txt[1]||'',location:txt.find(s=>/paris|lyon|bordeaux|remote|télétravail|france/i.test(s))||''});
  });
  return out;
}"""


def _wtj_429(pg: Any) -> bool:
    """WTJ nous bride-t-il ? Lisible MEME quand la navigation a echoue : la page d'erreur porte « Too Many Requests » alors que robust_goto rend ok=False."""
    try:
        return "too many requests" in pg.evaluate("document.body.innerText.slice(0,200)").lower()
    except Exception:
        return False


WTJ_SITEMAP = "https://www.welcometothejungle.com/sitemaps/index.xml.gz"

# Mesure : le challenge CloudFront de WTJ tombe apres ~3 minutes (202, 202, 200
# a 60 s d'intervalle). Attendre rapporte donc quelques fiches de plus par
# passe ; s'arreter au premier 202 en rendait zero.
WTJ_REPOS = 200  # secondes d'attente quand le mur tombe

WTJ_PATIENCE = 2  # nombre maximum d'attentes par passe

# 2 et non plus 6 (2026-10-02) : six attentes de 200 s faisaient 20 min d'immobilite
# dans une passe bornee a 60, pour un mur qui retombait aussitot la plupart du temps.


def _wtj_fiche(url: str, client: Any) -> dict[str, Any] | None:
    """JobPosting d'une fiche WTJ, ou None.

    Meme balisage que eFinancialCareers : un <script type="application/ld+json"> destine
    a Google.

    Leve `Bloque` sur 202/429 : c'est le challenge anti-bot de CloudFront, il
    vaut pour l'IP entiere et insister ne sert a rien. Surtout, 202 est un code
    de SUCCES — le confondre avec une page vide ferait passer le mur pour une
    fiche sans description.
    """
    from jobhunter.programmes.wtj_desc import UA as _WUA
    from jobhunter.programmes.wtj_desc import Bloque

    try:
        r = _commun._get_borne(client, url, headers=_WUA, timeout=30)
    except Exception:
        return None
    if r.status_code in (202, 429):
        raise Bloque(r.status_code)
    if r.status_code != 200:
        return None
    for bloc in re.findall(
        r'<script type="application/ld\+json"[^>]*>(.*?)</script>', r.text, re.S
    ):
        try:
            o = json.loads(bloc)
        except Exception:
            continue
        if isinstance(o, dict) and o.get("@type") == "JobPosting":
            return o
    return None


def scan_wtj(pages: int = 2) -> list[dict[str, Any]]:
    """Offres Welcome to the Jungle, via le SITEMAP declare dans robots.txt.

    L'ANCIENNE VERSION VISAIT UNE ROUTE INTERDITE, ET MORTE. Elle construisait
    des URL `/fr/jobs?query=<mots>`. Or le robots.txt de WTJ porte, noir sur
    blanc :

        disallow: */jobs?query=*
        Disallow: /*?

    C'est exactement ce qu'on demandait. Et depuis, WTJ a retire la recherche
    libre : `/fr/jobs?query=…` ignore le parametre et sert une page de
    presentation de leur produit « matching », la vraie recherche etant passee
    derriere une authentification (`/fr/authenticate/signin?redirect=/fr/jobs`).
    Le scan ne pouvait donc plus rien rendre — d'ou les 429 a repetition et les
    « 0 offre » silencieux.

    LA VOIE OUVERTE. Le meme robots.txt declare un sitemap :
        Sitemap: https://www.welcometothejungle.com/sitemaps/index.xml.gz
    Neuf fichiers `job-listings.N.xml.gz`, 88 000 annonces, 60 000 en francais.
    Les pages `/fr/companies/<slug>/jobs/<slug>` ne sont interdites nulle part.

    LE DEBIT RESTE BRIDE. Apres quelques fiches, CloudFront bascule l'IP sur un
    challenge et repond 202 avec un corps vide (voir wtj_desc.py, meme mur). On
    lit donc peu de fiches par passe, on s'arrete des le premier 202, et on
    garde ce qui est lu. `pages` est conserve pour la compatibilite des
    appelants et sert de plafond : pages * 5 fiches.
    """
    import gzip

    import httpx

    from jobhunter.programmes.wtj_desc import UA as _WUA
    from jobhunter.programmes.wtj_desc import Bloque

    _EX = _commun.contrats_exclus()
    offers: list[dict[str, Any]] = []

    def _lire(client: Any, url: str) -> str:
        r = _commun._get_borne(client, url, headers=_WUA, timeout=90)
        if r.status_code != 200:
            return ""
        b: bytes = r.content
        if b[:2] == b"\x1f\x8b":
            b = gzip.decompress(b)
        return b.decode("utf-8", "replace")

    with httpx.Client(follow_redirects=True) as client:
        try:
            idx = _lire(client, WTJ_SITEMAP)
        except Exception as e:
            _log.info(f"  ~ WTJ : sitemap injoignable ({type(e).__name__})")
            return offers
        fichiers = [l for l in re.findall(r"<loc>([^<]+)</loc>", idx) if "job-listings" in l]
        if not fichiers:
            _log.info("  ~ WTJ : aucun sitemap d'offres dans l'index")
            return offers

        cibles = []
        for f in fichiers:
            try:
                t = _lire(client, f)
            except Exception:
                continue
            for l in re.findall(r"<loc>([^<]+)</loc>", t):
                if "/fr/companies/" not in l or "/jobs/" not in l:
                    continue
                # Le slug porte l'intitule, en minuscules et sans accents : il
                # sert au PRE-FILTRE. Le vrai titre vient du ld+json de la fiche.
                approx = l.split("/jobs/")[-1].replace("-", " ")
                if contrat_du_titre(approx) in _EX:
                    continue
                if _RX_EFC_ESG.search(approx):
                    cibles.append(l)

        # On ne relit pas ce qui est deja en file : chaque fiche coute une
        # requete sur un debit tres limite.
        from jobhunter.stockage import file as queue_io

        connues = {
            _norm_url(x.get("url"))
            for x in queue_io.charger(_commun.QUEUE, descriptions=False)
            if x.get("url")
        }
        neuves = [u for u in cibles if _norm_url(u) not in connues]
        plafond = max(1, pages) * 5
        _log.info(
            f"  WTJ : {len(cibles)} offres ESG au sitemap, {len(neuves)} nouvelles "
            f"— {min(len(neuves), plafond)} lue(s) cette passe (le reste au prochain scan)"
        )

        # PATIENCE. Le mur de WTJ n'est pas definitif : mesure a la seconde, il
        # tombe apres ~3 minutes. S'arreter au premier 202 rendait 0 offre a
        # chaque passe alors qu'attendre en donne quelques-unes de plus. On
        # attend donc, un nombre limite de fois, et on rend la main ensuite.
        # Ce n'est pas un contournement : on ralentit, on ne force rien.
        etat = {"attentes": 0}

        def _fiche_patiente(url: str) -> Any:
            """JobPosting, ou None si WTJ nous ferme la porte pour de bon.

            Rend None UNIQUEMENT quand la patience est epuisee : l'appelant sait
            alors qu'il doit arreter la source, pas seulement sauter une fiche.
            """
            while True:
                try:
                    return _wtj_fiche(url, client) or {}
                except Bloque as e:
                    if etat["attentes"] >= WTJ_PATIENCE:
                        _log.info(f"  ~ {e} — arret WTJ apres {etat['attentes']} attente(s).")
                        return None
                    etat["attentes"] += 1
                    _log.info(f"  ~ {e} — pause {WTJ_REPOS} s ({etat['attentes']}/{WTJ_PATIENCE})…")
                    time.sleep(WTJ_REPOS)

        for u in neuves[:plafond]:
            jp = _fiche_patiente(u)
            if jp is None:  # mur durable : on rend la main
                break
            if not jp:  # fiche illisible : on passe a la suivante
                continue
            # UNE SEULE REQUETE PAR OFFRE. La description et l'intitule vivent
            # dans le MEME bloc ld+json : les chercher par deux appels separes
            # doublait la consommation d'un quota deja minuscule — le mur
            # tombait deux fois plus vite, pour rien.
            d = _strip_html(str(jp.get("description") or ""))
            if len(d) < 200:
                continue
            titre = str(jp.get("title") or "").strip()
            lieu = _efc_lieu(jp)
            if not titre or not title_ok(titre) or contrat_du_titre(titre) in _EX:
                continue
            if not en_france(lieu):
                continue
            soc = (jp.get("hiringOrganization") or {}).get("name") or "Welcome to the Jungle"
            offers.append(
                _mk(titre, u, soc, lieu, str(jp.get("datePosted") or "")[:10], "wtj-sitemap", d)
            )
    _log.info(f"  \u2713 Welcome to the Jungle \u2192 {len(offers)} offres (avec description)")
    return offers
