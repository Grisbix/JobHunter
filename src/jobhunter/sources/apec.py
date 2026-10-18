"""APEC.

Partie de jobhunter.sources (ancien Scripts/job_sources.py, phase 3.4)."""

import json
import time

from jobhunter import journal as _journal
from jobhunter.sources import commun as _commun
from jobhunter.sources.commun import (
    INCIDENTS,
    UA,
    _lire_borne,
    _mk,
    _strip_html,
    contrat_de_la_description,
    contrat_du_titre,
    title_ok,
)

_log = _journal.journal(__name__)


# ═══════════════ APEC — le remplacant d'Indeed ═══════════════
#
# POURQUOI. Indeed a rendu 0 offre le 17/09 : 184 requetes en un apres-midi ont
# epuise la tolerance, et douze sondes etalees sur cinq heures n'ont pas obtenu
# une seule reponse. Il fallait une source qui couvre le meme besoin — le
# marche francais large, avec contrat, date de parution et salaire.
#
# L'APEC est le site d'emploi des CADRES en France, et c'est la route la plus
# propre rencontree dans ce projet :
#
#   robots.txt        309 octets, AUCUN Disallow pour « User-agent: * »
#   sitemap declare   sitemap_offres_search_engine.xml.gz, dedie aux offres
#   API               cms/webservices/rechercheOffre, sans cle ni compte
#
# CE QU'ELLE DONNE, EXACTEMENT. Une requete rend 50 offres d'un coup, chacune
# avec un extrait de 283 caracteres — mesure : min 283, median 283, max 283,
# c'est une troncature nette. Plus long que les 160 d'Indeed et les 159 de
# Glassdoor, mais ce n'est PAS l'annonce entiere : j'avais ecrit le contraire
# ici avant de mesurer.
#
# La fiche complete n'est pas accessible : l'API de detail
# (cms/webservices/offre/...) repond 401, et la page HTML est une coquille
# Angular de 53 ko sans une ligne de l'annonce, ni ld+json. On s'arrete donc a
# l'extrait — le lien, lui, s'ouvre normalement dans le navigateur de l'utilisateur.
#
# En revanche, et c'est ce qui la rend precieuse : la date de publication est
# horodatee, le salaire est en clair (« A partir de 50 k€ brut annuel », 23 sur
# 23 renseignes a la mesure), et `indicateurFaibleCandidature` signale les
# offres peu concurrencees — personne d'autre ne publie cela.
#
# Le sitemap, lui, ne liste que 1288 URL de RECHERCHE par fonction et secteur,
# pas les offres. C'est l'API qui sert, et le sitemap qui atteste qu'elle est
# faite pour etre lue.
APEC_API = "https://www.apec.fr/cms/webservices/rechercheOffre"

APEC_FICHE = "https://www.apec.fr/candidat/recherche-emploi.html/emploi/detail-offre/"

APEC_PAUSE = 2  # aucun crawl-delay annonce ; on reste courtois

APEC_PAR_PAGE = 50

# LES CODES DE CONTRAT, ETABLIS PAR RECOUPEMENT — pas devines. L'API rend un
# identifiant de referentiel sans libelle. On a donc croise le code avec les
# titres qui nomment le contrat en clair, sur sept requetes :
#
#   101888   303 offres, 3 titres explicites, TOUS « CDI »
#   101887    30 offres, 6 titres explicites, TOUS « CDD »
#   597137     2 offres, 2 titres explicites, TOUS « Alternance »
#   101889    21 offres, AUCUN titre explicite  -> non mappe
#
# Aucun code ne se partage entre deux contrats. Les codes sans preuve restent
# dehors : mieux vaut « non precise » qu'une colonne fausse — c'est elle qui
# sert a filtrer, et quatre stages du Credit Agricole etiquetes CDD avaient
# deja remonte en tete du classement.
#
# Ce mapping n'intervient qu'en DERNIER RECOURS : un titre qui dit « CDD 8
# mois » l'emporte toujours sur le code.
_APEC_CONTRAT = {101888: "CDI", 101887: "CDD", 597137: "Alternance"}

# REFUS D'AFFILEE AU-DELA DESQUELS ON ARRETE. L'APEC est derriere DataDome : le
# 2026-10-02 au soir, apres ~540 requetes d'un audit de liens, ses 55 recherches
# ont toutes rendu 403. Insister sur les 52 suivantes ne rapporte rien et
# prolonge la mise a l'ecart. Trois refus d'affilee : la source est fermee
# pour aujourd'hui.
APEC_ABANDON = 3


