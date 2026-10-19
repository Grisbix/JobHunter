# 0008 — All the code in the package; `JobHunter.pyw` launches without installation

**Status**: accepted, 2026-10-18 (phase 3.9 and phase 6 of the plan, version 2.0).

## Context

After phase 3, the engine lived in `src/jobhunter`, but 57 programs remained
in `Scripts/` (pipeline, documents, application, audits, probes), next to 14 facades
that kept the old names (`job_sources`, `queue_io`…) and 55 `sys.path.insert` calls.
The package alone was therefore not enough to run JobHunter: a repository that wanted to
depend on an installed version still had to copy `Scripts/`.

Two constraints:

- ZIP installations (without `pip install`) must keep working, even
  if the folder is moved — hard-coded roots have broken four times.
- A 1.x installation updates itself with ITS OWN `mise_a_jour`, which checked the new
  tree by importing its own names (`queue_io`, `job_sources`…): removing the facades
  would have made every 1.x roll back 2.0.

## Decision

- The programs move into `jobhunter.programmes` (names unchanged); the facades and
  all the `sys.path.insert` calls in the code disappear. `Scripts/` keeps only the data.
  Data paths come from `jobhunter.racine`, no longer from `__file__`.
- The move was GENERATED (git mv + import rewriting via the syntax tree,
  same local name, hence same object) and checked by the bench: 0 differences.
- `python -m jobhunter <commande>` launches a named command (`collecte`, `pipeline`…)
  or any program by its name (`probe_ats`).
- **Without installation**, `JobHunter.pyw` is the entry point: with no argument the application, with
  arguments the command line. It is the only file that adds `src/` to the import
  path (computed from its own location); the `.bat`/`.sh` files and the scheduled
  task go through it. Steps launched as subprocesses inherit
  `PYTHONPATH` (`racine.exporter_paquet()`).
- **Installed by pip**, the package finds the data folder through `JOBHUNTER_RACINE`
  or by walking up from the current folder.
- **Bridge 1.15.0**: `mise_a_jour` checks the installed version with its code
  (`python -m jobhunter maj --controler`). 1.15 must precede 2.0; an
  older 1.x that jumped straight to 2.0 would be brought back to its version, with no
  loss.
- The post-update check flags a scheduled collection that still targets
  `Scripts/pipeline_quotidien.py` (to be recreated with `planifier.bat`/`planifier.sh`).

## Consequences

A data repository (like the author's) can depend on a tagged version
(`pip install "jobhunter @ git+https://github.com/Grisbix/JobHunter@v2.0.0"`) instead of
copying the code. The programs are not typed yet (excluded from mypy, to be worked off).
The historical names (`job_sources`…) remain as local aliases in the code
(`from jobhunter import sources as job_sources`): a rename would be another project.
