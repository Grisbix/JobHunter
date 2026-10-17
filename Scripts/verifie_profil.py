"""Montre comment le profil traite des intitules d'offre, sans reseau.

    python Scripts/verifie_profil.py "Chargé de communication" "Développeur Java" ...
    python Scripts/verifie_profil.py            # intitules tires des domaines du profil

Pour chaque intitule : garde ou ecarte par le filtre de collecte (title_ok), domaine
attribue, et note 1-10 calculee sur l'intitule seul (une vraie offre est notee avec sa
description, donc souvent plus haut). Sert a regler profil/profil.json : un metier vise
doit passer avec une note correcte, un metier hors cible doit etre ecarte ou noter bas.
"""

import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import profil  # noqa: E402

try:
    profil.charger()
except profil.ProfilAbsent as e:
    print(e)
    sys.exit(1)

import ats_match  # noqa: E402
import job_sources  # noqa: E402
import scrape_jobs  # noqa: E402


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
