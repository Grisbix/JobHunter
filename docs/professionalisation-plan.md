# Plan: bringing JobHunter up to professional level

Written on 2026-10-17. The substance is solid (measured and documented bugs, offline tests,
locks, atomic writes, safety rules upheld). This plan deals with **form**:
structure, tooling, testability, typing, distribution.

## Measured starting state (v1.3.2)

| Measure | Value |
|---|---|
| Programs / tests | 70 / 29 files — 28,400 / 4,800 lines |
| Files > 800 lines | `job_sources` 3,921 (90 functions), `web_nav` 3,380, `JobHunter.pyw` 3,281 (one `App` class with 191 methods), `tailor_application` 1,294, `scrape_jobs` 1,026, `site_strategies` 810 |
| Most imported modules | `queue_io` ← 29, `job_sources` ← 21 (also serves as a toolbox: `title_ok`, `_norm`…), `profil` ← 13, `util` ← 12 |
| Direct import cycles | `ats_match`↔`tailor_application`, `job_sources`↔`scrape_jobs`, `util`↔`queue_io`, `message_offre`↔`tailor_application` |
| Side effects at import | 91 module-level calls (profile read, patterns compiled from the profile…) |
| `sys.path.insert` | 57 files |
| Tooling | no linter, formatter or typing; home-made tests (✅/❌), no pytest; system Python |

## Principles

1. **Behaviour unchanged at every step.** A non-regression bench (phase 0) proves it;
   no phase is merged without it.
2. **One module at a time**, one branch and one PR per step, CI green. No big
   rewrite: the documented pitfalls would come back.
3. **Compatibility during the transition**: the old entry points (`Scripts/*.py`,
   `.bat`, scheduled task, `synchro_moteur`) stay as thin facades until the end.
4. **Nothing is added "just in case"**: every abstraction answers a measured problem.

---

## Phase 0 — Safety net (½ day)

Goal: be able to prove that a refactoring changes nothing.

- `tools/bench.py`: on a given queue, computes and records `fit`, `fit_fin`, the triage
  decision, domain, zone, country, and the fingerprint of the text of the letters, CVs and
  messages of a sample of offers. `--comparer` mode: reports any difference. (Takes over the
  bench of the 15/10 migration: 11,341 offers, 99 folders.)
- Two datasets: the **example profile + a fictitious queue** (versioned, run in CI) and
  the **real data** of Recherche_emploi (local only, never published).

Done when: `banc --comparer` reports 0 differences for the current version against itself, in CI.

## Phase 1 — Tooling (1 day) → v1.4.0

- `pyproject.toml`: metadata, bounded dependencies (taken from `requirements.txt`),
  tool configuration. `requirements.txt` stays, generated, for the `.bat` files.
- **uv** + lock file; `.venv` venv for development. The end user
  keeps `install.bat` (which creates the venv instead of installing into the system Python).
- **ruff** (lint + format). Rules `E,F,I,UP,B` first; formatting of all the code in **one
  dedicated commit**, declared in `.git-blame-ignore-revs`.
- **pre-commit**: ruff, line endings, files > 1 MB, secret detection.
- CI: `ruff check`, `ruff format --check`, bench, suites.

Done when: ruff clean, CI green, bench 0 differences, `install.bat` tested on a fresh folder.

## Phase 2 — Tests under pytest (1 to 2 days) → v1.4.x

- Immediate step: `tests/test_suites_historiques.py` runs each current suite as a
  (parametrized) pytest test — everything passes under `pytest` from day one.
- `conftest.py`: fixtures `profil_exemple`, `file_temporaire`, `suivi_temporaire`,
  `faux_reseau` (replaces the `_get_borne` doubles), simulated clock and `sleep`.
- Conversion suite by suite, from the smallest to the largest: each `check()` becomes a
  function or a `parametrize` case; assignments to globals (`J.KEYWORDS = …`)
  become `monkeypatch`, restored after each test.
- `pytest-cov`: coverage measured, threshold = starting value, which must no longer drop.

