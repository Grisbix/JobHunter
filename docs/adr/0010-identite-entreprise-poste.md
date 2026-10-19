# 0010 — An offer's identity stays "entreprise|poste"; we repair what it loses

**Status**: accepted on 2026-10-19 (study C2 of the roadmap, JobHunter 2.6.0).

## Context

An offer's identity is `entreprise|poste` (`queue_io.oid`). It is also the key of
`suivi.json`, the least reconstructible data in the project: a lost application does not
come back. Codex proposed studying a more robust identity; the study measured what
the current key actually loses.

1. **Same position in several cities.** Out of 86 offers drawn from real replayed responses
   (`tests/reponses/`), **12 share their key** with another one in a different location. For
   example: Forvis Mazars in Düsseldorf, Mannheim, Hamburg and Frankfurt, or Alan in Dakar
   and Abidjan. The scan's deduplication kept the first one seen, depending on arbitrary order: the
   wanted city could be lost in favour of another that the location filter then
   discarded.
2. **Same posting under two keys.** In a real queue of 12,169 offers, 9 posting URLs
   carry 2 or 3 keys. The causes:
   - an employer who tweaks its job title (Qonto: three titles for a single Lever
     posting);
   - a renamed feed ("PwC France", then "PwC", same Workday link).

   The merge already attaches by URL the offers it receives (checked): these are old
   duplicates that nothing brought together.

No case forces a change of key, and changing it would migrate the tracking file for an
unproven gain.

## Decision

- **The key stays `entreprise|poste`.** No migration of the tracking file.
- **Several cities**: the scan's deduplication (`sources.cli.dedoublonner`) keeps
  the copy from the best zone of the profile. The order is primary, secondary, rest
  of France, international, then unknown; on a tie, the first seen wins, as
  before. The other cities go into `autres_lieux`, displayed by the card ("Aussi à :" (Also in:)).
- **Same posting URL**: `doublons` brings together the offers that share a URL designating
  a posting, that is, one with a numeric identifier, a UUID or an offer path.
  A generic careers page never unites two positions. The triage removes the duplicates
  every day.
  - It keeps the tracked offer (never removed), then the best source, the language, and
    **the version the source still serves** (`vu_le`), hence the current title.

## Consequences

The Paris position is no longer lost behind its Berlin twin, and tweaked titles
no longer pile up. Two cases remain out of reach, with no harm to the
tracking file:
- two **truly distinct** positions with the same title and the same city, which the key
  confuses. None has been observed;
- a posting republished under a **new URL** and a new title.
