"""Lecteurs des API publiques d'ATS (Greenhouse, Lever, Ashby...) et des autres API de recrutement.

Partie de jobhunter.sources (ancien Scripts/job_sources.py, phase 3.4)."""

import datetime
import html
import json
import re
import time
from typing import Any
from urllib.parse import quote, unquote, urlparse

from jobhunter import journal as _journal
from jobhunter.sources import commun as _commun
from jobhunter.sources import workday as _workday
from jobhunter.sources.commun import INCIDENTS, UA, _mk, _strip_html, title_ok

_log = _journal.journal(__name__)


# ═══════════════ 1. ATS APIs (httpx pur, pas de navigateur) — AVEC descriptions ═══════════════
def _ats_ko(kind: str, slug: str, r: Any) -> bool:
    """Réponse inutilisable ? Et si oui, faut-il s'en inquiéter ?

    404 : le slug n'existe pas chez cet ATS. C'est le cas NORMAL — la liste est
    volontairement large, on sonde des sociétés qui n'y sont pas. Silence.
    Tout le reste (429 quota, 5xx panne) est un refus : la société a peut-être
    des offres, on ne les a pas vues. Ça se compte, sinon un scan entièrement
    bridé ressemble à un scan sans nouveauté.
    """
    if r.status_code == 200:
        return False
    if r.status_code != 404:
        INCIDENTS[f"ats:{kind}"][f"HTTP {r.status_code}"] += 1
    return True


# Le nom d'un compte ATS n'est pas celui de l'entreprise : `slug.title()` donnait
# « Grantthornton », « Societegenerale », « Vestiairecollective ». Une entreprise
# mal nommee echappe au tri par entreprise, au doublon avec LinkedIn et a toute
# recherche (2026-10-08 : Roland Berger « absent », 34 offres sous
# « rolandberger »). Les slugs absents d'ici gardent `slug.title()`.
ATS_NOMS = {
    "backmarket": "Back Market",
    "clarityai": "Clarity AI",
    "ecovadis": "EcoVadis",
    "ibanfirst": "iBanFirst",
    "payfit": "PayFit",
    "vestiairecollective": "Vestiaire Collective",
    "forvismazars": "Forvis Mazars",
    "alixpartners": "AlixPartners",
    "descartesunderwriting": "Descartes Underwriting",
    "sfeir": "SFEIR",
    "dedale-intelligence": "Dedale Intelligence",
    "grantthornton": "Grant Thornton",
    "meridiam": "Meridiam",
    "bakertilly": "Baker Tilly",
    "tikehaucapital": "Tikehau Capital",
    "axa": "AXA",
    "amundi": "Amundi",
    "bnpparibas": "BNP Paribas",
    "societegenerale": "Société Générale",
    "sycomoreassetmanagement": "Sycomore Asset Management",
    "jobteaser": "JobTeaser",
    "rolandberger": "Roland Berger",
    "southpole": "South Pole",
    "positiongreen": "Position Green",
    "cdpworldwide": "CDP",
    "keplercheuvreux": "Kepler Cheuvreux",
    "jobs.tennaxia.com": "Tennaxia",
    "paipartners": "PAI Partners",
    "8advisory": "Eight Advisory",
    "eqtpartners": "EQT",
    "epsa": "EPSA (Ekodev)",
    "masdar": "Masdar",
    "repriskag": "RepRisk",
    "ifrsfoundation": "IFRS Foundation (ISSB)",
    "oecd": "OCDE (OECD)",
    "saintgobain": "Saint-Gobain",
}


def nom_ats(slug: str) -> str:
    return ATS_NOMS.get(slug.lower()) or slug.title()


# Teamtailor : flux RSS public par societe, lieu en <tt:city>/<tt:country>.
# Ajoute le 2026-10-08 pour South Pole, Indefi, Datamaran, Position Green — le
# conseil ESG europeen y est, et sur aucun des cinq ATS lus jusque-la.
_RX_TT_ITEM = re.compile(r"<item>(.*?)</item>", re.S)


def _tt(champ: str, item: Any) -> str:
    m = re.search(r"<" + re.escape(champ) + r">(.*?)</" + re.escape(champ) + r">", item, re.S)
    return html.unescape(m.group(1).strip()) if m else ""


