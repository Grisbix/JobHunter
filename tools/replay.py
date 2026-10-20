#!/usr/bin/env python3
"""Real responses of the sources, recorded once, replayed without network.

The doubles in `tests/conftest.py` (faux_reseau) are hand-written: they say that the
code can read the response we IMAGINE, not the one the site returns today. Here, a real
public response is recorded (one request per source, reduced settings), cleaned, then
replayed by the tests: the parser must find exactly the same offers. An exchange that
was not recorded makes the test fail.

Everything goes through the single network boundary of the sources,
`sources.commun._get_borne` and `_post_borne`: that is what is recorded, then replaced
on replay.

Cleaning: no request header is kept, and from the response only the status code,
the content type, the final address and the body. Long JSON lists are reduced to 5
items when the replay stays complete without the rest.

Sources chosen according to the project rules: no APEC (refused entry, no new attempt
before 30 days), no WTJ (anti-bot challenge), and no key-based source (France Travail,
Adzuna, Jooble).

Record (goes on the network, run on purpose):
    python tools/replay.py enregistrer            # all sources
    python tools/replay.py enregistrer lever fir  # some of them
The replay is done by tests/test_source_replay.py.

Decision: docs/adr/0006-non-regression-bench.md
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

# name: (module, function, arguments, settings {module:NAME -> value})
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
        # fresh pass state: a stop left by another collection or another
        # test would make it return an empty list without any request
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


# ── the replayed response: what the sources read from an httpx.Response ──────────
class Reponse:
    """Réponse rejouée : code, en-têtes réduits, adresse finale, corps."""

    def __init__(self, statut: int, type_contenu: str, url: str, corps: str) -> None:
        """Builds the response from a recorded exchange."""
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
        """Raises like httpx on an error code."""
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


def cle(methode: str, url: str, kw: dict[str, Any]) -> str:
    """Identity of an exchange: method, address, parameters and JSON body of the request."""
    params = json.dumps(kw.get("params") or {}, sort_keys=True, ensure_ascii=False)
    corps = json.dumps(kw.get("json") or kw.get("data") or {}, sort_keys=True, ensure_ascii=False)
    return f"{methode} {url} {params} {corps}"


class EchangeManquant(AssertionError):
    """The code asked for an address the recording does not contain."""


def rejoueur(
    echanges: list[dict[str, Any]], manquants: list[str]
) -> tuple[Callable[..., Any], Callable[..., Any]]:
    """The stand-ins for `_get_borne` and `_post_borne`, served from the recording.

    A missing exchange is NOTED in `manquants` before raising: some sources catch
    any exception around their request and would silently return an empty list;
    `rejouer` checks the list after the call.
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
    """Applies a scenario's reduced settings, then puts the original values back."""
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
    """Runs a scenario's source (network or replay, depending on what is plugged in)."""
    module, fonction, args, _ = SCENARIOS[nom]
    return list(getattr(importlib.import_module(module), fonction)(*args) or [])


def empreinte(offres: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """What must stay identical on replay: useful fields, description by fingerprint."""
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
    """Replays a recording: returns the offers the source draws from it, without network."""
    from jobhunter.network import INCIDENTS
    from jobhunter.sources import common as commun

    manquants: list[str] = []
    get, post = rejoueur(cassette["echanges"], manquants)
    vrai_get, vrai_post, vrai_sleep = commun._get_borne, commun._post_borne, time.sleep
    commun._get_borne, commun._post_borne = get, post
    time.sleep = lambda s: None  # type: ignore[assignment]  # polite pauses are useless off the network
    INCIDENTS.clear()
    try:
        with reglages(SCENARIOS[cassette["scenario"]][3]):
            offres = appeler(cassette["scenario"])
        if manquants:  # even if the source swallowed the exception
            raise EchangeManquant("échange(s) non enregistré(s) : " + " ; ".join(manquants))
        return offres
    finally:
        commun._get_borne, commun._post_borne, time.sleep = vrai_get, vrai_post, vrai_sleep
        INCIDENTS.clear()


def _reduire(corps: str, type_contenu: str, titres: set[str]) -> str:
    """Keeps, in the JSON lists, the items that give a kept offer (their
    title appears there) and two others, which the filter must keep setting aside."""
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
    """Goes on the network ONCE for this scenario, cleans, checks the replay, writes."""
    from jobhunter.sources import common as commun

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
    # The full recording must give back EXACTLY the offers seen live.
    offres = rejouer(cassette)
    if empreinte(offres) != empreinte(en_direct):
        raise AssertionError(f"{nom} : le rejeu ne redonne pas les offres vues en direct")
    # Reduce long JSON lists to the useful items; kept only if the replay
    # gives back EXACTLY the same offers (otherwise the full body stays).
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
