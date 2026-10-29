"""What the web interface shows, computed from the queue and the applications.

Pure functions over plain lists and dicts, so the tests need neither a window nor files;
`Api` only loads the data through `storage` and hands the result to the page.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import threading
import time
import webbrowser
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from datetime import date, datetime
from functools import cache
from pathlib import Path
from typing import Any

from jobhunter.web.background import FondApi
from jobhunter.web.guided import CandidatureApi
from jobhunter.web.panels import PanneauxApi
from jobhunter.web.workshop import AtelierApi

# Statuses of an application still waiting for an answer (same as the follow-ups).
EN_ATTENTE = ("postulé", "relancé")
# Entries of the follow-up file that are not applications (offer set aside).
ECARTEES = ("mauvaise", "pas intéressé", "expiré")
# A follow-up is due after this many days (the J+7 template).
JOURS_RELANCE = 7
_RX_SCAN = re.compile(r"^Scan (\d{4}-\d{2}-\d{2})$")


def _fit(o: dict[str, Any], champ: str = "fit") -> float:
    try:
        return float(o.get(champ) or 0)
    except (TypeError, ValueError):
        return 0.0


# What ouvrir_fichier opens with its program: CVs, letters, drafts.
DOCUMENTS = frozenset({".docx", ".doc", ".pdf", ".txt", ".odt", ".rtf", ".md"})


def _python() -> str:
    """The interpreter of the programs the page starts: a console one (frozen.interpreteur).

    Not sys.executable: the window runs under pythonw.exe (the desktop shortcut) or the
    compiled JobHunter.exe, neither of which gets a console. A program that reads the
    keyboard opened in a new console without any window (login pages, tools).
    """
    from jobhunter import frozen

    return frozen.interpreteur()


def _oid(o: dict[str, Any]) -> str:
    return f"{(o.get('entreprise') or '').strip()}|{(o.get('poste') or '').strip()}"


def _date(texte: Any) -> date | None:
    try:
        return datetime.strptime(str(texte or ""), "%Y-%m-%d").date()
    except ValueError:
        return None


def tableau(
    offres: Sequence[Any],
    suivi: Mapping[str, Any],
    aujourd_hui: date | None = None,
) -> dict[str, Any]:
    """Everything the home screen draws, as JSON-ready data."""
    jour = aujourd_hui or date.today()
    par_oid = {_oid(o): o for o in offres}
    postulees = [k for k, v in suivi.items() if v.get("s") in EN_ATTENTE]

    # New offers per morning scan, the last seven scans.
    scans = Counter(m.group(1) for o in offres if (m := _RX_SCAN.match(str(o.get("statut") or ""))))
    derniers = sorted(scans)[-7:]
    collecte = [{"jour": j, "n": scans[j]} for j in derniers]

    a_traiter = [o for o in offres if _RX_SCAN.match(str(o.get("statut") or ""))]
    meilleures = sorted(a_traiter, key=lambda o: (-_fit(o), -_fit(o, "fit_fin")))[:5]

    relances: list[dict[str, Any]] = []
    for k in postulees:
        d = _date(suivi[k].get("d"))
        if d and (jour - d).days >= JOURS_RELANCE:
            entreprise, _, poste = k.partition("|")
            relances.append({"entreprise": entreprise, "poste": poste, "jours": (jour - d).days})
    relances.sort(key=lambda r: -r["jours"])

    zones = Counter(str(o.get("zone") or "inconnu") for o in offres if _fit(o) >= 7)
    total_zones = sum(zones.values()) or 1

    candidatures = []
    for k, v in suivi.items():
        if not v.get("s") or v.get("retiree") or v["s"] in ECARTEES:
            continue
        o = par_oid.get(k, {})
        entreprise, _, poste = k.partition("|")
        candidatures.append(
            {
                "entreprise": entreprise,
                "poste": poste,
                "statut": v["s"],
                "date": v.get("d") or "",
                "fit": _fit(o) if o else None,
            }
        )
    candidatures.sort(key=lambda c: c["date"], reverse=True)

    return {
        "stats": {
            "file": len(offres),
            "neuf": sum(1 for o in a_traiter if _fit(o) >= 9),
            "postulees": len(postulees),
        },
        "collecte": collecte,
        "meilleures": [
            {
                "poste": o.get("poste") or "",
                "entreprise": o.get("entreprise") or "",
                "lieu": _lieu_propre(str(o.get("localisation") or "")),
                "fit": _fit(o),
                "url": o.get("url") or "",
            }
            for o in meilleures
        ],
        "relances": relances[:4],
        "relances_toutes": relances,
        "zones": [
            {"zone": z, "n": n, "pct": round(100 * n / total_zones)}
            for z, n in zones.most_common(3)
        ],
        "candidatures": candidatures[:6],
    }


# --- Offers screen ---------------------------------------------------------------

# What the "Statut" filter offers, and which queue statuses each one keeps.
# "écartées": the offers the desktop hides (pas intéressé, expiré, mauvaise).
FILTRES_STATUT = ("à traiter", "postulées", "écartées", "toutes")
PAR_PAGE = 40
PAR_PAGE_CHOIX = (20, 40, 100, 200)


def _date_offre(o: Mapping[str, Any]) -> str:
    """The most telling date of an offer: its publication, else when it was seen, else its scan."""
    for champ in ("date_publication", "vu_le"):
        d = _date(str(o.get(champ) or "")[:10])
        if d:
            return d.isoformat()
    m = _RX_SCAN.match(str(o.get("statut") or ""))
    return m.group(1) if m else ""


@cache
def _pays(lieu: str) -> str:
    from jobhunter.scoring import zones as _zones

    return _zones.pays_lieu(lieu)


@cache
def _lieu_propre(lieu: str) -> str:
    from jobhunter.scoring import zones as _zones

    return _zones.lieu_propre(lieu)


def _cle_tri(nom: str) -> str:
    """Alphabetical order without accents: "Égypte" among the E, not after "Viêt Nam"."""
    from jobhunter.text import sans_accent

    return sans_accent(nom).lower()


@cache
def _region_du_pays(pays: str) -> str:
    from jobhunter.scoring import zones as _zones

    return _zones.region_pays(pays)


@cache
def _region(lieu: str) -> str:
    from jobhunter.scoring import zones as _zones

    return _zones.region_pays(_pays(lieu))


def _alerte(o: Mapping[str, Any]) -> str:
    """The desktop's ⚑ column: ⚠ knock-out, ↻ reposted again and again, ≡ same text."""
    from jobhunter.scoring import ranking

    s = str(o.get("signal") or "")
    if "⚠" in s:
        return "⚠"
    if (o.get("republiee") or 0) >= ranking.reglages()["republiee_des"]:
        return "↻"
    if "même texte" in s or "doublon" in s:
        return "≡"
    return ""


def _ligne(o: Mapping[str, Any], suivi: Mapping[str, Any]) -> dict[str, Any]:
    k = _oid(o)  # type: ignore[arg-type]
    lieu = str(o.get("localisation") or "")
    return {
        "id": k,
        "poste": o.get("poste") or "",
        "entreprise": o.get("entreprise") or "",
        "lieu": _lieu_propre(lieu),
        "fit": _fit(o),  # type: ignore[arg-type]
        "zone": o.get("zone") or "",
        "contrat": o.get("contrat") or "",
        "date": _date_offre(o),
        "suivi": (suivi.get(k) or {}).get("s") or "",
        "url": o.get("url") or "",
        # the desktop's other columns (app.common.COLS)
        "domaine": o.get("domaine") or "",
        "pays": _pays(lieu).replace("?", ""),
        "region": _region(lieu).replace("?", ""),
        "publiee": str(o.get("date_publication") or "")[:10],
        # last seen alive: link checked or served again, whichever is later
        "signal": o.get("signal") or "",
        "alerte": _alerte(o),
        "source": o.get("source") or "",  # its logo beside the company (3.67)
    }


def _choix(v: Any) -> set[str]:
    """A filter's chosen values: one value or several (the user, 2026-10-27); empty = all."""
    if isinstance(v, str):
        return {v} if v else set()
    if isinstance(v, (list, tuple, set)):
        return {str(x) for x in v if x}
    return set()


def _par_page(n: Any) -> int:
    try:
        n = int(n)
    except (TypeError, ValueError):
        return PAR_PAGE
    return n if n in PAR_PAGE_CHOIX else PAR_PAGE


