# What's new in JobHunter

The update (`mettre_a_jour.bat`, `./mettre_a_jour.sh` or the application's button)
shows the sections newer than your version. Format: `## x.y.z — date`, the most
recent at the top.

## 3.65.0 — 2026-10-28

Relances and Statistiques hold in the window when they open, like Candidatures.

- **Relances**: the three panels take the screen's height (in a 1280 × 720 window they ran 136 px under it); the follow-ups, the drafts and the open draft scroll inside their own panel.
- **Statistiques**: the applications sent become a fourth stack beside the three others instead of a full-width band, and a low window tightens the figures and the bars (286 px under a 1280 × 720 window before). A long section title wraps instead of widening the page.
- **Accueil**: a smaller chart in a low window: with one recent application the left column still ran 17 px under the window.

## 3.64.0 — 2026-10-28

The Applications board holds in the window when it opens.

- **No more board cut at the bottom.** In a 1280 × 720 window the six columns went onto two lines: the board ran out under the window, and the note « N offres écartées… » showed through the cards. The columns now stay on one line (narrower: 156 px, 112 px when empty), take the window's height, and each shows the cards that fit; « Voir les N autres » unfolds the rest, which scroll inside the column, with « Replier » kept in view. The count follows the window when it is resized. Below 1100 px wide the columns wrap again and the page scrolls.
- **Same margin at the bottom as at the top and on the sides** (24 px) on the list screens: Offres, Candidatures, Documents.

## 3.63.0 — 2026-10-28

The Microsoft Store package contains Node.js again.

- **`JobHunter.msix` ships Playwright's `node.exe`**, put back from the release's zip and checked against the build's SHA-256. Since 3.62 the installer downloads it at the first browser, but the Store's policy 10.2.2 forbids a product to extend itself with downloaded code: inside the Store package, nothing is downloaded, neither Node.js nor the updates (the Store installs those). `JobHunterSetup.exe` stays at 45 MB.

## 3.62.0 — 2026-10-28

A lighter installer: Node.js is fetched the first time a browser starts.

- **`node.exe` (88 MB) leaves `JobHunterSetup.exe` and the MSIX.** Playwright drives the browser through it, but most launches never open one. The build attaches it to the release as `playwright-node-win64.zip`; the application downloads it the first time a browser starts (applying, a few sources), checks it against the SHA-256 the build wrote inside the application, and keeps it in `%LOCALAPPDATA%/JobHunter/node/`, where the next versions reuse it. Offline, the browser step stops with a clear message; the rest of the application works as before.
- Installed with Python (`pip`, `install.bat`): nothing changes, Playwright keeps its own `node.exe`.

## 3.61.0 — 2026-10-28

Lighter: compressed backups, two dependencies fewer.

- **The daily backups are gzip-compressed** (`data/_backups/<date>/*.json.gz`). Seven days weighed 416 MB in a real data folder; a day goes from 60 MB to 16 MB, in half a second. The plain backups made before are compressed at the next collection, each one only once its copy reads back whole. `jobhunter restore`, the availability audit's copy and the reposts history read both.
- **openpyxl removed** (nothing used it) and **requests replaced by httpx** in the two programs that still used it (`link_check`, `enrich_homepages`): two dependencies fewer to install.
- **`resolve_offer_links` removed**: no screen, step or program called it any more.

## 3.60.0 — 2026-10-28

Downloaded again, JobHunter no longer starts from zero.

- **The welcome offers the previous folder's data.** Installed from source, the data live in JobHunter's own folder: unzipped elsewhere (a new download, another computer), the welcome asked for the CV again. It now looks for another JobHunter folder with a profile (beside it, in Documents, Downloads, Desktop, and Documents/JobHunter of the installer) and offers to take its data back — profile, CV, offers, applications, documents — or another folder chosen by hand. They are copied: the old folder does not change. Daily backups and logs are not copied.
- **The welcome window's bar shows JobHunter's logo**, no longer a coloured square.
- README: what happens on a new download.

## 3.59.0 — 2026-10-28

One logo everywhere: no more Python, Terminal or Inno Setup logo in front of JobHunter.

- **Start menu shortcut for installations from source or pip** (`jobhunter shortcut`, `--bureau` for the desktop too; `install.bat` runs it, and the window makes it once when missing). It carries JobHunter's icon and the window's identity: pinned to the taskbar, the window no longer shows pythonw.exe's logo.
- **Notifications under JobHunter's name and logo**, no longer Windows Terminal's (when the shortcut is there; the Terminal's otherwise).
- **The window has its icon from its creation**, not after it is shown (the taskbar first showed Python's).
- **JobHunterSetup.exe carries JobHunter's icon**, and its shortcuts the window's identity.
- The migration message uses JobHunter's icon; the README shows the logo.

## 3.58.0 — 2026-10-28

What a user found on a fresh install: the update that never finished, the documents screen with nothing to explain, the base CV and letter.

- **The update works for an engine installed with pip.** The data folder's own git repository was taken for the engine's: the update stopped on "does not track any remote branch". A pip install now downloads the signed files and installs them with pip (two steps, shown).
- **The update button tells where it is**: percentage of the download or elapsed time, on the button and on hover; then "Updated: restart JobHunter", "postponed" (queue busy) or "failed". The Engine card in Maintenance follows it too, instead of a label that never changed.
- **An MSIX installed from JobHunter.msix** (not from the Store) opens the releases page, no longer the Store.
- **Opaque at first opening** (transparency 0 by default).
- **One logo**: the page uses the application icon; the welcome window has the application's identity in the taskbar.
- **Offers: the header band lines up with the filters.**
- **Documents**: "Redo the CVs / letters" show only when there is something to redo; with no document yet, the screen explains the three steps and gives the two buttons. Redo says why when it did nothing.
- **Base CV as .docx shows in Profile** (PDF made with LibreOffice, else its text); a PDF alone shows too.
- **Base letter in Profile**: seen, replaced (the old one kept as .bak); its background paragraph is offered for the letters.

## 3.57.0 — 2026-10-28

Smoother window: lighter over Remote Desktop, a home screen that fits 1280×720, and a background loop that no longer redoes the same scoring.

- **Remote Desktop: light display.** `Api.session()` tells the page whether the window is seen through Remote Desktop (Windows' `SM_REMOTESESSION`); the page then drops the frosted blurs, the blurred backdrop and the animations (`body.leger`). There every frame is encoded and sent at about 30 per second; on the profile screen this cuts the GPU work while scrolling by about a third. Windows' "reduce motion" setting now also stops transitions and animations.
- **The background's news reach the page again.** `Api._fond` (the backdrop setter) overwrote the background loop of the same name: every `fond_etat` call failed. It is now `Api._toile`.
- **Skill matching is faster.** `skills_in` tests each skill's phrases through one flat list of precompiled patterns, with a cheap substring check first and a small memo of recent texts.
- **ATS rescoring runs once per series of description batches**, after the last batch, and only when a description was actually fetched (it took over a minute per batch on a real queue of 11 000 offers).
- **Refreshing keeps your place.** A data refresh restores the scroll position of the screen and of its scrolling lists.
- **Low windows (760 px and less)** tighten the home screen's spacing so its panels fit without being cut.

## 3.56.0 — 2026-10-28

No priority zone means the whole country.

### Changed
- **A profile without priority zones searches its whole country as the priority.** `zones.prioritaires` empty used to leave every offer of the home country « ailleurs »: « Préparer les 30 meilleures » (`documents --top`, priority and secondary zones only) then prepared none of them, and HelloWork read no city page. Now, without any priority sector, every place of the home country is « prioritaire » (overseas excepted; « France » alone stays unknown) and no sector gets the first-sector bonus. With at least one priority sector, nothing changes: the rest of the country stays « ailleurs ». On a real queue of 13 617 offers with an empty list: 3 178 offers go from « ailleurs » to « prioritaire »; scores, sorting, letters and CVs unchanged.

## 3.55.0 — 2026-10-28

Nothing overlaps, nothing scrolls sideways, and the home screen fits the window it opens in.

### Changed
- **Nothing scrolls sideways any more.** The offers' filters wrap onto a second line in a narrow window instead of one line scrolled with the wheel, and the applications' columns wrap onto a second row instead of crushing the one holding cards (its title, count and date overlapped at 900 px).
- **The home screen fits the window it opens in (1280 × 800), no panel cut by its edge.** It is more compact (one line per best offer, the title in full on hover; « À préparer » joins the line under « CV et lettres »; lower bars), and when room still lacks, whole items are put away, the least useful first, each column for itself: best offers beyond three, recent applications beyond one, zones beyond one, tasks beyond two, then the Documents button (also in the menu). Every item stays one click away. In one column (window under 1100 px) the page scrolls as before.

### Fixed
- **A low window no longer pushes the list out of its panel.** At the window's minimum size (900 × 560), the offers' and documents' lists kept 260 px of their own while their panel shrank: rows showed under the panel's edge. The panel now keeps room for a few rows and the page scrolls below that.
- The date of a recent application no longer breaks over two lines.
- Checked on every screen at 900 × 560, 1024 × 640, 1280 × 720, 1280 × 800 and 1440 × 900, in French and English: no element overlaps another, leaves its panel or goes past the window's right edge; the home screen at 1280 × 800 and 1440 × 900 with five best offers, five applications, five zones and five tasks holds without a cut.

## 3.54.0 — 2026-10-28

Sites are recognised by the URL's host, not by a piece of text.

### Fixed
- **A site is told by its host.** Eleven places tested « linkedin.com in url » (or Indeed, Welcome to the Jungle, Talent, SmartRecruiters): an address such as `https://example.org/?ref=linkedin.com` or `linkedin.com.example.org` passed for LinkedIn. They now go through `links.sur_site`, which reads the host (`fr.linkedin.com` passes, `notlinkedin.com` does not; « indeed. » matches every extension). Closes eleven CodeQL alerts (py/incomplete-url-substring-sanitization). No offer of a real queue changes.

## 3.53.0 — 2026-10-28

A new profile finds its trade and its country, and asks where to search.

### Changed
- **A broad job title asks for its specialty.** First launch writes « ingénieur / engineer + mécanique / mechanical » in the title filter instead of « ingénieur » alone: a mechanical engineer's collection no longer brings DevOps or civil posts. The filter syntax `a + b` (every part, any order; `a / b` for variants) works in any profile.
- **First launch asks where to search.** The home country only, or abroad too — and then which countries or regions (« Suisse, Belgique », « Europe », « monde »); and the preferred cities, a city of the catalogue standing for its sector (« Mérignac » → Bordeaux). The answer goes to the profile's `monde` (false, a list, or true), which `collect` follows: LinkedIn is asked for the home country and each country named instead of « Worldwide », and the merge lets in those countries' offers only. Same questions in the welcome window. Existing profiles keep their behaviour (no key = the world, as before). On three test CVs (engineer in Lyon, waiter in Bordeaux, lawyer in Paris), the home country only: 122, 4 and 13 foreign offers fewer.
- **The welcome windows take the 3.52 design codes.** Every font size and spacing is on style.css's scales (the profile and welcome titles at 44 px like the web pages' titles, sections at 20), ticks and radio buttons in the interface's accent, the sector lists on white cards. A test keeps them on the scales.

### Added
- **The free key that brings the most offers is advised.** France Travail for a profile in France (most offers outside executive jobs are there), Adzuna in the countries it covers: at the end of first launch, with the steps, and as the first line of the home screen's « À faire » until the key is saved.

### Not added
- Sites tested for new sources and left out, their rule respected: Cadremploi, Monster and Optioncarrière refuse (403 / anti-bot), Jobijoba's robots.txt forbids its search, Meteojob shows a CAPTCHA, L'Hôtellerie-Restauration forbids its `/api/`, JobTeaser requires a login. Choisir le service public was already collected (`--ats`).

## 3.52.0 — 2026-10-28

A cleaner window: one scale of sizes, no decoration that says nothing.

- **Nine font sizes instead of twenty, twelve spacings instead of thirty.** Sizes such
  as 12.5, 13.5 or 9.5 px had crept in one screen at a time; every text size is now a
  token of one type scale, every margin, padding and gap a step of one spacing scale,
  and a test keeps it so.
- **Flat colours where gradients said nothing**: the score circles, the morning
  collection's bars and the home tiles. The dark "To do" card loses its glow.
- **The best offers lose the rank badge** sitting on their score: the list is already
  in order.
- **The home chart waits for three collections** before drawing a curve, instead of
  one lone bar.
- **An offers column empty on the whole page is left out** (no zone set, nothing
  applied to yet): it showed a dash on every row.
- **"À postuler" no longer wraps** on the applications board: an empty column is as
  wide as its title.
- **The privacy policy names the public company directories** that
  `companies-import` asks (3.51): a country code and industry codes, nothing about you.

## 3.51.0 — 2026-10-28

The large employers of your country, from open directories.

- **`python -m jobhunter companies-import`** adds your country's large employers to
  the register of companies seen, which the career-site pass asks every morning:
  - **Wikidata**, for any country: companies of 500 employees or more, largest first,
    with their website and industry (2,330 for the United States, 1,760 for Germany,
    253 for Japan, measured on 28 October);
  - **SIRENE** in France (recherche-entreprises.api.gouv.fr): companies of 1,000
    employees or more, by activity section.
- **Only your fields' industries are kept**: banks and insurers for a finance profile,
  hospitals for a nurse, software for a developer; a company whose industry is unknown
  comes after them. Legal, HR, sales and project profiles work in every industry:
  nothing is filtered. `--tous-secteurs` keeps every industry, `--n` sets how many
  (300), `--dry` only counts.
- **The companies really seen in a collection are asked first**; a directory's come
  after them. With no offer page in the queue, the career-site pass reads the
  company's website to find its recruiting tool.
- Both directories are public and free, asked one request at a time with a pause and
  the project's name; a refusal stops the import.

## 3.50.1 — 2026-10-28

- **The morning collection starts again.** Since 3.47 it stopped one second after it
  began, on « NameError: name '_pays_usajobs' is not defined »: the function was
  written below the block that starts the program, so it did not exist yet when the
  scheduled task ran it. Nothing was collected on 28 October.
- The same mistake is corrected in the message, fit and applications modules, and a
  test now refuses any definition written after a module's starting block.

## 3.50.0 — 2026-10-28

The first launch reads CVs from London, Berlin, Tokyo and Madrid as well as from France.

- **CVs written in German or Spanish** are recognised as such. They were taken for
  French: « fr » was added to the spoken languages and the French gender question was
  asked. Their summary is no longer copied into the French or English letter paragraph.
- **« 2022–heute », « 2020–actualidad », « bis heute »** count as still in the job: the
  years of experience of a German or Spanish CV were short by the current job.
- **Languages named in English, French, German or Spanish** (« Englisch
  (verhandlungssicher) », « Inglés (C1) », « Japanese (native) ») are added to the
  spoken languages. The message's language sentence leaves out the CV's own language
  rather than French: a London CV now says « I speak French (intermediate) ».
- **The secondary zone abroad is the whole country by the name postings use**
  (« Spain », with « España » as an alias), when the CV gives no region. « Berlin,
  Deutschland » no longer made « Deutschland » a region.
- **Skills are shown under their English label** when the interface is not French.
- « English (fluent) » no longer gives the skill « Simulation numérique » (Ansys Fluent).

## 3.49.0 — 2026-10-28

Nothing assumes a French user or a finance profile any more.

- **The first launch speaks the interface's language** — the system's by default:
  « First name », « Target jobs », « PRIORITY places »… for a user whose system is in
  English, French otherwise. Yes/no answers take « y » as well as « o », and the
  command line's help is in English.
- **The default finance / ESG companies are offered only to a finance profile.** A nurse
  in Ohio is no longer asked whether to keep ninety banks and asset managers.
- **eFC's default filter follows the profile**: ESG titles for a profile whose core
  title words are ESG's, the profile's own titles otherwise. **The top offers' title
  bonus** uses the profile's core title words (`scoring.intitules_coeur`).
- **Merge counts say « hors zone »** (« outside the area »), not « hors de France ».
- Comments and the roadmap no longer name a user; the career-sites scan's messages say
  « offres retenues ».
- **The first launch no longer prints the e-mail and phone read in the CV**: it says
  « (filled in) », as the questions already did. Its output often goes to a log.

## 3.48.0 — 2026-10-28

Letters, messages and contract types follow the offer's country.

- **North American letters.** An English letter for an offer in the United States or
  Canada (or with no place, for a profile there) opens with « Dear Hiring Manager »,
  closes with « Sincerely » and is dated « October 28, 2026 ». Elsewhere it keeps
  the British forms — « Dear Sir or Madam », « Yours faithfully » — and is now dated
  « 28 October 2026 », as written there. Messages open the same way.
- **Contracts written in English** are read: « Job type: Part-time », « Employment
  type: Internship », « Contract Type: Permanent / Fixed Term », a title « (Contract) »
  or « (Temporary) ». « Contract Manager » stays a job, and « CDI à temps partiel »
  stays a CDI.
- **A « Temps partiel » contract type** (Part-time, Teilzeit, Media jornada), read in
  the title (« Part-time Nurse », « à temps partiel », « mi-temps ») and in the label;
  it can be set aside in Exclusions like the others.

## 3.47.0 — 2026-10-28

The collection searches where you live (`pays` in the profile, read from your CV
since 3.46). Nothing changes for a profile in France.

- **Each source runs where it covers you.** France Travail, the V.I.E, FIR, Jobs that
  make sense, Welcome to the Jungle, APEC, Glassdoor, HelloWork and Choisir le service
  public only list offers in France: they run for a profile in France, and the
  collection says which ones it skipped and why. EURES runs for a profile in Europe,
  the Bundesagentur for one in Europe who speaks German.
- **LinkedIn and Jooble search your country**, then LinkedIn searches the world, as
  France was before. With `--france`, the collection keeps your own country's offers.
- **Adzuna searches your country with your words** (the 19 countries it covers). The
  seven European countries it also searched stay for a profile in France;
  `adzuna_pays` in `sources_config.json` sets them for anyone (`[]` = home only).
  Jooble and Choisir le service public take your words too; `mots_sources` (`adzuna`,
  `adzuna_en`, `jooble`, `service_public`) keeps a hand-tuned list.
- **USAJOBS**, the US federal government's official job board, for a profile in the
  United States (`--usajobs` runs it anywhere). Its key is free: ask for it at
  developer.usajobs.gov, then enter it with the others (Accès → Collecte des offres),
  e-mail and key. The welcome tour only offers the keys of the sources that cover your
  country.

## 3.46.0 — 2026-10-28

JobHunter no longer assumes you live in France. The first launch reads your country
in the CV and measures every place from there.

- **Your country, from your CV.** The first launch reads the place in the CV's header
  (« Columbus, Ohio, United States », « Austin, TX 78701 », « Lyon, France ») and
  writes `pays` (ISO code: `us`, `ca`, `fr`…) into the profile. A profile without it
  stays in France, as before.
- **Zones anywhere in the world.** Outside France, « ailleurs » is the rest of your
  own country and « international » is abroad, France included. The priority zone
  proposed is your city, the secondary one your state or region (« Ohio » also
  matches « OH »). A place outside the French catalogue is kept as a free place
  instead of being dropped, and the French sectors are only listed for a profile in
  France. A state or province written in full (« Dayton, Ohio », « Dieppe, New
  Brunswick ») is now read in its country: such offers were counted in France.
- **The interface speaks your system's language** (French, English, German or
  Spanish; English otherwise) until you pick one in the settings.
- **The first launch reads an English CV better**: the job is the first one of the
  Experience section when the header has no title (a place or « PROFESSIONAL
  SUMMARY » is not a job), a North American phone number (« (614) 555-0100 ») is
  read, French is only added to the languages you speak when the CV or your country
  says so, and the « diplômé / diplômée » question is only asked for a CV in French.

## 3.45.0 — 2026-10-28

Your target companies now follow from your profile, for any profession: no list of
companies or words is written by hand per field any more.

- **The sources search with your words.** freehire, EURES, the Bundesagentur
  (arbeitsagentur.de) and the Workday feeds each had their own list of ESG / finance
  words. They now take your collection keywords (Ma recherche) — at most as many as
  their old list — so a seasonal worker, a nurse or a developer gets their own
  offers there too. A hand-tuned list per source still wins: `mots_sources` in
  `sources_config.json` (`{"freehire": [...], "eures": [...]}`); the old lists are
  kept for a profile with no keyword. With your words, EURES keeps the offers whose
  title names one of them (its ESG-only title filter stays with its own list).
- **Well-rated companies are followed on their own.** At the end of the career-site
  pass, a company whose feed just gave open offers and whose best offer reaches fit 7
  is added to Entreprises suivies (10 a run at most, no extra request), tagged
  « suivie auto ». A company you remove is never followed again by the engine
  (`flux_retires`). `"suivi_auto": {"fit_min": 8}` raises the bar, `false` turns it
  off; « Suivre les bien notées » still does it by hand.
- **Seasonal contracts.** « Saisonnier » is a contract type: read in the title
  (« Serveur saisonnier », « Seasonal ski instructor »), in the body (« Type de
  contrat : saisonnier », « emploi saisonnier ») and in France Travail's own field
  (`SAI`; `MIS` gives Interim). It can be set aside like any other in Exclusions.
- **A « Montagne (stations) » zone** in the places catalogue: the six departments that
  are mountains through and through (04, 05, 09, 65, 73, 74) and the resorts by name
  elsewhere (Font-Romeu, Métabief, Gérardmer, Le Lioran…). « Alpes » or « Pyrénées »
  alone are never read as mountains: Auvergne-Rhône-Alpes is Lyon.

## 3.44.0 — 2026-10-27

- **Finding the companies' career sites, better** (Sources → Entreprises vues, and
  the morning pass 1f). Each company of the register is asked, by the first way that
  works:
  - its recruiting tool's public API, when an offer link gave it — or when an
    earlier run learned it;
  - freehire, whose job links are the company's own: **the tool they show is now
    learned** (any job, before the title filter), and read directly next time;
  - **the tool guessed from its name**: the tenant of that name in your Workday
    directory, then the account of that name on Greenhouse, Lever, Ashby,
    SmartRecruiters and Recruitee (40 companies a run). Kept only with open offers;
    Greenhouse and SmartRecruiters must also give the same company name. Short names
    (« AXA », « EY ») are never guessed: they would be anyone's;
  - **its career page**: one of its offer pages already in the queue, read once for
    the link or frame of the tool behind it (30 a run).
- **A company with nothing open is asked less often**: after 7 days, then 14, 28,
  56. `_company_sites.json` keeps each ask (date, offers, empty answers in a row) and
  the tools learned; the old file is read as is.
- **Dead followed feeds are suspended on their own**: failing, never reached, or an
  empty page for 60 days. Suspended, never removed; Entreprises suivies shows them
  « suspendue auto » with the reason, and « Reprendre » brings one back. A feed whose
  offers just do not suit the profile is not dead.
- Workday directory (`python -m jobhunter.sources.discovery --workday`): measured on
  real data, six Common Crawl index pages gave 2,228 career sites of 1,117 tenants
  (five pages left for the next run).
- **The Microsoft Store package builds**: makeappx's « 0x8007007b » came from the
  `_rels` folders of python-docx's unzipped template (reserved names in a package,
  found by bisecting the 1,337 files). They are left out; python-docx reads its
  `default.docx`, not that folder. `JobHunter.msix` is attached to the release again.
