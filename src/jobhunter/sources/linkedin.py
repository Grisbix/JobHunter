"""LinkedIn : la recherche PUBLIQUE (API invite), avec attente sur 429.

Partie de jobhunter.sources (ancien Scripts/job_sources.py, phase 3.4)."""

import re
import time
from urllib.parse import quote

from jobhunter import journal as _journal
from jobhunter.sources import commun as _commun
from jobhunter.sources.commun import INCIDENTS, UA, _mk, title_ok

_log = _journal.journal(__name__)


# ═══════════════ 2. LinkedIn recherche PUBLIQUE (guest, httpx, paginé) ═══════════════
_LI_CARD = re.compile(
    r'<a[^>]+class="[^"]*base-card__full-link[^"]*"[^>]+href="([^"]+)"[^>]*>.*?'
    r'<span class="sr-only">\s*(.*?)\s*</span>',
    re.S,
)

_LI_COMP = re.compile(r"base-search-card__subtitle[^>]*>.*?>([^<]+)<", re.S)

_LI_LOC = re.compile(r"job-search-card__location[^>]*>([^<]+)<", re.S)


def linkedin_guest_search(keyword, pages=2, days=7, lieu="France"):
    """API guest LinkedIn (HTML fragments, AUCUN login, lecture publique).
    Pagination par start=0,25,50… f_TPR filtre fraîcheur (604800s=7j).

    `lieu` etait code en dur sur « France ». Desactiver le filtre geographique
    a l'entree de la file ne servait donc a rien pour cette source : elle ne
    DEMANDAIT que des offres francaises. Un filtre en aval ne peut pas rattraper
    ce qu'une requete en amont n'a jamais demande."""
    import html as _html

    import httpx

    out = []
    for p in range(pages):
        if _LI["stop"]:
            return out
        url = (
            "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
            f"?keywords={quote(keyword)}&location={quote(lieu)}"
            f"&f_TPR=r{days * 86400}&start={p * 25}"
        )
        try:
            r = _commun._get_borne(httpx, url, timeout=15, headers=UA)
            # Une limite de debit s'ATTEND : meme page, apres la pause.
            while r.status_code == 429:
                INCIDENTS["linkedin_http"][429] += 1
                if not _li_pause_429(r):
                    _LI["stop"] = "429"
                    return out
                r = _commun._get_borne(httpx, url, timeout=15, headers=UA)
            _LI["suite_429"] = 0
            if r.status_code in (403, 999):
                # Un REFUS s'arrete : plus aucune requete LinkedIn de la collecte.
                INCIDENTS["linkedin_http"][r.status_code] += 1
                _LI["stop"] = str(r.status_code)
                return out
            if r.status_code != 200:
                # UN REFUS N'EST PAS UNE ABSENCE D'OFFRES. `break` muet rendait
                # une liste vide indistinguable de « rien de neuf cette
                # semaine » — sur la source qui fournit les deux tiers de la
                # file. Un scan entierement bride affichait « 0 offres » et
                # passait pour une journee calme. On compte, et main() le dit.
                INCIDENTS["linkedin_http"][r.status_code] += 1
                break
            blocks = r.text.split("base-card")  # 1 carte par bloc
            for b in blocks:
                mu = re.search(r'href="(https://[a-z]+\.linkedin\.com/jobs/view/[^"?]+)', b)
                mt = re.search(r'<span class="sr-only">\s*([^<]+?)\s*</span>', b)
                if not (mu and mt):
                    continue
                comp = _LI_COMP.search(b)
                loc = _LI_LOC.search(b)
                titre = _html.unescape(mt.group(1)).strip()
                if title_ok(titre):
                    out.append(
                        _mk(
                            titre,
                            mu.group(1),
                            _html.unescape(comp.group(1)).strip() if comp else "LinkedIn",
                            _html.unescape(loc.group(1)).strip() if loc else "",
                            "",
                            f"linkedin-search:{keyword}",
                        )
                    )
        except Exception as e:
            INCIDENTS["linkedin_reseau"][type(e).__name__] += 1
            break
        _dormir(LI_PAUSE)  # poli : espace les pages
    return out


# LIMITE DE DEBIT LINKEDIN. Mesure du 2026-10-17 : a 1,2 s entre pages, l'API
# invite repond 429 des la premiere poignee de requetes — 13 mots-cles sur 14
# coupes en 32 s. Le code faisait `break` : page perdue, mot-cle suivant, 429 a
# nouveau. Du 13 au 16/10, la collecte LinkedIn est tombee de 200-640 offres
# par jour a 0-28, sans rien de visible hors du compteur d'incidents.
# Regle du projet : un 429 dit « reviens plus tard » — on espace davantage, on
# attend (Retry-After, sinon 60 s doublees jusqu'a 240), on reprend la MEME
# page. 403/999 sont des refus : arret immediat, aucune reprise.
#
# DUREE MAXIMALE DE LA PASSE, pas budget d'attente. Mesure du 17/10 avec un
# budget de 900 s d'attente : 184 offres (101 neuves) au lieu de 96, mais
# arret a 10 mots-cles sur 14, France seule — « Worldwide » n'aurait rien eu.
# La passe LinkedIn du pipeline est tuee a 3600 s, et une passe tuee perd TOUTE
# sa collecte (fusion en fin de passe) : on s'arrete proprement a 45 min.
LI_PAUSE = 3.0

