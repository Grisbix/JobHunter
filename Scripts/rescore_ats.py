#!/usr/bin/env python3
"""rescore_ats.py — Recalcule ats_pct + skills_match DIRECTEMENT sur apply_queue.json
(sans Excel). Exigences offre = missions + PROFIL requis (+ description si récupérée).
Couverture = CV variant. Écrit le nouveau % dans la queue.

Run : python rescore_ats.py            # tout
      python rescore_ats.py --dry      # montre les changements sans écrire"""

import argparse
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

HERE = Path(__file__).resolve().parent
QUEUE = HERE / "apply_queue.json"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()

    import queue_io

    if a.dry:  # aucune ecriture : ni verrou, ni relecture
        _travail(queue_io.charger(), a)
        return 0
    try:
        # verrou + relecture FRAICHE dedans + ecriture atomique a la sortie
        with queue_io.transaction() as q:
            _travail(q, a)
    except queue_io.VerrouIndisponible as e:
        print(f"! {e}")
        return 3
    return 0


def _travail(q, a):
    from ats_match import fit_detail, score_offer

    try:
        from tailor_application import match_skills
    except Exception:
        match_skills = None

    changed = fit_changed = senior = 0
    dist = {}
    for x in q:
        # exigences = poste + missions + profil + description (si dispo)
        full = " ".join(str(x.get(k) or "") for k in ("poste", "missions", "profil", "description"))
        miss = " ".join(str(x.get(k) or "") for k in ("missions", "description"))
        prof = str(x.get("profil") or "")
        r = score_offer(
            dict(role=x.get("poste", ""), missions=miss, profil=prof, domaine=x.get("domaine", ""))
        )
        old = x.get("ats_pct")
        new = r.get("pct")
        if new != old:
            changed += 1
            if not a.dry:
                x["ats_pct"] = new
        # FIT recalculé avec critère EXPÉRIENCE (l'utilisateur junior : malus si N ans exigés)
        newfit, yrs, fin = fit_detail(full, x.get("poste", ""))
        oldfit = str(x.get("fit") or "")
        if str(newfit) != oldfit:
            fit_changed += 1
        if yrs >= 3:
            senior += 1
        if not a.dry:
            x["fit"] = newfit
            x["fit_fin"] = fin
            x["exp_requise"] = yrs  # années d'expérience exigées (0 = non précisé)
        if match_skills and not a.dry:
            try:
                x["skills_match"] = len(
                    match_skills(f"{x.get('poste', '')} {x.get('domaine', '')} {miss} {prof}")
                )
            except Exception:
                pass
        b = "—" if new is None else f"{(new // 20) * 20}-{(new // 20) * 20 + 19}"
        dist[b] = dist.get(b, 0) + 1

    print(f"{'[DRY] ' if a.dry else ''}{changed} ATS% + {fit_changed} fit re-scorés / {len(q)}")
    print(f"Offres exigeant ≥3 ans d'expérience (fit pénalisé) : {senior}")
    print("Distribution ATS% :", {k: dist[k] for k in sorted(dist)})


if __name__ == "__main__":
    sys.exit(main())
