# Developer tools

Scripts for whoever modifies JobHunter. None of them is part of the installed package;
the user never runs them. Run them from the repository root with `uv run python …`.

| Tool | What it does |
| --- | --- |
| `bench.py` | Non-regression bench: records what the engine decides for each offer, then compares after a change (`enregistrer`, `comparer`). ADR 0006. |
| `bench_offers.py` | The fictitious, deterministic offers the bench runs on in CI. |
| `bench_reference.json` | The bench's reference decisions on those offers (384 offers). |
| `replay.py` | Records a source's real public response once, then replays it in `tests/test_rejeu_sources.py` without network. |
| `directories.py` | Regenerates the Lever, Ashby and Greenhouse company directories shipped in the package. |
| `personal_data.py` | Pre-commit check: refuses personal data (CV, queue, tracker, keys) in the public repository. |
| `check_version.py` | Checks that `VERSION` and `pyproject.toml` carry the same version (CI and pre-commit). |
| `signature.py` | Signs a published release with the author's private key (`cle` once, then `signer X.Y.Z --publier`). ADR 0012. |
| `installer/` | Standalone application and Windows installer: `build.py` builds them, `JobHunter.spec` (PyInstaller) and `JobHunter.iss` (Inno Setup) describe them, `launcher.py` is the executables' entry point, `check_installed.py` is the CI trial of the installed app. ADR 0011. |

Typical release check, after a change to the engine:

```bash
uv run python tools/bench.py comparer tools/bench_reference.json
uv run python tools/check_version.py
```
