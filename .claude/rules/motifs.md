---
paths:
  - src/jobhunter/scoring/fit.py
  - src/jobhunter/sources/**
  - src/jobhunter/sources/*.py
  - src/jobhunter/scoring/tri.py
  - src/jobhunter/scoring/*.py
  - src/jobhunter/texte.py
---
# Regex patterns — measured traps

**Regexes are not written through a shell heredoc.** `\b` becomes the backspace
character `\x08` or a literal backslash there; the pattern compiles, raises nothing, and
never matches again. Three occurrences in the project's history. Use Write/Edit.

`jutil.verifier_motifs(globals())` runs at the end of the module in `ats_match.py` and
`job_sources.py`: they refuse to start if one of their patterns is corrupted. It
sweeps **every** `re.Pattern` in the module, not only those prefixed `_RX_` — a
safeguard that picks its targets by name ends up missing some.

**Beware of substrings.** The most frequent family of bugs here:
"sin**GAP**ore", "dive**RSE**", "**CLIMAT**isation", "trans**VERSE**",
"**bp** in BPCE".

Conversely, a **trailing** `\b` on a stem kills its inflections: `sustainab\b` does not see
"Sustainability", `alternan[ct]\b` does not see "Alternance".
**Acronyms keep both of their boundaries, stems lose the right-hand one.**
