#!/usr/bin/env python3
"""resolve_offer_links.py — Remplace les liens « page carriere » par le lien de
L'OFFRE elle-meme.

Pourquoi : dans l'app, cliquer le lien d'une offre curatee ouvrait la page
d'accueil ou le portail carrieres de la societe, pas l'annonce. Le lien direct
n'a jamais existe pour ces entrees : elles ont ete creees a partir du nom de la
societe. Ce programme va le CHERCHER, en naviguant le site comme le ferait un
humain — via web_nav.find_offer, qui detecte l'ATS, utilise le champ de
recherche puis fouille les listes.

Le nouveau lien n'est ecrit que s'il est PLUS PRECIS que l'ancien (segment de
chemin en plus, identifiant, ou requete). L'ancien est conserve dans `url_home`
pour pouvoir revenir en arriere.

CAPTCHA : jamais contourne. Une page qui en presente un est notee et sautee.

Run :
  python resolve_offer_links.py --dry              # montre sans rien ecrire
  python resolve_offer_links.py --limit 20
  python resolve_offer_links.py --headed           # navigateur visible
"""

import argparse
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

HERE = Path(__file__).resolve().parent
QUEUE = HERE / "apply_queue.json"
PROFIL = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "apply_runner_chrome"

# Meme regle que l'app (JobHunter._marque_lien) : un lien d'offre porte toujours
# un identifiant, et ne se termine jamais par un mot de rubrique.
PAS_DIRECT = {"HOMEPAGE", "CAREERS_PORTAL", "OTHER", "RECHERCHE", "BOARD_SEARCH"}
RUBRIQUES = {
    "careers",
    "career",
    "carrieres",
    "carrières",
    "recrutement",
    "recruitment",
    "jobs",
    "job",
    "offres",
    "emplois",
    "emploi",
    "vacancies",
    "opportunities",
    "nous-rejoindre",
    "join-us",
}


def specificite(u):
    d = urlparse(str(u) or "")
    seg = [c for c in (d.path or "").split("/") if c]
    return len(seg) + (2 if d.query else 0) + (1 if any(c.isdigit() for c in "".join(seg)) else 0)


# Hotes d'ATS : un lien vers eux reste legitime meme si le domaine change.
ATS_HOTES = (
    "lever.co",
    "greenhouse.io",
    "ashbyhq.com",
    "recruitee.com",
    "smartrecruiters.com",
    "myworkdayjobs.com",
    "talent-soft.com",
    "talentsoft.com",
    "icims.com",
    "taleo.net",
    "successfactors",
    "teamtailor.com",
    "welcometothejungle.com",
    "workable.com",
    "personio.de",
    "softgarden.io",
    "flatchr.io",
    "jobaffinity.fr",
)
# Motifs de page de RECHERCHE : elles paraissent precises (elles ont une
# requete) alors qu'elles n'ouvrent aucune offre.
# (\.\w+)? : l'extension comptait. « /job/results.htm » echappait a ce motif
# faute du point, et etait pris pour une annonce — le lien LinkedIn DIRECT se
# faisait remplacer par une page de resultats de recherche.
RX_RECHERCHE = re.compile(
    r"[?&](q|s|search|keyword|query|search_keyword)=|"
    r"/(catalogsearch|search|recherche|results?|listing|liste)"
    r"(\.\w+)?(/|$|\?)",
    re.I,
)
# Un lien d'offre porte un identifiant : un nombre long, ou un segment de slug
# assez long apres /job|/offre|/poste.
# Le slug d'une annonce porte un chiffre ou des tirets : « analyste-esg-h-f-12345 ».
# Sans cette exigence, « /job/results.htm » (11 caracteres) passait pour un
# identifiant d'offre.
RX_OFFRE = re.compile(
    r"/\d{4,}|\d{6,}"
    r"|/(jobs?|offres?|postes?|vacancy|vacature)/(?=[^/?#]{8,})[^/?#]*[-_\d][^/?#]*"
    # Lever et Ashby identifient l'annonce par un UUID, sans segment « /jobs/ » :
    # jobs.lever.co/agicap/97f57bd6-c156-42cd-… — 20 vraies annonces de la file
    # etaient rejetees faute de ce cas.
    r"|/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
    # Recruitee : /o/<slug-de-l-offre>
    r"|/o/[a-z0-9][a-z0-9-]{7,}",
    re.I,
)


