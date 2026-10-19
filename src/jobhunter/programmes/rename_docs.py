#!/usr/bin/env python3
"""rename_docs.py — Renames CVs + letters in the "Firstname_Name_CV/Lettre_<Job>_<Company>" format (name read from the profile).
Name FIRST (the recruiter sees your name), then the CLEANED JOB (without H/F, duration,
contract, parentheses…), then the short company (anti-collision).

Source of truth = apply_queue.json (cv/lettre fields) → renames docx + twin PDF
+ UPDATES the file:/// links in the queue. Idempotent.

Run: python JobHunter.pyw rename_docs [--dry]"""

import argparse
import importlib
import re
import sys

from jobhunter import racine as _racine

sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]  # console : TextIOWrapper

HERE = _racine.scripts()

from jobhunter import chemins

QUEUE = HERE / "apply_queue.json"

NOISE = re.compile(
    r"(?i)\b(h/f|f/h|h-f|f-h|hf|fh|m/f|f/m|w/m/d|f/m/x|f/m/d|m/w/d|x/f/h"
    r"|cdi|cdd|stage|alternance|apprentissage|internship|intern|vie\b"
    r"|junior|senior|d[ée]butant|confirm[ée]|\d+\s*(mois|ans?)|temps (plein|partiel)"
    r"|paris|lyon|bordeaux|lille|nantes|toulouse|marseille|france|remote|t[ée]l[ée]travail)\b"
)


def clean_poste(p, maxlen=48):
    """Nom du poste SEUL : vire parenthèses, H/F, contrat, durée, ville…"""
    p = re.sub(r"\(.*?\)|\[.*?\]", " ", p or "")
    p = NOISE.sub(" ", p)
    # cuts at the separators: keeps the 1st substantial segment
    segs = [s.strip(" .,-") for s in re.split(r"[-–—:|•]| / ", p)]
    segs = [s for s in segs if len(s.split()) >= 2 or (s and len(segs) == 1)]
    p = segs[0] if segs else (p.strip() or "Poste")
    p = re.sub(r"\s+", " ", p).strip()[:maxlen].strip()
    return p or "Poste"


def _safe(s, maxlen=40):
    s = re.sub(r"[^\w\- ]", "", s, flags=re.U).strip()
    return re.sub(r"\s+", "_", s)[:maxlen].strip("_") or "X"


from jobhunter import profil as _P

PREFIXE = _P.prefixe_fichier()  # "Firstname_Name", read from the profile


def new_name(kind, poste, entreprise):
    ent = _safe(" ".join((entreprise or "").split()[:2]), 22)
    return f"{PREFIXE}_{kind}_{_safe(clean_poste(poste))}_{ent}"


from jobhunter.programmes.jutil import chemin_de as _path_of  # helpers partages
from jobhunter.programmes.jutil import url_de as _url_of


def rename_orphans(dry=False):
    """Fichiers PAS liés à la queue (anciens noms) → même format par pattern :
    « X_cover_letter » → Prenom_Nom_Lettre_X · « CV_X » → Prenom_Nom_CV_X."""
    ROOT = HERE.parent
    dirs = [(chemins.LT_PAR_OFFRE, "Lettre"), (chemins.CV_PAR_OFFRE, "CV")]
    n = 0
    for d, kind in dirs:
        if not d.exists():
            continue
        for f in sorted(d.glob("*.docx")) + sorted(d.glob("*.pdf")):
            if not f.exists() or f.stem.startswith(f"{PREFIXE}_"):
                continue
            stem = f.stem
            if stem.endswith("_cover_letter"):
                stem = stem[: -len("_cover_letter")]
            if stem.startswith("CV_"):
                stem = stem[3:]
            base = f"{PREFIXE}_{kind}_{_safe(stem, 70)}"
            cand, i = base, 2
            while (d / f"{cand}{f.suffix}").exists():
                cand = f"{base}_{i}"
                i += 1
            if not dry:
                try:
                    f.rename(d / f"{cand}{f.suffix}")
                    # twin (pdf/docx) follows with the SAME cand → pair kept
                    for ext in (".pdf", ".docx"):
                        tw = f.with_suffix(ext)
                        if ext != f.suffix and tw.exists() and not (d / f"{cand}{ext}").exists():
                            tw.rename(d / f"{cand}{ext}")
                except OSError:
                    continue
            n += 1
    print(f"{'[DRY] ' if dry else ''}orphelins renommés (même format) : {n}")


