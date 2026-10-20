"""The collection's command line (python Scripts/job_sources.py ...).

Part of jobhunter.sources (formerly Scripts/job_sources.py, phase 3.4).
"""

import argparse
import importlib
import json
import sys
from typing import Any

from jobhunter import lazy as _paresseux
from jobhunter import root as _racine
from jobhunter.sources import common as _commun
from jobhunter.sources import source_yield as _rendement
from jobhunter.sources.aggregators import scan_adzuna, scan_jooble
from jobhunter.sources.apec import scan_apec
from jobhunter.sources.ats import scan_ats
from jobhunter.sources.common import FRESH, INCIDENTS, _load_cfg, incidents_resume
from jobhunter.sources.efc import EFC_SITES, scan_efc
from jobhunter.sources.eures import scan_eures
from jobhunter.sources.fir import scan_fir
from jobhunter.sources.francetravail import scan_france_travail
from jobhunter.sources.glassdoor import scan_glassdoor
from jobhunter.sources.indeed import scan_indeed
from jobhunter.sources.linkedin import scan_linkedin
from jobhunter.sources.merge import merge_into_queue
from jobhunter.sources.talent import scan_talent
from jobhunter.sources.vie import scan_vie
from jobhunter.sources.workday import scan_workday
from jobhunter.sources.wtj import scan_wtj
from jobhunter.text import cle as _norm

_ici = sys.modules[__name__]
# Values taken from the profile: computed on first read, not at import
# (jobhunter.lazy). In this module, they are read through `_ici.NAME`.
_PARESSEUX: _paresseux.Fabriques = {}


def __getattr__(nom: str) -> Any:
    return _paresseux.lire(_ici, _PARESSEUX, nom)


_PARESSEUX["INDEED_LIEUX"] = lambda: (
    importlib.import_module("jobhunter.sources.indeed").INDEED_LIEUX
)


