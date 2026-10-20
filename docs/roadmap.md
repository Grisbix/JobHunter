# Roadmap after the professionalisation plan

The professionalisation plan (`docs/professionalisation-plan.md`) is finished. Phases 0 to 6 and 8
are done, phase 7 is set aside for lack of need. Three workstreams from Codex's first
proposals document (18/10) are delivered:

- applying from the app with proof of sending (2.2);
- checked folders (2.3);
- yield per source (2.4).

This roadmap crosses what remains with Codex's second document (19/10,
"Cross-repository exploration", ten tooling leads). It ranks everything by
value for the job search and by cost.

Rule unchanged: each step delivers on its own, bench at 0 differences, and is adopted only on
a reproduced failure or a measured gain. No dependency installed "in bulk".

## Step A — Make what was just delivered live (before any new code)

| # | What | Who | Done when |
|---|---|---|---|
| A1 | Real trial of the Candidatures panel on one offer; add to the confirmation detector the real phrasings it would have missed | Gabriel, then code | a real application recorded as `confirmé`, or an unrecognised page added to the patterns and tested |
| A2 | Sunday 25/10: first weekly availability check | reading the summary | the ~143 closed offers found are removed, step under 110 min |
| A3 | After one to two weeks of log: `jobhunter rendement` | reading + decision | each source has a stable verdict; decide (by hand) the fate of a source refused every time |

## Step B — Missing non-regression proofs (Codex 19/10, P1, low effort)

| # | What | Why here | Done when |
|---|---|---|---|
| B1 ✅ (v2.4.1) | **Architecture test**: the engine (`jobhunter.*` except `app`, `accueil`) imports neither `tkinter` nor `customtkinter` nor `jobhunter.app` | The plan says "checked in CI by import-linter", but nothing is wired in: a pytest test of a few lines is enough, without ArchUnitPython or import-linter | a deliberate Tkinter import in `scoring` fails the test; removing it makes it pass |
| B2 ✅ (v2.4.3) | **Recorded connector responses** (pytest-recording / VCR.py, test-only dependency): APEC (API), LinkedIn guest, WTJ sitemap, Workday, Greenhouse/Lever | The current doubles (`faux_reseau`) are written by hand: they do not say whether the parser still reads today's real response. A recorded real response, scrubbed (cookies, headers), makes the parser reproducible | ten responses replayed without network give the same offers; a missing exchange fails; no cookie or identifier in the versioned files |
| B3 ✅ (CONTRIBUTING, 19/10) | **Slowness diagnosis**: py-spy procedure (external tool, not a dependency) in `CONTRIBUTING.md` | Useful the next time a step exceeds its duration (collection, availability): locate instead of guessing | the procedure finds the function of a deliberately provoked stall, report without personal data (`--locals` disabled) |

## Step C — The two remaining business workstreams (Codex 18/10)

| # | What | Why | Done when |
|---|---|---|---|
| C1 ✅ (v2.5.0) | **Ranking evaluated on real judgements**: build the reference set from what already exists. Relevant: the offers applied to, followed up or at interview in the tracking. Useless: "not interested" and `exclusions.json`. Then measure the current ranking (precision of the top N). | There is no measure today of "are the top offers the right ones". It is the prerequisite for any variant, semantic or otherwise. | a reproducible reference figure (`jobhunter evaluation`); any change to scoring is compared against it, together with the bench |
| C2 ✅ (v2.6.0) | **More robust offer identity**: first a **study**. Count on the real queue the namesakes (same `entreprise\|poste`, different location or reference) and the duplicates under two titles. | The `entreprise\|poste` key is the one of `suivi.json`, the least reconstructable data. Nothing is migrated without a measured problem. | an ADR that quantifies the problem and decides: secondary identity (source reference) as a complement, or status quo |

## Step D — The application tested as it runs (Codex 19/10, P1, medium effort)

| # | What | Done when |
|---|---|---|
| D1 ✅ (19/10, decision: no) | **pywinauto probe, limited to half a day**: inspect the control tree of the real window. CustomTkinter draws its widgets on a canvas: they may be invisible to UI Automation. | written decision. If the controls are visible: a walkthrough with a fictitious profile (open, filter, sheet, Candidatures panel with the fake program). Otherwise: we keep the internal Tk tests and the panel smoke test, and note it. |

**Result of D1 (19/10/2026).** The app launched on a fictitious profile, read by pywinauto
(UIA backend): 206 elements, of which 153 panes and 43 images **without a name**. The only 5
named buttons are those of the Windows title bar. No JobHunter button, field or table
is visible: CustomTkinter draws them on a canvas. Decision: no pywinauto
walkthrough. We keep the internal Tk tests (`test_app_design`, panels opened
on a throwaway queue) and the screenshots taken from Python. Consequence for E3:
a screen reader does not see the application either. Fixing it would require
leaving CustomTkinter, or adding an accessibility layer to it.