def racine(host):
    """Domaine enregistrable approximatif : deux derniers labels, trois pour
    les suffixes composes (.co.uk, .com.au)."""
    h = (host or "").lower().replace("www.", "")
    parts = [x for x in h.split(".") if x]
    if len(parts) >= 3 and parts[-2] in ("co", "com", "org", "gov", "ac"):
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def accepte(depart, arrivee, titre, texte):
    """Le lien d'arrivee ouvre-t-il VRAIMENT l'offre attendue ?

    Le seul test de « plus precis » laissait passer : une page catalogue
    produits (samse.fr/catalogsearch/result/?q=…), une page de recherche
    (effektiv.fr/?search_keyword=…), une page de marque, et surtout un SAUT
    VERS UNE AUTRE SOCIETE — la navigation depuis AXA IM avait atterri sur
    group.bnpparibas.
    """
    if RX_RECHERCHE.search(arrivee):
        return False, "page de recherche"
    ha, hd = urlparse(arrivee).netloc, urlparse(depart).netloc
    meme_maison = racine(ha) == racine(hd) or any(x in ha.lower() for x in ATS_HOTES)
    # UN SITE CARRIERE VIT SOUVENT SUR UN AUTRE DOMAINE. Groupama recrute sur
    # groupama-gan-recrute.com, Bpifrance sur talents.bpifrance.fr : comparer
    # les domaines enregistrables rejetait ces sauts pourtant legitimes, et
    # c'etait la deuxieme cause d'echec mesuree. On accepte quand le domaine
    # d'arrivee reprend le nom de la maison de depart — « groupama » est dans
    # « groupama-gan-recrute ». Le saut AXA IM -> group.bnpparibas, lui, reste
    # refuse : « axa » n'apparait nulle part dans « bnpparibas ».
    if not meme_maison:
        marque = racine(hd).split(".")[0]
        if len(marque) >= 4 and marque in ha.lower().replace("-", ""):
            meme_maison = True
    if not meme_maison:
        return False, f"autre societe ({racine(ha)})"
    if not RX_OFFRE.search(arrivee):
        return False, "pas d'identifiant d'offre"
    # La page doit parler du poste : au moins deux mots significatifs du titre.
    mots = [m for m in re.findall(r"[a-zA-ZÀ-ÿ]{4,}", titre.lower())][:6]
    if mots:
        # Le slug de l'URL est un indice aussi fort que le corps de la page, et
        # il survit a un rendu JS incomplet.
        bas = ((texte or "") + " " + arrivee.replace("-", " ").replace("_", " ")).lower()
        trouves = sum(1 for m in mots if m in bas)
        if trouves < min(2, len(mots)):
            return False, f"autre offre que celle attendue ({trouves}/{len(mots)} mots du titre)"
    return True, "ok"


# Page qui LISTE les offres de la societe : pas l'annonce, mais un clic au lieu
# d'un site entier a explorer.
RX_BOARD = re.compile(r"^jobs\.|^careers\.|^recrutement\.|^emploi\.", re.I)
RX_CHEMIN_BOARD = re.compile(
    r"/(jobs?|careers?|carrieres|recrutement|offres|emplois|nous-rejoindre)(/|$)", re.I
)


def est_board(depart, arrivee):
    """Vrai si l'arrivee est le tableau d'offres de LA MEME societe."""
    ha, hd = urlparse(arrivee).netloc, urlparse(depart).netloc
    if racine(ha) != racine(hd) and not any(x in ha.lower() for x in ATS_HOTES):
        return False
    if RX_RECHERCHE.search(arrivee):
        return False
    chemin = urlparse(arrivee).path
    seg = [c for c in chemin.split("/") if c]
    if RX_CHEMIN_BOARD.search(chemin):
        return True
    # Un hote de recrutement ne suffit pas : recrutement.<x>/le-groupe/
    # nos-entreprises/... est une page corporate, pas un tableau d'offres.
    # On ne l'accepte que si le chemin reste court, donc proche de la racine.
    return bool(RX_BOARD.search(ha.replace("www.", ""))) and len(seg) <= 1


