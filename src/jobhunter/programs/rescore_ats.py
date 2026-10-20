#!/usr/bin/env python3
"""rescore_ats.py — Recomputes ats_pct + skills_match DIRECTLY on apply_queue.json
(without Excel). Offer requirements = missions + required PROFILE (+ description if fetched).
Coverage = CV variant. Writes the new % into the queue.

Run : python JobHunter.pyw rescore_ats            # everything
      python JobHunter.pyw rescore_ats --dry      # shows the changes without writing"""

import argparse
import sys

from jobhunter import root as _racine

sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]  # console : TextIOWrapper

HERE = _racine.scripts()
QUEUE = HERE / "apply_queue.json"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()

    from jobhunter.storage import queue as queue_io

    if a.dry:  # aucune ecriture : ni verrou, ni relecture
        _travail(queue_io.charger(), a)
        return 0
    try:
        # lock + FRESH re-read inside it + atomic write on exit
        with queue_io.transaction() as q:
            _travail(q, a)
    except queue_io.VerrouIndisponible as e:
        print(f"! {e}")
        return 3
    return 0


def _travail(q, a):
    from jobhunter.scoring.fit import fit_detail, score_offer

    try:
        from jobhunter.documents import match_skills
    except Exception:
        match_skills = None

    changed = fit_changed = senior = 0
    dist = {}
    for x in q:
        # requirements = job + missions + profile + description (if available)
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
        # FIT recomputed with the EXPERIENCE criterion (junior user: penalty if N years are required)
        newfit, yrs, fin = fit_detail(full, x.get("poste", ""))
        oldfit = str(x.get("fit") or "")
        if str(newfit) != oldfit:
            fit_changed += 1
        if yrs >= 3:
            senior += 1
        if not a.dry:
            x["fit"] = newfit
            x["fit_fin"] = fin
            x["exp_requise"] = yrs  # years of experience required (0 = not specified)
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
