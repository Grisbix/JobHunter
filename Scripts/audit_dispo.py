#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""audit_dispo.py — Verifie que les offres de la file sont encore ouvertes, et
retire celles qui ne le sont plus.

DEUX VOIES, sans navigateur :
  - LinkedIn : l'API guest `jobPosting/<id>` porte `closed-job` / « No longer
    accepting applications » quand le poste est ferme (meme detecteur que
    recheck_dead.linkedin_fast). ~1 s par offre.
  - les autres sites : HTTP 404/410, ou un message d'expiration dans la page.

LA BOUCLE, ET SA LIMITE. LinkedIn repond 429 (« trop de demandes ») au bout
d'environ 1900 controles : c'est une limite de debit, qui dit « reessaie plus
tard ». Le programme ATTEND alors — l'en-tete Retry-After s'il existe, sinon
15 min, doublees a chaque refus jusqu'a 60 — puis reprend ou il s'etait
arrete. Au bout de --pauses attentes, il sauvegarde et rend la main ; la
relance suivante reprend grace a l'etat sur disque.

Un 403, un 999 ou une page CAPTCHA, eux, ne sont PAS une limite de debit :
c'est un refus d'entree (APEC derriere DataDome, Glassdoor, Indeed). On ne
boucle pas dessus — on note « invérifiable » et on passe. Aucun contournement,
aucune rotation d'IP, aucune resolution de CAPTCHA.

L'ETAT vit dans `_audit_dispo.json` (oid -> [statut, note, url, date]). Une
offre controlee depuis moins de --frais jours n'est pas recontrolee : un arret,
voulu ou non, ne coute que le controle en cours.

LA SUPPRESSION (--supprime) passe par queue_io.transaction, apres copie de la
file dans _sauvegardes/<date>_avant_audit/. Elle epargne TOUJOURS les offres de
suivi.json et les lignes RECHERCHE. Motifs :
  - fermee verifiee (API LinkedIn, 404/410) ;
  - fermee d'apres le texte de la page ;
  - deja marquee MORT / EXPIREE / FERMEE ;
  - avec --age-max N : invérifiable ET collectee il y a plus de N jours.

Run :
  python audit_dispo.py                    # controle, n'ecrit que l'etat
  python audit_dispo.py --supprime         # controle puis retire les fermees
  python audit_dispo.py --supprime --age-max 60
  python audit_dispo.py --rapport          # bilan de l'etat, sans reseau
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
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import queue_io   # noqa: E402
import suivi_io   # noqa: E402

ETAT = HERE / "_audit_dispo.json"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# Memes motifs que recheck_dead : deux formats d'URL d'offre LinkedIn.
_RX_LI_ID = re.compile(r"/jobs/view/(?:[^/?#]*?-)?(\d{6,})(?:[/?#]|$)")
_RX_LI_FERME = re.compile(r"closed-job|no longer accepting applications", re.I)

# Message d'expiration dans une page HTTP 200. Verifie sur Talent (« Cette
# offre n'est plus disponible »), SmartRecruiters (« offre a expire »), WTJ.
_RX_MORT = re.compile(
    r"no longer (?:available|accepting|active)|job has expired"
    r"|this job (?:is|has been) (?:closed|filled|removed|expired)"
    r"|offre (?:n'est plus|n’est plus) (?:disponible|en ligne|active)"
    r"|annonce (?:a expiré|n'est plus|n’est plus)"
    r"|offre (?:a expiré|est expirée|a été pourvue)"
    r"|position has been filled|job is no longer|cette offre n.est plus", re.I)

# Une page carrieres generique dit souvent « no longer available » quelque
# part : le texte ne vaut que si l'URL designe une offre precise.
_RX_URL_GENERIQUE = re.compile(r"^https?://[^/]+/?(?:[a-z]{2}(?:-[a-z]{2})?/?)?$", re.I)

REFUS_DEBIT = {429}                 # limite de debit : on attend et on reprend
REFUS_ENTREE = {401, 403, 999}      # anti-bot : on ne boucle pas


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
    """Secondes a attendre apres le n-ieme 429 d'affilee."""
    try:
        ra = int(r.headers.get("Retry-After", ""))
        if 0 < ra <= 3600:
            return ra
    except (ValueError, AttributeError):
        pass
    return min(15 * 60 * 2 ** (n - 1), 60 * 60)


def controle_autre(url):
    # Client partage de job_sources : une connexion TLS par hote, pas par
    # requete (~3 s epargnees a chaque appel, voir _client_partage).
    import job_sources
    try:
        r = job_sources._get_borne(job_sources._client_partage(), url, timeout=20,
                                   headers=UA, follow_redirects=True)
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


