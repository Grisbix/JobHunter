# What's new in JobHunter

The update (`mettre_a_jour.bat`, `./mettre_a_jour.sh` or the application's button)
shows the sections newer than your version. Format: `## x.y.z — date`, the most
recent at the top.

## 3.18.0 — 2026-10-22

- **A « Profil » panel in the menu, with three tabs.**
  - **Profils**: every profile, the active one marked; open one (JobHunter restarts on
    it), rename, archive (nothing is deleted). Drop a CV on this tab, or choose one,
    to create a new profile.
  - **Fit**: how the fit is computed, and its weights to tune with sliders: each axis,
    the score worth 10, the junior bonus and senior penalty of the title, the penalty
    per years of experience asked for. Each move recomputes at once the queue's mean
    fit, its offers at 8 and more and its distribution 1-10 (the saved weights drawn
    as outlines), and the detail of the offer selected in the table. Nothing is
    written before « Enregistrer », which keeps the previous profile as `.bak` and
    offers to recompute the fit stored for every offer.
  - **Compétences**: the profile's skills, the words searched for each in the postings
    and the axes it counts for. Add, change, remove, then « Enregistrer ».
- **BPCE and Natixis titles are no longer glued to the rest of the card.** Their sites
  wrap the whole card in one link: the title came out as « Chargé d'affaires … - CDI
  Groupe Crédit CoopératifCDIGrenobleDécouvrir ». The link's heading is now the title,
  and the city given beside a location icon is read.
- The fit is now computed in two parts: what the offer says, then the weights. The
  result is unchanged (benchmark: 0 difference).

## 3.17.0 — 2026-10-22

- **Each offer's dates in the table and the card.** New columns « Publiée » (the date
  the posting appeared, when its source gives it) and « Vérifiée » (the last time the
  offer was seen alive: its link checked, or a collection serving it again); the
  former « Date offre » column, which held the day the engine found the offer, is now
  named « Trouvée ». The card shows the three dates on one line.
- **LinkedIn's publication date is read.** Each search result carries it, and it was
  ignored: two thirds of a queue came without a publication date. New offers get it,
  and offers already in the queue receive it when LinkedIn serves them again.

## 3.16.0 — 2026-10-22

- **The experience a posting asks for is read where it was missed.** Seven of the twenty
  offers set aside by October asked for experience the engine had not seen, and kept a
  fit of 10:
  - one word anywhere in the text made the whole offer "junior": « 2 années
    d'expérience minimum (stages et alternance compris) », a line about managing
    interns, an « INTERNSHIP » tag in a job board's footer. The junior test now reads
    the job title;
  - « expérience confirmée », « solide expérience », « proven experience » and
    LinkedIn's « Niveau hiérarchique : Confirmé / Mid-Senior » count as 3 years,
    « Directeur / Director » as 7;
  - a range asks for its lower bound: « 3 à 5 ans » is met with 3 (it was read as 5,
    which reached the sort's limit and removed offers a three-year candidate qualifies
    for);
  - not the team's or the company's years: « une équipe apportant en moyenne 10 ans
    d'expérience », « 15 years of working together », « 10 ans d'expertise », the « 5 »
    of « 3.5 years ».
- On a real queue of 10,425 offers: 1,630 requirements raised, 836 lowered; 181 offers
  now ask for 5 years or more and leave the queue at the next sort (applications kept,
  as always).

## 3.15.1 — 2026-10-22

- **Fold the left menu to give the table the whole width.** The button at the top left,
  named « Outils », already did it, but nothing said so: it is now « « Réduire le menu »
  (« ☰ Menu » to open it again), with a « « » in the menu's header too, and Ctrl+B. The
  choice is remembered for the next start (`data/_vues.json`).

## 3.15.0 — 2026-10-22

- **A copy of each posting you apply to.** Offers close and their page goes — 2,868
  left the queue in one week of October — and the interview invitation arrives three
  weeks later. When an offer is marked « postulé » (or any status after it), its posting
  is written once to `Letters/Postings/` as a PDF to read and a .txt to search, with the
  company, link, place, contract and salary. It is never rewritten: it is the version
  you applied to. The offer's card links to it. Morning step 4a and `jobhunter postings`
  catch the statuses set elsewhere (apply runner, emails).
- **Every status change is kept.** An application kept only its last status: « postulé »
  on 3/10 became « refus » on 21/10 and the day of sending was gone. Each entry now has
  its history (`h`), written by every program that changes a status, without any of them
  knowing it. The card shows it; the Statistics panel adds **Candidatures envoyées**:
  answers and answer rate, interviews, silence after 30 days, median time to answer,
  answers by contract and by field.
- **Knock-out conditions flagged.** A posting that requires a driving licence, a
  nationality, the right to work in a country, or a security clearance got a CV and a
  letter like any other. These are now found in the text (FR, EN, DE; a softened « a
  plus » / « souhaité » is not a requirement) and shown first in the Signal column and
  the card, never removed. The profile can say what you meet: section
  `eliminatoires` — `permis`, `habilitation`, `droit_de_travail` (FR, EU, UK, US…),
  `ignorer`. « No visa sponsorship » is ignored in Europe for a profile with EU or FR.
- **New ⚑ column**, before the company: ⚠ knock-out, ↻ reposted three times or more,
  ≡ same text under another company. The full text is in the card.
- **The order of the offers is the rank**: the decimal fit, minus 0.3 for an offer
  reposted three times or more in 90 days (often a « ghost » posting), plus a bonus per
  contract if your profile sets one (`classement` section: `malus_republiee`,
  `republiee_des`, `bonus_contrat`). The fit shown does not change. The table, the
  folders to prepare, the alerts and the daily selection follow it.
- **`jobhunter evaluation --analyse`**: where the ranking disagrees with your own
  choices (by contract, field and zone), and which contract bonus would help — kept only
  if the gain survives resampling, so a few dozen judgements do not teach the ranking
  their accidents.
- **Silent companies.** A company whose career page moved does not fail loudly: its
  feed answers, empty, every morning. The Companies panel and `jobhunter yield` now name
  the feeds silent for 30 days: failing, empty page (the address has probably changed),
  or offers but none for your profile.
- **Offers screen redesigned.** Company and job title were cut to ten letters while
  Country and Region (« Europe » on almost every row) took the room: both are now one
  click away in « Colonnes ▾ », and the two main columns share the width at every size.
  The three indicators sit on one line instead of three cards under a second title. The
  card's actions fit on one row, so the card shows the signal, the facts, the
  application and its history, the file and the kept posting at once.
- Fix: saving the tracking from the card replaced the whole entry, erasing the proof of
  sending and the email it cited. It now keeps them.
- « Candidatures envoyées » counts every application sent, not only those still at
  « postulé ».

## 3.14.1 — 2026-10-22

- `jobhunter app --help` prints a line instead of opening the window. It used to open
  it, and the window's background collection of company sites then kept running after
  the caller closed it.

## 3.14.0 — 2026-10-22

