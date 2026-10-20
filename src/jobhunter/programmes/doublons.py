#!/usr/bin/env python3
"""doublons.py — The same posting published twice under two titles.

WHY. job_sources' merge deduplicates on normalised "entreprise|poste" and on the URL.
The duplicates from before that rule (same URL under two keys) are also reunited here.
And two cases escape it, spotted by the user on 2026-10-05:

  1. THE SAME LANGUAGE, A BARELY DIFFERENT TITLE: "Consultant en Transformation
     Finance - F/H" and "Consultant Transformation Finance F/H", at the same place.
     Measured: 65 groups in the queue.
  2. THE SAME OFFER TRANSLATED: ABB in Eggelsberg publishes "Product Sustainability
     & EU Taxonomy Specialist" and "Spezialist:in Produktnachhaltigkeit &
     EU-Taxonomie". No title word in common.

For case 2, the title is useless and so is the text — it is translated. What is not
translated are the ACRONYMS and the NUMBERS (EU, CSRD, LCA, 2026, 40%…). Measured on
the 104 "same company, same place, different languages" pairs of the queue: the real
translations are at 0.60-1.00 Jaccard (ABB 0.85, Dollarama 0.91, Bombardier 1.00),
the false pairs at 0.55 at most (Indosuez 0.50 on two distinct jobs). Threshold 0.6,
and at least 5 tokens on each side: below that, two short descriptions look alike by
chance.

We keep ONE offer per group: the tracked one first (never removed), then the best
source (employer site > LinkedIn), then French or English (the user's languages), then
the one most recently served again by its source (the current title), then the best
fit, then the longest description.

Decision: docs/adr/0010-offer-identity-company-job.md
"""

import re
import unicodedata

JACCARD_MIN = 0.6
# A URL that designates ONE posting: numeric identifier or UUID, or offer path.
# A generic career page (same link for ten jobs) must never join two offers.
_RX_URL_ANNONCE = re.compile(r"\d{5,}|[0-9a-f]{8}-[0-9a-f]{4}-|/jobs?/[^/?#]{6,}", re.I)
JETONS_MIN = 5

_VIDES = {
    "de",
    "du",
    "des",
    "d",
    "la",
    "le",
    "les",
    "l",
    "en",
    "et",
    "a",
    "au",
    "aux",
    "and",
    "of",
    "the",
    "for",
    "in",
    "h",
    "f",
    "m",
    "x",
    "w",
    "e",
    "nb",
    "cdi",
    "cdd",
    "stage",
    "internship",
}
_RX_GENRE = re.compile(
    r"[(\[]?\s*\b(?:[hfmwxd]|nb|a)(?:\s*[/|.-]\s*(?:[hfmwxd]|nb|div))+\b\s*[)\]]?", re.I
)
_RX_JETON = re.compile(r"\b(?:[A-Z][A-Z0-9&]{1,}[a-z]*|\d+[\d.,%]*)\b")
_MOTS_LANGUE = {
    "fr": (" les ", " des ", " vous ", " et ", " pour "),
    "en": (" the ", " and ", " you ", " with ", " our "),
    "de": (" und ", " die ", " der ", " wir ", " sie "),
    "nl": (" het ", " een ", " wij ", " je ", " van "),
    "es": (" los ", " las ", " para ", " con ", " una "),
    "it": (" il ", " della ", " per ", " con ", " una "),
}


def _sans_accent(s):
    s = unicodedata.normalize("NFD", str(s or "").lower())
    return "".join(c for c in s if not unicodedata.combining(c))


_RX_NON_LATIN = re.compile(r"[^\x00-ɏ\s\W]")


def mots_titre(t):
    """Words of the title, WITH their repetitions, in alphabetical order.

    Not a set: "Finance and Accounting Leadership Program: Accounting" and
    "…: Finance" have the same SET of words and are two tracks (Fifth Third). A
    non-Latin title (Chinese, Japanese) returns None: once the ideograms are removed,
    only "ESG" is left, and six EY jobs in Taipei were mixed up."""
    t = str(t or "")
    if _RX_NON_LATIN.search(t):
        return None
    t = _RX_GENRE.sub(" ", t)
    m = tuple(sorted(x for x in re.split(r"[^a-z0-9]+", _sans_accent(t)) if x and x not in _VIDES))
    return m if len(m) >= 2 else None


