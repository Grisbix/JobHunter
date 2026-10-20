#!/usr/bin/env python3
"""refresh_letters.py — Refreshes ALL the letters (Lettres/Par_offre):
  1. DATE: replaces any existing French date with today's
     (adds a right-aligned "Le …" if there is none)
  2. ORDER: "Objet : …" BEFORE "Madame, Monsieur," (French standard)
  3. RECIPIENT: no known recruiter name → removes the company block
     ("<Entreprise>" + "À l'attention du service Recrutement")

Idempotent. Run: python JobHunter.pyw refresh_letters [--dry] [--no-pdf]"""

import argparse
import importlib
import re
import sys
from datetime import date
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH

from jobhunter import root as _racine
from jobhunter.documents import generated as _generes

sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]  # console : TextIOWrapper

ROOT = _racine.racine()

from jobhunter import paths as chemins

LT_DIR = chemins.LT_PAR_OFFRE
QUEUE = _racine.scripts() / "apply_queue.json"

MOIS = [
    "janvier",
    "février",
    "mars",
    "avril",
    "mai",
    "juin",
    "juillet",
    "août",
    "septembre",
    "octobre",
    "novembre",
    "décembre",
]
TODAY = f"Le {date.today().day} {MOIS[date.today().month - 1]} {date.today().year}"
DATE_RX = re.compile(
    r"^\s*(le\s+)?\d{1,2}(er)?\s+(janvier|f[ée]vrier|mars|avril|mai|juin|juillet"
    r"|ao[ûu]t|septembre|octobre|novembre|d[ée]cembre)\s+\d{4}\s*[.,]?\s*$",
    re.I,
)
ATTN_RX = re.compile(r"^\s*(à\s+l'attention|a\s+l'attention|attn)", re.I)


def _entreprises_by_letter():
    """letter stem -> company (from the queue) to remove the recipient line."""
    out = {}
    try:
        q = importlib.import_module("jobhunter.storage.queue").charger(QUEUE, descriptions=False)
        for x in q:
            u = x.get("lettre") or ""
            if u:
                p = importlib.import_module("jobhunter.programs.util").chemin_de(u)
                out[p.stem] = (x.get("entreprise") or "").strip()
    except Exception:
        pass
    return out


def _set_text(p, txt):
    for r in p.runs:
        r.text = ""
    (p.runs[0] if p.runs else p.add_run("")).text = txt


# ── Cleaning the job title in letters ALREADY written ────────────────────────
from jobhunter.documents.common import _de, titre_poste  # single source of the cleaning

# The two phrasings produced over time by the generator.
# We capture the title up to a FIXED anchor, not up to the end of the line:
# " … a retenu" and "… au sein de" bound the capture without swallowing the rest.
# re.S mandatory: some posting titles contain a line break
# ("… G4\nJob ID : 279556"). Without it, the pattern does not match at all and the
# paragraph stays as is. titre_poste() then reduces the blanks.
_OBJ_RX = re.compile(r"^(\s*Objet\s*:\s*Candidature au poste )(?:de |d')(.+?)\s*$", re.S)
_INTRO_RX = re.compile(r"^(.*?Votre annonce pour le poste )(?:de |d')(.+?)( a retenu.*)$", re.S)
_INTRO2_RX = re.compile(r"^(.*?Le poste )(?:de |d')(.+?)( au sein de .*)$", re.S)


def _nettoie_titre_dans(txt, ent=""):
    """Returns the corrected paragraph, or None if it does not contain a job title."""
    for rx in (_OBJ_RX, _INTRO_RX, _INTRO2_RX):
        m = rx.match(txt)
        if not m:
            continue
        brut = m.group(2)
        # old format: "… au poste de <role>, <COMPANY>". The current
        # generator no longer puts the company in the subject — we remove it here too.
        if ent:
            brut = re.sub(r"[,\s]+" + re.escape(ent) + r"\s*$", "", brut, flags=re.I)
        propre = titre_poste(brut)
        if not propre:
            # unusable title (postal address…): we do not make up an absurd sentence
            return "Objet : Candidature spontanée" if rx is _OBJ_RX else None
        reste = m.group(3) if rx.groups >= 3 else ""
        return m.group(1) + _de(propre) + reste
    return None


