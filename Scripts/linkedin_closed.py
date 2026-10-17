#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""linkedin_closed.py — Retire de la queue les offres LinkedIn qui n'acceptent plus de candidature.

LinkedIn renvoie HTTP 200 meme pour une annonce fermee : le code de statut ne dit
RIEN. Seule l'API invite (jobs-guest, sans authentification) porte le marqueur
« No longer accepting applications ». C'est ce marqueur, et lui seul, qui autorise
la suppression.

Regle de prudence : on ne supprime que sur un signal POSITIF de fermeture.
Un timeout, une erreur reseau, un 429 ou une page inattendue laissent l'offre en
place — mieux vaut garder une offre morte qu'effacer une offre vivante.

Les offres retirees sont sauvegardees dans _supprimees_linkedin_<date>.json
(non versionne) : la suppression reste annulable.

PIEGE DE LOCALISATION. LinkedIn sert la page dans la langue du visiteur, et la
tournure francaise est PASSIVE : « Les candidatures ne sont plus acceptées ».
Un motif qui n'attend que la forme active (« n'accepte plus de candidature ») ou
que l'anglais rate TOUTES les annonces servies en francais — l'essentiel d'entre
elles depuis la France — et les declare ouvertes. Verifie sur 6 annonces
(3 fermees, 3 ouvertes) : 6/6 correctes, y compris a travers la variante
« mur de connexion » que LinkedIn sert apres quelques dizaines de requetes.
Cette variante porte bien le marqueur : elle n'est PAS aveugle.

La memoire persistante (_linkedin_etat.json) evite de reinterroger ce qui est
deja tranche. Si le detecteur change, PURGER ce fichier : ses verdicts ont ete
rendus par l'ancienne version.

Run :
  python linkedin_closed.py --dry                      # compte seulement
  python linkedin_closed.py --workers 1 --pause 20     # passe lente
  python linkedin_closed.py                            # supprime pour de bon
"""

import sys
import re
import json
import time
import argparse
import datetime as _dt
import concurrent.futures as cf
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

HERE = Path(__file__).resolve().parent
QUEUE = HERE / "apply_queue.json"
API = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{}"
UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
}

# L'identifiant est le dernier nombre long de /jobs/view/<slug>-<id>
RX_ID = re.compile(r"/jobs/view/(?:[^/?#]*?-)?(\d{6,})")
# Marqueur de fermeture, FR et EN. LinkedIn sert l'une ou l'autre selon la locale.
# La tournure FRANCAISE est PASSIVE — « Les candidatures ne sont plus acceptées » —
# et non « n'accepte plus de candidature ». Attendre la forme active revenait a
# rater toutes les annonces servies en francais, c'est-a-dire l'essentiel d'entre
# elles depuis la France.
RX_FERME = re.compile(
    r"no longer accepting applications"
    r"|candidatures? ne sont plus accept"
    r"|ne sont plus accept[ée]e?s?"
    r"|n[e']accepte plus de candidature"
    r"|ne recrute plus"
    r"|cette offre n[e']est plus",
    re.I,
)

# Variante « mur de connexion » servie apres quelques dizaines de requetes invite.
# Elle est identique pour une offre ouverte et une offre fermee : illisible.
RX_MUR = re.compile(r"sign-in-modal|authwall|guest-homepage", re.I)
# Presence d'un vrai bouton de candidature = page reellement lisible
RX_POSTULER = re.compile(r"apply-button|jobs-apply-button|sign-up-modal__apply", re.I)

OUVERT, FERME, INCONNU = "ouvert", "ferme", "inconnu"


def job_id(url):
    m = RX_ID.search(str(url or ""))
    return m.group(1) if m else None


def etat(jid, client, essais=2):
    """OUVERT / FERME / INCONNU. INCONNU protege : il n'entraine aucune suppression."""
    for n in range(essais):
        try:
            r = client.get(API.format(jid), headers=UA, timeout=15)
        except Exception:
            time.sleep(1.5 * (n + 1))
            continue
        if r.status_code == 429:  # LinkedIn nous freine : on ralentit
            time.sleep(5 * (n + 1))
            continue
        if r.status_code == 404:
            # l'annonce n'existe plus du tout — mais LinkedIn sert aussi des 404
            # transitoires ; on ne supprime pas la-dessus, on le signale
            return INCONNU
        if r.status_code != 200:
            time.sleep(1.0)
            continue
        h = r.text
        if len(h) < 200:  # reponse tronquee : on ne conclut pas
            return INCONNU
        if RX_FERME.search(h):
            return FERME
        # PIEGE : passe un certain volume, LinkedIn sert une variante « mur de
        # connexion » IDENTIQUE pour une offre ouverte et une offre fermee — le
        # marqueur de fermeture en est absent. Conclure « ouvert » sur cette
        # page reviendrait a certifier une offre qu'on n'a pas pu lire.
        if RX_MUR.search(h) and not RX_POSTULER.search(h):
            return INCONNU
        return OUVERT
    return INCONNU


ETAT = HERE / "_linkedin_etat.json"  # memoire des verifications (non versionne)
SUIVI = HERE / "suivi.json"  # candidatures : statut, note, date


def _oid_offre(offre):
    """Meme cle que l'app et que suivi.json : « entreprise|poste »."""
    return f"{(offre.get('entreprise') or '').strip()}|{(offre.get('poste') or '').strip()}"


def _oids_suivis():
    """Offres portant une trace de candidature. Intouchables."""
    try:
        return set(__import__("suivi_io").charger(SUIVI))
    except (FileNotFoundError, ValueError):
        return set()


