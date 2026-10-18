"""Requetes HTTP BORNEES en duree totale, sur des connexions reutilisees.

Ancien bloc de Scripts/job_sources.py (phase 3.2 du plan). `timeout=` d'httpx borne
chaque paquet, pas la requete : un serveur qui distille un octet toutes les 19 s tient
la connexion indefiniment (le 2026-09-22, fr.talent.com a bloque le scan planifie
12 h 25). Ici le temps ecoule est verifie a chaque paquet recu.

    get_borne(envoi, url, **kw)     GET, rend une vraie httpx.Response
    post_borne(envoi, url, **kw)    POST
    req_borne(envoi, methode, url, total=..., max_octets=...)
    lire_borne(f, total, max_octets)  f.read() d'un urlopen, borne aussi
    client_partage()                le httpx.Client unique qui garde ses connexions
    INCIDENTS                       les refus et pannes du run, par source et par cause

`envoi` : le module httpx (on passe alors par le client partage) ou un httpx.Client.
job_sources garde ses anciens noms (`_get_borne`...) : les doublures des tests les
remplacent la, et les appels de job_sources passent par eux.
"""

import collections
import time
from typing import TYPE_CHECKING, Any, BinaryIO

if TYPE_CHECKING:
    import httpx

_CLIENT: "httpx.Client | None" = None


class Incidents(collections.defaultdict[str, collections.Counter[str | int]]):
    """Les refus et pannes du run : `INCIDENTS[source][cause] += 1`.

    Une collecte vide a deux causes opposees, rien a prendre ou un refus d'entree ;
    ce compteur les distingue, et `resume()` les affiche en fin de scan pour qu'un
    scan entierement bride ne ressemble pas a une journee calme.
    """

    def __init__(self) -> None:
        """Un compteur vide."""
        super().__init__(collections.Counter)

    def noter(self, source: str, cause: str | int) -> None:
        """Compte un refus ou une panne.

        Args:
            source: la source concernee (« linkedin », « apec »…).
            cause: le code HTTP ou le nom de l'exception.
        """
        self[source][cause] += 1

    def resume(self) -> list[str]:
        """Une ligne par source, causes les plus frequentes d'abord. Vide si rien."""
        lignes = []
        for source, par_cause in sorted(self.items()):
            detail = ", ".join(
                f"{cause}×{n}" for cause, n in sorted(par_cause.items(), key=lambda kv: -kv[1])
            )
            lignes.append(f"  ⚠ {source} : {detail}")
        return lignes


# Un seul compteur par processus, a cote du client qui fait les requetes.
INCIDENTS = Incidents()


def client_partage() -> "httpx.Client":
    """Un httpx.Client unique, qui GARDE SES CONNEXIONS OUVERTES.

    POURQUOI. Appeler `httpx.get` rouvre une connexion TLS a chaque requete.
    Mesure le 2026-10-02 : 4 appels SmartRecruiters en 13,7 s par le module,
    4,5 s par un client ; Workday 14,3 s contre 5,4. Sur une collecte de
    plusieurs centaines d'appels, c'etait l'essentiel du temps : talan seul
    prenait 8 min (69 fiches), chaque flux Workday 6 a 8 — et la passe a
    depassait ses 60 min avant d'atteindre LinkedIn.
    """
    global _CLIENT
    if _CLIENT is None:
        import httpx as _hx

        _CLIENT = _hx.Client(limits=_hx.Limits(max_connections=20, max_keepalive_connections=20))
    return _CLIENT


