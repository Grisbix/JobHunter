# 0003 — File lock, and exit code 3

**Status**: accepted.

## Context

The application, the scheduled pipeline and programs launched by hand can touch the
queue at the same time. A lock broken "because it looks old" once let two
programs write together.

## Decision

- Inter-process exclusion through a `.lock` file (PID and date), reentrant within a single
  process; `rendre_verrou` is not — release only what you took (`tenu`).
- A lock held by a LIVE process is never broken. A recycled PID (a process born
  after the lock) does not count as alive.
- A program that finds the queue busy exits with **code 3** without modifying anything. The pipeline
  and the app know how to display it ("another program is working, retry later").

## Consequences

- No concurrent writes; a blocked program does no damage.
- Every network request goes through the bounded functions of `jobhunter.reseau`, otherwise a slow
  server would hold the lock for hours (seen: 12 h 25, on 2026-09-22).