def fix_doc(path, ent="", dry=False):
    try:
        doc = Document(str(path))
    except Exception:
        return False
    paras = doc.paragraphs
    changed = False

    # 1) DATE: replaces the 1st date line; otherwise inserts before Objet/Madame
    has_date = False
    for p in paras[:10]:
        # old format: date buried in the multi-line header → replaces in the text
        if DATE_RX.match(p.text.strip()):
            if p.text.strip() != TODAY:
                _set_text(p, TODAY)
                p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                changed = True
            has_date = True
            break
        m = re.search(
            r"\d{1,2}(er)?\s+(janvier|f[ée]vrier|mars|avril|mai|juin|juillet"
            r"|ao[ûu]t|septembre|octobre|novembre|d[ée]cembre)\s+\d{4}",
            p.text,
            re.I,
        )
        if m and len(p.text) < 200:
            new = p.text[: m.start()] + TODAY.replace("Le ", "") + p.text[m.end() :]
            if new != p.text:
                _set_text(p, new)
                changed = True
            has_date = True
            break
    if not has_date:
        anchor = next(
            (
                p
                for p in paras[:14]
                if p.text.strip().lower().startswith(("objet", "madame, monsieur"))
            ),
            None,
        )
        if anchor is not None and not dry:
            np = anchor.insert_paragraph_before(TODAY)
            np.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            changed = True

    # 2) RECIPIENT: removes "À l'attention…" + the adjacent company-only line
    kill = []
    for i, p in enumerate(paras[:14]):
        t = p.text.strip()
        if ATTN_RX.match(t):
            kill.append(p)
            prev = paras[i - 1].text.strip() if i else ""
            if prev and len(prev) < 60 and (not ent or prev.lower().startswith(ent.lower()[:12])):
                kill.append(paras[i - 1])
        elif ent and t and t.lower() == ent.lower() and len(t) < 60:
            # company-only line (old format, after "Madame, Monsieur,")
            kill.append(p)
    for p in set(kill):
        p._element.getparent().remove(p._element)
        changed = True

    # 4) SUBJECT + INTRO: the raw title of the posting ("… (H/F) CDI - Paris") is
    #    not a job title. See tailor_application.titre_poste().
    for p in doc.paragraphs[:16]:
        neuf = _nettoie_titre_dans(p.text, ent)
        if neuf is not None and neuf != p.text:
            _set_text(p, neuf)
            changed = True

    # 3) ORDER: Objet BEFORE Madame, Monsieur
    paras = doc.paragraphs
    obj = next((p for p in paras[:14] if p.text.strip().lower().startswith("objet")), None)
    sal = next(
        (p for p in paras[:14] if p.text.strip().lower().startswith("madame, monsieur")), None
    )
    if obj is not None and sal is not None:
        oi = paras.index(obj)
        si = paras.index(sal)
        if si < oi:  # salutation before the subject → moves the subject just before it
            sal._element.addprevious(obj._element)
            changed = True

    if changed and not dry:
        try:
            doc.save(str(path))
            _generes.noter(path)  # our own edit, not a retouch
        except OSError:  # locked file (OneDrive) → we skip, can be rerun
            return False
    return changed


def main():
    # Inter-process lock: this program rewrites the ENTIRE queue. If
    # another one does it at the same time (scheduled task vs app), the last one
    # to write erases the other's work.
    if not importlib.import_module("jobhunter.programs.util").garder(QUEUE):
        return 3
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--no-pdf", action="store_true")
    a = ap.parse_args()
    ents = _entreprises_by_letter()
    docs = sorted(LT_DIR.glob("*.docx"))
    print(f"{len(docs)} lettres — date du jour : {TODAY}")
    n = 0
    for i, f in enumerate(docs):
        n += bool(fix_doc(f, ents.get(f.stem, ""), dry=a.dry))
        if (i + 1) % 300 == 0:
            print(f"  … {i + 1}")
    print(f"{'[DRY] ' if a.dry else ''}{n} lettres mises à jour (date/ordre/destinataire)")
    if a.dry or a.no_pdf:
        return
    # stale PDFs (mtime) regenerated
    import subprocess

    exe = next(
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
    todo = [
        f
        for f in docs
        if f.with_suffix(".pdf").exists()
        and f.with_suffix(".pdf").stat().st_mtime < f.stat().st_mtime
    ]
    if not exe:
        print(f"! LibreOffice absent — {len(todo)} PDF non resynchronisés")
        return
    print(f"Resynchronisation de {len(todo)} PDF…")
    ok = 0
    for i, f in enumerate(todo):
        try:
            r = subprocess.run(
                [exe, "--headless", "--convert-to", "pdf", "--outdir", str(LT_DIR), str(f)],
                capture_output=True,
                timeout=90,
            )
            ok += r.returncode == 0
        except Exception:
            pass
        if (i + 1) % 100 == 0:
            print(f"  … {i + 1}/{len(todo)}")
    print(f"PDF resynchronisés : {ok}/{len(todo)}")


if __name__ == "__main__":
    sys.exit(main())
