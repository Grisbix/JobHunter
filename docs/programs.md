# The programs — what does what

Formerly `data/README.md`. Since 2.0, the programs live in
`src/jobhunter/programs/` (and the engine in the other packages of `src/jobhunter`);
`data/` keeps only the data. The names below are the historical file names:
`job_sources.py` is `jobhunter.sources`, `queue_io.py` is
`jobhunter.storage.queue`, `web_nav.py` is `jobhunter.navigation`, etc.
(`docs/architecture.md`).

**Daily entry point: the app (`JobHunter.pyw`).** Almost everything here is called by
it. The command line is for when a program needs the keyboard, or for batch
operations: `python JobHunter.pyw <commande>` (or `python -m jobhunter
<commande>` once installed), and any program by its name
(`python JobHunter.pyw probe_ats`).

**The file that matters: `apply_queue.json`.** All the offers are in it — except their
descriptions, which live apart in `descriptions.json` (they weighed 64% of the file,
which 13 programs rewrote in full to modify a single offer). The separation is
invisible: `queue_io.charger()` reinjects them.

**To read or write the queue, go through `queue_io`.** Not `json.loads`: a direct read
no longer sees the descriptions, and a direct write loses the lock.

**For `applications.json`, go through `suivi_io`.** Same reason, higher stakes: a lost offer is
found again by the scan tomorrow; a lost application never comes back.

---

## The foundation — read by almost everything

| Program | Role |
|---|---|
| `web_nav.py` | Web navigation (Playwright): cookies, ATS detection, offer search, fallback to the career page. 3400 lines, the biggest piece. |
| `site_strategies.py` | Per-site strategies for the 62 sites without an account. |
| `util.py` | **Atomic** JSON writing (tmp + `os.replace`), inter-process lock (breaks that of a dead process), and the shared helpers: `chemin_de`, `url_de`, `existe`, `sans_accent`, `cle`. |
| `queue_io.py` | **The only access path to `apply_queue.json`.** `charger()` to read, `transaction()` to write (lock + fresh re-read + atomic write). Separates the descriptions into `descriptions.json`. |
| `suivi_io.py` | **The only access path to `applications.json`** — the applications, the project's least reconstructible data. Same contract as `queue_io`: `charger()`, `transaction()`, `modifier()`, `poser()`. |
| `ats_match.py` | **The scoring.** Six weighted axes (ESG ×3, finance ×2, AI ×1.5), cap by ESG density, seniority and experience penalty. |

## Offer collection

| Program | Role |
|---|---|
| `scrape_jobs.py` | Scrapes the 65 company career sites (`unique_domains.txt`). Writes `offres_fraiches.json` **and merges into the queue** (`--no-merge` to abstain). Respects `robots.txt`. |
| `job_sources.py` | Broad scan — ATS APIs, public LinkedIn, V.I.E, FIR, Talent, France Travail, WTJ — **and merge** into the queue. Writes `offres_scan.json`. |
| `add_offer.py` | Paste an offer link → analyses the page → queue + CV/letter. |
| `probe_ats.py` | Tests candidate slugs on the 5 public ATS APIs. |
| `probe_careers.py` | **Finds the real career page** of each site and **the ATS behind it**. Reads the home page (the site itself says where it recruits), then the sitemap, then guesses — in that order. Writes `carrieres_detectees.json`. |
| `probe_workday.py` | Finds the public Workday feeds of large groups. |
| `probe_keywords.py` | Measures the **real yield** of a search keyword. |
| `setup_francetravail.py` | Installs and checks the France Travail API credentials. |

## Queue quality

| Program | Role |
|---|---|
| `scrape_desc.py` | Fetches the description from the offer page. Fails on anti-bot sites. |
| `linkedin_desc.py` | LinkedIn descriptions via the **public guest API**, where `scrape_desc` hits the login wall. Re-scores right away. |
| `linkedin_closed.py` | Removes the LinkedIn offers that no longer accept applications. Deletes only on a positive signal. |
| `resolve_offer_links.py` | Replaces a "career page" link with the link of the offer. |
| `enrich_homepages.py` | Finds the home page of companies without an offer URL. |
| `link_check.py` | Checks the URLs (live / dead / soft-404). Module. |
| `recheck_dead.py` | Soft-404s rendered in JavaScript (HTTP 200 but empty body). |
| `availability_audit.py` | Checks the whole queue without a browser and removes closed offers; Workday, Ashby and Greenhouse through their public API first (`ats_liveness.py`, their pages are the same JavaScript shell open or closed); waits and resumes on 429; `--duree` stops it by itself before removing. Step 4b of the pipeline, on Sunday. |
| `reposts.py` | « Signal » column: knock-out conditions first (`scoring.knockouts`: licence, nationality, right to work, clearance; profile section `eliminatoires`), an offer back under a new address on the same site (history `_offres_vues.json`, 90 days; count in `republiee`, used by the rank), and the same text under another company (64-bit SimHash, agencies and job boards). Observations only. Step 4a. Limit: two identical titles opened in parallel at one company look like a repost. |
| `archive_postings.py` | A copy of the posting of every application (PDF + .txt in `Letters/Postings/`, engine `jobhunter.postings`), written once from the queue's text, never rewritten. Also done by the app at the « postulé » click. Step 4a'. `jobhunter postings`. |
| `restore.py` | Puts the queue back as it was in a backup (daily, before the audit, before the sort): `--liste`, then a name; inspection by default, `--appliquer` writes. Never restores the tracker, keeps the tracked offers, loses no description, and copies the state before so the restoration can be undone. `jobhunter restore`. |
| `queue_tools.py` | Queue maintenance. |
| `rescore_ats.py` | Recomputes `ats_pct` and `skills_match` over the whole queue. |
| `export_queue_csv.py` | Readable backup as CSV. |

