"""Collection of offers: one source per module, merged directly into apply_queue.json.

Formerly Scripts/job_sources.py (4,855 lines), split in phase 3.4 of the plan:

commun         settings (keywords, slugs, feeds), title filter, contracts, countries, `_mk`
ats            public ATS APIs (Greenhouse, Lever, Ashby...) and other recruiting APIs
workday        Workday
linkedin       LinkedIn public search (guest API), waiting on 429
wtj, efc       Welcome to the Jungle, eFinancialCareers (public sitemaps)
eures          European portal
indeed, apec, glassdoor   results pages, hard stop on refusal
vie, fir, talent, francetravail, agregateurs   V.I.E, FIR, Talent.com, France Travail, Adzuna/Jooble
fusion         merge into the queue: deduplication, URL promotion, scoring
cli            the command line (`python -m jobhunter.sources` or Scripts/job_sources.py)

FACADE (jobhunter._facade). `import jobhunter.sources` (and therefore `import
job_sources`) gives a module that sees ALL the names of the submodules, like the old
single file: `js.title_ok`, `js.scan_linkedin`, `js.MONDE`. An assignment
(`js.KEYWORDS = [...]`, a monkeypatch) goes to the submodule that OWNS the name; the
others read it through `_commun.KEYWORDS`, never by copy. Without this routing, a test
that replaces `_get_borne` would let the collection go out on the real network.
"""

import re
from typing import Any

from jobhunter import _facade

_SOUS_MODULES = (
    "commun",
    "ats",
    "workday",
    "linkedin",
    "wtj",
    "efc",
    "eures",
    "indeed",
    "apec",
    "glassdoor",
    "fusion",
    "vie",
    "fir",
    "talent",
    "francetravail",
    "agregateurs",
    "cli",
)
_MODULES = _facade.installer(__name__, _SOUS_MODULES)


def _motifs() -> Any:
    """All the compiled regexes of the submodules: {(module, name): pattern}."""
    return {
        (m.__name__.rsplit(".", 1)[1], n): v
        for m in _MODULES
        for n, v in vars(m).items()
        if isinstance(v, re.Pattern) and isinstance(v.pattern, str)
    }


def _verifier_motifs() -> None:
    # EVERY compiled regex of the collection, whatever its name and its submodule.
    # The check used to only look at the `_RX_` prefix and let through
    # _DOMAIN_RX, _HARD_NEG_RX, _AI_RX... — exactly the patterns of title_ok, the filter
    # that decides what enters the queue. A safeguard that does not cover the most
    # exposed code guards nothing.
    vus = 0
    for (_m, _n), _rx in _motifs().items():
        vus += 1
        assert "\x08" not in _rx.pattern, f"{_m}.{_n} : backspace au lieu de \\b"
        assert "\\\\b" not in _rx.pattern, f"{_m}.{_n} : antislash litteral au lieu de \\b"
    # The collection counts 27 of them. If this number collapses, the selection above
    # finds nothing any more — one more silent failure.
    assert vus >= 20, f"_verifier_motifs ne voit que {vus} motifs : selection cassee"


_verifier_motifs()
