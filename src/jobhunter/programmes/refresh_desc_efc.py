#!/usr/bin/env python3
"""refresh_desc_efc.py — Relit la description eFC des offres dont le lien a ete
promu vers eFinancialCareers mais dont le TEXTE est reste celui de LinkedIn.

POURQUOI. Promouvoir le lien sans reprendre la description laisse l'offre
decrite par la source la moins informative. CNP « EXPERT INVESTISSEMENT
RESPONSABLE ET INDICATEURS ESG » en est l'exemple : la version LinkedIn ne dit
rien du niveau attendu, celle d'eFC exige « Plus de 10 ans ». L'offre restait a
fit 10 avec exp_requise = 0 — le detecteur d'experience fonctionne, il n'avait
simplement jamais lu la phrase.

merge_into_queue reprend desormais la description a la promotion. Ce programme
repare les offres deja en file, que le scan ne repassera pas.

Run :
  python refresh_desc_efc.py --dry
  python refresh_desc_efc.py
"""

import argparse
import sys
import time

from jobhunter import racine as _racine

HERE = _racine.scripts()

sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)


def _a_reprendre(o):
    """Offre eFC dont la description vient visiblement d'ailleurs.

    « Show less » est le libelle du bouton de repli de LinkedIn : sa presence en
    fin de texte signe la provenance, quel que soit le lien porte par l'offre.
    """
    if "efinancial" not in (o.get("url") or "").lower():
        return False
    return (o.get("description") or "").rstrip().endswith(("Show less", "Voir moins"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()

    import httpx

    from jobhunter.scoring.fit import fit_detail
    from jobhunter.sources import EFC_DELAI, _efc_fiche, _strip_html
    from jobhunter.stockage import file as queue_io

    if a.dry:
        q = queue_io.charger()
        cibles = [o for o in q if _a_reprendre(o)]
        print(f"{len(cibles)} offre(s) eFC decrite(s) par une autre source")
        for o in cibles:
            print(
                f"  fit {o.get('fit')} exp {o.get('exp_requise')}  "
                f"{(o.get('entreprise') or '')[:24]:24} {(o.get('poste') or '')[:44]}"
            )
        print("[DRY] rien n'a ete ecrit.")
        return 0

    try:
        with queue_io.transaction() as q:
            cibles = [o for o in q if _a_reprendre(o)]
            print(f"{len(cibles)} offre(s) a relire ({EFC_DELAI} s entre chaque)")
            n = 0
            with httpx.Client(follow_redirects=True) as client:
                for i, o in enumerate(cibles):
                    if i:
                        time.sleep(EFC_DELAI)  # crawl-delay: 10
                    jp = _efc_fiche(o["url"], client)
                    if not jp:
                        print(f"  ~ illisible : {(o.get('poste') or '')[:44]}")
                        continue
                    t = _strip_html(str(jp.get("description") or ""))
                    if len(t) < 200:
                        continue
                    av_f, av_e = o.get("fit"), o.get("exp_requise")
                    o["description"] = t
                    o["fit"], o["exp_requise"], o["fit_fin"] = fit_detail(
                        f"{o.get('poste', '')} {t}", o.get("poste", "")
                    )
                    n += 1
                    print(
                        f"  fit {av_f} -> {o['fit']} · exp {av_e} -> {o['exp_requise']}  "
                        f"{(o.get('entreprise') or '')[:22]:22} {(o.get('poste') or '')[:40]}"
                    )
            print(f"\n{n} description(s) reprise(s) depuis eFinancialCareers.")
    except queue_io.VerrouIndisponible as e:
        print(f"! {e}")
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
