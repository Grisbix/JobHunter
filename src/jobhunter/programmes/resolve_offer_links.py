#!/usr/bin/env python3
"""resolve_offer_links.py — Replaces the "career page" links with the link of THE OFFER
itself.

Why: in the app, clicking the link of a curated offer opened the company's home page or
careers portal, not the posting. The direct link never existed for these entries: they
were created from the company's name. This program goes LOOKING for it, navigating the
site as a human would — through web_nav.find_offer, which detects the ATS, uses the
search field then digs through the lists.

The new link is only written if it is MORE PRECISE than the old one (an extra path
segment, an identifier, or a query). The old one is kept in `url_home` so as to be
able to go back.

CAPTCHA: never bypassed. A page that presents one is noted and skipped.

Run:
  python JobHunter.pyw resolve_offer_links --dry              # shows without writing anything
  python JobHunter.pyw resolve_offer_links --limit 20
  python JobHunter.pyw resolve_offer_links --headed           # visible browser
"""

import argparse
import importlib
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

from jobhunter import racine as _racine

sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)  # type: ignore[union-attr]  # console : TextIOWrapper

HERE = _racine.scripts()
QUEUE = HERE / "apply_queue.json"
PROFIL = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "apply_runner_chrome"

# Same rule as the app (JobHunter._marque_lien): an offer link always carries
# an identifier, and never ends with a section word.
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


# ATS hosts: a link to them stays legitimate even if the domain changes.
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
# SEARCH page patterns: they look precise (they have a
# query) while they open no offer.
# (\.\w+)?: the extension counted. "/job/results.htm" escaped this pattern
# for lack of the dot, and was taken for a posting — the DIRECT LinkedIn link
# got replaced by a search results page.
RX_RECHERCHE = re.compile(
    r"[?&](q|s|search|keyword|query|search_keyword)=|"
    r"/(catalogsearch|search|recherche|results?|listing|liste)"
    r"(\.\w+)?(/|$|\?)",
    re.I,
)
# An offer link carries an identifier: a long number, or a slug segment
# long enough after /job|/offre|/poste.
# A posting's slug carries a digit or dashes: "analyste-esg-h-f-12345".
# Without this requirement, "/job/results.htm" (11 characters) passed for an
# offer identifier.
RX_OFFRE = re.compile(
    r"/\d{4,}|\d{6,}"
    r"|/(jobs?|offres?|postes?|vacancy|vacature)/(?=[^/?#]{8,})[^/?#]*[-_\d][^/?#]*"
    # Lever and Ashby identify the posting by a UUID, without a "/jobs/" segment:
    # jobs.lever.co/agicap/97f57bd6-c156-42cd-… — 20 real postings of the queue
    # were rejected for lack of this case.
    r"|/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
    # Recruitee: /o/<slug-of-the-offer>
    r"|/o/[a-z0-9][a-z0-9-]{7,}",
    re.I,
)


def racine(host):
    """Approximate registrable domain: last two labels, three for compound suffixes
    (.co.uk, .com.au)."""
    h = (host or "").lower().replace("www.", "")
    parts = [x for x in h.split(".") if x]
    if len(parts) >= 3 and parts[-2] in ("co", "com", "org", "gov", "ac"):
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def accepte(depart, arrivee, titre, texte):
    """Does the arrival link REALLY open the expected offer?

    The "more precise" test alone let through: a product catalogue page
    (samse.fr/catalogsearch/result/?q=…), a search page
    (effektiv.fr/?search_keyword=…), a brand page, and above all a JUMP TO ANOTHER
    COMPANY — the navigation from AXA IM had landed on group.bnpparibas.
    """
    if RX_RECHERCHE.search(arrivee):
        return False, "page de recherche"
    ha, hd = urlparse(arrivee).netloc, urlparse(depart).netloc
    meme_maison = racine(ha) == racine(hd) or any(x in ha.lower() for x in ATS_HOTES)
    # A CAREER SITE OFTEN LIVES ON ANOTHER DOMAIN. Groupama recruits on
    # groupama-gan-recrute.com, Bpifrance on talents.bpifrance.fr: comparing
    # the registrable domains rejected these jumps, which are legitimate, and
    # it was the second measured cause of failure. We accept when the arrival
    # domain contains the name of the starting company — "groupama" is in
    # "groupama-gan-recrute". The jump AXA IM -> group.bnpparibas, on the other hand, stays
    # refused: "axa" appears nowhere in "bnpparibas".
    if not meme_maison:
        marque = racine(hd).split(".")[0]
        if len(marque) >= 4 and marque in ha.lower().replace("-", ""):
            meme_maison = True
    if not meme_maison:
        return False, f"autre societe ({racine(ha)})"
    if not RX_OFFRE.search(arrivee):
        return False, "pas d'identifiant d'offre"
    # The page must talk about the job: at least two significant words of the title.
    mots = [m for m in re.findall(r"[a-zA-ZÀ-ÿ]{4,}", titre.lower())][:6]
    if mots:
        # The URL slug is a clue as strong as the page body, and
        # it survives an incomplete JS render.
        bas = ((texte or "") + " " + arrivee.replace("-", " ").replace("_", " ")).lower()
        trouves = sum(1 for m in mots if m in bas)
        if trouves < min(2, len(mots)):
            return False, f"autre offre que celle attendue ({trouves}/{len(mots)} mots du titre)"
    return True, "ok"