def fetch_ats(kind: str, slug: str) -> list[dict[str, Any]]:
    import httpx

    out = []
    try:
        if kind == "greenhouse":
            # ?content=true → description HTML incluse dans la liste
            r = _commun._get_borne(
                httpx,
                f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true",
                timeout=15,
                headers=UA,
            )
            if _ats_ko(kind, slug, r):
                return []
            for j in r.json().get("jobs", []):
                out.append(
                    _mk(
                        j.get("title", ""),
                        j.get("absolute_url", ""),
                        nom_ats(slug),
                        (j.get("location") or {}).get("name", ""),
                        j.get("updated_at", "")[:10],
                        f"greenhouse:{slug}",
                        _strip_html(j.get("content", "")),
                    )
                )
        elif kind == "lever":
            r = _commun._get_borne(
                httpx, f"https://api.lever.co/v0/postings/{slug}?mode=json", timeout=15, headers=UA
            )
            if _ats_ko(kind, slug, r):
                return []
            for j in r.json():
                out.append(
                    _mk(
                        j.get("text", ""),
                        j.get("hostedUrl", ""),
                        nom_ats(slug),
                        (j.get("categories") or {}).get("location", ""),
                        "",
                        f"lever:{slug}",
                        j.get("descriptionPlain", "") or _strip_html(j.get("description", "")),
                    )
                )
        elif kind == "ashby":
            r = _commun._get_borne(
                httpx,
                f"https://api.ashbyhq.com/posting-api/job-board/{slug}",
                timeout=15,
                headers=UA,
            )
            if _ats_ko(kind, slug, r):
                return []
            for j in r.json().get("jobs", []):
                out.append(
                    _mk(
                        j.get("title", ""),
                        j.get("jobUrl", ""),
                        nom_ats(slug),
                        j.get("location", ""),
                        "",
                        f"ashby:{slug}",
                        _strip_html(j.get("descriptionHtml", "")),
                    )
                )
        elif kind == "recruitee":
            r = _commun._get_borne(
                httpx, f"https://{slug}.recruitee.com/api/offers/", timeout=15, headers=UA
            )
            if _ats_ko(kind, slug, r):
                return []
            for j in r.json().get("offers", []):
                out.append(
                    _mk(
                        j.get("title", ""),
                        j.get("careers_url", ""),
                        nom_ats(slug),
                        j.get("location", ""),
                        "",
                        f"recruitee:{slug}",
                        _strip_html(j.get("description", "")),
                    )
                )
        elif kind == "teamtailor":
            # Un domaine propre (jobs.tennaxia.com) sert le meme flux.
            hote = slug if "." in slug else f"{slug}.teamtailor.com"
            r = _commun._get_borne(httpx, f"https://{hote}/jobs.rss", timeout=15, headers=UA)
            if _ats_ko(kind, slug, r):
                return []
            for it in _RX_TT_ITEM.findall(r.text):
                lieu = ", ".join(x for x in (_tt("tt:city", it), _tt("tt:country", it)) if x)
                out.append(
                    _mk(
                        _tt("title", it),
                        _tt("link", it),
                        nom_ats(slug),
                        lieu,
                        "",
                        f"teamtailor:{slug}",
                        _strip_html(_tt("description", it)),
                    )
                )
        elif kind == "smartrecruiters":
            r = _commun._get_borne(
                httpx,
                f"https://api.smartrecruiters.com/v1/companies/{slug}/postings?limit=100",
                timeout=15,
                headers=UA,
            )
            if _ats_ko(kind, slug, r):
                return []
            for j in r.json().get("content", []):
                o = _mk(
                    j.get("name", ""),
                    f"https://jobs.smartrecruiters.com/{slug}/{j.get('id', '')}",
                    nom_ats(slug),
                    (j.get("location") or {}).get("city", ""),
                    str(j.get("releasedDate", ""))[:10],
                    f"smartrecruiters:{slug}",
                )
                out.append(o)
        # SmartRecruiters : description via appel détail — seulement pour les titres retenus (peu)
        if kind == "smartrecruiters":
            kept = [o for o in out if title_ok(o["titre"])]
            for o in kept:
                try:
                    jid = o["url"].rstrip("/").split("/")[-1]
                    rd = _commun._get_borne(
                        httpx,
                        f"https://api.smartrecruiters.com/v1/companies/{slug}/postings/{jid}",
                        timeout=12,
                        headers=UA,
                    )
                    if rd.status_code == 200:
                        secs = (rd.json().get("jobAd") or {}).get("sections") or {}
                        o["description"] = _strip_html(
                            " ".join(
                                str(v.get("text", "")) for v in secs.values() if isinstance(v, dict)
                            )
                        )[:30000]
                except Exception:
                    pass
                time.sleep(0.4)  # appel détail par offre : on ne mitraille pas
            # Meme garde que la sortie normale : une offre sans URL n'est pas
            # exploitable, elle ne doit pas entrer par cette branche non plus.
            return [o for o in kept if o["titre"] and o["url"]]
    except Exception as e:
        INCIDENTS[f"ats:{kind}"][type(e).__name__] += 1
        return []
    return [o for o in out if o["titre"] and o["url"] and title_ok(o["titre"])]


ATS_PAUSE = 0.5  # entre deux slugs : 40 appels d'affilee, autant les espacer


def scan_ats() -> list[dict[str, Any]]:
    offers = []
    for kind, slugs in _commun.ATS_SLUGS.items():
        for slug in slugs:
            got = fetch_ats(kind, slug)
            if got:
                _log.info(f"  ✓ {kind}:{slug} → {len(got)} offres")
            offers.extend(got)
            time.sleep(ATS_PAUSE)
    offers.extend(scan_autres())
    return offers