def req_borne(
    envoi: Any,
    methode: str,
    url: str,
    total: float | None = None,
    max_octets: int = 20_000_000,
    **kw: Any,
) -> "httpx.Response":
    """Requete httpx avec une duree TOTALE maximale. Rend une vraie httpx.Response.

    Voir `get_borne` pour le pourquoi. Generalisee le 2026-09-23 a toutes les
    sources : la premiere version ne protegeait que Talent.com, et rendait un
    objet sans `.json()`, ce qui interdisait de l'employer ailleurs.

    La Response est reconstruite SANS content-encoding : `iter_bytes` a deja
    decompresse le corps, et le laisser annonce gzip ferait decompresser deux
    fois.

    Args:
        envoi: le module httpx ou un httpx.Client — les deux ont `.stream()`.
        methode: « GET », « POST »…
        url: l'adresse demandee.
        total: duree maximale de toute la requete, en secondes ; None = trois fois
            le delai par operation, 60 s au moins.
        max_octets: taille maximale du corps.
        **kw: transmis a `envoi.stream` (headers, params, json, timeout…).

    Returns:
        Une vraie httpx.Response, corps deja lu.

    Raises:
        httpx.TimeoutException: duree totale ou taille maximale depassee.
    """
    import httpx as _hx

    if envoi is _hx:  # le module : pas de connexion reutilisee
        envoi = client_partage()
    kw.setdefault("timeout", 20)
    t = kw["timeout"] if isinstance(kw["timeout"], (int, float)) else 20
    total = total or max(60, 3 * t)
    debut = time.time()
    with envoi.stream(methode, url, **kw) as r:
        blocs: list[bytes] = []
        taille = 0
        for bloc in r.iter_bytes():
            blocs.append(bloc)
            taille += len(bloc)
            if time.time() - debut > total:
                raise _hx.TimeoutException(f"plus de {total:.0f} s pour {url}")
            if taille > max_octets:
                raise _hx.TimeoutException(f"plus de {max_octets} octets pour {url}")
        tetes = [
            (k, v)
            for k, v in r.headers.multi_items()
            if k.lower() not in ("content-encoding", "content-length", "transfer-encoding")
        ]
        return _hx.Response(
            r.status_code, headers=tetes, content=b"".join(blocs), request=r.request
        )


def post_borne(envoi: Any, url: str, **kw: Any) -> "httpx.Response":
    """POST borne en duree totale : `req_borne(envoi, "POST", url, **kw)`."""
    return req_borne(envoi, "POST", url, **kw)


def lire_borne(f: BinaryIO, total: float = 60, max_octets: int = 20_000_000) -> bytes:
    """`f.read()` d'un urlopen, mais borne en duree TOTALE.

    `urlopen(timeout=25)` borne chaque operation de socket, exactement comme
    httpx : un serveur qui distille ses octets le tient indefiniment.

    Args:
        f: la reponse ouverte par urlopen.
        total: duree maximale de la lecture, en secondes.
        max_octets: taille maximale lue.

    Returns:
        Le corps lu.

    Raises:
        TimeoutError: lecture plus longue que `total`.
    """
    debut, taille = time.time(), 0
    blocs: list[bytes] = []
    # read1, PAS read(n) : read(65536) attend que les 64 Ko soient arrives avant
    # de rendre la main, donc la duree n'etait controlee qu'a la toute fin —
    # mesure : un serveur a un octet toutes les 0,3 s tenait la lecture 60 s
    # malgre total=3. read1 rend ce qui est deja la.
    lire = getattr(f, "read1", f.read)
    while True:
        bloc = lire(65536)
        if not bloc:
            return b"".join(blocs)
        blocs.append(bloc)
        taille += len(bloc)
        if time.time() - debut > total or taille > max_octets:
            raise TimeoutError(f"lecture de plus de {total} s ou {max_octets} octets")


def get_borne(envoi: Any, url: str, **kw: Any) -> "httpx.Response":
    """GET avec une duree TOTALE maximale. Rend une vraie httpx.Response.

    POURQUOI. `timeout=20` dans httpx borne CHAQUE operation — connexion,
    lecture d'un paquet — pas la requete entiere. Un serveur qui envoie un
    octet toutes les 19 secondes garde donc la connexion ouverte pour toujours.
    Le 2026-09-22 a 22h49, le scan planifie s'est bloque ainsi sur fr.talent.com
    (3.175.86.19, CloudFront) : 12 h 25 de connexion etablie, 149 s de CPU, le
    verrou de la file tenu tout du long, et le delai de 90 min du pipeline, qui
    devait le tuer, n'a rien tue.

    Ici le temps ecoule est verifie a chaque paquet recu : au pire, total + 20 s.
    Leve httpx.TimeoutException au-dela, comme un delai ordinaire — les appelants
    qui attrapent deja `Exception` n'ont rien a changer.

    Args:
        envoi: le module httpx ou un httpx.Client.
        url: l'adresse demandee.
        **kw: comme `req_borne` (total, max_octets, headers, params…).

    Returns:
        Une vraie httpx.Response.

    Raises:
        httpx.TimeoutException: duree totale depassee.
    """
    return req_borne(envoi, "GET", url, **kw)
