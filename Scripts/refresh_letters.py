#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""refresh_letters.py — Rafraîchit TOUTES les lettres (Lettres/Par_offre) :
  1. DATE : remplace toute date française existante par celle du jour
     (ajoute « Le … » aligné à droite si aucune)
  2. ORDRE : « Objet : … » AVANT « Madame, Monsieur, » (standard français)
  3. DESTINATAIRE : pas de nom de recruteur connu → retire le bloc entreprise
     (« <Entreprise> » + « À l'attention du service Recrutement »)

Idempotent. Run : python refresh_letters.py [--dry] [--no-pdf]"""
import sys, re, json, argparse
from pathlib import Path
from datetime import date
from urllib.parse import unquote
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import chemins
LT_DIR = chemins.LT_PAR_OFFRE
QUEUE = Path(__file__).resolve().parent / "apply_queue.json"

MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
        "août", "septembre", "octobre", "novembre", "décembre"]
TODAY = f"Le {date.today().day} {MOIS[date.today().month - 1]} {date.today().year}"
DATE_RX = re.compile(r"^\s*(le\s+)?\d{1,2}(er)?\s+(janvier|f[ée]vrier|mars|avril|mai|juin|juillet"
                     r"|ao[ûu]t|septembre|octobre|novembre|d[ée]cembre)\s+\d{4}\s*[.,]?\s*$", re.I)
ATTN_RX = re.compile(r"^\s*(à\s+l'attention|a\s+l'attention|attn)", re.I)


def _entreprises_by_letter():
    """stem lettre -> entreprise (depuis la queue) pour retirer la ligne destinataire."""
    out = {}
    try:
        q = __import__("queue_io").charger(QUEUE, descriptions=False)
        for x in q:
            u = x.get("lettre") or ""
            if u:
                p = __import__("jutil").chemin_de(u)
                out[p.stem] = (x.get("entreprise") or "").strip()
    except Exception:
        pass
    return out


def _set_text(p, txt):
    for r in p.runs: r.text = ""
    (p.runs[0] if p.runs else p.add_run("")).text = txt


# ── Nettoyage du titre de poste dans les lettres DEJA ecrites ────────────────
from tailor_application import titre_poste, _de   # source unique du nettoyage

# Les deux formulations produites au fil du temps par le generateur.
# On capture le titre jusqu'a un ancrage FIXE, pas jusqu'a la fin de ligne :
# «  … a retenu » et « … au sein de » bornent la capture sans avaler la suite.
# re.S obligatoire : certains titres d'annonce contiennent un saut de ligne
# (« … G4\nJob ID : 279556 »). Sans lui, le motif ne matche pas du tout et le
# paragraphe reste tel quel. titre_poste() reduit ensuite les blancs.
_OBJ_RX = re.compile(r"^(\s*Objet\s*:\s*Candidature au poste )(?:de |d')(.+?)\s*$", re.S)
_INTRO_RX = re.compile(r"^(.*?Votre annonce pour le poste )(?:de |d')(.+?)( a retenu.*)$", re.S)
_INTRO2_RX = re.compile(r"^(.*?Le poste )(?:de |d')(.+?)( au sein de .*)$", re.S)


def _nettoie_titre_dans(txt, ent=""):
    """Renvoie le paragraphe corrige, ou None s'il ne contient pas de titre de poste."""
    for rx in (_OBJ_RX, _INTRO_RX, _INTRO2_RX):
        m = rx.match(txt)
        if not m:
            continue
        brut = m.group(2)
        # ancien format : « … au poste de <role>, <ENTREPRISE> ». Le generateur
        # actuel ne met plus l'entreprise dans l'objet — on la retire ici aussi.
        if ent:
            brut = re.sub(r"[,\s]+" + re.escape(ent) + r"\s*$", "", brut, flags=re.I)
        propre = titre_poste(brut)
        if not propre:
            # titre inexploitable (adresse postale…) : on ne fabrique pas une phrase absurde
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

    # 1) DATE : remplace la 1re ligne-date ; sinon insère avant Objet/Madame
    has_date = False
    for p in paras[:10]:
        # ancien format : date noyée dans l'en-tête multiligne → remplace dans le texte
        if DATE_RX.match(p.text.strip()):
            if p.text.strip() != TODAY:
                _set_text(p, TODAY); p.alignment = WD_ALIGN_PARAGRAPH.RIGHT; changed = True
            has_date = True; break
        m = re.search(r"\d{1,2}(er)?\s+(janvier|f[ée]vrier|mars|avril|mai|juin|juillet"
                      r"|ao[ûu]t|septembre|octobre|novembre|d[ée]cembre)\s+\d{4}", p.text, re.I)
        if m and len(p.text) < 200:
            new = p.text[:m.start()] + TODAY.replace("Le ", "") + p.text[m.end():]
            if new != p.text:
                _set_text(p, new); changed = True
            has_date = True; break
    if not has_date:
        anchor = next((p for p in paras[:14]
                       if p.text.strip().lower().startswith(("objet", "madame, monsieur"))), None)
        if anchor is not None and not dry:
            np = anchor.insert_paragraph_before(TODAY)
            np.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            changed = True

    # 2) DESTINATAIRE : retire « À l'attention… » + la ligne entreprise seule adjacente
    kill = []
    for i, p in enumerate(paras[:14]):
        t = p.text.strip()
        if ATTN_RX.match(t):
            kill.append(p)
            prev = paras[i - 1].text.strip() if i else ""
            if prev and len(prev) < 60 and (not ent or prev.lower().startswith(ent.lower()[:12])):
                kill.append(paras[i - 1])
        elif ent and t and t.lower() == ent.lower() and len(t) < 60:
            # ligne entreprise seule (ancien format, après « Madame, Monsieur, »)
            kill.append(p)
    for p in set(kill):
        p._element.getparent().remove(p._element)
        changed = True

    # 4) OBJET + INTRO : le titre brut de l'annonce (« … (H/F) CDI - Paris ») n'est
    #    pas un intitulé de poste. Voir tailor_application.titre_poste().
    for p in doc.paragraphs[:16]:
        neuf = _nettoie_titre_dans(p.text, ent)
        if neuf is not None and neuf != p.text:
            _set_text(p, neuf)
            changed = True

    # 3) ORDRE : Objet AVANT Madame, Monsieur
    paras = doc.paragraphs
    obj = next((p for p in paras[:14] if p.text.strip().lower().startswith("objet")), None)
    sal = next((p for p in paras[:14] if p.text.strip().lower().startswith("madame, monsieur")), None)
    if obj is not None and sal is not None:
        oi = paras.index(obj); si = paras.index(sal)
        if si < oi:   # salutation avant l'objet → déplace l'objet juste avant
            sal._element.addprevious(obj._element)
            changed = True

    if changed and not dry:
        try:
            doc.save(str(path))
        except OSError:   # fichier verrouillé (OneDrive) → on saute, relançable
            return False
    return changed


def main():
    # Verrou inter-processus : ce programme reecrit la queue ENTIERE. Si un
    # autre le fait en meme temps (tache planifiee vs app), le dernier qui
    # ecrit efface le travail de l'autre.
    if not __import__('jutil').garder(QUEUE):
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
            print(f"  … {i+1}")
    print(f"{'[DRY] ' if a.dry else ''}{n} lettres mises à jour (date/ordre/destinataire)")
    if a.dry or a.no_pdf:
        return
    # PDF périmés (mtime) régénérés
    import subprocess
    exe = next((s for s in (r"C:\Program Files\LibreOffice\program\soffice.exe",
                            r"C:\Program Files (x86)\LibreOffice\program\soffice.exe")
                if Path(s).exists()), None)
    todo = [f for f in docs if f.with_suffix(".pdf").exists()
            and f.with_suffix(".pdf").stat().st_mtime < f.stat().st_mtime]
    if not exe:
        print(f"! LibreOffice absent — {len(todo)} PDF non resynchronisés"); return
    print(f"Resynchronisation de {len(todo)} PDF…")
    ok = 0
    for i, f in enumerate(todo):
        try:
            r = subprocess.run([exe, "--headless", "--convert-to", "pdf",
                                "--outdir", str(LT_DIR), str(f)], capture_output=True, timeout=90)
            ok += (r.returncode == 0)
        except Exception:
            pass
        if (i + 1) % 100 == 0:
            print(f"  … {i+1}/{len(todo)}")
    print(f"PDF resynchronisés : {ok}/{len(todo)}")


if __name__ == "__main__":
    sys.exit(main())