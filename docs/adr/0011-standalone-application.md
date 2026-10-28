# 0011 — A standalone application for the user, the source code for whoever modifies it

**Status**: accepted on 2026-10-19 (step F4 of the roadmap, JobHunter 2.9.0).

## Context

Installing JobHunter required Python 3.12+, a ZIP to unzip, `installer.bat` (libraries
and Chromium browser), then `lancer.bat`. That is reasonable for someone who wants to modify the code,
off-putting for someone who just wants to look for a job. The user wanted a
"Download" button that gives an installer, like the Ibaraki project, with no Python required,
while the code remains downloadable for anyone who wants to customise it.

Constraints:
- the application launches its programs as subprocesses, through `[PY, "-m", module]`: without
  Python, an executable that understands `-m` is needed;
- the user's data must never live in the program folder, which the
  update replaces;
- embedding Chromium would make the installer about 150 MB heavier.

## Decision

- **Two executables compiled by PyInstaller, in the same folder**:
  `JobHunter.exe` (window, no console) and `jobhunter-cli.exe` (console). The second serves
  as the interpreter for subprocesses: it understands `-m module`, `-c code` and the
  `jobhunter` commands (`jobhunter.gele.aiguiller`). `jobhunter.gele.interpreteur()` designates it;
  under Python, it is `python.exe` (never `pythonw.exe`, which has no standard output).
- **Data in `Documents/JobHunter`** (or `JOBHUNTER_RACINE`). On first launch, the
  shipped skeleton is copied there (example profiles, source settings, CV folder),
  never replacing a file that is already present.
- **Inno Setup installer**, for the single user and without administrator rights
  (`%LOCALAPPDATA%\Programs\JobHunter`). It replaces the program folder entirely; the
  uninstall does not touch the data.
- **Built by the CI** (`.github/workflows/installateur.yml`) at every release, checked
  (silent installation, first launch), and attached to the release. The README points
  to `releases/latest/download/JobHunterSetup.exe`.
- **No embedded Chromium**: without Playwright's Chromium, the collection launches the system's Chrome or
  Edge (`navigation.navigateur.lancer`); Edge is present on every Windows 10/11.
  Applications and logins already used Chrome.
- **Update**: the installed application does not replace its files one by one. Since
  2.18, it downloads the new installer, checks it (the author's signature,
  ADR 0012; failing that, the published fingerprint) and opens it; Inno Setup closes the application
  (`CloseApplications`) and keeps the data. Offline, it opens the release page.

## Consequences

- Two audiences, two paths: the installer for use, the source code (ZIP or clone,
  with Python) for customising; the README presents both.
- The installed application takes up about 245 MB (Python, Playwright, libraries).
  Since 3.62, Playwright's `node.exe` (88 MB) is not in the installer: attached to
  the release, it is downloaded and checked (SHA-256 written by the build) the first
  time a browser starts, into `%LOCALAPPDATA%/JobHunter/node/` (`jobhunter.playwright_node`).
- The morning scheduled task: `planifier.bat` for the source code; since 2.19,
  the application (installed or not) creates it itself, Maintenance → "Collecte chaque
  matin…" (Collect every morning…) (`jobhunter.planification`, same task name, `jobhunter-cli.exe pipeline`).
- **Test on every build** (2.19): the CI installs with no Python on the PATH, then
  `outils/installateur/essai_installe.py`, run by the embedded Python, launches the
  system browser, merges a fictitious scan, writes a folder and prepares the
  update; the window must open and stay open; the next installer installs
  over it, keeping the data.
- The network test programs (`test_*`) read the queue at import: they are excluded from the
  executable's load check.