def verifier(cibles, etat, pauses_max, aujourd_hui):
    import httpx
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
            if refus < 3:                       # un 429 isole : courte pause
                time.sleep(30)
                continue
            if pauses >= pauses_max:
                print(f"  ⏸ LinkedIn limite toujours apres {pauses} pause(s) — "
                      f"arret a {i}/{len(li)}, la prochaine relance reprendra ici")
                break
            pauses += 1
            s = _attente(r, pauses)
            sauver_etat(etat)
            print(f"  ⏸ LinkedIn : limite de debit (429) a {i}/{len(li)} — "
                  f"pause {pauses}/{pauses_max} de {s // 60} min, puis reprise")
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
            st, note = ("FERMEE", "no longer accepting") if _RX_LI_FERME.search(r.text) else ("OK", "ouverte")
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


# ── RETROUVER L'OFFRE PAR LE CANAL QUI L'A TROUVEE ───────────────────────────
# APEC, Glassdoor, Indeed et WTJ refusent les robots sur la PAGE de l'offre
# (403, CAPTCHA, 202) : le controle direct rend « invérifiable » — 951 offres
# le 2026-10-02. Mais ces offres sont entrees par un canal qui, lui, repond :
# l'API de recherche APEC, le sitemap WTJ, la recherche Glassdoor. Ce qui a
# servi a les trouver sert a les retrouver.

def _domaine(url):
    from urllib.parse import urlparse
    return urlparse(str(url or "")).netloc.lower().replace("www.", "")


def _wtj_urls():
    """Toutes les URL d'offres du sitemap WTJ, ou None si illisible.

    Le sitemap liste les annonces EN LIGNE (88 000 le 24/09) : une offre qui
    n'y figure plus a ete retiree. Pas de page d'offre visitee, donc pas de
    mur anti-bot."""
    import gzip
    import httpx
    from job_sources import WTJ_SITEMAP, _get_borne
    from wtj_desc import UA as _WUA

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
                    urls.update(u.rstrip("/").lower() for u in
                                re.findall(r"<loc>([^<]+)</loc>", lire(client, f)))
    except Exception as e:
        print(f"  ~ WTJ : sitemap illisible ({type(e).__name__})")
        return None
    # Un sitemap tronque ferait passer toutes nos offres pour retirees.
    return urls if len(urls) > 10000 else None


def _apec_numero(url):
    m = re.search(r"detail-offre/([0-9]+[A-Z]?)", str(url or ""))
    return m.group(1) if m else None


# APEC est derriere DataDome : ~540 requetes en rafale l'ont fermee le 02/10
# au soir, collecte comprise. Au plus 150 offres par passe (~300 requetes) :
# le stock se verifie en quelques jours sans exposer la collecte.
APEC_PAR_PASSE = 150


def par_la_source(q, etat, aujourd_hui, limite):
    """Tranche les invérifiables APEC et WTJ par leur canal de collecte."""
    import job_sources
    a_voir = []
    for o in q:
        v = etat.get(queue_io.oid(o))
        if not v or v[0] is not None:
            continue                       # deja tranchee, ou jamais vue
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
        # L'intitule exact, deux pages de 50. Absente ALORS QUE la recherche a
        # tout rendu (total <= ce qu'on a lu) : retiree. Absente d'une recherche
        # plus longue que deux pages : on ne sait pas, on ne tranche pas.
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
    # PLUS SERVIE PAR SA SOURCE. Glassdoor et Indeed n'offrent ni sitemap ni
    # recherche ciblee : seule la collecte quotidienne les revoit, et elle pose
    # `vu_le`. Si le canal fonctionne (il a servi d'autres offres ces trois
    # derniers jours) et ne sert plus celle-ci depuis `absente` jours, elle est
    # retiree. Canal en panne : on ne conclut rien.
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
        seuil = (datetime.date.fromisoformat(aujourd_hui)
                 - datetime.timedelta(days=age_max)).isoformat()
    # Dans le pipeline, la sauvegarde du jour existe deja (prise avant toute
    # etape) : une seconde copie compterait dans ses sept jours glissants.
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
            absente = ((j - datetime.timedelta(days=absente_jours)).isoformat(),
                       canal_vivant)
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
    print(f"file {avant} -> {len(garde)} : {avant - len(garde)} retirees"
          + (f" (copie : {copie.relative_to(HERE)})" if copie else ""))
    for m, n in motifs.most_common():
        print(f"  {n:5}  {m}")


def _fit(o):
    try:
        return int(str(o.get("fit") or 0))
    except ValueError:
        return 0


