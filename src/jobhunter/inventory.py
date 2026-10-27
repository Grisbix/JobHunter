"""What the Companies, Access and My CVs panels show: data, without a window.

Part of jobhunter.app (step F2 of the roadmap). The three panels displayed wrong or
stale figures: companies counted by URL substring ("Bil": 546 offers), an empty ATS
column, sources removed weeks ago, 1,983 CVs listed flat. Everything they compute
lives here, in pure tested functions; the panels only display it.

- **Companies**: the feeds really collected (`sources_config.json`: ATS slugs,
  Workday feeds, other feeds) and the career sites read by the browser, each with the
  queue's offers that come from it. An offer comes from a feed when its `source` field
  is `tool:key`, the marker the collection sets: an exact count, not a cross-check.
- **Access**: the collection's sources, what they need (nothing, a key) and their
  last measured verdict (`_rendement.jsonl`, 2.4). The keys are never read: only the
  presence of the file counts.
- **My CVs**: one folder per offer (CV and letter together), with the state of the
  final documents, instead of two lists of files.
"""

import datetime
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from jobhunter import links as liens
from jobhunter.documents.checks import piece_finale

# Public page of a feed, per tool: what a click on the row opens.
URL_FLUX = {
    "greenhouse": "https://job-boards.greenhouse.io/{}",
    "lever": "https://jobs.lever.co/{}",
    "ashby": "https://jobs.ashbyhq.com/{}",
    "recruitee": "https://{}.recruitee.com",
    "smartrecruiters": "https://careers.smartrecruiters.com/{}",
    "teamtailor": "https://{}.teamtailor.com/jobs",
    "workable": "https://apply.workable.com/{}",
    "pinpoint": "https://{}.pinpointhq.com",
}

NOMS_OUTILS = {
    "greenhouse": "Greenhouse",
    "lever": "Lever",
    "ashby": "Ashby",
    "recruitee": "Recruitee",
    "smartrecruiters": "SmartRecruiters",
    "teamtailor": "Teamtailor",
    "workable": "Workable",
    "personio": "Personio",
    "breezy": "Breezy HR",
    "pinpoint": "Pinpoint",
    "workday": "Workday",
    "sfrss": "SuccessFactors",
    "talentsoft": "Talentsoft",
    "eightfold": "Eightfold",
    "phenom": "Phenom",
    "icims": "iCIMS",
    "csod": "Cornerstone",
    "oracle": "Oracle",
    "avature": "Avature",
    "sitemap": "plan du site",
    "site": "site (navigateur)",
}


@dataclass(frozen=True)
class Flux:
    """A followed company, and through which path its offers arrive."""

    nom: str
    outil: str  # greenhouse, workday, sfrss…, or "site" (read by the browser)
    cle: str  # slug, tenant, host…; the site's URL for "site"
    lien: str  # public page, opened on click


@dataclass(frozen=True)
class Compte:
    """The queue's offers that came from a feed."""

    offres: int = 0
    meilleur_fit: int = 0
    derniere: str = ""  # ISO date of the most recent one (publication, otherwise last seen)


def _nom_de_slug(slug: str) -> str:
    """« forvismazars » → « Forvismazars », « back-market » → « Back Market »."""
    return re.sub(r"[-_]+", " ", slug).strip().title() or slug


def _hote(url: str) -> str:
    h = urlparse(url if "//" in url else "https://" + url).netloc.lower()
    return h[4:] if h.startswith("www.") else h


def nom_de_site(url: str) -> str:
    """A company's name from its career site: "careers.axa.com" → "Axa"."""
    h = _hote(url)
    for p in ("careers.", "jobs.", "recrutement.", "talents.", "career.", "group.", "rejoindre-"):
        if h.startswith(p):
            h = h[len(p) :]
    return h.split(".")[0].replace("-", " ").title()


