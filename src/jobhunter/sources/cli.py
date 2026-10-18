"""La ligne de commande de la collecte (python Scripts/job_sources.py ...).

Partie de jobhunter.sources (ancien Scripts/job_sources.py, phase 3.4)."""

import argparse
import importlib
import json
import sys
from typing import Any

from jobhunter import paresseux as _paresseux
from jobhunter.sources import commun as _commun
from jobhunter.sources.agregateurs import scan_adzuna, scan_jooble
from jobhunter.sources.apec import scan_apec
from jobhunter.sources.ats import scan_ats
from jobhunter.sources.commun import FRESH, INCIDENTS, _load_cfg, incidents_resume
from jobhunter.sources.efc import EFC_SITES, scan_efc
from jobhunter.sources.eures import scan_eures
from jobhunter.sources.fir import scan_fir
from jobhunter.sources.francetravail import scan_france_travail
from jobhunter.sources.fusion import merge_into_queue
from jobhunter.sources.glassdoor import scan_glassdoor
from jobhunter.sources.indeed import scan_indeed
from jobhunter.sources.linkedin import scan_linkedin
from jobhunter.sources.talent import scan_talent
from jobhunter.sources.vie import scan_vie
from jobhunter.sources.workday import scan_workday
from jobhunter.sources.wtj import scan_wtj
from jobhunter.texte import cle as _norm

_ici = sys.modules[__name__]
# Valeurs tirees du profil : calculees a la premiere lecture, pas a l'import
# (jobhunter.paresseux). Dans ce module, on les lit par `_ici.NOM`.
_PARESSEUX: _paresseux.Fabriques = {}


def __getattr__(nom: str) -> Any:
    return _paresseux.lire(_ici, _PARESSEUX, nom)


_PARESSEUX["INDEED_LIEUX"] = lambda: (
    importlib.import_module("jobhunter.sources.indeed").INDEED_LIEUX
)


