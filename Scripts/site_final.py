#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""site_final.py — Retrouver une offre LinkedIn sur le site de l'employeur.

POURQUOI. 7265 offres de la file sur 8805 n'ont qu'un lien LinkedIn (2026-10-05),
dont 616 a fit >= 9. LinkedIn ne montre le lien du site de l'employeur qu'a un
compte CONNECTE : la page publique dit « Inscrivez-vous pour postuler », et son
HTML ne contient aucune adresse de sortie (verifie sur deux offres Deloitte).
On ne se connecte pas : un compte pilote par programme se fait restreindre, et
aucun programme ne manipule de mot de passe ici.

On prend donc l'autre bout : les API ATS publiques (Greenhouse, Lever, Ashby,
Recruitee, SmartRecruiters), qui rendent en JSON la liste des offres d'une
societe avec leur URL directe. Pour chaque entreprise :
  1. ses flux connus (job_sources.ATS_SLUGS, etat precedent), sinon on sonde
     des slugs plausibles (probe_ats_queue.variantes x 5 API) ;
  2. on VERIFIE que le flux est bien celui de cette societe (verify_ats_slugs :
     « alan » sur Ashby n'est pas forcement l'employeur « Alan ») — seul un
     verdict CONFIRME compte ;
  3. on cherche l'intitule dans le flux ; trouve -> l'offre prend l'URL du site
     final, l'URL LinkedIn est gardee dans `url_linkedin`.

UNE ABSENCE NE PROUVE PAS UNE FERMETURE. Un flux SmartRecruiters plafonne a
100 offres par page, une filiale publie ailleurs, un intitule est reformule.
Une offre absente d'un flux confirme est seulement NOTEE (`site_final` =
« absente du flux »), jamais retiree.

Etat : `_site_final.json`, une entree par entreprise (flux trouves, date).
Une entreprise sans flux n'est resondee qu'apres 30 jours.

Run :
  python site_final.py --dry               # mesure, n'ecrit rien dans la file
  python site_final.py                     # fit >= 9
  python site_final.py --fit 8 --limite 100
"""

import sys
import re
import json
import time
import argparse
import datetime
import unicodedata
import concurrent.futures as cf
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

import queue_io  # noqa: E402
import probe_ats  # noqa: E402
from probe_ats_queue import variantes  # noqa: E402
from verify_ats_slugs import nom_du_flux, verdict, _cle  # noqa: E402

ETAT = HERE / "_site_final.json"
RESONDE_JOURS = 30

UA = probe_ats.UA

# Mentions qui n'appartiennent pas a l'intitule : genre, contrat, lieu.
_RX_GENRE = re.compile(
    r"[(\[]?\s*\b(?:h\s*/\s*f|f\s*/\s*h|m\s*/\s*f(?:\s*/\s*[dx])?|"
    r"f\s*/\s*m(?:\s*/\s*[dx])?|w\s*/\s*m(?:\s*/\s*[dx])?|"
    r"m\s*/\s*w(?:\s*/\s*d)?|all\s+genders?|d\s*/\s*f\s*/\s*m)\b\s*[)\]]?",
    re.I,
)
_RX_BRUIT = re.compile(
    r"\b(?:cdi|cdd|stage|internship|alternance|vie|v\.i\.e|"
    r"paris|la\s+d[ée]fense|lyon|france|remote|hybrid|hybride)\b",
    re.I,
)


_VIDES = {
    "de",
    "du",
    "des",
    "d",
    "la",
    "le",
    "les",
    "l",
    "en",
    "et",
    "a",
    "au",
    "aux",
    "and",
    "of",
    "the",
    "for",
    "in",
    "h",
    "f",
    "m",
    "x",
    "w",
    "e",
}


def _sans_accent(s):
    s = unicodedata.normalize("NFD", str(s or "").lower())
    return "".join(c for c in s if not unicodedata.combining(c))


def titre_cle(t):
    """Intitule reduit a ses mots, pour comparer deux publications de la meme offre."""
    t = _RX_GENRE.sub(" ", str(t or ""))
    t = _RX_BRUIT.sub(" ", t)
    return " ".join(re.split(r"[^a-z0-9]+", _sans_accent(t))).strip()


def meme_titre(a, b):
    """Deux intitules designent-ils la meme annonce ? Strict : une fausse
    correspondance enverrait l'utilisateur postuler a un autre poste."""
    # MEMES MOTS, pas « assez ressemblants ». Un ratio de similarite rattachait
    # « Junior Energy Consultant » a l'annonce « Energy Consultant » (Baringa,
    # 2026-10-05) : un seul mot d'ecart, mais deux postes differents. Seuls les
    # mots vides et l'ordre peuvent varier.
    ma, mb = set(titre_cle(a).split()) - _VIDES, set(titre_cle(b).split()) - _VIDES
    return bool(ma) and ma == mb