LI_ATTENTES = (60, 120, 240)

LI_DUREE_MAX = 2700

_LI = {"stop": None, "attendu": 0.0, "suite_429": 0, "debut": 0.0}

_dormir = time.sleep  # les tests le remplacent

_horloge = time.monotonic  # idem


def _li_ecoule():
    return _horloge() - _LI["debut"]


def _li_pause_429(r):
    """Attend avant de redemander apres un 429. False si la passe n'a plus le temps."""
    ra = (getattr(r, "headers", None) or {}).get("Retry-After", "")
    n = _LI["suite_429"]
    pause = int(ra) if str(ra).isdigit() else LI_ATTENTES[min(n, len(LI_ATTENTES) - 1)]
    pause = min(pause, max(LI_ATTENTES))
    if _li_ecoule() + pause > LI_DUREE_MAX:
        return False
    _log.warning(f"  ⏳ linkedin : limite de débit (429), pause {pause} s puis reprise")
    _dormir(pause)
    _LI["attendu"] += pause
    _LI["suite_429"] = n + 1
    return True


# POURQUOI PLUS DE LISTE DE PAYS. Le critere n'est pas le pays, c'est la
# langue que l'annonce demande — et un pays ne la dit pas. Mesure du
# 2026-09-22 : la recherche publique LinkedIn accepte le lieu « Worldwide », et
# elle pagine en profondeur.
#
#   lieu=""            -> retombe sur les ETATS-UNIS (Oxnard, Indianapolis…)
#   lieu="Worldwide"   ->  2 pages : 17 offres, 12 pays
#                         10 pages : 78 offres, 37 pays
#
# Enumerer seize pays coutait 1 760 requetes pour seize pays. « Worldwide » en
# profondeur en coute 550 pour trente-sept et plus. Strictement meilleur.
#
# La France reste interrogee a part : c'est la que l'utilisateur vit, et une requete
# mondiale y noie les offres locales sous le volume indien et americain.
#
# Le dictionnaire donne la PROFONDEUR par lieu. Une liste simple reste acceptee
# et utilise alors la profondeur passee en argument.
LIEUX_MONDE = {"France": 3, "Worldwide": 12}


def scan_linkedin(pages=2, days=7, lieux=None):
    """days = fenetre de fraicheur LinkedIn (f_TPR). Le defaut de 7 jours suffit
    au scan quotidien, mais il rend invisibles les offres plus anciennes jamais
    captees : passer --days 31 pour rattraper un mois entier.

    `lieux` : les zones interrogees. En recherche mondiale on ne peut pas se
    contenter de retirer le filtre d'entree — il faut DEMANDER les autres pays.
    """
    if lieux is None:
        lieux = LIEUX_MONDE if _commun.MONDE else ["France"]
    # Un dict donne la profondeur par lieu, une liste garde celle de l'argument.
    profondeur = dict(lieux) if isinstance(lieux, dict) else {x: pages for x in lieux}
    offers, seen = [], set()
    _LI.update(stop=None, attendu=0.0, suite_429=0, debut=_horloge())
    for lieu in profondeur:
        n_lieu = 0
        for kw in _commun.KEYWORDS:
            if not _LI["stop"] and _li_ecoule() >= LI_DUREE_MAX:
                _LI["stop"] = "durée"
            if _LI["stop"]:
                break
            got = linkedin_guest_search(kw, pages=profondeur[lieu], days=days, lieu=lieu)
            new = [o for o in got if o["url"] not in seen]
            seen.update(o["url"] for o in new)
            n_lieu += len(new)
            if new and len(profondeur) == 1:
                _log.info(f"  ✓ linkedin «{kw}» → {len(new)} offres")
            offers.extend(new)
        if len(profondeur) > 1:
            _log.info(f"  ✓ linkedin {lieu} → {n_lieu} offres")
    if _LI["stop"] in ("429", "durée"):
        _log.warning(
            f"  ⚠ linkedin : durée maximale atteinte ({_li_ecoule():.0f} s, dont "
            f"{_LI['attendu']:.0f} s d'attente sur 429) — la suite à la prochaine collecte"
        )
    elif _LI["stop"]:
        _log.warning(f"  ⚠ linkedin : refus HTTP {_LI['stop']}, collecte LinkedIn arrêtée")
    return offers