- Tests: pytest 9.2 undoes some monkeypatches by deleting the name; the package facade
  no longer fails when a profile value was already recomputed in between.

## 3.43.0 — 2026-10-27

- **« Lancer la collecte » moves to Offres**, in place of « Préparer les 30
  meilleures »; the home screen has no header button any more.
- **Home screen, bottom right: CV and letters.** How many offers scored 8 and more
  have their CV and letter, how many wait, and « Préparer les 30 meilleures » there.
- **A Profiles panel.** « Gérer les profils » (the badge menu, the Profile screen,
  Maintenance → Profils…) opens its own panel: open another profile, add one from a
  CV, rename, archive. Settings keep a short card pointing to it.
- **Base CV and base letter, seen and edited** (Profile screen). Each base CV has
  « Voir » to read it or edit its text; « Remplacer mon CV de base… » stays. The
  letter is written for each offer, so its base is the paragraph about you it
  always carries: edit it in French and English, then remake the letters; « Voir la
  dernière lettre » shows what it gives.
- **Layout audit**, every screen at 1100, 1280 and 1440 px wide, overlaps and
  overflows measured in the page:
  - Offres: the list's header row was see-through, the rows scrolled under it showed
    through; it is opaque now. The place column is kept to two lines.
  - Offres: the ten filters wrapped into two ragged rows; search and display on top,
    the five filters on a grid of equal columns below.
  - Candidatures: on narrow cards the date and the score bar went past the card.

