#!/usr/bin/env python3
"""relecture.py — Relit les lettres générées et signale ce qui cloche, sans rien modifier.

Une seconde passe, sans le contexte de la rédaction (jobhunter.documents.relecture) :
dévalorisation, superlatif, « excellent » pour une langue, ponctuation, redites, autre
entreprise nommée, destinataire absent de l'annonce, texte venu d'une annonce piégée.
On corrige à la main, dans `Lettres/Sur_mesure/<entreprise>__<poste>.txt`.

Les candidatures déjà dans le suivi sont ignorées : leur lettre est partie.

Run :
  python JobHunter.pyw relecture                 # les lettres des offres de fit >= 8
  python JobHunter.pyw relecture --fit 0         # toutes
  python JobHunter.pyw relecture --url acme      # les offres dont l'URL ou le nom contient « acme »
"""

import argparse
import collections
import sys
from urllib.parse import urlparse

from jobhunter.documents.controle import lire_pdf, piece_finale
from jobhunter.documents.relecture import relire, texte
from jobhunter.liens import chemin_de
from jobhunter.profil import identite
from jobhunter.stockage import file as queue_io
from jobhunter.stockage import suivi as suivi_io


def _hote(url: str) -> str:
    h = urlparse(url or "").netloc.lower()
    return h[4:] if h.startswith("www.") else h


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="relit les lettres (lecture seule)")
    ap.add_argument("--fit", type=int, default=8, help="seulement les offres de fit >= N")
    ap.add_argument("--url", help="seulement les offres dont l'URL ou le nom contient ce texte")
    a = ap.parse_args(argv)

    suivi = suivi_io.charger()
    ident = identite()
    connus = [ident.get("email", ""), ident.get("linkedin", "")]
    offres = queue_io.charger()
    entreprises = {str(o.get("entreprise") or "") for o in offres if o.get("lettre")}
    cibles = []
    for o in offres:
        if not o.get("lettre") or queue_io.oid(o) in suivi:
            continue
        if a.url:
            cle = f"{o.get('url', '')} {o.get('entreprise', '')} {o.get('poste', '')}".lower()
            if a.url.lower() not in cle:
                continue
        elif int(o.get("fit") or 0) < a.fit:
            continue
        cibles.append(o)

    compte: collections.Counter[str] = collections.Counter()
    a_revoir = lues = 0
    for o in sorted(cibles, key=lambda x: -int(x.get("fit") or 0)):
        # Le .docx est la source de la lettre ; à défaut, le texte du PDF final.
        chemin = chemin_de(o.get("lettre"))
        if chemin is None:
            continue
        docx = chemin.with_suffix(".docx")
        if docx.exists():
            contenu = texte(docx)
        else:
            pdf = piece_finale(chemin)
            lu = lire_pdf(pdf) if pdf is not None and pdf.suffix == ".pdf" else None
            if lu is None:
                continue
            contenu = lu[0]
        lues += 1
        remarques = relire(
            contenu,
            entreprise=str(o.get("entreprise") or ""),
            annonce=str(o.get("description") or ""),
            autres_entreprises=entreprises,
            connus=connus + [_hote(str(o.get("url") or ""))],
        )
        if not remarques:
            continue
        a_revoir += 1
        print(f"\n■ {o.get('entreprise')} — {o.get('poste')}  (fit {o.get('fit')})")
        for r in remarques:
            compte[r.regle] += 1
            print(f"  · {r.regle} : {r.extrait}")
            print(f"      → {r.conseil}")
    print(f"\n{lues} lettre(s) relue(s) sur {len(cibles)}, {a_revoir} à revoir.")
    for regle, n in compte.most_common():
        print(f"  {regle:<15} {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
