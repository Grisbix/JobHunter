#!/usr/bin/env python3
"""linkedin_desc.py — Fetches the DESCRIPTION of LinkedIn offers from the guest API.

WHY. The fit is computed on "title + description". An offer without a description is
scored on eight title words: average fit 2.9 against 5.6 for an offer that was read.
228 LinkedIn offers of the queue had no description, and scrape_desc.py fails on them
(login wall): 5 successes out of 200.

The guest API `jobs-guest/jobs/api/jobPosting/<id>` is PUBLIC, without
authentication, and serves the full description. It is the same access point as
linkedin_closed.py — we reuse its tooling rather than duplicating it. No protection
bypass: it is the endpoint LinkedIn exposes to visitors who are not logged in.

Re-scores the fit AND exp_requise at the same time: a description added without
re-scoring leaves the offer at its old fit, computed without it.

Run:
  python JobHunter.pyw linkedin_desc --dry              # counts, writes nothing
  python JobHunter.pyw linkedin_desc --limit 100
  python JobHunter.pyw linkedin_desc                    # all the offers concerned
"""

import argparse
import concurrent.futures as cf
import html
import re
import sys
import time

from jobhunter import root as _racine
from jobhunter.scoring import history as _historique

sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)  # type: ignore[union-attr]  # console : TextIOWrapper

HERE = _racine.scripts()

QUEUE = HERE / "apply_queue.json"

from jobhunter.programs.linkedin_closed import API, RX_FERME, UA, job_id  # same endpoint, same UA

# The description lives in a `description__text` block; fallback on <section>.
RX_DESC = [
    re.compile(r'<div class="[^"]*description__text[^"]*">(.*?)</div>\s*</div>', re.S),
    re.compile(r'<section class="[^"]*description[^"]*">(.*?)</section>', re.S),
]
RX_BALISE = re.compile(r"<[^>]+>")
RX_SCRIPT = re.compile(r"<(script|style)\b.*?</\1>", re.S | re.I)


# Counter of throttlings, shared by the threads. It serves to TELL APART "LinkedIn
# is cutting us off" from "this posting has no description" — the first pass
# returned 1031 texts out of 2653 and the 1622 failures were taken for empty
# postings, while a simple retry read them all. A silent throttling
# looks like a result.
BRIDAGES = {"n": 0}

# Offers whose posting carries the closing marker. We already read the page for
# its description: seeing "No longer accepting applications" there costs nothing, and
# saves audit_dispo one more request on the same endpoint.
FERMEES: set[str] = set()


def description(jid, client, essais=4):
    """Text of the posting, or "" if unreadable. Never raises: a failure leaves
    the offer as it is, no data is degraded."""
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
            # Below 200 characters it is an interface fragment, not a posting
            if len(t) >= 200:
                return t
        return ""
    return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    # 6 threads got LinkedIn throttling from the first few hundred: 1622 failures out of
    # 2653, all readable on retry. Better read more slowly and read everything.
    ap.add_argument("--workers", type=int, default=3)
    # IN BATCHES, AND THE LOCK ONLY FOR WRITING. On 2026-09-22, the first
    # version read 6438 descriptions in three hours inside ONE SINGLE
    # transaction: lock held three hours, application blocked, and all the
    # work in memory until the last second — a crash at 2 h 50
    # lost 2 h 50 of network. Now: we read a snapshot without a lock,
    # we collect outside the lock, and each batch is written in a few seconds on a
    # queue RE-READ inside the lock. A stop only costs the batch in progress.
    ap.add_argument("--lot", type=int, default=500)
    a = ap.parse_args()

    from jobhunter.storage import queue as queue_io

    cibles = _cibles(queue_io.charger(), a.limit)
    print(f"{len(cibles)} offre(s) LinkedIn sans description")
    if a.dry:
        print("[DRY] rien n'a ete ecrit.")
        return 0
    if not cibles:
        return 0
    return _travail(cibles, a, queue_io)


def _cibles(q, limite=0):
    """The LinkedIn ids of the offers without a description, without duplicates."""
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
    """Puts the texts into the queue, under lock, on the RE-READ state.

    The offer is found by its LinkedIn id, never by its position: between the
    snapshot and the write, a scan may have inserted, deleted or reordered. An
    offer that received a description in the meantime is not overwritten. An offer
    that disappeared is simply ignored."""
    import datetime

    from jobhunter.scoring.fit import fit_detail

    ecrites, delta = 0, []
    with queue_io.transaction(attente=attente) as q:
        for o in q:
            if "linkedin.com" not in (o.get("url") or ""):
                continue
            # Marked, not removed: the deletion stays with audit_dispo, which
            # spares the tracking (reason "déjà marquée morte").
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
            # MANDATORY re-score: without it the offer keeps the fit computed without a description
            _historique.poser(
                o, *fit_detail(f"{o.get('poste', '')} {t}", o.get("poste", "")), "description"
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
    # Texts read but not yet placed. If the queue is busy at the time
    # of writing a batch, they wait for the next one instead of being lost.
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
        # Last chance, with a long wait: it is the only moment when
        # a refusal would really lose work.
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
    # A failure is not a verdict: saying how many times LinkedIn
    # throttled us avoids concluding "these postings have no description".
    if BRIDAGES["n"]:
        print(f"   ({BRIDAGES['n']} bridage(s) 429 rencontre(s) — relancer ramassera le reste)")
    manquantes = len(cibles) - ecrites
    if manquantes:
        print(
            f"   {manquantes} offre(s) restent sans description : relancer "
            f"le programme, il ne reprend que celles-la."
        )
    for d, av, ap_, ent, p in sorted(delta, reverse=True)[:10]:
        print(f"   +{d}  fit {av} -> {ap_}  {ent:26} {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
