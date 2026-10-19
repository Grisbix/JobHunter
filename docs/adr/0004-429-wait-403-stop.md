# 0004 — A rate limit is waited out, a refusal of entry is a stop

**Status**: accepted (2026-10-03; LinkedIn on 2026-10-17).

## Context

An empty collection has two opposite causes: nothing to take, or refusal of entry. Retrying them
the same way is exactly what must not be done against a quota.

## Decision

- **429** ("come back later"): pause (`Retry-After`, otherwise a growing wait), then
  the same page is requested again; the state is kept so as to resume from one run to the next.
  Pass duration is bounded (LinkedIn: 45 min).
- **403, 999, CAPTCHA**: refusal. The source stops, with no loop, and does not retry for
  30 days.
- `INCIDENTS` counts the refusals; the collection displays them, so that a throttled scan does not
  look like a quiet day.
- Never a workaround: no IP rotation, no imitated TLS fingerprint, no CAPTCHA
  solving, no "stealth" engine.

## Consequences

Fewer offers on some days, but no lasting block and no sanctioned account.
