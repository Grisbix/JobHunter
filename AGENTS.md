# AGENTS.md

Instructions for any coding agent working on this repository. Single source:
`CLAUDE.md` is only a one-line import of this file.

Language: documentation, comments and docstrings are in English; identifiers, profile keys and JSON keys stay in French (renaming them would break users' profiles and data). The user-facing French README is README.fr.md.

## Shared version: the engine knows nobody

Everything SPECIFIC TO THE PERSON lives in `profil/profil.json`, read by
`src/jobhunter/profil.py`: identity, target jobs (`domaines`), skills, scoring axes and
caps, title filters, level, families removed by the triage, zones, collection keywords,
texts of the letters and messages. **No module hard-codes a job, a city or a name.** To
change target, change the profile.

- Create the profile: `python -m jobhunter profil <cv.pdf|docx>`.
- Full reference profile: `profil/exemple_finance_esg.json` (junior in sustainable
  finance). **All the tests** run on it — `_profil_test.py`, imported at the top of every
  `test_*.py`, forces `PROFIL_JOBHUNTER` to this file.
- A word list in the profile accepts `"mot"` (bounded on the left) or `"re:motif"` (taken
  as is). `profil.motif()` compiles them.
- User guide: `README.md` (English) and `README.fr.md`. Setup through Claude Code: `/configure-profile` (`.claude/commands/configure-profile.md`).
- Double-click tools (`lanceurs/`, each one `cd`s to the folder above): `installer.bat`,
  `lancer.bat` (CV taken from `Mon_CV/`), `planifier.bat` (daily scheduled task),
  `mettre_a_jour.bat` (and their `.sh` twins for macOS/Linux). The update:
  `src/jobhunter/programmes/mise_a_jour.py` (git pull, or GitHub
  ZIP file by file: data never touched, modified file kept + `.nouveau`,
  removed file deleted if intact, load check then automatic rollback,
  `--annuler`). **At every release: bump `VERSION`, add its section at the top of
  `CHANGELOG.md`, and create the `v<version>` release** — the tag is the reference for the
  first update of a ZIP installation (without it, a file modified by the user cannot be
  recognised).
- `langues_parlees` (profile): a posting written in another language is capped at 2, a
  required language at 4 (`ats_match.plafond_langue`).
- CI: `.github/workflows/tests.yml` runs the network-free suites on every push.

## Read before touching the code

**`docs/programs.md`** — what each program does, and above all its final section
"Code pitfalls, learned the hard way". Each pitfall there is a real, measured bug, with
its symptom. Do not rediscover these bugs. `README.md` at the root is addressed to the
user; the history of changes is in the commit messages.

## Commands

```bash
# The application — daily entry point, at the root
python JobHunter.pyw

# Collection + merge into the queue (see --help: ~20 sources that can be enabled separately)
python -m jobhunter collecte --all
python -m jobhunter collecte --linkedin --apec --efc
python -m jobhunter collecte --efc --efc-sites monde --eures   # abroad: eFC ×9 sites, EURES

# Documents: CV + letter per offer
python -m jobhunter documents --top 30
python -m jobhunter documents --all --dry
python -m jobhunter regenerer --cv        # regenerates existing documents after a template change
python -m jobhunter cv-auto --liste           # fact bank of the automatic CV (CV/Faits.json)
python -m jobhunter documents --url <extrait>   # redoes CV and letter of one offer

# Closed offers: check (LinkedIn guest API, 404/410) then removal, automatic resume on 429
python -m jobhunter dispo --supprime
python -m jobhunter dispo --rapport     # status report, no network

# Semi-automatic application — IN A REAL TERMINAL, it waits for the keyboard
python -m jobhunter postuler --canal linkedin
```

### Tests and checks

```bash
uv sync                                  # .venv, pinned versions (uv.lock)
uv run pytest -q                         # 1,142 tests without network (~2 min)
uv run pytest -q tests/test_scoring.py   # one file; -k word to filter cases
uv run pytest -q --cov --cov-report=term # with coverage (threshold in CI)
uv run python outils/banc.py comparer outils/banc_reference.json   # non-regression
uv run ruff check . && uv run ruff format --check .
```

**The non-regression bench** (`outils/banc.py`) records what the engine decides on
384 fictitious offers — title filter, fit, fit_fin, domain, triage, zone, country, contract,
language, message, and the text of letters. It must stay at **0 differences** on every
commit. If a change of behaviour is intended, regenerate the reference (`banc.py enregistrer …`)
**in the same commit**, and say why in the message.

**The tests live in `tests/`**, in pytest (the 27 old suites of `Scripts/` were converted
there on 2026-10-18, case for case). `tests/conftest.py` sets the example profile
BEFORE any import of the engine and provides the fixtures: `faux_reseau` (double for
`_get_borne`/`_post_borne`), `horloge` (simulated time and pauses), `file_temporaire` and
`suivi_temporaire` (throwaway queue and tracking file), `navigateur`/`page` (one headless Chromium per
session, a fresh page per test). **Never assign an engine global directly
in a test: use `monkeypatch`**, otherwise state leaks from one test to the next. A test that reads
a user's real data carries the `donnees_reelles` mark and runs only on
demand (`pytest -m donnees_reelles`). `tests/test_pas_de_suite_historique.py` refuses any
program in `Scripts/`. `programmes/test_live_nav` and `programmes/test_acces_sites`
really go out on the web — outside pytest, do not run them mechanically.

`test_scoring` generates a "no backspace" case **per pattern of the module**: adding a
pattern to `ats_match` raises its count without any test having been written.

## Architecture

### The `src/jobhunter` package (2.0: all the code is there)

`Scripts/` keeps only the data; the code lives in `src/jobhunter`
(`docs/professionalisation-plan.md`):

| Package | Contents (former name) |
|---|---|
| `jobhunter.stockage` | `atomique`, `verrou`, `file` (`queue_io`), `suivi` (`suivi_io`) |
| `jobhunter.scoring` | `fit` (`ats_match`), `langue`, `zones`, `tri` (`tri_file`), `lexique`, `domaines` |
| `jobhunter.sources` | `job_sources`: one source per module, `commun`, `fusion`, `cli` — assignment routed to the owner |
| `jobhunter.documents` | `tailor_application` (`commun`, `cv`, `lettre`, `llm`, `rendu`), `message` (`message_offre`), `cv_auto` |
| `jobhunter.navigation` | `web_nav`: one section per module (`page`, `carrieres`, `formulaires`…), `strategies` (`site_strategies`) |
| `jobhunter.app` | `JobHunter.pyw` (now a launcher): `fenetre.App` = one mixin per domain, `theme`, `commun` |
| `jobhunter.programmes` | the ~57 programs (former `Scripts/*.py`): `pipeline_quotidien`, `generate_docs`, `apply_runner`, `audit_dispo`, `jutil`… |
| `jobhunter` | `racine`, `profil`, `reseau` (bounded requests), `chemins`, `texte`, `liens`, `accueil`, `cli` (`python -m jobhunter <commande>`) |

One-way dependencies, checked in tests (cycles `jutil`↔`queue_io`, `ats_match`↔`tailor`,
`job_sources`↔`scrape_jobs` broken). A split package sees the names of its submodules
(`_facade`): `jobhunter.sources.title_ok` works. Without installation, `python JobHunter.pyw
<commande>` runs everything (it is the only file that adds `src/` to the path); installed
(`pip install -e .`), `python -m jobhunter <commande>` or `jobhunter <commande>`.
`test_coherence_imports.py` checks that every `module.nom` used between modules exists.

### Three data files, three access contracts

```
Scripts/apply_queue.json    the offers          → go through queue_io
Scripts/descriptions.json   their text, apart   → queue_io reinjects it, transparently
Scripts/suivi.json          the applications    → go through suivi_io
```

**Never read or write these files with a direct `json.load`/`json.dump`.**

- `queue_io.charger()` reads without a lock (writes are atomic, so a read never sees a
  half-written file) and reinjects the descriptions.
  `queue_io.transaction()` is the only write path: lock, **fresh re-read inside the
  lock**, atomic write on exit, rollback if the block raises.
- The descriptions live apart because they weighed 64% of the file that thirteen
  programs rewrote in full to change a single field. `transaction(descriptions=False)`
  skips reading them when only a `fit` or a status is touched.
- `suivi.json` is the project's **least reconstructible** data: a lost offer is found
  again by the scan tomorrow; a lost application never comes back. `suivi_io.poser()`
  writes one entry under lock on the re-read state — never a memory snapshot.
- **Only `suivi.json` is versioned.** The queue, the descriptions and the scans have been out of
  git since 2026-09-23: `pipeline_quotidien.sauvegarder()` copies them every day into
  `Scripts/_sauvegardes/<date>/`, before any step, seven rolling days. The generated
  documents have been out of git since 20/09; the complete history from before the purge, 978 MB,
  is in `../_sauvegardes/Recherche_emploi_historique_complet_2026-09-23.bundle`.

The identity of an offer is `queue_io.oid(offre)` = `"entreprise|poste"`. Never the
URL: it changes when a better-ranked duplicate promotes it.

### The lock, and exit code 3

Inter-process exclusion by file (`jutil.prendre_verrou` / `rendre_verrou` / `garder`).
**A program that finds the queue busy exits with code 3 without modifying anything.** A
live lock is never broken; every network request goes through the bounded functions.
Details (reentrancy, recycled PIDs, double lock of `job_sources`, httpx timeouts):
`.claude/rules/locks.md`.

**The pipeline collection runs in five passes, each merged** (ATS/Workday/V.I.E;
LinkedIn; eFC/EURES; APEC/France Travail/Adzuna/Jooble; Glassdoor/WTJ last).
Talent and Indeed have been out of `--all` since 2026-10-03 (0 offers, 403); Adzuna and
Jooble go through their official API, key in the files adzuna.json / jooble.json of the Scripts folder
(ignored by git, to be created by the user; absent = source ignored).
`job_sources` only merges at the end of its pass: in a single `--all` pass, an
overrun lost the whole day's collection — four mornings out of five from 24 to
28/09/2026; with three passes, two still overran on 30/09.

**`_req_borne` reuses connections.** Called with the `httpx` module, it goes through a
shared `httpx.Client`: reopening a TLS connection per request tripled the duration
(talan 8 min → 1.7; a Workday feed 7.8 → 1.6). Talent no longer reloads the postings already
in the queue.

**A rate limit is waited out, a refusal of entry stops.** A 429 says "come back later":
`audit_dispo` pauses (Retry-After, otherwise 15 min doubled up to 60),
resumes where it stopped, and keeps its state in `_audit_dispo.json` to resume
from one run to the next. A 403/999/CAPTCHA (APEC behind DataDome) is a refusal:
no looping on it, and no new attempt before 30 days. In the pipeline,
step 4b only runs on Sunday (`--dispo-jour`, `--dispo` to force it), stops
by itself after 100 min (`audit_dispo --duree`) then removes the closed offers; a single
pause, code 4 if work remains — normal. Before, cut off every day by the 45-min
timer, it never reached the removal (08-18/10/2026).

### Rules loaded on demand

The per-domain details live in `.claude/rules/`. Each file declares in its
frontmatter the `paths:` it governs, and Claude Code only injects it when one of them is
touched — so zero context cost the rest of the time. The other agents (Codex, Cursor) read
them by following the link.

| Rule | Triggers on |
|---|---|
| `.claude/rules/scoring.md` | `ats_match.py`, `tri_file.py` — `fit_score`, ESG cap, penalty on the title alone |
| `.claude/rules/patterns.md` | `ats_match.py`, `job_sources.py`, `tri_file.py` — regex, heredoc, substrings, final `\b` |
| `.claude/rules/documents.md` | `tailor_application.py`, `generate_docs.py`, `regenere_docs.py`, `sync_docs.py`, `chemins.py` |
| `.claude/rules/web-navigation.md` | `web_nav.py`, `site_strategies.py`, `apply_runner.py`, `acces.py` |
| `.claude/rules/desktop-app.md` | `JobHunter.pyw` |
| `.claude/rules/locks.md` | `jutil.py`, `job_sources.py`, `linkedin_desc.py`, `pipeline_quotidien.py`, `audit_dispo.py` |

## Limits that are decisions, not gaps

They have held since the start of the project and are not reopened in passing during a task.
The detail is in `.claude/rules/web-navigation.md`; the short version, which holds everywhere:

- **No automatic submission.** The final click to send is the user's.
  Add no `--auto` / `--submit` flag to `apply_runner.py`, or anywhere else. The
  `--pilote` mode (Candidatures panel of the app) clicks nothing either: "J'ai envoyé"
  (I have sent it) DECLARES, then the page is observed (`envoi` = confirmed / uncertain, ADR 0009) — and
  "uncertain" never triggers a re-send.
- **No anti-bot circumvention**, no CAPTCHA solving.
  No stealth engine, no masking of automation, no personal Chrome profile:
  the browser presents itself as automated (details: `.claude/rules/web-navigation.md`).
- **No password handled by the programs.**
- **No automatic account creation**, no reading of a mailbox by a program.
- The repository is **local, with no remote**, because it contains personal data.

## Invariants not to break

**Never hard-code a root.** Project paths moved four times in two
days and everything that hard-coded a root broke silently — including a watch job that
declared itself `success` for two months while tracking only 2 accounts out of 44. Detect by
marker: the first candidate folder, going upward, that really contains a
witness file. `jobhunter.racine` looks for `Scripts/` + `profil/` (or `JOBHUNTER_RACINE`): the app
and the engine work wherever they are placed.

**Regexes are not written through a shell heredoc** — details and pattern pitfalls in
`.claude/rules/patterns.md`.

**Every automatic deletion must spare the offers present in `suivi.json`.**
A posting closes *after* one has applied to it: without this guard, the purge deletes first
those the user applied to.

**`sys.stdout.reconfigure(encoding="utf-8", errors="replace")` at the top of any program
that prints an emoji or an accent.** Without it, redirected output — pipe, log, scheduled
task — falls back to cp1252 and raises `UnicodeEncodeError` on the first line.

**Windows ignores the case of file names.** Two names that differ only by
case are a single file: any name deduplication groups in lowercase.

**Check an import by loading the module, never by parsing the AST.** `ast.parse` passes
on a missing `import`; the error only comes out at run time.

**An empty collection has two opposite causes** — nothing to take, or refusal of entry.
`job_sources.INCIDENTS` counts the refusals and `main()` prints them, so that an entirely
throttled scan does not look like a quiet day (and so that it is not relaunched, which is
exactly what must not be done facing a quota).

## Environment

Development: **uv** (`uv sync` creates `.venv` from `pyproject.toml` and `uv.lock`),
**ruff** (lint and format, rules and exceptions in `pyproject.toml`), **pre-commit**
(`uv run pre-commit install`, once). Details: `.github/CONTRIBUTING.md`. Roadmap:
`docs/professionalisation-plan.md`.

End user: `lanceurs/installer.bat` / `lanceurs/installer.sh` install `requirements.txt` (same
bounds as `pyproject.toml`) into the system Python. `VERSION` and the version of
`pyproject.toml` must stay equal (`outils/verifie_version.py`, in CI).