def main():
    _load_cfg()  # sources éditées depuis l'app
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
        help="Glassdoor : page 1 de la recherche (30 offres par mot-cle)",
    )
    ap.add_argument(
        "--apec", action="store_true", help="APEC : API publique, description entiere dans la liste"
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

    # DEUX VERROUS, DEUX ROLES. Il n'y en avait qu'un, sur la FILE, pris au
    # demarrage et garde toute la collecte — plus d'une heure en --all. Le
    # 2026-09-22 au soir, le scan planifie a ainsi bloque une purge deja
    # verifiee pendant toute sa duree, alors qu'il n'ecrit dans la file qu'a la
    # toute fin. Ce verrou jouait en fait deux roles :
    #
    #   1. proteger la file — c'est le travail de merge_into_queue, qui prend
    #      lui-meme le verrou et relit la file A L'INTERIEUR. Quelques secondes.
    #   2. empecher deux scans en parallele — ils se partageraient le quota des
    #      sources et s'ecraseraient mutuellement offres_scan.json.
    #
    # Le role 2 passe sur un verrou a part, pose sur offres_scan.json. La file
    # reste libre pendant la collecte.
    #
    # APRES argparse, et pas avant : `--help` et `--dry`, qui n'ecrivent rien,
    # ne doivent rien bloquer.
    from jobhunter.stockage import verrou

    if not a.dry and not verrou.garder(FRESH):
        return 3

    if a.fusion_seule:
        return _fusionner(json.loads(FRESH.read_text(encoding="utf-8")), a.dry)
    if a.france:
        _commun.MONDE = False
        print("── recherche restreinte à la FRANCE ──")
    # --efc et --efc-tout comptent comme une source demandee. Sans eux dans
    # cette liste, `--efc` seul retombait sur a.all = True et relancait TOUT le
    # scan quotidien avant d'arriver a eFC.
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
        fresh += scan_ats()
    if a.all or a.workday:
        print("── Workday (API publique des grands groupes) ──")
        fresh += scan_workday()
    if a.all or a.linkedin:
        print("── LinkedIn recherche publique (guest) ──")
        fresh += scan_linkedin(pages=a.pages, days=a.days)
    if a.all or a.vie:
        print("── V.I.E / V.I.A (Business France) ──")
        fresh += scan_vie()
    if a.all or a.fir:
        print("── FIR / French SIF (100 % ISR-ESG) ──")
        fresh += scan_fir()
    # TALENT ET INDEED HORS DE --all (2026-10-03). Talent : 0 offre en 30 min le
    # 30/09, 3 le 27/09. Indeed : 403 a la premiere requete depuis le 24/09.
    # Ils restent lancables a la main (--talent, --indeed) pour verifier s'ils
    # reviennent ; Adzuna et Jooble couvrent le meme vivier par une API.
    if a.talent:
        print("── Talent.com (agrégateur) ──")
        fresh += scan_talent()
    if a.indeed:
        print("── Indeed (page 1 des résultats — voir le commentaire de scan_indeed) ──")
        fresh += scan_indeed(
            lieux=[v.strip() for v in a.indeed_lieux.split(",") if v.strip()], persist=not a.dry
        )
    if a.all or a.apec:
        print("── APEC (API publique, annonce entière dans la liste) ──")
        fresh += scan_apec()
    if a.all or a.glassdoor:
        print("── Glassdoor (page 1 de la recherche, France entière) ──")
        fresh += scan_glassdoor()
    # eFC dans --all, mais BORNE : filtre ESG, les neuf sites, 30 fiches au
    # plus (les fiches deja en file sont sautees, donc chaque jour avance dans
    # le reste). Neuf sitemaps + 30 fiches a 10 s font ~6 min. Les filtres
    # larges (--efc-metier, --efc-tout) restent a lancer a part, par passes.
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
        fresh += scan_efc(limit=limite, filtre=filtre, sites=sites)
    if a.all or a.eures:
        print("── EURES (portail officiel UE, API publique, crawl-delay 10 s) ──")
        fresh += scan_eures()
    if a.all or a.ft:
        print("── France Travail (API officielle) ──")
        fresh += scan_france_travail()
    if a.all or a.adzuna:
        print("── Adzuna (API officielle, France + 7 pays) ──")
        fresh += scan_adzuna()
    if a.all or a.jooble:
        print("── Jooble (API officielle) ──")
        fresh += scan_jooble()
    if a.all or a.wtj:
        print("── Welcome to the Jungle (sitemap public, débit bridé) ──")
        fresh += scan_wtj(pages=a.pages)

    # dédup interne du scan
    seen, uniq = set(), []
    for o in fresh:
        k = _norm(o["entreprise"]) + "|" + _norm(o["titre"])
        if k in seen:
            continue
        seen.add(k)
        uniq.append(o)
    # --dry n'ecrit RIEN, pas meme le scan : il ne tient pas le verrou de
    # offres_scan.json, et l'ecraser pendant qu'un vrai scan le detient ruinait
    # le `--fusion-seule` de ce dernier. Vu le 2026-09-23 sur un --apec --dry.
    if not a.dry:
        FRESH.write_text(json.dumps(uniq, ensure_ascii=False, indent=1), encoding="utf-8")
    print(
        f"\nScan : {len(uniq)} offres uniques"
        + (" (non ecrit : --dry)" if a.dry else f" (→ {FRESH.name})")
    )

    # LES REFUS, AVANT LE BILAN. Sans ca, un scan bride de bout en bout affiche
    # le meme « 0 offres » qu'une journee sans nouveaute, et on relance — ce qui
    # est exactement ce qu'il ne faut pas faire face a un quota.
    refus = incidents_resume()
    if refus:
        print("\nRefus rencontrés (une collecte vide peut venir de là) :")
        for l in refus:
            print(l)

    code = _fusionner(uniq, a.dry)
    # La fusion reste prioritaire ; une source Indeed dégradée n'est pas un succès.
    return code or (4 if a.indeed and INCIDENTS.get("indeed") else 0)


def _fusionner(uniq, dry):
    """Fusionne le scan dans la file. Rend un code de sortie.

    Le verrou de la file n'est pris QU'ICI. Si un autre programme l'occupe, on
    attend jusqu'a 30 minutes : ce qui precede a coute une heure de reseau, et
    abandonner au bout de 3 minutes, comme par defaut, le jetterait. Si
    l'attente echoue quand meme, rien n'est perdu — le scan est deja dans
    offres_scan.json, et `--fusion-seule` le refusionne sans rien recollecter."""
    from jobhunter.stockage import file as queue_io

    try:
        r = merge_into_queue(uniq, dry=dry, attente=1800)
    except queue_io.VerrouIndisponible as e:
        print(f"! {e}")
        print(
            f"  Le scan est conserve dans {FRESH.name} : "
            f"`python job_sources.py --fusion-seule` le fusionnera."
        )
        return 3
    print(
        f"Merge {'[DRY] ' if dry else ''}: +{r['added']} nouvelles, {r['updated']} enrichies (desc), "
        f"{r['promus']} liens promus (LinkedIn -> vrai site), "
        f"{r['hors_zone']} hors de France, "
        f"{r['ecartees']} écartées à la main, {r.get('rejetees_tri', 0)} déjà rejetées par le tri, "
        f"{r['pays_ecartes']} pays écartés, "
        f"{r['purged']} bruits purgés — {r['total']} total"
    )
    if r["added"] and not dry:
        print("→ re-score + descriptions manquantes : automatiques au prochain lancement de l'app.")
    return 0