def main():
    # Inter-process lock: this program rewrites the ENTIRE queue. If
    # another one does it at the same time (scheduled task vs app), the last one
    # to write erases the other's work.
    if not importlib.import_module("jobhunter.programmes.jutil").garder(QUEUE):
        return 3
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    q = importlib.import_module("jobhunter.stockage.file").charger(QUEUE, descriptions=False)
    ren = upd = miss = 0

    def free(parent, base, suffix, old):
        """1er nom libre (docx ET pdf jumeau libres). old lui-même = déjà bon."""
        i, cand = 2, base
        while True:
            t = parent / f"{cand}{suffix}"
            tw = t.with_suffix(".pdf")
            if t == old:
                return t
            busy = t.exists() or (
                suffix.lower() == ".docx" and tw.exists() and tw != old.with_suffix(".pdf")
            )
            if not busy:
                return t
            cand = f"{base}_{i}"
            i += 1

    for x in q:
        for key, kind in (("cv", "CV"), ("lettre", "Lettre")):
            old = _path_of(x.get(key))
            if old is None:
                continue
            if old.name.startswith(f"{PREFIXE}_CV_ESG") or "Modèles" in str(old):
                continue  # generic ATS CVs: we do not touch them
            base = new_name(kind, x.get("poste", ""), x.get("entreprise", ""))
            if old.stem == base or old.stem.startswith(base + "_"):
                continue  # already renamed
            if not old.exists():
                # previous crash: file already renamed but link not updated
                for candp in sorted(old.parent.glob(base + "*" + old.suffix)):
                    if not a.dry:
                        x[key] = _url_of(candp)
                    upd += 1
                    break
                else:
                    miss += 1
                continue
            newp = free(old.parent, base, old.suffix, old)
            if newp == old:
                continue
            if not a.dry:
                try:
                    old.rename(newp)
                except FileExistsError:
                    miss += 1
                    continue
                tw_old, tw_new = old.with_suffix(".pdf"), newp.with_suffix(".pdf")
                if old.suffix.lower() == ".docx" and tw_old.exists() and not tw_new.exists():
                    tw_old.rename(tw_new)
                x[key] = _url_of(newp)
            ren += 1
        if not a.dry and (ren + upd) % 200 == 0 and (ren + upd):
            importlib.import_module("jobhunter.programmes.jutil").jwrite(QUEUE, q)  # checkpoint
    if not a.dry:
        importlib.import_module("jobhunter.programmes.jutil").jwrite(QUEUE, q)
    print(
        f"{'[DRY] ' if a.dry else ''}{ren} fichiers renommés · {upd} liens réalignés · {miss} introuvables"
    )
    rename_orphans(dry=a.dry)


if __name__ == "__main__":
    if "--test" in sys.argv:
        cases = [
            ("Analyste ESG / Investment (H/F) - CDI - Paris", "Analyste ESG"),
            ("Stage – Analyste Corporate Coverage – 6 mois – H/F", "Analyste Corporate Coverage"),
            (
                "Chargé d'Affaires Evaluation des Risques Sanitaires et Environnementaux H/F",
                "Chargé dAffaires Evaluation des Risques Sani",
            ),
            ("Data Analyst - F/H/X", "Data Analyst"),
        ]
        for src, _ in cases:
            print(f"  {src[:55]!r:58} -> {clean_poste(src)!r}")
        print(
            "name:",
            new_name(
                "CV", "Analyste ESG / Investment (H/F) - CDI - Paris", "AXA Investment Managers"
            ),
        )
    else:
        sys.exit(main())
