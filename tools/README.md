# Developer tools

Scripts for whoever modifies JobHunter. None of them is part of the installed package;
the user never runs them. Run them from the repository root with `uv run python …`.

| Tool | What it does |
| --- | --- |
| `bench.py` | Non-regression bench: records what the engine decides for each offer, then compares after a change (`enregistrer`, `comparer`). ADR 0006. |
| `bench_offers.py` | The fictitious, deterministic offers the bench runs on in CI. |
| `bench_reference.json` | The bench's reference decisions on those offers (384 offers). |
| `replay.py` | Records a source's real public response once, then replays it in `tests/test_source_replay.py` without network. |
| `directories.py` | Regenerates the Lever, Ashby and Greenhouse company directories shipped in the package. |
| `personal_data.py` | Pre-commit check: refuses personal data (CV, queue, tracker, keys) in the public repository. |
| `release.py` | A release in two commands: `preparer X.Y.Z` (branch, VERSION, pyproject, uv.lock), then `publier <PR>` once the CI is green (main, GitHub release, local main; `--installer <dossier>` upgrades the installed package). Never signs. |
| `check_version.py` | Checks that `VERSION` and `pyproject.toml` carry the same version (CI and pre-commit). |
| `signature.py` | Signs a published release with the author's private key (`cle` once, then `signer X.Y.Z --publier`). ADR 0012. |
| `installer/` | Standalone application and Windows installer: `build.py` builds them, `JobHunter.spec` (PyInstaller) and `JobHunter.iss` (Inno Setup) describe them, `launcher.py` is the executables' entry point, `check_installed.py` is the CI trial of the installed app. ADR 0011. |
| `screenshots.py` | The README and Store screenshots, on a fictitious profile, with the real engine and the real web window. |
| `design_check.py` | The window's layout on that fictitious profile, every screen and Sources tab, scrolled top to bottom: reports any text less than 8 px from its card's edge or cut by its container without a fade, and saves one screenshot per screen to judge the empty space by eye. `tests/test_design_layout.py` runs it in CI. DESIGN.md « Layout ». |

Typical release check, after a change to the engine:

```bash
uv run python tools/bench.py comparer tools/bench_reference.json
uv run python tools/check_version.py
```

After a change to the window (`src/jobhunter/web/static/`):

```bash
uv run python tools/design_check.py --out captures          # 0 défaut, then look at the captures
uv run python tools/design_check.py --vide --out captures   # the same with no application
```
