#!/usr/bin/env python3
"""queue_tools.py — Maintenance of apply_queue.json.
  mark_dead()  : checks all the URLs (link_check.batch_check) → `link_status` tag
                 on each offer (OK / EXPIREE / ANTI-BOT / MORT) + link_status.json sidecar.
  writeback()  : rewrites an offer's URL (e.g. dead URL → resolved homepage), keeps `url_orig`.
Called by apply_runner (write-back after homepage_fallback) and the JobHunter button (marking).
CLI: python JobHunter.pyw queue_tools mark        # marks the dead URLs
     python JobHunter.pyw queue_tools test        # self-test (temporary file)
"""

import sys
from pathlib import Path

from jobhunter import racine as _racine
from jobhunter.stockage import atomique
from jobhunter.stockage import file as queue_io
from jobhunter.stockage import suivi as suivi_io

SCRIPTS = _racine.scripts()
QUEUE = SCRIPTS / "apply_queue.json"
SIDECAR = SCRIPTS / "link_status.json"

sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]  # console : TextIOWrapper


# EVERY WRITE GOES THROUGH queue_io.transaction: lock, fresh re-read, atomic
# write. `mark_dead` read the queue, checked the links (minutes of network),
# then rewrote its snapshot with write_text, without a lock: a collection merged
# in the meantime was lost (audit of 19/10/2026). The network now happens outside
# the lock, and only its RESULTS are applied to the re-read queue.


def load(path=QUEUE):
    """The queue, read-only (without the descriptions)."""
    return queue_io.charger(path, descriptions=False)


def _tag(res):
    """{live,status,soft_dead,note} → étiquette lisible."""
    if res.get("soft_dead"):
        return "EXPIREE"
    if res.get("live"):
        return "OK"
    if res.get("status") in (429, 403, 401, 999):
        return "ANTI-BOT"
    return "MORT"


_HARD_HOSTS = ("linkedin.", "indeed.", "glassdoor.")  # systematic anti-bot: no point scanning


def mark_dead(path=QUEUE, verbose=True, _checker=None, skip_hard=True):
    """Checks each unique http URL of the queue, writes `link_status` on each offer.
    skip_hard=True: LinkedIn/Indeed/Glassdoor tagged ANTI-BOT without HTTP (useless scan, ban).
    _checker: fn(list[url])->{url:res} injectable (tests). Default = link_check.batch_check.
    Returns {total, checked, skipped_hard, counts:{tag:n}}."""
    all_urls = {r["url"] for r in load(path) if str(r.get("url") or "").startswith("http")}

    def _hard(u):
        return skip_hard and any(h in u.lower() for h in _HARD_HOSTS)

    urls = sorted(u for u in all_urls if not _hard(u))
    hard = sorted(u for u in all_urls if _hard(u))
    if _checker is None:
        from jobhunter.programmes.link_check import batch_check as _checker
    if verbose:
        print(
            f"Scan {len(urls)} URLs (carrière/ATS/homepage) · {len(hard)} LinkedIn/Indeed sautées (anti-bot)…"
        )
    res = _checker(urls) if urls else {}
    tags = {u: _tag(res.get(u, {"live": False, "status": 0})) for u in urls}
    for u in hard:
        tags[u] = "ANTI-BOT"
    counts = {}
    with queue_io.transaction(path, descriptions=False) as rows:
        for r in rows:
            u = r.get("url") or ""
            if u in tags:
                r["link_status"] = tags[u]
                counts[tags[u]] = counts.get(tags[u], 0) + 1
        total = len(rows)
    # sidecar (survives a rebuild: reference/inspection)
    try:
        atomique.ecrire_json(
            SIDECAR if path == QUEUE else Path(path).with_name("link_status.json"), tags
        )
    except OSError:
        pass
    if verbose:
        print(f"URLs vérifiées: {len(urls)} | offres taguées: {sum(counts.values())}")
        for k, v in sorted(counts.items(), key=lambda x: -x[1]):
            print(f"  {v:5}  {k}")
    return {"total": total, "checked": len(urls), "skipped_hard": len(hard), "counts": counts}