_RX_CDATA = re.compile(r"^<!\[CDATA\[(.*)\]\]>$", re.S)

_RX_LIEU_FIN = re.compile(r"\s*\(([^()]*)\)\s*$")

_RX_TS_CAT = re.compile(r"<category>(.*?)</category>", re.S)

_RX_TS_REF = re.compile(r"^\s*\d{4}-\d+\s+-\s+")

_RX_AV_TITRE = re.compile(
    r'<h3 class="article__header__text__title[^"]*">\s*<a (?:class="link" )?href="([^"]+)">\s*([^<]+?)\s*</a>'
)

_RX_AV_PAYS = re.compile(r'list-item-jobCountry">([^<]+)<')

_RX_AV_DATE = re.compile(r'list-item-jobCreationDate">(\d{2})-(\d{2})-(\d{4})<')

# Deux themes TalentBrew : titre dans le <a> (Moody's) ou dans un <h2> a l'interieur (ING).
_RX_TB_LIEN = re.compile(
    r'href="(/[a-z-]+/job/[^"]+)"[^>]*data-job-id="\d+"[^>]*>\s*(?:<h2[^>]*>)?\s*([^<]+?)\s*<'
)

_RX_TB_LIEU = re.compile(r'job-location">([^<]+)<')

_RX_ADB_LIGNE = re.compile(
    r'<a href="(https://www\.adb\.org/careers/\d+)">([^<]+?)\s*/\s*\d+</a>(.*?)</tr>', re.S
)

_RX_ADB_LIEU = re.compile(r'field-location">\s*([^<]+?)\s*<')

_RX_ADB_DATE = re.compile(r'field-date-content"><time datetime="(\d{4}-\d{2}-\d{2})')

_RX_PS_CHAMP = re.compile(
    r"id='(SCH_JOB_TITLE|HRS_APP_JBSCH_I_HRS_JOB_OPENING_ID|SCH_OPENED|LOCATION)\$(\d+)'\s*>([^<]*)<"
)

_RX_CSOD_CTX = re.compile(r"csod\.context\s*=\s*(\{.*?\});", re.S)

_RX_ICIMS_CARTE = re.compile(r'<li class="iCIMS_JobCardItem">(.*?)</li>', re.S)

_RX_ICIMS_LIEN = re.compile(r'<a href="([^"]+/jobs/\d+/[^"]*)"[^>]*title="\d+ - ([^"]+)"')

_RX_ICIMS_LIEU = re.compile(r"Job Locations</span>\s*</dt>\s*<dd[^>]*><span\s*>\s*([^<]+)</span>")

ICIMS_PAGES = 15

SITEMAP_JOURS = 60

_RX_SM_INDEX = re.compile(r"<sitemap>\s*<loc>([^<]+)</loc>")

_RX_SM_URL = re.compile(r"<url>\s*<loc>([^<]+)</loc>(.*?)</url>", re.S)

_RX_SM_DATE = re.compile(r"<lastmod>(\d{4}-\d{2}-\d{2})")

_RX_SM_NUM = re.compile(r"\s+\d{1,2}$")

_RX_SM_ID = re.compile(r"^\d{3,}[\s/]+")

_RX_SM_H1 = re.compile(r"<h1[^>]*>(.*?)</h1>", re.S)


def _sans_cdata(s: str) -> str:
    m = _RX_CDATA.match(s.strip())
    return m.group(1) if m else s