def main() -> int:
    """The collection's command line: chosen sources, deduplication, merge.

    Returns:
        0, 3 if the queue is locked by another program, 4 if Indeed was throttled.
    """
    _load_cfg()  # sources edited from the app
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--ats", action="store_true")
    ap.add_argument(
        "--workday",
        action="store_true",
        help="flux Workday publics (Eiffage, Ardian, Lombard Odier)",
    )
    ap.add_argument("--linkedin", action="store_true")
    ap.add_argument("--wtj", action="store_true")
    ap.add_argument("--vie", action="store_true")
    ap.add_argument("--fir", action="store_true")
    ap.add_argument("--talent", action="store_true")
    ap.add_argument(
        "--indeed",
        action="store_true",
        help="Indeed : page 1 des resultats (15 offres par requete)",
    )
    ap.add_argument(
        "--indeed-lieux",
        default=",".join(_ici.INDEED_LIEUX),
        help="villes Indeed, separees par des virgules",
    )
    ap.add_argument(
        "--glassdoor",
        action="store_true",
        help="Glassdoor : page 1 de la recherche (30 offres par mot-cle) ; hors --all",
    )
    ap.add_argument(
        "--apec",
        action="store_true",
        help="APEC : API publique, description entiere dans la liste ; hors --all",
    )
    ap.add_argument("--ft", action="store_true", help="France Travail (API officielle)")
    ap.add_argument(
        "--adzuna",
        action="store_true",
        help="Adzuna (API officielle, cle dans Scripts/adzuna.json)",
    )
    ap.add_argument(
        "--jooble",
        action="store_true",
        help="Jooble (API officielle, cle dans Scripts/jooble.json)",
    )
    ap.add_argument(
        "--efc", action="store_true", help="eFinancialCareers (sitemap public, crawl-delay 10 s)"
    )
    ap.add_argument(
        "--efc-graduate", action="store_true", help="eFC : programmes jeunes diplomes et V.I.E"
    )
    ap.add_argument(
        "--efc-tout", action="store_true", help="eFC sans le filtre ESG : ~2400 titres, tres long"
    )
    ap.add_argument(
        "--efc-metier",
        action="store_true",
        help="eFC : intitules compatibles avec le profil (869 sur 8478)",
    )
    ap.add_argument(
        "--efc-sites",
        default="fr",
        help="sites eFC a lire : fr, com, co.uk, de, ch, nl, lu, ie, sg "
        "(separes par des virgules) ou « monde » pour les neuf",
    )
    ap.add_argument(
        "--eures",
        action="store_true",
        help="EURES, portail officiel de l'UE (API publique, crawl-delay 10 s)",
    )
    ap.add_argument(
        "--efc-limite",
        type=int,
        default=40,
        help="nombre de fiches eFC lues par passe (10 s chacune)",
    )
    ap.add_argument("--pages", type=int, default=2)
    ap.add_argument(
        "--days", type=int, default=7, help="fraicheur LinkedIn en jours (31 = rattraper un mois)"
    )
    ap.add_argument("--dry", action="store_true")
    ap.add_argument(
        "--monde",
        action="store_true",
        help="sans effet, c'est le defaut (garde pour compatibilite)",
    )
    ap.add_argument(
        "--france",
        action="store_true",
        help="ne garder QUE les offres en France (annule le defaut mondial)",
    )
    ap.add_argument(
        "--fusion-seule",
        action="store_true",
        help="refusionne le dernier scan (offres_scan.json) sans rien collecter",
    )
    a = ap.parse_args()
    _rendement.MESURES.clear()  # one measurement per collection, even if called several times

    # TWO LOCKS, TWO ROLES. There used to be only one, on the QUEUE, taken at
    # start-up and kept for the whole collection — more than an hour with --all. On the
    # evening of 2026-09-22, the scheduled scan thus blocked an already verified
    # purge for its whole duration, while it only writes into the queue at the
    # very end. This lock actually played two roles:
    #
    #   1. protect the queue — that is the job of merge_into_queue, which takes
    #      the lock itself and re-reads the queue INSIDE it. A few seconds.
    #   2. prevent two scans in parallel — they would share the sources' quota
    #      and overwrite each other's offres_scan.json.
    #
    # Role 2 moves to a separate lock, set on offres_scan.json. The queue
    # stays free during the collection.
    #
    # AFTER argparse, and not before: `--help` and `--dry`, which write nothing,
    # must block nothing.
    from jobhunter.storage import lock as verrou

    if not a.dry and not verrou.garder(FRESH):
        return 3

    if a.fusion_seule:
        return _fusionner(json.loads(FRESH.read_text(encoding="utf-8")), a.dry)
    if a.france:
        _commun.MONDE = False
        print("── recherche restreinte à la FRANCE ──")
    # --efc and --efc-tout count as a requested source. Without them in
    # this list, `--efc` alone fell back on a.all = True and started the WHOLE
    # daily scan again before reaching eFC.
    if not (
        a.all
        or a.ats
        or a.workday
        or a.linkedin
        or a.wtj
        or a.vie
        or a.fir
        or a.talent
        or a.ft
        or a.efc
        or a.efc_tout
        or a.efc_graduate
        or a.efc_metier
        or a.indeed
        or a.glassdoor
        or a.apec
        or a.eures
        or a.adzuna
        or a.jooble
    ):
        a.all = True

    fresh = []
    if a.all or a.ats:
        print("── ATS APIs (greenhouse/lever/ashby/recruitee/smartrecruiters) ──")
        fresh += _rendement.mesurer("ats", scan_ats)
    if a.all or a.workday:
        print("── Workday (API publique des grands groupes) ──")
        fresh += _rendement.mesurer("workday", scan_workday)
    if a.all or a.linkedin:
        print("── LinkedIn recherche publique (guest) ──")
        fresh += _rendement.mesurer("linkedin", scan_linkedin, pages=a.pages, days=a.days)
    if a.all or a.vie:
        print("── V.I.E / V.I.A (Business France) ──")
        fresh += _rendement.mesurer("vie", scan_vie)
    if a.all or a.fir:
        print("── FIR / French SIF (100 % ISR-ESG) ──")
        fresh += _rendement.mesurer("fir", scan_fir)
    # TALENT AND INDEED OUT OF --all (2026-10-03). Talent: 0 offers in 30 min on
    # 30/09, 3 on 27/09. Indeed: 403 at the first request since 24/09.
    # They can still be run by hand (--talent, --indeed) to check whether they
    # come back; Adzuna and Jooble cover the same pool through an API.
    if a.talent:
        print("── Talent.com (agrégateur) ──")
        fresh += _rendement.mesurer("talent", scan_talent)
    if a.indeed:
        print("── Indeed (page 1 des résultats — voir le commentaire de scan_indeed) ──")
        fresh += _rendement.mesurer(
            "indeed",
            scan_indeed,
            lieux=[v.strip() for v in a.indeed_lieux.split(",") if v.strip()],
            persist=not a.dry,
        )
    # APEC (DataDome) and Glassdoor (Cloudflare challenge) out of --all since 3.10.0:
    # every collection measured since 07/10 was refused (403 behind a CAPTCHA page,
    # checked again on 21/10). We do not get around it; their flag still runs them.
    if a.apec:
        print("── APEC (API publique, annonce entière dans la liste) ──")
        fresh += _rendement.mesurer("apec", scan_apec)
    if a.glassdoor:
        print("── Glassdoor (page 1 de la recherche, France entière) ──")
        fresh += _rendement.mesurer("glassdoor", scan_glassdoor)
    # eFC in --all, but BOUNDED: ESG filter, the nine sites, 30 postings at
    # most (the postings already in the queue are skipped, so each day moves forward in
    # the rest). Nine sitemaps + 30 postings at 10 s make ~6 min. The wide
    # filters (--efc-metier, --efc-tout) are still run separately, in passes.
    if a.all or a.efc or a.efc_tout or a.efc_graduate or a.efc_metier:
        filtre = (
            "tout"
            if a.efc_tout
            else "graduate"
            if a.efc_graduate
            else "metier"
            if a.efc_metier
            else "esg"
        )
        sites = (
            EFC_SITES
            if (a.all and not a.efc) or a.efc_sites == "monde"
            else tuple(x.strip() for x in a.efc_sites.split(",") if x.strip())
        )
        limite = 30 if (a.all and not a.efc) else a.efc_limite
        print(
            f"── eFinancialCareers ({filtre}, {len(sites)} site(s), sitemap public, crawl-delay 10 s) ──"
        )
        fresh += _rendement.mesurer("efc", scan_efc, limit=limite, filtre=filtre, sites=sites)
    if a.all or a.eures:
        print("── EURES (portail officiel UE, API publique, crawl-delay 10 s) ──")
        fresh += _rendement.mesurer("eures", scan_eures)
    if a.all or a.ft:
        print("── France Travail (API officielle) ──")
        fresh += _rendement.mesurer("francetravail", scan_france_travail)
    if a.all or a.adzuna:
        print("── Adzuna (API officielle, France + 7 pays) ──")
        fresh += _rendement.mesurer("adzuna", scan_adzuna)
    if a.all or a.jooble:
        print("── Jooble (API officielle) ──")
        fresh += _rendement.mesurer("jooble", scan_jooble)
    if a.all or a.wtj:
        print("── Welcome to the Jungle (sitemap public, débit bridé) ──")
        fresh += _rendement.mesurer("wtj", scan_wtj, pages=a.pages)

    uniq = dedoublonner(fresh)
    # --dry writes NOTHING, not even the scan: it does not hold the lock of
    # offres_scan.json, and overwriting it while a real scan held it ruined
    # the latter's `--fusion-seule`. Seen on 2026-09-23 on an --apec --dry.
    if not a.dry:
        FRESH.write_text(json.dumps(uniq, ensure_ascii=False, indent=1), encoding="utf-8")
    print(
        f"\nScan : {len(uniq)} offres uniques"
        + (" (non ecrit : --dry)" if a.dry else f" (→ {FRESH.name})")
    )

    # THE REFUSALS, BEFORE THE SUMMARY. Without that, a scan throttled from start to end
    # shows the same "0 offres" as a day with nothing new, and it is run again — which
    # is exactly what must not be done against a quota.
    refus = incidents_resume()
    if refus:
        print("\nRefus rencontrés (une collecte vide peut venir de là) :")
        for l in refus:
            print(l)

    code = _fusionner(uniq, a.dry)
    # The merge stays the priority; a degraded Indeed source is not a success.
    return code or (4 if a.indeed and INCIDENTS.get("indeed") else 0)


