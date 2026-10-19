#!/usr/bin/env python3
"""queue_tools.py — Maintenance de apply_queue.json.
  mark_dead()  : vérifie toutes les URLs (link_check.batch_check) → tag `link_status`
                 sur chaque offre (OK / EXPIREE / ANTI-BOT / MORT) + sidecar link_status.json.
  writeback()  : réécrit l'URL d'une offre (ex: URL morte → homepage résolue), garde `url_orig`.
Appelé par apply_runner (write-back après homepage_fallback) et le bouton JobHunter (marquage).
CLI : python JobHunter.pyw queue_tools mark        # marque les URLs mortes
      python JobHunter.pyw queue_tools test        # auto-test (fichier temporaire)
"""

import json
import sys
from pathlib import Path

from jobhunter import racine as _racine

SCRIPTS = _racine.scripts()
QUEUE = SCRIPTS / "apply_queue.json"
SIDECAR = SCRIPTS / "link_status.json"

sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]  # console : TextIOWrapper


def load(path=QUEUE):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save(rows, path=QUEUE):
    Path(path).write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")


def _tag(res):
    """{live,status,soft_dead,note} → étiquette lisible."""
    if res.get("soft_dead"):
        return "EXPIREE"
    if res.get("live"):
        return "OK"
    if res.get("status") in (429, 403, 401, 999):
        return "ANTI-BOT"
    return "MORT"


_HARD_HOSTS = ("linkedin.", "indeed.", "glassdoor.")  # anti-bot systématique : inutile de scanner


def mark_dead(path=QUEUE, verbose=True, _checker=None, skip_hard=True):
    """Vérifie chaque URL http unique de la queue, écrit `link_status` sur chaque offre.
    skip_hard=True : LinkedIn/Indeed/Glassdoor tagués ANTI-BOT sans HTTP (scan inutile, ban).
    _checker : fn(list[url])->{url:res} injectable (tests). Défaut = link_check.batch_check.
    Retour {total, checked, skipped_hard, counts:{tag:n}}."""
    rows = load(path)
    all_urls = {r["url"] for r in rows if str(r.get("url") or "").startswith("http")}

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
    for r in rows:
        u = r.get("url") or ""
        if u in tags:
            r["link_status"] = tags[u]
            counts[tags[u]] = counts.get(tags[u], 0) + 1
    save(rows, path)
    # sidecar (survit à un rebuild : référence/inspection)
    try:
        Path(SIDECAR if path == QUEUE else Path(path).with_name("link_status.json")).write_text(
            json.dumps(tags, ensure_ascii=False, indent=1), encoding="utf-8"
        )
    except Exception:
        pass
    if verbose:
        print(f"URLs vérifiées: {len(urls)} | offres taguées: {sum(counts.values())}")
        for k, v in sorted(counts.items(), key=lambda x: -x[1]):
            print(f"  {v:5}  {k}")
    return {"total": len(rows), "checked": len(urls), "skipped_hard": len(hard), "counts": counts}


def prune(path=QUEUE, drop=("MORT",), verbose=True):
    """Supprime de la queue les offres dont link_status ∈ drop (défaut: MORT seul).
    N'enlève PAS EXPIREE/ANTI-BOT par défaut (récupérables / vivants). Retour nb supprimé.
    Lancer mark_dead AVANT. Réversible : queue régénérable via build_queue + backup git."""
    rows = load(path)
    before = len(rows)
    kept = [r for r in rows if r.get("link_status") not in drop]
    save(kept, path)
    n = before - len(kept)
    if verbose:
        print(f"prune: {n} offres supprimées (link_status ∈ {drop}) · {len(kept)} gardées")
    return n


def writeback(old_url, new_url=None, link_status=None, path=QUEUE):
    """Met à jour la/les offre(s) dont url == old_url : url→new_url (garde url_orig),
    + link_status. Retour nb d'offres modifiées. Persiste apply_queue.json."""
    if not old_url:
        return 0
    rows = load(path)
    n = 0
    for r in rows:
        if r.get("url") == old_url:
            if new_url and new_url != old_url:
                r.setdefault("url_orig", old_url)
                r["url"] = new_url
            if link_status:
                r["link_status"] = link_status
            n += 1
    if n:
        save(rows, path)
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
    save(rows, tf)
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
    elif cmd == "prune":  # mark_dead puis supprime les MORT
        mark_dead()
        prune()
    else:
        print("usage: queue_tools.py [mark|prune|test]")
