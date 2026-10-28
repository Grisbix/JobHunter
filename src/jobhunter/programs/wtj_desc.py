#!/usr/bin/env python3
"""wtj_desc.py — Fetches the DESCRIPTION of Welcome to the Jungle offers.

WHY. I had announced that WTJ was "unreadable, anti-bot protection". It is more
nuanced than that: a WTJ posting returns 200 on a bare HTTP request and carries a
`<script type="application/ld+json">` block of type JobPosting with the full
description — the markup WTJ publishes for Google. No need for a browser.

BUT the rate is throttled. After a few postings, CloudFront switches the IP to a
challenge and answers 202 with an empty body, and it stays there: slowing down to 8 s
between requests changed nothing (measured). We do not bypass this challenge. The
script reads what it can, stops dead at the first 202, keeps what was read. In
practice: a few postings per pass, several spaced passes.

Re-scores the fit AND exp_requise at the same time: a description added without
re-scoring leaves the offer at its old fit, computed on the title alone.

Run:
  python JobHunter.pyw wtj_desc --dry
  python JobHunter.pyw wtj_desc --limit 20
  python JobHunter.pyw wtj_desc
"""

import argparse
import concurrent.futures as cf
import html
import json
import re
import sys
import time

from jobhunter import root as _racine
from jobhunter.scoring import history as _historique

sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)  # type: ignore[union-attr]  # console : TextIOWrapper

HERE = _racine.scripts()

QUEUE = HERE / "apply_queue.json"

UA = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    )
}


class Bloque(Exception):
    """WTJ switched the IP to an anti-bot challenge. We stop, we do not bypass it."""

    def __init__(self, code):
        super().__init__(f"WTJ repond {code} (challenge anti-bot)")


RX_LD = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)
RX_BALISE = re.compile(r"<[^>]+>")


def _texte(brut):
    """Description HTML -> readable text, line breaks preserved."""
    t = re.sub(r"<\s*(br|/p|/li|/div)\s*/?>", "\n", brut, flags=re.I)
    t = html.unescape(RX_BALISE.sub(" ", t))
    t = re.sub(r"[ \t\xa0]+", " ", t)
    return re.sub(r"\n{3,}", "\n\n", t).strip()


def description(url, client, essais=2):
    """Text of the posting, or "" if unreadable. Never raises."""
    for n in range(essais):
        try:
            r = client.get(url, headers=UA, timeout=25)
        except Exception:
            time.sleep(1.5 * (n + 1))
            continue
        # 202 with an empty body = CloudFront anti-bot challenge. It does not come at
        # the first request: WTJ serves a few postings, then switches the IP to a
        # challenge and leaves it there (slowing down to 8 s between requests changes nothing,
        # measured). It is not a success code, it must absolutely not
        # be treated as such: the description would be overwritten with emptiness.
        if r.status_code == 202 or r.status_code == 429:
            raise Bloque(r.status_code)
        if r.status_code != 200:
            return ""
        for bloc in RX_LD.findall(r.text):
            try:
                o = json.loads(bloc)
            except Exception:
                continue
            # Only one block carries @type JobPosting; the other is a FAQPage
            # without a useful description.
            if isinstance(o, dict) and o.get("@type") == "JobPosting":
                t = _texte(str(o.get("description") or ""))
                # Below 200 characters it is an interface summary, not the posting
                return t if len(t) >= 200 else ""
        return ""
    return ""


def _cible(u):
    """WTJ offer posting, not a search nor a company page.

    The /fr/jobs?query=… URLs of the queue come from the scan: they have no
    description to read, counting them as failures would skew the summary.
    """
    from jobhunter import links

    return links.sur_site(u, "welcometothejungle.com") and "/jobs/" in u and "?query=" not in u


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=2)  # WTJ bride vite
    a = ap.parse_args()

    from jobhunter.storage import queue as queue_io

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

    from jobhunter.scoring.fit import fit_detail

    textes = {}
    with httpx.Client(follow_redirects=True) as client:
        with cf.ThreadPoolExecutor(max_workers=a.workers) as ex:
            futs = {ex.submit(description, q[i]["url"], client): i for i in cibles}
            for n, f in enumerate(cf.as_completed(futs), 1):
                try:
                    textes[futs[f]] = f.result()
                except Bloque as e:
                    # No point going on: the challenge applies to the whole IP.
                    # The descriptions already read are kept and written.
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
        _historique.poser(
            o, *fit_detail(f"{o.get('poste', '')} {t}", o.get("poste", "")), "description"
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
    for d, av, ap_, ent, p in sorted(delta, reverse=True)[:10]:
        print(f"   +{d}  fit {av} -> {ap_}  {ent:26} {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
