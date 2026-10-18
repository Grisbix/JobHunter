#!/usr/bin/env python3
"""regenere_docs.py — Refait lettres et CV avec le generateur actuel.

POURQUOI. Les corrections de redaction ne touchent que les lettres ECRITES
APRES elles. Celles deja sur disque gardent leur texte d'origine : citations
brutes de l'annonce, formes inclusives « un(e) », libelles de competence
recopies avec leurs barres obliques, « forecast » au milieu d'un texte
francais, jusqu'a quatre « et » dans une phrase. Les CV, eux, portaient
« valorisation (DCF, multiples) » sur leur ligne de competences.

CE QUI NE CHANGE PAS. Le NOM du fichier : il est repris tel quel de la file,
donc les liens de l'app et du suivi restent valides. Rien n'est ecrit dans
apply_queue.json — ce programme ne prend donc pas le verrou, et l'app peut
tourner pendant.

LA LANGUE EST RECALCULEE a chaque fois, comme le fait le generateur : une
offre en anglais recoit une lettre en anglais.

Les .docx d'origine sont suivis par git. En cas de doute :
    git checkout -- Lettres/Par_offre

Run :
  python JobHunter.pyw regenerer --dry
  python JobHunter.pyw regenerer                   # lettres
  python JobHunter.pyw regenerer --cv              # CV
  python JobHunter.pyw regenerer --cv --sans-pdf   # .docx seuls, PDF plus tard
"""

import argparse
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path

from jobhunter import racine as _racine

HERE = _racine.scripts()
ROOT = HERE.parent

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from jobhunter import chemins

SORTIE = {"lettre": chemins.LT_PAR_OFFRE, "cv": chemins.CV_PAR_OFFRE}

# LibreOffice converti en LOT. Une conversion a la fois coute 1,2 s dont
# l'essentiel est le demarrage du programme : 3336 lettres feraient plus d'une
# heure. Un seul demarrage pour 150 fichiers ramene ca a quelques minutes.
LOT_PDF = 150


def stem_de(url):
    """Le nom de fichier (sans extension) stocke dans la file.

    On le REPREND au lieu de le recalculer : new_name() peut avoir change
    depuis, et un nom different laisserait l'ancienne lettre sur le disque
    tandis que la file pointerait vers la nouvelle. Deux fichiers, un lien
    juste, un orphelin.
    """
    u = (url or "").strip()
    if not u:
        return ""
    if u.startswith("file:///"):
        u = urllib.parse.unquote(u[8:])
    return Path(u).stem


def convertir(fichiers, exe, dossier):
    """Les .docx -> .pdf, par lots. Rend le nombre de PDF produits."""
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
    from jobhunter.scoring.langue import langue_offre
    from jobhunter.stockage import file as queue_io

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
    offres_de = {}  # stem -> offre, pour reprendre un CV qui deborde
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
        # REPRISES. OneDrive tient les fichiers qu'il vient de synchroniser, et
        # l'ecriture echoue alors en « OSError: [Errno 22] Invalid argument »
        # sur un chemin pourtant valide. Une passe juste apres une autre en a
        # perdu 49 sur 3337 ainsi. Le meme remede que jutil.jwrite : attendre
        # et recommencer, l'accroche se relache en une seconde ou deux.
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
        # UNE PAGE, TOUJOURS. Les faits automatiques (cv_auto) ajoutent des
        # lignes ; la conversion par lots ne regarde pas les pages. On reprend
        # un par un ceux qui debordent, avec les allegements de CV/Faits.json.
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
