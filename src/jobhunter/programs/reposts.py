#!/usr/bin/env python3
"""reposts.py — Offers posted again, and the same text under another company.

Two signals, shown in the « Signal » column of the app. Observations only: they
change neither the fit nor the sorting, and they remove nothing.

1. REPOSTED. An employer that takes an offer down and puts it back under a new
   address, again and again, is often not hiring for it right now (a "ghost" offer)
   — or the post is hard to fill. Either way the user wants to know. The history
   `_offres_vues.json` keeps, for each offer (company + the SET of its title words),
   the addresses seen and the day each was first seen, over 180 days.
   Rules, from career-ops' detect-reposts.mjs, both born of false alarms there:
   - the addresses compared live on the SAME site. When the merge swaps a LinkedIn
     link for the employer's own (`final_site`), that is one offer with a better
     link, not a repost. LinkedIn addresses are compared by their job number,
     whatever the country subdomain;
   - two addresses first seen the SAME day come from one collection: they are
     parallel openings, not a repost, which needs a later day;
   - the title is compared as a set of words, not by similarity: "Analyst - Paris"
     and "Analyst - Lyon" are two jobs. Gender markers (H/F, F/H, m/w/d) are left out.
   Only the last 90 days count.

2. SAME TEXT ELSEWHERE. A recruitment agency often republishes an employer's offer
   with the employer's name removed but the text untouched. Each description gets a
   64-bit SimHash (3-word shingles, SHA-1): near-identical texts differ by a few bits.
   Two offers of DIFFERENT companies at 0.92 or more (5 bits of 64 at most) are
   flagged on both sides. Compared through 6 bands of the hash, so that 10,000
   offers need no 50 million comparisons: two hashes 5 bits apart at most share at
   least one band exactly. Descriptions under 200 characters are not fingerprinted:
   too little text, too many false matches. Technique: career-ops, fingerprint-core.mjs.

Run:
  python JobHunter.pyw reposts           # update the history and the signals
  python JobHunter.pyw reposts --dry     # print, write nothing
"""

import argparse
import collections
import datetime
import hashlib
import json
import re
import sys
import unicodedata
from collections.abc import Iterable, Sequence
from typing import Any
from urllib.parse import urlsplit

from jobhunter import root as _racine
from jobhunter.storage import queue as queue_io
from jobhunter.storage.atomic import ecrire_json
from jobhunter.types import Offre

HISTORIQUE = "_offres_vues.json"
FENETRE_JOURS = 90
GARDE_JOURS = 180
TEXTE_MIN = 200
SEUIL = 0.92
BANDES = 6

_GENRE = re.compile(
    r"\b(?:h\s*/\s*f|f\s*/\s*h|m\s*/\s*w\s*/\s*d|m\s*/\s*f|w\s*/\s*m\s*/\s*d|x\s*/\s*f)\b"
)
_LI_ID = re.compile(r"linkedin\.com/.*?(?:/view/|currentJobId=)(?:[^/?#]*?-)?(\d{6,})")


def _plat(t: str) -> str:
    t = unicodedata.normalize("NFKD", (t or "").casefold()).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def cle(entreprise: str, poste: str) -> str:
    """Company + the sorted set of title words, gender markers left out."""
    titre = _GENRE.sub(" ", (poste or "").casefold())
    mots = sorted(set(_plat(titre).split()))
    return f"{_plat(entreprise)}|{' '.join(mots)}"


def adresse(url: str) -> tuple[str, str] | None:
    """(site, identity of the address on that site); None if not an address."""
    url = (url or "").strip()
    if m := _LI_ID.search(url):
        return "linkedin", m.group(1)
    s = urlsplit(url)
    if s.scheme not in ("http", "https") or not s.netloc:
        return None
    gh = re.search(r"(?:^|&)gh_jid=(\d+)", s.query)
    return s.netloc.lower().removeprefix("www."), s.path.rstrip("/") + (
        f"?gh_jid={gh.group(1)}" if gh else ""
    )


# ── SimHash ──────────────────────────────────────────────────────────────────


def empreinte(texte: str) -> str:
    """64-bit SimHash of a description, 16 hex characters; '' if too short."""
    t = re.sub(r"<[^>]*>|&[a-z#0-9]+;|https?://\S+", " ", (texte or "").casefold())
    mots = re.sub(r"[^\w]+", " ", t).split()
    if len(" ".join(mots)) < TEXTE_MIN or len(mots) < 3:
        return ""
    poids = [0] * 64
    for i in range(len(mots) - 2):
        h = int.from_bytes(hashlib.sha1(" ".join(mots[i : i + 3]).encode()).digest()[:8], "big")
        for b in range(64):
            poids[b] += 1 if (h >> (63 - b)) & 1 else -1
    v = 0
    for b in range(64):
        if poids[b] > 0:
            v |= 1 << (63 - b)
    return f"{v:016x}"


def similarite(a: str, b: str) -> float:
    return 1 - bin(int(a, 16) ^ int(b, 16)).count("1") / 64