- **Workday, Ashby and Greenhouse offers really checked.** Their pages are drawn by
  JavaScript: the availability check received the same empty page, open or closed, and
  kept every offer. Measured on 21 October: 304 Workday offers checked, not one found
  closed — their API said half were withdrawn. The check now asks the ATS itself:
  Workday per offer (a withdrawal answers « S22 »), Ashby through the company's board
  (an offer no longer listed is closed), Greenhouse per offer. An unclear answer still
  falls back to reading the page, so a live offer is never removed on a doubt.
- **« Signal » column** (« Colonnes ▾ » to show it):
  - « republiée ×2 » — the offer came back under a new address on the same site, on a
    later day, within 90 days. An employer that keeps reposting a job is often not
    hiring for it right now. A better link found on the employer's site does not count.
  - « même texte : X » — another company publishes the same text: often an agency or a
    job board reposting the employer's offer. « doublon : X » when the two names are
    one group (« VINCI » / « VINCI Construction »).
  - Observations only: the fit, the sorting and the queue are untouched. New pipeline
    step 4a; `jobhunter reposts --sauvegardes` dates the addresses from the daily copies
    of the queue, so reposts show from the first day.
- Known limit: two identical titles opened in parallel at one company look like a repost.

## 3.13.1 — 2026-10-21

Three fixes found by reading the code of two large job-search projects (career-ops,
ai-job-search) side by side with ours.

- **Closed offers recognised in every language of the offers.** The availability
  check only read French and English closure banners, while offers abroad are wanted:
  « Diese Stelle ist bereits besetzt », « Deze vacature is niet meer beschikbaar »,
  « esta oferta ya no está disponible », « non è più disponibile », « vaga não está
  mais disponível » now close the offer too. The page is normalised first (typographic
  apostrophes, accents): « n’est plus disponible » written with ’ was missed. A live job
  about « closed-loop control » is not taken for a closed one.
- **Emails: fewer wrong suggestions, short company names found.** « Unfortunately we
  need to reschedule your interview » was suggested as a rejection, and an
  acknowledgement promising « next steps » as an interview. Phrases now come in two
  tiers: a strong one is enough, weak ones (« unfortunately », « regret to inform »)
  need a second one. EY, HP, 3M were never recognised (names under three letters were
  dropped); they now are, as whole words only — not « hp » inside « PHP ».
- **robots.txt read safely.** A file starting with a byte-order mark made Python's
  reader ignore its first rules — a `Disallow` was skipped (measured). The mark is
  removed before reading. The file is also fetched with a total time limit: the old
  reader had none, and a slow host could hold the scan.

## 3.13.0 — 2026-10-21

- **The morning collection, visible in the app.** Under « Actualiser les offres », one
  line says how the last collection went: « Collecte du matin : aujourd'hui 08:04 ✓ »
  (with the steps in error, if any), « en cours depuis… », « interrompue » (the computer
  was shut down halfway), « arrêtée » or « Pas de collecte depuis hier 08:04 ». When it
  is due, « Lancer la collecte du matin » runs the very pipeline the scheduled task
  runs — no terminal, no one to call. The line is read again every five minutes.
- The pipeline records that state in `_derniere_collecte.json` (start, end, code, run
  identifier, log, last success). A morning where one step failed (a source refusing,
  a folder to review) counts as a collection done, not as a failure; a quick test run
  (`--rapide`) does not count at all.
- **A sturdier daily task.** « Collecte chaque matin » now creates the task from a full
  definition: a morning missed because the computer was off or asleep is caught up as
  soon as it is back, the collection also runs on battery, it is stopped after 8 hours
  at most, and the task no longer has a start-in folder — a renamed folder made Windows
  refuse to start the author's task, silently, on 21 October.

## 3.12.0 — 2026-10-21

- **Saved views.** « Vues ▾ » above the table keeps the current filters, sort, search
  and columns under a name (« ESG Paris, fit first ») and brings them back in one click;
  « Vue par défaut » clears everything. Views belong to the active profile
  (`_vues.json` in its data folder). A view saved before a column was renamed still
  opens, without that column.
- **Columns you choose, remembered.** « Colonnes ▾ » is now a menu with one tick per
  column, plus « Vue compacte » and « Toutes les colonnes »; the choice survives a
  restart. The width freed by hidden columns goes to the job title and the company
  instead of blank space, and « Fit » is wide enough for « 10.2 ».
- **Document viewer.** An edited letter shows « ● » in its title and on the
  « Enregistrer » button, which stands out until it is saved (Ctrl+S saves). Choosing
  another document or leaving the panel asks whether to save the changes, instead of
  dropping them. « ＋ / － » also zoom a Word document's text, and the viewer says when
  Word holds the document open. The zoom and save buttons no longer fall out of a
  900-pixel-high window, and a long file name no longer hides the buttons beside it.

## 3.11.1 — 2026-10-21

- A release the author has not signed yet is now refused with a clear reason
  (« la version X n'est pas encore signée par l'auteur ») instead of a bare download
  error, and the installed application no longer opens the releases page for it.
  Nothing is installed either way.
- CI: the real-update test waits for the author's signature whenever the new version
  carries the key, and the installer test checks the signed update path (refused
  unsigned, installed once signed, with a throwaway test key).

## 3.11.0 — 2026-10-21

- **Signed updates are now active.** The author's public key is published in this
  version (`82c0f5a387a2be07…`, full value in `src/jobhunter/signature.py`). From now on, an
  update is installed only if the author signed it, outside GitHub, with the private key
  that never leaves their computer: a hijacked GitHub account or workflow can no longer
  push a booby-trapped version to your installation. This version itself is the last one
  installed without a signature, as planned (ADR 0012).
- If an update is ever refused with « Mise à jour refusée », nothing was installed and
  your data is untouched: wait for the signed release, or take the installer by hand.

## 3.10.2 — 2026-10-21

- **Security: certifi 2026.10.19.** The bundle of root certificates that JobHunter's web
  requests trust (certifi, through httpx and requests) carried emSign root authorities
  whose intermediate keys were compromised; a server holding such a key could pass for
  any site. JobHunter now requires certifi 2026.10.19 or later, which removes them. The
  Windows installer ships it; from source, the update installs it.

## 3.10.1 — 2026-10-21

- `jobhunter migrate` no longer gives up on a folder held open by another program. On
  Windows, a folder watched by an indexer, a sync tool or a file watcher cannot be
  renamed although everything inside it can be moved (seen on a real `Lettres/`): the
  migration now moves its content one item at a time into the new folder and leaves the
  old one, empty, telling you to delete it once it is freed. If anything else fails,
  everything is still put back as it was.

## 3.10.0 — 2026-10-21

- **Documents à comparer.** Since 3.7 a CV or letter you edited by hand is never
  overwritten: the new version waits beside it, in `_a_comparer/`. Maintenance →
  « Documents à comparer… » now lists them, shows the paragraphs that differ (red: only
  in yours, green: only in the new one) and lets you choose. The version you do not keep
  is set aside in `_a_comparer/_anciennes/`, never deleted.