def generique(o):
    u = str(o.get("url") or "")
    if not u.startswith("http"):
        return False
    if str(o.get("url_type") or "") in PAS_DIRECT:
        return True
    d = urlparse(u)
    seg = [c for c in (d.path or "").split("/") if c]
    if seg and seg[-1].lower().strip("-_") in RUBRIQUES:
        return True
    return not (d.query or len(seg) >= 2 or any(c.isdigit() for c in "".join(seg)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="0 = toutes")
    ap.add_argument("--dry", action="store_true", help="n'ecrit rien")
    ap.add_argument("--headed", action="store_true", help="navigateur visible")
    ap.add_argument("--every", type=int, default=10, help="ecrit la queue tous les N")
    a = ap.parse_args()

    if not a.dry and not __import__("jutil").garder(QUEUE):
        return 3

    q = __import__("queue_io").charger(QUEUE, descriptions=False)
    cibles = [o for o in q if generique(o)]
    if a.limit:
        cibles = cibles[: a.limit]
    if not cibles:
        print("Aucun lien generique a resoudre.")
        return 0
    print(f"{len(cibles)} lien(s) a resoudre" + (" — SIMULATION" if a.dry else ""))

    from web_nav import analyze, dismiss_cookies, find_offer, get_sync_playwright, goto_careers

    sp, eng = get_sync_playwright("auto")
    PROFIL.mkdir(parents=True, exist_ok=True)
    resolus = captcha = echecs = boards = 0

    with sp() as p:

        def lance():
            c = p.chromium.launch_persistent_context(
                user_data_dir=str(PROFIL),
                channel="chrome",
                headless=not a.headed,
                args=["--no-first-run", "--no-default-browser-check"],
                no_viewport=True,
                timeout=90000,
            )
            c.set_default_timeout(12000)
            c.set_default_navigation_timeout(25000)
            return c, (c.pages[0] if c.pages else c.new_page())

        ctx, page = lance()
        for i, o in enumerate(cibles, 1):
            depart = str(o.get("url") or "")
            role = str(o.get("poste") or "")
            ent = str(o.get("entreprise") or "")[:26]
            note = ""
            try:
                page.goto(depart, timeout=25000, wait_until="domcontentloaded")
                dismiss_cookies(page)
                x = analyze(page)
                # On ne force RIEN : une page protegee est notee et sautee.
                if x.get("captcha") or x.get("blocked"):
                    captcha += 1
                    print(f"  [{i}/{len(cibles)}] BLOQUE   {ent:<28}{depart[:44]}")
                    continue
                # Depuis une home corporate, atteindre d'abord la section carrieres.
                if str(o.get("url_type") or "") == "HOMEPAGE":
                    goto_careers(page)
                    dismiss_cookies(page)
                # max_tries=1 : les reprises _unstick (cookies, scroll, reload)
                # triplaient le temps sans rien changer au resultat sur ces sites.
                find_offer(page, role_hint=role, max_tries=1)
                arrivee = page.url
            except Exception as e:
                arrivee, note = depart, type(e).__name__
                if "Closed" in note or "crash" in str(e).lower():
                    try:
                        ctx.close()
                    except Exception:
                        pass
                    try:
                        ctx, page = lance()
                        note += " (navigateur relance)"
                    except Exception:
                        print("  ✖ relance impossible — arret")
                        break

            ok, pourquoi = False, note or "aucune offre atteinte"
            if arrivee != depart and specificite(arrivee) > specificite(depart):
                try:
                    texte = page.inner_text("body")[:20000]
                except Exception:
                    texte = ""
                ok, pourquoi = accepte(depart, arrivee, role, texte)
            if ok:
                resolus += 1
                print(f"  [{i}/{len(cibles)}] RESOLU   {ent:<28}{arrivee[:64]}")
                if not a.dry:
                    o.setdefault("url_home", depart)
                    o["url"] = arrivee
                    o["url_type"] = "OFFRE_DIRECTE"
            elif arrivee != depart and est_board(depart, arrivee):
                # L'annonce precise n'existe souvent plus : ces entrees ont ete
                # creees a partir d'un NOM DE SOCIETE, pas d'une offre reelle.
                # Le tableau d'offres de la societe reste bien meilleur que sa
                # page d'accueil : un clic, au lieu d'un site a explorer.
                boards += 1
                print(f"  [{i}/{len(cibles)}] board    {ent:<28}{arrivee[:60]}")
                if not a.dry:
                    o.setdefault("url_home", depart)
                    o["url"] = arrivee
                    o["url_type"] = "CAREERS_PORTAL"
            else:
                echecs += 1
                print(f"  [{i}/{len(cibles)}] refuse   {ent:<28}{pourquoi}")

            if not a.dry and a.every and i % a.every == 0:
                __import__("jutil").jwrite(QUEUE, q)
                print(f"      … point de reprise ({resolus} resolus)")
            if i % 25 == 0:
                try:
                    vieux = page
                    page = ctx.new_page()
                    vieux.close()
                except Exception:
                    pass
        try:
            ctx.close()
        except Exception:
            pass

    if not a.dry:
        __import__("jutil").jwrite(QUEUE, q)
    print(
        f"\nBILAN : {resolus} offre(s) precise(s) · {boards} tableau(x) d'offres"
        f" · {echecs} inchange(s) · {captcha} bloque(s), non contournes"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
