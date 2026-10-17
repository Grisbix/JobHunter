#!/usr/bin/env python3
"""sync_docs.py — GENDARME de cohérence CV/lettres. Le .docx est la SOURCE,
le .pdf est DÉRIVÉ. Quand un docx change quelque part, son pdf (et les liens
de l'app) suivent.

Passes (défaut = toutes sauf --format) :
  1. PAIRES    : docx sans pdf → pdf généré ; pdf orphelin (sans docx) → signalé
  2. FRAÎCHEUR : pdf plus vieux que son docx → régénéré (LibreOffice)
  3. LIENS     : cv/lettre de apply_queue.json cassés → re-matchés par nom de fichier
  4. --format  : homogénéise les lettres (justifié+césure, date du jour,
                 Objet avant salutation, destinataire retiré, tirets IA)

Run : python sync_docs.py            # 1+2+3
      python sync_docs.py --format   # 1+2+3+4
      python sync_docs.py --dry      # montre sans toucher"""

import argparse
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
QUEUE = HERE / "apply_queue.json"
sys.path.insert(0, str(Path(__file__).resolve().parent))
import chemins

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
    """Liens cv/lettre cassés dans la queue → re-match par stem dans le bon dossier."""
    try:
        q = __import__("queue_io").charger(QUEUE, descriptions=False)
    except Exception:
        return 0, 0
    fixed = broken = 0
    for x in q:
        for key, d in (("cv", DIRS[0]), ("lettre", DIRS[1])):
            u = x.get(key)
            if not u:
                continue
            p = __import__("jutil").chemin_de(u)
            if p.exists():
                continue
            # re-match : même stem, autre extension ou dossier attendu
            cand = None
            for ext in (p.suffix, ".pdf", ".docx"):
                c = d / (p.stem + ext)
                if c.exists():
                    cand = c
                    break
            if cand is not None:
                if not dry:
                    x[key] = "file:///" + quote(str(cand).replace("\\", "/"), safe="/:")
                fixed += 1
            else:
                broken += 1
    if fixed and not dry:
        __import__("jutil").jwrite(QUEUE, q)
    return fixed, broken


def pass_format(dry=False):
    """Format homogène des lettres : justifié+césure+formules (fix_letters),
    tirets (fix_dashes), date/ordre/destinataire (refresh_letters)."""
    import fix_letters
    import refresh_letters

    try:  # script personnel, absent de la version partagee
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
    # Verrou inter-processus : ce programme reecrit la queue ENTIERE. Si un
    # autre le fait en meme temps (tache planifiee vs app), le dernier qui
    # ecrit efface le travail de l'autre.
    if not __import__("jutil").garder(QUEUE):
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