def lire_flux(kind, slug, requete=""):
    """[(titre, url, lieu)] d'un flux, ou None si illisible."""
    import httpx

    if kind == "workday":
        return lire_workday(slug, requete)
    url = probe_ats.APIS[kind](slug)
    if kind == "smartrecruiters" and requete:
        from urllib.parse import quote

        url += "&q=" + quote(requete)
    try:
        r = httpx.get(url, timeout=20, headers=UA, follow_redirects=True)
        if r.status_code != 200:
            return None
        d = r.json()
    except Exception:
        return None
    out = []
    try:
        if kind == "greenhouse":
            for j in d.get("jobs", []):
                out.append(
                    (
                        j.get("title", ""),
                        j.get("absolute_url", ""),
                        (j.get("location") or {}).get("name", ""),
                    )
                )
        elif kind == "lever":
            for j in d:
                out.append(
                    (
                        j.get("text", ""),
                        j.get("hostedUrl", ""),
                        (j.get("categories") or {}).get("location", ""),
                    )
                )
        elif kind == "ashby":
            for j in d.get("jobs", []):
                out.append((j.get("title", ""), j.get("jobUrl", ""), j.get("location", "")))
        elif kind == "recruitee":
            for j in d.get("offers", []):
                out.append((j.get("title", ""), j.get("careers_url", ""), j.get("location", "")))
        elif kind == "smartrecruiters":
            for j in d.get("content", []):
                jid = j.get("id") or ""
                out.append(
                    (
                        j.get("name", ""),
                        f"https://jobs.smartrecruiters.com/{slug}/{jid}" if jid else "",
                        (j.get("location") or {}).get("city", ""),
                    )
                )
    except Exception:
        return None
    return [x for x in out if x[0] and x[1]]


# ═══════════════ Workday ═══════════════
# Les grands groupes publient sur *.myworkdayjobs.com, dont l'API JSON est
# publique (celle que leur propre page appelle). Mesure le 2026-10-07 :
#   - POST /wday/cxs/{tenant}/{site}/jobs sur un site inexistant rend 404
#     « not found: Job_Posting_Site_ID » si le tenant existe sur cet hote,
#     422 sinon : une requete par (tenant, hote) suffit a trouver le tenant ;
#   - le nom du site n'a aucune convention (ArdianCareers, erm_Careers,
#     Eiffage_Careers) mais il ignore la casse : on essaie les formes vues ;
#   - la fiche d'une offre donne `hiringOrganization.name`, le nom de
#     l'employeur : c'est la preuve d'identite, en plus du tenant.
WD_HOTES = ["wd1", "wd3", "wd5", "wd10", "wd12", "wd103", "wd105", "wd108", "wd501"]
_WD_SUFFIXES = [
    "Careers",
    "_Careers",
    "_External",
    "External",
    "_External_Careers",
    "ExternalCareers",
    "_Careers_External",
    "",
    "Jobs",
    "_Jobs",
]
_WD_GENERIQUES = [
    "External",
    "Careers",
    "External_Careers",
    "ExternalCareers",
    "ExternalCareerSite",
    "External_Career_Site",
    "Global",
    "Jobs",
    "Search",
    "Experienced",
    "Professional",
    "GlobalCareers",
    "CareerSite",
]
_WD_JSON = {**UA, "Accept": "application/json", "Content-Type": "application/json"}


def _wd_jobs(tenant, hote, site, texte="", limite=20):
    """Reponse brute de la recherche Workday, ou None si le reseau echoue."""
    import httpx

    try:
        return httpx.post(
            f"https://{tenant}.{hote}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs",
            json={"appliedFacets": {}, "limit": limite, "offset": 0, "searchText": texte},
            timeout=15,
            headers=_WD_JSON,
        )
    except Exception:
        return None


def tenant_workday(tenant, hote):
    r = _wd_jobs(tenant, hote, "zz_site_inexistant", limite=1)
    return r is not None and r.status_code == 404 and "Job_Posting_Site_ID" in r.text