def fetch_autre(kind: str, cle: str, nom: str) -> list[dict[str, Any]]:
    import httpx

    out = []
    try:
        if kind == "workable":
            r = _commun._get_borne(
                httpx,
                f"https://apply.workable.com/api/v1/widget/accounts/{cle}",
                timeout=15,
                headers=UA,
            )
            if _ats_ko(kind, cle, r):
                return []
            for j in r.json().get("jobs", []):
                lieu = ", ".join(x for x in (j.get("city"), j.get("country")) if x)
                out.append(
                    _mk(
                        j.get("title", ""),
                        j.get("url", ""),
                        nom,
                        lieu,
                        j.get("published_on", ""),
                        f"workable:{cle}",
                    )
                )
        elif kind == "pinpoint":
            hote = cle if "." in cle else f"{cle}.pinpointhq.com"  # domaine propre accepte
            r = _commun._get_borne(
                httpx,
                f"https://{hote}/postings.json",
                timeout=15,
                headers=UA,
                follow_redirects=True,
            )
            if _ats_ko(kind, cle, r):
                return []
            for j in r.json().get("data", []):
                out.append(
                    _mk(
                        j.get("title", ""),
                        j.get("url", ""),
                        nom,
                        (j.get("location") or {}).get("name", ""),
                        "",
                        f"pinpoint:{cle}",
                        _strip_html(j.get("description", "")),
                    )
                )
        elif kind == "sitemap":
            # Sites maison sans API, mais dont le sitemap liste chaque offre avec
            # sa date (Sia Partners, Carbone 4). Titre tire de l'adresse : leur
            # page d'offre affiche « Offres d'emploi » en <h1>, pas l'intitule.
            # « racine|chemin|h1 » : l'adresse ne porte qu'un identifiant (KBC),
            # le titre se lit alors dans le <h1> de chaque page.
            racine, chemin, *mode = cle.split("|")
            limite = (datetime.date.today() - datetime.timedelta(days=SITEMAP_JOURS)).isoformat()
            r = _commun._get_borne(httpx, racine, timeout=20, headers=UA, follow_redirects=True)
            if _ats_ko(kind, racine, r):
                return []
            xml = [r.text]
            for enfant in _RX_SM_INDEX.findall(r.text) if "<sitemapindex" in r.text else []:
                re_ = _commun._get_borne(
                    httpx, html.unescape(enfant), timeout=20, headers=UA, follow_redirects=True
                )
                if re_.status_code == 200:
                    xml.append(re_.text)
            vus = set()
            for x in xml:
                for loc, reste in _RX_SM_URL.findall(x):
                    loc = html.unescape(loc)
                    date = (_RX_SM_DATE.findall(reste) or [""])[0]
                    if chemin not in loc or loc in vus or (date and date < limite):
                        continue
                    vus.add(loc)
                    # Tout ce qui suit le chemin : « internship-consultant-m/f-january-2027 »
                    # contient un « / ». Le « -0 », « -1 » final est un doublon de slug.
                    slug = loc.split(chemin, 1)[1].strip("/")
                    titre = re.sub(r"[-_]+", " ", unquote(slug)).strip()
                    # « 7827/senior-esg-risk-analyst » (ABN AMRO) : l'identifiant en tete tombe.
                    titre = _RX_SM_ID.sub("", _RX_SM_NUM.sub("", titre)).capitalize()
                    if mode == ["h1"]:
                        p = _commun._get_borne(
                            httpx, loc, timeout=20, headers=UA, follow_redirects=True
                        )
                        h1 = _RX_SM_H1.search(p.text) if p.status_code == 200 else None
                        if not h1:
                            continue
                        titre = html.unescape(re.sub(r"<[^>]+>", "", h1.group(1))).strip()
                        time.sleep(_workday.WORKDAY_PAUSE)
                    out.append(_mk(titre, loc, nom, "", date, f"sitemap:{urlparse(racine).netloc}"))
        elif kind == "peoplesoft":
            # PeopleSoft Fluid (BEI) : la page de recherche rendue cote serveur
            # liste toutes les offres ouvertes, champs indexes par ligne ($0, $1...).
            # Le lien de detail exige la session : il ouvre la liste, puis l'offre.
            base = f"https://{cle}/c/HRS_HRAM_FL.HRS_CG_SEARCH_FL.GBL"
            r = _commun._get_borne(
                httpx,
                f"{base}?Page=HRS_APP_SCHJOB_FL&Action=U",
                timeout=30,
                headers=UA,
                follow_redirects=True,
            )
            if _ats_ko(kind, cle, r):
                return []
            champs: dict[str, Any] = {}
            for nom_champ, i, val in _RX_PS_CHAMP.findall(r.text):
                champs.setdefault(i, {})[nom_champ] = html.unescape(val.strip())
            for i in sorted(champs, key=int):
                c = champs[i]
                ident = c.get("HRS_APP_JBSCH_I_HRS_JOB_OPENING_ID", "")
                if not c.get("SCH_JOB_TITLE") or not ident:
                    continue
                jj, mm, aa = (c.get("SCH_OPENED", "").split("/") + ["", "", ""])[:3]
                out.append(
                    _mk(
                        c["SCH_JOB_TITLE"],
                        f"{base}?Page=HRS_APP_JBPST_FL&Action=U"
                        f"&FOCUS=Applicant&SiteId=1&JobOpeningId={ident}&PostingSeq=1",
                        nom,
                        c.get("LOCATION", ""),
                        f"{aa}-{mm}-{jj}" if aa else "",
                        f"peoplesoft:{cle.split('/')[0]}",
                    )
                )
        elif kind == "gogenerali":
            # Generali (portail italien, sieges et filiales) : l'API de la page
            # repond sans jeton. Les agences (hors perimetre « direzionale ») sont
            # des postes commerciaux, exclus. Fiche : /home/job/{id}/{titre}.
            r = _commun._get_borne(
                httpx,
                f"https://{cle}/rest-api/talent-farm-mediator/get-available-jobs-from-ats"
                f"?fromRecord=0&numRecords=1000&onlyDirectionalPerimeter=true",
                timeout=30,
                headers={**UA, "Accept": "application/json"},
            )
            if _ats_ko(kind, cle, r):
                return []
            for j in (r.json() or {}).get("response") or []:
                if not j.get("contestId") or j.get("currentStatus") != "PUBLISHED":
                    continue
                slug = re.sub(r"[^a-z0-9]+", "-", (j.get("title") or "").lower()).strip("-")
                desc = _strip_html(
                    (j.get("descriptionInternalHTML") or "")
                    + " "
                    + (j.get("internalQualificationHTML") or "")
                )
                out.append(
                    _mk(
                        j.get("title", ""),
                        f"https://{cle}/home/job/{j['contestId']}/{slug}",
                        nom,
                        j.get("primaryLocation") or "",
                        (j.get("currentStatusDate") or "")[:10],
                        f"gogenerali:{cle}",
                        desc,
                    )
                )
        elif kind == "adb":
            # Banque asiatique de developpement : tableau HTML de toutes les
            # offres ouvertes, « Intitule / reference » dans le lien.
            r = _commun._get_borne(
                httpx, f"https://{cle}", timeout=30, headers=UA, follow_redirects=True
            )
            if _ats_ko(kind, cle, r):
                return []
            for url, titre, reste in _RX_ADB_LIGNE.findall(r.text):
                l, d = _RX_ADB_LIEU.search(reste), _RX_ADB_DATE.search(reste)
                out.append(
                    _mk(
                        html.unescape(titre),
                        url,
                        nom,
                        html.unescape(l.group(1)) if l else "",
                        d.group(1) if d else "",
                        "adb:adb.org",
                    )
                )
        elif kind == "icims":
            # Liste HTML paginee (pr=0, 1, ...), filtree ensuite par title_ok :
            # la recherche par mot-cle de l'iframe ne rend rien sans session.
            vus = set()
            for page in range(ICIMS_PAGES):
                r = _commun._get_borne(
                    httpx,
                    f"https://{cle}/jobs/search?ss=1&in_iframe=1&pr={page}",
                    timeout=20,
                    headers=UA,
                    follow_redirects=True,
                )
                if _ats_ko(kind, cle, r):
                    break
                neufs = 0
                for carte in _RX_ICIMS_CARTE.findall(r.text):
                    m = _RX_ICIMS_LIEN.search(carte)
                    if not m or m.group(1) in vus:
                        continue
                    vus.add(m.group(1))
                    neufs += 1
                    l = _RX_ICIMS_LIEU.search(carte)
                    out.append(
                        _mk(
                            html.unescape(m.group(2)),
                            m.group(1).replace("?in_iframe=1", ""),
                            nom,
                            html.unescape(l.group(1).strip()) if l else "",
                            "",
                            f"icims:{cle}",
                        )
                    )
                if not neufs:
                    break
                time.sleep(_workday.WORKDAY_PAUSE)
        else:
            vus = set()
            for mot in _workday.WORKDAY_MOTS:
                for titre, url, lieu, date, desc in _cherche_autre(httpx, kind, cle, mot):
                    if url and url not in vus:
                        vus.add(url)
                        out.append(
                            _mk(titre, url, nom, lieu, date, f"{kind}:{cle.split('|')[0]}", desc)
                        )
                time.sleep(_workday.WORKDAY_PAUSE)
    except Exception as e:
        INCIDENTS[f"ats:{kind}"][type(e).__name__] += 1
        return []
    return [o for o in out if o["titre"] and o["url"] and title_ok(o["titre"])]


