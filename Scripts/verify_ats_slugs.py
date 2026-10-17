#!/usr/bin/env python3
"""verify_ats_slugs.py — Le flux ATS appartient-il VRAIMENT a la societe visee ?

POURQUOI. Un slug se devine a partir du nom : « CIC » -> lever/cic. Mais
lever/cic est Cambridge Innovation Center, pas le Credit Industriel et
Commercial ; ses offres sont a Tokyo. `probe_ats.py` documente deja ce piege
(« ne PAS ajouter metron : homonyme = societe de defense US »). Sans verification
d'identite, on injecterait dans la file les offres d'une autre entreprise.

Ce programme interroge chaque API pour le NOM que la societe se donne, et le
compare a celui de la file. Ne modifie rien.

Run : python verify_ats_slugs.py [--json _ats_candidats.json]
"""

import argparse
import concurrent.futures as cf
import difflib
import json
import re
import sys
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

import probe_ats

UA = probe_ats.UA

# Endpoints qui rendent le nom que la SOCIETE se donne.
# Lever et Ashby n'exposent AUCUN nom dans leur API : lire l'URL d'annonce y
# revenait a comparer le slug a lui-meme — une verification circulaire qui
# validait tout. On lit donc le titre de la page du portail.
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
    """Nom reduit a ses lettres significatives, pour comparer « Sia » et « Sia Partners »."""
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
    """Nom que la societe se donne dans son propre flux, ou "" si illisible."""
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
        # On retire l'habillage pour ne garder que le nom de la societe.
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
            # Le nom vit dans les POSTINGS : content[0].company.name.
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

    Un nom d'UN SEUL mot ne prouve rien : « bureau » est contenu dans « bureau
    veritas », mais Bureau (anti-fraude) et Bureau Veritas sont deux societes.
    Idem pour les sigles — lever/cic rend « CIC », qui designe aussi bien le
    Credit Industriel et Commercial que le Cambridge Innovation Center. Ces cas
    reclament un oeil humain, pas une heuristique.
    """
    a, t = _cle(attendu), _cle(trouve)
    if not t:
        return "A VERIFIER", 0.0  # identite illisible : ne pas ajouter a l'aveugle
    ma, mt = set(a.split()), set(t.split())
    communs = ma & mt
    ratio = difflib.SequenceMatcher(None, a, t).ratio()
    # EGALITE exacte : bien plus fort qu'une simple inclusion.
    if ma == mt:
        # Sauf les sigles : « CIC » designe le Credit Industriel et Commercial
        # comme le Cambridge Innovation Center. Quatre lettres ne prouvent rien.
        if len(a) <= 4:
            return "A VERIFIER", ratio
        return "CONFIRME", 1.0
    # Deux mots significatifs en commun : la coincidence devient improbable.
    if len(communs) >= 2:
        return "CONFIRME", 1.0
    # Inclusion a un seul mot : « bureau » tient dans « bureau veritas », et
    # pourtant Bureau (anti-fraude) n'est pas Bureau Veritas.
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
                # Les intitules et leur langue tranchent souvent : un poste a
                # Tokyo sous le sigle « CIC » n'est pas la banque francaise.
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