def _wd_vitrine(tenant, hote, site):
    """Texte que le site Workday montre de son employeur : le bandeau « About
    us » et le nom servi par sa premiere offre. "" si illisible."""
    import httpx

    base = f"https://{tenant}.{hote}.myworkdayjobs.com/wday/cxs/{tenant}/{site}"
    morceaux = []
    try:
        # Les TEXTES seuls : les adresses d'image (« /wday/cxs/erm/... »)
        # contiennent le tenant et confirmeraient n'importe quel site.
        for bloc in httpx.get(base + "/sidebar", timeout=15, headers=_WD_JSON).json() or []:
            morceaux += [str(bloc.get(k) or "") for k in ("title", "text", "altText")]
    except Exception:
        pass
    try:
        chemin = _wd_jobs(tenant, hote, site, limite=1).json()["jobPostings"][0]["externalPath"]
        d = httpx.get(base + chemin, timeout=15, headers=_WD_JSON).json()
        morceaux.append((d.get("hiringOrganization") or {}).get("name") or "")
    except Exception:
        pass
    return _sans_accent(re.sub(r"<[^>]+>", " ", " ".join(morceaux)))


def mots_du_tenant(entreprise, tenant):
    """Les mots du nom de l'entreprise dont le tenant est fait, ou [] :
    « lombardodier » -> [lombard, odier] pour « Lombard Odier »."""
    mots = [m for m in re.split(r"[^a-z0-9]+", _sans_accent(entreprise)) if m]
    cible = tenant.replace("-", "")
    for i in range(len(mots)):
        for j in range(i + 1, len(mots) + 1):
            if "".join(mots[i:j]) == cible:
                return mots[i:j]
    return []


def meme_employeur(entreprise, tenant, vitrine):
    """Le site Workday est-il celui de cette entreprise ? Le tenant vient deja
    de son nom ; on demande en plus que la vitrine le nomme EN MOTS ENTIERS.
    Pas `hiringOrganization` seul : il porte l'entite juridique, et Accenture
    y repond « 8140 ASOL - Gurugram Non STPI Company » (2026-10-07)."""
    mots = mots_du_tenant(entreprise, tenant)
    return (
        bool(mots)
        and re.search(r"\b" + r"\W+".join(map(re.escape, mots)) + r"\b", vitrine) is not None
    )


def flux_workday(entreprise):
    """[["workday", "tenant.hote/site"]] si l'entreprise publie sur Workday."""
    compact = re.sub(r"[^a-z0-9]", "", _sans_accent(entreprise))
    tenants = list(dict.fromkeys(([compact] if len(compact) >= 3 else []) + variantes(entreprise)))
    for t in tenants:
        for h in WD_HOTES:
            if not tenant_workday(t, h):
                continue
            # « Lombard_Odier_Careers » : les mots du nom, joints par « _ ».
            bases = list(
                dict.fromkeys([t, "_".join(m.capitalize() for m in mots_du_tenant(entreprise, t))])
            )
            for site in [b + s for b in bases if b for s in _WD_SUFFIXES] + _WD_GENERIQUES:
                r = _wd_jobs(t, h, site, limite=1)
                try:
                    ok = r is not None and r.status_code == 200 and (r.json() or {}).get("total")
                except Exception:
                    ok = False
                if not ok:
                    continue
                if ("workday", f"{t}.{h}/{site}") in FAUX_FLUX:
                    break
                if meme_employeur(entreprise, t, _wd_vitrine(t, h, site)):
                    return [["workday", f"{t}.{h}/{site}"]]
                break  # le site existe mais ne nomme pas l'entreprise
    return []


def lire_workday(slug, requete):
    """[(titre, url, lieu)] des offres du flux qui repondent a la requete."""
    tenant, reste = slug.split(".", 1)
    hote, site = reste.split("/", 1)
    r = _wd_jobs(tenant, hote, site, requete)
    if r is None or r.status_code != 200:
        return None
    base = f"https://{tenant}.{hote}.myworkdayjobs.com/{site}"
    return [
        (j.get("title", ""), base + j["externalPath"], j.get("locationsText", ""))
        for j in (r.json() or {}).get("jobPostings") or []
        if j.get("title") and j.get("externalPath")
    ]