Done when: all suites converted, `pytest -q` in < 2 min, coverage published in CI.

**Done on 2026-10-18.** The 27 suites converted case for case: 1,142 tests (one of which reads
real data, marked `donnees_reelles`), a safeguard against any new suite
in `Scripts/`. Coverage 31% of the engine (test files excluded), threshold 30 in CI.
Found while converting: checks that checked nothing (idempotence of
`titre_poste` in test_titres, a hard-coded `True` case in test_web_nav), about ten
suites that modified engine globals (`time.sleep`, `urlopen`, `httpx.Client`,
paths, keys) for the whole process without restoring them, and a "mocked network" test that
actually queried the web (80 s) and could write to the `homepages.json` cache. Duration:
~80 s, ~2 min 30 with coverage.

## Phase 3 — Package and split (1 to 2 weeks, by PR) → v2.0.0

Target structure:

```
src/jobhunter/
  storage/     verrou.py, atomique.py, file.py (queue_io), suivi.py, descriptions.py
  profil.py     Profil object (loaded once, passed as a parameter)
  network.py     HTTP client: time limits, pauses, 429 awaited, 403 = stop, incidents
  scoring/      fit.py (ats_match), langue.py, zones.py, tri.py, domaines.py
  sources/      commun.py (title_ok, normalisation, merge), linkedin.py, ats/<lecteur>.py,
                workday.py, efc.py, eures.py, apec.py, agregateurs.py, sites_carriere.py
  documents/    letter.py, cv.py, message.py, cv_auto.py, paths.py, rendering.py (docx/pdf)
  navigation/   web_nav split up: navigateur.py, formulaires.py, ats_detect.py, strategies/
  candidature/  apply_runner.py, relances.py, suivi.py
  app/          JobHunter split into views: table.py, fiche.py, journal.py, maintenance.py,
                update.py, theme.py
  pipeline.py   daily_pipeline
  cli.py        `jobhunter <command>`: collecte, tri, documents, postuler, pipeline, maj…
```

Order (from the leaves to the dependents, one PR each):

1. `storage/` — breaks the `util`↔`queue_io` cycle.
2. `profil.py` + `network.py`.
3. `scoring/` — takes `titre_poste()` and the common vocabulary out of `tailor_application` to
   break `ats_match`↔`tailor_application`.
4. `sources/` — splits `job_sources` (3,921 lines) by source; its shared utilities
   go into `sources/common.py`, which breaks `job_sources`↔`scrape_jobs`.
5. `documents/` — splits `tailor_application`, breaks `message_offre`↔`tailor_application`.
6. `navigation/` — splits `web_nav` (3,380 lines) and `site_strategies`.
7. `app/` — the `App` class (191 methods) becomes an assembly of views.
8. `cli.py`; the `.bat`/`.sh` files call `jobhunter …`.
9. Removal of the `Scripts/*.py` facades (last PR, after a complete cycle of the real pipeline).
   **1.15.0 bridge**: the engine, the tests and the application no longer import the
   facades; above all, `update` checks the installed version with ITS OWN code
   (`python -m jobhunter update --controler`). Without it, any 1.x installation would refuse
   2.0: its check imported `queue_io`, `job_sources`… by their old names. 1.15
   must therefore precede 2.0; an earlier installation that jumped straight to
   2.0 would be rolled back to its version (nothing is lost) — go through 1.15.

**Progress**: 1 to 8 done on 2026-10-18 (v1.5.0 to v1.12.0), bench 0 differences at each step.
`sources/` kept the sources as flat modules (`ats.py` brings together the ATS readers and the
"other APIs", which called each other); `sites_carriere` stays in `scrape_jobs`. `documents/`: `commun`, `cv`, `lettre`, `llm`,
`rendu`, `message`, `cv_auto`; `paths` stayed `jobhunter.paths` (shared with scoring). `navigation/`: one section
of `web_nav` per module, no cycle (checked by a test that loads each one alone). `app/`: the `App` class assembles one
mixin per domain (methods copied as they were); the first launch is `jobhunter.welcome`. `cli`: `python -m jobhunter <command>` routes
to the programs; the `.bat`/`.sh` files will move over to it with the installation (phase 6).

