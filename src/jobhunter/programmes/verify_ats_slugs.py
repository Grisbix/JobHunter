#!/usr/bin/env python3
"""verify_ats_slugs.py — Does the ATS feed REALLY belong to the targeted company?

WHY. A slug is guessed from the name: "CIC" -> lever/cic. But lever/cic is the
Cambridge Innovation Center, not the Crédit Industriel et Commercial; its offers are in
Tokyo. `probe_ats.py` already documents this trap ("ne PAS ajouter metron : homonyme =
societe de defense US"). Without an identity check, we would inject into the queue the
offers of another company.

This program asks each API for the NAME the company gives itself, and compares it with
the one in the queue. Changes nothing.

Run: python JobHunter.pyw verify_ats_slugs [--json _ats_candidats.json]
"""

import argparse
import concurrent.futures as cf
import difflib
import json
import re
import sys
import unicodedata
from pathlib import Path

from jobhunter import racine as _racine

HERE = _racine.scripts()

sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)  # type: ignore[union-attr]  # console : TextIOWrapper

from jobhunter.programmes import probe_ats

UA = probe_ats.UA

# Endpoints that return the name the COMPANY gives itself.
# Lever and Ashby expose NO name in their API: reading the posting URL there
# amounted to comparing the slug with itself — a circular check that
# validated everything. So we read the title of the portal page.
IDENTITE = {
    "greenhouse": lambda s: f"https://boards-api.greenhouse.io/v1/boards/{s}",
    "smartrecruiters": lambda s: (
        f"https://api.smartrecruiters.com/v1/companies/{s}/postings?limit=1"
    ),
    "recruitee": lambda s: f"https://{s}.recruitee.com/api/offers/",
    "ashby": lambda s: f"https://jobs.ashbyhq.com/{s}",
    "lever": lambda s: f"https://jobs.lever.co/{s}",
}
RX_TITRE = re.compile(r"<title[^>]*>(.*?)</title>", re.S | re.I)


def _sans_accent(s):
    s = unicodedata.normalize("NFD", str(s or "").lower())
    return "".join(c for c in s if not unicodedata.combining(c))


def _cle(s):
    """Name reduced to its significant letters, to compare "Sia" and "Sia Partners"."""
    BRUIT = {
        "group",
        "groupe",
        "france",
        "sa",
        "sas",
        "the",
        "and",
        "co",
        "company",
        "consulting",
        "conseil",
        "partners",
        "international",
        "inc",
        "ltd",
        "en",
        "jobs",
        "job",
        "careers",
        "career",
        "emploi",
        "emplois",
        "recrutement",
        "limited",
        "sarl",
        "sasu",
    }
    mots = [m for m in re.split(r"[^a-z0-9]+", _sans_accent(s)) if m and m not in BRUIT]
    return " ".join(mots)


def nom_du_flux(kind, slug):
    """Name the company gives itself in its own feed, or "" if unreadable."""
    import html as _html

    import httpx

    try:
        r = httpx.get(IDENTITE[kind](slug), timeout=20, headers=UA, follow_redirects=True)
        if r.status_code != 200:
            return ""
    except Exception:
        return ""

    if kind in ("lever", "ashby"):
        # Titre de page : « Theodo », « Cohere Careers », « Jobs at X »…
        m = RX_TITRE.search(r.text)
        if not m:
            return ""
        titre = _html.unescape(re.sub(r"\s+", " ", m.group(1))).strip()
        # We remove the dressing to keep only the company name.
        titre = re.sub(r"^(jobs? at|careers? at|emplois? chez)\s+", "", titre, flags=re.I)
        titre = re.split(r"\s*[|–—-]\s*(jobs?|careers?|emplois?|recrutement)\b", titre, flags=re.I)[
            0
        ]
        return titre.strip()

    try:
        d = r.json()
    except Exception:
        return ""
    try:
        if kind == "greenhouse":
            return d.get("name") or ""
        if kind == "smartrecruiters":
            # The name lives in the POSTINGS: content[0].company.name.
            c = d.get("content") or []
            return ((c[0].get("company") or {}).get("name") or "") if c else ""
        if kind == "recruitee":
            offres = d.get("offers") or []
            return (offres[0].get("company_name") or "") if offres else ""
    except Exception:
        pass
    return ""


