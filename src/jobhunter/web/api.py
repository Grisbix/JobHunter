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
from pathlib import Path
from typing import Any

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
                "lieu": o.get("localisation") or "",
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
FILTRES_STATUT = ("à traiter", "postulées", "toutes")
PAR_PAGE = 40


def _date_offre(o: Mapping[str, Any]) -> str:
    """The most telling date of an offer: its publication, else when it was seen, else its scan."""
    for champ in ("date_publication", "vu_le"):
        d = _date(str(o.get(champ) or "")[:10])
        if d:
            return d.isoformat()
    m = _RX_SCAN.match(str(o.get("statut") or ""))
    return m.group(1) if m else ""


def _ligne(o: Mapping[str, Any], suivi: Mapping[str, Any]) -> dict[str, Any]:
    k = _oid(o)  # type: ignore[arg-type]
    return {
        "id": k,
        "poste": o.get("poste") or "",
        "entreprise": o.get("entreprise") or "",
        "lieu": o.get("localisation") or "",
        "fit": _fit(o),  # type: ignore[arg-type]
        "zone": o.get("zone") or "",
        "contrat": o.get("contrat") or "",
        "date": _date_offre(o),
        "suivi": (suivi.get(k) or {}).get("s") or "",
        "url": o.get("url") or "",
    }