def coquille(postes):
    """Flux de demonstration : un compte ATS ouvert puis laisse vide garde ses
    offres modeles. Mesure le 2026-10-07 : google.recruitee.com ne publie que
    « Senior Marketer (Sample) » — ce n'est pas Google, le nom etait libre.
    UNE offre modele suffit : accenture.recruitee.com en garde une a cote d'une
    « sales executive » saisie a la main ; une vraie entreprise supprime le modele."""
    return any("(sample)" in t.lower() for t, *_ in postes)


# Homonymes verifies a la main : le nom concorde, l'employeur non.
# ashby:hatch est une start-up americaine, pas Hatch l'ingenierie (2026-10-07).
# Sonde des cabinets du 2026-10-08 : lever:oliverwyman et ashby:andera sont des
# start-up de San Francisco ; workday simon = Simon Property Group (centres
# commerciaux), pas Simon-Kucher — le tenant ne prenait que le premier mot.
FAUX_FLUX = {
    ("ashby", "hatch"),
    ("lever", "oliverwyman"),
    ("ashby", "andera"),
    ("workday", "simon.wd1/simon"),
}


def flux_de(entreprise, connus):
    """Flux ATS CONFIRMES pour cette entreprise : [[kind, slug], ...]."""
    trouves = []
    connus = [(k, s) for k, s in connus if k != "workday"]  # traites par sonder()
    candidats = list(connus) or [(k, s) for s in variantes(entreprise) for k in probe_ats.APIS]
    for kind, slug in candidats:
        if (kind, slug) in FAUX_FLUX:
            continue
        if not connus and not probe_ats.probe(kind, slug):
            continue
        v, _ = verdict(entreprise, nom_du_flux(kind, slug))
        if v == "CONFIRME" and not coquille(lire_flux(kind, slug) or []):
            trouves.append([kind, slug])
    return trouves


def flux_connus():
    """Flux deja declares dans job_sources, indexes par nom de societe reduit."""
    from job_sources import ATS_SLUGS, WORKDAY_FLUX

    idx = {}
    for kind, slugs in ATS_SLUGS.items():
        for s in slugs:
            idx.setdefault(_cle(s), []).append((kind, s))
    for tenant, hote, site, nom in WORKDAY_FLUX:
        idx.setdefault(_cle(nom), []).append(("workday", f"{tenant}.{hote}/{site}"))
    return idx


