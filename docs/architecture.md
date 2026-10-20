# JobHunter architecture

This document describes the state as of 18 October 2026 (version 1.12). Each structuring
choice has its own ADR in [`docs/adr/`](adr/); the plan that led here is
[`professionalisation-plan.md`](professionalisation-plan.md).

## Overview

```
                 profil/profil.json  (identity, jobs, keywords, scoring, texts)
                          │  read by jobhunter.profil
                          ▼
  ┌────────────── collection ────────────┐     ┌──── triage and scoring ─────┐
  │ jobhunter.sources                    │     │ jobhunter.scoring           │
  │  ats · workday · linkedin · wtj · efc│     │  fit (score 1-10, fit_fin)  │
  │  eures · indeed · apec · glassdoor   │ ──▶ │  langue · zones · domaines  │
  │  vie · fir · talent · francetravail  │     │  tri (removes what does not │
  │  agregateurs                         │     │  fit the profile)           │
  │  fusion ── dedupes, scores, writes ──┼──┐  └─────────────────────────────┘
  └──────────────────────────────────────┘  │
                                            ▼
                         Scripts/apply_queue.json  ◀── jobhunter.stockage.file
                         Scripts/descriptions.json      (lock, atomic write,
                         Scripts/suivi.json        ◀──   descriptions apart)
                                            │          jobhunter.stockage.suivi
             ┌──────────────────────────────┼───────────────────────────┐
             ▼                              ▼                           ▼
  ┌── documents ──────────┐   ┌── application ─────────┐   ┌── navigation ──────────┐
  │ jobhunter.documents   │   │ jobhunter.app          │   │ jobhunter.navigation   │
  │  cv · lettre · message│   │  fenetre.App = mixins  │   │  page · carrieres      │
  │  cv_auto · llm · rendu│   │  tableau · fiche ·     │   │  formulaires · segment │
  │  (.docx then .pdf)    │   │  actions · panneaux…   │   │  compte · linkedin…    │
  └───────────────────────┘   └────────────────────────┘   └────────────────────────┘
                                                              fills in, HIGHLIGHTS submit:
                                                              the final click is human
```

## The packages

| Package | Role | Depends on |
|---|---|---|
| `jobhunter.racine` | installation root (marker `Scripts/` + `profil/`, or `JOBHUNTER_RACINE`) | — |
| `jobhunter.profil` | reading the profile, patterns compiled from its lists; `utiliser()` injects a profile | racine, paresseux |
| `jobhunter.paresseux` | module values computed on first read ([ADR 0007](adr/0007-lazy-profile-values.md)) | — |
| `jobhunter.journal` | the engine's `logging`: console unchanged, one timestamped file per run | — |
| `jobhunter.reseau` | HTTP requests bounded in total duration, shared client, `INCIDENTS` counter of refusals | — |
| `jobhunter.texte`, `liens` | text normalisation, paths ↔ `file:///` | — |
| `jobhunter.stockage` | queue, descriptions, tracking: lock, atomicity | racine |
| `jobhunter.scoring` | score, language, zones, domain, triage | profil, texte, chemins |
| `jobhunter.sources` | collection per source, merge into the queue | reseau, scoring, stockage |
| `jobhunter.documents` | CV, letter, short message, PDF | profil, scoring.lexique, chemins |
| `jobhunter.navigation` | Playwright: from the company's site to the filled-in form | racine |
| `jobhunter.app` | the desktop application (customtkinter) | everything above |
| `jobhunter.programmes` | the programs (pipeline, documents, application, audits, probes) | everything above |
| `jobhunter.cli` | `python -m jobhunter <commande>`, and any program by its name | racine |

Dependencies go in one direction only (from top to bottom of the table). A few deferred
imports towards `jobhunter.programmes` remain, marked `TRANSITION` in the code:
`doublons`, `rejets_tri`, `exclusions`, `wtj_desc`, `enrich_homepages`, `relances`,
`mise_a_jour`.

**Running without installing**: `python JobHunter.pyw` (the application) or
`python JobHunter.pyw <commande>`; it is the only file that adds `src/` to the import
path, and the `.bat`/`.sh` files as well as the scheduled task go through it. Installed with
`pip`, the package finds the data folder through `JOBHUNTER_RACINE` or by walking up
from the current folder ([ADR 0008](adr/0008-programs-in-the-package.md)).

## The data

Three JSON files in `Scripts/`, three access contracts
([ADR 0002](adr/0002-three-files-three-contracts.md)):

- **`apply_queue.json`** — the offers. Identity: `oid = "entreprise|poste"`, never
  the URL. Written only by `stockage.file.transaction()`.
- **`descriptions.json`** — the text of the postings, apart: it weighed 64% of the queue.
  Reinjected on read, taken out again on write, transparently.
- **`suivi.json`** — the applications. The least reconstructible data: the only versioned
  file, written entry by entry (`stockage.suivi.poser`) on the state re-read under lock.

A program that finds the queue locked exits with **code 3** without modifying anything
([ADR 0003](adr/0003-file-lock-exit-code-3.md)).

## The daily pipeline

`jobhunter.programmes.pipeline_quotidien` (`python JobHunter.pyw pipeline`), launched every
morning by the task that `lanceurs/planifier.bat` sets up:

1. **collection**, in five passes each merged (ATS/Workday/V.I.E; LinkedIn;
   eFC/EURES; APEC/France Travail/Adzuna/Jooble; Glassdoor/WTJ) — a pass that exceeds
   its time loses only its own;
2. **detail pages** of the V.I.E, **descriptions** from LinkedIn and career sites;
3. **triage**: seniority, required experience, job — applications are spared;
4. **availability**, on Sunday: closed offers removed (public API, 404/410);
5. **documents**: CV and letter for the top of the queue.

A backup of the queue, the descriptions and the scans is made before any step
(`Scripts/_sauvegardes/<date>/`, seven rolling days).

Logs: `Scripts/_logs/pipeline_<date>_<heure>.log` keeps the console of each step;
`…_moteur.log` beside it keeps the engine's messages with time, level and module
(`jobhunter.journal`, variable `JOBHUNTER_JOURNAL`). In the engine, `print` is reserved for
command output (`main()`); everything else goes through `logging`.

## Network: what is allowed

**Public** pages and APIs only. A rate limit (429) is waited out and the pass
resumes where it stopped; a refusal (403, 999, CAPTCHA) stops the source, with no
new attempt before 30 days ([ADR 0004](adr/0004-429-wait-403-stop.md)).
No anti-bot circumvention, no stealth engine, no password handled, no automatic
submission ([ADR 0005](adr/0005-no-automatic-submission.md)).

## Split packages: a single namespace

A split package (`sources`, `documents`, `navigation`, `app`) sees the names of all
its submodules, and an assignment goes to the module that owns the name
([ADR 0001](adr/0001-facade-aliases.md)): `jobhunter.sources.title_ok` and a
`monkeypatch` on `jobhunter.sources._get_borne` both work. The old `Scripts/x.py`
files (aliases of these modules) were removed in 2.0.

## Checking that a change changes nothing

- `outils/banc.py comparer outils/banc_reference.json`: 384 fictitious offers, every
  decision (title kept, score, domain, triage, zone, country, contract, language, message, letter
  and CV) compared to the reference. 0 differences expected ([ADR 0006](adr/0006-non-regression-bench.md)).
- `pytest`: ~1,450 tests without network; `mypy`: strict on the core.