def _cherche_autre(httpx: Any, kind: str, cle: str, mot: str) -> list[Any]:
    """[(titre, url, lieu, date, description)] pour un mot-cle, cote serveur."""
    if kind == "eightfold":
        hote, domaine = cle.split("|")
        r = _commun._get_borne(
            httpx,
            f"https://{hote}/api/apply/v2/jobs?domain={domaine}&start=0&num=50&query={quote(mot)}",
            timeout=20,
            headers=UA,
        )
        if _ats_ko(kind, hote, r):
            return []
        return [
            (
                p.get("name", ""),
                p.get("canonicalPositionUrl", ""),
                p.get("location", ""),
                "",
                _strip_html(p.get("job_description", "")),
            )
            for p in r.json().get("positions", [])
        ]
    if kind == "sfrss":
        r = _commun._get_borne(
            httpx,
            f"https://{cle}/services/rss/job/?locale=en_US&keywords={quote(mot)}",
            timeout=20,
            headers=UA,
        )
        if _ats_ko(kind, cle, r):
            return []
        res = []
        for it in _RX_TT_ITEM.findall(r.text):
            titre = _sans_cdata(_tt("title", it))
            m = _RX_LIEU_FIN.search(titre)  # « Analyst - Paris (Paris, FR) »
            lieu = m.group(1) if m else ""
            titre = _RX_LIEU_FIN.sub("", titre) if m else titre
            titre = titre[6:] if titre.startswith("Job | ") else titre  # Belfius
            res.append(
                (
                    titre,
                    _sans_cdata(_tt("link", it)),
                    lieu,
                    "",
                    _strip_html(_sans_cdata(_tt("description", it))),
                )
            )
        return res
    if kind == "talentsoft":
        # Sans Rss_Keywords le flux rend les 20 dernieres offres, tous metiers.
        r = _commun._get_borne(
            httpx,
            f"https://{cle}/handlers/offerRss.ashx?LCID=1036&Rss_Keywords={quote(mot)}",
            timeout=20,
            headers=UA,
        )
        if _ats_ko(kind, cle, r):
            return []
        res = []
        for it in _RX_TT_ITEM.findall(r.text):
            cats = [html.unescape(c.strip()) for c in _RX_TS_CAT.findall(it)]
            titre = _RX_TS_REF.sub("", _tt("title", it))  # « 2026-116250 - Stage - ... »
            res.append(
                (
                    titre,
                    _tt("link", it),
                    cats[-1] if len(cats) >= 3 else "",
                    "",
                    _strip_html(_tt("description", it)),
                )
            )
        return res
    if kind == "phenom":
        # La page de resultats embarque ses offres en JSON (phApp.ddo), 10 par
        # page. C'est le rendu serveur que tout visiteur recoit.
        res = []
        for depart in (0, 10):
            r = _commun._get_borne(
                httpx,
                f"https://{cle}/search-results?keywords={quote(mot)}&from={depart}",
                timeout=20,
                headers=UA,
            )
            if _ats_ko(kind, cle, r):
                break
            i = r.text.find("phApp.ddo = ")
            if i < 0:
                break
            try:
                ddo, _ = json.JSONDecoder().raw_decode(r.text[i + 12 :])
                jobs = ddo["eagerLoadRefineSearch"]["data"]["jobs"]
            except Exception:
                break
            res += [
                (
                    j.get("title", ""),
                    f"https://{cle}/job/{j.get('jobId', '')}",
                    j.get("cityStateCountry") or j.get("location") or "",
                    str(j.get("postedDate") or "")[:10],
                    j.get("descriptionTeaser") or "",
                )
                for j in jobs
                if j.get("jobId")
            ]
            if len(jobs) < 10:
                break
        return res
    if kind == "jibe":
        # Jibe (Google Cloud Talent) : la page carriere appelle /api/jobs, JSON
        # public, description comprise. Schneider Electric (2026-10-08).
        r = _commun._get_borne(
            httpx,
            f"https://{cle}/api/jobs?page=1&keywords={quote(mot)}&sortBy=relevance&limit=50",
            timeout=20,
            headers={**UA, "Accept": "application/json"},
            follow_redirects=True,
        )
        if _ats_ko(kind, cle, r):
            return []
        res = []
        for j in (r.json() or {}).get("jobs") or []:
            d = j.get("data") or {}
            if not d.get("slug"):
                continue
            res.append(
                (
                    d.get("title", ""),
                    f"https://{cle}/jobs/{d['slug']}?lang=en-us",
                    d.get("location_name") or d.get("country") or "",
                    "",
                    _strip_html(d.get("description") or ""),
                )
            )
        return res
    if kind == "talentbrew":
        # Radancy TalentBrew : la page de recherche (mot dans le chemin) est
        # rendue cote serveur. Moody's, ING (2026-10-08). cle = « hote/langue|org ».
        base, org = cle.split("|")
        r = _commun._get_borne(
            httpx,
            f"https://{base}/search-jobs/{quote(mot)}/{org}/1",
            timeout=20,
            headers=UA,
            follow_redirects=True,
        )
        if _ats_ko(kind, base, r):
            return []
        hote = base.split("/")[0]
        res, vus = [], set()
        for m in _RX_TB_LIEN.finditer(r.text):
            if m.group(1) in vus:
                continue
            vus.add(m.group(1))
            l = _RX_TB_LIEU.search(r.text, m.end(), m.end() + 1500)
            res.append(
                (
                    html.unescape(m.group(2).strip()),
                    f"https://{hote}{m.group(1)}",
                    html.unescape(l.group(1).strip()) if l else "",
                    "",
                    "",
                )
            )
        return res
    if kind == "avature":
        # Page de recherche rendue cote serveur, 50 cartes par page.
        r = _commun._get_borne(
            httpx,
            f"https://{cle}/SearchJobs/?listFilterMode=1&jobRecordsPerPage=50&search={quote(mot)}",
            timeout=20,
            headers=UA,
            follow_redirects=True,
        )
        if _ats_ko(kind, cle, r):
            return []
        res = []
        for carte in r.text.split('class="article article--result"')[1:]:
            m = _RX_AV_TITRE.search(carte)
            if not m:
                continue
            pays = _RX_AV_PAYS.search(carte)
            d = _RX_AV_DATE.search(carte)
            res.append(
                (
                    html.unescape(m.group(2).strip()),
                    m.group(1),
                    html.unescape(pays.group(1).strip()) if pays else "",
                    f"{d.group(3)}-{d.group(2)}-{d.group(1)}" if d else "",
                    "",
                )
            )
        return res
    if kind == "csod":
        # Cornerstone : la page publique delivre a tout visiteur un jeton
        # anonyme, que son propre script envoie a l'API de recherche.
        hote, site = cle.split("|")
        tenant = hote.split(".")[0]
        page = _commun._get_borne(
            httpx,
            f"https://{hote}/ux/ats/careersite/{site}/home?c={tenant}",
            timeout=20,
            headers=UA,
        )
        if _ats_ko(kind, hote, page):
            return []
        m = _RX_CSOD_CTX.search(page.text)
        ctx = json.loads(m.group(1)) if m else {}
        api = ((ctx.get("endpoints") or {}).get("cloud") or "").rstrip("/")
        if not ctx.get("token") or not api:
            return []
        r = _commun._post_borne(
            httpx,
            f"{api}/rec-job-search/external/jobs",
            timeout=20,
            headers={
                **UA,
                "Authorization": "Bearer " + ctx["token"],
                "Content-Type": "application/json",
            },
            json={
                "careerSiteId": int(site),
                "careerSitePageId": int(site),
                "pageNumber": 1,
                "pageSize": 50,
                "cultureId": 1,
                "searchText": mot,
                "cultureName": "en-US",
                "states": [],
                "countryCodes": [],
                "cities": [],
                "placeID": "",
                "radius": None,
                "postingsWithinDays": None,
                "customFieldCheckboxKeys": [],
                "customFieldDropdowns": [],
                "customFieldRadios": [],
            },
        )
        if _ats_ko(kind, hote, r):
            return []
        res = []
        for j in ((r.json() or {}).get("data") or {}).get("requisitions") or []:
            loc = (j.get("locations") or [{}])[0]
            lieu = ", ".join(x for x in (loc.get("city"), loc.get("country")) if x)
            res.append(
                (
                    j.get("displayJobTitle", ""),
                    f"https://{hote}/ux/ats/careersite/{site}/home/requisition/"
                    f"{j.get('requisitionId', '')}?c={tenant}",
                    lieu,
                    "",
                    j.get("externalDescription") or "",
                )
            )
        return res
    if kind == "oracle":
        hote, site = cle.split("|")
        r = _commun._get_borne(
            httpx,
            f"https://{hote}/hcmRestApi/resources/latest/recruitingCEJobRequisitions"
            f"?onlyData=true&expand=requisitionList&finder=findReqs;siteNumber={site},"
            f"limit=50,keyword={quote(mot)}",
            timeout=20,
            headers=UA,
        )
        if _ats_ko(kind, hote, r):
            return []
        items = r.json().get("items") or [{}]
        return [
            (
                j.get("Title", ""),
                f"https://{hote}/hcmUI/CandidateExperience/en/sites/{site}/job/{j.get('Id', '')}",
                j.get("PrimaryLocation", ""),
                j.get("PostedDate", ""),
                j.get("ShortDescriptionStr") or "",
            )
            for j in items[0].get("requisitionList") or []
            if j.get("Id")
        ]
    return []


