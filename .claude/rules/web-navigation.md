---
paths:
  - src/jobhunter/navigation/**
  - src/jobhunter/navigation/strategies.py
  - src/jobhunter/navigation/*.py
  - src/jobhunter/programs/apply_runner.py
  - src/jobhunter/programs/access.py
---
# Web navigation and application

`web_nav.py` (3400 lines, the biggest piece) drives Playwright (standard, no stealth engine):
cookie banners, ATS detection, offer search, fallback to the careers page.
`site_strategies.py` holds the per-site strategies. `apply_runner.py` fills in and
uploads, **and stops at the Send button**.

## Limits that are decisions, not gaps

They have held since the start of the project and are not to be reopened in passing during a task:

- **No automatic submission.** The final send click is the user's. Ten
  automatic submissions in July produced zero confirmations. Add no
  `--auto` / `--submit` flag to `apply_runner.py`.
- **No anti-bot bypass**: no TLS fingerprint, no IP rotation, no CAPTCHA
  solving, no "stealth" engine (patchright, rebrowser), no masking of
  the automation (`navigator.webdriver`, `--enable-automation`,
  `AutomationControlled`), no "human" mouse or typing. The browser presents
  itself as automated.
- **Never the personal Chrome profile** (`User Data`): it holds the user's sessions and
  passwords. Only the dedicated profile of `access.py` is used. A detected CAPTCHA pauses for a human. Thirteen sites are
  inaccessible and stay so.
- **No password handled by the programs.** Sessions live in a
  dedicated Chrome profile; login is done once by hand through
  `python -m jobhunter acces --open <site>`.
- **No account creation, no reading of a mailbox by a program.** A code
  received by email (OTP) is read and entered by hand.
