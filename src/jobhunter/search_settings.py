"""The search, edited in the application: keywords, titles kept, titles set aside, places.

Four sections of the active profile's `profile.json`, the ones a user changes most:

- `collecte.mots_cles`: the searches run on LinkedIn, Welcome to the Jungle…;
- `filtre_titre.metier`: a title must contain one of these to be collected;
- `filtre_titre.exclus`: a title containing one of these is set aside;
- `zones.prioritaires` / `zones.secondaires`: where the user wants to work. An entry is a
  key of `scoring.zones.CATALOGUE` ("idf", "bordeaux"…) or, for any other place in the
  world, a sector {"cle", "libelle", "lieux"} (`lieu_libre`). `chercher_lieux` finds
  both from what the user types. They never touch the fit: they fill the Zone column.

An entry is a word or phrase (found anywhere in the title, case ignored) or, starting
with `re:`, a regular expression — the profile's own syntax, unchanged. `valider()` says
what is wrong before anything is written; `ecrire()` keeps the previous profile as `.bak`
and writes atomically, keeping the file's indentation and every other section as is.
"""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from jobhunter.text import sans_accent


@dataclass
class Reglages:
    """The editable part of the search."""

    mots_cles: list[str] = field(default_factory=list)
    garder: list[str] = field(default_factory=list)
    ecarter: list[str] = field(default_factory=list)
    # None = left as they are in the profile (a caller that does not edit the places).
    # An entry: a catalogue key (str) or a sector declared in full (dict).
    prioritaires: list[Any] | None = None
    secondaires: list[Any] | None = None


def _liste(v: object) -> list[str]:
    if isinstance(v, str):
        v = [v]
    return [str(x).strip() for x in (v or []) if str(x).strip()] if isinstance(v, list) else []


def lire(profil: dict[str, Any]) -> Reglages:
    """The search settings of a loaded profile."""
    ft = profil.get("filtre_titre") or {}
    zones = profil.get("zones") or {}
    return Reglages(
        mots_cles=_liste((profil.get("collecte") or {}).get("mots_cles")),
        garder=_liste(ft.get("metier")),
        ecarter=_liste(ft.get("exclus")),
        prioritaires=_lieux(zones.get("prioritaires")),
        secondaires=_lieux(zones.get("secondaires")),
    )


def _lieux(v: object) -> list[Any]:
    """The entries of a zone list: catalogue keys lowered, declared sectors as they are."""
    return [
        x.lower() if isinstance(x, str) else x
        for x in (v if isinstance(v, list) else [])
        if isinstance(x, dict) or (isinstance(x, str) and x.strip())
    ]


def _norme(t: object) -> str:
    return " ".join(sans_accent(t).replace("-", " ").split())


def libelle_lieu(entree: Any) -> str:
    """What the app shows for a zone entry: "Paris", "Londres"."""
    from jobhunter.scoring.zones import CATALOGUE

    if isinstance(entree, dict):
        return str(entree.get("libelle") or entree.get("cle") or "?")
    return str(CATALOGUE.get(str(entree), {}).get("libelle") or entree)


def cle_lieu(entree: Any) -> str:
    """The identity of a zone entry, to avoid choosing a place twice."""
    return str(entree.get("cle") if isinstance(entree, dict) else entree).lower()


def lieu_libre(nom: str) -> dict[str, Any]:
    """A place outside the catalogue (Londres, Genève, Montréal…), declared as a sector."""
    nom = " ".join(nom.split())
    if nom.islower():
        nom = nom.title()  # "londres" -> "Londres": the name as the app shows it
    return {"cle": _norme(nom).replace(" ", "-"), "libelle": nom, "lieux": [nom]}


