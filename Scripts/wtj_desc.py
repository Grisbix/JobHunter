#!/usr/bin/env python3
"""wtj_desc.py — Recupere la DESCRIPTION des offres Welcome to the Jungle.

POURQUOI. J'avais annonce que WTJ etait « illisible, protection anti-bot ».
C'est plus nuance que ca : une fiche WTJ rend 200 sur une requete HTTP nue et
porte un bloc `<script type="application/ld+json">` de type JobPosting avec la
description complete — le balisage que WTJ publie pour Google. Pas besoin de
navigateur.

MAIS le debit est bride. Apres quelques fiches, CloudFront bascule l'IP sur un
challenge et repond 202 avec un corps vide, et il y reste : ralentir a 8 s entre
requetes n'a rien change (mesure faite). On ne contourne pas ce challenge. Le
script lit ce qu'il peut, s'arrete net des le premier 202, garde ce qui est lu.
En pratique : quelques fiches par passe, plusieurs passes espacees.

Re-score le fit ET exp_requise dans la foulee : une description ajoutee sans
re-scoring laisse l'offre a son ancien fit, calcule sur le seul titre.

Run :
  python wtj_desc.py --dry
  python wtj_desc.py --limit 20
  python wtj_desc.py
"""

import argparse
import concurrent.futures as cf
import html
import json
import re
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
QUEUE = HERE / "apply_queue.json"

UA = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    )
}


class Bloque(Exception):
    """WTJ a bascule l'IP en challenge anti-bot. On s'arrete, on ne contourne pas."""

    def __init__(self, code):
        super().__init__(f"WTJ repond {code} (challenge anti-bot)")


RX_LD = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)
RX_BALISE = re.compile(r"<[^>]+>")


def _texte(brut):
    """HTML de la description -> texte lisible, sauts de ligne preserves."""
    t = re.sub(r"<\s*(br|/p|/li|/div)\s*/?>", "\n", brut, flags=re.I)
    t = html.unescape(RX_BALISE.sub(" ", t))
    t = re.sub(r"[ \t\xa0]+", " ", t)
    return re.sub(r"\n{3,}", "\n\n", t).strip()


def description(url, client, essais=2):
    """Texte de l'annonce, ou "" si illisible. Ne leve jamais."""
    for n in range(essais):
        try:
            r = client.get(url, headers=UA, timeout=25)
        except Exception:
            time.sleep(1.5 * (n + 1))
            continue
        # 202 avec corps vide = challenge anti-bot CloudFront. Il n'arrive pas a
        # la premiere requete : WTJ sert quelques fiches, puis bascule l'IP en
        # challenge et l'y laisse (ralentir a 8 s entre requetes n'y change rien,
        # mesure faite). Ce n'est pas un code de succes, il ne faut surtout pas
        # le traiter comme tel : la description serait ecrasee par du vide.
        if r.status_code == 202 or r.status_code == 429:
            raise Bloque(r.status_code)
        if r.status_code != 200:
            return ""
        for bloc in RX_LD.findall(r.text):
            try:
                o = json.loads(bloc)
            except Exception:
                continue
            # Un seul bloc porte @type JobPosting ; l'autre est une FAQPage
            # sans description utile.
            if isinstance(o, dict) and o.get("@type") == "JobPosting":
                t = _texte(str(o.get("description") or ""))
                # Sous 200 caracteres c'est un resume d'interface, pas l'annonce
                return t if len(t) >= 200 else ""
        return ""
    return ""


def _cible(u):
    """Fiche d'offre WTJ, pas une recherche ni une page societe.

    Les URL /fr/jobs?query=… de la queue viennent du scan : elles n'ont aucune
    description a lire, les compter comme des echecs fausserait le bilan.
    """
    return "welcometothejungle.com" in u and "/jobs/" in u and "?query=" not in u


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=2)  # WTJ bride vite
    a = ap.parse_args()

    import queue_io

    if a.dry:
        return _travail(queue_io.charger(), a, ecrire=False)
    try:
        with queue_io.transaction() as q:
            return _travail(q, a, ecrire=True)
    except queue_io.VerrouIndisponible as e:
        print(f"! {e}")
        return 3


def _travail(q, a, ecrire):
    import httpx

    cibles = [
        i
        for i, o in enumerate(q)
        if _cible(o.get("url") or "") and not (o.get("description") or "").strip()
    ]
    if a.limit:
        cibles = cibles[: a.limit]
    print(f"{len(cibles)} fiche(s) WTJ sans description")
    if not ecrire:
        print("[DRY] rien n'a ete ecrit.")
        return 0
    if not cibles:
        return 0

    from ats_match import fit_detail

    textes = {}
    with httpx.Client(follow_redirects=True) as client:
        with cf.ThreadPoolExecutor(max_workers=a.workers) as ex:
            futs = {ex.submit(description, q[i]["url"], client): i for i in cibles}
            for n, f in enumerate(cf.as_completed(futs), 1):
                try:
                    textes[futs[f]] = f.result()
                except Bloque as e:
                    # Inutile de continuer : le challenge vaut pour l'IP entiere.
                    # Les descriptions deja lues sont conservees et ecrites.
                    print(
                        f"  ~ {e} — arret. Les {len(textes)} fiches deja lues "
                        f"sont conservees ; reessaie plus tard."
                    )
                    for autre in futs:
                        autre.cancel()
                    break
                if n % 20 == 0:
                    print(f"  … {n}/{len(cibles)}")

    ecrites = remontes = 0
    delta = []
    for i, t in textes.items():
        if not t:
            continue
        o = q[i]
        avant = o.get("fit")
        o["description"] = t
        o["fit"], o["exp_requise"], o["fit_fin"] = fit_detail(
            f"{o.get('poste', '')} {t}", o.get("poste", "")
        )
        ecrites += 1
        if isinstance(avant, int) and o["fit"] > avant:
            remontes += 1
            delta.append(
                (
                    o["fit"] - avant,
                    avant,
                    o["fit"],
                    (o.get("entreprise") or "")[:24],
                    (o.get("poste") or "")[:40],
                )
            )
    print(
        f"\n{ecrites} description(s) recuperee(s) sur {len(cibles)} — "
        f"{remontes} offres remontent en fit"
    )
    for d, av, ap_, e, p in sorted(delta, reverse=True)[:10]:
        print(f"   +{d}  fit {av} -> {ap_}  {e:26} {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
