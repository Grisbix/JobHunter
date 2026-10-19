"""Fusion de la collecte dans apply_queue.json : dedoublonnage, promotion d'URL, scoring.

Partie de jobhunter.sources (ancien Scripts/job_sources.py, phase 3.4).
"""

import importlib
import time
from typing import Any

from jobhunter.scoring import zones as _zones
from jobhunter.sources import commun as _commun
from jobhunter.sources.commun import (
    _est_vie,
    _norm_url,
    _rx_pays_exclus,
    contrat_de_la_description,
    contrat_du_titre,
    en_france,
    title_ok,
)
from jobhunter.texte import cle as _norm

# accents CONSERVES (cle de deduplication de la queue)

# ── Qualite de la source d'une URL ──────────────────────────────────────────
# Une meme annonce paraît souvent sur LinkedIn ET sur un vrai site d'emploi
# (« Consultant(e) Junior ESG » chez Oderis : LinkedIn + Welcome to the Jungle).
# LinkedIn est le PIRE des deux : la page est derriere un mur de connexion, la
# description est illisible sans compte, et postuler renvoie de toute facon vers
# le site d'origine. On garde donc l'URL la mieux classee.
_AGREGATEURS = (
    "indeed.",
    "talent.com",
    "jobijoba",
    "optioncarriere",
    "jooble",
    "neuvoo",
    "glassdoor",
    "meteojob",
    "keljob",
    "cadremploi",
)

_SITES_EMPLOI = (
    "welcometothejungle",
    "efinancialcareers",
    "linkfinance",
    "apec.fr",
    "francetravail",
    "pole-emploi",
    "businessfrance",
    "hellowork",
    "monster.",
)

_ATS = (
    "greenhouse.io",
    "lever.co",
    "ashbyhq",
    "recruitee.com",
    "smartrecruiters",
    "myworkdayjobs",
    "workday",
    "taleo",
    "successfactors",
    "teamtailor",
    "workable.com",
    "personio",
    "icims.com",
    "avature",
    "flatchr",
    "softy.pro",
)


def rang_source(url: str | None) -> int:
    """Qualite de la source, du pire au meilleur. Sert a arbitrer les doublons.

    0 LinkedIn      mur de connexion, description illisible, redirige ailleurs
    1 agregateur    Indeed, Talent, Jobijoba : copie d'une annonce d'ailleurs
    2 site d'emploi WTJ, APEC, France Travail : annonce de premiere main
    3 ATS / site entreprise : la source, celle ou la candidature arrive
    """
    u = (url or "").lower()
    if not u:
        return -1
    if "linkedin.com" in u:
        return 0
    if any(k in u for k in _AGREGATEURS):
        return 1
    if any(k in u for k in _ATS):
        return 3
    if any(k in u for k in _SITES_EMPLOI):
        return 2
    return 3  # domaine d'entreprise : c'est la source


def merge_into_queue(fresh: list[dict[str, Any]], dry: bool = False, attente: float = 180) -> Any:
    """Fusionne `fresh` dans la file. Lecture-modification-ECRITURE : sous verrou.

    `main()` prend deja le verrou pour tout le processus (`verrou.garder`), et
    c'est le chemin normal. Mais cette fonction s'appelle aussi seule — depuis
    les tests, depuis l'app, depuis un autre programme — et elle s'executait
    alors a decouvert : relire la file, la transformer, puis la reecrire en
    entier sans verrou efface ce qu'un autre programme a ecrit entre-temps.
    On le prend si personne ne le tient, et on ne rend QUE ce qu'on a pris.
    """
    from jobhunter.scoring.fit import fit_detail, score_offer
    from jobhunter.stockage import file as queue_io
    from jobhunter.stockage import verrou

    a_nous = not dry and not verrou.tenu(_commun.QUEUE)
    if a_nous and not verrou.prendre_verrou(_commun.QUEUE, attente=attente):
        raise queue_io.VerrouIndisponible(
            f"{_commun.QUEUE.name} est modifié par un autre programme — rien n'a été fusionné."
        )
    try:
        return _merge_into_queue(fresh, dry, fit_detail, score_offer, queue_io)
    finally:
        if a_nous:
            verrou.rendre_verrou(_commun.QUEUE)