## 3.42.0 — 2026-10-27

- **Followed companies: one row per company.** A company read by several feeds
  (its recruiting tool, its career site, an old empty one) showed one row per feed:
  Amundi three times, Sweep three times, 235 rows for 210 companies. Each company is
  now one row with its offers summed and its tools listed; « n flux » opens its feeds
  underneath, each with its own Suspend / Remove.
- **Their real names.** A feed named from its slug or its site's host showed
  « Societegenerale », « Bnpparibas », « Rejoindre »; the row now takes a written
  name — the feed's, else the one its offers in the queue carry (« BNP Paribas »,
  « Covéa Finance »).

## 3.41.0 — 2026-10-27

- **The companies already seen, asked on their own career sites.** Every collection
  notes the companies it meets (Sources → Entreprises vues, some 5,000 names); a new
  source now asks 150 of them per run what they have open: by their recruiting
  tool's public API when an offer link gave it (Greenhouse, Workday…), otherwise
  through freehire's company search, under the company's exact name (« Mirova » is
  not « Mirvac »). Followed companies are skipped; a company is asked again after 7
  days, the most recently seen first. On a first try, 30 companies gave 269 offers,
  231 not in the queue. `collect --entreprises-vues`; collected every morning (pass
  1f), and the « Chercher leurs offres » button in Entreprises vues. The freehire
  requests count against its daily quota.

