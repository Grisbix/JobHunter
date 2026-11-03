# 0016 — The queue in SQLite, the tracking file stays JSON

Date: 2026-11-03. Status: accepted (3.77).

## Context

Since ADR 0002 the queue was two JSON files: `apply_queue.json` (the offers) and
`descriptions.json` (their text, 64 % of the weight). Two atomic files do not make one
transaction: `sauver` needed a three-step order (annex additions, queue, purge) so a
failure between two writes lost no description, and every write rewrote the whole
queue (~3 MB) to change one field. The audit of 19/10/2026 and the one of 29/10 each
found a way to lose descriptions through that order.

## Decision

- The queue lives in `queue.sqlite3`, next to where `apply_queue.json` was: a table
  `offres` (rank, oid, the offer as JSON without its description) and a table
  `descriptions` (oid, text). One write is ONE SQLite transaction, and only the rows
  that changed are written. Orphan texts are those whose oid is no longer in `offres`,
  read from the table itself: a write that did not load the texts cannot erase them.
- The public API of `storage.queue` does not change (`charger`, `transaction`,
  `modifier`, `sauver`, `oid`); `CHEMIN` keeps naming `apply_queue.json`, the queue's
  identity and the lock file's name. The cross-process file lock (exit code 3) stays:
  it orders whole read-modify-write cycles, which SQLite's own locking does not.
- Migration at the FIRST WRITE of 3.77, under the lock: a read never changes the data
  folder. The database is built under a temporary name then renamed into place; the
  JSON files are kept as `*.avant_sqlite`; the data format goes to 2, so a 3.76 that
  would read an empty queue refuses to write.
- A 2.x folder (`Scripts/`) stays JSON until its migration to 3.0, which rewrites the
  document links inside `apply_queue.json`.
- The backups stay JSON (`queue.exporter`): daily copies, before an audit, before a
  restoration, before the sort. `jobhunter restore` and `reposts` read every day alike.
- `applications.json` stays JSON: small, versioned by git in the user's folder by
  design, and read by hand.

## Consequences

- Any code that touched `apply_queue.json` as a file goes through `storage.queue`:
  `existe()` instead of `.exists()`, `fichier()` for a modification time,
  `exporter()` for a copy. `jwrite` on THE queue is routed to `sauver`.
- A JSON queue written by hand next to the database is ignored (the database wins);
  to put one back, use `jobhunter restore`.
