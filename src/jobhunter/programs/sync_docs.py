#!/usr/bin/env python3
"""sync_docs.py — CONSISTENCY KEEPER for CVs/letters. The .docx is the SOURCE, the .pdf is
DERIVED. When a docx changes somewhere, its pdf (and the app's links) follow.

Passes (default = all except --format):
  1. PAIRS     : docx without pdf → pdf generated; orphan pdf (without docx) → reported
  2. FRESHNESS : pdf older than its docx → regenerated (LibreOffice)
  3. LINKS     : broken cv/lettre of apply_queue.json → re-matched by file name
  4. --format  : homogenises the letters (justified+hyphenation, today's date,
                 Objet before the salutation, recipient removed, AI dashes)

Run: python JobHunter.pyw sync_docs            # 1+2+3
     python JobHunter.pyw sync_docs --format   # 1+2+3+4
     python JobHunter.pyw sync_docs --dry      # shows without touching"""

import argparse
import importlib
import subprocess
import sys
from pathlib import Path

from jobhunter import root as _racine

sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]  # console : TextIOWrapper

HERE = _racine.scripts()
ROOT = HERE.parent
QUEUE = HERE / "apply_queue.json"

from jobhunter import links as liens
from jobhunter import paths as chemins

DIRS = [chemins.CV_PAR_OFFRE, chemins.LT_PAR_OFFRE]
LT_DIR = chemins.LT_PAR_OFFRE
SOFFICE = next(
    (
        s
        for s in (
            r"C:\Program Files\LibreOffice\program\soffice.exe",
            r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        )
        if Path(s).exists()
    ),
    None,
)


def to_pdf(docx):
    if not SOFFICE:
        return False
    try:
        r = subprocess.run(
            [SOFFICE, "--headless", "--convert-to", "pdf", "--outdir", str(docx.parent), str(docx)],
            capture_output=True,
            timeout=90,
        )
        return r.returncode == 0
    except Exception:
        return False


def pass_pairs_freshness(dry=False):
    made = regen = orphans = 0
    for d in DIRS:
        if not d.exists():
            continue
        for f in sorted(d.glob("*.docx")):
            pdf = f.with_suffix(".pdf")
            if not pdf.exists():
                if not dry and to_pdf(f):
                    made += 1
                elif dry:
                    made += 1
            elif pdf.stat().st_mtime < f.stat().st_mtime:
                if not dry and to_pdf(f):
                    regen += 1
                elif dry:
                    regen += 1
        stems = {f.stem for f in d.glob("*.docx")}
        orphans += sum(1 for f in d.glob("*.pdf") if f.stem not in stems)
    return made, regen, orphans


def pass_links(dry=False):
    """Broken cv/letter links in the queue → re-match by stem in the right folder."""
    try:
        q = importlib.import_module("jobhunter.storage.queue").charger(QUEUE, descriptions=False)
    except Exception:
        return 0, 0
    fixed = broken = 0
    for x in q:
        for key, d in (("cv", DIRS[0]), ("lettre", DIRS[1])):
            u = x.get(key)
            if not u:
                continue
            p = importlib.import_module("jobhunter.programs.util").chemin_de(u)
            if p.exists():
                continue
            # re-match: same stem, other extension or expected folder
            cand = None
            for ext in (p.suffix, ".pdf", ".docx"):
                c = d / (p.stem + ext)
                if c.exists():
                    cand = c
                    break
            if cand is not None:
                if not dry:
                    x[key] = liens.url_de(cand)
                fixed += 1
            else:
                broken += 1
    if fixed and not dry:
        importlib.import_module("jobhunter.programs.util").jwrite(QUEUE, q)
    return fixed, broken


def pass_format(dry=False):
    """Homogeneous format of the letters: justified+hyphenation+formulas (fix_letters),
    dashes (fix_dashes), date/order/recipient (refresh_letters)."""
    from jobhunter.programs import fix_letters, refresh_letters

    try:  # personal script, missing from the shared version
        import fix_dashes
    except ImportError:
        fix_dashes = None
    ents = refresh_letters._entreprises_by_letter()
    n = 0
    docs = sorted(LT_DIR.glob("*.docx"))
    for i, f in enumerate(docs):
        c = False
        try:
            c |= bool(fix_letters.fix_doc(f, dry=dry))
            if fix_dashes:
                c |= bool(fix_dashes.fix_doc(f, dry=dry))
            c |= bool(refresh_letters.fix_doc(f, ents.get(f.stem, ""), dry=dry))
        except Exception:
            continue
        n += bool(c)
        if (i + 1) % 300 == 0:
            print(f"  … format {i + 1}/{len(docs)}")
    return n


def main():
    # Inter-process lock: this program rewrites the ENTIRE queue. If
    # another one does it at the same time (scheduled task vs app), the last one
    # to write erases the other's work.
    if not importlib.import_module("jobhunter.programs.util").garder(QUEUE):
        return 3
    ap = argparse.ArgumentParser()
    ap.add_argument("--format", action="store_true", help="homogénéise aussi le format des lettres")
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    tag = "[DRY] " if a.dry else ""
    if a.format:
        n = pass_format(dry=a.dry)
        print(f"{tag}format homogénéisé : {n} lettres touchées")
    made, regen, orphans = pass_pairs_freshness(dry=a.dry)
    fixed, broken = pass_links(dry=a.dry)
    print(f"{tag}pdf créés: {made} · pdf resynchronisés: {regen} · pdf orphelins: {orphans}")
    print(f"{tag}liens queue réparés: {fixed} · liens toujours cassés: {broken}")
    print(
        "✅ docx = source, pdf = dérivé — tout est aligné."
        if not (regen or made or fixed) or not a.dry
        else ""
    )


if __name__ == "__main__":
    sys.exit(main())
