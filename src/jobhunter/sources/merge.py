"""Merge of the collection into apply_queue.json: dedup, URL promotion, scoring.

Part of jobhunter.sources (formerly Scripts/job_sources.py, phase 3.4).
"""

import importlib
import time
from typing import Any

from jobhunter.scoring import zones as _zones
from jobhunter.sources import common as _commun
from jobhunter.sources.common import (
    _est_vie,
    _norm_url,
    _rx_pays_exclus,
    contrat_de_la_description,
    contrat_du_titre,
    en_france,
    title_ok,
)
from jobhunter.text import cle as _norm

# accents KEPT (dedup key of the queue)

# ── Quality of a URL's source ──────────────────────────────────────────
# The same posting often appears on LinkedIn AND on a real job site
# (« Consultant(e) Junior ESG » chez Oderis : LinkedIn + Welcome to the Jungle).
# LinkedIn is the WORSE of the two: the page is behind a login wall, the
# description is unreadable without an account, and applying sends you anyway to
# the original site. So we keep the best-ranked URL.
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
    """Quality of the source, from worst to best. Used to arbitrate duplicates.

    0 LinkedIn      login wall, unreadable description, redirects elsewhere
    1 aggregator    Indeed, Talent, Jobijoba: copy of a posting from elsewhere
    2 job site      WTJ, APEC, France Travail: first-hand posting
    3 ATS / company site: the source, where the application arrives
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
    return 3  # company domain: it is the source


def merge_into_queue(fresh: list[dict[str, Any]], dry: bool = False, attente: float = 180) -> Any:
    """Merges `fresh` into the queue. Read-modify-WRITE: under lock.

    `main()` already takes the lock for the whole process (`verrou.garder`), and
    that is the normal path. But this function is also called alone — from
    the tests, from the app, from another program — and it then ran
    unprotected: reading the queue, transforming it, then rewriting it in
    full without a lock erases what another program wrote in the meantime.
    We take it if nobody holds it, and we only release what we took.
    """
    from jobhunter.scoring.fit import fit_detail, score_offer
    from jobhunter.storage import lock as verrou
    from jobhunter.storage import queue as queue_io

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
    # Explicit QUEUE: the tests replace this constant with a throwaway
    # file. Without it, charger() would read the real queue.
    q = queue_io.charger(_commun.QUEUE)  # descriptions reinjectees depuis descriptions.json
    # Noise PURGE: 'Scan' rows already merged whose title fails the new anti-noise filter.
    # NEVER an offer of the tracker: a changed filter or profile must not deprive an
    # application of its posting (AGENTS.md invariant; audit of 19/10/2026, "Brand
    # Design Intern" applied to then purged by an empty merge).
    from jobhunter.storage import applications as suivi_io

    suivies = set(suivi_io.charger())
    before = len(q)
    q = [
        x
        for x in q
        if queue_io.oid(x) in suivies
        or not (str(x.get("statut", "")).startswith("Scan ") and not title_ok(x.get("poste", "")))
    ]
    purged = before - len(q)
    idx = {_norm(x.get("entreprise", "")) + "|" + _norm(x.get("poste", "")): x for x in q}
    have_url = {_norm_url(x.get("url")) for x in q if x.get("url")}
    par_url = {_norm_url(x.get("url")): x for x in q if x.get("url")}
    today = time.strftime("%Y-%m-%d")
    added = updated = promus = hors_zone = pays_ecartes = 0
    # per source of the collection (_passe label, set by rendement.mesurer)
    par_source: dict[str, dict[str, int]] = {}
    _EXCLUS = _commun.contrats_exclus()
    _RX_PAYS = _rx_pays_exclus()
    # Offers SET ASIDE by hand. Deleting an offer does not kill it: the scan
    # finds it again at the source and re-adds it the next day. The refusal must hold.
    from jobhunter.programs import exclusions as _exc

    _REFUSEES = _exc.charger()
    # Offers REMOVED BY THE SORT. The sort judges on the description, which the collection
    # does not have yet: without this memory, 1157 offers removed at noon came back
    # in the evening as new (2026-10-05). See rejets_tri.py.
    from jobhunter.programs import sort_rejections as _rej

    _REJ_TRI = _rej.charger(_commun.REJETS_TRI)
    ecartees = rejetees_tri = 0
    for o in fresh:
        # Outside France: we do not add. See en_france() — an ATS feed carries
        # the company's name, not its country.
        if not en_france(o.get("location")):
            hors_zone += 1
            continue
        # EXCLUDED COUNTRIES. See pays_exclus(): a purge of the queue does not hold,
        # the scan re-adds the next day what was deleted the day before.
        #
        # V.I.E ARE EXEMPT. The refusal of the United Kingdom and Belgium
        # targets LOCAL employers; a V.I.E remains a French contract, paid
        # in euros, supervised by Business France, in a subsidiary of a French
        # group. Measurement of 2026-09-22: the filter set aside 35 V.I.E, including
        # ArcelorMittal Brussels "Environment & CO2 data" and Bostik Stafford
        # "Sustainability data", both at fit 10. Belgium is even the
        # first V.I.E country, with 32 offers out of 143.
        if _RX_PAYS and not _est_vie(o) and _RX_PAYS.search(str(o.get("location") or "")):
            pays_ecartes += 1
            continue
        # Same key as queue_io.oid: "entreprise|poste", not normalised.
        if f"{o['entreprise'].strip()}|{o['titre'].strip()}" in _REFUSEES:
            ecartees += 1
            continue
        key = _norm(o["entreprise"]) + "|" + _norm(o["titre"])
        if key not in idx and f"{o['entreprise'].strip()}|{o['titre'].strip()}" in _REJ_TRI:
            rejetees_tri += 1
            continue
        desc = (o.get("description") or "").strip()
        if key in idx or _norm_url(o["url"]) in have_url:
            # already in the queue: if we now have a description and it does not → enrich + re-score
            # The row is found by identity OR by URL, BEFORE any enrichment: the
            # same posting whose source corrected the title otherwise never got its
            # description (audit of 19/10/2026).
            x = idx.get(key)
            if x is None:
                x = par_url.get(_norm_url(o["url"]))
            # URL PROMOTION. The same posting arrives from several sources; the
            # first one seen won, at the whim of the scan order. If this one
            # comes from a better source, it replaces the old one: we keep
            # the link where the user can read the offer AND apply.
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
                # The description FOLLOWS the link. Two sources publish the same
                # posting but not the same text: LinkedIn serves the prose, the
                # original site adds the frame (contract, degree, level
                # of experience). CNP "EXPERT INVESTISSEMENT RESPONSABLE" is
                # the example: the LinkedIn version says nothing about the level,
                # the eFinancialCareers one requires "Plus de 10 ans". The offer
                # stayed at fit 10 with exp_requise = 0 — the experience
                # detector works, it had simply never read the
                # sentence. Without this replacement, promoting the link left the
                # text of the least informative source.
                #
                # BUT a source can be better for the LINK and worse
                # for the TEXT. Indeed is the case: its link is worth
                # more than LinkedIn's, while it only delivers a
                # 160-character summary. Without this guard, promoting the
                # link destroyed a full posting to replace it with
                # three lines, and fit_score re-scored on what was left.
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
            # THE FRAME — contract, remote work, salary, publication date. A
            # source can be poor for the text and excellent for these
            # fields: Indeed serves them structured (15/15 cards carry
            # a contract type) where our other sources force us to
            # guess them in the prose. We NEVER replace a set value, we
            # only fill the gaps — and "non precise" is a gap, it is
            # what the detector writes when it found nothing.
            # VU_LE: the last time a source served the offer again.
            # For APEC, Glassdoor, Indeed, the offer page refuses robots
            # and cannot say whether the offer is still alive; the channel that
            # found it, on the other hand, serves it again as long as it is online. audit_dispo
            # uses it to remove what its source stopped publishing.
            # Matching by URL too: a duplicate recognised by its link alone
            # (same posting, retouched title) must count as seen again.
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
        # Excluded contract: we do not even add. The user is not a student;
        # no point letting in work-study and internship offers for
        # masquer ensuite a l'affichage.
        # A contract ANNOUNCED by the source comes before anything we could
        # read in the title or the prose: Indeed publishes `jobTypes` in clear,
        # deduction is no longer needed.
        _ctr = o.get("contrat") or contrat_du_titre(o["titre"], o.get("source", ""))
        # The title says nothing in 45 % of cases: the description does. We never
        # DEDUCE a missing contract — "non precise" is an answer.
        # A 160-character summary is not enough to decide: we do not
        # search it there.
        if not _ctr and not o.get("desc_partielle"):
            _ctr = contrat_de_la_description(desc, "non precise")
        _ctr = _ctr or "non precise"
        if _ctr in _EXCLUS:
            continue
        # scoring on title + DESCRIPTION (the ATS APIs provide it at scan time)
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
            # Place of the TITLE if it names a foreign city (zones.lieu_effectif):
            # Talent and Glassdoor sometimes give the head office, "Paris", to a New York V.I.E.
            "localisation": _zones.lieu_effectif(o.get("location", ""), o.get("titre", "")),
            # Geographic zone, computed on adding: without it, each new
            # offer would arrive without a zone and the app's column would fill with
            # gaps until the next run of zones.py.
            "zone": _zones.zone_lieu(
                _zones.lieu_effectif(o.get("location", ""), o.get("titre", ""))
            ),
            "teletravail": o.get("teletravail", ""),
            "salaire": o.get("salaire", ""),
            "profil": "",
            "pourquoi": "",
            "process": o.get("date") or today,
            # `process` has always mixed the publication date and the scan
            # date: out of 5911 offers, 2634 carry the same day, the one on which we
            # saw them. Impossible to tell one from the other afterwards, so we
            # will not overwrite it. The CERTAIN date goes in its own
            # field, empty when the source does not give it.
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
        if o.get("autres_lieux"):  # same job published in other cities (scan)
            ligne["autres_lieux"] = list(o["autres_lieux"])
        q.append(ligne)
        # INDEX THE ROW, NOT THE RAW OFFER. `idx[key] = o` stored the dict
        # of the scan, while the queue receives a DIFFERENT dict: any promotion
        # of URL or description arriving later in the SAME batch was written
        # on the orphan. The counter announced "promus: 1" and the queue kept
        # the LinkedIn link and its empty description. It is the NORMAL case — an
        # `--all` chains ATS, LinkedIn, WTJ, eFC and Indeed on the same posting.
        idx[key] = ligne
        par_url[_norm_url(o["url"])] = ligne
        added += 1
        compte = par_source.setdefault(
            str(o.get("_passe") or ""), {"nouvelles": 0, "pertinentes": 0}
        )
        compte["nouvelles"] += 1
        compte["pertinentes"] += int(fit >= 8)
    if not dry:
        importlib.import_module("jobhunter.programs.util").jwrite(_commun.QUEUE, q)
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