# Choisir le service public : le portail des trois fonctions publiques (CDC,
# Banque de France, AMF, ACPR, ministeres...). Trouve le 2026-10-08 en cherchant
# « Caisse des Depots recrutement » : la CDC n'a pas de flux propre, ses offres
# sont la. Recherche plein texte large (22 409 resultats pour « esg »), triee
# par pertinence : deux pages par mot suffisent, title_ok fait le reste.
CSP = "https://choisirleservicepublic.gouv.fr"

CSP_MOTS = [
    "esg",
    "finance durable",
    "analyste financier",
    "finance climat",
    "analyste investissement",
    "risques financiers",
    "taxonomie",
    "extra-financier",
]

# Mesure du 2026-10-08 : 178 offres passent title_ok, dont 36 communes et 31
# intercommunalites. On ne garde que les employeurs financiers publics, ou un
# intitule franchement ESG / finance durable quel que soit l'employeur.
_RX_CSP_EMPLOYEUR = re.compile(
    r"caisse des d[ée]p[ôo]ts|\bCDC\b|banque de france|\bAMF\b|autorit[ée] des march[ée]s|"
    r"\bACPR\b|contr[ôo]le prudentiel|\bAFD\b|agence fran[cç]aise de d[ée]veloppement|"
    r"bpifrance|tr[ée]sor|\bADEME\b|banque des territoires|cour des comptes|"
    r"\bIGF\b|inspection g[ée]n[ée]rale des finances|\bDGFIP\b|finances publiques|"
    r"[ée]conomie,? des finances|\bFRR\b|fonds de r[ée]serve|\bCNP\b|"
    r"agence des participations|\bAPE\b|\bIEDOM\b|\bIEOM\b",
    re.I,
)

