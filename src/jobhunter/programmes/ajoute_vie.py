#!/usr/bin/env python3
"""ajoute_vie.py — Adds a V.I.E offer to the queue, with CV and letter.

WHY. mon-vie-via is a single-page application: the raw HTML is an empty shell, and
the daily scan (job_sources --vie) only reads the LIST. The postings were therefore
copied by hand from the browser, field by field — three offers handled that way
before something better was found.

The API actually carries a DETAIL route:

    civiweb-api-prd.azurewebsites.net/api/Offers/details/{id}

It returns the whole posting — missions, profile, allowance, dates, contact — with
the same public key as the list, the one the site sends to every visitor. No account,
no personal data.

THE LANGUAGE IS NOT FORCED: langue_offre() reads the posting. A V.I.E written in
English receives a folder in English.

Run:
  python JobHunter.pyw ajoute_vie 245612
  python JobHunter.pyw ajoute_vie https://mon-vie-via.businessfrance.fr/offres/245612
  python JobHunter.pyw ajoute_vie 245612 --dry
"""

import argparse
import collections
import json
import re
import sys
import urllib.error
import urllib.request

from jobhunter import racine as _racine
from jobhunter.reseau import exiger_http

HERE = _racine.scripts()

sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]  # console : TextIOWrapper

API = "https://civiweb-api-prd.azurewebsites.net/api/Offers/details/{}"
SITE = "https://mon-vie-via.businessfrance.fr/offres/{}"


def fiche(id_):
    from jobhunter import sources as J

    r = urllib.request.Request(
        exiger_http(API.format(id_)),
        headers={"x-api-key": J._vie_key(), "Accept": "application/json"},
    )
    with urllib.request.urlopen(r, timeout=25) as f:  # nosec B310 : scheme checked by exiger_http
        return json.loads(f.read().decode("utf-8", "replace"))


def construire(d, id_):
    """The API posting -> a queue row. Also returns missions and profile,
    which tailor_* uses separately from the posting's body."""
    poste = (d.get("missionTitle") or "").strip()
    societe = (d.get("organizationName") or "").strip()
    lieu = f"{(d.get('cityName') or '').title()} ({(d.get('countryName') or '').title()})"
    missions = " ".join((d.get("missionDescription") or "").split())
    profil = " ".join((d.get("missionProfile") or "").split())
    desc = (
        f"V.I.E de {d.get('missionDuration')} mois a {lieu}, du "
        f"{str(d.get('missionStartDate'))[:10]} au {str(d.get('missionEndDate'))[:10]}. "
        f"Etablissement : {societe}. Indemnite mensuelle : {d.get('indemnite', 0):.2f} EUR. "
        f"Teletravail : {'oui' if d.get('teleworkingAvailable') else 'non'}. "
        f"Reference {d.get('reference')}, publiee le {str(d.get('startBroadcastDate'))[:10]}.\n\n"
        f"POSTE ET MISSION\n{(d.get('missionDescription') or '').strip()}\n\n"
        f"LE PROFIL IDEAL\n{(d.get('missionProfile') or '').strip()}"
    )
    return poste, societe, lieu, missions, profil, desc


def expire_le(d):
    """The end date of publication: publication + duration, in days."""
    import datetime

    try:
        d0 = datetime.date.fromisoformat(str(d.get("startBroadcastDate"))[:10])
        return (d0 + datetime.timedelta(days=int(d.get("durationBroadcast") or 30))).isoformat()
    except Exception:
        return ""


# ── Batch catch-up ──────────────────────────────────────────────────────────
# What the daily scan leaves behind. Measured on 21/09/2026 on the
# 274 V.I.E of the queue:
#
#     268  without salary
#     271  without recruiter contact
#      49  without CV or letter
#       3  without description
#
# `job_sources --vie` reads the API's LIST, which carries neither the allowance nor the
# contact. The DETAIL route carries them. Nobody went to get them.
_RX_ID_VIE = re.compile(r"/offres/(\d{4,})")


