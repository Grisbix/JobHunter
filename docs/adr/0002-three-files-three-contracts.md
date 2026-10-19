# 0002 — Three data files, three access contracts

**Status**: accepted (2026-09, taken up again in phase 3.1).

## Context

Thirteen programs rewrote `apply_queue.json` in full to change one field, with no
lock: changes were lost. Offer descriptions made up 64 % of the
file. And `suivi.json`, the only data no scan can recover, was written from a
memory snapshot: an "applied" ("postulé") click in the app erased the follow-ups noted in the meantime.

## Decision

- **Queue**: read through `stockage.file.charger()` (no lock, since writes are
  atomic); written only through `transaction()` — lock, fresh re-read INSIDE
  the lock, atomic write on exit, rollback if the block raises.
- **Descriptions**: a side file, injected back and written out again by the storage layer, invisible to
  callers. `transaction(descriptions=False)` avoids reading it.
- **Tracking**: `stockage.suivi.poser()` writes an entry onto the state re-read under lock.
- Never a direct `json.load` / `json.dump` on these files.

## Consequences

- No more silent loss; the queue weighs a third of its former size.
- Every automatic deletion must spare the offers present in the tracking file.
- Trap fixed in 1.9.0: paths are compared resolved — `Path("apply_queue.json")`
  from `Scripts/` lost the descriptions.