## 3.40.0 — 2026-10-27

- **New source: Bundesagentur für Arbeit**, Germany's public employment service, by
  the search API arbeitsagentur.de itself uses (no account). ESG, Nachhaltigkeit,
  CSRD, sustainable finance and analyst keywords, last 30 days: about 250 offers in
  Germany and Austria on a first try. `collect --arbeitsagentur`; collected every
  morning with eFinancialCareers and EURES.
- **freehire is no longer limited to France**: every country by default, or the ones
  listed in `freehire_pays` of `sources_config.json` (e.g. `["fr", "de", "ch"]`).
  The countries your profile excludes are still set aside.
- **The company directory knows 56 more companies**, from the career-ops project
  (MIT licence), including Workable and Recruitee job boards.

## 3.39.0 — 2026-10-27

- **Follow the well-rated companies in one click**: Sources → « Entreprises vues »,
  « Suivre les bien notées (fit ≥ 7) ». Each company whose offer link gives its
  recruiting tool is checked first — one request to the tool's public API — and
  followed only if it has open offers (up to 25 per click).
- **Workday directory**: Workday publishes no list of its career sites; Common Crawl,
  the public archive of the web, has seen them. « Construire l'annuaire Workday »
  (in the company directory) builds it on your PC, resumes where it stopped when the
  index is overloaded, and makes Workday companies searchable by name. A Workday
  site is followed only if it has open offers. The directory is never shipped with
  JobHunter: each installation builds its own.

## 3.38.0 — 2026-10-27

- **New source: freehire** (freehire.me, open source, MIT), a search engine over
  companies' own career pages (Workday, Teamtailor, SmartRecruiters… for 470,000
  companies). Its public API needs no key for personal use; JobHunter names itself,
  keeps to its limits (120 requests a minute, 2,000 a day, a pause on `429`) and
  stores the company's own link, without freehire's tracking marker. France, last
  30 days, ESG / sustainability / finance keywords. `collect --freehire`; collected
  every morning with France Travail, Adzuna and Jooble.

## 3.37.0 — 2026-10-27

- **The page stays put, the list scrolls**: in Offres, Documents and the Sources tabs
  with a long table, the filters and buttons stay on screen; only the list scrolls,
  inside its panel, with its header row kept in view. In Candidatures each column
  scrolls on its own.

## 3.36.0 — 2026-10-27

- **Every company seen is noted**: each collection writes the companies of its offers
  to `companies_seen.json` (next to the queue, saved with it each day), even offers set
  aside, out of zone or closed since. Sources → « Entreprises vues » lists them with
  their offers now, best fit and the sites they came from; « Ses offres » opens them
  in Offres, « Suivre » follows the company at the source when one of its offer links
  gives its recruiting tool (Workday, Greenhouse, Lever…).
- **Documents: a tool for the cover letters too**: « Refaire les lettres » next to
  « Refaire les CV », and a Tous / CV / Lettres filter.
- **Microsoft Store package**: an unset repository variable no longer empties the
  package name (the windows build failed since 3.33.0).

## 3.35.0 — 2026-10-27

- **Documents: see and edit a CV or a letter in the app**, as from an offer: a click
  opens it in the side panel. One line per document (the .docx and its PDF were listed
  twice). « Dossier des CV » / « Dossier des lettres » open CV/By_offer and
  Letters/By_offer.
- **Statistics tell the truth**: « dossiers prêts » now reads the descriptions, which
  live in their own file (it said 0, every offer looked « description trop courte »).
  Gone: link states, channel, ATS share and the status cards that repeated the board.
  New: the sites and the collection keywords the offers come from, and answers by
  contract and by field next to the application funnel.
- **Offers**: the 7+ / 8+ / 9+ buttons and the publication-date sorts are gone (every
  offer shown is current and above the profile's threshold).
- **Applications**: each column shows its first 6 cards, then « Voir les N autres »;
  empty columns shrink, so the whole board fits without scrolling sideways.
- **No more holes in the screens**: cards in a row share its height, short cards stack
  (Maintenance, Profil, Réglages), Relances' reader fills its column.

## 3.34.0 — 2026-10-27

- **Areas say what they are**: in Ma recherche, each priority or secondary area reads
  « ville et alentours » (Toulouse: the city and its towns) or « région » (Occitanie,
  which holds Toulouse, Montpellier, Perpignan…). « Paris » is now « Île-de-France »,
  which it always covered (75, 77, 78, 91–95).
- **A department named without its number is recognised**: « Muret, Haute-Garonne »
  counts as « Muret (31) » instead of « elsewhere in France ». Names that are also a
  city or a region's piece (Loire, Nord, Var, Vienne…) are left out.

## 3.33.0 — 2026-10-27

- **A package for the Microsoft Store** (`JobHunter.msix`, attached to each release):
  once JobHunter is listed there, installing it from the Store skips SmartScreen's
  « Windows a protégé votre ordinateur », since the Store signs the package. Installed
  that way, the update button opens the Store's updates page instead of downloading
  the installer. The installer and the ZIP do not change.

## 3.32.1 — 2026-10-27

- **Four more companies in the sector lists**, each feed checked on its public API:
  Ipsen, Pierre Fabre and EssilorLuxottica in Health, Michelin in Industry.

## 3.32.0 — 2026-10-27

- **Company lists by sector**: Sources → Entreprises suivies now starts with « Listes
  par secteur ». Tick a sector to collect its companies; open it to untick one company
  (its offers already in the queue stay). Besides the engine's original finance and ESG
  list: tech and digital (36 companies), health and life sciences (23), industry,
  energy and engineering (21), retail, luxury and consumer goods (11). Every feed was
  checked on its public ATS API on 2026-10-27 (Greenhouse, Lever, Ashby,
  SmartRecruiters, Workday). Before, the built-in companies only suited finance: any
  other profession started with none and added each one by hand.
- Nothing changes until a list is ticked. The first tick converts the settings without
  changing what is collected: the finance list stays ticked when it was in use, and its
  companies the settings had left out show unticked instead of coming back (checked on
  real settings: same 69 ATS, 49 Workday and 54 other feeds).
- Lists with many Workday feeds (health, industry) add a few minutes to the morning
  collection: each Workday feed is read keyword by keyword.
- A new profile that does not keep finance starts with no list ticked, and picks its
  sectors in the app.
- Removing a company that comes from a list says so, and points to unticking it.

## 3.31.0 — 2026-10-27

- **Window backdrops work in full size**: with the taskbar hidden, the full-size window
  was exactly the monitor's size, which Windows treats as full screen and so drops
  acrylic and mica for a flat grey — every backdrop looked the same. It is now one pixel
  short.
- **Transparency thins the background, not the text**: the slider used to fade the
  panels too, leaving their text floating over the desktop. Panels now keep their glass;
  only the window's background thins, and the text drawn straight on it (menu, page
  title) gets a soft halo as it does.