_RX_CSP_INTITULE = re.compile(
    # Pas « climat » seul : plans climat territoriaux, et meme « climat scolaire ».
    r"\bESG\b|\bRSE\b|finance durable|extra-?financ|taxonomie|\bISR\b|"
    r"analyste financ|analyste investissement|risques? financ|finance climat",
    re.I,
)

_RX_CSP_TITRE = re.compile(
    r'<h3 class="fr-card__title">\s*<a\s+href="([^"]+)"[^>]*>\s*([^<]+?)\s*</a>'
)

_RX_CSP_CHAMP = re.compile(r'<span class="sr-only">([^<]+?) : </span>\s*(.*?)\s*</li>', re.S)


def fetch_service_public() -> list[dict[str, Any]]:
    import httpx

    out, vus = [], set()
    try:
        for mot in CSP_MOTS:
            for page in (1, 2):
                url = f"{CSP}/nos-offres/filtres/mot-cles/{quote(mot)}/" + (
                    f"page/{page}/" if page > 1 else ""
                )
                r = _commun._get_borne(httpx, url, timeout=20, headers=UA, follow_redirects=True)
                if _ats_ko("service_public", mot, r):
                    break
                # Une carte contient ses propres <li> : on decoupe sur son
                # ouverture plutot que de chercher sa fermeture.
                for carte in r.text.split('<li class="fr-col-12 item">')[1:]:
                    m = _RX_CSP_TITRE.search(carte)
                    if not m or m.group(1) in vus:
                        continue
                    vus.add(m.group(1))
                    ch = {k.strip(): _texte_brut(v) for k, v in _RX_CSP_CHAMP.findall(carte)}
                    out.append(
                        _mk(
                            html.unescape(m.group(2)),
                            m.group(1),
                            ch.get("Employeur") or "Fonction publique",
                            ch.get("Localisation", ""),
                            "",
                            "service_public",
                        )
                    )
                time.sleep(_workday.WORKDAY_PAUSE)
    except Exception as e:
        INCIDENTS["service_public"][type(e).__name__] += 1
    return [
        o
        for o in out
        if o["titre"]
        and o["url"]
        and title_ok(o["titre"])
        and (_RX_CSP_EMPLOYEUR.search(o["entreprise"]) or _RX_CSP_INTITULE.search(o["titre"]))
    ]


