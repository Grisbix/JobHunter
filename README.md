# JobHunter

[![tests](https://github.com/Grisbix/JobHunter/actions/workflows/tests.yml/badge.svg)](https://github.com/Grisbix/JobHunter/actions/workflows/tests.yml)
[![version](https://img.shields.io/github/v/release/Grisbix/JobHunter)](https://github.com/Grisbix/JobHunter/releases/latest)
[![licence](https://img.shields.io/badge/licence-MIT-blue)](LICENSE)

🇬🇧 English · [🇫🇷 Français](README.fr.md)

**Your job search, prepared every morning.** JobHunter collects job offers from dozens of
sources, scores them from 1 to 10 against **your** profile, and prepares a tailored CV, a
cover letter and a short message for each one. **It never sends anything**: the final
“Send” click is always yours.

Everything runs on your computer. Your CV and your applications never leave your machine.

<p align="center">
  <a href="https://github.com/Grisbix/JobHunter/releases/latest/download/JobHunterSetup.exe"><img alt="Download the Windows installer" src="https://img.shields.io/badge/Download-JobHunterSetup.exe-2563eb?style=for-the-badge&logo=windows&logoColor=white"></a>
  &nbsp;
  <a href="#from-source"><img alt="Source code" src="https://img.shields.io/badge/Source%20code-customise-334155?style=for-the-badge&logo=github&logoColor=white"></a>
</p>

<p align="center"><sub>Windows 10/11 · no Python, no administrator rights · your data stays in <code>Documents\JobHunter</code></sub></p>

| Offers, ranked for your profile | The letter prepared for an offer |
|---|---|
| ![Offer list](docs/screenshots/offers.png) | ![Generated letter](docs/screenshots/letter.png) |

<sub>Screenshots use a **fictitious** profile and offers (Léa Martin, communications officer in Lyon). They show the French interface: switch to English in Maintenance → “Langue : English”.</sub>

- [Install (Windows)](#install-windows) · [From source](#from-source) · [macOS / Linux](#macos--linux)
- [Set up your profile with Claude Code](#set-up-your-profile-with-claude-code)
- [Day to day](#day-to-day)
- [The profile](#the-profile)
- [Project rules](#project-rules)
- [Troubleshooting](#troubleshooting)

---

## Install (Windows)

1. **Download [`JobHunterSetup.exe`](https://github.com/Grisbix/JobHunter/releases/latest/download/JobHunterSetup.exe)**
   and run it. No Python, no administrator rights: JobHunter installs for you only and adds
   a Start menu shortcut.
2. **On first launch**, pick your CV (`.docx` preferred): JobHunter reads it and asks five
   questions (target jobs, experience, cities, grammatical gender for French letters, sector).
3. **Click “Actualiser les offres”** (refresh offers): collection, scoring and documents all
   run from the app.

Your data (profile, CV, letters, offers, application log) lives in `Documents\JobHunter`:
updates and uninstalling never touch it. To update, the app offers the new version at
start-up; download and run the new installer.

Recommended: [LibreOffice](https://www.libreoffice.org/download/) (CVs and letters as PDF)
and Google Chrome (semi-automatic applications; without it, collection uses Edge, which
every Windows has).

## From source

To customise or develop JobHunter: the full code, with Python 3.12+.

| Tool | | What for |
|---|---|---|
| [Python 3.12+](https://www.python.org/downloads/) | **required** | runs JobHunter — `installer.bat` offers to install it |
| [LibreOffice](https://www.libreoffice.org/download/) | recommended | CVs and letters as PDF (otherwise `.docx`) |
| [Claude Code](https://claude.com/claude-code) | recommended | sets up your whole profile from your CV |
| [Git](https://git-scm.com/downloads) | optional | fetch updates (`git pull`) |
| [Ollama](https://ollama.com/) | optional | letters written by a free local AI |

1. **Download** the [source code](https://github.com/Grisbix/JobHunter/releases/latest)
   (`Source code (zip)`) or clone the repository, and unzip it.
2. **Double-click `installer.bat`**: Python libraries and the Chromium browser (a few
   minutes, once). Without Python, it offers to install it (winget). The libraries go
   into a `.venv` folder next to JobHunter, not into your computer's Python.
3. **Put your CV in `Mon_CV`**, a `.docx` preferably. This folder is never published.
4. **Double-click `lancer.bat`**: the first time, it builds your profile from your CV and five
   questions; then it opens the app.

Then: **`planifier.bat`** runs the collection every morning at 8:00 (`planifier.bat 07:30`
for another time, `planifier.bat supprimer` to stop), and **`mettre_a_jour.bat`** fetches
the latest version, checks that everything loads and rolls back on its own otherwise. Your
profile, CV, letters and log are **never** touched.

> **Why a `.docx`?** Every CV sent starts from this template. Write `[nom du poste]` in your
> summary: the exact job title of the offer goes there. A PDF is sent as is, untailored.

### macOS / Linux

Same steps with the `.sh` scripts, in a terminal opened in the folder (Python 3.12+ and, on
Linux, `python3-tk` first):

```bash
./installer.sh
./lancer.sh          # builds the profile from Mon_CV, then opens the app
./planifier.sh       # collection every morning (cron)
./mettre_a_jour.sh
```

> The `.sh` scripts are checked by CI but **not yet tested on a real Mac**: please report issues.

## Set up your profile with Claude Code

The first launch creates a profile that **works**, but a basic one. For a complete profile,
open [Claude Code](https://claude.com/claude-code) in the JobHunter folder and type:

```
/configure-profile Mon_CV\my_CV.docx
```

Claude reads your CV, asks its questions in one message, then fills everything in: job-title
variants, skills and the words offers use for them, scoring, filters, searches, letter
paragraphs. It checks that offers in your field pass and others are dropped. **It invents
no facts**: whatever is not in your CV, it asks you.

## Day to day

| What | How |
|---|---|
| Open the app | Start menu, or `lancer.bat` from source |
| Collect + sort + CV/letters for the best offers | button “Actualiser les offres”, or `python JobHunter.pyw pipeline` |
| CV + letter for the 20 best offers | `python JobHunter.pyw documents --top 20` |
| Semi-automatic form filling | in the app: tick offers, “Postuler la sélection” — you click Send |

`python -m jobhunter` lists every command (`collecte`, `documents`, `postuler`, `pipeline`,
`maj`…). Release notes: [`CHANGELOG.md`](CHANGELOG.md) (in French).

## The profile

Everything about you lives in **`profil/profil.json`**. The engine knows no trade: to change
target, change the profile. Full example: `profil/exemple_finance_esg.json` (a junior in
sustainable finance).

| Section | Content |
|---|---|
| `identite` | name, email, phone, city, `genre` (m/f, for French agreement) |
| `langues_parlees` | `["fr", "en", …]` — an offer written in another language scores 2 at most |
| `domaines` | one per target job: titles, CV to use, the letter's **background paragraph** |
| `competences` | your skills and the words offers use for them |
| `scoring` | how an offer is scored: core of the job, caps, off-target titles |
| `filtre_titre` | words required in a title to collect it, words that exclude it |
| `zones` | priority and secondary areas |
| `collecte.mots_cles` | searches run on LinkedIn, WTJ… |

Check it, offline: `python JobHunter.pyw verifier-profil "Communications officer" "Java developer"`.

## Project rules

- **No automatic sending.** The final click is always yours.
- **No anti-bot circumvention.** A standard browser that declares itself automated. A site
  that refuses (403, CAPTCHA) is left alone for 30 days. Sites whose terms forbid automated
  collection are not collected.
- **No passwords** read, stored or typed by the programs; no automatic account creation.
- **Never your personal Chrome profile**: JobHunter uses a dedicated one.
- **Your data stays with you**: profile, CV, letters, offers and log are ignored by git.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| “Profil introuvable” | run `lancer.bat`, or `/configure-profile` in Claude Code |
| No offer passes | `filtre_titre.metier` too narrow, or `collecte.mots_cles` too rare |
| Too many off-target offers | extend `filtre_titre.exclus` |
| CV not tailored to the offer | CV given as PDF: provide a `.docx` |
| “429” during collection | a site's rate limit: collection waits and resumes on its own |
| “403” or “challenge” | the site refuses: it is skipped, on purpose |

---

**Licence**: [MIT](LICENSE). **Developers**: architecture, conventions and tests in
[`AGENTS.md`](AGENTS.md) and [`CONTRIBUTING.md`](CONTRIBUTING.md); `python -m pytest -q` runs
about 1,850 offline tests on the example profile. The code and its comments are in French.