## Step E — Distribution beyond Gabriel (when the friend's PC and the Mac are back)

| # | What | Done when |
|---|---|---|
| E1 ✅ (v2.17.0 `.venv`; v2.18.0 "installation" workflow: `installer.bat` and `installer.sh` on fresh GitHub machines, Windows and Linux) | Dedicated Python environment created by `installer.bat` (postponed from phase 1) | a fresh installation on a blank Windows launches the app without touching the system Python |
| E2 ✅ (v2.18.0, ADR 0012: Ed25519 in pure Python, private key outside GitHub, `outils/signature.py`; the app downloads, checks and opens the installer. Active as soon as Gabriel creates his key) | **Signed** updates: WinSparkle or tufup (Codex P2), to be chosen on a prototype. Caution: tufup's destination purge is incompatible with a folder that contains the profile. | a tampered package is refused; the profile survives an interrupted update |
| E3 ◐ (v2.20.0: every button can be operated by keyboard — Tab, Enter, Space — with a visible focus ring on every background; field outline at 3:1; text contrasts checked in tests, WCAG AA. Still impossible without leaving CustomTkinter: giving the controls a name for a screen reader, and keyboard focus on the segmented tabs) | Accessibility (axe-windows, Accessibility Insights) | the main controls have a name; tabbing follows the visual order |

## Set aside or deferred, with the reason

| Lead (Codex 19/10) | Decision |
|---|---|
| Durable queue (litequeue, persist-queue) | No loss of work observed: each pipeline step resumes where it stopped (`_audit_dispo.json`, `apply_runner_done.json`, duration budget). Codex himself points out that no queue guarantees a network effect executed only once. To be reopened on an observed loss. |
| DocRefract (document comparison) | The bench already compares the text of 99 letters and CVs at every change, and `documents.controle` checks the final files. Marginal gain. |
| sqlite-utils / FTS5 (local search) | The app's search answers over 12,000 offers. To be reopened if it becomes slow. |
| ArchUnitPython | Replaced by test B1, simpler, no dependency. |
| confluence-exporter cancellation model | The panel has "Arrêter" ("Stop"), the pipeline has duration budgets and resumptions. |
| Huey, DurableFlow, spoolctl, beta distribution tools, PDF comparers under GPL/AGPL or without Windows | Already set aside by Codex, for the reasons he documents. |

## Step F — A product you download and understand (requested on 2026-10-19)

User's decisions:
- **standalone application**, without Python on the machine;
- **French and English**;
- **repository showcase in English**, the code keeping its French names;
- **complete clean-up**, old releases included.

| # | What | Done when |
|---|---|---|
| F1 ✅ (v2.7.0) | **Sort things out**, in three parts (see the detail under the table) | every remaining file has a written role; the tree can be read at a glance |
| F2 ✅ (v2.8.0) | **App panels brought up to date**, one by one (see the detail under the table) | every figure displayed is right and every line has an action |
| F3 ⛔ set aside | **HelloWork source**: public search pages, without circumvention; robots.txt and terms checked first | HelloWork offers in the queue, response recorded and replayed (B2), verdict in `rendement` |
| F4 ✅ (v2.9.0; v2.19.0 completion criterion checked at every build: without Python on the PATH, window, system browser, merge, folder, update over the top with data kept; morning collection from the app) | **Standalone installer** `JobHunterSetup.exe` (see the detail under the table) | on a Windows without Python: installation, opening, collection and folder |
| F5 ✅ (v2.10.0 navigation, panels, menus; v2.13.0 log and dialog boxes; v2.17.0 summaries of launched programs, the offer-by-offer detail remaining as it is) | **French and English**: interface texts in catalogues, choice in the settings; repository showcase in English (README, user docs, release notes), French version alongside | the whole app in English from one setting; English README with the link to the French one |

**F1 — sort things out**
- Remove from both repositories the dead or duplicate programs, the outdated documents,
  `Archive/` and the `.bak` files.
- Delete the old GitHub releases, from a prepared list. Deletion is
  irreversible: it is launched by the user, keeping at least 1.15 (the bridge) and
  the 2.x ones.
- Tidy the tree.

**F2 — app panels brought up to date, one by one**
- "Mes CV" ("My CVs"): profile variants, fact bank, state of the folders (2.3), CVs per
  offer retrieved from the offer rather than a list of 1,983.
- "Entreprises" ("Companies"): the feeds actually collected (ATS, Workday, other feeds), with
  yield and verdict (2.4); correct offer counts.
- "Accès" ("Access"): active sources only, real state (refusal, limit, missing key),
  Adzuna and Jooble included.