# Impactpool : agregateur des organisations internationales (ONU, OCDE, BEI,
# banques de developpement). robots.txt n'interdit rien. Trouve le 2026-10-08
# en cherchant ou publient les organisations dont la vitrine repond 403 :
# leur vitrine refuse, leurs offres sont ici.
IMPACTPOOL = "https://www.impactpool.org"

# Mesure du 2026-10-08 : 7 recherches a 0,6 s d'intervalle -> la 1re rend 200,
# les 6 suivantes 403. Un refus s'arrete (regle du projet) : peu de mots, une
# longue pause, et arret au premier refus — pas de nouvelle tentative.
# NON BRANCHE dans scan_autres : relance 1 min plus tard, la 1re requete rend
# deja 403 (adresse marquee). A reessayer au plus tot le 2026-11-08, a la main.
IMPACTPOOL_MOTS = ["sustainable finance", "ESG", "climate finance"]

IMPACTPOOL_PAUSE = 15

_RX_IP_CARTE = re.compile(
    r"<div class='job'>.*?<a[^>]*href=\"(/jobs/\d+)\".*?<h3[^>]*>\s*([^<]+?)\s*</h3>"
    r".*?type='bodyEmphasis'>\s*([^<]+?)\s*<.*?type='bodyEmphasis'>([^<]*)</div>",
    re.S,
)


def fetch_impactpool() -> list[dict[str, Any]]:
    import httpx

    out, vus = [], set()
    try:
        for mot in IMPACTPOOL_MOTS:
            r = _commun._get_borne(
                httpx,
                f"{IMPACTPOOL}/search?q={quote(mot)}",
                timeout=20,
                headers=UA,
                follow_redirects=True,
            )
            if _ats_ko("impactpool", mot, r):
                break  # refus : on s'arrete
            for chemin, titre, org, lieu in _RX_IP_CARTE.findall(r.text):
                if chemin in vus:
                    continue
                vus.add(chemin)
                out.append(
                    _mk(
                        html.unescape(titre),
                        IMPACTPOOL + chemin,
                        html.unescape(org),
                        html.unescape(lieu.strip()),
                        "",
                        "impactpool",
                    )
                )
            time.sleep(IMPACTPOOL_PAUSE)
    except Exception as e:
        INCIDENTS["impactpool"][type(e).__name__] += 1
    return [o for o in out if o["titre"] and o["url"] and title_ok(o["titre"])]


def _texte_brut(fragment: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def scan_autres() -> list[dict[str, Any]]:
    offres = []
    for kind, cle, nom in _commun.AUTRES_FLUX:
        got = fetch_autre(kind, cle, nom)
        _log.info(f"  ✓ {kind}:{cle.split('|')[0]} → {len(got)} offres")
        offres.extend(got)
        time.sleep(ATS_PAUSE)
    got = fetch_service_public()
    _log.info(f"  ✓ choisirleservicepublic → {len(got)} offres")
    offres.extend(got)
    return offres
