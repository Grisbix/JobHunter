"""eFinancialCareers : le sitemap public declare dans robots.txt.

Partie de jobhunter.sources (ancien Scripts/job_sources.py, phase 3.4)."""

import json
import re
import time
from typing import Any
from urllib.parse import unquote, urlparse

from jobhunter import journal as _journal
from jobhunter.sources import commun as _commun
from jobhunter.sources.commun import (
    INCIDENTS,
    _mk,
    _norm_url,
    _strip_html,
    contrat_du_titre,
    en_france,
    title_ok,
)

_log = _journal.journal(__name__)


# ═══════════════ 8. eFinancialCareers — sitemap PUBLIC declare dans robots.txt ═══
# POURQUOI. Site d'emploi 100 % finance, francais, exactement le marche de l'utilisateur.
# Il etait deja connu de _SITES_EMPLOI (rang 2) mais JAMAIS scanne : les 5 entrees
# de la file etaient des pages de categorie ramassees ailleurs, sans description.
#
# CE QUE robots.txt AUTORISE (verifie le 2026-09-04). `/search` est interdit a
# `User-agent: *` — on n'y touche pas. En revanche le fichier DECLARE lui-meme
# le sitemap des offres recentes :
#     Sitemap: https://www.efinancialcareers.fr/sitemap-secure/latestjobs/xml
# C'est la voie d'acces que le site publie pour etre indexe : 8100 offres, et
# les pages d'offres ne sont pas interdites. `crawl-delay: 10` est respecte.
#
# Chaque fiche porte un <script type="application/ld+json"> de type JobPosting
# avec intitule, societe, lieu, date et description complete (~10 000 car.).
EFC_SITEMAP = "https://www.efinancialcareers.fr/sitemap-secure/latestjobs/xml"

EFC_DELAI = 10  # crawl-delay annonce par robots.txt — ne pas baisser

# LES AUTRES SITES DU MEME EDITEUR (verifie le 2026-09-24) : meme robots.txt,
# meme sitemap declare, meme crawl-delay 10, meme ld+json. 48 000 offres de
# plus, dont 93 intitules ESG absents de la file. Seul le .fr etait lu.
EFC_SITES = ("fr", "com", "co.uk", "de", "ch", "nl", "lu", "ie", "sg")


def _efc_sitemap(site: str) -> str:
    return f"https://www.efinancialcareers.{site}/sitemap-secure/latestjobs/xml"


EFC_UA = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    )
}

# Les URL ont la forme /emploi-<Pays>-<Ville>-<Titre>.id<N>. La ville peut
# contenir des tirets (« Levallois-Perret »), donc on ne cherche PAS a la
# separer du titre : decouper au premier tiret donnait ville « Levallois » et
# titre « Perret-Responsable Projets IA ». Le bloc ville+titre sert seulement au
# PRE-FILTRE ; les champs exacts viennent du ld+json de la fiche.
_RX_EFC_SLUG = re.compile(r"/(?:emploi|jobs)-[^-]+-(.+)\.id(\d+)$")

# Filtre ESG strict. `responsab` a ete retire apres mesure : il faisait entrer
# 581 titres dont la quasi-totalite etaient des « Responsable … » sans rapport.
#
# Les \b sont INDISPENSABLES : sans eux « RSE » matche n'importe quel mot qui
# contient ces trois lettres. Meme famille de bug que _TITRE_CONTRAT et
# _RX_STAGE, ou un \b perdu a l'ecriture avait rendu le motif inoperant.
# « climat » exclut explicitement « climatisation » : deux postes de technicien
# de zone Climatisation etaient remontes a la mesure.
_RX_EFC_ESG = re.compile(
    r"\bESG\b|\bRSE\b|\bSFDR\b|\bCSRD\b|extra.?financi|durabilit"
    r"|d[ée]veloppement durable|sustainab|climat(?!isation)|carbone|taxonomie"
    r"|impact invest|finance verte|green finance|transition [ée]nerg"
    r"|stewardship|responsible invest|net.zero|biodiversit",
    re.I,
)

# Programmes jeunes diplomes.
_RX_EFC_GRAD = re.compile(
    r"\bgraduate\b|jeune[s]? dipl|\bearly career\b|trainee program"
    r"|young (?:graduate|talent)",
    re.I,
)

# Le V.I.E se cherche SANS re.I, et c'est indispensable : « vie » insensible a
# la casse fait entrer toute l'assurance vie, qui pese lourd sur un site
# finance (« Gestionnaire Assurance Vie », « Middle office Assurance Vie »…).
# En majuscules, l'acronyme ne se confond avec rien.
_RX_EFC_VIE = re.compile(r"\bV\.?I\.?E\b")