def flux_suivis(
    ats_slugs: dict[str, list[str]],
    workday: Iterable[Iterable[str]],
    autres: Iterable[Iterable[str]],
    sites: Iterable[str] = (),
) -> list[Flux]:
    """All the collection's feeds, sorted by name.

    Args:
        ats_slugs: {tool: [slugs]} (`sources_config.json`, `ats_slugs`).
        workday: [(tenant, host, site, name)].
        autres: [(tool, key, name)]; the key may carry "a|b" variants.
        sites: career sites read by the browser (`unique_domains.txt`).
    """
    from jobhunter.sources.company_lists import noms_connus

    noms = noms_connus()  # a list's slug has its real name: "realtimeboardglobal" is Miro
    sortie: list[Flux] = []
    for outil, slugs in (ats_slugs or {}).items():
        gabarit = URL_FLUX.get(outil, "")
        for slug in slugs or []:
            nom = noms.get((outil, str(slug).lower())) or _nom_de_slug(slug)
            sortie.append(Flux(nom, outil, slug, gabarit.format(slug)))
    for tenant, hote, site, nom in (tuple(f) for f in workday):
        lien = f"https://{tenant}.{hote}.myworkdayjobs.com/{site}"
        sortie.append(Flux(nom or _nom_de_slug(tenant), "workday", tenant, lien))
    for outil, cle, nom in (tuple(f) for f in autres):
        premiere = cle.split("|")[0]
        lien = "https://" + _hote(premiere) if "." in premiere else ""
        sortie.append(Flux(nom or premiere, outil, premiere, lien))
    for url in sites:
        sortie.append(Flux(nom_de_site(url), "site", url, url))
    return sorted(sortie, key=lambda f: (f.nom.lower(), f.outil))


def _marqueur(source: str) -> str:
    """Comparable form of the `source` field ("tool:key") of an offer or a feed.

    The markers have varied: "workday:pwc" today, "workday:pwc.wd3/Site" in older
    offers; "sitemap:www.sia-partners.com" for a feed declared by the full URL of its
    sitemap. We compare the tool and the tenant or the host.
    """
    outil, _, cle = source.lower().partition(":")
    if outil == "workday":
        cle = re.split(r"[./]", cle)[0]
    elif "." in cle:
        cle = _hote(cle)
    return f"{outil}:{cle}"


def _date(o: dict[str, Any]) -> str:
    return str(o.get("date_publication") or o.get("vu_le") or "")[:10]


def compter(offres: Iterable[dict[str, Any]], flux: Iterable[Flux]) -> dict[Flux, Compte]:
    """The queue's offers that came from each feed.

    An ATS feed is recognised by its exact marker (`tool:key`, case-insensitive); a
    career site, by the host of the offer's URL. Never by substring: "Bil" found
    546 offers because "bil" is in "mobilité".
    """
    flux = list(flux)
    par_marqueur = {_marqueur(f"{f.outil}:{f.cle}"): f for f in flux if f.outil != "site"}
    par_hote = {_hote(f.cle): f for f in flux if f.outil == "site"}
    cumul: dict[Flux, list[Any]] = {f: [0, 0, ""] for f in flux}
    for o in offres:
        f = par_marqueur.get(_marqueur(str(o.get("source") or "")))
        if f is None and par_hote:
            f = par_hote.get(_hote(str(o.get("url") or "")))
        if f is None:
            continue
        c = cumul[f]
        c[0] += 1
        c[1] = max(c[1], int(o.get("fit") or 0))
        c[2] = max(c[2], _date(o))
    return {f: Compte(*c) for f, c in cumul.items()}