- **Companies: suspend, and see each one's last collection.** The Companies panel gains a
  « Dernière collecte » column — ✓ date and offers, or ⚠ the incident (HTTP 404, timeout…)
  with its date — and a « Suspendre / Reprendre » button. A suspended company is no longer
  collected; it stays in the list, and its offers and applications are untouched. A
  refused collection keeps the date of the last success: a page that refuses us is not a
  closed page.
- **Which collection found this offer.** Every run has an identifier
  (`20261021-080012-a3f9`) shared by all the steps of the morning pipeline. It is written
  on new offers, on score changes, on site changes and on the yield log; the offer's card
  shows it under « Trouvée par », and `jobhunter yield --execution <id>` says what that run
  brought back.
- **Cleanup recipes.** Maintenance → « Recettes de nettoyage… »: one rule per line,
  `champ | value | new value` (company, place or contract; `re:` for a pattern), e.g.
  `entreprise | PricewaterhouseCoopers | PwC`. « Aperçu » lists every change on your queue
  before anything is written; replaying the same recipes changes nothing the second time.
  An offer you applied to is never renamed (its name identifies your application), and a
  rename that would create a duplicate is skipped — both are shown. Same from a terminal:
  `jobhunter recipes`, then `--appliquer`.
- **Collection progress, without a console.** While a collection runs, a line under the
  log shows each source: running (…), done with its offers (✓ 693), refused (⛔), limited
  (⏸), nothing to take (∅). At the end, one concrete sentence replaces « terminé »: new
  offers, how many sources answered, which ones refused or were cut.
- **Active filters you can see.** Each filter set in a column header, and the search
  words, now show as a label under the counter, each with its ✕, plus « Tout effacer »
  when there are several. A hidden column could filter the table without anything saying
  so.
- Design: outline buttons (« Annuler », « Fermer »…) had white text on a light background
  and could barely be read; IBM Plex Sans is used when it is installed.
- **APEC and Glassdoor leave `--all`.** Every collection measured since 7 October was
  refused: APEC answers 403 behind DataDome and a CAPTCHA page, Glassdoor behind a
  Cloudflare challenge (checked again on 21 October). JobHunter does not get around such
  protections, so the morning pipeline no longer asks; `--apec` and `--glassdoor` still
  run them on request. EURES stays: its refusals of 20 October were temporary and it
  answers normally again.
- For contributors: ruff 0.17.

## 3.9.1 — 2026-10-20

- For contributors: the test files have English names too (`tests/test_update.py`,
  `test_profiles.py`, `test_my_search.py`…), the last French names of the code base. No
  change for users.
- The shared test browser lives per test module: a test that starts its own browser no
  longer depends on running first.

## 3.9.0 — 2026-10-20

- **"Ma recherche", in the app.** A new panel (second in the sidebar) edits what you
  search without opening `profile.json`: the search keywords, the words a title must
  contain, the words that set a title aside. Nothing is written before "Enregistrer";
  the previous profile is kept as `profile.json.bak`; a pattern that does not compile is
  refused with a clear message.
- **"Aperçu sur ma file"**: before saving, the engine's real title filter runs on the
  offers already in your queue, with your current settings and with the new ones, and
  tells you how many would be set aside, with examples. Nothing is collected or changed.
- **"Suggestions depuis mon CV…"**: JobHunter reads a CV on your computer and proposes
  the skills it attests that your profile does not list yet — each with the sentence of
  the CV that proves it — and matching search keywords. Nothing is added until you tick
  it. A search keyword never enters your CVs or letters.

## 3.8.0 — 2026-10-20

- **Why a score changed.** When an offer's fit changes — its full description arrived, or
  it was re-scored with a changed profile or a new engine — the offer keeps the change:
  date, new fit, cause, and the rules in force (engine version and a fingerprint of the
  profile's scoring sections). The offer's card shows it under "Historique du score",
  and says when the rules changed between two scores. An unchanged score records
  nothing; at most ten entries per offer.

## 3.7.0 — 2026-10-20

- **Your retouches are never overwritten.** A CV or a letter you edited by hand (in Word,
  or in the app with "Enregistrer") stays as you left it when JobHunter regenerates the
  documents: the new version goes into `_a_comparer/` next to it, and the log says how
  many paragraphs differ. Delete your version to take the new one. Documents generated
  before this version are replaced as before the first time, then protected.
- **An older JobHunter never writes over newer data.** Each data folder records the format
  of its data (`_format.json`); a version that only knows an older format refuses to write
  there and asks to be updated — reading stays allowed. Useful with two computers, or an
  old installer run again.

## 3.6.0 — 2026-10-20

- **"Why this fit" in your language.** The explanation of an offer's score (vocabulary,
  caps, junior or senior title, language of the posting, experience asked for) now
  follows the interface language. The skills it names stay as your profile writes them.
- **Test an API access** (Access panel → "Tester la connexion"): one minimal request with
  the saved key for Adzuna, Jooble or France Travail, no offer imported, then a plain
  answer — the key works, no key saved, key refused, quota reached (the key is fine), the
  service is in error, or no answer. The key is never shown, not even in an error.

## 3.5.0 — 2026-10-20

- **Profiles from a terminal**: `jobhunter profiles` lists them (the active one marked),
  `use <name>` switches, `new <cv> --name "…"` creates one with the usual questions,
  `rename` and `archive`.
- **Rename or archive a profile**, also in the app (Maintenance → "Profils…"). A name
  changes without touching the folder or the profile file. Archiving moves the profile to
  `profiles/_archives/` — nothing is deleted — and never while a collection runs for it.
- **API quotas shared between profiles.** The Adzuna, Jooble and France Travail keys serve
  every profile, so the calls are now counted for the day all profiles together. Adzuna
  stops at 250 calls a day (its free access) instead of being refused by Adzuna for the
  rest of the day; the others are counted. Ceilings can be changed in
  `sources_config.json` (`"quotas_api": {"adzuna": 250}`). The Access panel shows today's
  calls.
- **Countries and regions in your language** in the offers table (the data and the
  filters of your profile keep the French names).
- My CVs panel: the bulk tools ("MAJ lettres", "Renommer (mon nom)", "Faits du CV") have
  their own row; at 1320 px they went off the window.

## 3.4.0 — 2026-10-20

- **The update installs exactly the announced version.** Without the author's signature,
  an installation from the ZIP took the current state of the repository (`main`), which
  could already hold changes not yet published; it now takes the published version's
  archive, like the signed update does.
- **Never during a collection.** The update waits for the queue of every profile to be
  free (30 s at most); if a collection or a document generation is running, nothing is
  touched and it says so (code 3). The installed application no longer opens its
  installer — which closes JobHunter — in the middle of a morning collection.
- **The new version is confirmed at start-up.** After an update, the next start of the
  app says "Mise à jour confirmée : JobHunter X a démarré", or that the update did not go
  through (installer cancelled, old copy still launched) and what to do.
- With a secondary profile active, the update looked for the program in that profile's
  folder and refused; it now always works on the installation's folder.
- A real update is tested after each release: the two previous versions, installed from
  their ZIP on Windows and Linux with invented data, update themselves; the new version
  must be running and every piece of data byte for byte the same.

