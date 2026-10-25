#!/usr/bin/env python3
"""metriques_hebdo.py — Weekly summary of the job search.

WHY THIS FILE EXISTS. The Monday summary was produced by a Hermes script
(`hermes/scripts/run_job_metrics_with_insight.py`) that read a `jobs` table of
veille.db and the vault's `Job Search/Applications/` folder. Both had disappeared: the
script exited with code 0 with zeros everywhere, and nobody could tell it from a quiet
week (noticed on 2026-10-07). The real data is here:

    Scripts/suivi.json            the applications      (read by suivi_io)
    Scripts/_logs/pipeline_*.log  what the pipeline merged each day

LIMIT TO KNOW. A tracking entry only keeps its LAST status and the date of that
status (`d`). An application that moved to "entretien" therefore no longer has its
sending date: "sent this week" counts the `postulé`/`relancé` dated within the week,
and answers are counted at the date of the answer. Some entries have no date, or a
`dd/mm` date without a year: they are counted separately rather than guessed.

Run: python JobHunter.pyw metriques_hebdo [--jours 7]
"""

import argparse
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from jobhunter import root as _racine
from jobhunter.storage import applications as suivi_io

LOGS = _racine.scripts() / "_logs"

EN_ATTENTE = ("postulé", "relancé")
REPONSES = ("entretien", "refus")
ENVOYEES = EN_ATTENTE + REPONSES
# Same threshold as relances.a_relancer() by default.
RELANCE_JOURS = 10

_MERGE = re.compile(r"Merge[^:\n]*: \+(\d+) nouvelles")
_LOG_DATE = re.compile(r"pipeline_(\d{4}-\d{2}-\d{2})_\d{4}\.log$")


def lire_date(texte, aujourdhui):
    """`YYYY-MM-DD` or `DD/MM` (current year, last year if that falls in the
    future). Returns None for a missing or unreadable date."""
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
    """Counts the applications. `suivi` is the dict from suivi_io.charger()."""
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
    """New offers merged per day, from the pipeline logs.
    A day without a log is a day the pipeline did not run."""
    debut = aujourdhui - timedelta(days=jours)
    par_jour = {}
    premier = aujourdhui
    for f in sorted(Path(dossier).glob("pipeline_*_*.log")):
        m = _LOG_DATE.search(f.name)
        if not m:
            continue
        d = datetime.strptime(m.group(1), "%Y-%m-%d").date()
        premier = min(premier, d)
        if not (debut < d <= aujourdhui):
            continue
        texte = f.read_text(encoding="utf-8", errors="replace")
        par_jour[d] = par_jour.get(d, 0) + sum(int(n) for n in _MERGE.findall(texte))
    # Not the days before the first run: a new installation is not missing them.
    manquants = [
        debut + timedelta(days=i)
        for i in range(1, jours + 1)
        if premier < debut + timedelta(days=i) and debut + timedelta(days=i) not in par_jour
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
    # "+N nouvelles" is counted at each merge, BEFORE the queue sorting:
    # an offer later set aside by tri_file appears in it anyway.
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