- **Several values per filter**: zone, field, contract, region and country now open a
  list of boxes. Tick as many as you want, then « Appliquer » (or click elsewhere,
  or Enter); Escape cancels. Past a dozen values, a field narrows the list. Saved
  views keep their single value as a list of one.
- **The countries follow the regions**: once regions are chosen, the country filter
  only offers their countries, and a country ticked outside them is dropped.
- **More offers per page**: 20, 40, 100 or 200, under the table; the choice is kept.
- **A folding menu**: « Replier le menu » at the foot of the side menu leaves only its
  icons, for more room for the filters; the choice is kept. A narrow window already
  folds it.
- **See and edit the CV and the letter in the window**: « CV » and « Lettre » in an
  offer's panel show the PDF; « Modifier le texte » lists its paragraphs. Only the
  ones changed are written into the .docx, in place (bold and italics stay), then the
  PDF is made again (LibreOffice). The generated version is kept once as `.docx.orig`;
  a paragraph holding a link stays for Word (« Ouvrir dans Word »).
- **Fewer columns**: « Trouvée », « Vérifiée » and « Signal » are gone, with the sort
  « Vérifiées en dernier »: checking that offers are still open is the application's
  job (closed ones leave the list), not a column to read. A saved view sorted that way
  falls back to the best score.
- **« Gérer les profils… » works**: a press inside the profiles list closed it before
  the click arrived, so neither that entry nor another profile could be picked. It now
  opens Réglages on the Profils card.
- **Adding a profile, said plainly**: the Profil screen has « Nouveau profil… » and
  « Gérer les profils »; the file is only « Fichier du profil (avancé) ». The steps are
  spelled out (name, CV, a form filled from the CV), and what a profile is (another
  job, city or person, with its own offers, CVs and letters).
- **The update button sits in the middle of the title bar**, clear of the window
  buttons.
- **Drag an application to another column** of « Candidatures » to change its status,
  with the same undo as the status list.
- **No more terminal flashing** when opening some screens: the scheduled-task check
  (`schtasks`), git and the PDF conversion now run without a console window.
- **Where the priority areas are set**: the zone filter ends with « Régler les zones… »,
  which opens Profil on « Zones prioritaires » / « Zones secondaires ».
- **« Lire les réponses par mail »** no longer stays stuck on « Lecture des courriels… »
  when the reading fails: the reason shows in the panel. Gmail not linked yet says
  what to do (an OAuth client file, then `pip install "jobhunter[gmail]"`); a .mbox
  export or a .eml folder works without anything.

## 3.30.0 — 2026-10-27

- **The open profile at the top left**: a round badge with its initials and its name
  (the holder's name for the main profile) replaces « JobHunter ». A click lists the
  profiles: pick one to switch (the window restarts on it), or « Gérer les profils… ».
- **Long filters can be typed in**: past a dozen choices (countries…), the filter is a
  field; type part of a name (accents optional), Enter takes the first match.
- **The score has its own column** in Offres, titled « Score », with a tooltip.
- **JobHunter's icon instead of Python's**: on the new window and its taskbar entry, and
  on the compiled app's executables (they had none, so PyInstaller's showed).
- **No more « ? » in the Country and Region filters.** Offers without a place get one
  from their posting: a « Location / Ville / City » field, a postal address, or the
  address of the page (Workday, Welcome to the Jungle, career sites). Only a recognised
  place is kept, never a guess. The daily sort applies it to the offers already in the
  queue. Measured on a real queue: 234 offers without a country → 92, and those left
  no longer appear as a choice.
- **More countries recognised**: Milano, Köln, München, Warszawa…, the codes « PT »,
  « RO », « MY » as a segment, Kuwait. Workday's « 3 Locations » no longer counts as
  France.
- **« Luxembourg, Luxembourg, Luxembourg » becomes « Luxembourg »**: a place segment
  repeating the previous one is dropped (« Geneva, Geneva, Switzerland » → « Geneva,
  Switzerland »).
- **Listing pages are no longer kept as offers** (jobijoba, linkfinance,
  efinancialcareers « /jobs/… », wizbii « /emploi/… »): the daily sort removes them.
- **Offer drawer**: the Follow-up card has inner margins and visible fields; the
  « non precise » contract chip is gone; countries sorted ignoring accents.

## 3.29.0 — 2026-10-27

- **The application opens in the new design**: double-clicking JobHunter (the installed
  app, `JobHunter.pyw` or `jobhunter app`) now opens the web window, which has every page
  of the classic one. pywebview becomes a dependency and ships with the installer.
- **Guided application in the new design**: tick offers, then « Candidature guidée… ».
  Chrome opens each offer, fills in the form, attaches CV and letter and stops before
  sending; you check and click Send in Chrome, then « J'ai envoyé » (or Ctrl+Enter) in
  the panel at the bottom right. Nothing is ever sent by JobHunter. Closing the window
  stops it and closes Chrome.
- **The background work of the classic window runs in the new one**: missing
  descriptions fetched in batches, docx → pdf sync, a scan of the company sites 2
  minutes after start then every 3 hours; news shown as a message, the page follows
  the queue when another program writes it. An update that did not start its version
  is said at start-up again.
- **The new design speaks English, German and Spanish**: the language chosen in
  Réglages → Langue now applies to both windows (it was French only in the new one).
  Texts, placeholders, tooltips, dialogs, the guided application and the output of the
  programs it runs are translated; offers, profile entries, letters and drafts keep
  their own language. The catalogues move to `jobhunter.locales` (the old
  `jobhunter.app.texts_*` names still import).
- **Spacing in the new design**: no more double gap under the filter bar; the header
  checkbox lines up with the rows; Statistiques' sections line up; the dark Moteur card
  has a visible button; in a narrow window the one-line filter bar scrolls with the
  wheel and fades on the right while more filters follow.
- The update button of the title bar says « Mise à jour en cours… » once clicked.
- The classic window only opens when the new one cannot (no web view on the machine),
  or on purpose with `jobhunter bureau`. Switching profile reopens the new design.
- Fixed while auditing the new window: the compiled app could not open it (no console,
  so no standard output) and fell back to the classic one without a word; login pages
  and console tools opened in no window under `pythonw.exe` or the compiled app; a file
  under CV/ or Letters/ is opened only when it is a document; the home chart showed
  « 1, 1, 1, 0, 0 » on an empty week; the classic window's sync logged every 10 minutes
  even when nothing changed (the new one says only real changes).

## 3.28.0 — 2026-10-27

- **An update shows as a button at the top of the window**: “Mettre à jour (X)”, at
  the right of the title bar, on every page, until it is installed. One click (and a
  confirmation) runs it. Before, a dialog at start-up: a hurried “Non” hid it for a
  day. The web interface has the same button in its title bar.
- **A version is announced only once it is signed.** It used to be offered as soon as
  it was published, before the author signed it, and the click only got “pas encore
  signée”.