def _bandes(e: str) -> list[tuple[int, int]]:
    v, largeur = int(e, 16), -(-64 // BANDES)
    return [(i, (v >> (i * largeur)) & ((1 << largeur) - 1)) for i in range(BANDES)]


def memes_textes(offres: list[tuple[str, str, str]]) -> dict[str, set[str]]:
    """oid → the other companies whose offer has the same text. (oid, company, hash)."""
    seaux: dict[tuple[int, int], list[int]] = collections.defaultdict(list)
    for i, (_, _, e) in enumerate(offres):
        if e:
            for b in _bandes(e):
                seaux[b].append(i)
    vu: set[tuple[int, int]] = set()
    out: dict[str, set[str]] = collections.defaultdict(set)
    for groupe in seaux.values():
        if len(groupe) > 200:  # boilerplate shared by a whole board: no signal
            continue
        for x in range(len(groupe)):
            for y in range(x + 1, len(groupe)):
                i, j = groupe[x], groupe[y]
                if (i, j) in vu:
                    continue
                vu.add((i, j))
                (oi, ei, hi), (oj, ej, hj) = offres[i], offres[j]
                if _plat(ei) != _plat(ej) and similarite(hi, hj) >= SEUIL:
                    out[oi].add(ej)
                    out[oj].add(ei)
    return out


# ── history and reposts ──────────────────────────────────────────────────────


def mettre_a_jour(hist: dict[str, Any], offres: Iterable[Offre], jour: str) -> None:
    """Note each offer's address and the day it was first seen."""
    for o in offres:
        a = adresse(o.get("url") or "")
        if not a:
            continue
        h = hist.setdefault(cle(o.get("entreprise", ""), o.get("poste", "")), {"u": {}})
        h["u"].setdefault(f"{a[0]} {a[1]}", jour)
        h["d"] = jour


def republications(h: dict[str, Any], jour: str) -> int:
    """How many times the offer came back under a new address on its site (90 days)."""
    debut = (datetime.date.fromisoformat(jour) - datetime.timedelta(FENETRE_JOURS)).isoformat()
    jours_par_site: dict[str, set[str]] = collections.defaultdict(set)
    for a, d in h.get("u", {}).items():
        if d >= debut:
            jours_par_site[a.split(" ", 1)[0]].add(d)
    return max((len(js) - 1 for js in jours_par_site.values()), default=0)


def elaguer(hist: dict[str, Any], jour: str) -> None:
    """Forget what was not seen for GARDE_JOURS days, and addresses older than that."""
    limite = (datetime.date.fromisoformat(jour) - datetime.timedelta(GARDE_JOURS)).isoformat()
    for k in [k for k, h in hist.items() if h.get("d", "") < limite]:
        del hist[k]
    for h in hist.values():
        h["u"] = {a: d for a, d in h["u"].items() if d >= limite}


def signaux(hist: dict[str, Any], offres: Sequence[Offre], jour: str) -> dict[str, str]:
    """oid → the text of the « Signal » column ('' when nothing to say)."""
    textes = memes_textes(
        [
            (queue_io.oid(o), o.get("entreprise", ""), empreinte(o.get("description") or ""))
            for o in offres
        ]
    )
    out = {}
    for o in offres:
        oid = queue_io.oid(o)
        morceaux = []
        n = republications(hist.get(cle(o.get("entreprise", ""), o.get("poste", "")), {}), jour)
        if n:
            morceaux.append(f"republiée ×{n}")
        autres = sorted(textes.get(oid, ()))
        # Same first word ("VINCI", "VINCI Construction"): one group under two names,
        # a duplicate. Otherwise often an agency or a job board republishing it.
        tete = (_plat(o.get("entreprise", "")).split() or [""])[0]
        memes = [x for x in autres if (_plat(x).split() or [""])[0] == tete]
        ailleurs = [x for x in autres if x not in memes]
        for etiquette, noms in (("doublon", memes), ("même texte", ailleurs)):
            if noms:
                morceaux.append(
                    f"{etiquette} : " + ", ".join(noms[:2]) + ("…" if len(noms) > 2 else "")
                )
        out[oid] = " · ".join(morceaux)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--dry", action="store_true", help="afficher sans rien écrire")
    ap.add_argument(
        "--sauvegardes",
        action="store_true",
        help="amorcer l'historique avec les copies quotidiennes de la file (_backups)",
    )
    a = ap.parse_args(argv)
    jour = datetime.date.today().isoformat()
    chemin = _racine.dans(_racine.scripts(), HISTORIQUE)
    try:
        hist = json.loads(chemin.read_text(encoding="utf-8"))
    except FileNotFoundError:
        hist = {}

    if a.sauvegardes:
        # The daily copies (seven days) date the addresses better than "today".
        for d in sorted(p for p in (chemin.parent / "_backups").glob("20??-??-??") if p.is_dir()):
            f = d / "apply_queue.json"
            if f.exists():
                mettre_a_jour(hist, queue_io.charger(f, descriptions=False), d.name)
    offres = queue_io.charger()
    mettre_a_jour(hist, offres, jour)
    elaguer(hist, jour)
    sig = signaux(hist, offres, jour)
    n_rep = sum("republiée" in s for s in sig.values())
    n_txt = sum("même texte" in s or "doublon" in s for s in sig.values())
    print(
        f"{len(offres)} offres : {n_rep} republiée(s), {n_txt} au même texte qu'une autre entreprise"
    )
    for oid, s in sorted(sig.items(), key=lambda x: x[1], reverse=True)[:15]:
        if s:
            print(f"  {oid[:70]:70}  {s}")
    if a.dry:
        return 0

    with queue_io.transaction(descriptions=False) as file:
        for o in file:
            s = sig.get(queue_io.oid(o), "")
            if s:
                o["signal"] = s
            else:
                o.pop("signal", None)
    ecrire_json(chemin, hist)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    sys.exit(main())
