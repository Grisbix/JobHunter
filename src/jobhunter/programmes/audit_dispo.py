#!/usr/bin/env python3
"""audit_dispo.py — Checks that the queue's offers are still open, and removes those that
no longer are.

TWO ROUTES, without a browser:
  - LinkedIn: the guest API `jobPosting/<id>` carries `closed-job` / "No longer
    accepting applications" when the job is closed (same detector as
    recheck_dead.linkedin_fast). ~1 s per offer.
  - the other sites: HTTP 404/410, or an expiry message in the page.

THE LOOP, AND ITS LIMIT. LinkedIn answers 429 ("too many requests") after about 1900
checks: it is a rate limit, which says "try again later". The program then WAITS —
the Retry-After header if there is one, otherwise 15 min, doubled at each refusal up
to 60 — then resumes where it stopped. After --pauses waits, it saves and gives
control back; the next run resumes thanks to the state on disk.

THE DURATION (--duree N, in minutes). The program stops ON ITS OWN after N minutes of
checking, then removes what it found closed. Without it, the pipeline's timer killed
it: from 08 to 18/10/2026, step 4b was cut at 45 min EVERY day, before reaching the
deletion — 30 to 60 closed offers found per day, none removed. A rate-limit wait that
would exceed the duration is not started.

A 403, a 999 or a CAPTCHA page are a refusal, not a limit (ADR 0004 below): the offer
is marked "invérifiable" and the program moves to the next one.

THE STATE lives in `_audit_dispo.json` (oid -> [status, note, url, date]). An offer
checked less than --frais days ago is not checked again: a stop, intended or not,
only costs the check in progress.

THE DELETION (--supprime) goes through queue_io.transaction, after copying the queue
into _sauvegardes/<date>_avant_audit/. It ALWAYS spares the offers of suivi.json and
the SEARCH rows. Reasons:
  - closed, verified (LinkedIn API, 404/410);
  - closed according to the page text;
  - already marked MORT / EXPIREE / FERMEE;
  - with --age-max N: unverifiable AND collected more than N days ago.

Run:
  python JobHunter.pyw dispo                    # check, only writes the state
  python JobHunter.pyw dispo --supprime         # check then remove the closed ones
  python JobHunter.pyw dispo --supprime --age-max 60
  python JobHunter.pyw dispo --rapport          # summary of the state, without network

Decision: docs/adr/0004-429-wait-403-stop.md
"""

import argparse
import collections
import datetime
import json
import os
import re
import shutil
import sys
import time
from concurrent.futures import ThreadPoolExecutor

from jobhunter import racine as _racine

sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)  # type: ignore[union-attr]  # console : TextIOWrapper

HERE = _racine.scripts()

from jobhunter.stockage import file as queue_io  # noqa: E402
from jobhunter.stockage import suivi as suivi_io  # noqa: E402

ETAT = HERE / "_audit_dispo.json"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# Same patterns as recheck_dead: two formats of LinkedIn offer URL.
_RX_LI_ID = re.compile(r"/jobs/view/(?:[^/?#]*?-)?(\d{6,})(?:[/?#]|$)")
_RX_LI_FERME = re.compile(r"closed-job|no longer accepting applications", re.I)

# Expiry message in an HTTP 200 page. Checked on Talent ("Cette
# offre n'est plus disponible"), SmartRecruiters ("offre a expiré"), WTJ.
_RX_MORT = re.compile(
    r"no longer (?:available|accepting|active)|job has expired"
    r"|this job (?:is|has been) (?:closed|filled|removed|expired)"
    r"|offre (?:n'est plus|n’est plus) (?:disponible|en ligne|active)"
    r"|annonce (?:a expiré|n'est plus|n’est plus)"
    r"|offre (?:a expiré|est expirée|a été pourvue)"
    r"|position has been filled|job is no longer|cette offre n.est plus",
    re.I,
)

# A generic careers page often says "no longer available" somewhere:
# the text only counts if the URL designates a specific offer.
_RX_URL_GENERIQUE = re.compile(r"^https?://[^/]+/?(?:[a-z]{2}(?:-[a-z]{2})?/?)?$", re.I)

REFUS_DEBIT = {429}  # rate limit: we wait and resume
REFUS_ENTREE = {401, 403, 999}  # anti-bot: we do not loop


def _date_collecte(o):
    for k in ("source", "process", "date_pub"):
        m = re.search(r"20\d\d-\d\d-\d\d", str(o.get(k) or ""))
        if m:
            return m.group()
    return ""


