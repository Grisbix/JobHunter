#!/usr/bin/env python3
"""audit_fraicheur.py — Combien d'offres de la file n'existent plus ? Par source.

POURQUOI. « Beaucoup d'offres n'existent plus. » Avant de supprimer quoi que ce
soit il faut savoir OU est la pourriture, et le savoir par la mesure.

Deux pieges que ce script prend au serieux :

1. HTTP 200 NE VEUT PAS DIRE VIVANT. Wizbii sert 200 sur une annonce publiee en
   2015 ; LinkedIn sert 200 sur une annonce fermee. Le code de statut ne tranche
   que dans un sens : 404/410 = morte. Pour le reste il faut un marqueur dans la
   page.

2. Un echec reseau n'est pas une preuve de mort. Timeout, 429, anti-bot : la
   verdict est « inconnu », jamais « morte ».

Ne supprime RIEN. Echantillonne, mesure, rapporte. La suppression est un autre
programme et une autre decision.

Run :
  python JobHunter.pyw audit_fraicheur                 # 12 offres par source
  python JobHunter.pyw audit_fraicheur --par-source 30
  python JobHunter.pyw audit_fraicheur --source indeed
"""

import argparse
import collections
import concurrent.futures as cf
import random
import re
import sys
from urllib.parse import urlparse

from jobhunter import racine as _racine

HERE = _racine.scripts()

sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)  # type: ignore[union-attr]  # console : TextIOWrapper

UA = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
}

# Marqueurs de FERMETURE, par famille de site. Un seul de ces motifs suffit a
# declarer l'offre morte ; leur absence ne prouve pas qu'elle est vivante.
RX_FERMEE = re.compile(
    r"candidatures? ne sont plus accept"  # LinkedIn FR (passif)
    r"|no longer accepting applications"  # LinkedIn EN
    r"|cette offre (?:n'est plus|a expir)"
    r"|offre (?:expiree|expirée|pourvue|clôturée|cloturee)"
    r"|annonce (?:expiree|expirée|n'est plus disponible)"
    r"|this (?:job|position|vacancy) (?:is )?(?:no longer|has expired|is closed)"
    r"|position (?:has been )?(?:filled|closed)"
    r"|n'est plus disponible|plus en ligne|offre introuvable"
    r"|job posting (?:is )?(?:expired|closed|not found)",
    re.I,
)

# Page anti-bot : verdict INCONNU, surtout pas « morte ».
RX_ANTIBOT = re.compile(
    r"captcha|are you a robot|vérifiez que vous|verifying you are human"
    r"|cloudflare|access denied|request unsuccessful|too many requests",
    re.I,
)


RX_SCRIPT = re.compile(r"<(script|style|template)\b.*?</\1>", re.S | re.I)
RX_BALISE = re.compile(r"<[^>]+>")


def visible(html_):
    """Texte AFFICHE, scripts retires.

    Indispensable : Talent.com embarque dans un <script> un dictionnaire de
    traductions qui contient « Les candidatures ne sont plus acceptées » sur
    CHAQUE page, morte ou vivante. Chercher le marqueur dans le HTML brut
    declarait mortes 45 offres sur 45 — un tableau i18n pris pour un message.
    """
    import html as _h

    t = RX_SCRIPT.sub(" ", html_)
    t = _h.unescape(RX_BALISE.sub(" ", t))
    return re.sub(r"\s+", " ", t)


def hote(u):
    return urlparse(u or "").netloc.replace("www.", "").lower()


