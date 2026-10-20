## What

<!-- One or two sentences: what changes, and why. -->

## Checks

- [ ] `uv run pytest -q` passes (offline)
- [ ] `uv run mypy` passes
- [ ] `uv run python tools/bench.py comparer tools/bench_reference.json` — 0 difference,
      or the reference is regenerated in this PR with the reason
- [ ] `CHANGELOG.md` updated if users will notice
- [ ] No personal data (profile, offers, letters, CVs, keys) — `python tools/personal_data.py`

## Project rules

- [ ] Nothing is sent automatically: the final “Send” click stays human
- [ ] No anti-bot circumvention, no CAPTCHA solving, no password handled by the code
- [ ] A new source respects the site's robots.txt and terms of use
