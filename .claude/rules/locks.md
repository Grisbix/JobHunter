---
paths:
  - src/jobhunter/programmes/jutil.py
  - src/jobhunter/stockage/*.py
  - src/jobhunter/reseau.py
  - src/jobhunter/sources/**
  - src/jobhunter/sources/*.py
  - src/jobhunter/programmes/linkedin_desc.py
  - src/jobhunter/programmes/pipeline_quotidien.py
  - src/jobhunter/programmes/audit_dispo.py
---
# Locks, exit code 3, bounded requests

`jutil.prendre_verrou` / `rendre_verrou` / `garder` implement a file-based
inter-process exclusion, which breaks the lock of a dead process. Project convention:
**a program that finds the queue busy exits with code 3 without modifying anything.**

`prendre_verrou` is reentrant, `rendre_verrou` is not. A function that takes then
releases, while its caller held the lock for the whole program, takes it away from the caller.
`jutil.tenu(chemin)` answers before taking.

**A live lock is not broken.** `perime` (30 min) now applies only to a lock
whose owner cannot be read. As long as the recorded PID is running, we wait, then
the caller exits with code 3. Before 2026-09-23, age was enough: a three-hour job
had its lock broken after thirty minutes, by a program that then went on to
write over it.

**Windows recycles PIDs.** "Alive" means: the PID exists AND the process was born
before the lock (`GetProcessTimes` against the file's timestamp). On 2026-10-02, the
PID of a dead collection was reassigned to the Chrome extension: the orphan lock
passed for held, and every collection exited with code 3.

**`job_sources.main()` holds two locks, for two roles.** The lock on
`offres_scan.json` lasts the whole collection: there is only one scan at a time. The one on
`apply_queue.json` is taken only for the merge, for a few seconds, with a
wait of 30 min instead of 3. If the merge fails anyway, the collection is already
written to `offres_scan.json`, and `--fusion-seule` merges it again without rescanning.
Until 2026-09-23, the queue was locked for the entire scan, i.e. over an hour.

**A long job writes in batches.** `linkedin_desc.py` collects outside the lock and writes
in packets of 500. A stop costs only the batch in progress.

**An httpx `timeout=` bounds each packet, not the request.** A server that trickles one
byte every 19 s holds the connection indefinitely. On 2026-09-22, fr.talent.com
blocked the scheduled scan this way for 12 h 25. In `job_sources`, **every** request goes
through `_get_borne` / `_post_borne` (total duration, a real `httpx.Response`) and every `urlopen`
through `_lire_borne` — which reads with `read1`, because `read(n)` waits for the buffer to be
full before handing control back. `pipeline_quotidien.etape()` additionally kills any step that
exceeds its maximum duration — **the process tree** (`taskkill /T`), without which a child
that keeps the output open prolongs the step — without killing the pipeline. The 20 h watchdog
reads the pipeline's log.