def chercher_lieux(texte: str, limite: int = 8) -> list[tuple[Any, str]]:
    """The places matching what the user typed: [(entry, label shown)].

    The catalogue first — by name, then by a town it contains ("Mérignac" gives
    Bordeaux, "Courbevoie" gives Paris) — then the typed text itself as a free
    place, so that any city of the world can be chosen.
    """
    from jobhunter.scoring.zones import CATALOGUE

    q = _norme(texte)
    if len(q) < 2:
        return []
    par_nom: list[tuple[Any, str]] = []
    par_ville: list[tuple[Any, str]] = []
    exact = False
    for cle, s in CATALOGUE.items():
        if q in _norme(s["libelle"]) or q in _norme(cle):
            par_nom.append((cle, str(s["libelle"])))
            continue
        villes = [*s.get("lieux", ()), *s.get("communes", ())]
        trouve = next((v for v in villes if q in _norme(v)), None)
        if trouve:
            par_ville.append((cle, f"{s['libelle']} (comprend {trouve.title()})"))
            exact = exact or _norme(trouve) == q
    sortie = (par_nom + par_ville)[: limite - 1]
    # The typed text as a place of its own, unless the catalogue already names it.
    if not exact and not any(_norme(lib) == q for _e, lib in sortie):
        libre = lieu_libre(texte)
        sortie.append((libre, f"{libre['libelle']} (ville ou pays)"))
    return sortie


def _groupe(corps: str) -> list[str] | None:
    """The alternatives of "(a|b|c)" wrapping the whole pattern, split at its top level."""
    if not (corps.startswith("(") and corps.endswith(")")):
        return None
    morceaux, courant, prof, classe, i = [], "", 0, False, 1
    while i < len(corps) - 1:
        c = corps[i]
        if c == "\\":
            courant += corps[i : i + 2]
            i += 2
            continue
        if classe:
            classe = c != "]"
        elif c == "[":
            classe = True
        elif c == "(":
            prof += 1
        elif c == ")":
            prof -= 1
            if prof < 0:
                return None  # "(a)|(b)": the first group closes before the end
        elif c == "|" and prof == 0:
            morceaux.append(courant)
            courant = ""
            i += 1
            continue
        courant += c
        i += 1
    return morceaux + [courant] if prof == 0 and not classe else None


_RX_LITTERAL = re.compile(r"[\w &'-]", re.U)
_RX_CLASSE = re.compile(r"\[([^\]\\^-]+)\]")


def _mots(alternative: str) -> list[str] | None:
    r"""The plain words an alternative means: "d[ée]carbon" -> décarbon, decarbon.

    None when it uses anything else (\b, ?, a nested group…): it then stays a re: line.
    """
    variantes = [""]
    i = 0
    while i < len(alternative):
        m = _RX_CLASSE.match(alternative, i)
        if m:
            choix = list(dict.fromkeys(m.group(1)))
            if not all(_RX_LITTERAL.fullmatch(c) for c in choix):
                return None
            variantes = [v + c for v in variantes for c in choix]
            i = m.end()
        elif _RX_LITTERAL.fullmatch(alternative[i]):
            variantes = [v + alternative[i] for v in variantes]
            i += 1
        else:
            return None
        if len(variantes) > 4:
            return None
    return [v.strip() for v in variantes if v.strip()]


def eclater(entrees: list[str]) -> list[str]:
    r"""One readable entry per line: a "re:(a|b|c)" list becomes its words.

    Each alternative that is only letters (and [ée]-style choices) becomes a plain
    word; the others ("csr\b", "account (executive|manager)") stay as `re:` lines.
    A word finds what STARTS with it ("financ": finance, financier); a "*" in front
    lets it start inside a word too (profile.motif).
    """
    sortie: list[str] = []
    for e in entrees:
        alternatives = _groupe(e[3:]) if e.startswith("re:") else None
        if alternatives is None:
            sortie.append(e)
            continue
        for alt in alternatives:
            mots = _mots(alt)
            if mots is None:
                sortie.append("re:" + alt)
                continue
            # In the regex they had no left boundary. A short word (an acronym: esg,
            # rse, ux) gets one — "rse" no longer finds "diveRSE"; a longer single word
            # keeps finding a compound: "*analyst" still finds "Nachhaltigkeitsanalyst".
            sortie += [m if len(m) <= 4 or " " in m else "*" + m for m in mots]
    return list(dict.fromkeys(sortie))