## 3.3.0 — 2026-10-20

- **Where an offer was found.** The same posting often arrives from several places
  (a LinkedIn search, the company's Workday, Welcome to the Jungle…). The queue kept only
  the best link; the offer's card now lists every source and search that found it,
  under "Trouvée par": you see which searches are worth keeping.
- **What its site changed.** When the site that published an offer serves it again with a
  different title, salary, contract or place, the card says so under "Modifiée par son
  site" (date, before → after). Only a site compared with itself, so two sites wording a
  place differently is not a change; your queue's values are never replaced.
- **The table follows the queue.** When the morning collection, a terminal or a second
  window writes the queue while the app is open, the table reloads by itself (every 15 s,
  never while you type or while a step of the app runs). No more Ctrl+R.
- The offer card's labels (contract, place, application file…) follow the interface
  language.
- README screenshots of the English interface, rebuilt by `tools/screenshots.py` on a
  fictitious profile.

## 3.2.0 — 2026-10-20

- **Several profiles, several searches.** Maintenance → "Profils…" lists your profiles
  and creates a new one from a CV (or drop a CV on the window and choose "Nouveau profil
  depuis ce CV"). Each profile is a complete workspace of its own — queue, applications,
  CVs, letters — in `profiles/<name>/` inside the JobHunter folder, so two searches never
  mix. Your current profile stays where it is.
- Switching profile restarts JobHunter on the chosen one. The sidebar shows the active
  profile as soon as there are two.
- The morning collection runs every profile, one after the other, each with its own log.
  The scheduled task does not change.
- The API keys (Adzuna, Jooble, France Travail) and Gmail access are shared: they stay in
  the main profile and are never copied.
- `jobhunter pipeline --un-profil` runs only the active profile.

## 3.1.0 — 2026-10-20

- **Drag your CV onto JobHunter.** On the welcome window (no profile yet), drop your CV
  in the box instead of looking for it. In the app, drop a `.docx` or `.pdf` anywhere on
  the window to replace your base CV: the old one is kept as `.bak`, and JobHunter offers
  to redo the CVs already prepared for the offers. The CV panel has the same thing as a
  button, "Remplacer mon CV de base…", for those who prefer a file dialog.
- New dependency: `tkinterdnd2` (drag-and-drop for Windows, macOS and Linux). Without it,
  everything works as before, with the buttons.

## 3.0.0 — 2026-10-20

- **Your folders in English.** `Scripts/` → `data/`, `profil/profil.json` →
  `profile/profile.json`, `Mon_CV/` → `My_CV/`, `Lettres/` → `Letters/`; inside:
  `Par_offre` → `By_offer`, `Modèles` → `Templates`, `Sur_mesure` → `Tailored`,
  `Relances` → `Follow_ups`, `suivi.json` → `applications.json`, `Faits.json` →
  `Facts.json`, `_sauvegardes` → `_backups`, `_preuves` → `_proofs`…
- **Nothing to do.** The first time the app starts after this update, your folders take
  their new names by themselves, after a backup (`_backup_migration_<date>.zip` in the
  JobHunter folder, with everything that cannot be rebuilt). The links of your CVs and
  letters are rewritten, then checked: same offers, same applications, no document lost —
  otherwise everything is put back as it was and JobHunter carries on as before. A file
  that you changed and that the update also ships stays yours; the new one is set aside
  as `.nouveau`.
- `jobhunter migrate` does it by hand (`--verifier` only says whether it is needed). In a
  folder without a `VERSION` file (a development copy, or a folder that installs the
  engine with pip), it is never automatic: the French names keep working there.
- The launchers recognise both layouts until the migration.

## 2.25.0 — 2026-10-20

- **Programs and files in English.** The packages and modules took English names
  (`jobhunter.programmes` → `jobhunter.programs`, `stockage` → `storage`, `courriels` →
  `mail`, `racine` → `root`, `chemins` → `paths`, `profil` → `profile`, `gele` →
  `frozen`; programs such as `pipeline_quotidien` → `daily_pipeline`, `audit_dispo` →
  `availability_audit`, `premier_lancement` → `first_launch`, `mise_a_jour` → `update`,
  `relances` → `follow_ups`; the app's `fenetre` → `window`, `panneaux` → `panels`…).
  The full table is `src/jobhunter/_old_names.py`.
- **Commands in English**: `jobhunter collect`, `sort`, `regenerate`, `availability`,
  `restore`, `yield`, `check`, `proofread`, `mail-statuses`, `apply`, `add`, `profile`,
  `check-profile`, `show-profile`, `update`.
- **Launchers and tools**: `lanceurs/` → `launchers/` (`install`, `start`, `schedule`,
  `update`, in `.bat` and `.sh`), `outils/` → `tools/` (`bench.py`, `replay.py`,
  `installer/`…).
- **Nothing breaks.** The French names keep working: `jobhunter collecte`, `maj`,
  `postuler`…, a program by its old file name (`jobhunter relances`), and in code
  `import jobhunter.programmes.jutil` or `python -m jobhunter.programmes.x` reach the
  same module as the new name. A collection already scheduled keeps working.
- Your data (`Scripts/`, `profil/`, `Mon_CV/`, `CV/`, `Lettres/`) and the profile's keys
  do not change in this version.

## 2.24.0 — 2026-10-20

- **A tidier folder.** The eight double-click tools (`installer`, `lancer`, `planifier`,
  `mettre_a_jour`, in `.bat` for Windows and `.sh` for macOS/Linux) moved from the root
  into a `lanceurs/` folder: double-click them there, they still work on the JobHunter
  folder above. `CONTRIBUTING.md` and `SECURITY.md` moved to `.github/`, where GitHub
  shows them the same way. The README lists what each folder holds.
- If you update with `mettre_a_jour.bat`, its window may close at the end, because the
  update removes it from the root: that is expected, the update is done. Use
  `lanceurs\mettre_a_jour.bat` from now on, or the app's "Mettre à jour JobHunter" button.
  The daily collection already scheduled keeps working (it runs `JobHunter.pyw`, which
  did not move).
- macOS/Linux: after an update, the `.sh` launchers are made executable again.

## 2.23.1 — 2026-10-20

- **Tested on macOS.** CI now runs `installer.sh` on a Mac runner, then the bench and
  the whole test suite in the environment it built, including every panel of the app in
  every language. It is part of the required check.
- Fixed on macOS/Linux: a document linked by a standard `file:///Users/…` URL was read
  as a relative path, hence "not found"; links are now written with three slashes
  (they had four on a Mac), and the old four-slash links still read. Windows links are
  unchanged.

## 2.23.0 — 2026-10-20

- **The app in German and Spanish**, as well as French and English. Maintenance →
  “Langue / Language…” lists the languages, each under its own name; the choice
  applies at the next start. The interface, the log and the reports of the programs
  it launches are translated; your letters, CVs and profile keep their language.
- A few texts of the offer list were still in French in every language (search and
  link fields, the offer count, the help of the details pane): translated.

## 2.22.2 — 2026-10-20

- **The Access panel opens even with a damaged log**: a line of the collection log cut
  mid-character (power cut, crash) kept the panel from opening. Only that line is now
  skipped.
- **Every panel tested as you open it**: Offers, CVs, Companies, Job sites, Statistics
  and Access are opened with no console, as the installed app runs, then again with
  damaged data files; each one must display and the next button must still work.
- **A new README**, in English and French: what JobHunter does differently, how it works,
  the sources it reads, and what backs it.

## 2.22.1 — 2026-10-20

- **Job titles in letters**: a title such as "Analyste ESG - H&M - H/F" became
  "Analyste ESG - H&" (the M of H&M was taken for a gender mention), and a mention
  written with long dashes ("Analyste – F – H") was only removed by a second cleaning.
  Both fixed; none of your 10,455 current titles changes.
- **Tests on generated cases**: the cleaning of titles, the URL duplicate key, the score
  and the merge are now checked on thousands of generated inputs, not only on the
  examples written by hand. This is how the two title bugs were found.
- The automatic tests also run on Python 3.14, the version the application uses.

## 2.22.0 — 2026-10-20

- **Undo a clean-up**: `jobhunter restaurer` puts the offer queue back as it was in a
  backup — the daily one, the one taken before the availability check, or before a sort.
  `jobhunter restaurer --liste` shows them; with a name, it first says which offers would
  come back and which would leave, and writes only with `--appliquer`. Your applications
  (suivi.json) are never restored and their offers stay; no description is lost; the
  state before is kept, so a restoration can itself be undone.
- **Network failures, proven**: every company career feed reader is tested against a
  refusal, a rate limit, a server error, a timeout and an unreadable answer; each one is
  reported as an incident, never as "nothing new today".
- The last French comments and docstrings of the code are in English.

## 2.21.1 — 2026-10-20

- **English file names for the documentation**: `docs/programs.md`, `docs/roadmap.md`,
  `docs/professionalisation-plan.md`, `docs/screenshots/`, the twelve decisions in
  `docs/adr/`, the agent rules in `.claude/rules/` and the issue templates. Every link and
  every "Decision:" citation in the code follows.
- The Claude Code command that sets up your profile is now **`/configure-profile`**
  (formerly `/configurer-profil`).

## 2.21.0 — 2026-10-20

- **The repository is in English.** Every comment and docstring of the code, the
  documentation (architecture, programs and their pitfalls, decisions, plan, roadmap,
  contributing guide, this changelog) and the instructions for coding agents are now in
  English. Function names, profile keys and JSON keys stay in French: renaming them would
  break existing profiles and data. The French README stays as `README.fr.md`.
- **Tidier repository**: an index of the documentation (`docs/README.md`) and of the
  developer tools (`outils/README.md`); `Mon_CV/LISEZ-MOI.txt` also says it in English.
- Nothing changes in what the program does: the non-regression bench gives the same
  decisions, offer for offer.

## 2.20.0 — 2026-10-20

- **Statuses from your emails** (`jobhunter statuts-mail`, or Maintenance →
  "Statuts depuis mes courriels…" (Statuses from my emails)): rejections, interviews and
  acknowledgements of receipt recognised in French, English and German, matched to your
  applications, and proposed **one by one**; nothing is written without your approval, and
  a status only ever moves forward. The emails come from an export (a Google Takeout
  .mbox file, a folder of .eml files), with no key at all, or from the Gmail API in
  **read-only** mode, with an OAuth client that you create yourself
  (`pip install "jobhunter[gmail]"`); the program never sees a password.
- **Keyboard use**: every button can be reached with Tab and triggered with Enter or
  Space, with a visible focus ring; the outline of input fields is easier to see (3:1);
  text contrast checked (WCAG AA). A screen reader still cannot see the controls: the
  interface library does not allow it.

## 2.19.0 — 2026-10-19

- **Collection every morning, from the application**: Maintenance → "Collecte chaque
  matin…" (Collection every morning) creates the Windows task at the chosen time (or
  removes it). It is the same task as `planifier.bat`; the installed application, without
  Python, can finally collect on its own.
- **The installed application is tried at every build of the installer**, on a fresh
  Windows machine **without Python on the PATH**: the window opens and stays open; the
  system browser starts; a fictitious scan is merged into the queue; an application folder
  is written; the update downloads, checks and prepares the next installer, which installs
  over the old one while keeping the data.
- Architecture document of the standalone application (ADR 0011) updated.

## 2.18.0 — 2026-10-19

- **One-click update of the installed application**: the "Mettre à jour" (Update) button
  downloads `JobHunterSetup.exe`, checks it, then opens it (it closes JobHunter and keeps
  your data). Before, it opened the releases page.
- **Updates signed by the author** (ADR 0012): Ed25519 signature made outside GitHub, with
  a key that never leaves the author's computer. A release in which a file, or the
  installer, is not the one the author signed is refused, and nothing is written; an old
  signature does not make you go back to an earlier version. Active as soon as the
  author's public key is in the code; until then, the update works as before, and the
  application at least checks the published fingerprint of the installer.
- Author's tool: `outils/signature.py cle` (once) and `signer X.Y.Z --publier` (for each
  release). Procedure in CONTRIBUTING.
- **Installation from source tested on fresh machines**: the "installation" workflow runs
  the real `installer.bat` and `installer.sh` (Windows, Linux) and checks that the
  libraries go into `.venv`, that the program loads and that the update ignores `.venv`.

## 2.17.0 — 2026-10-19

- **The app's log in English, programs included**: the summaries of the collection
  (sources, yield, merge) and of the "TOUT FAIRE" (Do everything) steps (descriptions,
  re-scoring, dead links, export, alerts) are translated. The offer-by-offer detail
  (company and job titles) stays as it is.
- Fixes from a second Codex audit, on the code of versions 2.12 to 2.16:
  - **The reviewer is no longer fooled by an address that imitates a known one**:
    `acme.fr.evil.test` or `evil.test/acme.fr` were taken for the site `acme.fr`. Hosts
    are now compared whole, at a dot boundary.
  - **Every addressee of the salutation is checked** against the job posting ("Madame
    Martin, Madame Dupont,"), not only the first.
  - **Two simultaneous entries of an API key no longer overwrite each other**: the write
    is done under a lock. Every JSON write uses a temporary file of its own.
- **Installation from source: a separate Python environment.** `installer.bat` (and
  `installer.sh`) creates `.venv` in the JobHunter folder and installs the libraries
  there, without touching the computer's Python. `lancer`, `mettre_a_jour` and `planifier`
  use it when it exists; an older installation keeps running on the system Python. The
  update never touches `.venv`, nor `Scripts/francetravail.json`.
- A queue that is busy during the merge now advises `jobhunter collecte --fusion-seule`
  (the message still quoted the old `job_sources.py`).

## 2.16.0 — 2026-10-19

Fixes from an audit of the repository (Codex, 19/10): four possible data losses and four
defects, each reproduced then covered by a test.

- **The link check no longer overwrites a collection** that was merging during its checks:
  the network work is done outside the lock, then only the results are applied to the
  re-read queue. The purge of dead links spares the offers in the tracking file.
- **An unreadable tracking file is never replaced**: if `suivi.json` exists but cannot be
  read (truncated file), every write is refused and the file left as it is, instead of
  starting again from an empty tracking file that wiped out all the applications.
- **A failure while writing the queue no longer loses a description**: orphan texts are
  purged only once the queue has been written.
- **The merge no longer removes a tracked offer** when a filter or a modified profile
  rejects it: an application keeps its record.
- A nested transaction no longer releases its caller's lock.
- A posting recognised by its link, under a corrected title, receives its description.
- The update installs the dependencies before checking the new version, and a pip failure
  rolls back to the previous version instead of announcing "up to date".
- "TOUT FAIRE terminé" (Everything done) is no longer displayed after a failure: the log
  names the interrupted step.
- CONTRIBUTING: py-spy procedure to locate a slowdown. Roadmap: the pywinauto probe
  concludes that the interface is invisible to UI Automation.

## 2.15.0 — 2026-10-19

- **"Pourquoi ce fit"** (Why this fit) in the record of each offer: the skills found per
  axis, the vocabulary score, the cap and its reason (title of the core target, secondary
  target job, HSE or off-target veto), the title's bonuses and penalties, the posting's
  language and the experience requested. The score does not change: it is the same
  calculation, explained (`scoring.fit.expliquer`).

## 2.14.0 — 2026-10-19

- **Review of the letters** (`jobhunter relecture`, or Maintenance → Documents →
  "Relire les lettres" (Review the letters)): a second pass that flags, without rewriting
  anything, what is wrong in a letter — a candidate who undersells themselves, an empty
  superlative, "excellent" for a language, an em dash or a slash, repetitions, another
  company named (copy-paste), an addressee that the posting does not name, and what a
  booby-trapped posting could have slipped into a letter written by AI (an instruction to
  the model, an unknown address).
- **Folder check**: a title in square brackets ("[Open to internal and external
  applicants]") is no longer mistaken for a forgotten template.
- Maintenance menu: "Contrôler les dossiers" (Check the folders) added; "Tests live"
  relaunched (it pointed to a file removed in 2.0).

## 2.13.0 — 2026-10-19

- **Directory of 3,600 companies** in the Companies panel: type a name ("Alan", "Qonto"…)
  in the add field or click "Annuaire" (Directory), choose, and the company is followed
  through the public API of Lever, Ashby or Greenhouse from the next collection. No web
  search: the directories come from the jobsync project (MIT licence), shipped with the
  application. A company that is already followed is marked.
- **Interface in English, log included**: the application's messages (selection,
  cancellation, backup, updates, reminders…) and its dialog boxes follow the language
  setting. The output of the programs it launches stays in French.

## 2.12.0 — 2026-10-19

- **API keys entered in the application, in the right place.** Access panel: choose
  France Travail, Adzuna or Jooble, then "Saisir la clé" (Enter the key) (or double-click).
  A small window asks for the fields, hides the secret, and writes the file that the
  source really reads (`Scripts/francetravail.json`, `adzuna.json`, `jooble.json`). Before,
  the France Travail button stored the key in `api_keys.json`, which no source reads: it
  was never used. `jobhunter acces --set-key francetravail` follows the same rule.
- **Collect a single source** from the Access panel, to try a key straight away. A source
  refused less than 30 days ago stays blocked; an official API that refuses the key
  displays "clé refusée — vérifie-la" (key refused — check it) and is retried as soon as
  the key is corrected.
- Access panel in two tabs, "Collecte des offres" (Offer collection) and "Connexions pour
  candidater" (Logins for applying): the second table no longer runs off the screen.
- Companies panel: a filter (name, tool, address) and an add field that says what to
  paste.
- The application without a console (`JobHunter.pyw`, the exe) can no longer trip over a
  module that sets the console encoding at load time.

## 2.11.0 — 2026-10-19

- **Lever in Europe.** Some companies are hosted in Lever's European region: their feed
  answered "not found" and their offers were missing. The collection now also looks for
  them on `api.eu.lever.co`.
- **No personal data can enter the public repository**: a check
  (`outils/donnees_perso.py`, run before each commit and by the CI) refuses profile,
  queue, tracking file, letters, CVs and API keys, even when added by force.
- Repository: issue and PR templates, dependency review (a known vulnerability blocks the
  PR), private vulnerability reporting enabled.

## 2.10.1 — 2026-10-19

Security, with no visible change:

- only `http(s)` addresses are opened: a `file://` address coming from a page or a setting
  can no longer make a file on your machine be read;
- an XML sitemap with a DOCTYPE or entities is refused (XML bomb);
- an update archive can no longer write outside the program's folder;
- the installed application ignores the `JOBHUNTER_ACTION` test hook;
- CI: actions pinned by fingerprint, read-only permissions except for publishing, CodeQL
  analysis; the installer is published with its SHA-256 fingerprint and a signed
  provenance attestation (`gh attestation verify`). Policy: `SECURITY.md`.

## 2.10.0 — 2026-10-19

- **The interface in English.** Maintenance → "Langue : English" (Language: English), then
  restart JobHunter: navigation, buttons, panels and headers switch to English
  ("Language: français" to go back). The profile, the letters and the tracking statuses
  keep their language. A text that is not yet translated stays in French.
- **The GitHub repository presents itself in English** (`README.md`); the French version
  is in `README.fr.md`.

*English: the interface can now be switched to English (Maintenance → “Langue : English”,
then restart). The repository README is in English; the French one is `README.fr.md`.*

## 2.9.0 — 2026-10-19

- **JobHunter installs without Python.** `JobHunterSetup.exe`, attached to each release on
  GitHub, installs the application for you alone, without administrator rights, with a
  Start menu shortcut. Your data lives in `Documents\JobHunter`: neither the update nor
  the uninstall touches it. The source code remains downloadable for whoever wants to
  customise it.
- **No more need for Playwright's browser to collect.** If it is not installed, the
  collection uses Chrome or Edge, already on your machine.
- In the installed application, "Mettre à jour" (Update) opens the page of the new release,
  where you download the new installer.

## 2.8.0 — 2026-10-19

The "Entreprises" (Companies), "Accès" (Access) and "Mes CV" (My CVs) panels finally show
correct figures.

- **Companies**: one line per company actually followed, with the tool that reads its
  offers (Workday, Lever, SuccessFactors… or its careers site), the number of offers in
  your queue that come from it, the best fit and the date of the latest. The counts are
  exact: the old panel counted by address fragment (546 offers for "Bil", because of
  "mobilité") and left the ATS column empty.
  - Paste the address of a careers page and click **Suivre** (Follow): a Greenhouse,
    Lever, Ashby, Recruitee, SmartRecruiters, Teamtailor, Workable or Workday is
    recognised and read through its API from the next collection; any other site is read
    by the browser.
  - **Ne plus suivre** (Stop following) removes the company from the collection.
- **Access**: each source of the collection, what it needs (nothing, or an API key) and the
  state of its last collection (ok, refused until a given date, limited, key to create).
  Adzuna and Jooble appear there; Indeed, which has left the collection, no longer does.
  The logins for applying are in a second table. No key and no password is read: only the
  presence of the file counts.
- **My CVs**: one folder per offer, CV and letter together, the best ranked first, with its
  state (✓ ready, ⚠ PDF to redo, ✗ incomplete). The **CV ⇄ lettre** (CV ⇄ letter) button
  switches from one to the other, **Faits du CV** (CV facts) displays your fact bank.
  Before: two flat lists of 1,983 and 1,200 files.
- The window header carries the name of the open page, instead of "Suivi des candidatures"
  (Application tracking) everywhere.

## 2.7.0 — 2026-10-19

- **Ten fewer programs.** One-off repair tools, already run on the data or replaced by
  something better, rarely left their folder and cluttered the list. They are removed:
  - `audit_fraicheur` and `verify_links`: replaced by the availability check
    (`audit_dispo`);
  - `offres_depuis_site`, `probe_ats_esg` and `homepages_linkedin`: replaced by the
    followed ATS feeds and `probe_ats_queue`;
  - `deplace_docs`, `reclasse_domaines`, `redetecte_contrats`, `refresh_desc_efc` and
    `fix_wtj_urls`: repairs done once, now useless. The "Fix WTJ" entry leaves the
    Maintenance menu.

  The code stays in the git history for whoever might need it.

## 2.6.0 — 2026-10-19

- **The right copy of a job posted in several cities.** When a company posts the same job
  in Paris, Lyon and Berlin, only one enters your queue. Until now it was the first one
  seen, at random; it is now the one in your highest-priority zone. The other cities are
  noted, and the record displays them ("Aussi à :" (Also in:)).
- **Reworded titles no longer pile up.** When an employer renames its posting (same link,
  new title), the old versions left in the queue are removed during sorting. Only the
  current version remains, unless you have already acted on another one: the one in your
  tracking file is always kept.

## 2.5.0 — 2026-10-19

- **Your ranking against your choices.** `python JobHunter.pyw evaluation` compares the
  score of each offer with what you did with it: applied or to apply on one side, "bad" or
  "not interested" on the other. It tells whether the offers you keep are scored much
  higher than those you set aside (with the margin of uncertainty), and which ones the
  ranking overestimates or underestimates the most. `--enregistrer` keeps the result for
  later comparison. The more offers you mark, the more reliable the figure.

## 2.4.3 — 2026-10-19

- **Sample configuration**: 10 of the 16 Greenhouse accounts no longer answered (404):
  those companies now recruit elsewhere. 7 were found again and follow their new tool
  (Lever: Pigment, Swile, Vestiaire Collective; Ashby: Back Market, Sweep;
  SmartRecruiters: EcoVadis; Recruitee: iBanFirst). ClarityAI, Payfit and Spendesk are
  removed. If your configuration still contains them,
  `python JobHunter.pyw probe_ats --slugs <nom>` looks for their new tool.
- Behind the scenes: the sources are tested against real recorded responses, replayed
  without network.

## 2.4.2 — 2026-10-19

- Behind the scenes, nothing visible: every public function of the engine is documented in
  the same format, and the checking tool now requires it.

## 2.4.1 — 2026-10-19

- Behind the scenes: the folder of your data (`Scripts/`) is no longer added to Python's
  import path. It was a leftover from the old organisation: a `.py` file dropped there
  could take precedence over a program module of the same name. Nothing changes in use.

## 2.4.0 — 2026-10-19

- **What each source brings in.** At the end of each collection, one line per source:
  offers returned, new ones, relevant ones (fit ≥ 8), time spent, and a verdict that says
  WHY: "ok", "rien à prendre" (nothing to take; a quiet day), "limité" (limited; the site
  asked to slow down), "partiel" (partial; errors along the way) or "refusé" (refused;
  access denied, CAPTCHA). An empty collection no longer looks like a day without news.
- `python JobHunter.pyw rendement`: the summary of the last 14 days (`--jours 30` for
  more), the most profitable sources first; a source refused at every collection is
  flagged. No circumvention: removing it is decided by hand.

## 2.3.0 — 2026-10-19

- **Every folder is checked before it goes out.** For the CV and letter that will really be
  attached: the file exists, opens, contains text, fits on one page, carries your name,
  email and phone, and no template was left empty ("[nom du poste]"…). The Applications
  panel displays it for each offer, and so does the record; a folder to review blocks
  nothing, you decide.
- **The right file is attached**: when an offer pointed to the letter in .docx while its
  up-to-date PDF existed next to it, the PDF is now the one that goes out.
- `python JobHunter.pyw controle`: summary of all the folders, without modifying anything.
  The daily routine does it too after the folders and alerts you if some need review.

## 2.2.0 — 2026-10-19

- **Apply from the application, without a console.** Tick offers, "Postuler la sélection"
  (Apply to the selection): a panel opens. For each offer, JobHunter opens the page in
  Chrome, fills in the form, attaches the CV and letter and highlights the submit button.
  You check, **you click Submit in Chrome**, then "J'ai envoyé" (I have sent it) in the
  panel. Buttons: Sauter (Skip), Re-remplir (Fill again), Rouvrir l'offre (Reopen the
  offer), Arrêter (Stop). A CAPTCHA or a login is reported to you: it is up to you,
  JobHunter circumvents nothing.