_RX_ATS = (
    ("greenhouse", re.compile(r"greenhouse\.io/(?:embed/job_board\?for=)?([\w-]+)", re.I)),
    ("lever", re.compile(r"jobs\.(?:eu\.)?lever\.co/([\w-]+)", re.I)),
    ("ashby", re.compile(r"jobs\.ashbyhq\.com/([\w.-]+)", re.I)),
    ("recruitee", re.compile(r"//([\w-]+)\.recruitee\.com", re.I)),
    ("smartrecruiters", re.compile(r"(?:careers|jobs)\.smartrecruiters\.com/([\w-]+)", re.I)),
    ("teamtailor", re.compile(r"//([\w-]+)\.teamtailor\.com", re.I)),
    ("workable", re.compile(r"apply\.workable\.com/([\w-]+)", re.I)),
    ("personio", re.compile(r"//([\w-]+)\.jobs\.personio\.(?:de|com)", re.I)),
    ("breezy", re.compile(r"//([\w-]+)\.breezy\.hr", re.I)),
)
# Read by sources.ats.fetch_autre, so listed in `autres_flux`, not `ats_slugs`: a Workable
# URL pasted in the Companies panel used to land in ats_slugs, which never reads it.
AUTRES_OUTILS = ("workable", "personio", "breezy")
_RX_WORKDAY = re.compile(
    r"//([\w-]+)\.(wd\d+)\.myworkdayjobs\.com/(?:[a-z]{2}-[A-Z]{2}/)?([\w-]+)", re.I
)


def flux_depuis_url(url: str) -> tuple[str, Any] | None:
    """Recognises, in the URL of a career page, a feed that can be read through an API.

    Returns:
        ("greenhouse", "slug") for an ATS, ("workday", (tenant, host, site)) for
        Workday, None if the URL designates no known tool (the site will be read by
        the browser).
    """
    m = _RX_WORKDAY.search(url)
    if m:
        return "workday", (m.group(1).lower(), m.group(2).lower(), m.group(3))
    for outil, rx in _RX_ATS:
        m = rx.search(url)
        if m and m.group(1).lower() not in ("api", "v1", "embed", "jobs", "www"):
            return outil, m.group(1)
    return None


# ── Access: the collection's sources ─────────────────────────────────────────

# (name in the yield log, label, key file or "")
SOURCES_COLLECTE = (
    ("ats", "Flux ATS des entreprises (Greenhouse, Lever, Ashby…)", ""),
    ("workday", "Flux Workday des entreprises", ""),
    ("linkedin", "LinkedIn — pages publiques, sans connexion", ""),
    ("efc", "eFinancialCareers", ""),
    ("eures", "EURES (offres européennes)", ""),
    ("vie", "V.I.E — Business France", ""),
    ("fir", "FIR (finance responsable)", ""),
    ("francetravail", "France Travail — API officielle", "francetravail.json"),
    ("adzuna", "Adzuna — API officielle", "adzuna.json"),
    ("jooble", "Jooble — API officielle", "jooble.json"),
    ("freehire", "freehire — sites carrières des entreprises (API publique)", ""),
    ("apec", "APEC", ""),
    ("glassdoor", "Glassdoor", ""),
    ("wtj", "Welcome to the Jungle", ""),
    ("makesense", "Jobs that make sense (emplois à impact)", ""),
    ("hellowork", "HelloWork (essai, hors collecte du matin)", ""),
)

# The `python -m jobhunter.sources` flag that collects this source alone.
DRAPEAUX_COLLECTE = {
    "ats": "--ats",
    "workday": "--workday",
    "linkedin": "--linkedin",
    "efc": "--efc",
    "eures": "--eures",
    "vie": "--vie",
    "fir": "--fir",
    "francetravail": "--ft",
    "adzuna": "--adzuna",
    "jooble": "--jooble",
    "freehire": "--freehire",
    "apec": "--apec",
    "glassdoor": "--glassdoor",
    "wtj": "--wtj",
    "makesense": "--makesense",
    "hellowork": "--hellowork",
}

# A refused source is not retried before this delay (ADR 0004).
ATTENTE_REFUS_JOURS = 30


@dataclass(frozen=True)
class EtatSource:
    """A row of the Access panel."""

    source: str
    libelle: str
    acces: str  # "libre" or "clé"
    etat: str  # verdict lisible
    le: str  # date of the last measured collection, or ""
    gravite: str  # "ok", "ko", "ancien" or "" (row colour)
    bloque: bool = False  # refused less than 30 days ago: no new attempt