def _memoire():
    try:
        return json.loads(ETAT.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _frais(entree, jours):
    """Une verification concluante de moins de `jours` jours est reutilisable."""
    if not entree or entree.get("etat") == INCONNU:
        return False
    try:
        vu = _dt.date.fromisoformat(entree["date"])
    except Exception:
        return False
    return (_dt.date.today() - vu).days < jours


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true", help="compte sans rien supprimer")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--limit", type=int, default=0, help="n'examiner que les N premieres")
    ap.add_argument(
        "--pause",
        type=float,
        default=0.0,
        help="secondes entre deux requetes (contourne la limitation invite)",
    )
    ap.add_argument(
        "--jours",
        type=int,
        default=7,
        help="reutilise une verification concluante de moins de N jours",
    )
    ap.add_argument(
        "--abandon",
        type=int,
        default=40,
        help="arrete apres N indeterminees d'affilee : LinkedIn nous a coupes",
    )
    a = ap.parse_args()

    import httpx

    # En --dry on n'ecrit pas la queue : prendre le verrou d'ecriture ferait
    # attendre 3 min derriere une generation de documents, pour rien. Les
    # ecritures etant atomiques (tmp + replace), la lecture reste coherente.
    if not a.dry and not __import__("jutil").garder(QUEUE):
        return 3

    q = __import__("queue_io").charger(QUEUE, descriptions=False)
    cibles = []
    for i, o in enumerate(q):
        if "linkedin.com" not in (o.get("url") or ""):
            continue
        jid = job_id(o.get("url"))
        if jid:
            cibles.append((i, jid, o))
    # Reutilise les verifications concluantes recentes : LinkedIn bride l'acces
    # invite, donc chaque requete compte. On ne rejoue que l'indetermine.
    memo = _memoire()
    res, a_faire = {}, []
    for i, jid, _ in cibles:
        e = memo.get(jid)
        if _frais(e, a.jours):
            res[i] = e["etat"]
        else:
            a_faire.append((i, jid))
    if a.limit:
        a_faire = a_faire[: a.limit]
    print(
        f"{len(cibles)} offre(s) LinkedIn — {len(res)} deja connues, "
        f"{len(a_faire)} a verifier ({a.workers} en parallele, pause {a.pause}s)"
    )

    coupe = 0
    with httpx.Client(follow_redirects=True) as client:
        if a.workers <= 1 or a.pause:
            # marche lente : une requete a la fois, pause entre chaque
            for n, (i, jid) in enumerate(a_faire, 1):
                v = etat(jid, client)
                res[i] = v
                memo[jid] = {"etat": v, "date": str(_dt.date.today())}
                coupe = coupe + 1 if v == INCONNU else 0
                if coupe >= a.abandon:
                    print(
                        f"  ! {coupe} indeterminees d'affilee — LinkedIn a coupe l'acces "
                        f"invite. Arret a {n}/{len(a_faire)}, relance plus tard."
                    )
                    break
                if n % 50 == 0:
                    print(f"  … {n}/{len(a_faire)}")
                if a.pause:
                    time.sleep(a.pause)
        else:
            with cf.ThreadPoolExecutor(max_workers=a.workers) as ex:
                futs = {ex.submit(etat, jid, client): (i, jid) for i, jid in a_faire}
                for n, f in enumerate(cf.as_completed(futs), 1):
                    i, jid = futs[f]
                    res[i] = f.result()
                    memo[jid] = {"etat": res[i], "date": str(_dt.date.today())}
                    if n % 200 == 0:
                        print(f"  … {n}/{len(a_faire)}")
    ETAT.write_text(json.dumps(memo, ensure_ascii=False, indent=1), encoding="utf-8")

    # NE JAMAIS supprimer une offre a laquelle l'utilisateur a candidate. Une annonce
    # ferme APRES qu'on y a postule : c'est meme le cas le plus frequent. Sans ce
    # garde-fou, l'outil effacait en priorite les offres du suivi — la trace de la
    # candidature devenait orpheline et disparaissait de l'app. C'est arrive pour
    # de vrai (Volkswagen Financial Services, candidature du 11/07).
    fermes, proteges = [], 0
    suivis = _oids_suivis()
    for i, v in res.items():
        if v != FERME:
            continue
        if _oid_offre(q[i]) in suivis:
            proteges += 1
            continue
        fermes.append(i)
    inconnus = sum(1 for v in res.values() if v == INCONNU)
    if proteges:
        print(f"  {proteges} offre(s) fermee(s) CONSERVEE(S) : tu y as candidate")
    print(f"\n  ouvertes : {sum(1 for v in res.values() if v == OUVERT)}")
    print(f"  fermees  : {len(fermes)}")
    print(f"  indeterminees (conservees par prudence) : {inconnus}")

    for i in fermes[:10]:
        o = q[i]
        print(f"    - {(o.get('entreprise') or '')[:26]:28} {(o.get('poste') or '')[:46]}")
    if len(fermes) > 10:
        print(f"    … et {len(fermes) - 10} autres")

    if a.dry:
        print("\n[DRY] rien n'a ete supprime.")
        return 0
    if not fermes:
        print("\nRien a supprimer.")
        return 0

    perdus = {i for i in fermes}
    sauv = HERE / f"_supprimees_linkedin_{_dt.date.today()}.json"
    sauv.write_text(
        json.dumps([q[i] for i in sorted(perdus)], ensure_ascii=False, indent=1), encoding="utf-8"
    )
    neuf = [o for i, o in enumerate(q) if i not in perdus]
    __import__("jutil").jwrite(QUEUE, neuf)  # ecriture atomique (tmp + replace)
    print(f"\n{len(perdus)} offre(s) retiree(s). Sauvegarde : {sauv.name}")
    print(f"Queue : {len(q)} -> {len(neuf)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