def verdict(attendu, trouve):
    """CONFIRME / A VERIFIER / HOMONYME.

    A ONE-word name proves nothing: "bureau" is contained in "bureau veritas", but
    Bureau (anti-fraud) and Bureau Veritas are two companies. Same for acronyms —
    lever/cic returns "CIC", which designates the Crédit Industriel et Commercial as
    well as the Cambridge Innovation Center. These cases call for a human eye, not a
    heuristic.
    """
    a, t = _cle(attendu), _cle(trouve)
    if not t:
        return "A VERIFIER", 0.0  # unreadable identity: do not add blindly
    ma, mt = set(a.split()), set(t.split())
    communs = ma & mt
    ratio = difflib.SequenceMatcher(None, a, t).ratio()
    # EXACT equality: much stronger than a mere inclusion.
    if ma == mt:
        # Except acronyms: "CIC" designates the Crédit Industriel et Commercial
        # as well as the Cambridge Innovation Center. Four letters prove nothing.
        if len(a) <= 4:
            return "A VERIFIER", ratio
        return "CONFIRME", 1.0
    # Two significant words in common: coincidence becomes unlikely.
    if len(communs) >= 2:
        return "CONFIRME", 1.0
    # One-word inclusion: "bureau" fits inside "bureau veritas", and
    # yet Bureau (anti-fraud) is not Bureau Veritas.
    if communs:
        return "A VERIFIER", ratio
    if ratio >= 0.85:
        return "CONFIRME", ratio
    if ratio >= 0.45:
        return "A VERIFIER", ratio
    return "HOMONYME", ratio


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=str(HERE / "_ats_candidats.json"))
    ap.add_argument("--workers", type=int, default=10)
    a = ap.parse_args()

    d = json.loads(Path(a.json).read_text(encoding="utf-8"))
    utiles = [r for r in d if r.get("pertinents")]
    utiles.sort(key=lambda r: -len(r["pertinents"]))
    print(f"{len(utiles)} flux a verifier\n")

    with cf.ThreadPoolExecutor(max_workers=a.workers) as ex:
        noms = list(ex.map(lambda r: nom_du_flux(r["ats"], r["slug"]), utiles))

    groupes = {"CONFIRME": [], "A VERIFIER": [], "HOMONYME": []}
    for r, nom in zip(utiles, noms):
        v, ratio = verdict(r["entreprise"], nom)
        r["identite"], r["verdict"], r["ratio"] = nom, v, round(ratio, 2)
        groupes[v].append(r)

    for v in ("CONFIRME", "A VERIFIER", "HOMONYME"):
        lot = groupes[v]
        print(
            f"=== {v} : {len(lot)} flux, "
            f"{sum(len(r['pertinents']) for r in lot)} offres pertinentes ==="
        )
        for r in lot:
            print(
                f"  {len(r['pertinents']):4} · {r['ats']:16} {r['slug']:20} "
                f"file={r['entreprise'][:24]:26} flux={r['identite'][:26]}"
            )
            if v == "A VERIFIER":
                # The titles and their language often decide: a job in
                # Tokyo under the acronym "CIC" is not the French bank.
                for ex in r["pertinents"][:2]:
                    print(f"          · {ex[:70]}")
        print()

    Path(a.json).write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    ok = groupes["CONFIRME"]
    if ok:
        par = {}
        for r in ok:
            par.setdefault(r["ats"], []).append(r["slug"])
        print("A ajouter (identite CONFIRMEE seulement) :")
        for k, v in par.items():
            print(f'  "{k}": {sorted(set(v))},')
    return 0


if __name__ == "__main__":
    sys.exit(main())