def _incompletes(q):
    """The V.I.E about which the detail API has something to teach, with their id."""
    out = []
    for o in q:
        if o.get("contrat") != "V.I.E" and "mon-vie-via" not in (o.get("url") or ""):
            continue
        m = _RX_ID_VIE.search(o.get("url") or "")
        if not m:
            continue
        manque = [
            k
            for k in ("salaire", "rh", "rh_email", "description", "missions")
            if not str(o.get(k) or "").strip()
        ]
        if manque:
            out.append((m.group(1), o, manque))
    return out


def completer(a):
    """Completes all the incomplete V.I.E from the detail API.

    THE LOCK IS ONLY TAKEN FOR WRITING. 258 network calls spaced by a pause is
    several minutes; doing them under lock would block the app all that time for
    nothing. We collect first, we write afterwards.
    """
    import time

    from jobhunter.stockage import file as queue_io

    q = queue_io.charger()
    lot = _incompletes(q)
    if a.limite:
        lot = lot[: a.limite]
    print(f"{len(lot)} V.I.E a completer (sur {len(q)} offres en file)")
    if not lot:
        return 0

    recolte, morts, erreurs = {}, [], 0
    for i, (id_, o, manque) in enumerate(lot, 1):
        try:
            d = fiche(id_)
        except urllib.error.HTTPError as e:
            # 404 AND 500 mean "this posting no longer exists".
            # Checked on 21/09/2026: the id 246087 (live offer) answers
            # every call, the ids 244993 and 244988 always return
            #     {"message":"Une erreur est survenue lors du traitement..."}
            # So it is not a throttle — the API serves its generic error
            # instead of a clean 404. A V.I.E expires after a month:
            # on a queue several weeks old, it is the MAJORITY case,
            # not a failure.
            if e.code in (404, 500):
                morts.append(id_)
            else:
                erreurs += 1
                print(f"  ! {id_} : HTTP {e.code}")
            continue
        except Exception as e:
            erreurs += 1
            print(f"  ! {id_} : {type(e).__name__}")
            continue
        recolte[id_] = d
        if i % 25 == 0 or i == len(lot):
            print(f"  {i}/{len(lot)} lues — {len(morts)} retirees, {erreurs} en erreur")
        time.sleep(a.pause)

    print(f"\n{len(recolte)} fiches recuperees, {len(morts)} annonces retirees, {erreurs} erreurs")

    # A TOTAL FAILURE IS NOT "everything expired". If not a single posting
    # comes back, the likely cause is the key, the network or the API — not an entirely
    # stale queue. We say so, and write NOTHING: marking 258 offers
    # "expirées" on an API failure would be a dead loss.
    if not recolte and (morts or erreurs):
        print("! AUCUNE fiche recuperee sur l'ensemble du lot.")
        print("  Cle d'API, reseau ou service indisponible — rien n'est ecrit.")
        return 4

    if a.dry:
        print("[DRY] rien n'a ete ecrit.")
        return 0
    if not recolte:
        return 0

    rempli = collections.Counter()
    touchees = 0
    with queue_io.transaction() as file:
        index = {}
        for o in file:
            m = _RX_ID_VIE.search(o.get("url") or "")
            if m:
                index.setdefault(m.group(1), o)
        for id_, d in recolte.items():
            o = index.get(id_)
            if o is None:
                continue
            _, _, _, missions, profil, desc = construire(d, id_)
            neuf = {
                "salaire": f"{d.get('indemnite', 0):.2f} EUR / mois",
                "rh": d.get("contactName") or "",
                # The recruiter's email, which nothing stored. On a V.I.E
                # it is the direct contact: a follow-up reaches them, where
                # a form never acknowledges receipt.
                "rh_email": d.get("contactEmail") or "",
                "missions": missions,
                "profil": profil,
                "date_publication": str(d.get("startBroadcastDate"))[:10],
                "teletravail": "oui" if d.get("teleworkingAvailable") else "non",
            }
            chg = False
            for k, v in neuf.items():
                if v and not str(o.get(k) or "").strip():
                    o[k] = v
                    rempli[k] += 1
                    chg = True
            if len(desc) > len(o.get("description") or ""):
                o["description"] = desc
                rempli["description"] += 1
                chg = True
            touchees += chg

        # The withdrawn ones take the status that `tri_file` can read. We do not
        # DELETE them: a posting closed after an application must keep its
        # row, otherwise the trace of the send becomes orphaned.
        expirees = 0
        for id_ in morts:
            o = index.get(id_)
            if o is not None and (o.get("link_status") or "") != "EXPIREE":
                o["link_status"] = "EXPIREE"
                expirees += 1

    print(f"{touchees} offres enrichies, {expirees} marquees EXPIREE")
    for k, n in rempli.most_common():
        print(f"   {k:18} +{n}")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("offre", nargs="?", default="", help="identifiant ou URL mon-vie-via")
    ap.add_argument(
        "--completer",
        action="store_true",
        help="balaie la file et complete toutes les V.I.E incompletes",
    )
    ap.add_argument("--limite", type=int, default=0, help="avec --completer")
    ap.add_argument(
        "--pause", type=float, default=0.5, help="secondes entre deux appels a l'API (defaut 0,5)"
    )
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()

    if a.completer:
        return completer(a)
    if not a.offre:
        ap.error("donner un identifiant, ou --completer")

    m = re.search(r"(\d{5,})", a.offre)
    if not m:
        print("! identifiant introuvable dans", a.offre)
        return 2
    id_ = m.group(1)

    d = fiche(id_)
    poste, societe, lieu, missions, profil, desc = construire(d, id_)
    url = SITE.format(id_)

    from jobhunter.programmes.scrape_jobs import classify_domaine
    from jobhunter.scoring.fit import fit_detail, score_offer
    from jobhunter.scoring.langue import langue_offre
    from jobhunter.scoring.zones import zone_lieu
    from jobhunter.stockage import file as queue_io

    fit, yrs, fin = fit_detail(f"{poste} {desc}", poste)
    dom = classify_domaine(poste)
    lg = langue_offre(poste, desc, lieu)
    try:
        ats = score_offer(dict(role=poste, missions=missions, profil=profil, domaine=dom)).get(
            "pct"
        )
    except Exception:
        ats = None

    print(f"{societe} — {poste}")
    print(f"  {lieu} | zone {zone_lieu(lieu)} | langue {lg}")
    print(f"  fit {fit}, experience demandee {yrs} an(s), domaine {dom}, ATS {ats}")
    print(
        f"  {d.get('indemnite', 0):.2f} EUR/mois, {d.get('missionDuration')} mois, "
        f"depart {str(d.get('missionStartDate'))[:10]}"
    )
    print(f"  publiee le {str(d.get('startBroadcastDate'))[:10]}, expire le {expire_le(d)}")
    print(f"  {d.get('viewCounter')} vue(s), {d.get('candidateCounter')} candidat(s)")
    if a.dry:
        print("\n[DRY] rien n'a ete ecrit.")
        return 0

    import time

    from jobhunter.documents import tailor_letter, to_pdf
    from jobhunter.programmes.jutil import url_de
    from jobhunter.programmes.rename_docs import new_name

    try:
        with queue_io.transaction() as q:
            cle = f"{societe}|{poste}"
            deja = next((o for o in q if f"{o.get('entreprise')}|{o.get('poste')}" == cle), None)
            if deja is not None:
                # ALREADY IN THE QUEUE DOES NOT MEAN ALREADY COMPLETE. The daily scan
                # (job_sources --vie) only reads the LIST: it returns the title,
                # the company and the place, without salary, without description, without
                # missions. The DETAIL API carries everything. Giving up here
                # left the offer half empty and without a folder — which is
                # exactly the case we just met on 246087:
                # in the queue for three days, empty salary, no document.
                #
                # We REPLACE nothing: we only fill what is missing. Only
                # the description is an exception, and only if the one we
                # hold is longer — it is the rule already set in
                # merge_into_queue, where an excerpt must never overwrite a
                # texte entier.
                neuf = {
                    "salaire": f"{d.get('indemnite', 0):.2f} EUR / mois",
                    "missions": missions,
                    "profil": profil,
                    "contrat": "V.I.E",
                    "localisation": lieu,
                    "zone": zone_lieu(lieu),
                    "exp_requise": yrs,
                    "date_publication": str(d.get("startBroadcastDate"))[:10],
                    "ats_pct": ats,
                    "url": url,
                    "url_type": "OFFRE_DIRECTE",
                    "teletravail": "oui" if d.get("teleworkingAvailable") else "non",
                    "rh": d.get("contactName") or None,
                }
                rempli = [
                    k
                    for k, v in neuf.items()
                    if v not in (None, "", 0) and not str(deja.get(k) or "").strip()
                ]
                for k in rempli:
                    deja[k] = neuf[k]
                if len(desc) > len(deja.get("description") or ""):
                    deja["description"] = desc
                    rempli.append("description")
                print(
                    "\ndeja en file — "
                    + (
                        f"{len(rempli)} champ(s) completes : {', '.join(rempli)}"
                        if rempli
                        else "rien a completer"
                    )
                )
                o = deja
            else:
                o = {
                    "entreprise": societe,
                    "poste": poste,
                    "domaine": dom,
                    "statut": f"Ajout manuel {time.strftime('%Y-%m-%d')}",
                    "url": url,
                    "cv": None,
                    "lettre": None,
                    "rh": d.get("contactName") or None,
                    "cv_variant": None,
                    "url_type": "OFFRE_DIRECTE",
                    "site_kind": "board",
                    "fit": fit,
                    "fit_fin": fin,
                    "exp_requise": yrs,
                    "action": "",
                    "contrat": "V.I.E",
                    "localisation": lieu,
                    "zone": zone_lieu(lieu),
                    "teletravail": "oui" if d.get("teleworkingAvailable") else "non",
                    "salaire": f"{d.get('indemnite', 0):.2f} EUR / mois",
                    "profil": profil,
                    "pourquoi": "",
                    "process": str(d.get("startBroadcastDate"))[:10],
                    "date_publication": str(d.get("startBroadcastDate"))[:10],
                    "source": "vie-api",
                    "missions": missions,
                    "skills_match": 0,
                    "ats_pct": ats,
                    "canal": "manuel",
                    "is_stage": False,
                    "priorite": "prio" if fit >= 7 else "normal",
                    "link_status": "OK",
                    "description": desc,
                }
                q.append(o)

            # THE FOLDER IS NOT REDONE IF IT EXISTS. On an offer already in
            # the queue, `o` is the existing row: regenerating would overwrite a
            # document perhaps already reviewed, or even already sent. We only produce
            # what is missing, or what whose file has disappeared.
            from jobhunter.programmes.jutil import chemin_de  # noqa: E402  (after the lock)

            off = dict(
                company=societe,
                role=poste,
                offer_text=f"{poste} {desc}",
                missions=missions[:400],
                profil=profil[:300],
                domaine=dom,
                rh=o.get("rh"),
            )
            from jobhunter.documents import cv_une_page

            for quoi, champ in (("CV", "cv"), ("Lettre", "lettre")):
                ancien = chemin_de(o.get(champ))
                if ancien is not None and ancien.exists():
                    print(f"  {quoi:7} deja la -> {ancien.name}")
                    continue
                nom = new_name(quoi, poste, societe)
                if champ == "cv":
                    p, pdf = cv_une_page(off, nom=nom, langue=lg)
                else:
                    p = tailor_letter(off, nom=nom, langue=lg)
                    pdf = to_pdf(p) if p else None
                if p:
                    o[champ] = url_de(pdf or p)
                    print(f"  {quoi:7} -> {p.stem}")
    except queue_io.VerrouIndisponible as e:
        print(f"! {e}")
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