def charger_etat():
    try:
        return json.loads(ETAT.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _age(date, jour):
    try:
        return (jour - datetime.date.fromisoformat(date)).days
    except Exception:
        return RESONDE_JOURS


def a_resonder(x, jour):
    """(ATS publics, Workday) : lesquels sonder pour cette entreprise ?
    Un flux trouve ne se resonde pas ; une absence, apres 30 jours."""
    if not x:
        return True, True
    fl = x.get("flux") or []
    ats = not any(k != "workday" for k, _ in fl) and _age(x.get("date"), jour) >= RESONDE_JOURS
    # `wd_date` absente : entree d'avant Workday (2026-10-07), jamais sondee.
    wd = not any(k == "workday" for k, _ in fl) and (
        "wd_date" not in x or _age(x["wd_date"], jour) >= RESONDE_JOURS
    )
    return ats, wd


def sonder(e, x, connus, jour):
    """Nouvelle entree d'etat pour l'entreprise `e`."""
    ats, wd = a_resonder(x, jour)
    x = dict(x or {})
    ancien = x.get("flux") or []
    fl_ats = (
        [f for f in flux_de(e, connus) if f[0] != "workday"]
        if ats
        else [f for f in ancien if f[0] != "workday"]
    )
    fl_wd = [f for f in ancien if f[0] == "workday"] or [
        ["workday", s] for k, s in connus if k == "workday"
    ]
    if wd and not fl_wd:
        fl_wd = flux_workday(e)
    if ats:
        x["date"] = jour.isoformat()
    if wd:
        x["wd_date"] = jour.isoformat()
    x.setdefault("date", jour.isoformat())
    x["flux"] = fl_ats + fl_wd
    return x


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fit", type=int, default=9)
    ap.add_argument("--limite", type=int, default=0, help="nombre max d'entreprises")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--dry", action="store_true", help="n'ecrit rien dans la file")
    a = ap.parse_args()

    q = queue_io.charger(descriptions=False)
    cibles = [
        o
        for o in q
        if "linkedin.com" in str(o.get("url") or "").lower()
        and (o.get("fit") or 0) >= a.fit
        and (o.get("entreprise") or "").strip()
    ]
    par_ent = {}
    for o in cibles:
        par_ent.setdefault(o["entreprise"].strip(), []).append(o)
    ents = sorted(par_ent, key=lambda e: -len(par_ent[e]))
    if a.limite:
        ents = ents[: a.limite]

    etat = charger_etat()
    jour = datetime.date.today()
    connus = flux_connus()

    # Un flux Workday ajoute a la main (job_sources.WORKDAY_FLUX) entre aussi
    # dans une entreprise deja sondee, sans attendre ses 30 jours.
    def _cure_manquant(e):
        fl = (etat.get(e) or {}).get("flux") or []
        return any(k == "workday" and [k, s] not in fl for k, s in connus.get(_cle(e), []))

    a_sonder = [e for e in ents if any(a_resonder(etat.get(e), jour)) or _cure_manquant(e)]
    print(
        f"{len(cibles)} offre(s) LinkedIn a fit >= {a.fit} · {len(ents)} entreprise(s) · "
        f"{len(a_sonder)} a sonder"
    )

    t0 = time.time()
    with cf.ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs = {
            ex.submit(sonder, e, etat.get(e), connus.get(_cle(e), []), jour): e for e in a_sonder
        }
        for n, f in enumerate(cf.as_completed(futs), 1):
            e = futs[f]
            try:
                etat[e] = f.result()
            except Exception:
                pass  # resonde au prochain passage
            if n % 25 == 0:
                # Ecrit en cours de route : le pipeline peut couper l'etape.
                ETAT.write_text(json.dumps(etat, ensure_ascii=False, indent=1), encoding="utf-8")
                print(f"  … {n}/{len(a_sonder)} sondees ({time.time() - t0:.0f} s)")
    ETAT.write_text(json.dumps(etat, ensure_ascii=False, indent=1), encoding="utf-8")

    # Recherche des intitules dans les flux confirmes.
    trouvees, absentes = {}, {}
    avec_flux = [e for e in ents if (etat.get(e) or {}).get("flux")]
    for e in avec_flux:
        cache = {}
        for o in par_ent[e]:
            for kind, slug in etat[e]["flux"]:
                # Ces deux API cherchent cote serveur : la liste complete est
                # tronquee (SmartRecruiters 100, Workday 20 par page).
                cherche = kind in ("smartrecruiters", "workday")
                cle = (kind, slug, o["poste"] if cherche else "")
                if cle not in cache:
                    cache[cle] = (
                        lire_flux(kind, slug, titre_cle(o["poste"]) if cherche else "") or []
                    )
                hit = next((x for x in cache[cle] if meme_titre(o["poste"], x[0])), None)
                if hit:
                    trouvees[queue_io.oid(o)] = (hit[1], f"{kind}:{slug}")
                    break
            else:
                absentes[queue_io.oid(o)] = "absente du flux"

    print(f"\n{len(avec_flux)} entreprise(s) avec un flux ATS confirme sur {len(ents)}")
    print(f"  {len(trouvees)} offre(s) retrouvee(s) sur le site final")
    print(f"  {len(absentes)} absente(s) du flux (notees, pas retirees)")
    for e in avec_flux[:30]:
        print(f"    {e[:34]:34} {etat[e]['flux']}")
    for oid, (u, src) in list(trouvees.items())[:20]:
        print(f"  ✓ {oid[:70]}\n      -> {u}")

    if a.dry:
        print("\n[DRY] file non modifiee.")
        return 0
    try:
        with queue_io.transaction(descriptions=False) as file_:
            for o in file_:
                k = queue_io.oid(o)
                if k in trouvees and "linkedin.com" in str(o.get("url") or "").lower():
                    u, src = trouvees[k]
                    o["url_linkedin"] = o["url"]
                    o["url"], o["source"] = u, src
                    o["canal"], o["site_kind"], o["link_status"] = "auto", "entreprise", "OK"
                    o["site_final"] = f"retrouvee {jour.isoformat()}"
                elif k in absentes:
                    o["site_final"] = f"{absentes[k]} {jour.isoformat()}"
    except queue_io.VerrouIndisponible as e:
        print(f"! {e}")
        return 3
    print(f"\nFile mise a jour : {len(trouvees)} lien(s) remplace(s) par le site final.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