Done when: `pip install -e .` then `jobhunter pipeline` works; no
`sys.path.insert`; no cycle (checked in CI by `import-linter`); bench 0 differences at each PR.
*(Correction of 2026-10-19: `import-linter` was never wired in. Cycles are
checked package by package by the `test_*_paquet.py` tests; the rule "the engine
does not import the interface" is step B1 of [the roadmap](roadmap.md).)*

**Criteria met (2026-10-19, v2.4.1)**: the eight transitional `sys.path.insert(Scripts/)`
calls, forgotten when the facades were removed, are removed (no import went through them any more,
but they put the DATA folder at the head of the import path). `tests/test_architecture.py`
now checks that the engine imports neither Tkinter nor `jobhunter.app`, and that no
module touches `sys.path`; only `JobHunter.pyw` adds `src/`, outside the package.

**Done (2026-10-18, v1.15.0 then v2.0.0)**: 3.9 in two stages. The 1.15.0 bridge
(above) was published and tested on its own (ZIP update 1.14 → 1.15). 2.0.0 moves
the 57 programs of `Scripts/` into `jobhunter.programs` (`git mv`, history kept),
removes the 14 facades; `Scripts/` keeps only the data ([ADR 0008](adr/0008-programs-in-the-package.md)).
`JobHunter.pyw` is the only `sys.path.insert` (to launch without installation). Merged
after a complete cycle of the real pipeline on the previous code.

## Phase 4 — Side effects, configuration, logs (2 to 3 days, together with phase 3)

- **No file or network read at import** (91 calls today). The patterns
  that depend on the profile are compiled by the `Profil`, not when the module is loaded.
- `Profil`, `ClientHttp` and paths **injected** as parameters: the tests build what
  they need, without patching globals.
- **`logging`** throughout the engine (levels, common format, one file per pipeline
  run); `print` reserved for CLI output. `INCIDENTS` becomes a counter carried by
  `ClientHttp`.

Done when: `python -c "import jobhunter.sources.linkedin"` reads no file.

**Progress (2026-10-18, v1.13.0)**: import no longer writes anything (three folders were
created at load time) and opens no connection — checked by
`tests/test_import_side_effects.py`, a ratchet.

**Done (2026-10-18, v1.14.0)**: import no longer reads any file. The ~110 values
drawn from the profile and from `chemins.json` are computed on first read
(`jobhunter.lazy`, [ADR 0007](adr/0007-lazy-profile-values.md));
`profil.utiliser()` injects an in-memory profile, `profil.recharger()` goes back to the
file. `logging` (`jobhunter.log`) replaces the 80 `print` calls in the engine functions,
with the same console output and one timestamped file per pipeline run.
`INCIDENTS` lives in `jobhunter.network`, next to the HTTP client. Not done, on purpose:
passing `ClientHttp` and the paths as a parameter of every function — the tests already
replace them without hidden globals (`_get_borne`, `CHEMIN`), and the change
would touch every signature for nothing measurable.

## Phase 5 — Typing (ongoing, from phase 3)

- Annotations on all public functions. `Offre` and `Candidature` as `TypedDict`
  (the JSON does not change), then `dataclass` where useful.
- **mypy** in CI: strict on `storage/`, `profil.py`, `network.py`, `scoring/`; non-strict
  elsewhere, tightened module by module.

Done when: mypy strict on the core, no `# type: ignore` without a comment.

**Progress (2026-10-18, v1.13.0)**: mypy in CI on the whole package; strict on the base layer
(`stockage`, `profil`, `network`, `root`, `texte`, `liens`, `types`) and on all of
`scoring` (+ `paths`, `_facade`): the completion criterion is reached. What remains, ongoing,
is the `TypedDict`s of `Offre` and `Candidature`, and the tightening of the other packages.

**Progress (2026-10-19)**: `Offre` and `Candidature` are non-total `TypedDict`s
(all keys optional: an offer is built in stages), inventoried on a real queue
of 12,137 offers and on the keys the code reads or writes. `cli`, `welcome` and
`update` join the strict list. Measured for what comes next, in strict-mode errors:
`documents` 187, `navigation` 175, `sources` 395, `app` 1,024, the programs ~85.
Then `documents.rendu`, `llm`, `commun`, `cv_auto` and `cv` become strict (bench 0 differences);
then `lettre` and `message`: **all of `documents` is strict**, then **all of `navigation`**
(Playwright objects typed `Any`: `page.evaluate` returns Any anyway), then **all of
`sources`**, then **all of `app`**: a generated `Protocol` (`app/_app_type.py`) declares what
each mixin sees of `self` — a name that is read and defined nowhere becomes an error, but the
types there remain `Any` (to be made precise attribute by attribute). Finally the **programs** are
no longer excluded: checked in normal mode (82 errors cleared), their functions mostly remaining
unannotated. **The whole package passes mypy**; strict covers everything except the programs. Lesson: a variable
rename that mypy judged correct broke `contrat_de_la_description` (32 differences in the bench, no
test) — the bench stays mandatory even for typing.

## Phase 6 — Distribution (1 day) → v2.x

- JobHunter installable: `pip install git+https://github.com/Grisbix/JobHunter@v2.0.0`.
- Recherche_emploi **depends on** a tagged version instead of copying the engine:
  `synchro_moteur.py` is removed; the repository keeps only profile, data and personal scripts.
- A single source of version (`pyproject.toml`, read by `update`).
- **1.3.x → 2.0 upgrade test** on a real ZIP install and a real clone: the
  restructuring moves dozens of files (the update removes the old ones when untouched,
  keeps the modified ones — to be checked for real, as for 1.3.0).

**Progress (2026-10-18, v1.13.0)**: `src/jobhunter` builds as a wheel (checked in CI)
and installs; the `jobhunter` command works from a fresh venv, the programs still
in `Scripts/` via `JOBHUNTER_RACINE`. What remains, and it depends on the removal of the facades
(3.9): Recherche_emploi depending on a tagged version instead of `synchro_moteur`, and
the 1.x → 2.0 test. `VERSION` stays read by the update as long as 1.x installations
exist (CI checks that it equals `pyproject.toml`).

**Done (2026-10-19, v2.0.0 and v2.1.0)**: real 1.15 → 2.0 upgrade verified on a ZIP
installation and on a git clone (`Scripts/` emptied of its `.py` files, VERSION 2.0.0, commands
and check OK). Recherche_emploi depends on the installed package at a tagged version
(`pip install "jobhunter @ git+…@v2.1.0"`); `synchro_moteur` and the copies of the engine are
removed there. Bench on its data: 0 differences over 12,137 offers and 99 letters/CVs (1.14 against
2.1, same queue). Remaining, postponed: the test on a fresh Windows and on a Mac.

## Phase 7 — Data (optional, later)

- SQLite behind the `storage/` interface (unchanged): transactions, indexes, no more
  file lock or full rewrite. JSON → SQLite migration script, JSON export
  kept. To be started only if volume or concurrent access justify it.

## Phase 8 — Documentation (ongoing)

- Narrative comments become short **ADRs** (`docs/adr/NNNN-titre.md`: context,
  decision, consequence); the code keeps one or two lines and the link.
- `docs/architecture.md` (diagram of the packages and the pipeline), `CONTRIBUTING.md`
  (install, test, publish), Google-style docstrings on the public API.

**Progress (2026-10-18, v1.13.0)**: `docs/architecture.md` and six ADRs (facades, data,
lock, 429/403, no submission, bench). Remaining: the Google docstrings and the
gradual replacement of narrative comments by references to the ADRs.

**Progress (2026-10-19)**: Google-style docstrings (Args, Returns, Yields, Raises)
on the whole public API of the base layer — `stockage` (file, suivi, verrou, atomique), `profil`,
`root`, `network`. Ruff now requires them on these files (rule `D`, google
convention); a module joins the list once documented, as with strict mypy.

**Progress (2026-10-19, continued)**: the eight ADRs are cited in the code, at the end of the
docstring of the modules where each decision applies (14 modules). `tests/test_adr.py`
guards the link in both directions: an ADR that nothing cites, or a citation of an ADR
that does not exist, fails the suite. Remaining, as time allows: shortening the narratives that the ADR
already covers — one passage at a time, because it is a judgement call, not a substitution.

**Done (2026-10-19, v2.4.2)**: Google-style docstrings on **the whole public API**
of the package. This required:
- writing 37 public functions that had none;
- isolating the summary of 84 docstrings, with an automatic check that the words remain
  identical.

Ruff (`D`, google convention) requires them everywhere. Exempt are the programs
(`jobhunter.programs`, command lines) and the window (`jobhunter.app`, interface
mixins).

Narratives: only one repeated an ADR (the 403/CAPTCHA refusal in `availability_audit`), reduced to a
line and the link. The others tell a measured bug, specific to their function ("cut off at
45 min every day from 08 to 18/10"…): they stay in the code, that is their place. An
ADR decides; the narrative says why a given line exists.

---

## Indicative schedule

| Week | Phases | Version |
|---|---|---|
| 1 | 0, 1, 2 (immediate step) | 1.4.0 |
| 2 | 2 (conversion), 3.1–3.3, 4 in parallel | 1.4.x |
| 3–4 | 3.4–3.9, 5 on the core | 2.0.0 |
| 5 | 6, real upgrade test, 8 | 2.0.x |
| later | 7 if needed | — |

## Risks and countermeasures

| Risk | Countermeasure |
|---|---|
| Silent regression of scoring or documents | Phase 0 bench, mandatory at every PR |
| Scheduled task, `.bat`, app broken by the moves | Facades until the end of phase 3; one complete real pipeline run before removing them |
| 1.3 → 2.0 update that breaks a user's install | Real ZIP + git test before publication; automatic rollback already in place |
| Recherche_emploi out of sync during the refactoring | It stays on 1.3.x until 2.0; urgent fixes backported |
| Refactoring that drags on | Each PR delivers on its own and leaves everything green; we can stop after any of them |

---

## After the plan: applying from the application (2.2.0, 2026-10-19)

First workstream of the follow-up proposed by Codex (note of 18/10). The Candidatures panel
drives `apply_runner --pilote`; after "J'ai envoyé" ("I have sent it"), the page is observed and the tracking
receives `envoi` (confirmed / uncertain / declared) and `preuve` (proof)
([ADR 0009](adr/0009-proof-distinct-from-declaration.md)). The send click remains
human; no command of the protocol clicks. Possible follow-ups, from the same document:
ranking evaluated on real judgements, a more robust offer identity, yield per
source, check of the final PDF.

**2.3.0 (same day)**: second axis, "documents checked down to the final file".
`jobhunter.documents.checks` checks the files that will really go out (readable PDF with
text, one page, profile contact details, no empty template); a folder to review is
flagged in the panel, the sheet and the routine (step 5b). Found along the way: 22 offers
pointed to the .docx letter although its PDF was next to it — the up-to-date PDF is what
now goes out.

**2.4.0 (same day)**: third axis, "a measurable yield for every connector".
`jobhunter.sources.source_yield` measures each source call (duration, items returned, incidents of
THAT call), the merge counts new and relevant offers per source; verdict ok / nothing to pick up /
limited / partial / refused. Log `Scripts/_rendement.jsonl`, summary
`jobhunter yield`. Not measured for now: full descriptions and employer
links per source (they arrive at later pipeline steps, not at collection).

**Next**: [roadmap after the plan](roadmap.md) (2026-10-19).
