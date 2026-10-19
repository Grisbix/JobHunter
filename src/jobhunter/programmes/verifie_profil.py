"""Shows how the profile treats offer titles, without network.

    python JobHunter.pyw verifier-profil "Chargé de communication" "Développeur Java" ...
    python JobHunter.pyw verifier-profil            # titles drawn from the profile's domains

For each title: kept or set aside by the collection filter (title_ok), assigned domain,
and score 1-10 computed on the title alone (a real offer is scored with its
description, hence often higher). Used to tune profil/profil.json: a target job must
pass with a correct score, an off-target job must be set aside or score low.
"""

import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]  # console : TextIOWrapper

from jobhunter import profil  # noqa: E402

try:
    profil.charger()
except profil.ProfilAbsent as e:
    print(e)
    sys.exit(1)

from jobhunter import sources as job_sources  # noqa: E402
from jobhunter.programmes import scrape_jobs  # noqa: E402
from jobhunter.scoring import fit as ats_match  # noqa: E402


def intitules_du_profil():
    titres = []
    for d in profil.domaines():
        if d.get("libelle"):
            titres.append(d["libelle"])
    return titres or ["Assistant administratif"]


def main():
    titres = sys.argv[1:] or intitules_du_profil()
    print(f"Profil : {profil.FICHIER}\n")
    print(f"{'intitule':<48} {'collecte':<9} {'note':>4}  domaine")
    for t in titres:
        garde = job_sources.title_ok(t)
        fit, _ans, fin = ats_match.fit_detail(t, t)
        dom = scrape_jobs.classify_domaine(t)
        print(f"{t[:48]:<48} {'garde' if garde else 'ECARTE':<9} {fin:>4.1f}  {dom}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
