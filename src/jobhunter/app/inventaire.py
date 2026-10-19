"""Ce que montrent les panneaux Entreprises, Accès et Mes CV : des données, sans fenêtre.

Partie de jobhunter.app (étape F2 de la feuille de route). Les trois panneaux affichaient
des chiffres faux ou périmés : des entreprises comptées par sous-chaîne d'URL (« Bil » :
546 offres), une colonne ATS vide, des sources retirées depuis des semaines, 1 983 CV
listés à plat. Tout ce qu'ils calculent vit ici, en fonctions pures et testées ; les
panneaux ne font plus que l'afficher.

- **Entreprises** : les flux réellement collectés (`sources_config.json` : slugs ATS,
  flux Workday, autres flux) et les sites carrière lus par le navigateur, chacun avec les
  offres de la file qui en viennent. Une offre vient d'un flux quand son champ `source`
  vaut `outil:clé`, le marqueur que pose la collecte : un compte exact, pas un recoupement.
- **Accès** : les sources de la collecte, ce qu'il leur faut (rien, une clé) et leur
  dernier verdict mesuré (`_rendement.jsonl`, 2.4). Les clés ne sont jamais lues : seule
  la présence du fichier compte.
- **Mes CV** : un dossier par offre (CV et lettre ensemble), avec l'état des pièces
  finales, au lieu de deux listes de fichiers.
"""

import datetime
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from jobhunter import liens
from jobhunter.documents.controle import piece_finale

# Page publique d'un flux, par outil : ce qu'ouvre un clic sur la ligne.
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
    """Une entreprise suivie, et par quel chemin ses offres arrivent."""

    nom: str
    outil: str  # greenhouse, workday, sfrss…, ou « site » (lu par le navigateur)
    cle: str  # slug, tenant, hôte… ; l'URL du site pour « site »
    lien: str  # page publique, ouverte au clic


@dataclass(frozen=True)
class Compte:
    """Les offres de la file venues d'un flux."""

    offres: int = 0
    meilleur_fit: int = 0
    derniere: str = ""  # date ISO de la plus récente (publication, sinon dernière vue)


def _nom_de_slug(slug: str) -> str:
    """« forvismazars » → « Forvismazars », « back-market » → « Back Market »."""
    return re.sub(r"[-_]+", " ", slug).strip().title() or slug


def _hote(url: str) -> str:
    h = urlparse(url if "//" in url else "https://" + url).netloc.lower()
    return h[4:] if h.startswith("www.") else h


def nom_de_site(url: str) -> str:
    """Le nom d'une entreprise d'après son site carrière : « careers.axa.com » → « Axa »."""
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
    """Tous les flux de la collecte, triés par nom.

    Args:
        ats_slugs: {outil: [slugs]} (`sources_config.json`, `ats_slugs`).
        workday: [(tenant, hôte, site, nom)].
        autres: [(outil, clé, nom)] ; la clé peut porter des variantes « a|b ».
        sites: sites carrière lus par le navigateur (`unique_domains.txt`).
    """
    sortie: list[Flux] = []
    for outil, slugs in (ats_slugs or {}).items():
        gabarit = URL_FLUX.get(outil, "")
        for slug in slugs or []:
            sortie.append(Flux(_nom_de_slug(slug), outil, slug, gabarit.format(slug)))
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
    """Forme comparable du champ `source` (« outil:clé ») d'une offre ou d'un flux.

    Les marqueurs ont varié : « workday:pwc » aujourd'hui, « workday:pwc.wd3/Site » dans
    les offres anciennes ; « sitemap:www.sia-partners.com » pour un flux déclaré par
    l'URL complète de son plan de site. On compare l'outil et le tenant ou l'hôte.
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
    """Les offres de la file venues de chaque flux.

    Un flux ATS se reconnaît à son marqueur exact (`outil:clé`, sans casse) ; un site
    carrière, à l'hôte de l'URL de l'offre. Jamais par sous-chaîne : « Bil » trouvait
    546 offres parce que « bil » est dans « mobilité ».
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
)
_RX_WORKDAY = re.compile(
    r"//([\w-]+)\.(wd\d+)\.myworkdayjobs\.com/(?:[a-z]{2}-[A-Z]{2}/)?([\w-]+)", re.I
)


def flux_depuis_url(url: str) -> tuple[str, Any] | None:
    """Reconnaît un flux qu'on peut lire par API dans l'URL d'une page carrière.

    Returns:
        ("greenhouse", "slug") pour un ATS, ("workday", (tenant, hôte, site)) pour
        Workday, None si l'URL ne désigne aucun outil connu (le site sera lu par le
        navigateur).
    """
    m = _RX_WORKDAY.search(url)
    if m:
        return "workday", (m.group(1).lower(), m.group(2).lower(), m.group(3))
    for outil, rx in _RX_ATS:
        m = rx.search(url)
        if m and m.group(1).lower() not in ("api", "v1", "embed", "jobs", "www"):
            return outil, m.group(1)
    return None


