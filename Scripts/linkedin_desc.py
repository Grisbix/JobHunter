#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""linkedin_desc.py — Recupere la DESCRIPTION des offres LinkedIn depuis l'API invite.

POURQUOI. Le fit se calcule sur « intitule + description ». Une offre sans
description est notee sur huit mots de titre : fit moyen 2.9 contre 5.6 pour une
offre lue. 228 offres LinkedIn de la queue n'avaient pas de description, et
scrape_desc.py echoue dessus (mur de connexion) : 5 succes sur 200.

L'API invite `jobs-guest/jobs/api/jobPosting/<id>` est PUBLIQUE, sans
authentification, et sert la description complete. C'est le meme point d'acces que
linkedin_closed.py — on reutilise son outillage plutot que de le dupliquer.
Aucun contournement de protection : c'est l'endpoint que LinkedIn expose aux
visiteurs non connectes.

Re-score le fit ET exp_requise dans la foulee : une description ajoutee sans
re-scoring laisse l'offre a son ancien fit, calcule sans elle.

Run :
  python linkedin_desc.py --dry              # compte, n'ecrit rien
  python linkedin_desc.py --limit 100
  python linkedin_desc.py                    # toutes les offres concernees
"""

import sys
import re
import json
import html
import time
import argparse
import concurrent.futures as cf
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
QUEUE = HERE / "apply_queue.json"

from linkedin_closed import API, UA, job_id, RX_FERME  # meme endpoint, meme UA

# La description vit dans un bloc `description__text` ; repli sur <section>.
RX_DESC = [
    re.compile(r'<div class="[^"]*description__text[^"]*">(.*?)</div>\s*</div>', re.S),
    re.compile(r'<section class="[^"]*description[^"]*">(.*?)</section>', re.S),
]
RX_BALISE = re.compile(r"<[^>]+>")
RX_SCRIPT = re.compile(r"<(script|style)\b.*?</\1>", re.S | re.I)


# Compteur de bridages, partage par les threads. Sert a DISTINGUER « LinkedIn
# nous coupe » de « cette annonce n'a pas de description » — la premiere passe
# a rendu 1031 textes sur 2653 et les 1622 echecs ont ete pris pour des annonces
# vides, alors qu'un simple reessai les lisait toutes. Un bridage silencieux
# ressemble a un resultat.
BRIDAGES = {"n": 0}

# Offres dont la fiche porte le marqueur de fermeture. On lit deja la page pour
# sa description : y voir « No longer accepting applications » ne coute rien, et
# evite a audit_dispo une requete de plus sur le meme endpoint.
FERMEES = set()


def description(jid, client, essais=4):
    """Texte de l'annonce, ou "" si illisible. Ne leve jamais : un echec laisse
    l'offre telle quelle, aucune donnee n'est degradee."""
    for n in range(essais):
        try:
            r = client.get(API.format(jid), headers=UA, timeout=20)
        except Exception:
            time.sleep(1.5 * (n + 1))
            continue
        if r.status_code == 429:
            BRIDAGES["n"] += 1
            time.sleep(5 * (n + 1))
            continue
        if r.status_code != 200:
            return ""
        if RX_FERME.search(r.text):
            FERMEES.add(jid)
            return ""
        h = RX_SCRIPT.sub(" ", r.text)
        for rx in RX_DESC:
            m = rx.search(h)
            if not m:
                continue
            t = html.unescape(RX_BALISE.sub(" ", m.group(1)))
            t = re.sub(r"\s+", " ", t).strip()
            # Sous 200 caracteres c'est un fragment d'interface, pas une annonce
            if len(t) >= 200:
                return t
        return ""
    return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    # 6 threads bridaient LinkedIn des les premieres centaines : 1622 echecs sur
    # 2653, tous lisibles au reessai. Mieux vaut lire moins vite et tout lire.
    ap.add_argument("--workers", type=int, default=3)
    # PAR LOTS, ET LE VERROU SEULEMENT POUR ECRIRE. Le 2026-09-22, la premiere
    # version a lu 6438 descriptions en trois heures a l'interieur d'UNE SEULE
    # transaction : verrou tenu trois heures, application bloquee, et tout le
    # travail en memoire jusqu'a la derniere seconde — un plantage a 2 h 50
    # perdait 2 h 50 de reseau. Maintenant : on lit un instantane sans verrou,
    # on collecte hors verrou, et chaque lot s'ecrit en quelques secondes sur une
    # file RELUE dans le verrou. Un arret ne coute que le lot en cours.
    ap.add_argument("--lot", type=int, default=500)
    a = ap.parse_args()

    import queue_io

    cibles = _cibles(queue_io.charger(), a.limit)
    print(f"{len(cibles)} offre(s) LinkedIn sans description")
    if a.dry:
        print("[DRY] rien n'a ete ecrit.")
        return 0
    if not cibles:
        return 0
    return _travail(cibles, a, queue_io)


def _cibles(q, limite=0):
    """Les id LinkedIn des offres sans description, sans doublon."""
    vus, cibles = set(), []
    for o in q:
        if "linkedin.com" not in (o.get("url") or ""):
            continue
        if (o.get("description") or "").strip():
            continue
        jid = job_id(o.get("url"))
        if jid and jid not in vus:
            vus.add(jid)
            cibles.append(jid)
    return cibles[:limite] if limite else cibles


def _ecrire(textes, queue_io, attente=180):
    """Pose les textes dans la file, sous verrou, sur l'etat RELU.

    L'offre est retrouvee par son id LinkedIn, jamais par sa position : entre
    l'instantane et l'ecriture, un scan a pu inserer, supprimer ou reordonner.
    Une offre qui a recu une description entre-temps n'est pas ecrasee. Une
    offre disparue est simplement ignoree."""
    from ats_match import fit_detail
    import datetime

    ecrites, delta = 0, []
    with queue_io.transaction(attente=attente) as q:
        for o in q:
            if "linkedin.com" not in (o.get("url") or ""):
                continue
            # Marquee, pas retiree : la suppression reste a audit_dispo, qui
            # epargne le suivi (motif « deja marquee morte »).
            if job_id(o.get("url")) in FERMEES and o.get("link_status") != "EXPIREE":
                o["link_status"] = "EXPIREE"
                o["ls_check"] = datetime.date.today().isoformat()
                continue
            if (o.get("description") or "").strip():
                continue
            t = textes.get(job_id(o.get("url")))
            if not t:
                continue
            avant = o.get("fit")
            o["description"] = t
            # re-score OBLIGATOIRE : sans lui l'offre garde le fit calcule sans description
            o["fit"], o["exp_requise"], o["fit_fin"] = fit_detail(
                f"{o.get('poste', '')} {t}", o.get("poste", "")
            )
            ecrites += 1
            if isinstance(avant, int) and o["fit"] > avant:
                delta.append(
                    (
                        o["fit"] - avant,
                        avant,
                        o["fit"],
                        (o.get("entreprise") or "")[:24],
                        (o.get("poste") or "")[:40],
                    )
                )
    return ecrites, delta


def _travail(cibles, a, queue_io):
    import httpx

    ecrites, delta = 0, []
    # Textes lus mais pas encore poses. Si la file est occupee au moment
    # d'ecrire un lot, ils attendent le suivant au lieu d'etre perdus.
    en_attente = {}
    faits = 0
    with httpx.Client(follow_redirects=True) as client:
        for debut in range(0, len(cibles), a.lot):
            lot = cibles[debut : debut + a.lot]
            with cf.ThreadPoolExecutor(max_workers=a.workers) as ex:
                futs = {ex.submit(description, jid, client): jid for jid in lot}
                for f in cf.as_completed(futs):
                    t = f.result()
                    if t:
                        en_attente[futs[f]] = t
                    faits += 1
                    if faits % 50 == 0:
                        print(f"  … {faits}/{len(cibles)}")
            try:
                n, d = _ecrire(en_attente, queue_io)
            except queue_io.VerrouIndisponible as e:
                print(f"  ! lot non ecrit, reporte au suivant : {e}")
                continue
            ecrites += n
            delta += d
            en_attente = {}
            print(f"  ✓ lot ecrit · {ecrites} descriptions posees au total")
    if en_attente:
        # Derniere chance, avec une attente longue : c'est le seul moment ou
        # un refus perdrait vraiment du travail.
        try:
            n, d = _ecrire(en_attente, queue_io, attente=900)
            ecrites += n
            delta += d
        except queue_io.VerrouIndisponible as e:
            print(f"! {len(en_attente)} descriptions lues mais NON ecrites : {e}")
            print("  relancer le programme les relira.")
            return 3
    remontes = len(delta)
    print(
        f"\n{ecrites} description(s) recuperee(s) sur {len(cibles)} — {remontes} offres remontent en fit"
    )
    if FERMEES:
        print(f"  {len(FERMEES)} offre(s) fermee(s) reperee(s) au passage — marquees EXPIREE")
    # Un echec n'est pas un verdict : dire combien de fois LinkedIn nous a
    # brides evite de conclure « ces annonces n'ont pas de description ».
    if BRIDAGES["n"]:
        print(f"   ({BRIDAGES['n']} bridage(s) 429 rencontre(s) — relancer ramassera le reste)")
    manquantes = len(cibles) - ecrites
    if manquantes:
        print(
            f"   {manquantes} offre(s) restent sans description : relancer "
            f"le programme, il ne reprend que celles-la."
        )
    for d, av, ap_, e, p in sorted(delta, reverse=True)[:10]:
        print(f"   +{d}  fit {av} -> {ap_}  {e:26} {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