def offres(
    offres: Sequence[Any],
    suivi: Mapping[str, Any],
    texte: str = "",
    zone: str | Sequence[str] = "",
    fit_min: float = 0,
    statut: str = "à traiter",
    domaine: str | Sequence[str] = "",
    contrat: str | Sequence[str] = "",
    tri: str = "fit",
    page: int = 0,
    pays: str | Sequence[str] = "",
    region: str | Sequence[str] = "",
    par_page: int = PAR_PAGE,
) -> dict[str, Any]:
    """One page of the offers screen, filtered and sorted, with the filter choices.

    Each list filter takes one value or several (any of them matches). The countries
    offered are those of the chosen regions; a chosen country outside them is dropped.
    """
    mots = [m for m in (texte or "").lower().split() if m]
    zones_, domaines, contrats = _choix(zone), _choix(domaine), _choix(contrat)
    regions = _choix(region)
    tous_pays = {p for o in offres if (p := _pays(str(o.get("localisation") or ""))) != "?"}
    proposes = {p for p in tous_pays if not regions or _region_du_pays(p) in regions}
    pays_ = _choix(pays) & proposes if regions else _choix(pays)
    par_page = _par_page(par_page)
    gardees = []
    for o in offres:
        st = str(o.get("statut") or "")
        k = _oid(o)
        if statut == "à traiter" and (not _RX_SCAN.match(st) or k in suivi):
            continue
        if statut == "postulées" and (suivi.get(k) or {}).get("s") not in EN_ATTENTE:
            continue
        if statut == "écartées" and (suivi.get(k) or {}).get("s") not in ECARTEES:
            continue
        if domaines and o.get("domaine") not in domaines:
            continue
        if contrats and o.get("contrat") not in contrats:
            continue
        if zones_ and o.get("zone") not in zones_:
            continue
        if pays_ and _pays(str(o.get("localisation") or "")) not in pays_:
            continue
        if regions and _region(str(o.get("localisation") or "")) not in regions:
            continue
        if fit_min and _fit(o) < fit_min:
            continue
        if mots:
            botte = f"{o.get('poste') or ''} {o.get('entreprise') or ''} {o.get('localisation') or ''}".lower()
            if not all(m in botte for m in mots):
                continue
        gardees.append(o)
    cles: dict[str, Callable[[Any], Any]] = {
        "fit": lambda o: (-_fit(o), -_fit(o, "fit_fin")),
        "date": lambda o: _date_offre(o),
        "entreprise": lambda o: str(o.get("entreprise") or "").lower(),
        "publiee": lambda o: str(o.get("date_publication") or "")[:10],
    }
    gardees.sort(key=cles.get(tri, cles["fit"]), reverse=tri in ("date", "publiee"))
    page = max(0, int(page))
    debut = page * par_page
    return {
        "total": len(gardees),
        "page": page,
        "pages": max(1, -(-len(gardees) // par_page)),
        "par_page": par_page,
        "lignes": [_ligne(o, suivi) for o in gardees[debut : debut + par_page]],
        # what the filters really applied: the countries left once the regions chosen
        "choisis": {"pays": sorted(pays_, key=_cle_tri)},
        "zones": sorted({str(o.get("zone")) for o in offres if o.get("zone")}),
        "domaines": sorted({str(o.get("domaine")) for o in offres if o.get("domaine")}),
        "contrats": sorted({str(o.get("contrat")) for o in offres if o.get("contrat")}),
        # "?" is no choice: the offers it groups have no place (zones.lieu_deduit
        # finds most of them); "Tous les pays" still shows them.
        "pays": sorted(proposes, key=_cle_tri),
        "regions": sorted(
            {r for o in offres if (r := _region(str(o.get("localisation") or ""))) != "?"},
            key=_cle_tri,
        ),
        "statuts": list(FILTRES_STATUT),
    }


def fiche(o: Mapping[str, Any], suivi: Mapping[str, Any], description: str) -> dict[str, Any]:
    """Everything the detail sheet of one offer shows."""
    k = _oid(o)  # type: ignore[arg-type]
    s = suivi.get(k) or {}
    return {
        **_ligne(o, suivi),
        "statut": o.get("statut") or "",
        "domaine": o.get("domaine") or "",
        "source": o.get("source") or "",
        "fit_fin": _fit(o, "fit_fin"),  # type: ignore[arg-type]
        "description": description or "",
        "note": s.get("n") or "",
        "postule_le": s.get("d") or "",
        "envoi": s.get("envoi") or "",
        "pourquoi": o.get("pourquoi") or "",
        "republiee": o.get("republiee") or 0,  # programs/reposts: times reposted in 90 days
        "exp_requise": o.get("exp_requise") or "",
        "salaire": o.get("salaire") or "",
        "teletravail": o.get("teletravail") or "",
        "cv": o.get("cv") or "",
        "lettre": o.get("lettre") or "",
    }


# --- Applications screen ------------------------------------------------------------

# Columns of the applications board, in order; any other status goes to "Autres".
COLONNES = ("à postuler", "postulé", "relancé", "entretien", "refus")


def candidatures(offres: Sequence[Any], suivi: Mapping[str, Any]) -> dict[str, Any]:
    """The applications grouped by status, most recent first in each column."""
    par_oid = {_oid(o): o for o in offres}
    colonnes: dict[str, list[dict[str, Any]]] = {c: [] for c in (*COLONNES, "autres")}
    ecartees = 0
    for k, v in suivi.items():
        s = v.get("s")
        if not s or v.get("retiree"):
            continue
        if s in ECARTEES:
            ecartees += 1
            continue
        entreprise, _, poste = k.partition("|")
        o = par_oid.get(k, {})
        colonnes[s if s in colonnes else "autres"].append(
            {
                "id": k,
                "entreprise": entreprise,
                "poste": poste,
                "statut": s,
                "date": v.get("d") or "",
                "note": v.get("n") or "",
                "fit": _fit(o) if o else None,
                "url": o.get("url") or "",
            }
        )
    for c in colonnes.values():
        c.sort(key=lambda e: e["date"], reverse=True)
    return {
        "colonnes": [
            {"statut": c, "entrees": colonnes[c]} for c in colonnes if colonnes[c] or c in COLONNES
        ],
        "ecartees": ecartees,
    }


# --- Sources screen --------------------------------------------------------------------


def rendement(lignes: Sequence[Mapping[str, Any]], derniers: int = 7) -> list[dict[str, Any]]:
    """Per source, over the last runs of the yield log: offers brought, new, verdict."""
    par_source: dict[str, dict[str, Any]] = {}
    for ligne in list(lignes)[-derniers * 6 :]:
        le = str(ligne.get("le") or "")[:10]
        for nom, r in (ligne.get("sources") or {}).items():
            s = par_source.setdefault(
                nom, {"source": nom, "ramenees": 0, "nouvelles": 0, "dernier": "", "verdict": ""}
            )
            s["ramenees"] += int(r.get("ramenees") or 0)
            s["nouvelles"] += int(r.get("nouvelles") or 0)
            if le >= s["dernier"]:
                s["dernier"], s["verdict"] = le, str(r.get("verdict") or "")
    return sorted(par_source.values(), key=lambda s: -s["nouvelles"])


# --- Settings screen -------------------------------------------------------------------

# Windows 11 backdrops (DWMWA_SYSTEMBACKDROP_TYPE): acrylic blurs what is behind the
# window, mica only tints the wallpaper, "net" draws nothing so the desktop shows sharp
# through the see-through page, "aucun" draws nothing either but the page is opaque.
FONDS = {"acrylique": 3, "mica": 2, "net": 1, "aucun": 1}
# Accent families and fonts of the settings screen; their looks live in style.css / app.js.
TEINTES = ("terre", "vert", "bleu", "noir")
POLICES = ("segoe", "bahnschrift", "corbel", "sitka", "georgia")
# Light or dark; "auto" follows Windows.
MODES = ("auto", "clair", "sombre")
REGLAGES: dict[str, Any] = {
    "fond": "acrylique",
    # Opaque at first: the user chooses how much of the desktop shows through
    # (the user, 2026-10-28: « à la première ouverture, l'opacité au maximum »).
    "verre": 0,
    "teinte": "terre",
    "police": "segoe",
    "mode": "auto",
    "menu": "large",
    "par_page": PAR_PAGE,
}


def reglages(brut: Any) -> dict[str, Any]:
    """The display settings, each missing or wrong value replaced by its default.

    verre: 0 (opaque) to 100 (the blurred wallpaper shows the most), in steps of 1.
    """
    d = brut if isinstance(brut, Mapping) else {}
    fond = d.get("fond")
    try:
        verre = min(100, max(0, int(d.get("verre", REGLAGES["verre"]))))
    except (TypeError, ValueError):
        verre = REGLAGES["verre"]
    teinte, police = d.get("teinte"), d.get("police")
    return {
        "fond": fond if fond in FONDS else REGLAGES["fond"],
        "verre": verre,
        "teinte": teinte if teinte in TEINTES else REGLAGES["teinte"],
        "police": police if police in POLICES else REGLAGES["police"],
        "mode": d.get("mode") if d.get("mode") in MODES else REGLAGES["mode"],
        # the side menu folded to its icons, for more room (the user, 2026-10-27)
        "menu": d.get("menu") if d.get("menu") in ("large", "etroit") else REGLAGES["menu"],
        "par_page": _par_page(d.get("par_page")),
    }


def _fichier_reglages() -> Path | None:
    """The main folder's settings file, the same as the interface language's.

    Same path as `jobhunter.app.language._fichier()`, rebuilt here: only the desktop
    app may import jobhunter.app (tests/test_architecture.py).
    """
    from jobhunter import profiles, root

    try:
        p = profiles.principale()
    except RuntimeError:
        return None
    return p / root.nom("Scripts", p) / "_interface.json"


def lire_reglages() -> dict[str, Any]:
    """The saved display settings, defaults when there are none."""
    f = _fichier_reglages()
    try:
        brut = json.loads(f.read_text(encoding="utf-8")).get("web") if f else None
    except (OSError, ValueError, AttributeError):
        brut = None
    return reglages(brut)


def ecrire_reglages(valeurs: Any) -> dict[str, Any]:
    """Saves the display settings under "web", keeping the file's other keys.

    A file that exists but cannot be read is left alone: overwriting it would lose
    the interface language.
    """
    propres = reglages(valeurs)
    f = _fichier_reglages()
    if f is None:
        return propres
    try:
        tout = json.loads(f.read_text(encoding="utf-8"))
    except FileNotFoundError:
        tout = {}
    except (OSError, ValueError):
        return propres
    if not isinstance(tout, dict):
        return propres
    tout["web"] = propres
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_name(f.name + ".tmp")
    tmp.write_text(json.dumps(tout, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, f)
    return propres


# --- Tasks -------------------------------------------------------------------------------

# What the buttons may start: programs the desktop app's buttons already run
# (app/execution.py, app/common.py), and nothing else. None of them sends anything.
TACHES: dict[str, tuple[str, list[str]]] = {
    "collecte": ("Collecte du matin", ["jobhunter.programs.daily_pipeline", "--un-profil"]),
    "scan": ("Scan offres", ["jobhunter.sources", "--all"]),  # the desktop's first step
    "brouillons": ("Brouillons de relance", ["jobhunter.programs.follow_ups", "--brouillons"]),
    "regenerer_cv": ("Refaire les CV", ["jobhunter.programs.regenerate_docs", "--cv"]),
    "regenerer_lettres": ("Refaire les lettres", ["jobhunter.programs.regenerate_docs"]),
    "disponibilite": (
        "Contrôle des offres fermées",
        ["jobhunter.programs.availability_audit", "--supprime"],
    ),
    "sites_carrieres": (
        "Offres des entreprises vues",
        ["jobhunter.sources", "--entreprises-vues"],
    ),
    "annuaire_workday": (
        "Annuaire Workday (Common Crawl)",
        ["jobhunter.sources.discovery", "--workday"],
    ),
    "documents_top": (
        "CV et lettres des 30 meilleures offres",
        ["jobhunter.programs.generate_docs", "--top", "30"],
    ),
    # after a change of places / of skills (the desktop app runs the same)
    "zones": ("Zones des offres mises à jour", ["jobhunter.scoring.zones", "--ecrire"]),
    "rescore": ("Recalculer le fit", ["jobhunter.programs.rescore_ats"]),
    # signed release, checked before it is installed (programs.update)
    "maj": ("Mise à jour de JobHunter", ["jobhunter.programs.update"]),
    # + the offer's URL, which generate_docs matches by substring
    "documents": ("CV et lettre de l'offre", ["jobhunter.programs.generate_docs", "--url"]),
    # + an http(s) link pasted by the user: title, company, description → queue
    "ajout": ("Ajouter une offre", ["jobhunter.programs.add_offer", "--url"]),
    # + the offer's identity: its description fetched online (headless)
    "description": ("Description de l'offre", ["jobhunter.programs.scrape_desc", "--key"]),
}

# Interface languages (jobhunter.app.language.noms; that module is the desktop's).
LANGUES = {"fr": "Français", "en": "English", "de": "Deutsch", "es": "Español"}

# Statuses the page may set on an application: the desktop's list ("" clears it).
STATUTS = ("à postuler", "à vérifier", "postulé", "relancé", "entretien", "refus", *ECARTEES)


class Tache:
    """One program started by a button, its output kept for the page to poll."""

    def __init__(self, cle: str, libelle: str, cmd: list[str], cwd: Path) -> None:
        """Starts `cmd` without a console window; a thread reads its output."""
        self.cle, self.libelle = cle, libelle
        self.lignes: list[str] = []
        self.code: int | None = None
        self.debut = time.time()
        self.proc = subprocess.Popen(  # nosec B603 : our own programs, from TACHES
            cmd,
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        threading.Thread(target=self._lire, daemon=True).start()

    def _lire(self) -> None:
        assert self.proc.stdout is not None
        for ligne in self.proc.stdout:
            self.lignes.append(ligne.rstrip("\n"))
            if len(self.lignes) > 500:
                del self.lignes[:100]
        self.code = self.proc.wait()

    def etat(self) -> dict[str, Any]:
        """What the task panel shows: label, last lines, finished or not, exit code."""
        return {
            "cle": self.cle,
            "libelle": self.libelle,
            "lignes": [x for x in self.lignes if x.strip()][-8:],
            "fini": self.code is not None,
            "code": self.code,
            "duree": int(time.time() - self.debut),
        }


# --- Profile and search, edited ----------------------------------------------------------


def _textes(v: Any) -> list[str]:
    """A list of non-empty strings from whatever the page sent."""
    return [str(x).strip() for x in (v if isinstance(v, list) else []) if str(x).strip()]


def _entrees(v: Any) -> list[str]:
    """Words of a list as typed, repeats removed: NOT stripped.

    A space can be meant: the synonym "ia " finds "IA " but not "social", "git " not
    "digital". Stripping it, as the desktop's skill editor does, widens the match.
    """
    vus: dict[str, None] = {}
    for x in v if isinstance(v, list) else []:
        s = str(x)
        if s.strip() and s.lower() not in {k.lower() for k in vus}:
            vus[s] = None
    return list(vus)


def _lieu(e: Any) -> Any:
    """A zone entry the page sent back: a catalogue key, or a declared sector; else None."""
    if isinstance(e, str) and e.strip():
        return e.strip().lower()
    if isinstance(e, Mapping) and str(e.get("cle") or "").strip():
        return {
            "cle": str(e["cle"]).strip(),
            "libelle": str(e.get("libelle") or e["cle"]).strip(),
            "lieux": _textes(e.get("lieux")) or [str(e.get("libelle") or e["cle"]).strip()],
        }
    return None


def _ecrire_json(f: Path, donnees: Any) -> None:
    """Atomic write, the way search_settings writes sources_config.json."""
    tmp = f.with_name(f.name + ".tmp")
    tmp.write_text(json.dumps(donnees, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(f)


def _version_installee() -> str:
    """The running JobHunter's version.

    The compiled application (installer, Store) carries no pip metadata: its version is
    the VERSION file shipped with it. Reading only the metadata showed « ? » there, and
    offered every release as new (the user, 2026-10-29).
    """
    from importlib.metadata import PackageNotFoundError, version

    from jobhunter import frozen

    if frozen.est_gele():
        from jobhunter.programs import update

        v = update.version_locale()
        return v if v != "0" else "?"
    try:
        return version("jobhunter")
    except PackageNotFoundError:
        return "?"


# Waits for the application to close, then sends its data folder to the Recycle Bin.
# Values come by environment variables, never pasted into the script.
_CORBEILLE = r"""
try { Wait-Process -Id ([int]$env:JH_PID) -Timeout 120 -ErrorAction Stop } catch {}
Add-Type -AssemblyName Microsoft.VisualBasic
[Microsoft.VisualBasic.FileIO.FileSystem]::DeleteDirectory(
  $env:JH_DOSSIER, 'OnlyErrorDialogs', 'SendToRecycleBin')
"""


def _dossier_effacable() -> Path | None:
    """The data folder « Effacer mes données » may remove, None when there is none.

    Only the installed application's own folder (Documents/JobHunter): never a folder
    named by JOBHUNTER_RACINE, nor a source or pip installation's, which may hold
    anything else (a git repository, the author's own files).
    """
    from jobhunter import frozen, profiles

    if not frozen.est_gele():
        return None
    dossier = profiles.principale().resolve()
    defaut = (Path.home() / "Documents" / "JobHunter").resolve()
    return dossier if dossier == defaut and dossier.is_dir() else None


def _derniere_version(timeout: float = 6) -> str:
    """The latest release tag of the public repository, "" when offline."""
    import urllib.request

    req = urllib.request.Request(
        "https://api.github.com/repos/Grisbix/JobHunter/releases/latest",
        headers={"User-Agent": "JobHunter-web", "Accept": "application/vnd.github+json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:  # nosec B310 : fixed https URL
            return str(json.loads(r.read()).get("tag_name") or "").removeprefix("v")
    except (OSError, ValueError):
        return ""


def _signee(version: str, timeout: float = 6) -> bool:
    """Is the author's signature of `version` published (the release asset)?

    A release exists as soon as it is merged, before the author signs it: offering it
    then led to "pas encore signée" on the click (programs.update.prete).
    """
    import urllib.request

    from jobhunter import signature

    url = f"https://github.com/Grisbix/JobHunter/releases/download/v{version}/{signature.FICHIER}"
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "JobHunter-web"})
    try:
        with urllib.request.urlopen(req, timeout=timeout):  # nosec B310 : fixed https URL
            return True
    except (OSError, ValueError):
        return False


def _plus_recente(a: str, b: str) -> bool:
    """Is version `a` more recent than `b`? ("3.28.0" > "3.27.2")."""

    def cle(v: str) -> tuple[int, ...]:
        return tuple(int(x) if x.isdigit() else 0 for x in v.strip().split("."))

    return bool(a) and cle(a) > cle(b)


def bureau_a_distance() -> bool:
    """True in a Remote Desktop session (Windows' SM_REMOTESESSION).

    There every frame is encoded and sent over the network, at about 30 per second:
    the frosted panels and the blurred backdrop are redrawn and sent with each scroll
    (the user's session, 2026-10-28: « je trouve ça lent »).
    """
    if sys.platform != "win32":
        return False
    try:
        import ctypes

        return bool(ctypes.windll.user32.GetSystemMetrics(0x1000))  # type: ignore[attr-defined,unused-ignore]
    except (AttributeError, OSError):
        return False


class Api(PanneauxApi, AtelierApi, CandidatureApi, FondApi):
    """Methods the page calls through `window.pywebview.api`.

    Nothing here writes to the queue, the applications or the profile; only the
    display settings are saved.
    """

    # Set by __main__ once the window exists; private, so pywebview does not expose it.
    _fenetre: Any = None
    _basculer: Any = None  # full screen <-> rounded window
    # Applies a backdrop by name, see FONDS. Not `_fond`: that is the background loop
    # (web.background), which this attribute overwrote — every fond_etat call failed
    # and the background's news never reached the page (found 2026-10-28).
    _toile: Any = None
    _tache: Tache | None = None

    def __init__(self) -> None:
        """An empty cache: each data file is read on first use."""
        self._cache: dict[str, tuple[float, Any]] = {}
        self._propositions: list[Any] = []  # last email suggestions, applied by index
        # Undo (the desktop's Ctrl+Z): per gesture, each application as it was before.
        self._annuler: list[list[tuple[str, dict[str, Any]]]] = []

    # Data, reloaded only when its file changed.
    def _lire(self, cle: str, fichier: Path, charger: Any) -> Any:
        try:
            mtime = fichier.stat().st_mtime
        except OSError:
            mtime = 0.0
        vu = self._cache.get(cle)
        if vu is None or vu[0] != mtime:
            vu = (mtime, charger())
            self._cache[cle] = vu
        return vu[1]

    def _file(self) -> list[Any]:
        from jobhunter.storage import queue

        return self._lire("file", queue.CHEMIN, lambda: queue.charger(descriptions=False))

    def _suivi(self) -> Mapping[str, Any]:
        from jobhunter.storage import applications

        return self._lire("suivi", applications.CHEMIN, applications.charger)

    def _descriptions(self) -> Mapping[str, str]:
        from jobhunter.storage import queue

        return self._lire("desc", queue.DESCRIPTIONS, queue._lire_descriptions)

    # Screens.
    def tableau(self) -> dict[str, Any]:
        """The home screen data, from the real queue and applications."""
        from jobhunter.links import existe

        d = tableau(self._file(), self._suivi())
        bonnes = [o for o in self._file() if (o.get("fit") or 0) >= 8]
        prets = sum(1 for o in bonnes if existe(o.get("cv")) and existe(o.get("lettre")))
        d["documents"] = {"bonnes": len(bonnes), "prets": prets, "a_preparer": len(bonnes) - prets}
        from jobhunter import api_keys, root
        from jobhunter.sources import countries

        nom = api_keys.conseillee(root.dossier_cles(), countries.maison())
        d["cle_conseillee"] = (
            {
                "nom": nom,
                "libelle": api_keys.CLES[nom].libelle,
                "obtenir": api_keys.CLES[nom].obtenir,
            }
            if nom
            else None
        )
        return d

    # Saved views of the offers screen and its columns (web.saved_views).
    def vues(self) -> dict[str, Any]:
        """The saved views and the visible columns."""
        from jobhunter.web import saved_views

        return saved_views.lire()

    def enregistrer_vue(self, nom: str, filtres: dict[str, Any]) -> dict[str, Any]:
        """Keeps the screen's filters and sort under a name (same name: replaced)."""
        from jobhunter.web import saved_views

        if not saved_views.enregistrer(nom, filtres):
            return {"ok": False, "erreur": "donne un nom à la vue"}
        return {"ok": True}

    def supprimer_vue(self, nom: str) -> dict[str, Any]:
        """Forgets a saved view (the offers are not touched)."""
        from jobhunter.web import saved_views

        if not saved_views.supprimer(nom):
            return {"ok": False, "erreur": "vue inconnue"}
        return {"ok": True}

    def memoriser_colonnes(self, colonnes: list[str]) -> dict[str, Any]:
        """Remembers the visible columns for the next start."""
        from jobhunter.web import saved_views

        if not saved_views.memoriser_colonnes(colonnes):
            return {"ok": False, "erreur": "garde au moins une colonne"}
        return {"ok": True}

    def offres(self, filtres: dict[str, Any] | None = None) -> dict[str, Any]:
        """One page of the offers screen; filtres: texte, zone, fit_min, statut, tri, page, par_page."""
        f = filtres or {}
        return offres(
            self._file(),
            self._suivi(),
            texte=str(f.get("texte") or ""),
            zone=sorted(_choix(f.get("zone"))),
            fit_min=float(f.get("fit_min") or 0),
            statut=str(f.get("statut") or "à traiter"),
            domaine=sorted(_choix(f.get("domaine"))),
            contrat=sorted(_choix(f.get("contrat"))),
            pays=sorted(_choix(f.get("pays"))),
            region=sorted(_choix(f.get("region"))),
            tri=str(f.get("tri") or "fit"),
            page=int(f.get("page") or 0),
            par_page=_par_page(f.get("par_page")),
        )

    def offre(self, ident: str) -> dict[str, Any] | None:
        """The detail sheet of one offer, by its "entreprise|poste" identity."""
        for o in self._file():
            if _oid(o) == ident:
                return fiche(o, self._suivi(), self._descriptions().get(ident, ""))
        return None

    def candidatures(self) -> dict[str, Any]:
        """The applications board."""
        return candidatures(self._file(), self._suivi())

    def relances(self) -> dict[str, Any]:
        """Follow-ups due, and the drafts already written in Letters/Follow_ups."""
        dossier = _dossier_relances()
        brouillons = []
        if dossier.is_dir():
            for p in sorted(dossier.glob("*.txt"), key=lambda p: -p.stat().st_mtime):
                brouillons.append(
                    {
                        "nom": p.name,
                        "titre": p.stem.replace("_", " "),
                        "date": datetime.fromtimestamp(p.stat().st_mtime).date().isoformat(),
                    }
                )
        d = tableau(self._file(), self._suivi())
        return {"dues": d["relances_toutes"], "brouillons": brouillons[:60]}

    def brouillon(self, nom: str) -> str:
        """The text of one follow-up draft; only a plain file name of that folder."""
        if not re.fullmatch(r"[^\\/:*?\"<>|]+\.txt", nom or ""):
            return ""
        try:
            return (_dossier_relances() / nom).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return ""

    def documents(self, filtres: dict[str, Any] | None = None) -> dict[str, Any]:
        """CVs and letters made per offer, most recent first, filtered by text.

        One line per document: its .docx (the text to change) and its .pdf (what is
        sent) are the same CV, listed twice before 3.35. `dossiers` says where they are.
        """
        f = filtres or {}
        mots = [m for m in str(f.get("texte") or "").lower().split() if m]
        seul = f.get("genre")  # "CV" or "Lettre"; anything else: both
        par_doc: dict[tuple[str, str], dict[str, Any]] = {}
        # How many exist, whatever the filters: « Refaire » shows only when there is
        # something to redo (the user, 2026-10-28).
        existants: dict[str, set[str]] = {"CV": set(), "Lettre": set()}
        for genre, dossier in _dossiers_documents().items():
            if not dossier.is_dir():
                continue
            for p in dossier.iterdir():
                if p.suffix.lower() not in (".pdf", ".docx"):
                    continue
                existants.setdefault(genre, set()).add(p.stem.lower())
                if seul in ("CV", "Lettre") and genre != seul:
                    continue
                if mots and not all(m in p.stem.lower() for m in mots):
                    continue
                st = p.stat()
                date = datetime.fromtimestamp(st.st_mtime).date().isoformat()
                # Windows ignores case: « CV_X.pdf » and « cv_x.docx » are one document.
                d = par_doc.setdefault(
                    (genre, p.stem.lower()),
                    {"genre": genre, "nom": p.stem.replace("_", " "), "date": date},
                )
                d["date"] = max(d["date"], date)
                d[p.suffix[1:].lower()] = str(p)
        fichiers = [
            {
                **{k: v for k, v in d.items() if k not in ("docx", "pdf")},
                "chemin": d.get("docx") or d["pdf"],
                "modifiable": "docx" in d,
            }
            for d in par_doc.values()
        ]
        fichiers.sort(key=lambda x: x["date"], reverse=True)
        page = max(0, int(f.get("page") or 0))
        return {
            "total": len(fichiers),
            "existants": {g: len(s) for g, s in existants.items()},
            "page": page,
            "pages": max(1, -(-len(fichiers) // PAR_PAGE)),
            "fichiers": fichiers[page * PAR_PAGE : (page + 1) * PAR_PAGE],
            "dossiers": [{"genre": g, "chemin": str(d)} for g, d in _dossiers_documents().items()],
        }

    def ouvrir_dossier_documents(self, genre: str) -> bool:
        """Opens the folder of the CVs or of the letters made per offer in the Explorer."""
        d = _dossiers_documents().get(genre)
        if d is None or not d.is_dir():
            return False
        os.startfile(d)  # type: ignore[attr-defined,unused-ignore]  # nosec B606
        return True

    def profil(self) -> dict[str, Any]:
        """What the profile says, without the application form fields."""
        from jobhunter import profile, search_settings

        p = profile.charger()
        ident = p.get("identite") or {}
        reg = search_settings.lire(p)
        sc = p.get("scoring") or {}
        return {
            "identite": {
                k: ident.get(k) or "" for k in ("prenom", "nom", "ville", "email", "linkedin")
            },
            "langues": p.get("langues_parlees") or [],
            "domaines": [
                {"libelle": d.get("libelle") or d.get("cle") or "", "cle": d.get("cle") or ""}
                for d in (p.get("domaines") or [])
            ],
            "competences": list((p.get("competences") or {}).keys()),
            "outils": list((p.get("termes") or {}).keys()),
            "prioritaires": [search_settings.libelle_lieu(e) for e in reg.prioritaires or []],
            "secondaires": [search_settings.libelle_lieu(e) for e in reg.secondaires or []],
            "garder": reg.garder,
            "ecarter": reg.ecarter,
            "scoring": {
                k: sc.get(k)
                for k in (
                    "cible_score",
                    "plafond_complement",
                    "plafond_sans_coeur",
                    "plafond_second",
                )
                if k in sc
            },
        }

    def sources(self) -> dict[str, Any]:
        """Collection keywords, career-site slugs, exclusions and the yield of each source."""
        import json

        from jobhunter import root

        donnees = root.scripts()
        try:
            conf = json.loads((donnees / "sources_config.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            conf = {}
        lignes = []
        try:
            texte = (donnees / root.nom("_rendement.jsonl")).read_text(encoding="utf-8")
        except OSError:
            texte = ""
        for t in texte.splitlines():
            try:
                lignes.append(json.loads(t))
            except ValueError:
                continue
        slugs = conf.get("ats_slugs") or {}
        return {
            "mots_cles": conf.get("keywords") or [],
            "ats": {k: len(v) if isinstance(v, (list, dict)) else 1 for k, v in slugs.items()},
            "contrats_exclus": conf.get("contrats_exclus") or [],
            "pays_exclus": conf.get("pays_exclus") or [],
            "rendement": rendement(lignes),
        }

    def maintenance(self) -> dict[str, Any]:
        """Engine version, last collection, backups and data sizes."""
        import json

        from jobhunter import root

        donnees = root.scripts()
        v = _version_installee()
        try:
            c = json.loads((donnees / "_derniere_collecte.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            c = {}
        sauvegardes = root.dans(donnees, "_sauvegardes")
        tailles = []
        for nom in ("apply_queue.json", "descriptions.json", root.nom("suivi.json")):
            p = donnees / nom
            if p.exists():
                tailles.append({"nom": nom, "octets": p.stat().st_size})
        jours = (
            sorted((p.name for p in sauvegardes.iterdir() if p.is_dir()), reverse=True)[:7]
            if sauvegardes.is_dir()
            else []
        )
        collecte = {k: c.get(k) for k in ("etat", "debut", "fin", "code", "dernier_succes")}
        collecte["erreurs"] = len(c.get("erreurs") or [])
        return {
            "version": v,
            "effacable": _dossier_effacable() is not None,
            "collecte": collecte,
            "sauvegardes": jours,
            "tailles": tailles,
            "offres": len(self._file()),
            "candidatures": sum(1 for e in self._suivi().values() if e.get("s")),
        }

    def reglages(self) -> dict[str, Any]:
        """The display settings: window backdrop and glass strength."""
        return lire_reglages()

    def session(self) -> dict[str, Any]:
        """Is the window seen through Remote Desktop? Then the page drops its blurs."""
        return {"distance": bureau_a_distance()}

    def textes(self) -> dict[str, Any]:
        """The interface language and its catalogue, for app.js (jobhunter.web.i18n)."""
        from jobhunter.web import i18n

        return i18n.catalogue(i18n.langue())

    def regler(self, valeurs: dict[str, Any]) -> dict[str, Any]:
        """Saves the display settings; a new backdrop applies at once."""
        r = ecrire_reglages(valeurs)
        if self._toile:
            self._toile(r["fond"])
        return r

    # Profile and search, edited: the same functions as the desktop app's panels
    # (search_settings, skills_settings): checked first, previous profile kept as .bak.
    def _profil_brut(self) -> dict[str, Any]:
        from jobhunter import profile

        return dict(json.loads(Path(profile.FICHIER).read_text(encoding="utf-8")))

    def _ecrire_profil(self, nouveau: dict[str, Any]) -> str:
        from jobhunter import profile, search_settings

        bak = search_settings.ecrire(Path(profile.FICHIER), nouveau)
        profile.recharger()
        return bak.name

    def recherche(self) -> dict[str, Any]:
        """Collection keywords, titles kept and set aside, places, as the page edits them."""
        from jobhunter import search_settings as rs

        p = self._profil_brut()
        r = rs.lire(p)

        def lieux(v: list[Any] | None) -> list[dict[str, Any]]:
            return [
                {"entree": e, "libelle": rs.libelle_lieu(e), "genre": rs.genre_lieu(e)}
                for e in v or []
            ]

        return {
            "mots_cles": rs.mots_cles_collecte(p),
            "garder": rs.eclater(r.garder),
            "ecarter": rs.eclater(r.ecarter),
            "prioritaires": lieux(r.prioritaires),
            "secondaires": lieux(r.secondaires),
        }

    def lieux(self, texte: str) -> list[dict[str, Any]]:
        """Places matching what is typed: the catalogue, then the text as a free place."""
        from jobhunter import search_settings as rs

        return [
            {"entree": e, "libelle": lib, "genre": rs.genre_lieu(e)}
            for e, lib in rs.chercher_lieux(str(texte or ""))
        ]

    def enregistrer_recherche(self, d: dict[str, Any]) -> dict[str, Any]:
        """Saves the search (profile + sources_config keywords); new places re-zone the queue."""
        from jobhunter import search_settings as rs

        def places(cle: str) -> list[Any]:
            return [x for x in (_lieu((e or {}).get("entree")) for e in d.get(cle) or []) if x]

        p = self._profil_brut()
        avant = rs.lire(p)
        mots, garder, ecarter = (_entrees(d.get(k)) for k in ("mots_cles", "garder", "ecarter"))
        # A list left as it was keeps its form in the file: the page shows "re:(a|b)" as
        # one word per line (eclater), which would otherwise be rewritten at each save.
        mots_changes = mots != rs.mots_cles_collecte(p)
        r = rs.Reglages(
            mots_cles=mots if mots_changes else avant.mots_cles or mots,
            garder=avant.garder if garder == rs.eclater(avant.garder) else garder,
            ecarter=avant.ecarter if ecarter == rs.eclater(avant.ecarter) else ecarter,
            prioritaires=places("prioritaires"),
            secondaires=places("secondaires"),
        )
        if erreurs := rs.valider(r):
            return {"ok": False, "erreurs": erreurs}
        bak = self._ecrire_profil(rs.appliquer(p, r))
        if mots_changes:
            rs.ecrire_mots_cles(r.mots_cles)  # what the collection reads
        zones = (avant.prioritaires, avant.secondaires) != (r.prioritaires, r.secondaires)
        if zones:
            self.lancer("zones")  # the Zone column follows the new places
        return {"ok": True, "bak": bak, "zones": zones}

    def competences(self) -> dict[str, Any]:
        """The skills, the axes they count for, and which are CV base skills (not removable)."""
        from jobhunter import skills_settings as sk

        p = self._profil_brut()
        base = set(p.get("competences_de_base") or [])
        return {
            "axes": sk.axes(p),
            "liste": [
                {
                    "nom": c.nom,
                    "axes": c.axes,
                    "synonymes": c.synonymes,
                    "en": c.en,
                    "base": c.nom in base,
                }
                for c in sk.lire(p)
            ],
        }

    def enregistrer_competences(self, liste: list[dict[str, Any]]) -> dict[str, Any]:
        """Saves the skills; what the page does not show (prose_fr…) is kept by name."""
        from jobhunter import skills_settings as sk

        p = self._profil_brut()
        autres = {c.nom: c.autres for c in sk.lire(p)}
        nouvelles = []
        for x in liste if isinstance(liste, list) else []:
            nom = str(x.get("nom") or "").strip()
            nouvelles.append(
                sk.Competence(
                    nom=nom,
                    axes=_textes(x.get("axes")),
                    synonymes=_entrees(x.get("synonymes")),
                    en=str(x.get("en") or "").strip(),
                    autres=dict(autres.get(nom, {})),
                )
            )
        if erreurs := sk.valider(nouvelles, p):
            return {"ok": False, "erreurs": erreurs}
        return {"ok": True, "bak": self._ecrire_profil(sk.appliquer(p, nouvelles))}

    def enregistrer_identite(self, d: dict[str, Any]) -> dict[str, Any]:
        """Saves name, town, email, LinkedIn and the languages spoken."""
        p = self._profil_brut()
        ident = dict(p.get("identite") or {})
        for k in ("prenom", "nom", "ville", "email", "linkedin"):
            if k in d:
                ident[k] = str(d.get(k) or "").strip()
        if not ident.get("prenom") or not ident.get("nom"):
            return {"ok": False, "erreurs": ["le prénom et le nom sont nécessaires (lettres, CV)"]}
        nouveau = json.loads(json.dumps(p))
        nouveau["identite"] = ident
        if "langues" in d:
            codes = [c.lower() for c in _textes(d.get("langues"))]
            if bad := [c for c in codes if not re.fullmatch(r"[a-z]{2}", c)]:
                return {
                    "ok": False,
                    "erreurs": [f"code de langue à deux lettres : {', '.join(bad)}"],
                }
            nouveau["langues_parlees"] = list(dict.fromkeys(codes))
        return {"ok": True, "bak": self._ecrire_profil(nouveau)}

    def enregistrer_exclusions(self, d: dict[str, Any]) -> dict[str, Any]:
        """Saves the contracts and countries the collection leaves out (sources_config.json)."""
        from jobhunter import search_settings as rs

        f = rs._fichier_sources()
        try:
            conf = json.loads(f.read_text(encoding="utf-8"))
        except FileNotFoundError:
            conf = {}
        except (OSError, ValueError) as e:
            return {"ok": False, "erreurs": [f"sources_config.json illisible : {e}"]}
        for cle in ("contrats_exclus", "pays_exclus"):
            if cle in d:
                conf[cle] = list(dict.fromkeys(_textes(d.get(cle))))
        _ecrire_json(f, conf)
        return {"ok": True}

    # Statuses from emails: read an export or Gmail (read-only), suggest, apply one by one.
    def lire_courriels(self, source: str) -> dict[str, Any]:
        """Reads the emails and returns the status suggestions; nothing is written here."""
        from jobhunter import root
        from jobhunter.mail import reading, statuses
        from jobhunter.storage import applications

        if source == "gmail":
            cles = root.dossier_cles()
            if not (cles / reading.CLIENT).exists():
                # Gmail is not linked yet: say what to do, not a FileNotFoundError.
                return {
                    "ok": False,
                    "erreur": (
                        f"Gmail n'est pas encore relié. Crée un client OAuth « application de "
                        f"bureau » (API Gmail activée) dans ta console Google Cloud, enregistre "
                        f"son fichier sous {cles / reading.CLIENT}, puis installe la "
                        f'bibliothèque : pip install "jobhunter[gmail]". En attendant, un '
                        f"export .mbox (Google Takeout) ou un dossier .eml marche sans rien."
                    ),
                }
            lot: Callable[[], Any] = lambda: reading.depuis_gmail(cles)  # noqa: E731
        elif source in ("mbox", "eml"):
            if self._fenetre is None:
                return {"ok": False, "erreur": "il faut l'application pour choisir un fichier"}
            import webview

            if source == "mbox":
                choix = self._fenetre.create_file_dialog(
                    webview.FileDialog.OPEN,
                    file_types=("Courriels (*.mbox)", "Tous les fichiers (*.*)"),
                )
            else:
                choix = self._fenetre.create_file_dialog(webview.FileDialog.FOLDER)
            if not choix:
                return {"ok": False, "annule": True}
            chemin = Path(choix[0])
            lot = (
                (lambda: reading.depuis_mbox(chemin))
                if source == "mbox"
                else (lambda: reading.depuis_eml(chemin))
            )
        else:
            return {"ok": False, "erreur": f"source inconnue : {source}"}
        try:
            tous = list(lot())
            self._propositions = statuses.propositions(tous, applications.charger())
        except ImportError:
            return {
                "ok": False,
                "erreur": 'Lecture Gmail : installe d\'abord pip install "jobhunter[gmail]".',
            }
        except Exception as e:  # noqa: BLE001 — shown to the user, never swallowed
            return {"ok": False, "erreur": f"{type(e).__name__}: {e}"}
        champs = ("oid", "actuel", "propose", "raison", "de", "sujet", "le")
        return {
            "ok": True,
            "lus": len(tous),
            "propositions": [
                {k: str(getattr(x, k, "")) for k in champs} for x in self._propositions
            ],
        }

    def appliquer_proposition(self, i: int) -> dict[str, Any]:
        """Applies one suggestion if it still moves the application forward."""
        from jobhunter.programs import mail_statuses
        from jobhunter.storage import applications

        if not 0 <= int(i) < len(self._propositions):
            return {"ok": False, "erreur": "proposition inconnue"}
        try:
            ecrit = mail_statuses.appliquer(self._propositions[int(i)], attente=3)
        except applications.VerrouIndisponible:
            return {"ok": False, "erreur": "Suivi occupé : réessaie dans un instant."}
        if not ecrit:
            return {"ok": False, "erreur": "Le suivi a changé entre-temps : rien écrit."}
        return {"ok": True}

    # Actions that write: a status, or a program started by a button.
    def _ecrire_suivi(
        self, changements: dict[str, Callable[[dict[str, Any]], dict[str, Any]]]
    ) -> dict[str, Any]:
        """Applies one change per application in ONE locked write; the gesture can be undone.

        Each change receives the entry as re-read on disk (a note or a follow-up
        written meanwhile survives) and returns the new one; empty erases it.
        """
        from jobhunter.storage import applications

        geste: list[tuple[str, dict[str, Any]]] = []

        def _f(s: dict[str, Any]) -> None:
            geste.clear()
            for oid, changer in changements.items():
                avant = dict(s.get(oid) or {})
                apres = changer(dict(avant))
                if apres:
                    s[oid] = apres
                else:
                    s.pop(oid, None)
                geste.append((oid, avant))

        try:
            applications.modifier(_f, attente=4)
        except applications.VerrouIndisponible:
            return {
                "ok": False,
                "erreur": "Un autre programme écrit le suivi : réessaie dans un instant.",
            }
        self._annuler.append(list(geste))
        del self._annuler[:-50]
        return {"ok": True, "n": len(geste)}

    def _connue(self, ident: str) -> bool:
        return ident in self._suivi() or any(_oid(o) == ident for o in self._file())

    def _garder_annonces(self, idents: list[str], statut: str) -> None:
        """Keeps the posting's copy of an offer applied to (postings), in a thread."""
        from jobhunter import postings

        if statut not in postings.ENVOYEES:
            return
        offres = [o for o in self._file() if _oid(o) in idents]

        def garder() -> None:
            for o in offres:
                try:
                    postings.archiver(o)
                except Exception:  # noqa: BLE001,S110 — the morning pipeline tries again
                    pass

        threading.Thread(target=garder, daemon=True).start()

    def marquer(self, ident: str | list[str], statut: str) -> dict[str, Any]:
        """Sets the status of one or several applications; "" clears it (undoable).

        The date is today's when the status changes; the note and the rest stay.
        """
        idents = [ident] if isinstance(ident, str) else [str(x) for x in ident or []]
        if statut and statut not in STATUTS:
            return {"ok": False, "erreur": f"statut inconnu : {statut}"}
        if not idents or not all(self._connue(i) for i in idents):
            return {"ok": False, "erreur": "offre introuvable"}
        jour = date.today().isoformat()

        def changer(rec: dict[str, Any]) -> dict[str, Any]:
            if not statut:
                return {}
            if rec.get("s") != statut:
                rec["d"] = jour
            rec["s"] = statut
            return rec

        r = self._ecrire_suivi(dict.fromkeys(idents, changer))
        if r["ok"]:
            self._garder_annonces(idents, statut)
        return r

    def suivre(self, ident: str, d: dict[str, Any]) -> dict[str, Any]:
        """The tracking fields of the offer sheet: status, note, date (the desktop's card)."""
        if not self._connue(ident):
            return {"ok": False, "erreur": "offre introuvable"}
        statut = str(d.get("statut") or "")
        if statut and statut not in STATUTS:
            return {"ok": False, "erreur": f"statut inconnu : {statut}"}
        le = str(d.get("date") or "").strip()
        if le and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", le):
            return {"ok": False, "erreur": "date au format AAAA-MM-JJ"}

        def changer(rec: dict[str, Any]) -> dict[str, Any]:
            for cle, val in (("s", statut), ("n", str(d.get("note") or "").strip()), ("d", le)):
                if val:
                    rec[cle] = val
                else:
                    rec.pop(cle, None)
            return rec if any(rec.get(k) for k in ("s", "n", "d")) else {}

        r = self._ecrire_suivi({ident: changer})
        if r["ok"]:
            self._garder_annonces([ident], statut)
        return r

    def declarer_envoi(self, ident: str) -> dict[str, Any]:
        """Records an application the user says they sent ("déclaré", ADR 0009).

        Nothing is sent here: the page asks "As-tu envoyé cette candidature ?" first.
        """
        from jobhunter.storage import applications

        if not self._connue(ident):
            return {"ok": False, "erreur": "offre introuvable"}
        avant = dict(self._suivi().get(ident) or {})
        try:
            applications.declarer_envoi(ident, "déclaré", attente=4)
        except applications.VerrouIndisponible:
            return {
                "ok": False,
                "erreur": "Un autre programme écrit le suivi : réessaie dans un instant.",
            }
        self._annuler.append([(ident, avant)])
        self._garder_annonces([ident], "postulé")
        return {"ok": True}

    def annuler(self) -> dict[str, Any]:
        """Puts the tracking of the last gesture back as it was (the desktop's Ctrl+Z)."""
        from jobhunter.storage import applications

        if not self._annuler:
            return {"ok": False, "erreur": "Rien à annuler."}
        geste = self._annuler.pop()

        def _f(s: dict[str, Any]) -> None:
            for oid, avant in geste:
                if avant:
                    s[oid] = avant
                else:
                    s.pop(oid, None)

        try:
            applications.modifier(_f, attente=4)
        except applications.VerrouIndisponible:
            self._annuler.append(geste)
            return {"ok": False, "erreur": "Suivi occupé : réessaie dans un instant."}
        return {"ok": True, "n": len(geste)}

    def motifs(self) -> list[str]:
        """The frequent reasons to set offers aside (exclusions.MOTIFS)."""
        from jobhunter.programs import exclusions

        return list(exclusions.MOTIFS)

    def ecarter(self, idents: list[str], motif: str) -> dict[str, Any]:
        """Sets offers aside WITH a reason: out of the queue, and the scan will not re-add them.

        The refusal is recorded before the offers leave: one exclusion too many is
        better than an offer gone without its reason.
        """
        from jobhunter.programs import exclusions
        from jobhunter.storage import queue as queue_io

        motif = str(motif or "").strip()
        oids = {str(x) for x in idents or []}
        if not motif or not oids:
            return {"ok": False, "erreur": "il faut des offres et un motif"}
        try:
            with queue_io.transaction(attente=20) as file:
                n_exc = exclusions.ajouter([o for o in file if queue_io.oid(o) in oids], motif)
                avant = len(file)
                file[:] = [o for o in file if queue_io.oid(o) not in oids]
                retirees = avant - len(file)
        except queue_io.VerrouIndisponible:
            return {
                "ok": False,
                "erreur": "Un autre programme modifie la file : réessaie dans un instant.",
            }
        return {"ok": True, "retirees": retirees, "exclusions": n_exc}

    def supprimer(self, idents: list[str]) -> dict[str, Any]:
        """Removes offers from the queue after a dated copy in _corbeille/ (nothing lost)."""
        from jobhunter import root
        from jobhunter.storage import queue as queue_io

        oids = {str(x) for x in idents or []}
        if not oids:
            return {"ok": False, "erreur": "aucune offre"}
        corbeille = root.scripts() / "_corbeille"
        try:
            with queue_io.transaction(attente=20) as file:
                partantes = [o for o in file if queue_io.oid(o) in oids]
                # THE COPY FIRST: if it fails, the block raises and nothing is written.
                corbeille.mkdir(parents=True, exist_ok=True)
                f = corbeille / f"supprimees_{datetime.now():%Y-%m-%d_%H%M%S}.json"
                _ecrire_json(f, partantes)
                file[:] = [o for o in file if queue_io.oid(o) not in oids]
        except queue_io.VerrouIndisponible:
            return {
                "ok": False,
                "erreur": "Un autre programme modifie la file : réessaie dans un instant.",
            }
        except OSError as e:
            return {"ok": False, "erreur": f"copie impossible, rien supprimé : {e}"}
        return {"ok": True, "n": len(partantes), "copie": f.name}

    def ajouter_offre(self, url: str) -> dict[str, Any]:
        """Analyses a pasted offer link (add_offer) and adds it to the queue."""
        url = str(url or "").strip()
        if not re.match(r"^https?://", url):
            return {"ok": False, "erreur": "colle un lien http(s) d'offre"}
        if self._tache and self._tache.code is None:
            return {"ok": False, "erreur": f"« {self._tache.libelle} » tourne encore."}
        return self._demarrer("ajout", TACHES["ajout"][0], [*TACHES["ajout"][1], url])

    def chercher_web(self, ident: str) -> bool:
        """Searches the company and the job on the web (the desktop's right-click entry)."""
        from urllib.parse import quote

        entreprise, _, poste = str(ident).partition("|")
        return webbrowser.open(
            f"https://www.google.com/search?q={quote(f'{entreprise} {poste} recrutement')}"
        )

    def compte(self, ident: str) -> dict[str, Any]:
        """Marks or unmarks "I have an account on this site" (comptes_sites.json, no password)."""
        from urllib.parse import urlparse

        from jobhunter import profile, root

        o = next((x for x in self._file() if _oid(x) == ident), None)
        url = str((o or {}).get("url") or "")
        if not url.startswith("http"):
            return {"ok": False, "erreur": "pas de lien, donc pas de site"}
        hote = urlparse(url).netloc.replace("www.", "").lower()
        f = root.dans(root.scripts(), "comptes_sites.json")
        try:
            comptes = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
        except (OSError, ValueError) as e:
            return {"ok": False, "erreur": f"comptes_sites.json illisible : {e}"}
        lies = [h for h in comptes if hote == h or hote.endswith("." + h) or h.endswith("." + hote)]
        if lies:
            for h in lies:
                comptes.pop(h, None)
        else:
            email = str((profile.charger().get("identite") or {}).get("email") or "")
            comptes[hote] = {
                "site": (o or {}).get("entreprise", ""),
                "login": url,
                "email": email,
                "src": "manuel",
            }
        _ecrire_json(f, comptes)
        return {"ok": True, "compte": not lies, "site": hote}

    def lancer(self, cle: str, ident: str = "") -> dict[str, Any]:
        """Starts one of TACHES, one at a time. `ident`: the offer, for "documents"."""
        if self._tache and self._tache.code is None:
            return {"ok": False, "erreur": f"« {self._tache.libelle} » tourne encore."}
        if cle not in TACHES:
            return {"ok": False, "erreur": f"tâche inconnue : {cle}"}
        libelle, args = TACHES[cle][0], list(TACHES[cle][1])
        if cle == "ajout":
            return {"ok": False, "erreur": "passe par ajouter_offre"}
        if cle == "description":
            if not any(_oid(o) == ident for o in self._file()):
                return {"ok": False, "erreur": "offre introuvable"}
            args.append(ident)
            libelle = f"{libelle} · {ident.partition('|')[0]}"
        elif cle == "documents":
            url = next((str(o.get("url") or "") for o in self._file() if _oid(o) == ident), "")
            if not re.match(r"^https?://", url):
                return {"ok": False, "erreur": "cette offre n'a pas de lien"}
            args.append(url)
            libelle = f"{libelle} · {ident.partition('|')[0]}"
        return self._demarrer(cle, libelle, args)

    def _demarrer(self, cle: str, libelle: str, args: list[str]) -> dict[str, Any]:
        from jobhunter import root

        try:
            self._tache = Tache(cle, libelle, [_python(), "-m", *args], root.scripts())
        except OSError as e:
            return {"ok": False, "erreur": str(e)}
        return {"ok": True}

    def outils(self) -> list[dict[str, Any]]:
        """The Outils menu, the desktop's own list (tools_catalog), by group."""
        from jobhunter import tools_catalog as cat

        def genre(quoi: list[str] | str) -> str:
            args = cat.programme(quoi)
            return "action" if args is None else "console" if cat.interactif(args) else "tache"

        return [
            {
                "groupe": groupe,
                "outils": [
                    {"libelle": lib, "genre": genre(q), "action": q if isinstance(q, str) else ""}
                    for lib, q in items
                ],
            }
            for groupe, items in cat.OUTILS
        ]

    def lancer_outil(self, libelle: str) -> dict[str, Any]:
        """Runs one tool of the Outils menu, found by its label (never a command sent by the page).

        A program that reads the keyboard opens in a console of its own, as on the
        desktop: its output is not followed here. An action is the page's to open.
        """
        from jobhunter import root
        from jobhunter import tools_catalog as cat

        quoi = next((q for _g, items in cat.OUTILS for lib, q in items if lib == libelle), None)
        if quoi is None:
            return {"ok": False, "erreur": f"outil inconnu : {libelle}"}
        args = cat.programme(quoi)
        if args is None:
            return {"ok": True, "action": quoi}
        if cat.interactif(args):
            try:
                subprocess.Popen(  # nosec B603 : a program of tools_catalog
                    [_python(), "-m", *args],
                    cwd=str(root.scripts()),
                    creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0x10),
                )
            except OSError as e:
                return {"ok": False, "erreur": str(e)}
            return {"ok": True, "console": True}
        if self._tache and self._tache.code is None:
            return {"ok": False, "erreur": f"« {self._tache.libelle} » tourne encore."}
        return self._demarrer("outil", libelle, args)

    def tache(self) -> dict[str, Any] | None:
        """The running (or last) task for the task panel; None when none was started."""
        return self._tache.etat() if self._tache else None

    def arreter(self) -> bool:
        """Stops the running task."""
        if self._tache and self._tache.code is None:
            self._tache.proc.terminate()
            return True
        return False

    def mise_a_jour(self) -> dict[str, Any]:
        """Installed engine version and the latest published one (a check only).

        `store`: the Microsoft Store installed it and installs its updates.
        """
        from jobhunter import frozen

        installee = _version_installee()
        derniere = _derniere_version()
        nouvelle = installee != "?" and _plus_recente(derniere, installee)
        store = frozen.paquet_msix() and frozen.msix_du_store()
        signee = nouvelle and not store and _signee(derniere)
        attente = ""
        if nouvelle and not store and not signee:
            # The latest waits for its author's signature (up to an hour): an earlier
            # signed one newer than the installed one is offered meanwhile.
            from jobhunter.programs import update

            attente = derniere
            try:
                proposee = update.derniere_signee(6)
            except Exception:  # noqa: BLE001 — offline, rate limit: nothing offered
                proposee = ""
            if _plus_recente(proposee, installee):
                derniere, signee = proposee, True
            else:
                nouvelle = False
        return {
            "installee": installee,
            "derniere": derniere,
            "nouvelle": nouvelle,
            "signee": signee,
            "attente": attente,
            "store": store,
        }

    def annonce_maj(self) -> dict[str, Any] | None:
        """A newer signed version, for the button of the title bar; None otherwise."""
        v = self.mise_a_jour()
        return v if v["signee"] else None

    def effacer_donnees(self) -> dict[str, Any]:
        """Sends the installed application's data to the Recycle Bin, then closes it.

        Uninstalling never touches Documents/JobHunter (the installer asks, the Store
        cannot): this is how to start again from nothing (the user, 2026-10-29). The
        daily collection is unscheduled first, else it would make the folder again.
        """
        dossier = _dossier_effacable()
        if dossier is None:
            return {"ok": False, "message": "Réservé à l'application installée."}
        from jobhunter import scheduling
        from jobhunter.programs import update

        if not update.file_libre(garder=False):
            return {"ok": False, "message": "Une tâche tourne : réessaie quand elle est finie."}
        if scheduling.disponible() and scheduling.planifiee():
            scheduling.supprimer()
        env = dict(os.environ, JH_PID=str(os.getpid()), JH_DOSSIER=str(dossier))
        drapeaux = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(
            subprocess, "DETACHED_PROCESS", 0
        )
        subprocess.Popen(  # nosec B603 B607 : fixed script, values by environment
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", _CORBEILLE],
            env=env,
            creationflags=drapeaux,
        )
        if self._fenetre is not None:
            self._fenetre.destroy()
        return {"ok": True, "dossier": str(dossier)}

    # Actions that only open things.
    def ouvrir_profil(self) -> bool:
        """Opens profile.json in its editor (no password lives there)."""
        from jobhunter import profile

        p = Path(profile.FICHIER)
        if not p.is_file():
            return False
        os.startfile(p)  # type: ignore[attr-defined,unused-ignore]  # Windows only
        return True

    # Settings: language, daily collection, profiles (the desktop's Paramètres page).
    def parametres(self) -> dict[str, Any]:
        """Interface language, daily collection state, profiles."""
        from jobhunter import profiles, scheduling

        f = _fichier_reglages()
        try:
            langue = (
                str(json.loads(f.read_text(encoding="utf-8")).get("langue") or "fr") if f else "fr"
            )
        except (OSError, ValueError, AttributeError):
            langue = "fr"
        try:
            liste = profiles.liste()
            actif = profiles.actif()
        except Exception:  # noqa: BLE001 — no profiles folder: the main one only
            liste, actif = [], ""
        return {
            "langue": langue,
            "langues": LANGUES,
            "planif": {
                "disponible": scheduling.disponible(),
                "planifiee": scheduling.disponible() and scheduling.planifiee(),
            },
            "profils": [{"slug": x.slug, "nom": x.nom or "Principal"} for x in liste],
            "actif": actif,
            "titulaire": self._titulaire(),
        }

    def _titulaire(self) -> str:
        """The open profile's "Prénom Nom" (the menu's badge), "" when unknown."""
        try:
            ident = self._profil_brut().get("identite") or {}
        except (OSError, ValueError, AttributeError):
            return ""
        return " ".join(str(ident.get(k) or "").strip() for k in ("prenom", "nom")).strip()

    def choisir_langue(self, code: str) -> dict[str, Any]:
        """The interface language, both windows' (same file and key as the desktop).

        Only the interface: letters, messages and the profile keep their language.
        """
        if code not in LANGUES:
            return {"ok": False, "erreur": f"langue inconnue : {code}"}
        f = _fichier_reglages()
        if f is None:
            return {"ok": False, "erreur": "dossier de données introuvable"}
        try:
            tout = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
        except (OSError, ValueError):
            return {"ok": False, "erreur": f"{f.name} illisible : rien écrit"}
        if not isinstance(tout, dict):
            tout = {}
        tout["langue"] = code
        f.parent.mkdir(parents=True, exist_ok=True)
        _ecrire_json(f, tout)
        return {"ok": True}

    def planifier(self, heure: str = "") -> dict[str, Any]:
        """Creates the daily collection at `heure` (HH:MM), or removes it when heure is ""."""
        from jobhunter import scheduling

        if not scheduling.disponible():
            return {"ok": False, "erreur": "Planification disponible sous Windows seulement."}
        heure = str(heure or "").strip()
        if heure and not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", heure):
            return {"ok": False, "erreur": "heure au format 08:00"}
        ok, msg = scheduling.creer(heure) if heure else scheduling.supprimer()
        return {"ok": ok, "message": msg, "erreur": "" if ok else msg}

    def _relancer(self) -> None:
        """Starts the web interface again on the active profile, then closes this window."""
        from jobhunter import frozen, profiles

        principale = profiles.principale()
        env = {k: v for k, v in os.environ.items() if k != profiles.ENV_PRINCIPALE}
        env["JOBHUNTER_RACINE"] = str(principale)
        # As the desktop's _relancer: the compiled app, else the folder's launcher.
        if frozen.est_gele():
            cmd = [sys.executable]
        elif (principale / "JobHunter.pyw").exists():
            cmd = [sys.executable, str(principale / "JobHunter.pyw")]
        else:
            cmd = [sys.executable, "-m", "jobhunter.launch"]
        subprocess.Popen(cmd, cwd=str(principale), env=env)  # nosec B603 : our own program
        if self._fenetre is not None:
            self._fenetre.destroy()

    def changer_profil(self, slug: str) -> dict[str, Any]:
        """Opens another profile: the window restarts on its data (paths are fixed at start)."""
        from jobhunter import profiles

        if slug not in {x.slug for x in profiles.liste()}:
            return {"ok": False, "erreur": "profil inconnu"}
        if self._tache and self._tache.code is None:
            return {
                "ok": False,
                "erreur": "Une tâche tourne sur ce profil : attends qu'elle finisse.",
            }
        profiles.activer(slug)
        self._relancer()
        return {"ok": True}

    def renommer_profil(self, nom: str) -> dict[str, Any]:
        """Renames the open profile (its displayed name only; its folder never changes)."""
        from jobhunter import profiles

        nom = str(nom or "").strip()
        if not nom:
            return {"ok": False, "erreur": "nom vide"}
        profiles.renommer(profiles.actif(), nom)
        return {"ok": True}

    def archiver_profil(self) -> dict[str, Any]:
        """Moves the open profile to the archives (never deleted), then opens the main one."""
        from jobhunter import profiles

        s = profiles.actif()
        if not s:
            return {"ok": False, "erreur": "Le profil principal ne s'archive pas."}
        if self._tache and self._tache.code is None:
            return {"ok": False, "erreur": "Une tâche tourne : attends qu'elle finisse."}
        try:
            profiles.archiver(s)  # the main profile becomes the active one
        except (ValueError, RuntimeError) as e:
            return {"ok": False, "erreur": str(e)}
        self._relancer()
        return {"ok": True}

    def nouveau_profil(self, nom: str) -> dict[str, Any]:
        """A new profile from a CV: its folder, then the guided first launch in it.

        The questions are answered in a window of their own (jobhunter.welcome);
        `profil_cree` checks the result.
        """
        from jobhunter import profiles

        nom = str(nom or "").strip()
        if not nom:
            return {"ok": False, "erreur": "donne un nom au profil"}
        if self._fenetre is None:
            return {"ok": False, "erreur": "il faut l'application pour choisir un CV"}
        import webview

        choix = self._fenetre.create_file_dialog(
            webview.FileDialog.OPEN, file_types=("CV (*.docx;*.pdf)", "Tous les fichiers (*.*)")
        )
        if not choix:
            return {"ok": False, "annule": True}
        try:
            racine = profiles.creer(nom)
        except FileExistsError:
            return {"ok": False, "erreur": "Un profil de ce nom existe déjà."}
        env = {
            **os.environ,
            "JOBHUNTER_RACINE": str(racine),
            profiles.ENV_PRINCIPALE: str(profiles.principale()),
        }
        subprocess.Popen(  # nosec B603 : our own program, arguments built here
            [sys.executable, "-m", "jobhunter.welcome", str(choix[0])],
            cwd=str(racine),
            env=env,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000),
        )
        return {"ok": True, "slug": racine.name}

    def profil_cree(self, slug: str, ouvrir: bool = False) -> dict[str, Any]:
        """After the console: the profile exists if its questions were answered.

        An unfinished one is moved to the archives (never deleted).
        """
        from jobhunter import profiles

        racine = profiles.racine_de(slug)
        if not (racine / "profile" / "profile.json").exists():
            if racine.exists():
                try:
                    profiles.archiver(slug)
                except (ValueError, RuntimeError):
                    pass  # left as it is: never deleted
            return {"ok": False, "erreur": "Le profil n'a pas été créé (questions non terminées)."}
        profiles.nommer(racine)
        if ouvrir:
            profiles.activer(slug)
            self._relancer()
        return {"ok": True}

    def ouvrir_dossier(self) -> bool:
        """Opens the data folder in the Explorer (the desktop's "Ouvrir le dossier")."""
        from jobhunter import root

        os.startfile(root.racine())  # type: ignore[attr-defined,unused-ignore]  # nosec B606
        return True

    def ouvrir(self, url: str) -> bool:
        """Opens an offer in the default browser; only web links."""
        if not re.match(r"^https?://", url or ""):
            return False
        return webbrowser.open(url)

    def ouvrir_fichier(self, chemin: str) -> bool:
        """Opens a CV or a letter with its program; only files under CV/ or Letters/."""
        p = _document_permis(chemin)
        if p is None:
            return False
        os.startfile(p)  # type: ignore[attr-defined,unused-ignore]  # Windows only
        return True

    # A CV or a letter seen and edited in the window (the user, 2026-10-27): its PDF to
    # look at, the text of its .docx to change; the PDF is made again after a change.
    def document(self, chemin: str) -> dict[str, Any]:
        """The PDF (base64) and the paragraphs of the .docx next to `chemin`.

        A base CV given as a .docx has no PDF yet: it is made here (LibreOffice), else
        the page shows the paragraphs. A PDF alone is shown, not edited. Before 3.58
        both showed nothing (the user, 2026-10-28: « si le CV de base est docx, je ne
        peux pas le voir dans Profil »).
        """
        import base64

        from jobhunter.documents import editing, rendering

        p = _document_permis(chemin)
        docx = p.with_suffix(".docx") if p else None
        if p is not None and docx is not None and not docx.is_file() and p.suffix.lower() == ".pdf":
            return {
                "ok": True,
                "nom": p.stem,
                "docx": "",
                "paragraphes": [],
                "modifiables": [],
                "pdf": base64.b64encode(p.read_bytes()).decode("ascii"),
            }
        if docx is None or not docx.is_file():
            return {"ok": False, "erreur": "document introuvable (seul un .docx se modifie)"}
        pdf = docx.with_suffix(".pdf")
        if not pdf.is_file():
            rendering.to_pdf(docx)
        try:
            return {
                "ok": True,
                "nom": docx.stem,
                "docx": str(docx),
                "paragraphes": editing.lire(docx),
                "modifiables": editing.modifiables(docx),
                "pdf": base64.b64encode(pdf.read_bytes()).decode("ascii") if pdf.is_file() else "",
            }
        except Exception as e:  # noqa: BLE001 — a damaged file is said, not hidden
            return {"ok": False, "erreur": f"{type(e).__name__}: {e}"}

    def enregistrer_document(
        self, chemin: str, avant: list[str], apres: list[str]
    ) -> dict[str, Any]:
        """Writes the changed paragraphs into the .docx (first copy kept), remakes the PDF."""
        import shutil

        from jobhunter.documents import editing, rendering

        p = _document_permis(chemin)
        docx = p.with_suffix(".docx") if p else None
        if docx is None or not docx.is_file():
            return {"ok": False, "erreur": "document introuvable"}
        if not isinstance(avant, list) or not isinstance(apres, list) or len(avant) != len(apres):
            return {"ok": False, "erreur": "texte reçu incomplet"}
        origine = docx.with_name(docx.name + ".orig")
        if not origine.exists():
            shutil.copy2(docx, origine)  # the generated version, kept once
        try:
            faits, refus = editing.modifier(docx, [str(x) for x in avant], [str(x) for x in apres])
        except PermissionError:
            return {"ok": False, "erreur": "le fichier est ouvert ailleurs (Word ?) : ferme-le"}
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "erreur": f"{type(e).__name__}: {e}"}
        pdf = rendering.to_pdf(docx) if faits else None
        return {"ok": True, "modifies": faits, "refuses": refus, "pdf": pdf is not None}

    def fenetre(self, action: str) -> None:
        """The title bar buttons of the frameless window: reduire, agrandir, fermer."""
        f = self._fenetre
        if f is None:
            return
        if action == "reduire":
            f.minimize()
        elif action == "agrandir":
            if self._basculer:
                self._basculer()
        elif action == "fermer":
            self._fermer_seance()  # a guided application running: stopped, Chrome closed
            f.destroy()


def _dossier_relances() -> Path:
    from jobhunter import root

    return root.dans(root.dossier("Lettres"), "Relances")


def _dossiers_documents() -> dict[str, Path]:
    """Where the CVs and letters made per offer are: CV/By_offer, Letters/By_offer."""
    from jobhunter import root

    return {
        "CV": root.dans(root.racine() / "CV", "Par_offre"),
        "Lettre": root.dans(root.dossier("Lettres"), "Par_offre"),
    }


def _document_permis(chemin: str) -> Path | None:
    """`chemin` if it is a document under CV/ or Letters/; never a program dropped there."""
    from jobhunter import root

    p = _chemin_local(chemin)
    if p is None or not p.is_file() or p.suffix.lower() not in DOCUMENTS:
        return None
    permis = (root.racine() / "CV", root.dossier("Lettres"))
    if not any(p.is_relative_to(d.resolve()) for d in permis):
        return None
    return p


def _chemin_local(chemin: str) -> Path | None:
    """A local path from a path or a file:// URL, resolved; None for anything else."""
    from urllib.parse import unquote, urlparse

    t = (chemin or "").strip()
    if t.lower().startswith("file:"):
        t = unquote(urlparse(t).path)
        if re.match(r"^/[A-Za-z]:", t):
            t = t[1:]
    elif re.match(r"^[a-z][a-z0-9+.-]*://", t, re.I):
        return None
    if not t:
        return None
    try:
        return Path(t).resolve()
    except OSError:
        return None