# ── Accès : les sources de la collecte ───────────────────────────────────────

# (nom dans le journal de rendement, libellé, fichier de clé ou "")
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
    ("apec", "APEC", ""),
    ("glassdoor", "Glassdoor", ""),
    ("wtj", "Welcome to the Jungle", ""),
)

# Le drapeau de `python -m jobhunter.sources` qui collecte cette source seule.
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
    "apec": "--apec",
    "glassdoor": "--glassdoor",
    "wtj": "--wtj",
}

# Une source refusée n'est pas réessayée avant ce délai (ADR 0004).
ATTENTE_REFUS_JOURS = 30


@dataclass(frozen=True)
class EtatSource:
    """Une ligne du panneau Accès."""

    source: str
    libelle: str
    acces: str  # « libre » ou « clé »
    etat: str  # verdict lisible
    le: str  # date de la dernière collecte mesurée, ou ""
    gravite: str  # "ok", "ko", "ancien" ou "" (couleur de la ligne)
    bloque: bool = False  # refusée il y a moins de 30 jours : pas de nouvel essai


def etat_sources(
    journal: Iterable[dict[str, Any]],
    cle_presente: Callable[[str], bool],
    aujourd_hui: datetime.date | None = None,
) -> list[EtatSource]:
    """L'état de chaque source de la collecte, d'après sa dernière mesure.

    Args:
        journal: les lignes de `_rendement.jsonl` (`rendement.lire_journal`).
        cle_presente: dit si le fichier de clé existe ; il n'est jamais ouvert.
        aujourd_hui: pour les tests.
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
            # Une API officielle qui refuse (401/403) refuse NOTRE clé : ce n'est pas un
            # anti-bot. On corrige la clé et on réessaie, sans attendre 30 jours.
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


# ── Mes CV : un dossier par offre ────────────────────────────────────────────


@dataclass(frozen=True)
class Dossier:
    """Le CV et la lettre d'une offre, tels qu'ils partiraient."""

    titre: str
    cv: Path | None
    lettre: Path | None
    etat: str  # « prêt », « PDF à refaire », « incomplet »
    fit: int


def dossier(offre: dict[str, Any]) -> Dossier:
    """Le dossier d'une offre : pièces finales (PDF à jour préféré, 2.3) et leur état.

    Args:
        offre: l'offre (champs `cv` et `lettre`) ; une pièce absente du disque compte
            comme manquante.
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
    """Les dossiers des offres qui en ont un, les mieux classées d'abord.

    Args:
        offres: la file.
        filtre: texte cherché dans l'entreprise ou le poste, sans casse.
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


# ── Entreprises : ajouter ou retirer un flux de sources_config.json ─────────


def _graine(cfg: dict[str, Any], cle: str, defaut: Any) -> Any:
    """La valeur de `cle` dans la config, semée des défauts du moteur si absente.

    Une clé absente veut dire « les listes livrées » : y écrire une liste d'un seul
    élément effacerait toutes les autres.
    """
    if cle not in cfg:
        cfg[cle] = defaut
    return cfg[cle]


def ajouter_flux(cfg: dict[str, Any], defauts: dict[str, Any], trouve: tuple[str, Any]) -> str:
    """Ajoute à `cfg` (modifiée en place) le flux reconnu par `flux_depuis_url`.

    Args:
        cfg: le contenu de `sources_config.json`.
        defauts: les listes du moteur ({"ats_slugs", "workday_flux"}).
        trouve: ("lever", "slug") ou ("workday", (tenant, hôte, site)).

    Returns:
        Le message à afficher.
    """
    outil, cle = trouve
    if outil == "workday":
        tenant, hote, site = cle
        lst = _graine(cfg, "workday_flux", [list(x) for x in defauts.get("workday_flux", [])])
        if any(str(x[0]).lower() == tenant for x in lst):
            return f"déjà suivi : Workday {tenant}"
        lst.append([tenant, hote, site, _nom_de_slug(tenant)])
        return f"＋ flux Workday {tenant} — lu par API dès la prochaine collecte"
    slugs_par_outil = _graine(
        cfg, "ats_slugs", {k: list(v) for k, v in defauts.get("ats_slugs", {}).items()}
    )
    slugs = slugs_par_outil.setdefault(outil, [])
    if any(s.lower() == str(cle).lower() for s in slugs):
        return f"déjà suivi : {NOMS_OUTILS.get(outil, outil)} {cle}"
    slugs.append(cle)
    return f"＋ flux {NOMS_OUTILS.get(outil, outil)} {cle} — lu par API dès la prochaine collecte"


def retirer_flux(cfg: dict[str, Any], defauts: dict[str, Any], flux: Flux) -> bool:
    """Retire un flux ATS, Workday ou autre de `cfg` (modifiée en place).

    Returns:
        True si le flux était dans la config. Un site carrière (« site ») n'y est pas :
        il vit dans `unique_domains.txt`.
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
