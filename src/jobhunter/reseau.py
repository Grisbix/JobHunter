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

`envoi` : le module httpx (on passe alors par le client partage) ou un httpx.Client.
job_sources garde ses anciens noms (`_get_borne`...) : les doublures des tests les
remplacent la, et les appels de job_sources passent par eux.
"""

import time

_CLIENT = None


def client_partage():
    """Un httpx.Client unique, qui GARDE SES CONNEXIONS OUVERTES.

    POURQUOI. Appeler `httpx.get` rouvre une connexion TLS a chaque requete.
    Mesure le 2026-10-02 : 4 appels SmartRecruiters en 13,7 s par le module,
    4,5 s par un client ; Workday 14,3 s contre 5,4. Sur une collecte de
    plusieurs centaines d'appels, c'etait l'essentiel du temps : talan seul
    prenait 8 min (69 fiches), chaque flux Workday 6 a 8 — et la passe a
    depassait ses 60 min avant d'atteindre LinkedIn."""
    global _CLIENT
    if _CLIENT is None:
        import httpx as _hx

        _CLIENT = _hx.Client(limits=_hx.Limits(max_connections=20, max_keepalive_connections=20))
    return _CLIENT


def req_borne(envoi, methode, url, total=None, max_octets=20_000_000, **kw):
    """Requete httpx avec une duree TOTALE maximale. Rend une vraie httpx.Response.

    `envoi` : le module httpx ou un httpx.Client — les deux ont `.stream()`.
    `total` : par defaut trois fois le delai par operation, 60 s au moins.

    Voir `get_borne` pour le pourquoi. Generalisee le 2026-09-23 a toutes les
    sources : la premiere version ne protegeait que Talent.com, et rendait un
    objet sans `.json()`, ce qui interdisait de l'employer ailleurs.

    La Response est reconstruite SANS content-encoding : `iter_bytes` a deja
    decompresse le corps, et le laisser annonce gzip ferait decompresser deux
    fois."""
    import httpx as _hx

    if envoi is _hx:  # le module : pas de connexion reutilisee
        envoi = client_partage()
    kw.setdefault("timeout", 20)
    t = kw["timeout"] if isinstance(kw["timeout"], (int, float)) else 20
    total = total or max(60, 3 * t)
    debut = time.time()
    with envoi.stream(methode, url, **kw) as r:
        blocs, taille = [], 0
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


def post_borne(envoi, url, **kw):
    return req_borne(envoi, "POST", url, **kw)


def lire_borne(f, total=60, max_octets=20_000_000):
    """`f.read()` d'un urlopen, mais borne en duree TOTALE.

    `urlopen(timeout=25)` borne chaque operation de socket, exactement comme
    httpx : un serveur qui distille ses octets le tient indefiniment."""
    debut, blocs, taille = time.time(), [], 0
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


def get_borne(envoi, url, **kw):
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
    qui attrapent deja `Exception` n'ont rien a changer."""
    return req_borne(envoi, "GET", url, **kw)