def _merge_into_queue(
    fresh: list[dict[str, Any]], dry: bool, fit_detail: Any, score_offer: Any, queue_io: Any
) -> dict[str, Any]:
    # QUEUE explicite : les tests remplacent cette constante par un fichier
    # jetable. Sans elle, charger() lirait la vraie file.
    q = queue_io.charger(_commun.QUEUE)  # descriptions reinjectees depuis descriptions.json
    # PURGE bruit : rows 'Scan' déjà mergées dont le titre échoue le nouveau filtre anti-bruit
    before = len(q)
    q = [
        x
        for x in q
        if not (str(x.get("statut", "")).startswith("Scan ") and not title_ok(x.get("poste", "")))
    ]
    purged = before - len(q)
    idx = {_norm(x.get("entreprise", "")) + "|" + _norm(x.get("poste", "")): x for x in q}
    have_url = {_norm_url(x.get("url")) for x in q if x.get("url")}
    par_url = {_norm_url(x.get("url")): x for x in q if x.get("url")}
    today = time.strftime("%Y-%m-%d")
    added = updated = promus = hors_zone = pays_ecartes = 0
    # par source de la collecte (etiquette _passe, posee par rendement.mesurer)
    par_source: dict[str, dict[str, int]] = {}
    _EXCLUS = _commun.contrats_exclus()
    _RX_PAYS = _rx_pays_exclus()
    # Offres ECARTEES a la main. Supprimer une offre ne la tue pas : le scan la
    # retrouve a la source et la reajoute le lendemain. Le refus doit tenir.
    from jobhunter.programmes import exclusions as _exc

    _REFUSEES = _exc.charger()
    # Offres RETIREES PAR LE TRI. Le tri juge sur la description, que la collecte
    # n'a pas encore : sans cette memoire, 1157 offres retirees a midi revenaient
    # le soir comme nouvelles (2026-10-05). Voir rejets_tri.py.
    from jobhunter.programmes import rejets_tri as _rej

    _REJ_TRI = _rej.charger(_commun.REJETS_TRI)
    ecartees = rejetees_tri = 0
    for o in fresh:
        # Hors de France : on n'ajoute pas. Voir en_france() — un flux ATS porte
        # le nom de la societe, pas son pays.
        if not en_france(o.get("location")):
            hors_zone += 1
            continue
        # PAYS ECARTES. Voir pays_exclus() : une purge de la file ne tient pas,
        # le scan reajoute le lendemain ce qu'on a supprime la veille.
        #
        # LES V.I.E EN SONT EXEMPTS. Le refus du Royaume-Uni et de la Belgique
        # vise les employeurs LOCAUX ; un V.I.E reste un contrat francais, paye
        # en euros, encadre par Business France, dans une filiale d'un groupe
        # francais. Mesure du 2026-09-22 : le filtre ecartait 35 V.I.E, dont
        # ArcelorMittal Bruxelles « Environment & CO2 data » et Bostik Stafford
        # « Sustainability data », toutes deux a fit 10. La Belgique est meme le
        # premier pays V.I.E, avec 32 offres sur 143.
        if _RX_PAYS and not _est_vie(o) and _RX_PAYS.search(str(o.get("location") or "")):
            pays_ecartes += 1
            continue
        # Meme cle que queue_io.oid : « entreprise|poste », non normalisee.
        if f"{o['entreprise'].strip()}|{o['titre'].strip()}" in _REFUSEES:
            ecartees += 1
            continue
        key = _norm(o["entreprise"]) + "|" + _norm(o["titre"])
        if key not in idx and f"{o['entreprise'].strip()}|{o['titre'].strip()}" in _REJ_TRI:
            rejetees_tri += 1
            continue
        desc = (o.get("description") or "").strip()
        if key in idx or _norm_url(o["url"]) in have_url:
            # déjà en queue : si on a maintenant une description et pas elle → enrichit + re-score
            x = idx.get(key)
            # PROMOTION D'URL. La meme annonce arrive de plusieurs sources ; la
            # premiere vue gagnait, au hasard de l'ordre des scans. Si celle-ci
            # vient d'une meilleure source, elle remplace l'ancienne : on garde
            # le lien ou l'utilisateur peut lire l'offre ET postuler.
            if x is not None and rang_source(o.get("url")) > rang_source(x.get("url")):
                x["url"] = o["url"]
                x["source"] = o.get("source", x.get("source", ""))
                u_ = o["url"].lower()
                x["canal"] = (
                    "manuel"
                    if ("linkedin.com" in u_ or "indeed." in u_ or "welcometothejungle" in u_)
                    else "auto"
                )
                x["site_kind"] = "board" if x["canal"] == "manuel" else "entreprise"
                x["link_status"] = "OK"
                have_url.add(_norm_url(o["url"]))
                promus += 1
                # La description SUIT le lien. Deux sources publient la meme
                # annonce mais pas le meme texte : LinkedIn sert la prose, le
                # site d'origine y ajoute le cadre (contrat, diplome, niveau
                # d'experience). CNP « EXPERT INVESTISSEMENT RESPONSABLE » en
                # est l'exemple : la version LinkedIn ne dit rien du niveau,
                # celle d'eFinancialCareers exige « Plus de 10 ans ». L'offre
                # est restee a fit 10 avec exp_requise = 0 — le detecteur
                # d'experience marche, il n'avait simplement jamais lu la
                # phrase. Sans ce remplacement, promouvoir le lien laissait le
                # texte de la source la moins informative.
                #
                # MAIS une source peut etre meilleure pour le LIEN et moins
                # bonne pour le TEXTE. Indeed en est le cas : son lien vaut
                # mieux que celui de LinkedIn, alors qu'elle ne livre qu'un
                # resume de 160 caracteres. Sans cette garde, promouvoir le
                # lien detruisait une annonce complete pour la remplacer par
                # trois lignes, et fit_score rescorait sur ce qui restait.
                if desc and o.get("desc_partielle") and (x.get("description") or "").strip():
                    desc = ""
                if desc:
                    x["description"] = desc
                    x["fit"], x["exp_requise"], x["fit_fin"] = fit_detail(
                        f"{x.get('poste', '')} {desc}", x.get("poste", "")
                    )
            if x is not None and desc and not (x.get("description") or "").strip():
                x["description"] = desc
                x["fit"], x["exp_requise"], x["fit_fin"] = fit_detail(
                    f"{x.get('poste', '')} {desc}", x.get("poste", "")
                )
                try:
                    x["ats_pct"] = score_offer(
                        dict(
                            role=x.get("poste", ""),
                            missions=desc,
                            profil="",
                            domaine=x.get("domaine", ""),
                        )
                    ).get("pct")
                except Exception:
                    pass
                updated += 1
            # LE CADRE — contrat, teletravail, salaire, date de parution. Une
            # source peut etre mediocre pour le texte et excellente pour ces
            # champs-la : Indeed les sert structures (15/15 des cartes portent
            # un type de contrat) quand nos autres sources obligent a les
            # deviner dans la prose. On ne REMPLACE jamais une valeur posee, on
            # ne comble que les trous — et « non precise » est un trou, c'est
            # ce que le detecteur ecrit quand il n'a rien trouve.
            # VU_LE : la derniere fois qu'une source a de nouveau servi l'offre.
            # Pour APEC, Glassdoor, Indeed, la page de l'offre refuse les robots
            # et ne peut pas dire si l'offre vit encore ; le canal qui l'a
            # trouvee, lui, la ressert tant qu'elle est en ligne. audit_dispo
            # s'en sert pour retirer ce que sa source a cesse de publier.
            # Rattachement par URL aussi : un doublon reconnu au lien seul
            # (meme annonce, intitule retouche) doit compter comme revu.
            if x is None:
                x = par_url.get(_norm_url(o["url"]))
            if x is not None:
                x["vu_le"] = today
            if x is not None:
                if o.get("contrat") and (x.get("contrat") or "") in ("", "non precise"):
                    x["contrat"] = o["contrat"]
                for champ in ("teletravail", "salaire", "date_publication"):
                    v = o.get("date" if champ == "date_publication" else champ)
                    if v and not str(x.get(champ) or "").strip():
                        x[champ] = v
            continue
        have_url.add(_norm_url(o["url"]))
        u = o["url"].lower()
        canal = (
            "manuel"
            if ("linkedin.com" in u or "indeed." in u or "welcometothejungle" in u)
            else "auto"
        )
        # Contrat exclu : on n'ajoute meme pas. l'utilisateur n'est pas etudiant ;
        # inutile de faire entrer des alternances et des stages pour les
        # masquer ensuite a l'affichage.
        # Un contrat ANNONCE par la source passe avant tout ce qu'on pourrait
        # lire dans le titre ou la prose : Indeed publie `jobTypes` en clair,
        # la deduction n'a plus lieu d'etre.
        _ctr = o.get("contrat") or contrat_du_titre(o["titre"], o.get("source", ""))
        # Le titre ne dit rien dans 45 % des cas : la description, si. On ne
        # DEDUIT jamais un contrat absent — « non precise » est une reponse.
        # Un resume de 160 caracteres ne suffit pas a trancher : on ne l'y
        # cherche pas.
        if not _ctr and not o.get("desc_partielle"):
            _ctr = contrat_de_la_description(desc, "non precise")
        _ctr = _ctr or "non precise"
        if _ctr in _EXCLUS:
            continue
        # scoring sur titre + DESCRIPTION (les APIs ATS la fournissent au scan)
        fit, yrs, fin = fit_detail(f"{o['titre']} {desc}", o["titre"])
        try:
            ats = score_offer(
                dict(role=o["titre"], missions=desc, profil="", domaine=o["domaine"])
            ).get("pct")
        except Exception:
            ats = None
        ligne = {
            "entreprise": o["entreprise"],
            "poste": o["titre"],
            "domaine": o["domaine"],
            "statut": f"Scan {today}",
            "url": o["url"],
            "cv": None,
            "lettre": None,
            "rh": None,
            "cv_variant": None,
            "url_type": "OFFRE_DIRECTE",
            "site_kind": "board" if canal == "manuel" else "entreprise",
            "fit": fit,
            "fit_fin": fin,
            "exp_requise": yrs,
            "action": "",
            "contrat": _ctr,
            # Lieu de l'INTITULE s'il nomme une ville etrangere (zones.lieu_effectif) :
            # Talent et Glassdoor donnent parfois le siege, « Paris », a un V.I.E New York.
            "localisation": _zones.lieu_effectif(o.get("location", ""), o.get("titre", "")),
            # Zone geographique, calculee a l'ajout : sans ca, chaque nouvelle
            # offre arriverait sans zone et la colonne de l'app se remplirait de
            # trous jusqu'au prochain passage de zones.py.
            "zone": _zones.zone_lieu(
                _zones.lieu_effectif(o.get("location", ""), o.get("titre", ""))
            ),
            "teletravail": o.get("teletravail", ""),
            "salaire": o.get("salaire", ""),
            "profil": "",
            "pourquoi": "",
            "process": o.get("date") or today,
            # `process` melange depuis toujours la date de parution et celle du
            # scan : sur 5911 offres, 2634 portent le meme jour, celui ou on les
            # a vues. Impossible d'y distinguer l'une de l'autre apres coup, on
            # ne va donc pas l'ecraser. La date CERTAINE va dans son propre
            # champ, vide quand la source ne la donne pas.
            "date_publication": o.get("date") or "",
            "source": o.get("source", ""),
            "missions": "",
            "skills_match": 0,
            "ats_pct": ats,
            "canal": canal,
            "is_stage": False,
            "priorite": "prio" if fit >= 7 else "normal",
            "link_status": "OK",
            "description": desc,
            "vu_le": today,
        }
        q.append(ligne)
        # INDEXER LA LIGNE, PAS L'OFFRE BRUTE. `idx[key] = o` rangeait le dict
        # du scan, alors que la file recoit un dict DIFFERENT : toute promotion
        # d'URL ou description arrivant plus tard dans le MEME lot s'ecrivait
        # sur l'orphelin. Le compteur annoncait « promus: 1 » et la file gardait
        # le lien LinkedIn et sa description vide. C'est le cas NORMAL — un
        # `--all` enchaine ATS, LinkedIn, WTJ, eFC et Indeed sur la meme annonce.
        idx[key] = ligne
        par_url[_norm_url(o["url"])] = ligne
        added += 1
        compte = par_source.setdefault(
            str(o.get("_passe") or ""), {"nouvelles": 0, "pertinentes": 0}
        )
        compte["nouvelles"] += 1
        compte["pertinentes"] += int(fit >= 8)
    if not dry:
        importlib.import_module("jobhunter.programmes.jutil").jwrite(_commun.QUEUE, q)
    return dict(
        added=added,
        updated=updated,
        promus=promus,
        purged=purged,
        hors_zone=hors_zone,
        ecartees=ecartees,
        rejetees_tri=rejetees_tri,
        pays_ecartes=pays_ecartes,
        total=len(q),
        par_source=par_source,
    )