def verdict(url, client):
    """('morte'|'vivante'|'inconnu', detail). Ne leve jamais."""
    # LinkedIn : la page publique sert un mur anti-bot des la deuxieme requete,
    # ce qui rendait l'echantillon illisible (11 « inconnu » sur 12). L'API
    # invite, elle, repond et porte le marqueur de fermeture. C'est le meme
    # point d'acces que linkedin_closed.py.
    if "linkedin.com" in url:
        from jobhunter.programmes.linkedin_closed import API, RX_FERME, job_id

        jid = job_id(url)
        if not jid:
            return "inconnu", "identifiant illisible"
        try:
            r = client.get(API.format(jid), headers=UA, timeout=25)
        except Exception as e:
            return "inconnu", type(e).__name__
        if r.status_code in (404, 410):
            return "morte", f"http {r.status_code}"
        if r.status_code != 200:
            return "inconnu", f"http {r.status_code}"
        return (
            ("morte", "marqueur de fermeture")
            if RX_FERME.search(r.text)
            else ("vivante", "api invite")
        )
    try:
        r = client.get(url, headers=UA, timeout=25)
    except Exception as e:
        return "inconnu", type(e).__name__
    code = r.status_code
    if code in (404, 410):
        return "morte", f"http {code}"
    if code == 403 or code == 202:
        # 403 = mur anti-bot (Indeed), 202 = challenge CloudFront (WTJ).
        # Aucune information sur l'offre elle-meme.
        return "inconnu", f"http {code} (mur)"
    if code != 200:
        return "inconnu", f"http {code}"
    vu = visible(r.text)
    if RX_FERMEE.search(vu):
        return "morte", "marqueur de fermeture"
    if RX_ANTIBOT.search(vu[:4000]):
        return "inconnu", "page anti-bot"
    if len(r.text) < 1500:
        return "inconnu", "page quasi vide"
    return "vivante", f"http 200, {len(r.text)} o"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--par-source", type=int, default=12, help="taille de l'echantillon par domaine"
    )
    ap.add_argument("--source", default="", help="ne tester qu'un domaine (sous-chaine)")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument(
        "--graine", type=int, default=1, help="graine aleatoire : un meme tirage est reproductible"
    )
    a = ap.parse_args()

    import httpx

    from jobhunter.stockage import file as queue_io

    q = queue_io.charger(descriptions=False)  # les textes ne servent pas ici

    par_hote = collections.defaultdict(list)
    for o in q:
        u = o.get("url") or ""
        if u.startswith("http"):
            par_hote[hote(u)].append(o)

    rnd = random.Random(a.graine)
    lots = []
    for h, offres in sorted(par_hote.items(), key=lambda t: -len(t[1])):
        if a.source and a.source.lower() not in h:
            continue
        ech = offres if len(offres) <= a.par_source else rnd.sample(offres, a.par_source)
        lots.append((h, len(offres), ech))

    total_offres = sum(n for _, n, _ in lots)
    total_test = sum(len(e) for _, _, e in lots)
    print(f"{len(lots)} source(s) · {total_offres} offres · {total_test} testees\n")

    lignes = []
    with httpx.Client(follow_redirects=True) as client:
        for h, n, ech in lots:
            res = collections.Counter()
            details = collections.Counter()
            with cf.ThreadPoolExecutor(max_workers=a.workers) as ex:
                for v, d in ex.map(lambda o: verdict(o["url"], client), ech):
                    res[v] += 1
                    details[d] += 1
            testes = sum(res.values())
            mortes = res["morte"]
            connus = res["morte"] + res["vivante"]
            # Le taux se calcule sur ce qu'on a pu TRANCHER. Diviser par
            # l'echantillon entier ferait passer un mur anti-bot pour une preuve
            # de bonne sante.
            taux = (100.0 * mortes / connus) if connus else None
            lignes.append((h, n, testes, res, taux, details))
            t = "  n/a" if taux is None else f"{taux:5.1f}%"
            print(
                f"  {h:32} {n:5} offres · {testes:3} testees · "
                f"mortes {mortes:3} · vivantes {res['vivante']:3} · "
                f"inconnu {res['inconnu']:3} · {t} mortes"
            )
            for d, c in details.most_common(3):
                print(f"        {c:3}x {d}")

    # On n'extrapole QUE sur un echantillon reellement tranche. Avec une ou deux
    # offres decidees, un taux de 100 % ne veut rien dire : c'est ainsi que
    # LinkedIn, dont 11 tests sur 12 avaient tape un mur anti-bot, se retrouvait
    # credite de 1344 offres mortes sur la foi d'une seule.
    MINI = 5
    print(f"\n=== estimation (extrapolee seulement si >= {MINI} offres tranchees) ===")
    total_est = 0
    indecis = 0
    for h, n, testes, res, taux, _ in lignes:
        connus = res["morte"] + res["vivante"]
        if taux is None or connus < MINI:
            indecis += n
            print(f"  {h:32} {n:5} offres — indeterminable ({connus} tranchee(s) sur {testes})")
            continue
        est = int(round(n * taux / 100.0))
        total_est += est
        print(f"  {h:32} ~{est:5} mortes sur {n}")
    print(
        f"\n  ~{total_est} mortes estimees · {indecis} offres indeterminables "
        f"· {total_offres} au total"
    )
    print("\nAucune suppression : ce programme mesure seulement.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
