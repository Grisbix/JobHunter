# Security policy

## Supported versions

Only the latest release receives fixes. The app offers each new version at start-up.

## Reporting a vulnerability

Please **do not open a public issue**. Use GitHub's private reporting instead:
[Report a vulnerability](https://github.com/Grisbix/JobHunter/security/advisories/new).
You will get an answer within a week. Once fixed, the advisory is published with credit,
unless you prefer otherwise.

## What JobHunter does to stay safe

- **Your data stays on your machine.** Profile, CV, letters, offers and application log
  are ignored by git and never sent anywhere. API keys live in local files
  (`Scripts/adzuna.json`, `Scripts/jooble.json`), never in the repository.
- **No passwords** are read, stored or typed by the programs; no account is created
  automatically; nothing is ever sent on your behalf — the final click is yours.
- **No anti-bot circumvention**: a site that refuses access is left alone.
- **Network**: only `http(s)` URLs are opened (`jobhunter.network.exiger_http`); update
  archives cannot write outside the program folder; sitemaps with a DOCTYPE are refused.
- **Supply chain**: GitHub Actions are pinned to commit SHAs with read-only tokens by
  default; dependencies are locked (`uv.lock`) and watched by Dependabot; CodeQL and
  secret scanning (with push protection) run on the repository.
- **Installer provenance**: each `JobHunterSetup.exe` is built by CI from a tagged release,
  with a SHA-256 file and a signed build attestation. Check it with:

  ```bash
  gh attestation verify JobHunterSetup.exe --repo Grisbix/JobHunter
  ```

  The installer is not code-signed yet, so Windows SmartScreen may warn on first run.
