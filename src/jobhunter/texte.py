"""Text normalisation and pattern safeguard (former helpers of Scripts/jutil.py).

The copies of these functions DIVERGED from one program to another: a case-sensitive
comparison here, insensitive there, an accent table that forgot half
the letters. A single version, everywhere.
"""

import re
import unicodedata
from collections.abc import Mapping


# ── Normalisation de texte ───────────────────────────────────────────────────
def sans_accent(s: object) -> str:
    """Lowercase without accents, through NFD.

    Replaces manual tables that forgot half the letters
    ("ë", "ï", "ù", "ü" were not in them).
    """
    s = unicodedata.normalize("NFD", str(s or "").lower())
    return "".join(c for c in s if not unicodedata.combining(c))


def cle(s: str | None) -> str:
    """Comparison key: lowercase, blanks normalised. KEEPS the accents.

    Deliberately distinct from `sans_accent`: this function serves as the
    DEDUP key of the queue. Making it ignore accents would merge
    offers that are distinct today — a change of behaviour, not a
    clean-up. Use `sans_accent(cle(s))` when you want both.
    """
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def verifier_motifs(espace: Mapping[str, object], minimum: int = 1) -> int:
    r"""Refuses to start if a regex of the module carries a corrupted `\b`.

    A word boundary gets corrupted in two ways, both SILENT —
    the pattern compiles, raises nothing, and never matches again:
      \\x08          a \\b passed through a shell heredoc becomes a backspace
      \\\\b (literal) a "fix" of the previous case that escapes the backslash

    `job_sources` had this check, not `ats_match` — and it is `ats_match` that
    had caught it: its `_ESG_TITLE_RX` started with a backspace, so the
    fit cap NEVER lifted for an ESG title. The scoring had been running
    since who knows when with its main rule dead. Hence this shared
    version: a safeguard copied by hand into each module ends up
    missing where it matters.

    Typical call, at the END of the module (globals() must be complete):

        jutil.verifier_motifs(globals(), minimum=6)

    `minimum`: number of patterns expected. If the selection stops finding anything,
    the check would reassure without checking anything — we prefer it to shout.
    """
    import re as _re

    vus = 0
    for nom, val in list(espace.items()):
        if not isinstance(val, _re.Pattern) or not isinstance(val.pattern, str):
            continue
        vus += 1
        assert "\x08" not in val.pattern, f"{nom} : backspace au lieu de \\b"
        assert "\\\\b" not in val.pattern, f"{nom} : antislash litteral au lieu de \\b"
    assert vus >= minimum, f"verifier_motifs ne voit que {vus} motifs (>= {minimum} attendus)"
    return vus