## Documents — CVs and letters

| Program | Role |
|---|---|
| `tailor_application.py` | **Generates** the CV and the letter tailored to an offer. Contains `titre_poste()`, the cleaning of the job title. |
| `generate_docs.py` | Batches from the queue. Selectors: `--top`, `--all`, `--sans-source`, `--objet`, `--collisions`, `--cv-generique`. |
| `rename_docs.py` | Names in the format `Camille_Exemple_CV/Lettre_<Poste>_<Entreprise>`. |
| `sync_docs.py` | Consistency enforcer: the `.docx` is the source, the PDF derives from it. |
| `refresh_letters.py` | Refreshes all the letters — date, order, subject. Idempotent. |
| `fix_letters.py` | Rehabilitates existing letters. |

## Application and tracking

| Program | Role |
|---|---|
| `ranking_evaluation.py` | The ranking against the judgements in the tracking: AUC and interval, precision of the top ones, worst errors; `--enregistrer` keeps a reference (`data/_evaluation.json`); `--analyse` splits by contract, field and zone and tries contract bonuses (`scoring.calibration`), suggesting one only if its gain's 90 % interval stays above zero. The ranking is `scoring.ranking.rang`. `python JobHunter.pyw evaluation`. Read-only. |
| `source_yield.py` | Per-source report of the collections (log `data/_rendement.jsonl`): returned, new, relevant, time, verdict (ok, nothing to take, limited, partial, refused); then the followed companies silent for 30 days (`sources.feeds.muet`: failing, empty page, nothing for the profile). `python JobHunter.pyw yield`. Read-only. |
| `check_folders.py` | Check of the application files before sending (read-only): readable PDF, one page, contact details, template filled in; prefers the up-to-date PDF over its .docx. Step 5b of the pipeline. `python JobHunter.pyw check`. |
| `apply_runner.py` | Fills in the forms, **semi-automatic**: the final click to send remains yours. Driven by the Candidatures panel of the app (`--pilote`) or by keyboard; after "envoyé" (sent), observes the page and writes the tracking with the proof (`envoi` confirmed / uncertain, screenshot in `data/_proofs/`). |
| `mail_statuses.py` | Statuses proposed from the emails received (rejection, interview, acknowledgement of receipt), **validated one by one**: `jobhunter mail-statuses --mbox …` (Google Takeout export), `--eml <dossier>` or `--gmail` (read-only API, OAuth client created by the user in `data/gmail_client.json`, token in `data/gmail_token.json`, `pip install "jobhunter[gmail]"`). The status only moves downstream; the entry keeps the quoted email (`courriel`). Window in the app: Maintenance → "Statuts depuis mes courriels…" (Statuses from my emails…). Engine: `jobhunter.mail`. |
| `follow_ups.py` | D+7 / D+10 follow-up emails per offer. `--brouillons` prepares those of all the follow-ups due, opening nothing and sending nothing: Windows task `Relances`, on Monday at 9:30, report in the vault (`Routines/Relances/`). |
| `weekly_metrics.py` | Report of the week, read-only: applications sent, to follow up, replies, pipeline merges and days without a run. Launched on Sunday at 21:00 by the Windows task `Metriques_Emploi`; output in the vault, `Routines/Metriques_Emploi/`. |
| `notify_matches.py` | Windows alert when a high-fit offer arrives. |
| `access.py` | Manages access to the sites **without ever storing a password**. |
| `test_site_access.py` | Measures which sites of the queue can be opened. |

## Tests