def _apec_page(mot, debut):
    """Une page de resultats APEC. Liste vide en cas de refus."""
    import urllib.error
    import urllib.request

    corps = json.dumps(
        {
            "motsCles": mot,
            "pagination": {"range": APEC_PAR_PAGE, "startIndex": debut},
            "sorts": [{"type": "DATE", "direction": "DESCENDING"}],
            "activeFiltre": True,
        }
    ).encode("utf-8")
    tetes = dict(UA)
    tetes["Content-Type"] = "application/json"
    tetes["Accept"] = "application/json"
    try:
        r = urllib.request.Request(APEC_API, data=corps, headers=tetes, method="POST")
        with urllib.request.urlopen(r, timeout=30) as f:
            d = json.loads(_lire_borne(f).decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        _log.info(f"    ! {mot} : HTTP {e.code}")
        INCIDENTS["apec"][f"HTTP {e.code}"] += 1
        return None, 0
    except Exception as e:
        _log.info(f"    ! {mot} : {type(e).__name__}")
        return [], 0
    return d.get("resultats") or [], d.get("totalCount") or 0


def scan_apec(mots=None, pages=2):
    """Offres APEC : titre, societe, lieu, date, salaire, extrait de 283 car.

    `pages` : pages de 50 par mot-cle. Une page coute UNE requete, d'ou le
    meilleur rendement de toutes nos sources — mais l'extrait reste un extrait,
    et les offres partent avec `desc_partielle` pour que la promotion d'URL ne
    remplace jamais une annonce complete par ces 283 caracteres.
    """
    mots = mots or _commun.KEYWORDS
    _EX = _commun.contrats_exclus()
    offers, vus = [], set()
    _log.info(
        f"  APEC : {len(mots)} mots-cles x {pages} page(s) de {APEC_PAR_PAGE} "
        f"({APEC_PAUSE} s entre chaque)"
    )
    fait = refus = 0
    for mot in mots:
        if refus >= APEC_ABANDON:
            _log.warning(
                f"  ⏸ APEC : {refus} refus d'affilee — source fermee pour aujourd'hui, "
                f"pas d'insistance"
            )
            break
        for p in range(pages):
            if fait:
                time.sleep(APEC_PAUSE)
            fait += 1
            res, total = _apec_page(mot, p * APEC_PAR_PAGE)
            if res is None:
                refus += 1
                break
            refus = 0
            if not res:
                break
            for o in res:
                num = o.get("numeroOffre") or o.get("id")
                if not num or num in vus:
                    continue
                vus.add(num)
                titre = (o.get("intitule") or "").strip()
                if not titre or not title_ok(titre):
                    continue
                desc = _strip_html(o.get("texteOffre") or "")
                # Le titre d'abord, puis l'extrait, puis le code de l'APEC.
                # Dans cet ordre : un titre qui dit « CDD 8 mois » est plus sur
                # qu'un identifiant de referentiel, et 283 caracteres ne
                # suffisent pas a trancher — 583 offres sur 654 sortaient en
                # « non precise » avant que le code ne soit exploite.
                ctr = (
                    contrat_du_titre(titre)
                    or contrat_de_la_description(desc, "")
                    or _APEC_CONTRAT.get(o.get("typeContrat"), "")
                )
                if ctr in _EX:
                    continue
                x = _mk(
                    titre,
                    APEC_FICHE + str(num),
                    (o.get("nomCommercial") or "APEC").strip(),
                    o.get("lieuTexte") or "",
                    str(o.get("datePublication") or "")[:10],
                    "apec",
                    desc,
                )
                x["contrat"] = ctr
                x["salaire"] = (o.get("salaireTexte") or "").strip()
                # 283 caracteres ne sont pas une annonce : sans ce drapeau, la
                # promotion d'URL remplacerait une description complete par cet
                # extrait. Meme garde que pour Indeed et Glassdoor.
                x["desc_partielle"] = True
                # Peu de candidats : l'APEC est seule a le publier, et c'est
                # exactement ce qui fait la difference sur une candidature.
                if o.get("indicateurFaibleCandidature"):
                    x["peu_de_candidats"] = True
                offers.append(x)
            if len(res) < APEC_PAR_PAGE:
                break
    rares = sum(1 for x in offers if x.get("peu_de_candidats"))
    _log.info(
        f"  ✓ APEC → {len(offers)} offres sur {fait} requetes "
        f"(extrait de 283 car., {rares} a faible candidature)"
    )
    return offers