def ville(o):
    """First segment of the place: "Nimes, Occitanie" and "Nimes - 30" give "nimes"."""
    l = _sans_accent(o.get("localisation") or "")
    return re.split(r"\s*(?:,|\s-\s|\(|/)\s*", l.strip())[0].strip()


def entreprise(o):
    return re.sub(r"[^a-z0-9]", "", _sans_accent(o.get("entreprise") or ""))


def langue(o):
    t = " " + _sans_accent((o.get("description") or "")[:3000]) + " "
    scores = {k: sum(t.count(w) for w in mots) for k, mots in _MOTS_LANGUE.items()}
    k = max(scores, key=scores.get)
    return k if scores[k] else ""


def jetons(o):
    return set(_RX_JETON.findall(o.get("description") or ""))


def _rang(o, proteges, rang_source):
    return (
        (o.get("_oid") in proteges),
        rang_source(o.get("url")),
        langue(o) in ("fr", "en"),
        # the version the source STILL serves (current title), not the old one
        str(o.get("vu_le") or ""),
        o.get("fit") or 0,
        len(o.get("description") or ""),
    )


def doublons(file, proteges=frozenset(), rang_source=None, oid=None):
    """{removed oid: reason} for the given queue. Changes nothing.

    `oid` and `rang_source` are injected so that this module stays without
    dependencies (the tests pass simple functions)."""
    if rang_source is None:
        from jobhunter.sources import rang_source
    if oid is None:
        from jobhunter.stockage.file import oid
    for o in file:
        o["_oid"] = oid(o)
    try:
        # Union-find on the recognised pairs.
        parent = {id(o): id(o) for o in file}

        def racine(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def unir(a, b):
            parent[racine(id(a))] = racine(id(b))

        # 0. THE SAME POSTING URL: the same offer, whatever the title or the company
        #    name. Measured on 2026-10-19: 9 groups in the queue, born before the
        #    merge linked by URL — an employer who edits their title (Qonto:
        #    three titles for the same Lever posting), a renamed feed ("PwC France"
        #    puis « PwC », meme lien Workday).
        from jobhunter.sources.commun import _norm_url

        par_url = {}
        for o in file:
            if (o.get("url_type") or "") == "RECHERCHE":
                continue
            u = _norm_url(o.get("url"))
            if u and _RX_URL_ANNONCE.search(u):
                par_url.setdefault(u, []).append(o)
        for lot in par_url.values():
            for b in lot[1:]:
                unir(lot[0], b)

        par_ent = {}
        for o in file:
            if (o.get("url_type") or "") == "RECHERCHE":
                continue
            e = entreprise(o)
            if e:
                par_ent.setdefault(e, []).append(o)
        for lot in par_ent.values():
            if len(lot) < 2:
                continue
            for i in range(len(lot)):
                a = lot[i]
                va, ta = ville(a), mots_titre(a.get("poste"))
                for b in lot[i + 1 :]:
                    vb = ville(b)
                    if not va or va != vb:
                        continue
                    # 1. same title apart from stop words, gender and order
                    if ta and ta == mots_titre(b.get("poste")):
                        unir(a, b)
                        continue
                    # 2. translation: different languages, common acronyms and numbers
                    la, lb = langue(a), langue(b)
                    if la and lb and la != lb:
                        ja, jb = jetons(a), jetons(b)
                        if len(ja) >= JETONS_MIN and len(jb) >= JETONS_MIN:
                            if len(ja & jb) / len(ja | jb) >= JACCARD_MIN:
                                unir(a, b)

        groupes = {}
        for o in file:
            groupes.setdefault(racine(id(o)), []).append(o)
        retires = {}
        for g in groupes.values():
            if len(g) < 2:
                continue
            g.sort(key=lambda o: _rang(o, proteges, rang_source), reverse=True)
            garde = g[0]
            for o in g[1:]:
                if o["_oid"] in proteges or o["_oid"] == garde["_oid"]:
                    continue
                retires[o["_oid"]] = f"doublon de « {garde.get('poste')} »"
        return retires
    finally:
        for o in file:
            o.pop("_oid", None)
