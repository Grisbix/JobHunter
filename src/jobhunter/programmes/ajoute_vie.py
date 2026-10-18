#!/usr/bin/env python3
"""ajoute_vie.py — Ajoute une offre V.I.E a la file, avec CV et lettre.

POURQUOI. mon-vie-via est une application monopage : le HTML brut est une
coquille vide, et le scan quotidien (job_sources --vie) ne lit que la LISTE.
Les fiches arrivaient donc recopiees a la main depuis le navigateur, champ par
champ — trois offres traitees ainsi avant qu'on ne trouve mieux.

L'API porte en fait une route DETAIL :

    civiweb-api-prd.azurewebsites.net/api/Offers/details/{id}

Elle rend la fiche entiere — missions, profil, indemnite, dates, contact —
avec la meme cle publique que la liste, celle que le site expedie a tout
visiteur. Pas de compte, pas de donnees personnelles.

LA LANGUE N'EST PAS FORCEE : langue_offre() lit l'annonce. Une V.I.E redigee
en anglais recoit un dossier en anglais.

Run :
  python ajoute_vie.py 245612
  python ajoute_vie.py https://mon-vie-via.businessfrance.fr/offres/245612
  python ajoute_vie.py 245612 --dry
"""

import argparse
import collections
import json
import re
import sys
import urllib.error
import urllib.request

from jobhunter import racine as _racine

HERE = _racine.scripts()

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

API = "https://civiweb-api-prd.azurewebsites.net/api/Offers/details/{}"
SITE = "https://mon-vie-via.businessfrance.fr/offres/{}"


def fiche(id_):
    from jobhunter import sources as J

    r = urllib.request.Request(
        API.format(id_), headers={"x-api-key": J._vie_key(), "Accept": "application/json"}
    )
    with urllib.request.urlopen(r, timeout=25) as f:
        return json.loads(f.read().decode("utf-8", "replace"))


def construire(d, id_):
    """La fiche de l'API -> une ligne de file. Rend aussi missions et profil,
    que tailor_* consomme separement du corps de l'annonce."""
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
    """La date de fin de diffusion : publication + duree, en jours."""
    import datetime

    try:
        d0 = datetime.date.fromisoformat(str(d.get("startBroadcastDate"))[:10])
        return (d0 + datetime.timedelta(days=int(d.get("durationBroadcast") or 30))).isoformat()
    except Exception:
        return ""


# ── Rattrapage en lot ───────────────────────────────────────────────────────
# Ce que le scan quotidien laisse derriere lui. Mesure du 21/09/2026 sur les
# 274 V.I.E de la file :
#
#     268  sans salaire
#     271  sans contact recruteur
#      49  sans CV ni lettre
#       3  sans description
#
# `job_sources --vie` lit la LISTE de l'API, qui ne porte ni l'indemnite ni le
# contact. La route DETAIL les porte. Personne n'allait les chercher.
_RX_ID_VIE = re.compile(r"/offres/(\d{4,})")


def _incompletes(q):
    """Les V.I.E dont l'API detail a quelque chose a apprendre, avec leur id."""
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
    """Complete toutes les V.I.E incompletes depuis l'API detail.

    LE VERROU N'EST PRIS QU'A L'ECRITURE. 258 appels reseau espaces d'une
    pause, c'est plusieurs minutes ; les passer sous verrou bloquerait l'app
    pendant tout ce temps pour rien. On collecte d'abord, on ecrit ensuite.
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
            # 404 ET 500 veulent dire « cette annonce n'existe plus ».
            # Verifie le 21/09/2026 : l'id 246087 (offre vivante) repond a
            # chaque appel, les ids 244993 et 244988 rendent toujours
            #     {"message":"Une erreur est survenue lors du traitement..."}
            # Ce n'est donc pas un throttle — l'API sert son erreur generique
            # a la place d'un 404 propre. Une V.I.E expire au bout d'un mois :
            # sur une file de plusieurs semaines, c'est le cas MAJORITAIRE,
            # pas une panne.
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

    # UN ECHEC TOTAL N'EST PAS « tout a expire ». Si pas une seule fiche ne
    # revient, la cause probable est la cle, le reseau ou l'API — pas une file
    # entierement perimee. On le dit, et on n'ecrit RIEN : marquer 258 offres
    # « expirees » sur une panne d'API serait une perte seche.
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
                # Le mail du recruteur, que rien ne stockait. Sur une V.I.E
                # c'est l'interlocuteur direct : une relance y arrive, la ou
                # un formulaire n'accuse jamais reception.
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

        # Les retirees prennent le statut que `tri_file` sait lire. On ne les
        # SUPPRIME pas : une annonce fermee apres candidature doit garder sa
        # ligne, sinon la trace de l'envoi devient orpheline.
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
                # DEJA EN FILE NE VEUT PAS DIRE DEJA COMPLETE. Le scan quotidien
                # (job_sources --vie) ne lit que la LISTE : il rend l'intitule,
                # l'entreprise et le lieu, sans salaire, sans description, sans
                # missions. L'API DETAIL, elle, porte tout. Abandonner ici
                # laissait l'offre a moitie vide et sans dossier — ce qui est
                # exactement le cas qu'on vient de rencontrer sur la 246087 :
                # en file depuis trois jours, salaire vide, aucun document.
                #
                # On ne REMPLACE rien : on ne remplit que ce qui manque. Seule
                # la description fait exception, et seulement si celle qu'on
                # tient est plus longue — c'est la regle deja posee dans
                # merge_into_queue, ou un extrait ne doit jamais ecraser un
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

            # LE DOSSIER NE SE REFAIT PAS S'IL EXISTE. Sur une offre deja en
            # file, `o` est la ligne existante : regenerer ecraserait un
            # document peut-etre deja relu, voire deja envoye. On ne produit
            # que ce qui manque, ou ce dont le fichier a disparu.
            from jobhunter.programmes.jutil import chemin_de  # noqa: E402  (apres le verrou)

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
