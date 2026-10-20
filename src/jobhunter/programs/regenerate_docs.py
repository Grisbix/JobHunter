#!/usr/bin/env python3
"""regenere_docs.py — Redoes letters and CVs with the current generator.

WHY. The wording fixes only affect the letters WRITTEN AFTER them. Those already on
disk keep their original text: raw quotations from the posting, inclusive forms
"un(e)", skill labels copied with their slashes, "forecast" in the middle of a French
text, up to four "et" in a sentence. The CVs, for their part, carried "valorisation
(DCF, multiples)" on their skills line.

WHAT DOES NOT CHANGE. The file NAME: it is taken as is from the queue, so the links of
the app and of the tracking stay valid. Nothing is written into apply_queue.json — so
this program does not take the lock, and the app can run meanwhile.

THE LANGUAGE IS RECOMPUTED each time, as the generator does: an offer in English
receives a letter in English.

The original .docx files are tracked by git. When in doubt:
    git checkout -- Lettres/Par_offre

Run:
  python JobHunter.pyw regenerate --dry
  python JobHunter.pyw regenerate                   # letters
  python JobHunter.pyw regenerate --cv              # CVs
  python JobHunter.pyw regenerate --cv --sans-pdf   # .docx only, PDFs later
"""

import argparse
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path

from jobhunter import root as _racine

HERE = _racine.scripts()
ROOT = HERE.parent

sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]  # console : TextIOWrapper

from jobhunter import paths as chemins

SORTIE = {"lettre": chemins.LT_PAR_OFFRE, "cv": chemins.CV_PAR_OFFRE}

# LibreOffice converts in BATCH. One conversion at a time costs 1.2 s, most
# of which is the program start-up: 3336 letters would take more than an
# hour. A single start-up for 150 files brings that down to a few minutes.
LOT_PDF = 150


def stem_de(url):
    """The file name (without extension) stored in the queue.

    We TAKE IT BACK instead of recomputing it: new_name() may have changed since, and
    a different name would leave the old letter on disk while the queue would point
    to the new one. Two files, one right link, one orphan.
    """
    u = (url or "").strip()
    if not u:
        return ""
    if u.startswith("file:///"):
        u = urllib.parse.unquote(u[8:])
    return Path(u).stem


def convertir(fichiers, exe, dossier):
    """The .docx -> .pdf, in batches. Returns the number of PDFs produced."""
    faits = 0
    for i in range(0, len(fichiers), LOT_PDF):
        lot = fichiers[i : i + LOT_PDF]
        try:
            subprocess.run(
                [exe, "--headless", "--convert-to", "pdf", "--outdir", str(dossier)]
                + [str(f) for f in lot],
                check=True,
                capture_output=True,
                timeout=60 + 8 * len(lot),
            )
            faits += sum(1 for f in lot if f.with_suffix(".pdf").exists())
        except Exception as e:
            print(f"  ! lot PDF {i // LOT_PDF + 1} : {type(e).__name__}")
        print(f"    PDF … {min(i + LOT_PDF, len(fichiers))}/{len(fichiers)}")
    return faits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--limite", type=int)
    ap.add_argument("--sans-pdf", action="store_true")
    ap.add_argument("--cv", action="store_true", help="refaire les CV au lieu des lettres")
    a = ap.parse_args()

    from jobhunter.documents import SOFFICE, tailor_cv, tailor_letter
    from jobhunter.scoring.language import langue_offre
    from jobhunter.storage import queue as queue_io

    champ = "cv" if a.cv else "lettre"
    faire = tailor_cv if a.cv else tailor_letter
    dossier = SORTIE[champ]

    q = queue_io.charger()
    cibles = [(o, stem_de(o.get(champ))) for o in q if (o.get(champ) or "").strip()]
    cibles = [(o, s) for o, s in cibles if s]
    if a.limite:
        cibles = cibles[: a.limite]

    print(f"{len(cibles)} {'CV' if a.cv else 'lettre(s)'} a refaire")
    if a.dry:
        for o, s in cibles[:8]:
            lg = langue_offre(
                o.get("poste") or "", o.get("description") or "", o.get("localisation") or ""
            )
            print(f"  [{lg}] {s[:78]}")
        print("\n[DRY] rien n'a ete ecrit.")
        return 0

    t0 = time.time()
    faits, rates = [], 0
    offres_de = {}  # stem -> offer, to redo a CV that overflows
    for n, (o, stem) in enumerate(cibles, 1):
        off = dict(
            company=o.get("entreprise") or "",
            role=o.get("poste") or "",
            offer_text=f"{o.get('poste', '')} {o.get('description', '')}",
            missions=(o.get("missions") or "")[:400],
            profil=(o.get("profil") or "")[:300],
            domaine=o.get("domaine"),
            rh=o.get("rh"),
        )
        lg = langue_offre(
            o.get("poste") or "", o.get("description") or "", o.get("localisation") or ""
        )
        # RETRIES. OneDrive holds the files it has just synced, and
        # the write then fails with "OSError: [Errno 22] Invalid argument"
        # on a path that is nevertheless valid. A pass just after another one
        # lost 49 out of 3337 that way. The same remedy as jutil.jwrite: wait
        # and start again, the hold is released in a second or two.
        p = None
        for essai in range(4):
            try:
                p = faire(off, nom=stem, langue=lg)
                break
            except OSError as e:
                if essai == 3:
                    rates += 1
                    if rates <= 5:
                        print(f"  ! {stem[:60]} : {type(e).__name__}: {e}")
                else:
                    time.sleep(0.5 * (essai + 1))
            except Exception as e:
                rates += 1
                if rates <= 5:
                    print(f"  ! {stem[:60]} : {type(e).__name__}: {e}")
                break
        if p:
            faits.append(p)
            offres_de[Path(p).stem] = o
        if n % 500 == 0:
            print(f"  … {n}/{len(cibles)} ({time.time() - t0:.0f} s)")
    print(f"\n{len(faits)} .docx refaits, {rates} echec(s) — {time.time() - t0:.0f} s")

    if a.sans_pdf or not faits:
        print("PDF non regeneres (--sans-pdf) : ils portent encore l'ancien texte.")
        return 0

    exe = next((s for s in SOFFICE if Path(s).exists()), None)
    if not exe:
        print("! LibreOffice introuvable, PDF non regeneres.")
        return 2
    print(f"\nConversion PDF, par lots de {LOT_PDF} :")
    t1 = time.time()
    n = convertir(faits, exe, dossier)
    print(f"{n} PDF ecrits — {time.time() - t1:.0f} s")
    if a.cv:
        # ONE PAGE, ALWAYS. The automatic facts (cv_auto) add
        # lines; the batch conversion does not look at pages. We redo
        # one by one those that overflow, with the lightenings of CV/Faits.json.
        from jobhunter.documents import _pages_pdf, cv_une_page

        par_stem = offres_de
        trop = [p for p in faits if _pages_pdf(dossier / (Path(p).stem + ".pdf")) > 1]
        print(f"{len(trop)} CV sur plus d'une page, repris un par un")
        for p in trop:
            o = par_stem.get(Path(p).stem)
            if o is None:
                continue
            off = dict(
                company=o.get("entreprise") or "",
                role=o.get("poste") or "",
                offer_text=f"{o.get('poste', '')} {o.get('description', '')}",
                domaine=o.get("domaine"),
                rh=o.get("rh"),
            )
            lg = langue_offre(
                o.get("poste") or "", o.get("description") or "", o.get("localisation") or ""
            )
            cv_une_page(off, nom=Path(p).stem, langue=lg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