**F4 — standalone installer**
- Compiled application (PyInstaller) and Windows installer.
- Built by CI and attached to every release.
- Two badges in the README, like Ibaraki: "Télécharger l'installeur" ("Download the installer") and "Code
  source" ("Source code").
- Chrome and LibreOffice detected, with a link if they are missing.
- Update of the installed app by the next release.

Order: **F1 → F2 → F3 → F4 → F5**. We sort first, so as not to compile or translate dead
code. The installer is built on a clean base. We translate last, once the texts
have stabilised.

## Step G — Ideas from the GitHub watch (19/10)

| # | What | Done when |
|---|---|---|
| G1 ✅ (v2.13.0) | **Company directories** Lever, Ashby, Greenhouse (jobsync, MIT) in the Entreprises panel | type a name, choose, follow; `outils/annuaires.py --verifier` reproduces the files |
| G2 ✅ (v2.14.0) | **Letter reviewer**: a second pass, without the context of the drafting, that checks the letter against the style guide and the facts; the job posting is an untrusted input (injection) | each flaw reported is reproduced by a test; no letter rewritten without agreement |
| G3 ◐ (v2.15.0: each fit explained in the sheet; remaining: rank better, once there are enough judgements) | **Justified fit score** (C1 bis): each point of the fit cites the passage of the posting that gives it | `jobhunter evaluation` does better than the 0.46 AUC of 2.5.0, on the same judgements |
| G4 ✅ (v2.20.0: `jobhunter statuts-mail`, .mbox/.eml export or read-only Gmail API; window in the app) | **Statuses from Gmail**, read-only, proposals validated one by one — only if Gabriel asks | — |

## Step H — Ideas from the architecture watch (20/10), sorted