| Program | Coverage |
|---|---|
| `test_patterns.py` | 68 cases — form recognition, offer search, filling in. |
| `test_job_titles.py` | 38 cases — title cleaning, elision, idempotence. |
| `test_contracts.py` | 26 cases — deduction of the contract type, and its false positives. |
| `test_sources.py` | 24 cases — arbitration of duplicates between sources. |
| `test_queue_io.py` | 25 cases — exclusion between processes, no write on exception, separation of the descriptions. |
| `test_applications.py` | 9 cases — a recorded application never disappears, even if its posting closes. |
| `test_follow_ups.py` | 11 cases — D+7 then D+10 template, edited draft never overwritten, nothing is sent. |
| `test_weekly_metrics.py` | 26 cases — dates `AAAA-MM-JJ` and `jj/mm`, entries without a date, follow-up threshold, pipeline logs. |
| `test_web_nav_mock.py` | 20 cases — network and Ollama mocked. |
| `test_web_nav.py` | Synthetic tests of `web_nav`, without network. |
| `test_live_nav.py` | Real read-only test on real career sites. |

The first five run without network: `python test_patterns.py`, etc.

## Out of scope

No account creation and no reading of a mailbox by a program: these are
actions the user does themselves.

---

## Code pitfalls, learned the hard way

**`\b` in a regex written through a shell heredoc.** It becomes either the backspace
character `\x08`, or a literal backslash. In both cases the pattern compiles, raises
nothing, and **never matches again**. Three occurrences. `job_sources.py` and
`tailor_application.py` now refuse to start if one of their patterns is corrupted.

**A selector must compare the content of the file, not the source data.** A test like
`titre_poste(brut) != brut` is permanently true: it never converges and
keeps proposing the same offers forever.

**Windows ignores the case of file names.** Two names that differ only by
case are **a single file**. Any name deduplication must group in lowercase.

**`sys.stdout.reconfigure(encoding="utf-8")` is mandatory** in any program that
prints an emoji. Without it, redirected output (pipe, log, scheduled task) falls back to
cp1252 and raises `UnicodeEncodeError` on the first line.

**A posting closes AFTER one has applied to it.** Any automatic deletion must therefore
spare the offers present in `applications.json` — otherwise it deletes first those
the user applied to, and the trace becomes orphaned.

**Check an import by loading the module, not by analysing the syntax.** `ast.parse`
passes on a missing `import`; the error only comes out at run time.

**An index must point to the object you keep, not to the one you read.**
`merge_into_queue` stored in its index the dict coming from the *scan*, whereas the queue
received a *different* dict. Any URL or description promotion arriving later in the
same batch was therefore written to an orphan: the counters announced "1 link promoted"
and the queue kept the LinkedIn link and its empty description. This is the **normal** case, not
an edge case — one `--all` chains ATS, LinkedIn, WTJ, eFC and Indeed on the same posting.

**A guard that chooses its targets by name ends up missing some.** The check of the `\b`
only looked at the globals prefixed `_RX_`: it ignored `_DOMAIN_RX`, `_HARD_NEG_RX`
and `_AI_RX`, that is exactly the patterns of `title_ok`, the filter that decides what
enters the queue. It now sweeps **every** `re.Pattern` of the module.

**Two keyword lists that must agree diverge silently.** `title_ok` requires
a word from the broad lexicon (`scrape_jobs`) **and** a job word (`_DOMAIN_RX`): a term
present in one and absent from the other makes the offer be thrown away without a word. "CSRD" was a
*search* keyword of the scan and lived in `_DOMAIN_RX`, but not in the lexicon — these offers were
requested from LinkedIn only to be thrown away on arrival. `test_sources.py` tests
the invariant.

**An empty collection has two opposite causes.** Nothing to take, or refusal of entry. Both
returned `[]` without a word, so that an entirely throttled scan looked like a quiet
day — and it was relaunched, which is exactly what must not be done facing a
quota. `job_sources.INCIDENTS` counts the refusals and `main()` prints them; an ATS 404
stays silent, though, because a dead slug is the normal case.

**Return only the lock you took.** `prendre_verrou` is reentrant, `rendre_verrou`
is not. A function that takes then returns it, when its caller held it for the whole
program (`util.garder`), removes it from the caller — and the rest of the work is done unprotected.
`util.tenu(chemin)` answers before taking.

**Writing a memory snapshot overwrites the work of others.** The app kept `applications.json`
in memory and rewrote it IN FULL on every click. A "applied" on one offer therefore erased
the follow-ups that `follow_ups.py` had just noted on others — without a word. One writes
one entry, under lock, on the state re-read inside the lock: this is what
`suivi_io.poser` does. Tested by `test_applications.py`.

**An `after` loop that only catches one specific exception dies at the first other one.**
`_drain` (the app) only saw `queue.Empty`; any other failure came out BEFORE the line that
reschedules the loop. Measured: 1 round instead of 20, and no more table reloads
after a scan. The rescheduling goes into a `finally`. In a `.pyw` there is no
console, so the trace goes nowhere: `root.report_callback_exception` now files it
in `_logs/app_erreurs.log`.

