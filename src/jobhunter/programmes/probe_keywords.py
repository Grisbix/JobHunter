#!/usr/bin/env python3
"""probe_keywords.py — Mesure le RENDEMENT réel de mots-clés de recherche.

Inventer une liste de mots-clés ne dit rien : seul compte ce qu'ils rapportent.
Ce script interroge la recherche publique LinkedIn pour chaque candidat et
distingue :
  - trouvées : offres passant le filtre anti-bruit (title_ok)
  - NOUVELLES : absentes de apply_queue.json (dédup par URL normalisée)

Un mot-clé qui ne ramène que du déjà-vu ne sert à rien ; c'est « nouvelles »
qui décide s'il vaut la peine d'être ajouté au scan.

Ne modifie RIEN. Ajout au scan = via sources_config.json (voir --config).

Run :
  python JobHunter.pyw probe_keywords                       # liste candidate intégrée
  python JobHunter.pyw probe_keywords --kw "analyste climat,finance verte"
  python JobHunter.pyw probe_keywords --min-new 3 --config  # ajoute les rentables à la config
"""

import argparse
import importlib
import json
import sys
import time

from jobhunter import racine as _racine

sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

HERE = _racine.scripts()
QUEUE = HERE / "apply_queue.json"
CFG = HERE / "sources_config.json"

# Vocabulaire réel des offres ESG/finance FR+EN pour un profil junior.
# Regroupé par thème pour que la sortie soit lisible.
CANDIDATS = {
    "ESG / réglementaire": [
        "notation esg",
        "esg controller",
        "esg risk analyst",
        "reporting csrd",
        "taxonomie verte",
        "double matérialité",
        "analyste climat",
        "risques climatiques",
        "performance extra-financière",
        "conformité esg",
        "analyste rse",
        "reporting rse",
        "article 9 fonds",
        "pai reporting",
    ],
    "Finance durable / impact": [
        "finance verte",
        "obligations vertes",
        "green finance",
        "impact investing",
        "investissement responsable",
        "investissement à impact",
        "sustainable investing",
        "sustainability analyst",
        "sustainability reporting",
        "transition énergétique analyste",
        "biodiversité finance",
    ],
    "Carbone / climat": [
        "bilan carbone",
        "empreinte carbone",
        "trajectoire carbone",
        "comptabilité carbone",
        "analyste décarbonation",
        "climate analyst",
    ],
    "Finance junior": [
        "analyste financier junior",
        "analyste risques junior",
        "analyste crédit junior",
        "contrôleur de gestion junior",
        "analyste quantitatif junior",
        "middle office junior",
        "reporting réglementaire",
        "analyste conformité",
    ],
    "Data / quant": [
        "data analyst finance",
        "analyste données climat",
        "esg quant",
        "analyste data esg",
    ],
}

# Profil « construit son propre outillage avec Claude Code » : dev assisté par IA,
# agents, LLM. Testé séparément (--set ia) car c'est un autre marché que l'ESG.
CANDIDATS_IA = {
    "Vibe coding / dev assisté IA": [
        "vibe coding",
        "ai engineer",
        "ingénieur ia",
        "llm engineer",
        "prompt engineer",
        "ingénieur prompt",
        "développeur ia",
        "ai software engineer",
        "copilot",
        "github copilot",
    ],
    "Agents / LLM / RAG": [
        "ai agent",
        "agents ia",
        "agentic",
        "llm",
        "rag",
        "langchain",
        "llmops",
        "fine-tuning",
    ],
    "IA générative — produit & conseil": [
        "ia générative",
        "generative ai",
        "genai",
        "consultant ia",
        "ai product manager",
        "chef de projet ia",
        "ai automation",
        "automatisation ia",
        "ai analyst",
        "transformation ia",
    ],
}