def charger_etat():
    try:
        return json.loads(ETAT.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def sauver_etat(etat):
    tmp = ETAT.with_suffix(".tmp")
    tmp.write_text(json.dumps(etat, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, ETAT)


def _attente(r, n):
    """Seconds to wait after the n-th 429 in a row."""
    try:
        ra = int(r.headers.get("Retry-After", ""))
        if 0 < ra <= 3600:
            return ra
    except (ValueError, AttributeError):
        pass
    return min(15 * 60 * 2 ** (n - 1), 60 * 60)


def controle_autre(url):
    # job_sources' shared client: one TLS connection per host, not per
    # request (~3 s saved at each call, see _client_partage).
    from jobhunter import sources as job_sources

    try:
        r = job_sources._get_borne(
            job_sources._client_partage(), url, timeout=20, headers=UA, follow_redirects=True
        )
    except Exception as e:
        return None, type(e).__name__
    if r.status_code in (404, 410):
        return "FERMEE", f"HTTP {r.status_code}"
    if r.status_code != 200:
        return None, f"HTTP {r.status_code}"
    if "captcha" in str(r.url).lower():
        return None, "captcha"
    m = _RX_MORT.search(r.text[:300000])
    if m and not _RX_URL_GENERIQUE.match(url):
        return "FERMEE_TEXTE", m.group(0)
    return "OK", "200"


def verifier(cibles, etat, pauses_max, aujourd_hui, fin=None):
    """Checks the targets; returns True if all of them were. `fin`: instant
    (time.monotonic) at which to stop on its own, None = no duration."""
    import httpx

    def temps_ecoule(marge=0):
        return fin is not None and time.monotonic() + marge >= fin

    li = [o for o in cibles if _RX_LI_ID.search(o["url"])]
    autres = [o for o in cibles if not _RX_LI_ID.search(o["url"])]
    print(f"{len(li)} LinkedIn, {len(autres)} autres sites a controler")

    c = collections.Counter()
    with ThreadPoolExecutor(8) as ex:
        for o, (st, note) in zip(autres, ex.map(lambda o: controle_autre(o["url"]), autres)):
            etat[queue_io.oid(o)] = [st, note, o["url"], aujourd_hui]
            c[st or "invérifiable"] += 1
    sauver_etat(etat)
    print(f"  autres sites : {dict(c)}")

    c = collections.Counter()
    pauses = refus = 0
    cl = httpx.Client(timeout=15, headers=UA, follow_redirects=True)
    i = 0
    while i < len(li):
        if temps_ecoule():
            print(f"  ⏱ duree ecoulee — arret a {i}/{len(li)}, la prochaine relance reprendra ici")
            break
        o = li[i]
        oid = queue_io.oid(o)
        url = f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{_RX_LI_ID.search(o['url']).group(1)}"
        try:
            r = cl.get(url)
        except Exception as e:
            etat[oid] = [None, type(e).__name__, o["url"], aujourd_hui]
            i += 1
            continue
        if r.status_code in REFUS_DEBIT:
            refus += 1
            if refus < 3:  # an isolated 429: short pause
                time.sleep(30)
                continue
            if pauses >= pauses_max or temps_ecoule(_attente(r, pauses + 1)):
                print(
                    f"  ⏸ LinkedIn limite toujours apres {pauses} pause(s) — "
                    f"arret a {i}/{len(li)}, la prochaine relance reprendra ici"
                )
                break
            pauses += 1
            s = _attente(r, pauses)
            sauver_etat(etat)
            print(
                f"  ⏸ LinkedIn : limite de debit (429) a {i}/{len(li)} — "
                f"pause {pauses}/{pauses_max} de {s // 60} min, puis reprise"
            )
            time.sleep(s)
            refus = 0
            continue
        refus = 0
        if r.status_code in REFUS_ENTREE:
            print(f"  ✋ LinkedIn refuse l'entree (HTTP {r.status_code}) — arret, pas de boucle")
            break
        if r.status_code == 404:
            st, note = "FERMEE", "guest 404"
        elif r.status_code == 200 and len(r.text) >= 400:
            st, note = (
                ("FERMEE", "no longer accepting")
                if _RX_LI_FERME.search(r.text)
                else ("OK", "ouverte")
            )
        else:
            st, note = None, f"HTTP {r.status_code}"
        etat[oid] = [st, note, o["url"], aujourd_hui]
        c[st or "invérifiable"] += 1
        i += 1
        time.sleep(0.5)
        if i % 250 == 0:
            sauver_etat(etat)
            print(f"  -- {i}/{len(li)} {dict(c)}")
    sauver_etat(etat)
    print(f"  LinkedIn : {dict(c)}")
    return i >= len(li)


# ── FIND THE OFFER AGAIN THROUGH THE CHANNEL THAT FOUND IT ───────────────────
# APEC, Glassdoor, Indeed and WTJ refuse robots on the offer's PAGE
# (403, CAPTCHA, 202): the direct check returns "invérifiable" — 951 offers
# on 2026-10-02. But these offers came in through a channel that does answer:
# the APEC search API, the WTJ sitemap, the Glassdoor search. What
# served to find them serves to find them again.


def _domaine(url):
    from urllib.parse import urlparse

    return urlparse(str(url or "")).netloc.lower().replace("www.", "")


def _wtj_urls():
    """All the offer URLs of the WTJ sitemap, or None if unreadable.

    The sitemap lists the postings ONLINE (88,000 on 24/09): an offer that is no
    longer in it was withdrawn. No offer page visited, hence no anti-bot wall."""
    import gzip

    import httpx

    from jobhunter.programmes.wtj_desc import UA as _WUA
    from jobhunter.sources import WTJ_SITEMAP, _get_borne

    def lire(client, url):
        r = _get_borne(client, url, headers=_WUA, timeout=90)
        if r.status_code != 200:
            return ""
        b = r.content
        if b[:2] == b"\x1f\x8b":
            b = gzip.decompress(b)
        return b.decode("utf-8", "replace")

    urls = set()
    try:
        with httpx.Client(follow_redirects=True) as client:
            idx = lire(client, WTJ_SITEMAP)
            for f in re.findall(r"<loc>([^<]+)</loc>", idx):
                if "job-listings" in f:
                    urls.update(
                        u.rstrip("/").lower()
                        for u in re.findall(r"<loc>([^<]+)</loc>", lire(client, f))
                    )
    except Exception as e:
        print(f"  ~ WTJ : sitemap illisible ({type(e).__name__})")
        return None
    # A truncated sitemap would make all our offers look withdrawn.
    return urls if len(urls) > 10000 else None


def _apec_numero(url):
    m = re.search(r"detail-offre/([0-9]+[A-Z]?)", str(url or ""))
    return m.group(1) if m else None


# APEC is behind DataDome: ~540 requests in a burst closed it on the evening of
# 02/10, collection included. At most 150 offers per pass (~300 requests):
# the stock is checked in a few days without exposing the collection.
APEC_PAR_PASSE = 150


def par_la_source(q, etat, aujourd_hui, limite):
    """Tranche les invérifiables APEC et WTJ par leur canal de collecte."""
    from jobhunter import sources as job_sources

    a_voir = []
    for o in q:
        v = etat.get(queue_io.oid(o))
        if not v or v[0] is not None:
            continue  # already decided, or never seen
        if len(v) > 3 and str(v[1]).startswith("source") and v[3] >= limite:
            continue
        a_voir.append(o)
    wtj = [o for o in a_voir if "welcometothejungle" in _domaine(o["url"])]
    apec = [o for o in a_voir if _apec_numero(o["url"])][:APEC_PAR_PASSE]
    c = collections.Counter()

    if wtj:
        en_ligne = _wtj_urls()
        if en_ligne is None:
            print("  WTJ : sitemap indisponible, rien tranche")
        else:
            for o in wtj:
                u = o["url"].split("?")[0].rstrip("/").lower()
                st = "OK" if u in en_ligne else "FERMEE_SOURCE"
                etat[queue_io.oid(o)] = [st, "source: sitemap WTJ", o["url"], aujourd_hui]
                c[f"wtj {st}"] += 1

    refus = 0
    for i, o in enumerate(apec):
        if refus >= job_sources.APEC_ABANDON:
            print(f"  ⏸ APEC : {refus} refus d'affilee — reprise a la prochaine passe")
            break
        num, titre = _apec_numero(o["url"]), (o.get("poste") or "").strip()
        vus, total, refuse = set(), 0, False
        # The exact title, two pages of 50. Missing WHILE the search
        # returned everything (total <= what we read): withdrawn. Missing from a search
        # longer than two pages: we do not know, we do not decide.
        for page in range(2):
            res, total = job_sources._apec_page(titre, page * job_sources.APEC_PAR_PAGE)
            time.sleep(job_sources.APEC_PAUSE)
            if res is None:
                refus += 1
                refuse = True
                break
            refus = 0
            vus.update(str(r.get("numeroOffre") or r.get("id") or "") for r in res)
            if num in vus or len(vus) >= total or not res:
                break
        if refuse:
            continue
        if num in vus:
            st = "OK"
        elif total and len(vus) >= total:
            st = "FERMEE_SOURCE"
        else:
            st = None
        etat[queue_io.oid(o)] = [st, "source: recherche APEC", o["url"], aujourd_hui]
        c[f"apec {st or 'indecis'}"] += 1
        if (i + 1) % 50 == 0:
            sauver_etat(etat)
            print(f"  -- APEC {i + 1}/{len(apec)} {dict(c)}")
    sauver_etat(etat)
    print(f"  par la source : {dict(c)}")


def motif(o, etat, suivi, seuil, absente=None):
    oid = queue_io.oid(o)
    if oid in suivi or o.get("url_type") == "RECHERCHE":
        return None
    v = etat.get(oid)
    st = v[0] if v else None
    if st == "FERMEE":
        return "fermee (verifiee)"
    if st == "FERMEE_TEXTE":
        return "fermee (texte de la page)"
    if st == "FERMEE_SOURCE":
        return "retiree par sa source (sitemap, recherche)"
    if (o.get("link_status") or "") in ("MORT", "EXPIREE", "FERMEE"):
        return "deja marquee morte"
    if seuil and st is None:
        d = _date_collecte(o)
        if d and d < seuil:
            return "invérifiable et ancienne"
    # NO LONGER SERVED BY ITS SOURCE. Glassdoor and Indeed offer neither a sitemap nor
    # a targeted search: only the daily collection sees them again, and it sets
    # `vu_le`. If the channel works (it served other offers in the last three
    # days) and has not served this one for `absente` days, it is
    # withdrawn. Channel down: we conclude nothing.
    if absente and st is None:
        limite_vue, canal_vivant = absente
        if canal_vivant.get(_domaine(o.get("url"))):
            vue = max(str(o.get("vu_le") or ""), _date_collecte(o))
            if vue and vue < limite_vue:
                return "plus servie par sa source"
    return None


def supprimer(etat, age_max, aujourd_hui, copier=True, absente_jours=30):
    seuil = ""
    if age_max:
        seuil = (
            datetime.date.fromisoformat(aujourd_hui) - datetime.timedelta(days=age_max)
        ).isoformat()
    # In the pipeline, today's backup already exists (taken before any
    # step): a second copy would count in its seven rolling days.
    copie = None
    if copier:
        copie = HERE / "_sauvegardes" / f"{aujourd_hui}_avant_audit"
        copie.mkdir(parents=True, exist_ok=True)
        for f in ("apply_queue.json", "descriptions.json"):
            if (HERE / f).exists():
                shutil.copy2(HERE / f, copie / f)
    suivi = suivi_io.charger()
    motifs = collections.Counter()
    with queue_io.transaction(descriptions=False) as q:
        absente = None
        if absente_jours:
            j = datetime.date.fromisoformat(aujourd_hui)
            recent = (j - datetime.timedelta(days=3)).isoformat()
            canal_vivant = collections.defaultdict(bool)
            for o in q:
                if str(o.get("vu_le") or "") >= recent:
                    canal_vivant[_domaine(o.get("url"))] = True
            absente = ((j - datetime.timedelta(days=absente_jours)).isoformat(), canal_vivant)
        avant, garde = len(q), []
        for o in q:
            m = motif(o, etat, suivi, seuil, absente)
            if m:
                motifs[m] += 1
                continue
            v = etat.get(queue_io.oid(o))
            if v and v[0] == "OK":
                o["link_status"], o["ls_check"] = "OK", v[3]
            garde.append(o)
        q[:] = garde
    print(
        f"file {avant} -> {len(garde)} : {avant - len(garde)} retirees"
        + (f" (copie : {copie.relative_to(HERE)})" if copie else "")
    )
    for m, n in motifs.most_common():
        print(f"  {n:5}  {m}")


def _fit(o):
    try:
        return int(str(o.get("fit") or 0))
    except ValueError:
        return 0


def choisir_cibles(q, etat, suivi, j, frais=0):
    """The offers to check today, the most important first.

    Sets in passing, in `etat`, "OK" for those that a source has just served again:
    no request for a known answer."""
    jours = lambda n: (j - datetime.timedelta(days=n)).isoformat()
    # THE PACE FOLLOWS THE AGE. Measured on 5441 LinkedIn checks of 02/10:
    # 8% of offers closed before 7 days, ~20% between 7 and 20, 37-40% beyond
    # three weeks. A young offer is checked again every 10 days, an
    # offer older than two weeks every 5.
    # SPREADING. A full audit dates all the offers on the same day, which
    # would then all come back together: ~4000 checks on the 6th day, three
    # hours in a step capped at 45 min. Each offer gets a fixed offset
    # of 0 to 2 days, drawn from its identity (stable from one day to the next).
    import zlib

    def limite_pour(o):
        if frais:
            return jours(frais)
        d = _date_collecte(o)
        base = 10 if d and d >= jours(14) else 5
        return jours(base + zlib.crc32(queue_io.oid(o).encode()) % 3)

    revue_recente = jours(2)
    # A site that refused entry (APEC behind DataDome, Glassdoor, Indeed)
    # will refuse again tomorrow: asking again every day proves nothing and
    # exposes us to being banned from the collection TOO. Once a month is enough.
    limite_refus = jours(30)
    cibles = []
    for o in q:
        oid = queue_io.oid(o)
        if oid in suivi or o.get("url_type") == "RECHERCHE":
            continue
        if not str(o.get("url") or "").startswith("http"):
            continue
        # SEEN AGAIN BY THE COLLECTION = OPEN. If a source served the offer again in the
        # last two days (vu_le, set at merge), it is online: checking
        # it again would cost a request for a known answer.
        if str(o.get("vu_le") or "") >= revue_recente:
            etat[oid] = ["OK", "source: revue par la collecte", o["url"], o["vu_le"]]
            continue
        v = etat.get(oid)
        if v and len(v) > 3:
            refus = v[0] is None and re.match(r"HTTP (?:401|403|999)|captcha", str(v[1]))
            if v[3] >= (limite_refus if refus else limite_pour(o)):
                continue
        cibles.append(o)
    # THE BEST FIRST. A rate limit or the maximum duration of
    # the step cut the pass; what remains to be done must be what matters
    # least. Decreasing fit, then the oldest (the most often closed).
    cibles.sort(key=lambda o: (-_fit(o), _date_collecte(o) or "9999"))
    return cibles


def rapport(etat):
    c = collections.Counter(v[0] or "invérifiable" for v in etat.values())
    print(f"{len(etat)} offres controlees : {dict(c)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--supprime", action="store_true", help="retire les offres fermees")
    ap.add_argument(
        "--age-max",
        type=int,
        default=0,
        help="retire aussi les invérifiables collectees il y a plus de N jours",
    )
    ap.add_argument(
        "--frais",
        type=int,
        default=0,
        help="intervalle fixe de recontrole en jours (0 = selon l'age de l'offre)",
    )
    ap.add_argument(
        "--pauses",
        type=int,
        default=4,
        help="nombre max de pauses sur limite de debit avant de rendre la main",
    )
    ap.add_argument("--rapport", action="store_true", help="bilan de l'etat, sans reseau")
    ap.add_argument(
        "--sans-copie",
        action="store_true",
        help="pas de copie avant suppression (le pipeline a deja la sienne)",
    )
    ap.add_argument("--limite", type=int, default=0, help="plafond d'offres a controler (essai)")
    ap.add_argument(
        "--duree",
        type=float,
        default=0,
        help="minutes de controle au plus, puis suppression (0 = sans limite)",
    )
    ap.add_argument(
        "--absente",
        type=int,
        default=30,
        help="retire une invérifiable que sa source ne sert plus depuis N jours (0 = non)",
    )
    ap.add_argument(
        "--sans-source",
        action="store_true",
        help="ne pas retrouver les invérifiables par leur canal (APEC, WTJ)",
    )
    a = ap.parse_args()

    etat = charger_etat()
    if a.rapport:
        rapport(etat)
        return 0
    aujourd_hui = datetime.date.today().isoformat()
    suivi = suivi_io.charger()
    q = queue_io.charger(descriptions=False)
    cibles = choisir_cibles(q, etat, suivi, datetime.date.today(), a.frais)
    limite = (datetime.date.today() - datetime.timedelta(days=a.frais or 5)).isoformat()
    if a.limite:
        cibles = cibles[: a.limite]
    fin = time.monotonic() + a.duree * 60 if a.duree else None
    complet = verifier(cibles, etat, a.pauses, aujourd_hui, fin)
    if not a.sans_source and (fin is None or time.monotonic() < fin):
        par_la_source(q, etat, aujourd_hui, limite)
    rapport(etat)
    if a.supprime:
        supprimer(etat, a.age_max, aujourd_hui, copier=not a.sans_copie, absente_jours=a.absente)
    return 0 if complet else 4


if __name__ == "__main__":
    sys.exit(main())
