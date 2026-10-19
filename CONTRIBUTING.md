# Contributing to JobHunter

Documentation, comments and docstrings are in English. Identifiers (function and module
names), profile keys and JSON keys stay in French, as do the CLI command names. The French
README is `README.fr.md`. Issues and pull requests in English are welcome. Set up with
`uv sync`, then before each commit run `uv run pytest -q` (about 1,850 offline tests),
`uv run mypy` and `uv run python outils/banc.py comparer outils/banc_reference.json` (0
difference expected). Architecture and conventions: [`AGENTS.md`](AGENTS.md) and
[`docs/adr/`](docs/adr/). The Windows installer is built by
`outils/installateur/construire.py` (see ADR 0011). Rules that are not up for debate:
nothing is ever sent automatically, no anti-bot circumvention, no password handled by the
programs.

## Setting up the development environment

```bash
uv sync                                           # .venv + locked dependencies (uv.lock)
uv run python -m playwright install chromium      # browser for the navigation tests
uv run pre-commit install                         # checks before each commit
```

Python 3.12 or newer. Without uv: `python -m venv .venv`, then
`pip install -r requirements.txt ruff pytest pre-commit`.

## Before each commit

```bash
uv run pytest -q                                                   # ~1,850 tests, no network
uv run python outils/banc.py comparer outils/banc_reference.json   # 0 difference expected
uv run mypy                                                        # types; strict except for programs
```

pre-commit runs ruff (lint and format), checks YAML/TOML, large files, private keys and the
consistency of `VERSION` / `pyproject.toml`. GitHub CI redoes everything, under Windows
and Linux.

**Types and docstrings.** mypy is strict on the whole package except the programs
(`jobhunter.programmes`), which are checked in normal mode. Every public function outside
the programs and the window (`jobhunter.app`) has a Google-format docstring: ruff (`D`)
requires it.

**A source changes its response?** `tests/test_rejeu_sources.py` replays real recorded
responses (`tests/reponses/`). If a site has changed and the parser has been adapted,
record the source again (network, to be run on purpose):
`uv run python outils/rejeu.py enregistrer lever`. APEC, WTJ and the sources that need a
key are not there: entry refusal, anti-bot challenge or credentials.

## Installing the package

`uv sync` installs `src/jobhunter` in editable mode; `pip install -e .` does too. The
`jobhunter <commande>` command then exists (`jobhunter` alone lists the commands). Outside
the repository, `JOBHUNTER_RACINE` designates the folder that contains `Scripts/` and
`profil/` (otherwise the package looks for it going upward from the current folder).
Without installation: `python JobHunter.pyw <commande>`.

## Understanding the code

[`docs/architecture.md`](docs/architecture.md): packages, data, pipeline.
[`docs/adr/`](docs/adr/): the decisions that are not reopened in passing during a task.

## Writing a test

In `tests/`, with pytest, using the fixtures of `tests/conftest.py` (fake network, clock,
throwaway queue and tracking file, browser). Never assign an engine global directly:
`monkeypatch`. Fictitious data and the sample profile only. A test that needs another
profile builds it and passes it to `profil.utiliser(donnees)`, then
`profil.recharger()` at the end of the test.

## Diagnosing a slowdown (py-spy)

When a step exceeds its duration (collection, availability, documents), locate the cause
before assuming. [py-spy](https://github.com/benfred/py-spy) reads the stack of a running
Python program without stopping or modifying it. It is an external tool, not a dependency
of the project:

```powershell
# 1. find the PID of the slow program
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*jobhunter*' } | Select ProcessId, CommandLine

# 2. the stack of each thread, right now
uvx --from py-spy py-spy dump --pid <PID>

# 3. where the time goes, over 60 s (SVG file to open in a browser)
uvx --from py-spy py-spy record --pid <PID> --duration 60 -o lenteur.svg
```

**Never `--locals`**: it prints the variables of each frame, hence offers, letters,
personal paths. Without it, the report contains only function and file names of the
package; it can be attached to an issue.

Verified on 19/10/2026 on Python 3.14: a `time.sleep` triggered in a function
`etape_bloquee` comes out at the top of the `dump`, with its file and line.

## Rules

- **Behaviour unchanged, unless explicitly intended.** The bench proves it. A deliberate
  change regenerates the reference in the same commit, and the message says why.
- **One subject per commit**, clear message that explains the why.
- **The engine knows nobody**: everything specific to a person lives in
  `profil/profil.json` (see `AGENTS.md`).
- **Nothing at import**: no reading, no writing, no network (`tests/test_effets_import.py`).
  A value taken from the profile is written `_PARESSEUX["NOM"] = lambda: ...` and read as
  `_ici.NOM` in its module ([ADR 0007](docs/adr/0007-lazy-profile-values.md)).
- **`print` for a command's output (`main()`), `logging` for the rest**:
  `_log = journal.journal(__name__)`.
- **Non-negotiable limits**: no automatic submission of an application, no anti-bot
  circumvention or CAPTCHA solving, no password handled by the programs. Details:
  `AGENTS.md`.
- The tests run on the **sample profile** and **fictitious offers**, never on real data.

## Publishing a release

1. Bump `VERSION` **and** `version` in `pyproject.toml` (identical).
2. Add the section `## X.Y.Z — date` at the top of `CHANGELOG.md`.
3. CI green on `main`, then `gh release create vX.Y.Z` with the CHANGELOG section: the tag
   serves as the reference for updating ZIP installations.
4. **Sign** (ADR 0012), once the "installateur" workflow has finished, on the computer
   that holds the private key:
   `uv run python outils/signature.py signer X.Y.Z --publier`. Without `signature.json`,
   installations that have the public key refuse the release. The very first time:
   `uv run python outils/signature.py cle`, then commit `src/jobhunter/signature.py`
   and back up `~/.jobhunter/cle_signature` off the computer.
