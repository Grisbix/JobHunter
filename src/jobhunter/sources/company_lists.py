"""Company lists by sector: whole sets of followed companies, switched on or off.

Part of jobhunter.sources. The engine's built-in companies target finance and ESG, so a
profile in another profession started with none and had to add each one by hand. A
list is a sector's set of companies whose job feeds were checked on their public ATS
API (`lists/*.json`, date in `verifie_le`); the user ticks the lists to collect, then
unticks a company inside one if needed (`flux_suspendus`, sources.feeds).

In `sources_config.json`:

    "listes": ["finance", "sante"]

Without that key the configuration works as before 3.32: the engine's finance lists,
replaced by `ats_slugs` / `workday_flux` / `autres_flux` when present. With it, those
three keys hold only the companies added by hand, and each ticked list adds its own.
The first tick converts an old configuration (`activer`), keeping what it collected.
"""

from __future__ import annotations

import functools
import json
import re
from dataclasses import dataclass, field
from importlib import resources
from typing import Any

CLE = "listes"
FINANCE = "finance"  # the engine's built-in lists (sources.common), not a JSON file
OUTILS_ATS = ("greenhouse", "lever", "ashby", "recruitee", "smartrecruiters", "teamtailor")
OUTILS_AUTRES = ("workable", "personio", "breezy")
CLES_FLUX = ("ats_slugs", "workday_flux", "autres_flux")


@dataclass(frozen=True)
class Liste:
    """A sector's companies, as the three kinds of feeds the collection reads."""

    ident: str
    titre: str
    description: str
    ats_slugs: dict[str, list[str]] = field(default_factory=dict)
    workday_flux: list[tuple[str, ...]] = field(default_factory=list)
    autres_flux: list[tuple[str, ...]] = field(default_factory=list)
    noms: dict[tuple[str, str], str] = field(default_factory=dict)  # (tool, slug) → name


def _depuis_json(ident: str, d: dict[str, Any]) -> Liste:
    ats: dict[str, list[str]] = {}
    workday: list[tuple[str, ...]] = []
    autres: list[tuple[str, ...]] = []
    noms: dict[tuple[str, str], str] = {}
    for e in d.get("entreprises") or []:
        outil, cle, nom = str(e["outil"]), str(e["cle"]), str(e["nom"])
        if outil == "workday":
            tenant, hote, site = cle.split("/")
            workday.append((tenant, hote, site, nom))
        elif outil in OUTILS_ATS:
            ats.setdefault(outil, []).append(cle)
            noms[(outil, cle.lower())] = nom
        else:
            autres.append((outil, cle, nom))
    return Liste(
        ident, str(d["titre"]), str(d.get("description") or ""), ats, workday, autres, noms
    )


def _finance() -> Liste:
    from jobhunter.sources import common

    ats, workday, autres = common.DEFAUTS_FLUX
    return Liste(
        FINANCE,
        "Finance et ESG",
        "Banques, gestion d'actifs, assurance, conseil et acteurs de la finance durable "
        "(la liste d'origine du moteur).",
        {k: list(v) for k, v in ats.items()},
        list(workday),
        list(autres),
    )


@functools.cache
def _fichiers() -> tuple[Liste, ...]:
    dossier = resources.files(__package__) / "lists"
    sortie = []
    for f in sorted(dossier.iterdir(), key=lambda p: p.name):
        if f.name.endswith(".json"):
            sortie.append(_depuis_json(f.name[:-5], json.loads(f.read_text(encoding="utf-8"))))
    return tuple(sortie)


def toutes() -> list[Liste]:
    """Every list, the engine's finance one first."""
    return [_finance(), *_fichiers()]


def par_ident(ident: str) -> Liste | None:
    """The list named `ident` ("tech", "finance"…), None if there is none."""
    return next((x for x in toutes() if x.ident == ident), None)


def noms_connus() -> dict[tuple[str, str], str]:
    """The readable name of each slug of the lists: "realtimeboardglobal" is Miro."""
    sortie: dict[tuple[str, str], str] = {}
    for x in _fichiers():
        sortie.update(x.noms)
    return sortie


def actives(cfg: dict[str, Any]) -> list[str] | None:
    """The ticked lists; None for a configuration from before the lists."""
    v = cfg.get(CLE)
    if not isinstance(v, list):
        return None
    return [str(x) for x in v if par_ident(str(x)) is not None]


def _ajouter(
    ats: dict[str, list[str]],
    workday: list[tuple[str, ...]],
    autres: list[tuple[str, ...]],
    liste: Liste,
) -> None:
    for outil, slugs in liste.ats_slugs.items():
        deja = {s.lower() for s in ats.setdefault(outil, [])}
        ats[outil] += [s for s in slugs if s.lower() not in deja]
    # A tenant may have several sites (PwC: experienced and campus): one per site.
    sites = {(str(f[0]).lower(), str(f[2]).lower()) for f in workday}
    workday += [
        f for f in liste.workday_flux if (str(f[0]).lower(), str(f[2]).lower()) not in sites
    ]
    vus = {(str(f[0]), str(f[1]).lower()) for f in autres}
    autres += [f for f in liste.autres_flux if (str(f[0]), str(f[1]).lower()) not in vus]