def offres(
    offres: Sequence[Any],
    suivi: Mapping[str, Any],
    texte: str = "",
    zone: str = "",
    fit_min: float = 0,
    statut: str = "à traiter",
    tri: str = "fit",
    page: int = 0,
) -> dict[str, Any]:
    """One page of the offers screen, filtered and sorted, with the filter choices."""
    mots = [m for m in (texte or "").lower().split() if m]
    gardees = []
    for o in offres:
        st = str(o.get("statut") or "")
        k = _oid(o)
        if statut == "à traiter" and (not _RX_SCAN.match(st) or k in suivi):
            continue
        if statut == "postulées" and (suivi.get(k) or {}).get("s") not in EN_ATTENTE:
            continue
        if zone and o.get("zone") != zone:
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
    }
    gardees.sort(key=cles.get(tri, cles["fit"]), reverse=(tri == "date"))
    page = max(0, int(page))
    debut = page * PAR_PAGE
    return {
        "total": len(gardees),
        "page": page,
        "pages": max(1, -(-len(gardees) // PAR_PAGE)),
        "lignes": [_ligne(o, suivi) for o in gardees[debut : debut + PAR_PAGE]],
        "zones": sorted({str(o.get("zone")) for o in offres if o.get("zone")}),
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
REGLAGES: dict[str, Any] = {"fond": "acrylique", "verre": 50, "teinte": "terre", "police": "segoe"}


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
    "brouillons": ("Brouillons de relance", ["jobhunter.programs.follow_ups", "--brouillons"]),
    "regenerer_cv": ("Refaire les CV", ["jobhunter.programs.regenerate_docs", "--cv"]),
    "disponibilite": (
        "Contrôle des offres fermées",
        ["jobhunter.programs.availability_audit", "--supprime"],
    ),
    "documents_top": (
        "CV et lettres des 30 meilleures offres",
        ["jobhunter.programs.generate_docs", "--top", "30"],
    ),
    # + the offer's URL, which generate_docs matches by substring
    "documents": ("CV et lettre de l'offre", ["jobhunter.programs.generate_docs", "--url"]),
}

# Statuses the page may set on an application.
STATUTS = (*COLONNES, *ECARTEES)


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


class Api:
    """Methods the page calls through `window.pywebview.api`.

    Nothing here writes to the queue, the applications or the profile; only the
    display settings are saved.
    """

    # Set by __main__ once the window exists; private, so pywebview does not expose it.
    _fenetre: Any = None
    _basculer: Any = None  # full screen <-> rounded window
    _fond: Any = None  # applies a backdrop by name, see FONDS
    _tache: Tache | None = None

    def __init__(self) -> None:
        """An empty cache: each data file is read on first use."""
        self._cache: dict[str, tuple[float, Any]] = {}

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
        return tableau(self._file(), self._suivi())

    def offres(self, filtres: dict[str, Any] | None = None) -> dict[str, Any]:
        """One page of the offers screen; filtres: texte, zone, fit_min, statut, tri, page."""
        f = filtres or {}
        return offres(
            self._file(),
            self._suivi(),
            texte=str(f.get("texte") or ""),
            zone=str(f.get("zone") or ""),
            fit_min=float(f.get("fit_min") or 0),
            statut=str(f.get("statut") or "à traiter"),
            tri=str(f.get("tri") or "fit"),
            page=int(f.get("page") or 0),
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
        """CVs and letters made per offer, most recent first, filtered by text."""
        from jobhunter import root

        f = filtres or {}
        mots = [m for m in str(f.get("texte") or "").lower().split() if m]
        fichiers: list[dict[str, Any]] = []
        for genre, dossier in (
            ("CV", root.dans(root.racine() / "CV", "Par_offre")),
            ("Lettre", root.dans(root.dossier("Lettres"), "Par_offre")),
        ):
            if not dossier.is_dir():
                continue
            for p in dossier.iterdir():
                if p.suffix.lower() not in (".pdf", ".docx"):
                    continue
                if mots and not all(m in p.stem.lower() for m in mots):
                    continue
                st = p.stat()
                fichiers.append(
                    {
                        "genre": genre,
                        "nom": p.stem.replace("_", " "),
                        "chemin": str(p),
                        "format": p.suffix[1:].upper(),
                        "date": datetime.fromtimestamp(st.st_mtime).date().isoformat(),
                        "ko": round(st.st_size / 1024),
                    }
                )
        fichiers.sort(key=lambda x: x["date"], reverse=True)
        page = max(0, int(f.get("page") or 0))
        return {
            "total": len(fichiers),
            "page": page,
            "pages": max(1, -(-len(fichiers) // PAR_PAGE)),
            "fichiers": fichiers[page * PAR_PAGE : (page + 1) * PAR_PAGE],
        }

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
        from importlib.metadata import PackageNotFoundError, version

        from jobhunter import root

        donnees = root.scripts()
        try:
            v = version("jobhunter")
        except PackageNotFoundError:
            v = "?"
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
            "collecte": collecte,
            "sauvegardes": jours,
            "tailles": tailles,
            "offres": len(self._file()),
            "candidatures": sum(1 for e in self._suivi().values() if e.get("s")),
        }

    def reglages(self) -> dict[str, Any]:
        """The display settings: window backdrop and glass strength."""
        return lire_reglages()

    def regler(self, valeurs: dict[str, Any]) -> dict[str, Any]:
        """Saves the display settings; a new backdrop applies at once."""
        r = ecrire_reglages(valeurs)
        if self._fond:
            self._fond(r["fond"])
        return r

    # Actions that write: a status, or a program started by a button.
    def marquer(self, ident: str, statut: str) -> dict[str, Any]:
        """Sets the status of one application, dated today, under the tracker's lock."""
        from jobhunter.storage import applications

        if statut not in STATUTS:
            return {"ok": False, "erreur": f"statut inconnu : {statut}"}
        if ident not in self._suivi() and not any(_oid(o) == ident for o in self._file()):
            return {"ok": False, "erreur": "offre introuvable"}

        def _f(s: dict[str, Any]) -> None:
            rec = dict(s.get(ident) or {})
            rec["s"] = statut
            rec["d"] = date.today().isoformat()
            s[ident] = rec

        try:
            applications.modifier(_f, attente=4)
        except applications.VerrouIndisponible:
            return {
                "ok": False,
                "erreur": "Un autre programme écrit le suivi : réessaie dans un instant.",
            }
        return {"ok": True}

    def lancer(self, cle: str, ident: str = "") -> dict[str, Any]:
        """Starts one of TACHES, one at a time. `ident`: the offer, for "documents"."""
        from jobhunter import root

        if self._tache and self._tache.code is None:
            return {"ok": False, "erreur": f"« {self._tache.libelle} » tourne encore."}
        if cle not in TACHES:
            return {"ok": False, "erreur": f"tâche inconnue : {cle}"}
        libelle, args = TACHES[cle][0], list(TACHES[cle][1])
        if cle == "documents":
            url = next((str(o.get("url") or "") for o in self._file() if _oid(o) == ident), "")
            if not re.match(r"^https?://", url):
                return {"ok": False, "erreur": "cette offre n'a pas de lien"}
            args.append(url)
            libelle = f"{libelle} · {ident.partition('|')[0]}"
        try:
            self._tache = Tache(cle, libelle, [sys.executable, "-m", *args], root.scripts())
        except OSError as e:
            return {"ok": False, "erreur": str(e)}
        return {"ok": True}

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
        """Installed engine version and the latest published one (a check only)."""
        from importlib.metadata import PackageNotFoundError, version

        try:
            installee = version("jobhunter")
        except PackageNotFoundError:
            installee = "?"
        return {"installee": installee, "derniere": _derniere_version()}

    # Actions that only open things.
    def ouvrir_profil(self) -> bool:
        """Opens profile.json in its editor (no password lives there)."""
        from jobhunter import profile

        p = Path(profile.FICHIER)
        if not p.is_file():
            return False
        os.startfile(p)  # type: ignore[attr-defined,unused-ignore]  # Windows only
        return True

    def ouvrir(self, url: str) -> bool:
        """Opens an offer in the default browser; only web links."""
        if not re.match(r"^https?://", url or ""):
            return False
        return webbrowser.open(url)

    def ouvrir_fichier(self, chemin: str) -> bool:
        """Opens a CV or a letter with its program; only files under CV/ or Letters/."""
        from jobhunter import root

        p = _chemin_local(chemin)
        if p is None or not p.is_file():
            return False
        permis = (root.racine() / "CV", root.dossier("Lettres"))
        if not any(p.is_relative_to(d.resolve()) for d in permis):
            return False
        os.startfile(p)  # type: ignore[attr-defined,unused-ignore]  # Windows only
        return True

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
            f.destroy()


def _dossier_relances() -> Path:
    from jobhunter import root

    return root.dans(root.dossier("Lettres"), "Relances")


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
