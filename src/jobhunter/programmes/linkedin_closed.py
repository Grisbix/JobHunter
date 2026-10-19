#!/usr/bin/env python3
"""linkedin_closed.py — Removes from the queue the LinkedIn offers that no longer accept applications.

LinkedIn returns HTTP 200 even for a closed posting: the status code says NOTHING.
Only the guest API (jobs-guest, without authentication) carries the marker "No longer
accepting applications". It is this marker, and it alone, that allows the deletion.

Caution rule: we only delete on a POSITIVE closing signal. A timeout, a network error,
a 429 or an unexpected page leave the offer in place — better keep a dead offer than
erase a live one.

The removed offers are saved in _supprimees_linkedin_<date>.json (not versioned): the
deletion stays reversible.

LOCALISATION TRAP. LinkedIn serves the page in the visitor's language, and the French
phrasing is PASSIVE: "Les candidatures ne sont plus acceptées". A pattern that only
expects the active form ("n'accepte plus de candidature") or only the English misses
ALL the postings served in French — most of them from France — and declares them open.
Checked on 6 postings (3 closed, 3 open): 6/6 right, including through the "login
wall" variant that LinkedIn serves after a few dozen requests. That variant does carry
the marker: it is NOT blind.

The persistent memory (_linkedin_etat.json) avoids asking again about what is already
decided. If the detector changes, PURGE this file: its verdicts were given by the old
version.

Run:
  python JobHunter.pyw linkedin_closed --dry                      # counts only
  python JobHunter.pyw linkedin_closed --workers 1 --pause 20     # slow pass
  python JobHunter.pyw linkedin_closed                            # deletes for good
"""

import argparse
import concurrent.futures as cf
import datetime as _dt
import importlib
import json
import re
import sys
import time

from jobhunter import racine as _racine

sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)  # type: ignore[union-attr]  # console : TextIOWrapper

HERE = _racine.scripts()
QUEUE = HERE / "apply_queue.json"
API = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{}"
UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
}

# The identifier is the last long number of /jobs/view/<slug>-<id>
RX_ID = re.compile(r"/jobs/view/(?:[^/?#]*?-)?(\d{6,})")
# Closing marker, FR and EN. LinkedIn serves one or the other depending on the locale.
# The FRENCH phrasing is PASSIVE — "Les candidatures ne sont plus acceptées" —
# and not "n'accepte plus de candidature". Expecting the active form meant
# missing all the postings served in French, that is most of
# them from France.
RX_FERME = re.compile(
    r"no longer accepting applications"
    r"|candidatures? ne sont plus accept"
    r"|ne sont plus accept[ée]e?s?"
    r"|n[e']accepte plus de candidature"
    r"|ne recrute plus"
    r"|cette offre n[e']est plus",
    re.I,
)

# "Login wall" variant served after a few dozen guest requests.
# It is identical for an open offer and a closed offer: unreadable.
RX_MUR = re.compile(r"sign-in-modal|authwall|guest-homepage", re.I)
# Presence of a real apply button = page really readable
RX_POSTULER = re.compile(r"apply-button|jobs-apply-button|sign-up-modal__apply", re.I)

OUVERT, FERME, INCONNU = "ouvert", "ferme", "inconnu"


def job_id(url):
    m = RX_ID.search(str(url or ""))
    return m.group(1) if m else None


def etat(jid, client, essais=2):
    """OUVERT / FERME / INCONNU. INCONNU protects: it leads to no deletion."""
    for n in range(essais):
        try:
            r = client.get(API.format(jid), headers=UA, timeout=15)
        except Exception:
            time.sleep(1.5 * (n + 1))
            continue
        if r.status_code == 429:  # LinkedIn slows us down: we slow down
            time.sleep(5 * (n + 1))
            continue
        if r.status_code == 404:
            # the posting no longer exists at all — but LinkedIn also serves transient
            # 404s; we do not delete on that, we report it
            return INCONNU
        if r.status_code != 200:
            time.sleep(1.0)
            continue
        h = r.text
        if len(h) < 200:  # truncated response: we do not conclude
            return INCONNU
        if RX_FERME.search(h):
            return FERME
        # TRAP: past a certain volume, LinkedIn serves a "login wall"
        # variant IDENTICAL for an open offer and a closed offer — the
        # closing marker is missing from it. Concluding "open" on this
        # page would amount to certifying an offer that could not be read.
        if RX_MUR.search(h) and not RX_POSTULER.search(h):
            return INCONNU
        return OUVERT
    return INCONNU


ETAT = HERE / "_linkedin_etat.json"  # memory of the checks (not versioned)
SUIVI = HERE / "suivi.json"  # candidatures : statut, note, date


def _oid_offre(offre):
    """Meme cle que l'app et que suivi.json : « entreprise|poste »."""
    return f"{(offre.get('entreprise') or '').strip()}|{(offre.get('poste') or '').strip()}"


def _oids_suivis():
    """Offers carrying a trace of application. Untouchable."""
    try:
        return set(importlib.import_module("jobhunter.stockage.suivi").charger(SUIVI))
    except (FileNotFoundError, ValueError):
        return set()


def _memoire():
    try:
        return json.loads(ETAT.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _frais(entree, jours):
    """A conclusive check less than `jours` days old can be reused."""
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

    # With --dry we do not write the queue: taking the write lock would make
    # us wait 3 min behind a document generation, for nothing. The
    # writes being atomic (tmp + replace), the read stays consistent.
    if not a.dry and not importlib.import_module("jobhunter.programmes.jutil").garder(QUEUE):
        return 3

    q = importlib.import_module("jobhunter.stockage.file").charger(QUEUE, descriptions=False)
    cibles = []
    for i, o in enumerate(q):
        if "linkedin.com" not in (o.get("url") or ""):
            continue
        jid = job_id(o.get("url"))
        if jid:
            cibles.append((i, jid, o))
    # Reuses the recent conclusive checks: LinkedIn throttles guest
    # access, so every request counts. We only replay the undetermined.
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
            # slow walk: one request at a time, pause between each
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

    # NEVER delete an offer the user applied to. A posting
    # closes AFTER one applied: it is even the most frequent case. Without this
    # safeguard, the tool erased the tracked offers first — the trace of the
    # application became orphaned and disappeared from the app. It happened
    # for real (Volkswagen Financial Services, application of 11/07).
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
    importlib.import_module("jobhunter.programmes.jutil").jwrite(
        QUEUE, neuf
    )  # ecriture atomique (tmp + replace)
    print(f"\n{len(perdus)} offre(s) retiree(s). Sauvegarde : {sauv.name}")
    print(f"Queue : {len(q)} -> {len(neuf)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
