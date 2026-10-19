# Developer tools

Scripts for whoever modifies JobHunter. None of them is part of the installed package;
the user never runs them. Run them from the repository root with `uv run python …`.

| Tool | What it does |
| --- | --- |
| `banc.py` | Non-regression bench: records what the engine decides for each offer, then compares after a change (`enregistrer`, `comparer`). ADR 0006. |
| `banc_offres.py` | The fictitious, deterministic offers the bench runs on in CI. |
| `banc_reference.json` | The bench's reference decisions on those offers (384 offers). |
| `rejeu.py` | Records a source's real public response once, then replays it in `tests/test_rejeu_sources.py` without network. |
| `annuaires.py` | Regenerates the Lever, Ashby and Greenhouse company directories shipped in the package. |
| `donnees_perso.py` | Pre-commit check: refuses personal data (CV, queue, tracker, keys) in the public repository. |
| `verifie_version.py` | Checks that `VERSION` and `pyproject.toml` carry the same version (CI and pre-commit). |
| `signature.py` | Signs a published release with the author's private key (`cle` once, then `signer X.Y.Z --publier`). ADR 0012. |
| `installateur/` | Standalone application and Windows installer: `construire.py` builds them, `JobHunter.spec` (PyInstaller) and `JobHunter.iss` (Inno Setup) describe them, `lanceur.py` is the executables' entry point, `essai_installe.py` is the CI trial of the installed app. ADR 0011. |

Typical release check, after a change to the engine:

```bash
uv run python outils/banc.py comparer outils/banc_reference.json
uv run python outils/verifie_version.py
```