**A promise of undo must designate a file that exists.** The deletion box
said "recoverable via git"; on the day of the check, 424 offers on disk
were in no commit. The deletion now writes a timestamped copy in
`_corbeille/` before removing anything.

**Two paths to the same file are not equal.** `queue_io` only reinjected the
descriptions if the path received equalled `CHEMIN` *as is*: `Path("apply_queue.json")`,
launched from `data/`, returned the 11,710 offers without a description (the real bench saw
25,461 differences, all false), and `sauver` would have rewritten them into the queue. Paths
are now compared resolved (`_est_la_file`).

**A failed read is not an absence.** `suivi.charger` returned `{}` for a missing file
as for a truncated JSON; the transaction then wrote this `{}` plus the
new application, and all the others disappeared. A write now starts
from `_lire`, which raises `SuiviIllisible` and leaves the file as it is (audit of 19/10).

**Two atomic files do not make a transaction.** `sauver` purged the orphan
descriptions then wrote the queue: a failure between the two kept the removed offer in the queue,
without its text. Current order: additions to the annex, queue, then
purge. A failure only leaves orphans (audit of 19/10).

**A snapshot rewritten after network work erases what changed in the meantime.**
`queue_tools.mark_dead` read the queue, checked the links for minutes, then
rewrote its copy without a lock: the collection merged in the meantime was lost. The
network work is done outside the lock, and only its results are applied to the queue re-read in
`queue_io.transaction` (audit of 19/10).

**Every purge consults the tracking, the merge included.** The merge removed the "Scan"
rows whose title failed a modified filter, without looking at the tracking: an
application lost its record. The invariant of AGENTS.md held for explicit
deletions, not for this cleanup (audit of 19/10).

**A pattern spelled one way misses the page written another way.** Portals write
"n’est plus disponible" with a typographic apostrophe (U+2019) and German pages
"verfügbar": a closure pattern with a plain `'` or without the umlaut never matched,
and the offer stayed "open". `availability_audit.texte_ferme` normalises the page
first (ASCII quotes, no accents, single blanks) and every pattern is spelled in that
alphabet. Offers abroad are wanted, so closure banners exist in seven languages
(career-ops audit, 21/10).

**One weak word is not a status.** "Unfortunately we need to reschedule your interview"
was suggested as a rejection, and an acknowledgement promising "next steps" as an
interview. `mail/statuses` splits phrases in two tiers: a strong one is enough, weak
ones need a second one, and a weak interview word does not count in an
acknowledgement (21/10).

**A length floor on words drops whole names.** Company words under three letters were
discarded to skip "de", "of"…: EY, HP and 3M then had no word left and were never
matched. Short names are kept when they are all the name has, and matched as whole
words — never "hp" inside "php" (21/10).

**`urllib.robotparser` trusts what it is given.** A robots.txt starting with a UTF-8
byte-order mark glues the mark to the first `User-agent` line, the parser drops that
group, and its `Disallow` lines are ignored (measured on Python 3.14). And
`RobotFileParser.read()` calls `urlopen` without a timeout. `scrape_jobs` fetches the
file through `get_borne` and strips the mark before `parse()` (21/10).

**A page drawn by JavaScript says nothing.** Workday and Ashby send the same empty
shell, HTTP 200, for an open offer and a withdrawn one: the availability check found
304 Workday offers "OK" and not one closed, while their API said half were withdrawn
(10 of 20 sampled, each confirmed missing from the employer's job list). Ask the ATS's
API (`ats_liveness`); on Workday a withdrawn offer is a 403 whose JSON says
`errorCode: "S22"`, any other 403 proves nothing (21/10).

**A save from a form must start from the entry on disk, not from the form.** The card's
« Enregistrer » built a new entry from its three fields (status, date, note) and wrote it
whole: the proof of sending and the email the status cited, not on the form, were
erased at every save (found 22/10, fixed in 3.15). Same trap with a shallow copy: the
status history is a list, and `dict(entry)` shares it with the copy Ctrl+Z keeps —
appending to it rewrote the undo too. `historiser` builds a new list.

**A Treeview stretches only its stretchable columns, and only on resize.** The job title
had `stretch`, the company did not: at start-up the company stayed at its minimum width
and was cut, whatever the share computed for it, because that share was only applied
after a change of columns. The share is now applied on every `<Configure>` of the table,
unless the user has dragged a column edge (22/10).

**A junior test on the whole text makes every posting junior.** `experience_years`
returned 0 as soon as the text said « stage », « alternance » or « internship »
anywhere — « 2 années d'expérience minimum (stages et alternance compris) », an
« INTERNSHIP » footer tag. Seven of twenty rejected offers kept fit 10 that way. The test
reads the title; the requirement is read in the text, ranges by their lower bound, and
« years of » alone is no longer a context (« 15 years of working together ») (3.16, 22/10).

