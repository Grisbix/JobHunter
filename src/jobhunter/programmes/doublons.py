#!/usr/bin/env python3
"""doublons.py — La meme annonce publiee deux fois sous deux intitules.

POURQUOI. La fusion de job_sources deduplique sur « entreprise|poste » normalise
et sur l'URL. Deux cas lui echappent, releves par l'utilisateur le 2026-10-05 :

  1. LA MEME LANGUE, UN INTITULE A PEINE DIFFERENT : « Consultant en
     Transformation Finance - F/H » et « Consultant Transformation Finance F/H »,
     au meme endroit. Mesure : 65 groupes dans la file.
  2. LA MEME OFFRE TRADUITE : ABB a Eggelsberg publie « Product Sustainability
     & EU Taxonomy Specialist » et « Spezialist:in Produktnachhaltigkeit &
     EU-Taxonomie ». Aucun mot de titre en commun.

Pour le cas 2, le titre ne sert a rien et le texte non plus — il est traduit.
Ce qui ne se traduit pas, ce sont les SIGLES et les NOMBRES (EU, CSRD, LCA,
2026, 40 %…). Mesure sur les 104 paires « meme entreprise, meme lieu, langues
differentes » de la file : les vraies traductions sont a 0,60-1,00 de Jaccard
(ABB 0,85, Dollarama 0,91, Bombardier 1,00), les fausses paires a 0,55 au plus
(Indosuez 0,50 sur deux postes distincts). Seuil 0,6, et au moins 5 jetons de
chaque cote : en dessous, deux descriptions courtes se ressemblent par hasard.

On garde UNE offre par groupe : celle du suivi d'abord (jamais retiree), puis
la meilleure source (site employeur > LinkedIn), puis le francais ou l'anglais
(langues de l'utilisateur), puis le meilleur fit, puis la description la plus longue.
"""

import re
import unicodedata

JACCARD_MIN = 0.6
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
    """Mots de l'intitule, AVEC leurs repetitions, dans l'ordre alphabetique.

    Pas un ensemble : « Finance and Accounting Leadership Program: Accounting »
    et « …: Finance » ont le meme ENSEMBLE de mots et sont deux filieres
    (Fifth Third). Un titre non latin (chinois, japonais) rend None : une fois
    les ideogrammes retires, il ne reste que « ESG », et six postes EY de Taipei
    se confondaient."""
    t = str(t or "")
    if _RX_NON_LATIN.search(t):
        return None
    t = _RX_GENRE.sub(" ", t)
    m = tuple(sorted(x for x in re.split(r"[^a-z0-9]+", _sans_accent(t)) if x and x not in _VIDES))
    return m if len(m) >= 2 else None


def ville(o):
    """Premier segment du lieu : « Nimes, Occitanie » et « Nimes - 30 » font « nimes »."""
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
        o.get("fit") or 0,
        len(o.get("description") or ""),
    )


def doublons(file, proteges=frozenset(), rang_source=None, oid=None):
    """{oid retire: motif} pour la file donnee. Ne modifie rien.

    `oid` et `rang_source` sont injectes pour que ce module reste sans
    dependance (les tests passent des fonctions simples)."""
    if rang_source is None:
        from jobhunter.sources import rang_source
    if oid is None:
        from jobhunter.stockage.file import oid
    for o in file:
        o["_oid"] = oid(o)
    try:
        # Union-find sur les paires reconnues.
        parent = {id(o): id(o) for o in file}

        def racine(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def unir(a, b):
            parent[racine(id(a))] = racine(id(b))

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
                    # 1. meme intitule aux mots vides, au genre et a l'ordre pres
                    if ta and ta == mots_titre(b.get("poste")):
                        unir(a, b)
                        continue
                    # 2. traduction : langues differentes, sigles et nombres communs
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