- **A PDF CV is adapted to each offer too.** A PDF cannot be edited, so it went out
  identical for every offer. At the first launch, JobHunter now rebuilds it as a plain
  Word file:
  - same text and order;
  - headings, bold job lines with their dates, bullets;
  - contact details under the name;
  - skills on one line, the ones each posting asks for first.

  Measured on 10 real PDF CVs: every word kept, the name found, one page each. The form
  offers a preview (“Voir la version Word”). Untick the box to send the PDF as is. The
  PDF stays next to the Word file either way.
- **Your letters speak in your words**: the form shows the background paragraph of
  your letters, to correct. “Reprendre celui de ma lettre…” takes it from a letter you
  already wrote (.pdf or .docx): the paragraph about your studies and experience, not
  the one about the company. Found in 30 letters out of 30 in a test.

## 3.27.2 — 2026-10-26

- **The CV is read whatever its template**: text boxes (Canva and Word “design”
  templates), content controls (Microsoft resume templates), tables inside tables, and
  the page header and footer, where the name often sits. Before, such a CV gave almost
  no text and the first launch created no profile.
- **The first launch's questions are in a window, not a console**: name, e-mail, phone,
  city, jobs, years of experience, regions and companies, prefilled from the CV, to check
  and complete. If the profile cannot be created, the window says why and offers another
  CV. A scanned PDF (an image, no text) is flagged in the form: use the .docx instead.
- **PDF first, and read better**: the PDF is the format most CVs come in.
  - On a two-column design (Canva), the name now comes first. Before, the sidebar came
    first: on a fictitious CV, the name read was “Gestion de projet” and the job
    “Bordeaux”.
  - Ligatures (“ﬁ”, “ﬂ”) are expanded, so “ﬁnance” matches the keywords again.
  - A PDF protected by a password, scanned, or with its text turned into curves now
    gets its own advice.
  - Measured on 10 real PDF CVs: name, e-mail, phone and jobs read identically.
- **The welcome windows take the new interface's design**: warm background, pale panel,
  dark main button, brown ticks, Inter font, instead of Tk's grey default. As in that
  window, there is no Windows title bar: the corners are rounded, and a white bar on top
  carries the brand, “reduce” and “close” (drag it to move the window). The form scrolls
  on a short screen, and its buttons stay visible at the bottom.
- “New profile” (desktop and web interface) uses the same window.
- **A three-step tour after the first profile**, in the same window, each step skippable:
  1. the job sites scanned, by group, and which ones refuse robots (outside the daily
     collection);
  2. the free API keys (France Travail, Adzuna, Jooble): what each brings, a link to its
     official page, masked fields; the key goes into the file the source reads, on this
     PC only;
  3. a first real scan of the quick sources (LinkedIn, V.I.E, makesense, plus each API
     whose key is set), with its log, then the three best offers and how to go on in
     the application. Nothing is ever sent.

## 3.27.1 — 2026-10-26

- **Dark mode in the web interface**: Settings → Colours and font → Mode, “Comme
  Windows” (follows the Windows setting, live), light or dark.
- **Narrow window**: below 1100 px the offers' filters stay on one line that scrolls
  sideways, instead of five lines pushing the table down.
- **Fewer cut words, no false hovers**: titles, companies and table cells wrap on two
  lines instead of ending in “…”; a text still cut shows in full in its tooltip. Only the
  rows that open something light up under the mouse (offers, documents, recent
  applications), not the tables of Sources, Statistics or recipes.
- **README**: the screenshots are rebuilt, and the new interface is shown (home in light
  mode, offers in dark mode) with how to install and open it. `tools/screenshots.py`
  captures it headless, on the fictitious profile only.

## 3.27.0 — 2026-10-26

- **A new interface, in a web window** (`python -m jobhunter.web`, extra `web`:
  `pip install "jobhunter[web]"`). It does what the desktop application does, with
  another design: home, offers (filters, saved views, chosen columns, ticked offers,
  status, notes, set aside, recycle bin, undo), applications, follow-ups, documents,
  statistics, profile (identity, search, skills, fit weights, base CV), sources
  (keywords, followed companies and their directory, job boards, access and API keys),
  settings (look, language, update, daily collection, profiles) and the tools menu
  (cleaning recipes, documents to compare, CV and letters in bulk, replies read from
  mail). The desktop application stays the default; nothing is sent from the web
  window: applying is done from the desktop one, the final click being yours.
- An API key typed in the web window goes straight to the file its source reads; it is
  never shown again. Logins are made by you, in the browser: no password is handled.
- The skills editor keeps the space at the edge of a synonym: « ia » no longer finds
  « social » once the skill is saved.
- Development: logic shared by both interfaces moves out of the desktop package
  (`inventory`, `base_cv`, `tools_catalog`); the old module names still import.

## 3.26.2 — 2026-10-26

- Development: `tools/release.py` makes a release in two commands (`preparer X.Y.Z`,
  then `publier <PR>` once the CI is green); it never signs. A pre-push hook runs
  mypy as the CI does (`pre-commit install --hook-type pre-push`), and AGENTS.md asks
  every session, cloud ones included, to run ruff, mypy and the tests before a push.
- Development: `bench.py comparer` must run on an installed copy of the engine
  (`pip install --no-deps --target <dossier> .`, then `PYTHONPATH=<dossier>`); with
  `PYTHONPATH=src` it reported thousands of false differences on real data.

## 3.26.1 — 2026-10-26

- **Postings in a non-Latin script are recognised.** One written mostly in Japanese,
  Chinese, Korean, Thai, Hebrew, Arabic, Greek, Cyrillic, Hindi, Bengali, Tamil, Georgian
  or Armenian now gets the cap of a language not spoken (fit 2), like a Dutch or
  Spanish one. The language check only counted Latin function words, so these came
  out « undecided » and kept their fit: 113 offers of a real queue, 36 of them at 6 or
  more. A few ideographs in an English posting (an office address) change nothing:
  the script must make a fifth of the letters.
- Development: `virtualenv` 21.14.13 in `uv.lock` (security advisory on 21.14.9–12).

## 3.26.0 — 2026-10-26

- **The progress moves to the top bar**, right of the page title: a progress bar and
  one line (« 3/8 sources · 58 % · ~7 min restantes · 642 offres trouvées », or
  « Vérification 120/900 · 13 % · 7 fermée(s) »), shown only while something runs. It
  sat at the bottom of the left menu in small type, over four lines, and pushed the
  « Lancer la collecte du matin » button out of shape.
- **Hovering the progress** lists each source on its own line with its sign, then what
  the signs mean (✓ answered, ◐ in part, ⏸ limited, ⛔ refused, ∅ nothing new).
- `tools/sweep_app.py` works on Windows: its fake process now supports
  `subprocess.run` (the scheduled-task check), which it reported as an app error.
  It no longer opens the « Outils » and « Profils… » menus on screen either: on
  Windows they waited for a click elsewhere, and the sweep stood still.

## 3.25.5 — 2026-10-25

Five design and testing methods applied to the app (break-ui, emil-design-eng,
create-design-md, UI UX Pro Max, webapp-testing):

- **Worst-case data** (break-ui: very long names, Chinese, Arabic, emoji, HTML in a
  title, a line break, empty fields, a fit written as text, 0, 1 and 5,000 offers):
  - the Statistics page no longer stops on a fit written as text (« 9 »);
  - a title with a line break no longer doubles its row in the table;
  - « AT&amp;T » and HTML tags from a source are cleaned at collection;
  - an offer without a title gets « Candidature spontanée », not « au poste de ce
    poste ».
- **« Ne plus suivre » a company** asks first: its feed address is lost with it.
- **DESIGN.md** at the root documents the app's colours, fonts, shapes and rules,
  validated with the DESIGN.md linter.
- Checked: every text colour of the theme reaches the 4.5:1 contrast (WCAG AA).

## 3.25.4 — 2026-10-25

- **Keywords changed in « Ma recherche » were never used by the collection**: it reads
  `sources_config.json` first, and the page only wrote the profile. Both are now
  written together, and the page shows the list the collection really uses. A keyword
  added or removed in « Sites d'offres » is also written to the profile.
- Checked: a skill added, changed or removed in the app reaches the fit, the ATS %,
  the letter, and leaves its axis when removed; a title word kept or set aside in
  « Ma recherche » changes the title filter at once.

