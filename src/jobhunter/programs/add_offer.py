#!/usr/bin/env python3
"""add_offer.py — PASTE AN offer LINK → analyses the page (title, company,
description), scores (fit/ATS), adds to apply_queue.json, then generates CV + letter.

Run: python JobHunter.pyw add --url "https://…"           # analysis + queue + docs
     python JobHunter.pyw add --url "https://…" --no-docs # without CV/letter
"""

import argparse
import importlib
import re
import sys
import time
from urllib.parse import urlparse

from jobhunter import root as _racine
from jobhunter.navigation.browser import lancer as _lancer

sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]  # console : TextIOWrapper

HERE = _racine.scripts()
QUEUE = HERE / "apply_queue.json"

# title + company from the page (og: meta > h1 > <title>)
_META_JS = r"""
() => {
  const q=s=>document.querySelector(s);
  const og=p=>{const m=q(`meta[property="og:${p}"],meta[name="og:${p}"]`);return m?m.content:''};
  const h1=q('h1')?q('h1').innerText.trim():'';
  return {ogTitle:og('title'), ogSite:og('site_name'), h1:h1,
          title:(document.title||'').trim()};
}"""


def analyze_url(url):
    """Ouvre la page (headless TURBO) → {titre, entreprise, description}."""
    from jobhunter.navigation import (
        block_resources,
        dismiss_cookies,
        get_sync_playwright,
        robust_goto,
    )
    from jobhunter.programs.scrape_desc import _DESC_JS, _EXPAND_JS, CAP

    spw, eng = get_sync_playwright("auto")
    out = {"titre": "", "entreprise": "", "description": ""}
    with spw() as p:
        b = _lancer(p.chromium, headless=True)
        pg = b.new_page()
        block_resources(pg.context, images=False)
        g = robust_goto(pg, url, tries=2)
        if not g.get("ok"):
            b.close()
            return None, f"page inaccessible ({g.get('note', '')})"
        try:
            dismiss_cookies(pg)
        except Exception:
            pass
        time.sleep(1.2)
        for _ in range(2):
            try:
                if not pg.evaluate(_EXPAND_JS):
                    break
                time.sleep(0.7)
            except Exception:
                break
        try:
            m = pg.evaluate(_META_JS)
        except Exception:
            m = {}
        try:
            d = pg.evaluate(_DESC_JS, CAP)
            out["description"] = (d or {}).get("text", "").strip()
        except Exception:
            pass
        b.close()
    out["titre"], out["entreprise"] = titre_et_entreprise(m, url)
    if len(out["description"]) < 120:
        out["description"] = ""
    return out, "ok"


def titre_et_entreprise(m, url):
    """(job title, company) from the page's meta tags."""
    import html as _html

    # title: og:title > h1 > <title> — cleans entities + "| Site"
    t = _html.unescape((m.get("ogTitle") or m.get("h1") or m.get("title") or "").strip())
    t = re.split(r"\s*[|•]\s*", t)[0].strip()
    ent = _html.unescape((m.get("ogSite") or "").strip())
    # LinkedIn: "COMPANY hiring JOB in CITY" → split
    mm = re.match(r"^(.{2,50}?)\s+hiring\s+(.+?)(?:\s+in\s+.{2,60})?$", t, re.I)
    # French LinkedIn: "COMPANY recrute pour des postes de JOB (CITY)"
    mm = mm or re.match(
        r"^(.{2,50}?)\s+recrute\s+(?:pour\s+des\s+postes\s+de\s+|un\(?e?\)?\s+|une?\s+)?"
        r"(.+?)(?:\s+\([^()]{2,60}\))?$",
        t,
        re.I,
    )
    if mm:
        ent, t = mm.group(1).strip(), mm.group(2).strip()
    # boards: og:site_name = name of the site, not the employer
    if not ent or ent.lower() in (
        "linkedin",
        "indeed",
        "welcome to the jungle",
        "glassdoor",
        "hellowork",
        "apec",
    ):
        mm = re.search(r"(?:chez|at)\s+([A-Z][\w&' .-]{2,40})", t)
        # The site's own name, not its language subdomain ("fr.linkedin.com" gave "Fr").
        hote = urlparse(url).netloc.split(".")
        ent = mm.group(1).strip() if mm else (hote[-2] if len(hote) > 1 else hote[0]).title()
        # A LinkedIn job URL names the company: ".../jobs/view/<job>-at-<company>-<id>".
        lk = re.search(r"-at-([a-z0-9-]{2,60}?)-\d+/?$", urlparse(url).path)
        if not mm and lk and "linkedin" in urlparse(url).netloc:
            ent = lk.group(1).replace("-", " ").title()
    return t[:120] or "Offre sans titre", ent[:60]