def etat_sources(
    journal: Iterable[dict[str, Any]],
    cle_presente: Callable[[str], bool],
    aujourd_hui: datetime.date | None = None,
) -> list[EtatSource]:
    """The state of each source of the collection, according to its last measurement.

    Args:
        journal: the lines of `_rendement.jsonl` (`rendement.lire_journal`).
        cle_presente: says whether the key file exists; it is never opened.
        aujourd_hui: for the tests.
    """
    jour = aujourd_hui or datetime.date.today()
    dernier: dict[str, tuple[str, dict[str, Any]]] = {}
    for ligne in journal:
        le = str(ligne.get("le") or "")
        for nom, m in (ligne.get("sources") or {}).items():
            if nom not in dernier or le >= dernier[nom][0]:
                dernier[nom] = (le, m)
    sortie = []
    for nom, libelle, fichier in SOURCES_COLLECTE:
        acces = "clé" if fichier else "libre"
        if fichier and not cle_presente(fichier):
            sortie.append(EtatSource(nom, libelle, acces, "clé à créer", "", "ancien"))
            continue
        if nom not in dernier:
            sortie.append(EtatSource(nom, libelle, acces, "pas encore mesurée", "", ""))
            continue
        le, m = dernier[nom]
        verdict = str(m.get("verdict") or "?")
        n = int(m.get("ramenees") or 0)
        etat, gravite = verdict, "ok"
        if verdict == "ok":
            etat = f"ok — {n} offre{'s' if n > 1 else ''}"
        elif verdict == "refusé" and fichier:
            # An official API that refuses (401/403) refuses OUR key: it is not an
            # anti-bot. We fix the key and try again, without waiting 30 days.
            etat, gravite = "clé refusée — vérifie-la", "ko"
        elif verdict == "refusé":
            gravite = "ko"
            try:
                reprise = datetime.date.fromisoformat(le[:10]) + datetime.timedelta(
                    days=ATTENTE_REFUS_JOURS
                )
                if reprise > jour:
                    etat = f"refusé — pas avant le {reprise:%d/%m}"
                    sortie.append(EtatSource(nom, libelle, acces, etat, le[:10], gravite, True))
                    continue
            except ValueError:
                pass
        elif verdict in ("limité", "partiel"):
            gravite = "ancien"
        elif verdict == "rien à prendre":
            gravite = ""
        sortie.append(EtatSource(nom, libelle, acces, etat, le[:10], gravite))
    return sortie


# ── My CVs: one folder per offer ─────────────────────────────────────────────


@dataclass(frozen=True)
class Dossier:
    """The CV and the letter of an offer, as they would be sent."""

    titre: str
    cv: Path | None
    lettre: Path | None
    etat: str  # "prêt", "PDF à refaire", "incomplet"
    fit: int


def dossier(offre: dict[str, Any]) -> Dossier:
    """The folder of an offer: final documents (up-to-date PDF preferred, 2.3) and their state.

    Args:
        offre: the offer (`cv` and `lettre` fields); a document missing from disk
            counts as missing.
    """
    pieces: list[Path | None] = []
    for cle in ("cv", "lettre"):
        finale = piece_finale(liens.chemin_de(offre.get(cle)))
        pieces.append(finale if finale is not None and finale.exists() else None)
    cv, lettre = pieces
    if cv is None or lettre is None:
        etat = "incomplet"
    elif cv.suffix.lower() != ".pdf" or lettre.suffix.lower() != ".pdf":
        etat = "PDF à refaire"
    else:
        etat = "prêt"
    titre = f"{offre.get('entreprise') or '?'} — {offre.get('poste') or '?'}"
    return Dossier(titre, cv, lettre, etat, int(offre.get("fit") or 0))