The watch of 20/10 (Obsidian, "Nouvelles idées architecturales", 17 ideas, and "Modèles
de repos professionnels") was collected without ranking. Each idea is compared with
what JobHunter already does; only what fills a real gap is kept.

| # | Idea | Decision | Why |
|---|---|---|---|
| H1 ✅ (v2.22.0) | 2. Undo a batch clean-up | **kept** | the sort, the audit and the merge back up before removing, but nothing put a backup back: `jobhunter restaurer` (tracker never restored, tracked offers kept, state before copied) |
| H2 ✅ (v2.22.0) | Network failure matrix (HTTPX, Scrapy models) | **kept** | 22 ATS and career-feed readers × 403, 429, 500, timeout, empty or unreadable JSON: each failure counted, never a calm day; 404 silent (`tests/test_pannes_reseau.py`) |
| H3 ✅ (v2.22.0) | 6. Keep unknown fields on read then write | **kept, test only** | already true (plain dicts, `transaction` rewrites what it read); now proven for the queue and the tracker |
| — | 4. Explicit status transitions | already done | ADR 0009: an open browser never yields "postulé"; the guard is tested |
| — | 8, 17. Provenance of a score, run identity | partly done | `jobhunter.scoring` explains each fit (G3); a run identifier waits for a measured need |
| — | 9. Context of an offer | partly done | `_passe`, `autres_lieux`, URL promotion keep the sources; deferred |
| — | 15. Common retry budget | already done | bounded requests (`jobhunter.reseau`), Retry-After honoured, refusals stop (ADR 0004) |
| — | 11. Secret-free settings | already done | the profile holds no secret; keys live in separate ignored files |
| — | 1, 12. Detect and show changes of an offer, diff before replacement | **deferred** | useful, but needs a stored previous version of each offer: decide with the availability results (A2) |
| — | 3. Reusable cleaning recipes | deferred | the profile already carries the rules; no repeated manual clean-up to capture |
| — | 7, 14, 16. Event-driven views, task queue | set aside | one process, one user: the lock and the background threads are enough |
| — | 5, 13. CRDT / Automerge / Yjs | set aside | a single machine; the lock + fresh reread already prevents silent loss |
| — | 10. Rule language (expr) | set aside | no `eval`; the profile's declarative lists are enough |

## Step I — GitHub sweep, carried further (20/10)

The Codex sweep of 20/10 (Obsidian, "Grand Sweep GitHub", 34 repositories) read mostly
general Python libraries, half of them from the README only, and none of the projects
that do the same job. Completed by reading the code of three of them —
[JobSpy](https://github.com/speedyapply/JobSpy),
[JobFunnel](https://github.com/PaulMcInnis/JobFunnel) (archived),
[career-ops](https://github.com/career-ops-hq/career-ops) — and by doing the sweep's
cheap actions instead of only listing them.

| # | Idea (source) | Decision | Why |
|---|---|---|---|
| I1 ✅ (v2.22.1) | Generated-case invariants (Hypothesis) | **kept** | `tests/test_proprietes.py`: title cleaning stable, tracking parameters ignored by the URL key, score in 1..10 with a level its decimals never move, a merge repeated adds nothing, a tracked offer survives any merge. First run: two title bugs ("H&M - H/F" → "H&"; "– F – H" kept), fixed, 0 real title changed out of 10,455 |
| I2 ✅ (v2.22.1) | Test on the interpreter really used (Codex) | **kept** | the Windows tests run on 3.12 (the floor) and 3.14 (`C:\Python314`) |
| — | Per-site errors and warnings (JobSpy) | already done | `INCIDENTS` and `_rendement.jsonl` verdicts |
| — | ATS feeds (career-ops: Greenhouse, Ashby, Lever, Wellfound) | already wider | Greenhouse, Lever (and its EU region), Ashby, Recruitee, Teamtailor, SmartRecruiters, Workable, Workday |
| — | Fact-check before export (career-ops) | already done | `Faits.json`, `controle`, `relecture` |
| — | Advisory score calibration (career-ops `calibrate`) | already done, stricter | `jobhunter evaluation`: AUC with a resampled interval, never auto-tunes |
| — | Outcomes per channel, count-gated (career-ops `analyze-patterns`) | **deferred** | 16 applications sent, no answer yet: every group would read "too few". Revisit at ~30 sent with answers |
| — | Repost / ghost-job detection (career-ops `detect-reposts`: same company, same title word set, ≥ 2 URLs over 1–90 days) | **deferred** | needs a history of removed offers; same prerequisite as H 1/12 |
| — | Panels opened without a console, with an injected read error (Codex, Thonny) | next | the import without console is tested, the visible panels are not yet |
| — | HTTP cache (requests-cache) | set aside | it serves a stale answer when the request fails: it would lie about a closed offer |
| — | Tenacity, structlog, loguru, APScheduler, Pydantic, nox | set aside | the existing bounded requests, logging, scheduled tasks and TypedDicts cover the need; no second layer |

## Proposed order

**A** (ongoing, mostly observation) → **B1** (one hour) → **B2** → **C1** →
**C2 (study)** → **D1 (probe)** → **B3** when a slowness shows up → **E** when
distribution comes back.

What remains out of reach, whatever happens:
- no automatic submission;
- no anti-bot circumvention;
- no password handled.

## Done

- **B1** (v2.4.1): `tests/test_architecture.py`.
- **B2** (v2.4.3): `outils/rejeu.py` records a real public response from seven sources
  (Greenhouse, Lever, Ashby, Workday, LinkedIn, EURES, FIR), scrubbed;
  `tests/test_rejeu_sources.py` replays it without network and requires the same offers.
  - No VCR.py: all the sources' requests already go through `_get_borne` and
    `_post_borne`, which is where we record and replay.
  - A missing exchange fails, even when the source swallows the exception (the case of
    LinkedIn).
  - Found along the way: 10 of the 16 Greenhouse accounts in the configuration answered 404
    (companies that left Greenhouse), removed from the example configuration.
- **C1** (v2.5.0): `jobhunter evaluation` measures the ranking (`fit_fin`) against the
  judgements in the tracking. Relevant: applied, followed up, interview, rejection, to apply.
  Useless: bad, not interested; a "bad" whose note states a fact (filled,
  page without an offer) does not count. The command gives the AUC with a 90% interval,
  the precision of the top ones, and the worst errors.
  `--enregistrer` keeps a reference to judge any variant.
  - **First finding**, on one user's 37 judgements: **AUC 0.46**
    (interval 0.31 – 0.62), that is, no better than chance **on the judged offers**.
  - Many discarded offers are scored at the maximum, often without a note saying
    why: the engine cannot learn what it does not see.
  - **Logical follow-up (C1 bis)**: a one-click reason when discarding an offer (internship,
    language, seniority, job, location…), to know what scoring misses before
    modifying it.
- **C2** (v2.6.0, [ADR 0010](adr/0010-offer-identity-company-job.md)): quantified study.
  - Findings: 12 offers out of 86 lost as the same job in several cities; 9 URLs
    carry 2 or 3 keys in a queue of 12,169 offers.
  - Decision: the `entreprise|poste` key stays, there is no migration of the tracking.
  - The scan's deduplication keeps the city of the best zone and notes the others
    (`autres_lieux`).
  - `doublons` brings together the offers with the same posting URL, keeping the tracked offer, then
    the current title.
- **F3** set aside on 2026-10-19: HelloWork's terms of use (art. 8.2)
  forbid any automated extraction, even non-commercial, without a written licence;
  robots.txt also forbids the search pages. Compliant leads: Adzuna and Jooble
  (official APIs, which carry over part of these offers), adding an offer by its
  link, or a licence requested from HelloWork.
