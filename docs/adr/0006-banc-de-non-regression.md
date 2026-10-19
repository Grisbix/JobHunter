# 0006 — A non-regression bench before any overhaul

**Status**: accepted, 2026-10-17 (phase 0 of the plan).

## Context

The engine decides which offers get in, their score, the CV variant and the text of the
letter. An overhaul (moving 15,000 lines into a package) must prove that it changes
NONE of these decisions — unit tests do not cover everything.

## Decision

- `outils/banc.py` records, for each offer, all the decisions and the full text of the
  letter and CV (date neutralised), and compares them with a reference.
- CI reference: 384 fictitious offers (`outils/banc_offres.py`), example profile.
- On the real data (11,710 offers, 99 letters and CVs): snapshot before the
  synchronisation, comparison after — at every version.
- File splits are GENERATED from the syntax tree of the original by
  replayable scripts, never retyped.

## Consequences

Every step of phases 3 to 5 shipped with 0 differences. An intended change of decision
is made in a separate commit that re-records the reference and says why.
