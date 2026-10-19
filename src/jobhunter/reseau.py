"""HTTP requests BOUNDED in total duration, on reused connections.

Former block of Scripts/job_sources.py (phase 3.2 of the plan). httpx's `timeout=`
bounds each packet, not the request: a server that drips one byte every 19 s holds the
connection forever (on 2026-09-22, fr.talent.com blocked the scheduled scan for
12 h 25). Here the elapsed time is checked at each packet received.

    get_borne(envoi, url, **kw)     GET, returns a real httpx.Response
    post_borne(envoi, url, **kw)    POST
    req_borne(envoi, methode, url, total=..., max_octets=...)
    lire_borne(f, total, max_octets)  f.read() of an urlopen, also bounded
    client_partage()                the single httpx.Client that keeps its connections
    INCIDENTS                       the run's refusals and failures, per source and per cause

`envoi`: the httpx module (we then go through the shared client) or an httpx.Client.
job_sources keeps its old names (`_get_borne`...): the test doubles replace them there,
and job_sources' calls go through them.

Decision: docs/adr/0004-429-attendre-403-arreter.md
"""

import collections
import time
from typing import TYPE_CHECKING, Any, BinaryIO

if TYPE_CHECKING:
    import httpx

_CLIENT: "httpx.Client | None" = None


def exiger_http(url: str) -> str:
    """Returns `url` if its scheme is http or https; raises ValueError otherwise.

    `urllib.request.urlopen` also opens `file://` and other schemes: an address coming
    from a page or a setting (sitemap, Ollama host) could make it read a local file.
    Every call to `urlopen` goes through here first.

    Args:
        url: the address to open.

    Returns:
        The same address.

    Raises:
        ValueError: scheme other than http or https.
    """
    schema = url.split(":", 1)[0].lower() if ":" in url else ""
    if schema not in ("http", "https"):
        raise ValueError(f"schéma d'URL refusé : {schema or '(aucun)'}")
    return url


class Incidents(collections.defaultdict[str, collections.Counter[str | int]]):
    """The run's refusals and failures: `INCIDENTS[source][cause] += 1`.

    An empty collection has two opposite causes, nothing to take or a refused entry;
    this counter tells them apart, and `resume()` displays them at the end of the scan
    so that an entirely throttled scan does not look like a quiet day.
    """

    def __init__(self) -> None:
        """An empty counter."""
        super().__init__(collections.Counter)

    def noter(self, source: str, cause: str | int) -> None:
        """Counts a refusal or a failure.

        Args:
            source: the source concerned ("linkedin", "apec"…).
            cause: the HTTP code or the name of the exception.
        """
        self[source][cause] += 1

    def resume(self) -> list[str]:
        """One line per source, most frequent causes first. Empty if nothing."""
        lignes = []
        for source, par_cause in sorted(self.items()):
            detail = ", ".join(
                f"{cause}×{n}" for cause, n in sorted(par_cause.items(), key=lambda kv: -kv[1])
            )
            lignes.append(f"  ⚠ {source} : {detail}")
        return lignes


# A single counter per process, next to the client that makes the requests.
INCIDENTS = Incidents()


def client_partage() -> "httpx.Client":
    """A single httpx.Client, which KEEPS ITS CONNECTIONS OPEN.

    WHY. Calling `httpx.get` reopens a TLS connection at each request. Measured on
    2026-10-02: 4 SmartRecruiters calls in 13.7 s through the module, 4.5 s through a
    client; Workday 14.3 s versus 5.4. On a collection of several hundred calls, it was
    most of the time: talan alone took 8 min (69 postings), each Workday feed 6 to 8 —
    and pass a exceeded its 60 min before reaching LinkedIn.
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
    """Httpx request with a maximum TOTAL duration. Returns a real httpx.Response.

    See `get_borne` for the why. Generalised on 2026-09-23 to all the sources: the
    first version only protected Talent.com, and returned an object without
    `.json()`, which prevented using it elsewhere.

    The Response is rebuilt WITHOUT content-encoding: `iter_bytes` has already
    decompressed the body, and leaving it announced as gzip would make it decompress
    twice.

    Args:
        envoi: the httpx module or an httpx.Client — both have `.stream()`.
        methode: "GET", "POST"…
        url: the requested address.
        total: maximum duration of the whole request, in seconds; None = three times
            the per-operation delay, at least 60 s.
        max_octets: maximum size of the body.
        **kw: passed to `envoi.stream` (headers, params, json, timeout…).

    Returns:
        A real httpx.Response, body already read.

    Raises:
        httpx.TimeoutException: total duration or maximum size exceeded.
    """
    import httpx as _hx

    if envoi is _hx:  # the module: no reused connection
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
    """POST bounded in total duration: `req_borne(envoi, "POST", url, **kw)`."""
    return req_borne(envoi, "POST", url, **kw)


def lire_borne(f: BinaryIO, total: float = 60, max_octets: int = 20_000_000) -> bytes:
    """`f.read()` of an urlopen, but bounded in TOTAL duration.

    `urlopen(timeout=25)` bounds each socket operation, exactly like httpx: a server
    that drips its bytes holds it forever.

    Args:
        f: the response opened by urlopen.
        total: maximum duration of the read, in seconds.
        max_octets: maximum size read.

    Returns:
        The body read.

    Raises:
        TimeoutError: read longer than `total`.
    """
    debut, taille = time.time(), 0
    blocs: list[bytes] = []
    # read1, NOT read(n): read(65536) waits for the 64 KB to have arrived before
    # giving control back, so the duration was only checked at the very end —
    # measured: a server at one byte every 0.3 s held the read for 60 s
    # despite total=3. read1 returns what is already there.
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
    """GET with a maximum TOTAL duration. Returns a real httpx.Response.

    WHY. `timeout=20` in httpx bounds EACH operation — connection, reading a packet —
    not the whole request. A server that sends one byte every 19 seconds therefore
    keeps the connection open forever. On 2026-09-22 at 22:49, the scheduled scan got
    stuck that way on fr.talent.com (3.175.86.19, CloudFront): 12 h 25 of established
    connection, 149 s of CPU, the queue lock held all along, and the pipeline's 90-min
    delay, which was supposed to kill it, killed nothing.

    Here the elapsed time is checked at each packet received: at worst, total + 20 s.
    Raises httpx.TimeoutException beyond that, like an ordinary timeout — the callers
    that already catch `Exception` have nothing to change.

    Args:
        envoi: the httpx module or an httpx.Client.
        url: the requested address.
        **kw: like `req_borne` (total, max_octets, headers, params…).

    Returns:
        A real httpx.Response.

    Raises:
        httpx.TimeoutException: total duration exceeded.
    """
    return req_borne(envoi, "GET", url, **kw)
