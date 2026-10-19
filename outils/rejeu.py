#!/usr/bin/env python3
"""Réponses réelles des sources, enregistrées une fois, rejouées sans réseau.

Les doublures de `tests/conftest.py` (faux_reseau) sont écrites à la main : elles disent
que le code sait lire la réponse qu'on IMAGINE, pas celle que le site renvoie
aujourd'hui. Ici, une vraie réponse publique est enregistrée (une requête par source,
réglages réduits), nettoyée, puis rejouée par les tests : le parseur doit retrouver
exactement les mêmes offres. Un échange non enregistré fait échouer le test.

Tout passe par la frontière réseau unique des sources, `sources.commun._get_borne` et
`_post_borne` : c'est elle qu'on enregistre, puis qu'on remplace au rejeu.

Nettoyage : aucun en-tête de requête n'est gardé, et de la réponse seulement le code,
le type de contenu, l'adresse finale et le corps. Les listes JSON longues sont
réduites à 5 éléments quand le rejeu reste complet sans le reste.

Sources choisies selon les règles du projet : pas d'APEC (refus d'entrée, pas de
nouvel essai avant 30 jours), pas de WTJ (défi anti-bot), ni de source à clé (France
Travail, Adzuna, Jooble).

Enregistrer (va sur le réseau, à lancer exprès) :
    python outils/rejeu.py enregistrer            # toutes les sources
    python outils/rejeu.py enregistrer lever fir  # certaines
Le rejeu est fait par tests/test_rejeu_sources.py.

Decision : docs/adr/0006-banc-de-non-regression.md
"""

import hashlib
import importlib
import json
import sys
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

RACINE = Path(__file__).resolve().parent.parent
CASSETTES = RACINE / "tests" / "reponses"
MAX_ELEMENTS = 5

# nom : (module, fonction, arguments, réglages {module:NOM -> valeur})
SCENARIOS: dict[str, tuple[str, str, list[Any], dict[str, Any]]] = {
    "greenhouse": ("jobhunter.sources.ats", "fetch_ats", ["greenhouse", "forvismazars"], {}),
    "lever": ("jobhunter.sources.ats", "fetch_ats", ["lever", "agicap"], {}),
    "ashby": ("jobhunter.sources.ats", "fetch_ats", ["ashby", "alan"], {}),
    "workday": (
        "jobhunter.sources.workday",
        "fetch_workday",
        ["eiffage", "wd3", "Eiffage_Careers", "Eiffage"],
        {
            "jobhunter.sources.workday:WORKDAY_MOTS": ["finance"],
            "jobhunter.sources.workday:WORKDAY_PAGES": 1,
            "jobhunter.sources.workday:WORKDAY_DETAILS": 2,
            "jobhunter.sources.workday:WORKDAY_PAUSE": 0,
        },
    ),
    "linkedin": (
        "jobhunter.sources.linkedin",
        "linkedin_guest_search",
        ["analyste esg", 1, 7],
        # etat de passe neuf : un arret (« stop ») laisse par une autre collecte ou un
        # autre test ferait rendre une liste vide sans aucune requete
        {
            "jobhunter.sources.linkedin:_LI": {
                "stop": None,
                "attendu": 0.0,
                "suite_429": 0,
                "debut": 0.0,
            }
        },
    ),
    "eures": (
        "jobhunter.sources.eures",
        "scan_eures",
        [1, 10, ["ESG"]],
        {"jobhunter.sources.eures:EURES_DELAI": 0},
    ),
    "fir": ("jobhunter.sources.fir", "fetch_fir", [], {}),
}


# ── la réponse rejouée : ce que les sources lisent d'une httpx.Response ──────────
class Reponse:
    """Réponse rejouée : code, en-têtes réduits, adresse finale, corps."""

    def __init__(self, statut: int, type_contenu: str, url: str, corps: str) -> None:
        """Construit la réponse depuis un échange enregistré."""
        self.status_code = statut
        self.headers = {"content-type": type_contenu}
        self.url = url
        self.text = corps
        self.content = corps.encode("utf-8")
        self.encoding = "utf-8"

    def json(self) -> Any:
        """Le corps décodé en JSON."""
        return json.loads(self.text)

    def raise_for_status(self) -> None:
        """Lève comme httpx sur un code d'erreur."""
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