def add_to_queue(url, meta):
    from jobhunter.programs.scrape_jobs import classify_domaine
    from jobhunter.sources import _mk, merge_into_queue

    o = _mk(
        meta["titre"],
        url,
        meta["entreprise"],
        source="ajout manuel",
        description=meta.get("description", ""),
    )
    o["domaine"] = classify_domaine(meta["titre"])
    r = merge_into_queue([o], dry=False)
    return r


def make_docs(url):
    """Generates CV + letter for the queue row of this URL, updates the links."""
    from jobhunter.storage import queue as queue_io

    # Explicit QUEUE: the tests replace this constant with a throwaway
    # file. Without it, charger() would read the real queue.
    q = queue_io.charger(QUEUE)  # descriptions reinjectees depuis descriptions.json
    x = next((v for v in q if v.get("url") == url), None)
    if not x:
        return "offre introuvable en queue"
    from jobhunter.documents import cv_une_page, tailor_letter, to_pdf

    offer = dict(
        company=x["entreprise"],
        role=x["poste"],
        offer_text=f"{x['poste']} {x.get('description', '')}",
        lieu=x.get("localisation") or "",
        missions=(x.get("description") or "")[:400],
        profil="",
        domaine=x.get("domaine", ""),
        rh=x.get("rh"),
    )
    from jobhunter.links import url_de as _url_of

    try:
        cv, pdf = cv_une_page(offer)
        if cv:
            x["cv"] = _url_of(pdf or cv)
            x["cv_variant"] = None
    except Exception as e:
        print(f"  ! cv: {type(e).__name__}")
    try:
        lt = tailor_letter(offer)
        if lt:
            pdf = to_pdf(lt)
            x["lettre"] = _url_of(pdf or lt)
    except Exception as e:
        print(f"  ! lettre: {type(e).__name__}")
    importlib.import_module("jobhunter.programs.util").jwrite(QUEUE, q)
    return "docs générés"


def main():
    # Inter-process lock: this program rewrites the ENTIRE queue. If
    # another one does it at the same time (scheduled task vs app), the last one
    # to write erases the other's work.
    if not importlib.import_module("jobhunter.programs.util").garder(QUEUE):
        return 3
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--no-docs", action="store_true")
    a = ap.parse_args()
    url = a.url.strip()
    if not url.startswith("http"):
        print("URL invalide.")
        return 1
    print(f"🔎 analyse {url[:80]}…")
    meta, note = analyze_url(url)
    if meta is None:
        print(f"✗ {note}")
        return 1
    print(f"  poste      : {meta['titre']}")
    print(f"  entreprise : {meta['entreprise']}")
    print(f"  description: {len(meta['description'])} car.")
    r = add_to_queue(url, meta)
    print(
        f"  queue      : +{r['added']} ({r['total']} total)"
        + (" — déjà présente (mise à jour desc)" if not r["added"] else "")
    )
    if not a.no_docs:
        print("  " + make_docs(url))
    print("✅ terminé — recharge l'app pour voir l'offre.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