# Page that LISTS the company's offers: not the posting, but one click instead
# of a whole site to explore.
RX_BOARD = re.compile(r"^jobs\.|^careers\.|^recrutement\.|^emploi\.", re.I)
RX_CHEMIN_BOARD = re.compile(
    r"/(jobs?|careers?|carrieres|recrutement|offres|emplois|nous-rejoindre)(/|$)", re.I
)


def est_board(depart, arrivee):
    """True if the arrival is the job board of THE SAME company."""
    ha, hd = urlparse(arrivee).netloc, urlparse(depart).netloc
    if racine(ha) != racine(hd) and not any(x in ha.lower() for x in ATS_HOTES):
        return False
    if RX_RECHERCHE.search(arrivee):
        return False
    chemin = urlparse(arrivee).path
    seg = [c for c in chemin.split("/") if c]
    if RX_CHEMIN_BOARD.search(chemin):
        return True
    # A recruiting host is not enough: recrutement.<x>/le-groupe/
    # nos-entreprises/... is a corporate page, not a job board.
    # We only accept it if the path stays short, hence close to the root.
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

    if not a.dry and not importlib.import_module("jobhunter.programmes.jutil").garder(QUEUE):
        return 3

    q = importlib.import_module("jobhunter.stockage.file").charger(QUEUE, descriptions=False)
    cibles = [o for o in q if generique(o)]
    if a.limit:
        cibles = cibles[: a.limit]
    if not cibles:
        print("Aucun lien generique a resoudre.")
        return 0
    print(f"{len(cibles)} lien(s) a resoudre" + (" — SIMULATION" if a.dry else ""))

    from jobhunter.navigation import (
        analyze,
        dismiss_cookies,
        find_offer,
        get_sync_playwright,
        goto_careers,
    )

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
                # We force NOTHING: a protected page is noted and skipped.
                if x.get("captcha") or x.get("blocked"):
                    captcha += 1
                    print(f"  [{i}/{len(cibles)}] BLOQUE   {ent:<28}{depart[:44]}")
                    continue
                # From a corporate home, first reach the careers section.
                if str(o.get("url_type") or "") == "HOMEPAGE":
                    goto_careers(page)
                    dismiss_cookies(page)
                # max_tries=1: the _unstick retries (cookies, scroll, reload)
                # tripled the time without changing anything to the result on these sites.
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
                # The precise posting often no longer exists: these entries were
                # created from a COMPANY NAME, not from a real offer.
                # The company's job board is still much better than its
                # home page: one click, instead of a site to explore.
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
                importlib.import_module("jobhunter.programmes.jutil").jwrite(QUEUE, q)
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
        importlib.import_module("jobhunter.programmes.jutil").jwrite(QUEUE, q)
    print(
        f"\nBILAN : {resolus} offre(s) precise(s) · {boards} tableau(x) d'offres"
        f" · {echecs} inchange(s) · {captcha} bloque(s), non contournes"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
