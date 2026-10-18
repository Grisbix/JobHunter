#!/usr/bin/env python3
"""fix_letters.py — Réhabilite les lettres existantes (Lettres/Par_offre) :
  1. JUSTIFIE le corps + active la CÉSURE auto (texte justifié sans trous/rivières)
  2. adoucit les formules trop agressives de l'ancien générateur
  3. régénère les PDF jumeaux (LibreOffice)

Idempotent. Run : python fix_letters.py [--dry] [--no-pdf]"""

import argparse
import subprocess
import sys
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn

from jobhunter import racine as _racine

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = _racine.racine()

from jobhunter import chemins

LT_DIR = chemins.LT_PAR_OFFRE
SOFFICE = [
    r"C:\Program Files\LibreOffice\program\soffice.exe",
    r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
]

# formules agressives → version posée (préserve la suite de la phrase)
SOFTEN = [
    (
        "Concrètement, je peux mobiliser sans délai : ",
        "Au fil de ce parcours, je me suis notamment familiarisé avec ",
    ),
    ("— recoupent directement ce que j'ai pratiqué", "— font écho à ces expériences"),
    ("recoupent directement ce que j'ai pratiqué", "font écho à ces expériences"),
    ("Vivement intéressé par le poste", "Très intéressé par le poste"),
]
# lignes à ne PAS justifier (en-têtes, signature, objet…)
from jobhunter import profil as _P

_ID = _P.identite()
NO_JUST = tuple(
    x
    for x in (
        "madame, monsieur",
        "objet :",
        "à l'attention",
        _ID["nom"].lower(),
        _ID["ville"].lower(),
        "@",
        "06",
        "07",
        "+33",
    )
    if x
)


def fix_doc(path, dry=False):
    try:
        doc = Document(str(path))
    except Exception:
        return False
    changed = False
    # 1) césure auto
    try:
        s = doc.settings.element
        if s.find(qn("w:autoHyphenation")) is None:
            s.append(s.makeelement(qn("w:autoHyphenation"), {qn("w:val"): "true"}))
            changed = True
    except Exception:
        pass
    for p in doc.paragraphs:
        t = p.text.strip()
        if not t:
            continue
        low = t.lower()
        # 2) formules adoucies
        for old, new in SOFTEN:
            if old in p.text:
                for r in p.runs:
                    if old in r.text:
                        r.text = r.text.replace(old, new)
                        changed = True
        # 1b) justification du corps (pas les en-têtes/signature courts)
        if (
            len(t) > 90
            and not any(k in low for k in NO_JUST)
            and p.alignment != WD_ALIGN_PARAGRAPH.JUSTIFY
        ):
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            changed = True
    if changed and not dry:
        doc.save(str(path))
    return changed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--no-pdf", action="store_true")
    a = ap.parse_args()
    docs = sorted(LT_DIR.glob("*.docx"))
    print(f"{len(docs)} lettres docx à traiter…")
    touched = []
    for i, f in enumerate(docs):
        if fix_doc(f, dry=a.dry):
            touched.append(f)
        if (i + 1) % 300 == 0:
            print(f"  … {i + 1}/{len(docs)}")
    print(f"{'[DRY] ' if a.dry else ''}{len(touched)} lettres modifiées (justif/césure/formules)")
    if a.dry or a.no_pdf or not touched:
        return
    exe = next((s for s in SOFFICE if Path(s).exists()), None)
    pdfs = [f for f in touched if f.with_suffix(".pdf").exists()]
    if not exe:
        print(f"! LibreOffice absent — {len(pdfs)} PDF non régénérés.")
        return
    print(f"Régénération de {len(pdfs)} PDF…")
    ok = 0
    for i, f in enumerate(pdfs):
        try:
            r = subprocess.run(
                [exe, "--headless", "--convert-to", "pdf", "--outdir", str(LT_DIR), str(f)],
                capture_output=True,
                timeout=90,
            )
            ok += r.returncode == 0
        except Exception:
            pass
        if (i + 1) % 50 == 0:
            print(f"  … {i + 1}/{len(pdfs)}")
    print(f"PDF régénérés : {ok}/{len(pdfs)}")


if __name__ == "__main__":
    main()