def _est_graduate(titre: str) -> bool:
    """Programme jeune diplome ou V.I.E ?"""
    return bool(_RX_EFC_GRAD.search(titre) or _RX_EFC_VIE.search(titre))


# ── LE FILTRE PAR METIER, et pourquoi pas par secteur ──────────────────────
#
# eFinancialCareers EST le site d'emploi de la banque et de la gestion
# d'actifs : 8478 offres au sitemap, dont 32 seulement etaient en file. C'est
# de loin la plus grosse source non exploitee, et elle est sanctionnee
# (sitemap declare, crawl-delay 10 s).
#
# Premier essai : filtrer par SECTEUR. Echec — le slug du sitemap ne porte que
# l'intitule, pas l'employeur. « power » y trouvait « Power Platform »,
# « energie » y trouvait « Consultant transformation numerique Energie ». On
# remontait des missions de conseil, pas des postes chez un energeticien.
#
# On filtre donc sur le METIER de l'utilisateur. Mesure du 17/09 sur les 8478 :
#   7208 hors metier, 217 contrat exclu, 184 trop senior, 869 A LIRE.
#
# 869 fiches a 10 s font 144 minutes. Inutile de tenir un index de rotation :
# scan_efc ecarte deja les URL presentes en file, donc chaque passe avance
# d'elle-meme dans le reste.
_RX_EFC_METIER = re.compile(
    r"analyst|analyste|contr[oô]le de gestion|controlling|FP&A"
    r"|gestion de portefeuille|g[eé]rant|risk|risque|cr[eé]dit|credit"
    r"|valoris|valuation|M&A|corporate finance|private equity"
    r"|\bESG\b|\bISR\b|\bRSE\b|extra.?financ|durab|climat(?!isation)|carbon"
    r"|\bCSRD\b|\bSFDR\b|graduate|jeune dipl|junior|reporting",
    re.I,
)

# Postes hors de portee d'un profil sorti d'ecole. Les ecarter AVANT de payer
# 10 s de lecture : c'est le tri le moins cher qu'on puisse faire.
_RX_EFC_SENIOR = re.compile(
    r"senior|directeur|director|head of|responsable|manager|principal"
    r"|associate director|\bVP\b|expert|chef de",
    re.I,
)


def _est_metier(titre: str) -> bool:
    """Intitule compatible avec le profil, et pas deja trop senior ?"""
    return bool(_RX_EFC_METIER.search(titre)) and not _RX_EFC_SENIOR.search(titre)


def _efc_urls(client: Any, site: str = "fr") -> list[tuple[Any, str]]:
    """(url, titre approximatif) de chaque offre du sitemap. Une seule requete."""
    r = _commun._get_borne(client, _efc_sitemap(site), headers=EFC_UA, timeout=60)
    if r.status_code != 200:
        _log.info(f"  ~ eFC .{site} : sitemap injoignable (statut {r.status_code})")
        INCIDENTS[f"efc:{site}"][f"HTTP {r.status_code}"] += 1
        return []
    out = []
    for loc in re.findall(r"<loc>([^<]+)</loc>", r.text):
        m = _RX_EFC_SLUG.search(loc)
        if m:
            out.append((loc, unquote(m.group(1)).replace("_", " ").strip()))
    return out


def _efc_fiche(url: str, client: Any) -> dict[str, Any] | None:
    """JobPosting de la fiche, ou None. Ne leve jamais."""
    try:
        r = _commun._get_borne(client, url, headers=EFC_UA, timeout=30)
    except Exception:
        return None
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


def _efc_lieu(jp: Any) -> str:
    """Ville du JobPosting. jobLocation peut etre un objet ou une liste."""
    loc = jp.get("jobLocation")
    if isinstance(loc, list):
        loc = loc[0] if loc else None
    if not isinstance(loc, dict):
        return ""
    ad = loc.get("address") or {}
    return " ".join(
        str(ad.get(k) or "") for k in ("addressLocality", "addressRegion", "addressCountry")
    ).strip()