def cle(methode: str, url: str, kw: dict[str, Any]) -> str:
    """Identité d'un échange : méthode, adresse, paramètres et corps JSON de la requête."""
    params = json.dumps(kw.get("params") or {}, sort_keys=True, ensure_ascii=False)
    corps = json.dumps(kw.get("json") or kw.get("data") or {}, sort_keys=True, ensure_ascii=False)
    return f"{methode} {url} {params} {corps}"


class EchangeManquant(AssertionError):
    """Le code a demandé une adresse que l'enregistrement ne contient pas."""


def rejoueur(
    echanges: list[dict[str, Any]], manquants: list[str]
) -> tuple[Callable[..., Any], Callable[..., Any]]:
    """Les remplaçants de `_get_borne` et `_post_borne`, servis depuis l'enregistrement.

    Un échange absent est NOTÉ dans `manquants` avant de lever : certaines sources
    attrapent toute exception autour de leur requête et rendraient une liste vide en
    silence ; `rejouer` vérifie la liste après l'appel.
    """
    table = {e["cle"]: e for e in echanges}

    def servir(methode: str, url: str, kw: dict[str, Any]) -> Reponse:
        e = table.get(cle(methode, url, kw))
        if e is None:
            manquants.append(f"{methode} {url}")
            raise EchangeManquant(f"échange non enregistré : {methode} {url}")
        return Reponse(e["statut"], e["type"], e["url"], e["corps"])

    def get(envoi: Any, url: str, **kw: Any) -> Reponse:
        return servir("GET", url, kw)

    def post(envoi: Any, url: str, **kw: Any) -> Reponse:
        return servir("POST", url, kw)

    return get, post


@contextmanager
def reglages(valeurs: dict[str, Any]) -> Iterator[None]:
    """Applique les réglages réduits d'un scénario, puis remet les valeurs d'origine."""
    avant = []
    for chemin, valeur in valeurs.items():
        module, nom = chemin.split(":")
        m = importlib.import_module(module)
        avant.append((m, nom, getattr(m, nom)))
        setattr(m, nom, valeur)
    try:
        yield
    finally:
        for m, nom, v in avant:
            setattr(m, nom, v)


def appeler(nom: str) -> list[dict[str, Any]]:
    """Lance la source d'un scénario (réseau ou rejeu selon ce qui est branché)."""
    module, fonction, args, _ = SCENARIOS[nom]
    return list(getattr(importlib.import_module(module), fonction)(*args) or [])