def dossiers(offres: Iterable[dict[str, Any]], filtre: str = "") -> list[Dossier]:
    """The folders of the offers that have one, best ranked first.

    Args:
        offres: the queue.
        filtre: text searched in the company or the job, case-insensitive.
    """
    f = filtre.strip().lower()
    sortie = []
    for o in offres:
        if not (o.get("cv") or o.get("lettre")):
            continue
        if f and f not in f"{o.get('entreprise', '')} {o.get('poste', '')}".lower():
            continue
        sortie.append(dossier(o))
    return sorted(sortie, key=lambda d: (-d.fit, d.titre.lower()))


# ── Companies: add or remove a feed from sources_config.json ─────────────────


def _graine(cfg: dict[str, Any], cle: str, defaut: Any) -> Any:
    """The value of `cle` in the config, seeded with the engine's defaults if missing.

    A missing key means "the shipped lists": writing a one-item list into it would
    erase all the others.
    """
    if cle not in cfg:
        cfg[cle] = defaut
    return cfg[cle]


def ajouter_flux(cfg: dict[str, Any], defauts: dict[str, Any], trouve: tuple[str, Any]) -> str:
    """Adds to `cfg` (modified in place) the feed recognised by `flux_depuis_url`.

    Args:
        cfg: the content of `sources_config.json`.
        defauts: the engine's lists ({"ats_slugs", "workday_flux"}).
        trouve: ("lever", "slug") or ("workday", (tenant, host, site)).

    Returns:
        The message to display.
    """
    outil, cle = trouve
    if outil == "workday":
        tenant, hote, site = cle
        lst = _graine(cfg, "workday_flux", [list(x) for x in defauts.get("workday_flux", [])])
        if any(str(x[0]).lower() == tenant for x in lst):
            return f"déjà suivi : Workday {tenant}"
        lst.append([tenant, hote, site, _nom_de_slug(tenant)])
        return f"＋ flux Workday {tenant} — lu par API dès la prochaine collecte"
    if outil in AUTRES_OUTILS:
        autres = _graine(cfg, "autres_flux", [list(x) for x in defauts.get("autres_flux", [])])
        if any(x[0] == outil and str(x[1]).lower() == str(cle).lower() for x in autres):
            return f"déjà suivi : {NOMS_OUTILS[outil]} {cle}"
        autres.append([outil, cle, _nom_de_slug(cle)])
        return f"＋ flux {NOMS_OUTILS[outil]} {cle} — lu par API dès la prochaine collecte"
    slugs_par_outil = _graine(
        cfg, "ats_slugs", {k: list(v) for k, v in defauts.get("ats_slugs", {}).items()}
    )
    slugs = slugs_par_outil.setdefault(outil, [])
    if any(s.lower() == str(cle).lower() for s in slugs):
        return f"déjà suivi : {NOMS_OUTILS.get(outil, outil)} {cle}"
    slugs.append(cle)
    return f"＋ flux {NOMS_OUTILS.get(outil, outil)} {cle} — lu par API dès la prochaine collecte"


def retirer_flux(cfg: dict[str, Any], defauts: dict[str, Any], flux: Flux) -> bool:
    """Removes an ATS, Workday or other feed from `cfg` (modified in place).

    Returns:
        True if the feed was in the config. A career site ("site") is not there:
        it lives in `unique_domains.txt`.
    """
    if flux.outil == "site":
        return False
    if flux.outil == "workday":
        lst = _graine(cfg, "workday_flux", [list(x) for x in defauts.get("workday_flux", [])])
        avant = len(lst)
        lst[:] = [x for x in lst if str(x[0]).lower() != flux.cle.lower()]
        return len(lst) < avant
    slugs = _graine(
        cfg, "ats_slugs", {k: list(v) for k, v in defauts.get("ats_slugs", {}).items()}
    ).get(flux.outil)
    if slugs and flux.cle in slugs:
        slugs.remove(flux.cle)
        return True
    autres = _graine(cfg, "autres_flux", [list(x) for x in defauts.get("autres_flux", [])])
    avant = len(autres)
    autres[:] = [
        x for x in autres if not (x[0] == flux.outil and str(x[1]).split("|")[0] == flux.cle)
    ]
    return len(autres) < avant