def norm_url(u):
    from jobhunter.sources import _norm_url

    return _norm_url(u)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kw", help="liste CSV de mots-clés (sinon liste intégrée)")
    ap.add_argument(
        "--set",
        choices=["esg", "ia"],
        default="esg",
        help="jeu de candidats intégré à tester (déf. esg)",
    )
    ap.add_argument("--pages", type=int, default=1)
    ap.add_argument("--days", type=int, default=30, help="fraîcheur LinkedIn (jours)")
    ap.add_argument(
        "--min-new",
        type=int,
        default=3,
        help="seuil de nouvelles offres pour juger un mot-clé rentable",
    )
    # LEÇON du 29/07 : juger sur la NOUVEAUTÉ seule a fait entrer 169 offres
    # hors sujet sur 201 (15 % de pertinence). Un mot-clé n'est bon que s'il
    # ramène du nouveau ET du pertinent → on exige les deux.
    ap.add_argument(
        "--relevant-rx",
        default="",
        help="regex sur l'intitulé : un mot-clé n'est retenu que si ses "
        "nouvelles offres matchent (mesure la PERTINENCE, pas que le volume)",
    )
    ap.add_argument(
        "--min-rel",
        type=int,
        default=1,
        help="nb mini de nouvelles offres PERTINENTES (si --relevant-rx)",
    )
    ap.add_argument(
        "--config", action="store_true", help="AJOUTE les mots-clés rentables à sources_config.json"
    )
    a = ap.parse_args()

    import re

    rx = re.compile(a.relevant_rx, re.I) if a.relevant_rx else None

    from jobhunter.sources import linkedin_guest_search

    q = (
        importlib.import_module("jobhunter.stockage.file").charger(QUEUE, descriptions=False)
        if QUEUE.exists()
        else []
    )
    have = {norm_url(o.get("url")) for o in q if o.get("url")}
    cfg = json.loads(CFG.read_text(encoding="utf-8")) if CFG.exists() else {"keywords": []}
    deja = {k.lower() for k in cfg.get("keywords", [])}
    print(f"queue : {len(q)} offres | mots-clés déjà au scan : {len(deja)}")

    if a.kw:
        groupes = {"(demandés)": [s.strip() for s in a.kw.split(",") if s.strip()]}
    elif a.set == "ia":
        groupes = CANDIDATS_IA
    else:
        groupes = CANDIDATS

    res = []
    for theme, kws in groupes.items():
        print(f"\n── {theme} ──")
        for kw in kws:
            if kw.lower() in deja:
                print(f"  ·  {kw:<34} déjà au scan")
                continue
            try:
                hits = linkedin_guest_search(kw, pages=a.pages, days=a.days)
            except Exception as e:
                print(f"  ✖  {kw:<34} erreur {type(e).__name__}")
                continue
            urls = {norm_url(h["url"]) for h in hits}
            new = urls - have
            news = [h for h in hits if norm_url(h["url"]) in new]
            rel = [h for h in news if rx.search(h["titre"])] if rx else news
            res.append(
                {
                    "kw": kw,
                    "theme": theme,
                    "trouvees": len(hits),
                    "nouvelles": len(new),
                    "pertinentes": len(rel),
                }
            )
            ok = len(new) >= a.min_new and (not rx or len(rel) >= a.min_rel)
            flag = "✅" if ok else ("~ " if new else "  ")
            ex = rel or news
            ex = ex[0]["titre"] if ex else ""
            pert = f"| {len(rel):>2} PERTIN. " if rx else ""
            print(f"  {flag} {kw:<32} {len(hits):>3} trouv. | {len(new):>3} nouv. {pert}{ex[:34]}")
            time.sleep(0.4)

    res.sort(key=lambda r: (-r["pertinentes"], -r["nouvelles"]))
    bons = [
        r for r in res if r["nouvelles"] >= a.min_new and (not rx or r["pertinentes"] >= a.min_rel)
    ]
    crit = f">= {a.min_new} nouvelles" + (f" ET >= {a.min_rel} pertinentes" if rx else "")
    print(f"\n=== {len(bons)} mot(s)-clé(s) retenus ({crit}) sur {len(res)} testés ===")
    for r in bons:
        p = f" | {r['pertinentes']:>2} pertinentes" if rx else ""
        print(f"  {r['nouvelles']:>3} nouvelles{p}  {r['kw']}")
    if rx:
        vol = [r for r in res if r["nouvelles"] >= a.min_new and r["pertinentes"] == 0]
        if vol:
            print(f"\n{len(vol)} à VOLUME mais 0 pertinente (le piège du 29/07) :")
            for r in vol:
                print(f"  {r['nouvelles']:>3} nouvelles |  0 pertinentes  {r['kw']}")
    steriles = [r["kw"] for r in res if r["nouvelles"] == 0]
    if steriles:
        print(f"\n{len(steriles)} sans aucune nouveauté (à ne PAS ajouter) :")
        print("  " + ", ".join(steriles))

    if a.config and bons:
        cfg.setdefault("keywords", []).extend(r["kw"] for r in bons)
        importlib.import_module("jobhunter.programmes.jutil").jwrite(CFG, cfg)
        print(
            f"\n-> sources_config.json : +{len(bons)} mots-clés ({len(cfg['keywords'])} au total)"
        )
    elif bons:
        print("\n(relancer avec --config pour les ajouter au scan)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