def depuis_texte(texte: str) -> list[str]:
    """One entry per line, empty lines and duplicates removed, order kept."""
    vus: dict[str, None] = {}
    for ligne in texte.splitlines():
        ligne = ligne.strip()
        if ligne and ligne.lower() not in {v.lower() for v in vus}:
            vus[ligne] = None
    return list(vus)


def valider(r: Reglages) -> list[str]:
    """What prevents saving, in plain words; [] if nothing."""
    erreurs = []
    if not r.mots_cles:
        erreurs.append("au moins un mot-clé de recherche")
    if not r.garder:
        erreurs.append("au moins un mot d'intitulé à garder (sinon aucune offre ne passe)")
    for nom, liste in (("à garder", r.garder), ("à écarter", r.ecarter)):
        for e in liste:
            if e.startswith("re:"):
                try:
                    re.compile(e[3:], re.I)
                except re.error as x:
                    erreurs.append(f"intitulés {nom} : motif invalide « {e[:40]} » ({x.msg})")
    return erreurs


def appliquer(profil: dict[str, Any], r: Reglages) -> dict[str, Any]:
    """A copy of `profil` with the settings in; every other key and its order kept."""
    nouveau = json.loads(json.dumps(profil))
    nouveau.setdefault("collecte", {})["mots_cles"] = list(r.mots_cles)
    ft = nouveau.setdefault("filtre_titre", {})
    ft["metier"] = list(r.garder)
    ft["exclus"] = list(r.ecarter)
    zones = nouveau.setdefault("zones", {})
    for cle, choix in (("prioritaires", r.prioritaires), ("secondaires", r.secondaires)):
        if choix is not None:
            zones[cle] = json.loads(json.dumps(list(choix)))
    return nouveau


def _indentation(texte: str) -> int:
    for ligne in texte.splitlines()[1:]:
        if ligne.strip():
            return len(ligne) - len(ligne.lstrip(" "))
    return 1


# ── The collection's keywords live in two files ──────────────────────────────
# The collection reads `sources_config.json` ("keywords") before the profile's
# `collecte.mots_cles` (sources.common._load_cfg), and first_launch writes both. A
# keyword added or removed in "Ma recherche" only reached the profile: the collection
# went on with the old list, silently. Both are now read and written together.
def _fichier_sources() -> Path:
    from jobhunter import root as _racine

    return _racine.dans(_racine.scripts(), "sources_config.json")


def mots_cles_collecte(profil: dict[str, Any]) -> list[str]:
    """The keywords the collection really uses: sources_config's, else the profile's."""
    try:
        cfg = json.loads(_fichier_sources().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        cfg = {}
    return _liste(cfg.get("keywords")) or _liste((profil.get("collecte") or {}).get("mots_cles"))


def ecrire_mots_cles(mots: list[str]) -> None:
    """Writes the collection's keywords into sources_config.json (other keys kept)."""
    f = _fichier_sources()
    try:
        cfg = json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        cfg = {}
    cfg["keywords"] = list(mots)
    tmp = f.with_name(f.name + ".tmp")
    tmp.write_text(json.dumps(cfg, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(f)


def ecrire(fichier: Path, profil: dict[str, Any]) -> Path:
    """Writes the profile: the previous one kept as `<name>.bak`, atomic replace.

    Returns:
        The backup's path.
    """
    ancien = fichier.read_text(encoding="utf-8")
    sauvegarde = fichier.with_name(fichier.name + ".bak")
    sauvegarde.write_text(ancien, encoding="utf-8")
    tmp = fichier.with_name(fichier.name + ".tmp")
    tmp.write_text(
        json.dumps(profil, ensure_ascii=False, indent=_indentation(ancien)) + "\n",
        encoding="utf-8",
    )
    tmp.replace(fichier)
    return sauvegarde