## 3.25.3 — 2026-10-25

- Switching profile in the app (Profil → Ouvrir) was tested for real, there and back:
  the window restarts on the other profile with its own offers, name, job and skills.
- Saving « Ma recherche », the skills or the fit weights keeps every other detail of
  the profile.
- **A skill added in the app is quoted in the letter**: it had no sentence form, so
  the letter never named it. It is now written in lower case (« consolidation »), an
  acronym as it is (« SAP »).

## 3.25.2 — 2026-10-25

The Profile, Fit, Statistics and Companies pages, read for seven profiles:

- **Companies**: a new finance profile kept « the ~90 finance companies » but got
  none: it copied the main profile's settings, whose lists were empty. Fixed.
- **Statistics**: under « Sur les offres à fit ≥ 8 », the percentages were of the whole
  queue (21 blocked out of 24 showed « 12% »); they are now of those offers.
- **Fit**: the axes show their name (« Santé », « Développement »), not their key
  (« Sante », « DEV »).

## 3.25.1 — 2026-10-25

**The app, clicked everywhere**: every button of every page and every entry of
« Outils », on five profiles and in the four languages, with the questions answered
« yes » and the buttons of the windows that open clicked too (`tools/sweep_app.py`,
over 590 clicks). No error. One window stayed in French in the other languages (« CV /
lettres », how many offers to process): translated.

## 3.25.0 — 2026-10-25

**Any CV**: 45 fictitious CVs (42 jobs, from nurse to forklift driver, lawyer or
architect; Word, two columns, Canva PDF, English) now go through the profile creation
and are checked automatically (`python tools/sweep_cv.py`). All 45 pass. What the
sweep found and fixed:

- **Your own job was sorted out as senior** when its title says « Chef de rayon »,
  « Responsable logistique » or « Responsable RH ».
- **Years of experience** are read from the dates of your jobs (« 2019-2026 ») when the
  CV does not write « N ans d'expérience »: a seven-year manager was taken for a junior.
- **Skills the CV does not have** no longer appear in the letter: « perfusion » read as
  mergers and acquisitions, « tableaux électriques » as Tableau, « évaluation » as DCF
  valuation, « conseil client » as strategy consulting, « gestion des stocks » as supply
  chain.
- **New skills** in the catalogue: instructional design, contract law, company law,
  data protection, non-financial reporting, life cycle assessment, inventory management.
- A title with a digit (« Commercial B2B ») is proposed as your job, not « PROFIL ».
- The letter says « Je suis… » for any job, and short CV summaries are kept.
- CAP, bac pro, CACES, FIMO, CQP, DN MADE, titre professionnel are degrees.
- Your own skills are written in lower case in the letter, and « CACES 1, 3 et 5 » is no
  longer split into a skill « 3 et 5 ».

## 3.24.1 — 2026-10-25

Harder CVs and the rest of the app, tested:

- **Canva CVs** (PDF in columns): the name on two lines, the spaced headings
  (« C O M P É T E N C E S »), one language per line and a degree such as « DCG » are
  read. A name in capitals is signed « Julie Moreau », not « JULIE MOREAU ».
- **A scanned CV** (an image) no longer creates an empty profile: nothing is written
  until a text CV or the jobs (`--metiers`) are given.
- **Foreign phone numbers** (+44, +1…) are read.
- « bilan » or « portefeuille » alone no longer make an accountant a financial analyst
  or an asset manager.
- **Automatic CV facts**: the example file wrote `\b` in JSON, which is an invisible
  character: those triggers never fired. Fixed, and such triggers in your own
  `CV/Facts.json` now work — **check your facts**: some may start to apply.
- **Offers in Tunisia, Morocco, Algeria, Senegal, Côte d'Ivoire, Cameroon** get a
  French letter when their text is too short to tell.
- **Linux/macOS**: `schedule.sh` no longer says « planifiée » when cron is missing;
  a Python without Tk is explained at install and start instead of a crash.
- `mail-statuses --eml` accepts a single `.eml` file.
- The app's « Vérifier les offres en ligne » button fits the side bar; the statistics
  translate « Autre », « manuel », « auto ».

## 3.24.0 — 2026-10-25

The CV and the letter, read one by one for four new profiles:

- **The CV follows the offer**: on a profile created from your CV, the skills line puts
  first the ones the posting names. Nothing is added or removed.
- **The letter says « Je »**: the summary taken from the CV (« Ingénieure diplômée
  de… ») becomes « Je suis ingénieure diplômée de… ».
- **No hollow sentence**: without a background paragraph (an English CV in a French
  letter), « Au fil de ce parcours » becomes « Je me suis familiarisé avec… ».
- **No claim the CV does not make**: Docker alone no longer makes the letter say « le
  cloud » (cloud and continuous integration are two skills now); a nurse's letter says
  « les soins aux patients », not « le soin ».
- « d'État » keeps its capital in the letter's subject too.
- Recreating your profile (`profile <cv> --force`) puts the queue's offers in its new
  domains (the statistics showed « Autre » for most of them).

## 3.23.1 — 2026-10-25

Every command and every panel of the app run again on four new profiles:

- **The ATS %** is measured against the job's usual skills, not only the CV's own: a
  profile built from a CV showed 100 % on every offer. Recreate your profile
  (`jobhunter profile <cv> --force`) to benefit, then « Recalculer le fit ».
- **Job titles in both genders and both languages**: « Infirmière » postings were not
  recognised for an « Infirmier » profile, nor « Développeur » for an English CV
  (« Developer »); « Software Engineer » now counts as a developer's posting.
- **An English CV** writes its summary in the English letter, not in the French one.
- **« Sonder mots-clés »** tries keywords of your own job (a nurse was offered
  « notation esg »).
- **Adding an offer from a French LinkedIn page** reads its title and company (the
  company was « Fr »).
- An experienced profile's letter no longer says « expérience » three times; a message
  no longer starts a paragraph with a space; « d'État » keeps its capital.
- `profiles use principal` finds the main profile after it was renamed; the weekly
  summary of a new installation no longer lists the days before it.

## 3.23.0 — 2026-10-24

Four new profiles (aerospace engineer, nurse, junior developer, management
controller) run from the CV to the letters, with the morning routine:

- **PDF on macOS and Linux**: LibreOffice was looked for only in `C:\Program Files`:
  the CV and letter stayed `.docx` everywhere else. Now found on every system.
- **A CV in PDF** (or a Word CV laid out in a table) is read for the ATS %: it gave 0 %
  on every offer.
- **Health skills** in the catalogue (nursing care, multidisciplinary team, care
  records, emergency and intensive care, infection prevention…): a nurse's offers
  scored 4 almost all; now 41 at fit 9 or more out of 127.
- **Volunteer roles** (« bénévole », « volunteer ») are a contract type, set aside like
  internships: an unpaid role came first for a junior developer.
- **makesense offers** get their description again (the page refuses the automated
  browser; it is read the way the collection reads it).
- **A first profile from a CV**: generic words of a title (« gestion », « État »,
  « diplômé »…) no longer widen the title filter; an English CV's languages are said
  in French in the messages.
- **The quick trial** (`pipeline --rapide`) collects from LinkedIn and makesense: APEC,
  which refuses every request, left the trial with an empty list.
- Updating no longer fails on a system without `crontab`.

## 3.22.0 — 2026-10-24

Still for someone whose job is not finance:

- **No Claude Code needed after the profile**: your degree and languages are read from
  the CV for the messages, and the end message points to « Ma recherche » and
  « Profil » in the app (Claude Code stays optional).
- **Letters with experience**: from 3 years of experience, the letter says « Dans ces
  postes, j'ai mis en œuvre… J'apporterai cette expérience à vos équipes » instead of
  the young-graduate wording. Set by `lettre.ton` in the profile.
- **Companies from your offers**: « Entreprises » › « Trouver depuis mes offres » looks
  for the public recruiting feed of the companies of your good offers, and follows
  only the feeds that really hold one of their offers (a feed guessed from a name can
  belong to another company). Same thing by hand: `probe_ats_queue --ajouter`.