def prune(path=QUEUE, drop=("MORT",), verbose=True):
    """Removes from the queue the offers whose link_status ∈ drop (default: MORT only).
    Does NOT remove EXPIREE/ANTI-BOT by default (recoverable / alive). Returns the number removed.
    Run mark_dead BEFORE. Reversible: queue regenerable through build_queue + git backup."""
    # Tracked offers NEVER leave: a posting closes after one applied,
    # and that is precisely the one we want to keep (invariant of AGENTS.md).
    suivies = set(suivi_io.charger())
    with queue_io.transaction(path, descriptions=False) as rows:
        before = len(rows)
        rows[:] = [
            r for r in rows if r.get("link_status") not in drop or queue_io.oid(r) in suivies
        ]
        n, kept = before - len(rows), len(rows)
    if verbose:
        print(f"prune: {n} offres supprimées (link_status ∈ {drop}) · {kept} gardées")
    return n


def writeback(old_url, new_url=None, link_status=None, path=QUEUE):
    """Updates the offer(s) whose url == old_url: url→new_url (keeps url_orig),
    + link_status. Returns the number of offers modified. Persists apply_queue.json."""
    if not old_url:
        return 0
    n = 0
    with queue_io.transaction(path, descriptions=False) as rows:
        for r in rows:
            if r.get("url") == old_url:
                if new_url and new_url != old_url:
                    r.setdefault("url_orig", old_url)
                    r["url"] = new_url
                if link_status:
                    r["link_status"] = link_status
                n += 1
    return n


def _selftest():
    import os
    import tempfile

    tf = os.path.join(tempfile.gettempdir(), "qt_test_queue.json")
    rows = [
        {"entreprise": "A", "poste": "x", "url": "https://live.test/1"},
        {"entreprise": "B", "poste": "y", "url": "https://dead.test/2"},
        {"entreprise": "C", "poste": "z", "url": "https://expired.test/3"},
        {"entreprise": "D", "poste": "w", "url": ""},
    ]
    atomique.ecrire_json(tf, rows)
    fake = {
        "https://live.test/1": {"live": True, "status": 200, "soft_dead": None},
        "https://dead.test/2": {"live": False, "status": 404, "soft_dead": None},
        "https://expired.test/3": {"live": False, "status": 200, "soft_dead": "offre pourvue"},
    }
    r = mark_dead(tf, verbose=False, _checker=lambda urls: fake)
    got = {x["entreprise"]: x.get("link_status") for x in load(tf)}
    P = F = 0

    def ck(n, c):
        nonlocal P, F
        (P := P + 1) if c else (F := F + 1)
        print(("  OK " if c else "  KO ") + n)

    ck("live→OK", got["A"] == "OK")
    ck("404→MORT", got["B"] == "MORT")
    ck("soft-404→EXPIREE", got["C"] == "EXPIREE")
    ck("url vide non taguée", got["D"] is None)
    n = writeback("https://dead.test/2", "https://b.com/carrieres", "HOMEPAGE_FALLBACK", path=tf)
    e = next(x for x in load(tf) if x["entreprise"] == "B")
    ck("writeback url remplacée", n == 1 and e["url"] == "https://b.com/carrieres")
    ck("writeback garde url_orig", e.get("url_orig") == "https://dead.test/2")
    ck("writeback link_status", e.get("link_status") == "HOMEPAGE_FALLBACK")
    os.remove(tf)
    print(f"\n=== queue_tools: {P} OK / {F} KO ===")
    return F == 0


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "mark"
    if cmd == "test":
        sys.exit(0 if _selftest() else 1)
    elif cmd == "mark":
        mark_dead()
    elif cmd == "prune":  # mark_dead then deletes the MORT ones
        mark_dead()
        prune()
    else:
        print("usage: queue_tools.py [mark|prune|test]")