def flux_effectifs(
    cfg: dict[str, Any],
) -> tuple[dict[str, list[str]], list[tuple[str, ...]], list[tuple[str, ...]]] | None:
    """The feeds to collect: the hand-added ones plus those of each ticked list.

    None for a configuration from before the lists (sources.common keeps the old rule).
    """
    ids = actives(cfg)
    if ids is None:
        return None
    ats = {k: list(v) for k, v in (cfg.get("ats_slugs") or {}).items()}
    workday = [tuple(x) for x in cfg.get("workday_flux") or []]
    autres = [tuple(x) for x in cfg.get("autres_flux") or []]
    for ident in ids:
        liste = par_ident(ident)
        if liste is not None:
            _ajouter(ats, workday, autres, liste)
    return ats, workday, autres


def activer(cfg: dict[str, Any], ident: str, oui: bool = True) -> None:
    """Ticks or unticks a list in `cfg` (modified in place).

    The first time, an old configuration is converted without changing what it
    collects: the engine's finance list stays ticked when it was in use (one of the
    three keys absent, so its default applied), the keys present become the
    hand-added part, and the finance companies such a key had left out are unticked
    in the list (suspended) instead of coming back.
    """
    if par_ident(ident) is None:
        raise ValueError(f"liste inconnue : {ident}")
    ids = actives(cfg)
    if ids is None:
        ids = [FINANCE] if any(k not in cfg for k in CLES_FLUX) else []
        if ids:
            _suspendre_ecartees(cfg)
        for k, vide in (("ats_slugs", {}), ("workday_flux", []), ("autres_flux", [])):
            cfg.setdefault(k, vide)
    ids = [x for x in ids if x != ident]
    if oui:
        ids.append(ident)
    ordre = [x.ident for x in toutes()]
    cfg[CLE] = sorted(ids, key=ordre.index)


def _suspendre_ecartees(cfg: dict[str, Any]) -> None:
    """Suspends the finance feeds an old configuration's own keys did not collect.

    Before the lists, a key present in sources_config.json replaced the engine's: its
    finance companies missing from it were not collected (the user may have removed
    them). Ticking finance would bring them back; suspended, they stay out and show
    unticked in the list.
    """
    from jobhunter.sources import feeds

    finance = _finance()
    ecartees: list[str] = []
    if "ats_slugs" in cfg:
        gardes = {(o, str(s).lower()) for o, v in (cfg["ats_slugs"] or {}).items() for s in v}
        ecartees += [
            feeds.cle(o, s)
            for o, slugs in finance.ats_slugs.items()
            for s in slugs
            if (o, s.lower()) not in gardes
        ]
    if "workday_flux" in cfg:
        gardes_wd = {str(f[0]).lower() for f in cfg["workday_flux"] or []}
        ecartees += [
            feeds.cle("workday", f[0])
            for f in finance.workday_flux
            if str(f[0]).lower() not in gardes_wd
        ]
    if "autres_flux" in cfg:
        gardes_au = {(str(f[0]), str(f[1]).lower()) for f in cfg["autres_flux"] or []}
        ecartees += [
            feeds.cle(f[0], f[1])
            for f in finance.autres_flux
            if (str(f[0]), str(f[1]).lower()) not in gardes_au
        ]
    for x in dict.fromkeys(ecartees):
        feeds.suspendre(cfg, x)


def origine(cfg: dict[str, Any], outil: str, cle: str) -> list[str]:
    """The ticked lists a feed comes from (empty: added by hand, or an old configuration)."""
    sortie = []
    for ident in actives(cfg) or []:
        liste = par_ident(ident)
        if liste is not None and cle.lower() in _cles(liste, outil):
            sortie.append(ident)
    return sortie


def _cles(liste: Liste, outil: str) -> set[str]:
    if outil == "workday":
        return {str(f[0]).lower() for f in liste.workday_flux}
    if outil in liste.ats_slugs:
        return {s.lower() for s in liste.ats_slugs[outil]}
    return {str(f[1]).split("|")[0].lower() for f in liste.autres_flux if f[0] == outil}


def resume(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    """Each list for the Companies screen: ticked or not, and its companies."""
    ids = actives(cfg)
    if ids is None:
        ids = [FINANCE] if any(k not in cfg for k in CLES_FLUX) else []
    sortie = []
    for liste in toutes():
        entreprises = [
            {"nom": nom or _nom(slug), "outil": outil, "cle": slug}
            for outil, slugs in liste.ats_slugs.items()
            for slug in slugs
            for nom in [liste.noms.get((outil, slug.lower()), "")]
        ]
        entreprises += [
            {"nom": f[3] or f[0], "outil": "workday", "cle": f[0]} for f in liste.workday_flux
        ]
        entreprises += [
            {"nom": f[2] or f[1], "outil": f[0], "cle": str(f[1]).split("|")[0]}
            for f in liste.autres_flux
        ]
        uniques = {(e["outil"], e["cle"].lower()): e for e in entreprises}
        sortie.append(
            {
                "id": liste.ident,
                "titre": liste.titre,
                "description": liste.description,
                "active": liste.ident in ids,
                "entreprises": sorted(uniques.values(), key=lambda e: e["nom"].lower()),
            }
        )
    return sortie


def _nom(slug: str) -> str:
    """« forvismazars » → « Forvismazars » (as inventory names a slug)."""
    return re.sub(r"[-_]+", " ", slug).strip().title() or slug