def empreinte(offres: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Ce qui doit rester identique au rejeu : champs utiles, description par empreinte."""
    sortie = []
    for o in offres:
        desc = str(o.get("description") or "")
        sortie.append(
            {
                "titre": o.get("titre"),
                "url": o.get("url"),
                "entreprise": o.get("entreprise"),
                "location": o.get("location"),
                "date": o.get("date"),
                "source": o.get("source"),
                "description": hashlib.sha256(desc.encode("utf-8")).hexdigest()[:16]
                if desc
                else "",
            }
        )
    return sortie


def rejouer(cassette: dict[str, Any]) -> list[dict[str, Any]]:
    """Rejoue un enregistrement : rend les offres que la source en tire, sans réseau."""
    from jobhunter.reseau import INCIDENTS
    from jobhunter.sources import commun

    manquants: list[str] = []
    get, post = rejoueur(cassette["echanges"], manquants)
    vrai_get, vrai_post, vrai_sleep = commun._get_borne, commun._post_borne, time.sleep
    commun._get_borne, commun._post_borne = get, post
    time.sleep = lambda s: None  # type: ignore[assignment]  # les pauses polies ne servent pas hors réseau
    INCIDENTS.clear()
    try:
        with reglages(SCENARIOS[cassette["scenario"]][3]):
            offres = appeler(cassette["scenario"])
        if manquants:  # meme si la source a avale l'exception
            raise EchangeManquant("échange(s) non enregistré(s) : " + " ; ".join(manquants))
        return offres
    finally:
        commun._get_borne, commun._post_borne, time.sleep = vrai_get, vrai_post, vrai_sleep
        INCIDENTS.clear()


def _reduire(corps: str, type_contenu: str, titres: set[str]) -> str:
    """Garde, dans les listes JSON, les éléments qui donnent une offre retenue (leur
    titre y figure) et deux autres, que le filtre doit continuer d'écarter."""
    if "json" not in type_contenu:
        return corps
    try:
        d = json.loads(corps)
    except ValueError:
        return corps

    def tri(liste: list[Any]) -> list[Any]:
        utiles, autres = [], []
        for el in liste:
            texte = json.dumps(el, ensure_ascii=False)
            (utiles if any(t and t in texte for t in titres) else autres).append(el)
        return utiles + autres[:2]

    if isinstance(d, list):
        d = tri(d)
    elif isinstance(d, dict):
        d = {
            k: (tri(v) if isinstance(v, list) and len(v) > MAX_ELEMENTS else v)
            for k, v in d.items()
        }
    return json.dumps(d, ensure_ascii=False)


def enregistrer(nom: str) -> dict[str, Any]:
    """Va sur le réseau UNE fois pour ce scénario, nettoie, vérifie le rejeu, écrit."""
    from jobhunter.sources import commun

    echanges: list[dict[str, Any]] = []
    vrai_get, vrai_post = commun._get_borne, commun._post_borne

    def capter(methode: str, vraie: Callable[..., Any]) -> Callable[..., Any]:
        def f(envoi: Any, url: str, **kw: Any) -> Any:
            r = vraie(envoi, url, **kw)
            echanges.append(
                {
                    "cle": cle(methode, url, kw),
                    "statut": int(r.status_code),
                    "type": str(r.headers.get("content-type", "")),
                    "url": str(r.url),
                    "corps": r.text,
                }
            )
            return r

        return f

    commun._get_borne, commun._post_borne = capter("GET", vrai_get), capter("POST", vrai_post)
    try:
        with reglages(SCENARIOS[nom][3]):
            en_direct = appeler(nom)
    finally:
        commun._get_borne, commun._post_borne = vrai_get, vrai_post

    cassette = {"scenario": nom, "le": time.strftime("%Y-%m-%d"), "echanges": echanges}
    # L'enregistrement complet doit redonner EXACTEMENT les offres vues en direct.
    offres = rejouer(cassette)
    if empreinte(offres) != empreinte(en_direct):
        raise AssertionError(f"{nom} : le rejeu ne redonne pas les offres vues en direct")
    # Réduire les listes JSON longues aux éléments utiles ; gardé seulement si le rejeu
    # redonne EXACTEMENT les mêmes offres (sinon le corps complet reste).
    titres = {str(o.get("titre") or "") for o in en_direct}
    reduite = dict(
        cassette,
        echanges=[dict(e, corps=_reduire(e["corps"], e["type"], titres)) for e in echanges],
    )
    try:
        if empreinte(rejouer(reduite)) == empreinte(offres):
            cassette = reduite
    except EchangeManquant:
        pass
    cassette["attendu"] = empreinte(offres)
    CASSETTES.mkdir(parents=True, exist_ok=True)
    chemin = CASSETTES / f"{nom}.json"
    chemin.write_text(json.dumps(cassette, ensure_ascii=False, indent=1), encoding="utf-8")
    print(
        f"{nom:<11} {len(echanges)} échange(s), {len(en_direct)} offres en direct, "
        f"{len(offres)} au rejeu, {chemin.stat().st_size // 1024} Ko"
    )
    return cassette


def main(argv: list[str]) -> int:
    """`enregistrer [scénario...]` : enregistre (réseau) les scénarios demandés."""
    if not argv or argv[0] != "enregistrer":
        print(__doc__)
        return 2
    for nom in argv[1:] or list(SCENARIOS):
        try:
            enregistrer(nom)
        except Exception as e:
            print(f"{nom:<11} ÉCHEC : {type(e).__name__}: {e}")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(RACINE / "src"))
    sys.exit(main(sys.argv[1:]))