# The zones, from the best to the worst for the profile.
_ORDRE_ZONES = ("prioritaire", "secondaire", "ailleurs", "international", "inconnu")


def dedoublonner(fresh: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One offer per "entreprise|poste" in the scan, the most useful city kept.

    The SAME job published in several cities shares the same key: a single copy gets
    into the queue. Measured on 2026-10-19 on real replayed responses: 12 offers out
    of 86 (Forvis Mazars in Düsseldorf, Mannheim, Hamburg, Frankfurt…). We kept the
    FIRST one seen, by chance of the order; we now keep the one in the profile's best
    zone (priority, then secondary, then the rest of France), and the other cities go
    into `autres_lieux`, which the card displays. On a tie, the first one seen wins,
    as before.

    Args:
        fresh: the offers of all the collection's sources.

    Returns:
        The unique offers, in the order of first appearance of their key.
    """
    from jobhunter.scoring import zones as _zones

    def rang(o: dict[str, Any]) -> int:
        z = _zones.zone_lieu(o.get("location") or "")
        return -_ORDRE_ZONES.index(z) if z in _ORDRE_ZONES else -len(_ORDRE_ZONES)

    groupes: dict[str, list[dict[str, Any]]] = {}
    for o in fresh:
        groupes.setdefault(_norm(o["entreprise"]) + "|" + _norm(o["titre"]), []).append(o)
    uniq = []
    for lot in groupes.values():
        meilleur = max(lot, key=rang)  # max keeps the FIRST of the ties
        autres = sorted(
            {
                str(x.get("location"))
                for x in lot
                if x is not meilleur
                and x.get("location")
                and _norm(str(x.get("location"))) != _norm(str(meilleur.get("location") or ""))
            }
        )
        if autres:
            meilleur["autres_lieux"] = autres
        uniq.append(meilleur)
    return uniq


def _fusionner(uniq: Any, dry: bool) -> int:
    """Merges the scan into the queue. Returns an exit code.

    The queue lock is ONLY taken HERE. If another program holds it, we wait up to 30
    minutes: what came before cost an hour of network, and giving up after 3 minutes,
    as by default, would throw it away. If the wait still fails, nothing is lost —
    the scan is already in offres_scan.json, and `--fusion-seule` merges it again
    without collecting anything.
    """
    from jobhunter.storage import queue as queue_io

    try:
        r = merge_into_queue(uniq, dry=dry, attente=1800)
    except queue_io.VerrouIndisponible as e:
        print(f"! {e}")
        print(
            f"  Le scan est conserve dans {FRESH.name} : "
            f"`jobhunter collect --fusion-seule` le fusionnera."
        )
        return 3
    # YIELD PER SOURCE: what each one brought back, and why not more.
    _rendement.completer(uniq, r.get("par_source") or {})
    if _rendement.MESURES:
        print("\nRendement par source :")
        for ligne in _rendement.resume():
            print(ligne)
        if not dry:
            try:
                _rendement.enregistrer(_racine.dans(_commun.HERE, "_rendement.jsonl"))
            except OSError as e:
                print(f"  ! journal de rendement non écrit : {e}")
    if not dry:
        # Per company: last attempt, last success, incident (sources.feeds).
        from jobhunter.sources import feeds as _flux

        try:
            _flux.enregistrer(_racine.dans(_commun.HERE, _flux.FICHIER))
        except OSError as e:
            print(f"  ! état des entreprises non écrit : {e}")
    print(
        f"Merge {'[DRY] ' if dry else ''}: +{r['added']} nouvelles, {r['updated']} enrichies (desc), "
        f"{r['promus']} liens promus (LinkedIn -> vrai site), "
        f"{r['hors_zone']} hors de France, "
        f"{r['ecartees']} écartées à la main, {r.get('rejetees_tri', 0)} déjà rejetées par le tri, "
        f"{r['pays_ecartes']} pays écartés, "
        f"{r['purged']} bruits purgés — {r['total']} total"
    )
    _rendement.progres(f"bilan {r['added']} nouvelles")
    if r.get("modifiees"):
        print(
            f"  {r['modifiees']} offre(s) modifiée(s) par leur site (titre, salaire, contrat, lieu)"
        )
    if r["added"] and not dry:
        print("→ re-score + descriptions manquantes : automatiques au prochain lancement de l'app.")
    return 0
