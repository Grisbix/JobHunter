# 0001 — The old modules become aliases of the package

**Status**: accepted, 2026-10-18 (phases 3.1 to 3.7). The `Scripts/x.py` aliases are removed in 2.0 ([0008](0008-programs-in-the-package.md)); the package facade (`_facade`) remains.

## Context

The engine lived in `Scripts/`: about a hundred programs that import each other by name
(`import queue_io`, `from job_sources import title_ok`), plus users' personal scripts,
scheduled tasks and the command lines in the README. Moving it into
`src/jobhunter` without breaking all of that required keeping the old names.

A copy of the names (`from jobhunter.stockage.file import *`) would have broken the tests: a
`monkeypatch.setattr(queue_io, "CHEMIN", ...)` would have modified the copy, not the real code —
and a test that believes it is redirecting the queue would write into the real one.

## Decision

- `Scripts/x.py` replaces its entry in `sys.modules` with the package module:
  `import queue_io` **is** `jobhunter.stockage.file`. When run directly, it executes the
  module through `runpy`.
- An old large module that was split up (`job_sources`, `tailor_application`, `web_nav`,
  `JobHunter.pyw`) becomes a package for which `jobhunter._facade` provides a facade: reading a name
  looks it up in the submodules; assigning it goes to the module that owns it; the exit `delattr`
  of `unittest.mock.patch` restores the original value.
- A name that can be set from outside (`KEYWORDS`, `MONDE`, `_get_borne`, theme fonts) is
  never imported by copy into another submodule: it is read there as `_proprietaire.NOM`.

## Consequences

- Nothing changes for callers; `test_coherence_imports.py` checks that every
  `module.nom` used between modules still exists.
- Cost: one level of indirection to understand. The facades disappear once the package
  is installed by `pip` and callers import `jobhunter.*` (phase 6).