- **Proof, not only a declaration.** After "J'ai envoyé", JobHunter looks at the page —
  without clicking anything — and notes in your tracking file:
  - "envoi confirmé" (sending confirmed) if the site displays its confirmation ("Merci pour
    votre candidature", "Application submitted"…);
  - "envoi non confirmé" (sending not confirmed) otherwise: check your mailbox or your
    candidate area. Nothing is ever resent automatically.
  A capture of the page is kept in `Scripts/_preuves/`; the offer's record shows the state
  and the excerpt.
- No more double confirmation: "J'ai envoyé" is enough, the application moves to
  "postulé" (applied). "Confirmer une candidature envoyée…" (Confirm a sent application…)
  (record, right click) remains for a sending done elsewhere.

## 2.1.1 — 2026-10-19

- **Mac and Linux**: the buttons that open a document or a folder (CVs, letters, project
  folder) crashed — they called a Windows-specific function. They now go through the
  system application (`open` on Mac, `xdg-open` on Linux). Nothing changes under Windows.
- Behind the scenes, nothing visible: the whole program is now checked by the typing tool,
  and every design decision is linked to the code that applies it.

## 2.1.0 — 2026-10-18

- **Closed offers are finally removed.** The availability check was cut off every morning
  after 45 min, before reaching the deletion: it found 30 to 60 closed offers a day and
  removed none. It now stops by itself in time, then removes what it found.
- **Once a week, on Sunday**, instead of every day: the collection on the other days is
  ~45 min shorter. `python JobHunter.pyw pipeline --dispo-jour 2` moves it to Wednesday;
  `--dispo` runs it today.
- The tests no longer write to the availability check's state file in your folder when run
  at your place.

## 2.0.0 — 2026-10-18

Nothing changes in what JobHunter does; what changes is how you launch commands by hand.
Go through 1.15 first (the update does it by itself if you are up to date).

- The whole program now lives in `src/jobhunter`; `Scripts/` keeps only your data (offer
  queue, tracking file, settings, logs).
- Commands are launched with `python JobHunter.pyw <commande>`: `collecte`, `documents`,
  `postuler`, `pipeline`, `maj`… (`python JobHunter.pyw aide` lists them), and any other
  program by its name (`python JobHunter.pyw probe_ats`). The old `python Scripts/xxx.py`
  lines no longer work.
- Double-click, `lancer.bat`, `mettre_a_jour.bat`: nothing changes.
- **Scheduled collection**: if you had scheduled it with `planifier.bat` or
  `./planifier.sh`, run it once more — the old task points to a file that no longer
  exists. The update tells you if that is the case.

## 1.15.0 — 2026-10-18

Transition release to 2.0: install it before 2.0. Nothing changes in what JobHunter does.

- The update checks the new version with the code of that new version. Without this, 2.0,
  which arranges the programs differently, would be wrongly refused.
- The engine, the tests and the application no longer use the old files of `Scripts/`
  (`job_sources.py`, `queue_io.py`…), which will disappear in 2.0.

## 1.14.0 — 2026-10-18

Nothing changes in what JobHunter does.

- Loading the engine no longer reads any file: whatever comes from the profile is computed
  on first use. Changing profile (first launch) takes effect everywhere at once.
- The morning pipeline writes, next to its usual log, a timestamped engine log
  (`Scripts/_logs/pipeline_<date>_<heure>_moteur.log`).
- `python Scripts/chemins.py` works again (it raised an error).

## 1.13.0 — 2026-10-18

Nothing changes in what JobHunter does.

- Loading the engine no longer creates folders: they are created at the time a CV, a
  letter or a message is written.
- The foundation (storage, profile, network) and the score calculation are fully typed,
  checked by mypy in CI.
- Documentation: `docs/architecture.md` and the architecture decisions (`docs/adr/`).
- The engine installs as a package (`pip install -e .`): the `jobhunter` command then
  exists directly.

## 1.12.0 — 2026-10-18

A single entry point for all programs: `python -m jobhunter` lists the commands
(`collecte`, `documents`, `postuler`, `pipeline`, `maj`…). The old lines
(`python Scripts/generate_docs.py …`) still work.

## 1.11.0 — 2026-10-18

- The application joins the `src/jobhunter/app` package; `JobHunter.pyw` (double-click)
  now does nothing but launch it. Nothing changes on screen.
- The update also checks that the application and the navigation load, and rolls back
  otherwise.

## 1.10.0 — 2026-10-18

Nothing changes in what JobHunter does. The web navigation (`web_nav.py`, nearly 4,000
lines) and `site_strategies.py` join the `src/jobhunter/navigation` package, one section
per module; the old names remain valid.

## 1.9.0 — 2026-10-18

- CV, letter and short message join the `src/jobhunter/documents` package;
  `tailor_application.py`, `message_offre.py` and `cv_auto.py` remain valid.
- Fix: reading the queue through a relative path (`apply_queue.json` from `Scripts/`)
  returned the offers without their description.

## 1.8.0 — 2026-10-18

Nothing changes in what JobHunter does. The collection (`job_sources.py`, nearly 5,000
lines) is split into one module per source in `src/jobhunter/sources`;
`python Scripts/job_sources.py ...` works as before, and so does
`python -m jobhunter.sources`.

## 1.7.0 — 2026-10-18

Nothing changes in what JobHunter does. The calculation of scores, language and zones, and
the sorting of offers, join the `src/jobhunter/scoring` package; the old program names
(`tri_file.py`, `zones.py`…) remain valid, on the command line as in the code.

## 1.6.0 — 2026-10-18

Nothing changes in what JobHunter does. The profile and the network requests (limited in
total duration, so that a slow site never blocks the collection) join the
`src/jobhunter/` package. These requests now have their own tests, and a new check
verifies that every function that one program calls on another really exists.

## 1.5.0 — 2026-10-18

Nothing changes in what JobHunter does. The storage code (the offer queue, the application
tracking, safe writing and the lock between programs) moves into a new `src/jobhunter/`
folder: first step of splitting the engine into a package. The update adds this folder;
the old names (`queue_io`, `suivi_io`, `jutil`) remain valid. The tests are now written
with pytest (1,155 tests).

## 1.4.0 — 2026-10-17

"Workshop" release: nothing changes in what JobHunter does, but the code is now checked
like professional software (see `docs/professionalisation-plan.md`).

- **Non-regression bench**: 384 fictitious offers whose every decision (score, sorting,
  zone, language, message, letter) is compared with a reference at each change.
- Code formatted and checked automatically (ruff), checks before each commit, reproducible
  development environment (uv), tests run by pytest.
- Two test series that never ran (reminders, navigation) are hooked up.
- The update will replace almost all the program's files (formatting): a file that you
  modified is kept, the new version placed next to it as `.nouveau`.

## 1.3.2 — 2026-10-17

- **LinkedIn: the collection no longer loses the rate-limited pages.** Since 13/10,
  LinkedIn answers "too many requests" (429) from the first pages; each refused page was
  lost, and the LinkedIn collection had fallen to a few offers a day. Now the pages are
  spaced out, and a 429 makes it wait and ask for the same page again; the LinkedIn pass
  stops cleanly after 45 min. A refusal (403/999) stops LinkedIn for the day.

## 1.3.1 — 2026-10-15

- The installer records the fingerprint of the installed files: an installation made from
  the ZIP of `main` (between two releases) also recognises your modifications.
- In a copy without a `VERSION` file, the update says so and attempts nothing.
- A file that you modified and that the new version does not change is no longer flagged,
  and no needless `.nouveau` is placed next to it.

## 1.3.0 — 2026-10-15

- **Update from the application**: when a release comes out, JobHunter offers to install it
  right away, shows the progress, then restarts. Also in "🔧 Maintenance ▾ → Accès &
  diagnostic → Mettre à jour JobHunter" (Access & diagnostics → Update JobHunter).
- **What's new displayed** before and after each update (this file).
- **Check after installation**: all the scripts are compiled and the core modules loaded;
  on failure, automatic return to the previous version.
- **`--annuler`** (cancel): goes back to the version before the last update.
- **Your modifications are recognised from the first update**: the reference is the
  official ZIP of your version. A file that you changed is never overwritten again.
- **Files removed from the program are deleted** (if they have not been modified), with a
  copy in the backup.
- **New profile settings flagged** after the update.
- A fresh git clone under Windows no longer sees the `.bat` files as modified (the first
  `git pull` failed).
- customtkinter 6 accepted (tested: the application opens and works with 5 and 6).

## 1.2.0 — 2026-10-15

- No more reading of a mailbox by a program: a code received by email is entered by hand.
- Bounded dependencies, automatic tests under Windows and Linux.
- Sample profile entirely fictitious; documentation cleaned up.
- Language cap: a posting in a language you do not speak no longer rises to 10.
