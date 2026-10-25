#!/usr/bin/env python3
"""probe_keywords.py — Measures the real YIELD of search keywords.

Inventing a list of keywords says nothing: only what they bring back counts. This
script queries LinkedIn's public search for each candidate and distinguishes:
  - found: offers passing the anti-noise filter (title_ok)
  - NEW: missing from apply_queue.json (dedup by normalised URL)

A keyword that only brings back the already-seen is useless; it is "new" that decides
whether it is worth adding to the scan.

Changes NOTHING. Adding to the scan = through sources_config.json (see --config).

Run:
  python JobHunter.pyw probe_keywords                       # built-in candidate list
  python JobHunter.pyw probe_keywords --kw "analyste climat,finance verte"
  python JobHunter.pyw probe_keywords --min-new 3 --config  # adds the profitable ones to the config
"""

import argparse
import importlib
import json
import re
import sys
import time

from jobhunter import root as _racine

sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)  # type: ignore[union-attr]  # console : TextIOWrapper

HERE = _racine.scripts()
QUEUE = HERE / "apply_queue.json"
CFG = HERE / "sources_config.json"

# Real vocabulary of ESG/finance FR+EN offers for a junior profile.
# Grouped by theme so that the output is readable.
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

# Profile "builds their own tooling with Claude Code": AI-assisted dev,
# agents, LLM. Tested separately (--set ia) because it is another market than ESG.
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


def _sans_accent(s):
    import unicodedata

    return "".join(c for c in unicodedata.normalize("NFD", s) if not unicodedata.combining(c))


def candidats_du_profil():
    """The candidates for THIS profile: the built-in lists keep what its title filter
    keeps (a nurse was offered "notation esg"), plus its job word with its core skills.
    """
    from jobhunter import profile as _P
    from jobhunter.sources import title_ok

    groupes = {}
    for theme, kws in CANDIDATS.items():
        gardes = [k for k in kws if title_ok(k)]
        if gardes:
            # Mostly the profile's ground: the whole theme, as the owner always ran it.
            groupes[theme] = kws if 2 * len(gardes) >= len(kws) else gardes
    sc = _P.get("scoring", {}) or {}
    coeur = (sc.get("axes", {}) or {}).get(sc.get("axe_coeur", ""), {})
    comps = _P.get("competences", {}) or {}
    simple = re.compile(r"^[\wÀ-ÿ' -]+$")
    mots = [
        d["mots_titre"][0]
        for d in _P.domaines()
        if d.get("mots_titre") and simple.match(d["mots_titre"][0])
    ]
    metier = []
    for w in mots[:2]:
        for lab in coeur.get("competences", []):
            for syn in (comps.get(lab, {}).get("synonymes") or [])[:2]:
                if (
                    simple.match(syn)
                    and len(syn) > 3
                    and _sans_accent(syn)[:5] != _sans_accent(w)[:5]
                ):
                    metier.append(f"{w} {syn}")
    if metier:
        groupes["Ton métier"] = list(dict.fromkeys(metier))[:20]
    return groupes


def norm_url(u):
    from jobhunter.sources import _norm_url

    return _norm_url(u)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kw", help="liste CSV de mots-clés (sinon liste intégrée)")
    ap.add_argument(
        "--set",
        choices=["profil", "esg", "ia"],
        default="profil",
        help="jeu de candidats à tester (déf. : tiré du profil)",
    )
    ap.add_argument("--pages", type=int, default=1)
    ap.add_argument("--days", type=int, default=30, help="fraîcheur LinkedIn (jours)")
    ap.add_argument(
        "--min-new",
        type=int,
        default=3,
        help="seuil de nouvelles offres pour juger un mot-clé rentable",
    )
    # LESSON of 29/07: judging on NOVELTY alone let in 169 off-topic offers
    # out of 201 (15% relevance). A keyword is only good if it
    # brings back new AND relevant → we require both.
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

    rx = re.compile(a.relevant_rx, re.I) if a.relevant_rx else None

    from jobhunter.sources import linkedin_guest_search

    q = (
        importlib.import_module("jobhunter.storage.queue").charger(QUEUE, descriptions=False)
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
    elif a.set == "esg":
        groupes = CANDIDATS
    else:
        groupes = candidats_du_profil()

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
        importlib.import_module("jobhunter.programs.util").jwrite(CFG, cfg)
        print(
            f"\n-> sources_config.json : +{len(bons)} mots-clés ({len(cfg['keywords'])} au total)"
        )
    elif bons:
        print("\n(relancer avec --config pour les ajouter au scan)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