def choisir_cibles(q, etat, suivi, j, frais=0):
    """Les offres a controler aujourd'hui, les plus importantes d'abord.

    Pose au passage, dans `etat`, « OK » pour celles qu'une source vient de
    resservir : pas de requete pour une reponse connue."""
    jours = lambda n: (j - datetime.timedelta(days=n)).isoformat()
    # LE RYTHME SUIT L'AGE. Mesure sur 5441 controles LinkedIn du 02/10 :
    # 8 % d'offres fermees avant 7 jours, ~20 % entre 7 et 20, 37-40 % au-dela
    # de trois semaines. Une offre jeune se recontrole tous les 10 jours, une
    # offre de plus de deux semaines tous les 5.
    # ETALEMENT. Un audit complet date toutes les offres du meme jour, qui
    # reviendraient alors toutes ensemble : ~4000 controles le 6e jour, trois
    # heures dans une etape bornee a 45 min. Chaque offre recoit un decalage
    # fixe de 0 a 2 jours, tire de son identite (stable d'un jour a l'autre).
    import zlib
    def limite_pour(o):
        if frais:
            return jours(frais)
        d = _date_collecte(o)
        base = 10 if d and d >= jours(14) else 5
        return jours(base + zlib.crc32(queue_io.oid(o).encode()) % 3)
    revue_recente = jours(2)
    # Un site qui a refuse l'entree (APEC derriere DataDome, Glassdoor, Indeed)
    # refusera encore demain : le redemander chaque jour ne prouve rien et
    # l'expose a nous bannir AUSSI de la collecte. Une fois par mois suffit.
    limite_refus = jours(30)
    cibles = []
    for o in q:
        oid = queue_io.oid(o)
        if oid in suivi or o.get("url_type") == "RECHERCHE":
            continue
        if not str(o.get("url") or "").startswith("http"):
            continue
        # REVUE PAR LA COLLECTE = OUVERTE. Si une source a resservi l'offre ces
        # deux derniers jours (vu_le, pose a la fusion), elle est en ligne : la
        # recontroler couterait une requete pour une reponse connue.
        if str(o.get("vu_le") or "") >= revue_recente:
            etat[oid] = ["OK", "source: revue par la collecte", o["url"], o["vu_le"]]
            continue
        v = etat.get(oid)
        if v and len(v) > 3:
            refus = v[0] is None and re.match(r"HTTP (?:401|403|999)|captcha", str(v[1]))
            if v[3] >= (limite_refus if refus else limite_pour(o)):
                continue
        cibles.append(o)
    # LES MEILLEURES D'ABORD. Une limite de debit ou la duree maximale de
    # l'etape coupent la passe ; ce qui reste a faire doit etre ce qui compte
    # le moins. Fit decroissant, puis la plus ancienne (la plus souvent fermee).
    cibles.sort(key=lambda o: (-_fit(o), _date_collecte(o) or "9999"))
    return cibles


def rapport(etat):
    c = collections.Counter(v[0] or "invérifiable" for v in etat.values())
    print(f"{len(etat)} offres controlees : {dict(c)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--supprime", action="store_true", help="retire les offres fermees")
    ap.add_argument("--age-max", type=int, default=0,
                    help="retire aussi les invérifiables collectees il y a plus de N jours")
    ap.add_argument("--frais", type=int, default=0,
                    help="intervalle fixe de recontrole en jours (0 = selon l'age de l'offre)")
    ap.add_argument("--pauses", type=int, default=4,
                    help="nombre max de pauses sur limite de debit avant de rendre la main")
    ap.add_argument("--rapport", action="store_true", help="bilan de l'etat, sans reseau")
    ap.add_argument("--sans-copie", action="store_true",
                    help="pas de copie avant suppression (le pipeline a deja la sienne)")
    ap.add_argument("--limite", type=int, default=0, help="plafond d'offres a controler (essai)")
    ap.add_argument("--absente", type=int, default=30,
                    help="retire une invérifiable que sa source ne sert plus depuis N jours (0 = non)")
    ap.add_argument("--sans-source", action="store_true",
                    help="ne pas retrouver les invérifiables par leur canal (APEC, WTJ)")
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
        cibles = cibles[:a.limite]
    complet = verifier(cibles, etat, a.pauses, aujourd_hui)
    if not a.sans_source:
        par_la_source(q, etat, aujourd_hui, limite)
    rapport(etat)
    if a.supprime:
        supprimer(etat, a.age_max, aujourd_hui, copier=not a.sans_copie,
                  absente_jours=a.absente)
    return 0 if complet else 4


if __name__ == "__main__":
    sys.exit(main())