def scan_efc(
    limit: int = 40, filtre: str = "esg", sites: tuple[str, ...] = ("fr",)
) -> list[dict[str, Any]]:
    """Offres eFinancialCareers, description comprise.

    filtre :
      "esg"      — intitules qui parlent d'ESG (43 sur 8100) ;
      "graduate" — programmes jeunes diplomes et V.I.E ;
      "metier"   — les intitules compatibles avec le profil, seniors ecartes :
                   869 sur 8478 a la mesure du 17/09. C'est le gisement des
                   banques et de la gestion d'actifs, eFC etant leur site
                   d'emploi. Chaque passe avance dans le reste, les URL deja
                   en file etant ecartees ;
      "tout"     — tout ce que title_ok retient, soit ~2400 titres : a 10 s la
                   fiche c'est presque 7 h, pour un fit calcule sur des postes
                   bancaires generiques.
    """
    import httpx

    _EX = _commun.contrats_exclus()
    offers = []
    with httpx.Client(follow_redirects=True) as client:
        # Une offre publiee sur deux sites porte le meme identifiant : on ne la
        # lit qu'une fois.
        toutes, ids = [], set()
        for i, site in enumerate(sites):
            if i:
                time.sleep(EFC_DELAI)  # crawl-delay, sitemaps compris
            for url, approx in _efc_urls(client, site):
                m = _RX_EFC_SLUG.search(url)
                if m and m.group(2) in ids:
                    continue
                if m:
                    ids.add(m.group(2))
                toutes.append((url, approx))
        cibles = []
        for url, approx in toutes:
            if contrat_du_titre(approx) in _EX:
                continue
            if filtre == "esg":
                if not _RX_EFC_ESG.search(approx):
                    continue
            elif filtre == "graduate":
                if not _est_graduate(approx):
                    continue
            elif filtre == "metier":
                if not _est_metier(approx):
                    continue
            elif not title_ok(approx):
                continue
            cibles.append(url)
        # Fiches DEJA en file : ne pas les relire. A 10 s chacune, une seconde
        # passe repayait tout le temps de la premiere pour n'apporter que ce que
        # merge_into_queue aurait de toute facon deduplique.
        from jobhunter.stockage import file as queue_io

        connues = {_norm_url(x.get("url")) for x in queue_io.charger(_commun.QUEUE) if x.get("url")}
        neuves = [u for u in cibles if _norm_url(u) not in connues]
        deja = len(cibles) - len(neuves)
        # A TOUR DE ROLE entre les sites. Pris dans l'ordre des sitemaps, les
        # `limit` places allaient toutes au .fr, lu en premier : a l'essai, 8
        # fiches sur 8 etaient parisiennes et l'etranger n'etait jamais atteint.
        par_site: dict[str, Any] = {}
        for u in neuves:
            par_site.setdefault(urlparse(u).netloc, []).append(u)
        alterne = []
        while any(par_site.values()):
            for lst in par_site.values():
                if lst:
                    alterne.append(lst.pop(0))
        cibles = alterne[:limit]
        _log.info(
            f"  eFC : {len(toutes)} offres au sitemap → {len(cibles)} a lire "
            f"({deja} deja en file) "
            f"({EFC_DELAI} s entre chaque, {len(cibles) * EFC_DELAI // 60} min)"
        )
        for n, url in enumerate(cibles, 1):
            if n > 1:
                time.sleep(EFC_DELAI)  # crawl-delay: 10
            jp = _efc_fiche(url, client)
            if not jp:
                continue
            # Le ld+json porte des entites HTML dans le titre : sans unescape,
            # « Originateur &laquo; Sustainable banking » finissait tel quel dans
            # l'objet de la lettre. _strip_html ne s'applique qu'a la description.
            titre = __import__("html").unescape(str(jp.get("title") or ""))
            # eFC suffixe le titre du lieu et du mode de travail :
            # « … | Paris, FR | Hybride ». On ne garde que l'intitule.
            titre = re.sub(r"\s*\|.*$", "", titre).strip()
            lieu = _efc_lieu(jp)
            # Le titre exact du ld+json est plus fiable que le slug : on refait
            # les deux filtres dessus avant de garder l'offre.
            if not titre or not title_ok(titre) or contrat_du_titre(titre) in _EX:
                continue
            if not en_france(lieu):
                continue
            soc = (jp.get("hiringOrganization") or {}).get("name") or "eFinancialCareers"
            offers.append(
                _mk(
                    titre,
                    url,
                    soc,
                    lieu,
                    str(jp.get("datePosted") or "")[:10],
                    "efinancialcareers",
                    _strip_html(str(jp.get("description") or "")),
                )
            )
            if n % 10 == 0:
                _log.info(f"    … {n}/{len(cibles)} ({len(offers)} retenues)")
    _log.info(f"  ✓ eFinancialCareers → {len(offers)} offres (avec description)")
    return offers
