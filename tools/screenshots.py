"""The README and Store screenshots, on a fictitious profile and fictitious offers.

    uv run python tools/screenshots.py [--lang en] [--out docs/screenshots]
    # the Store's French set: --lang fr --out docs/store/screenshots_fr

Builds a throwaway data folder (the example profile, "Camille Exemple", and eight
invented companies), prepares the CV and letter of the best offer with the real
engine (`jobhunter documents`, LibreOffice for the PDF), then captures the web
interface — the application's window since 3.27, and what the Microsoft Store shows:
`web_home.png`, `web_offers.png`, `web_applications.png` in light mode and
`web_offers_dark.png` in dark mode. The page runs in Playwright's Chromium, its calls
answered by the real `jobhunter.web.api.Api` on the same fictitious folder: no window
opens, nothing of the screen behind is captured.

Nothing of the user's own data is read: the folder is created in a temporary
directory and `JOBHUNTER_RACINE` points to it.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from jobhunter.programs import sandbox

REPO = Path(__file__).resolve().parent.parent

_SCORER = sandbox.SCORER


def python(racine: Path, *args: str) -> None:
    env = {**os.environ, "JOBHUNTER_RACINE": str(racine), "PYTHONIOENCODING": "utf-8"}
    env.pop("JOBHUNTER_PRINCIPALE", None)
    subprocess.run([sys.executable, *args], env=env, cwd=racine, check=True)  # nosec B603


def jobhunter(racine: Path, *args: str) -> None:
    env = {**os.environ, "JOBHUNTER_RACINE": str(racine), "PYTHONIOENCODING": "utf-8"}
    env.pop("JOBHUNTER_PRINCIPALE", None)
    subprocess.run(  # nosec B603 : our own program
        [sys.executable, "-m", "jobhunter", *args], env=env, cwd=racine, check=True
    )


# Stands in for pywebview: window.pywebview.api.<name>(...) goes to the Python Api.
_PONT = """
window.pywebview = { api: new Proxy({}, { get: (_, nom) => (...args) => window.__jh(nom, args) }) };
"""


# (file, light or dark mode, screen) of the web interface's screenshots.
ECRANS_WEB = (
    ("web_home.png", "clair", "accueil"),
    ("web_offers_dark.png", "sombre", "offres"),
    ("web_offers.png", "clair", "offres"),
    ("web_applications.png", "clair", "candidatures"),
)


def capturer_web(racine: Path, sortie: Path, langue: str = "en") -> None:
    """The web interface's screenshots, rendered headless (see the module's doc)."""
    os.environ.update(JOBHUNTER_RACINE=str(racine), JOBHUNTER_LANGUE=langue)
    os.environ.pop("JOBHUNTER_PRINCIPALE", None)
    from playwright.sync_api import sync_playwright

    from jobhunter.web.__main__ import STATIC
    from jobhunter.web.api import Api

    api = Api()

    def pont(nom: str, args: list) -> object:
        # JSON round trip: what pywebview would hand the page.
        return json.loads(json.dumps(getattr(api, nom)(*args), default=str))

    with sync_playwright() as p:
        nav = p.chromium.launch()
        page = nav.new_page(viewport={"width": 1440, "height": 900})
        page.expose_function("__jh", pont)
        page.add_init_script(_PONT)
        page.goto((STATIC / "index.html").as_uri())
        page.wait_for_timeout(1500)
        # No see-through window here: the page paints its own background.
        page.evaluate("document.body.classList.remove('natif')")

        def photo(nom: str, mode: str, ecran: str) -> None:
            page.evaluate(
                f"(async () => {{ modeAffiche = '{mode}'; appliquerMode();"
                f" await aller('{ecran}'); }})()"
            )
            page.wait_for_timeout(1200)
            page.evaluate("window.scrollTo(0, 0)")  # a focused field may scroll it
            page.screenshot(path=str(sortie / nom))
            print("  ", sortie / nom)

        for nom, mode, ecran in ECRANS_WEB:
            photo(nom, mode, ecran)
        nav.close()


def main() -> int:
    a = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    a.add_argument("--lang", default="en", help="interface language: en, fr, de, es")
    a.add_argument("--out", default=str(REPO / "docs" / "screenshots"))
    a.add_argument("--garder", action="store_true", help="keep the fictitious folder")
    args = a.parse_args()
    sortie = Path(args.out).resolve()
    sortie.mkdir(parents=True, exist_ok=True)
    racine = Path(tempfile.mkdtemp(prefix="jobhunter_captures_"))
    try:
        sandbox.preparer(racine)
        sandbox.gabarit_cv(racine)
        python(racine, "-c", _SCORER)
        jobhunter(racine, "documents", "--top", "1")
        jobhunter(racine, "reposts")  # the Signal column: knock-outs
        jobhunter(racine, "postings")  # the posting kept for the application
        capturer_web(racine, sortie, args.lang)
    finally:
        if args.garder:
            print("dossier fictif :", racine)
        else:
            shutil.rmtree(racine, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
