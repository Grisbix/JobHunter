#!/usr/bin/env python3
"""metriques_hebdo.py — Bilan hebdomadaire de la recherche d'emploi.

POURQUOI CE FICHIER EXISTE. Le bilan du lundi était produit par un script
Hermes (`hermes/scripts/run_job_metrics_with_insight.py`) qui lisait une table
`jobs` de veille.db et le dossier `Job Search/Applications/` du vault. Les deux
avaient disparu : le script sortait en code 0 avec des zéros partout, et
personne ne pouvait le distinguer d'une semaine creuse (constaté le
2026-10-07). Les vraies données sont ici :

    Scripts/suivi.json            les candidatures      (lu par suivi_io)
    Scripts/_logs/pipeline_*.log  ce que le pipeline a fusionné chaque jour

LIMITE À CONNAÎTRE. Une entrée du suivi ne garde que son DERNIER statut et la
date de ce statut (`d`). Une candidature passée à « entretien » n'a donc plus
sa date d'envoi : « envoyées cette semaine » compte les `postulé`/`relancé`
datés de la semaine, et les réponses se comptent à la date de la réponse.
Certaines entrées n'ont pas de date, ou une date `jj/mm` sans année : elles
sont comptées à part plutôt que devinées.

Run : python metriques_hebdo.py [--jours 7]
"""

import argparse
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from jobhunter import racine as _racine
from jobhunter.stockage import suivi as suivi_io

LOGS = _racine.scripts() / "_logs"

EN_ATTENTE = ("postulé", "relancé")
REPONSES = ("entretien", "refus")
ENVOYEES = EN_ATTENTE + REPONSES
# Même seuil que relances.a_relancer() par défaut.
RELANCE_JOURS = 10

_MERGE = re.compile(r"Merge[^:\n]*: \+(\d+) nouvelles")
_LOG_DATE = re.compile(r"pipeline_(\d{4}-\d{2}-\d{2})_\d{4}\.log$")


def lire_date(texte, aujourdhui):
    """`AAAA-MM-JJ` ou `JJ/MM` (année courante, l'an passé si ça tombe dans le
    futur). Rend None pour une date absente ou illisible."""
    texte = (texte or "").strip()
    try:
        return datetime.strptime(texte, "%Y-%m-%d").date()
    except ValueError:
        pass
    try:
        j, m = (int(x) for x in texte.split("/"))
        d = date(aujourdhui.year, m, j)
    except (ValueError, TypeError):
        return None
    return d if d <= aujourdhui else date(aujourdhui.year - 1, m, j)


def bilan_suivi(suivi, aujourdhui, jours=7):
    """Compte les candidatures. `suivi` est le dict de suivi_io.charger()."""
    debut = aujourdhui - timedelta(days=jours)
    debut_30 = aujourdhui - timedelta(days=30)
    b = {
        "statuts": {},
        "envoyees_periode": 0,
        "reponses_30j": 0,
        "en_attente": 0,
        "a_relancer": [],
        "sans_date": 0,
        "envoyees_total": 0,
        "reponses_total": 0,
    }
    for oid, rec in suivi.items():
        rec = rec or {}
        s = str(rec.get("s") or "").strip().lower()
        b["statuts"][s or "(aucun)"] = b["statuts"].get(s or "(aucun)", 0) + 1
        if s not in ENVOYEES:
            continue
        b["envoyees_total"] += 1
        d = lire_date(rec.get("d"), aujourdhui)
        if d is None:
            b["sans_date"] += 1
        if s in REPONSES:
            b["reponses_total"] += 1
            if d and d > debut_30:
                b["reponses_30j"] += 1
            continue
        b["en_attente"] += 1
        if d and d > debut:
            b["envoyees_periode"] += 1
        if d and (aujourdhui - d).days >= RELANCE_JOURS:
            b["a_relancer"].append((oid, (aujourdhui - d).days))
    b["a_relancer"].sort(key=lambda t: -t[1])
    b["taux_reponse"] = b["reponses_total"] / b["envoyees_total"] if b["envoyees_total"] else None
    return b


def bilan_pipeline(dossier, aujourdhui, jours=7):
    """Offres nouvelles fusionnées par jour, d'après les journaux du pipeline.
    Un jour sans journal est un jour où le pipeline n'a pas tourné."""
    debut = aujourdhui - timedelta(days=jours)
    par_jour = {}
    for f in sorted(Path(dossier).glob("pipeline_*_*.log")):
        m = _LOG_DATE.search(f.name)
        if not m:
            continue
        d = datetime.strptime(m.group(1), "%Y-%m-%d").date()
        if not (debut < d <= aujourdhui):
            continue
        texte = f.read_text(encoding="utf-8", errors="replace")
        par_jour[d] = par_jour.get(d, 0) + sum(int(n) for n in _MERGE.findall(texte))
    manquants = [
        debut + timedelta(days=i)
        for i in range(1, jours + 1)
        if debut + timedelta(days=i) not in par_jour
    ]
    return {"par_jour": par_jour, "total": sum(par_jour.values()), "jours_sans_run": manquants}


def rapport(bs, bp, aujourdhui, jours=7):
    l = [f"# Bilan recherche d'emploi — {aujourdhui.isoformat()} ({jours} derniers jours)", ""]
    l.append(f"Candidatures envoyées sur la période : **{bs['envoyees_periode']}**")
    l.append(f"En attente de réponse : {bs['en_attente']}")
    l.append(f"Réponses sur 30 jours : {bs['reponses_30j']}")
    if bs["taux_reponse"] is None:
        l.append("Taux de réponse cumulé : — (aucune candidature envoyée)")
    else:
        l.append(
            f"Taux de réponse cumulé : {bs['taux_reponse']:.0%} "
            f"({bs['reponses_total']}/{bs['envoyees_total']})"
        )
    if bs["sans_date"]:
        l.append(
            f"⚠ {bs['sans_date']} candidature(s) sans date exploitable, hors des comptes datés"
        )
    l.append("")
    l.append(f"## À relancer (≥ {RELANCE_JOURS} jours) : {len(bs['a_relancer'])}")
    for oid, age in bs["a_relancer"][:15]:
        l.append(f"- {oid.replace('|', ' — ')} ({age} j)")
    l.append("")
    l.append("## Statuts du suivi")
    for s, n in sorted(bs["statuts"].items(), key=lambda t: -t[1]):
        l.append(f"- {s} : {n}")
    l.append("")
    # « +N nouvelles » est compté à chaque fusion, AVANT le tri de la file :
    # une offre écartée ensuite par tri_file y figure quand même.
    l.append(f"## Pipeline : {bp['total']} offres nouvelles fusionnées (avant tri)")
    for d, n in sorted(bp["par_jour"].items()):
        l.append(f"- {d.isoformat()} : +{n}")
    if bp["jours_sans_run"]:
        l.append(
            "⚠ Pas de journal du pipeline : "
            + ", ".join(d.isoformat() for d in bp["jours_sans_run"])
        )
    return "\n".join(l)


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--jours", type=int, default=7)
    a = ap.parse_args()
    auj = date.today()
    print(
        rapport(
            bilan_suivi(suivi_io.charger(), auj, a.jours),
            bilan_pipeline(LOGS, auj, a.jours),
            auj,
            a.jours,
        )
    )


if __name__ == "__main__":
    main()