- **eFinancialCareers and FIR** (finance and ESG job sites) are skipped when your title
  filter keeps no finance job: they would bring nothing.
- Statistiques: the Domaine section shows each domain's name, not its file key.

## 3.21.1 — 2026-10-24

A new user with another job, checked from start to end (CV, profile, collection,
sorting, letters). The profile made from a CV is better for any job, not only finance:

- **A job title in the feminine** (« Ingénieure », « Technicienne », « Conseillère »)
  no longer removes its own offers: the sorting used to drop « Ingénieur structure »
  postings for an « Ingénieure structures » profile. The masculine form is also
  searched, and the letters' agreement is guessed right.
- **Title words in the plural** (« structures ») now also find the singular.
- **Years of experience** are read from the CV (« Trois ans d'expérience ») and proposed,
  instead of 0, which set aside every « confirmé » posting.
- **Skills**: the LinkedIn address no longer counts as « Réseaux sociaux ». New in the
  catalogue: structural analysis (Nastran, finite elements…), composites, fatigue,
  aircraft certification, numerical simulation. The skills your CV lists in its own
  « Compétences » section and the catalogue does not know are kept too, in your core axis.
- **Welcome to the Jungle** reads the postings your title filter keeps, your core
  titles first, instead of a fixed ESG list.
- An empty list now says what to do: click « Actualiser les offres ».

## 3.21.0 — 2026-10-24

- **New source: Jobs that make sense** (jobs.makesense.org), impact jobs: climate,
  CSR, social economy. Its public sitemap is read, your title filter sorts the
  offers, then at most 30 new ones per collection are opened (description included).
  It runs in the morning collection, next to eFinancialCareers (`--makesense` by hand).
- **« Intitulés à garder / à écarter » readable**: one word per line instead of one long
  pattern cut in the middle of words. A word finds what starts with it (« financ »
  finds finance, financier); « *mot » also finds it inside a word (« *analyst » finds
  Nachhaltigkeitsanalyst). Saving keeps the same choices on the reference titles, and
  short words are now bounded: « rse » no longer finds « diverse » or « vendeurse ».
- **Choose your cities in « Ma recherche »**: type a city, a region or a country, press
  « Rechercher », then « + Prioritaire » or « + Secondaire ». Only the places you chose
  are listed, each removed by its ✕; any city of the world works (London, Geneva…).
  Until now they could only be changed by editing `profile.json`. They never change
  the fit: they fill the Zone column, and the offers already in your list are
  relabelled when you save.
- **Two more career-page feeds**: Personio (`personio`, XML) and Breezy HR (`breezy`,
  JSON), to list in `autres_flux`. `probe_ats` now looks for them too, and its built-in
  list gained about 80 finance names (private equity, fintech, sustainable savings).
- **Company lists checked live**: 22 accounts no longer answered (the company had
  moved to another recruiting tool, or closed its page) and left. Pennylane, Qonto,
  Back Market and Sweep were found at their new address. Added: Shift Technology,
  Younited, Finary, Akur8, iBanFirst, PAI Partners, Capza, EcoVadis.
- **A Workable, Personio or Breezy career page pasted in « Entreprises » is now
  collected.** A Workable address used to go into a list the collection never reads.
- **HelloWork, as a trial** (`--hellowork`, outside the morning collection): you asked
  for it, knowing its terms forbid automated extraction. Only what its robots.txt
  allows is read: the job-name pages (the closest to your keywords first, 15 per
  pass), their city pages for your priority zones, their internship and work-study
  pages unless you exclude those contracts (40 list pages in all), then at most 30
  new offers, two seconds apart. Its sitemap answers 403
  (Cloudflare): not used. A refusal stops the pass; nothing is worked around.
- Places of eFinancialCareers, WTJ and makesense offers lose a double space when
  the region is missing (« Paris  FR »).

## 3.20.0 — 2026-10-23

- **The collection shows where it is**: under the « Outils » button, a line such as
  « 3/8 sources · 42 % · ~6 min restantes · 812 offres trouvées », then « 136 nouvelles
  ajoutées » once merged. The time left comes from each source's usual duration (the
  median of its last five collections) and counts down between two lines.
- **So does the availability check**: « Vérification 120/900 · 13 % · ~14 min restantes
  · 7 fermée(s) », and at the end how many offers left the queue. The time left never
  exceeds the check's own limit (30 minutes from the button).
- **☰ at the top left folds and opens the menu** (Ctrl+B still does), and the menu
  opens as you left it.
- **One place for the settings**: the ⚙ wheel becomes « Outils » (scan, batch
  applications, maintenance, folder). The language and the update were already in
  « Paramètres » and leave that menu; « Collecte chaque matin… » moves to « Paramètres »,
  with whether it is scheduled.

## 3.19.1 — 2026-10-22

- **Two actions in the left menu**: « Actualiser les offres » and a new « Vérifier que
  les offres sont disponibles » (checks each offer is still open, then removes the
  closed ones — never one you applied to, the queue copied first; 30 minutes at most).
- **A ⚙ wheel at the bottom left** holds everything else, by intent: Scan offres,
  Candidatures en lot, LinkedIn, then one submenu per group (Sources & offres,
  Documents, Hygiène de la file, Suivi, Accès & diagnostic), the folder and Recharger.
  It replaces the three step buttons, the folded « Maintenance » list, « Recharger »
  and « Dossier ».
- The « ↶ Retour » button is gone (Alt+Left still undoes a layout change). The menu
  entries are a little tighter so that everything fits without scrolling.
- **No « Offres » button on every page**: the menu entry is enough. The pages lose
  their duplicate title too (the bar at the top names the page), the status line moves
  up to that bar, and the page margins shrink: each page takes the room.
- **JobHunter's own icon** (a briefcase and a magnifier on the app's blue) on the
  window and the taskbar, instead of Python's or CustomTkinter's.
- **The ⚑ column explains itself**: hovering its header shows its three signs
  (⚠ knock-out condition, ↻ reposted 3 times or more in 90 days, ≡ same text under
  another company).

## 3.19.0 — 2026-10-22

- **A « Paramètres » panel** in the menu: the interface language, as one row of
  buttons (Français, English, Deutsch, Español) — JobHunter restarts in it at once —,
  the version and « Vérifier les mises à jour ». The language was hidden under
  Maintenance and applied only at the next start.
- **One language for every profile.** It was saved in each profile's folder:
  opening another profile switched the interface back to French.
- **Statuses and contracts translated.** In English, German or Spanish, the table,
  the status menu, the card and the history showed « postulé », « entretien »,
  « CDI »… They are still stored in French (the follow-ups and the tracking read
  them), and shown in the interface language; a status chosen in English is saved
  in French. Also translated: the statistics' sections, the companies' counter, the
  job sites' help line.
- Wider « Vérifiée » and « Contrat » columns: « Checked » and « Permanent » were cut.
- **A plainer window.** Gone: the log box at the bottom of the left menu (« Prêt… »,
  the shortcuts list, the follow-ups reminder — each message still shows on the
  status line under the table), the « JOBHUNTER » heading above the profile list, and
  the « Réduire le menu » button (Ctrl+B still folds the menu, which now always
  opens unfolded). The window is titled « JobHunter ».

## 3.18.1 — 2026-10-22

- **The active profile is named at the top left, always**, under « PROFIL ACTIF », and
  in the window's title. It was shown only once a second profile existed, in small
  print. It is a drop-down list: every profile (● the open one), « Nouveau profil… »
  and « Gérer les profils… »; choosing a profile opens it. It follows renames,
  creations and archives.
- **Choosing a profile opens it at once**: the window restarts on its data, without a
  question (refused while a task runs, so as not to cut it). The « Profil » panel is
  now at the top of the menu.
- **« Lancer la collecte du matin » collects the open profile only.** It ran every
  profile one after the other; the scheduled task still does.
- **A launcher that skipped the active profile no longer opens the wrong one.** An old
  copy of `JobHunter.pyw` started the app without applying the chosen profile: the
  main profile opened whatever was chosen. The app now notices it and restarts itself
  on the active profile.

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
