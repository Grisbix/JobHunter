"""Trial of the installed application, on throwaway data (step F4, end criterion).

Run BY the compiled executable, with its embedded Python, after the CI's silent
installation, with no Python on the PATH:

    jobhunter-cli.exe -c "exec(open(r'outils/installateur/essai_installe.py', encoding='utf-8').read())"

`JOBHUNTER_RACINE` points to a throwaway data folder: never a user's.
Nothing goes out to the web: the browser opens a page written in memory, and the
collection merges a fictitious scan. Each step prints "ok"; the first that fails raises.

Steps: example profile → browser (Playwright's Chromium, otherwise the system's Chrome
or Edge, as on the user's machine) → merge of a scan into the queue → CV and letter of
an offer → update (the next installer downloaded, checked, ready to open).
"""

import hashlib
import json
import os
import shutil
from pathlib import Path

RACINE = Path(os.environ["JOBHUNTER_RACINE"])
SCRIPTS = RACINE / "Scripts"


def etape(nom: str) -> None:
    print(f"ok  {nom}", flush=True)


# 1. A configured profile: the example one, as after "first launch".
profil = RACINE / "profil" / "profil.json"
if not profil.exists():
    shutil.copy2(RACINE / "profil" / "exemple_finance_esg.json", profil)
etape("profil d'exemple en place")

# 2. The browser: embedded Playwright, the system's browser if Chromium is missing.
from playwright.sync_api import sync_playwright  # noqa: E402

from jobhunter.navigation.navigateur import lancer  # noqa: E402

with sync_playwright() as pw:
    nav = lancer(pw.chromium, headless=True)
    page = nav.new_page()
    page.set_content("<title>JobHunter</title><p>essai</p>")
    assert page.title() == "JobHunter", page.title()
    etape(f"navigateur {nav.version}")
    nav.close()

# 3. The collection, without network: a fictitious scan merged into the queue.
from jobhunter.cli import main as jobhunter  # noqa: E402

scan = [
    {
        "titre": "Analyste ESG",
        "url": "https://exemple.invalid/offres/analyste-esg",
        "entreprise": "Exemple Gestion",
        "domaine": "",
        "location": "Paris, France",
        "date": "2026-10-19",
        "source": "essai",
        "description": "Analyse ESG des émetteurs, notation extra-financière, SFDR, "
        "taxonomie verte, rapports d'impact pour les fonds article 9.",
        "scraped_at": "2026-10-19",
    }
]
(SCRIPTS / "offres_scan.json").write_text(json.dumps(scan, ensure_ascii=False), encoding="utf-8")
code = jobhunter(["collecte", "--fusion-seule"])
assert code == 0, f"fusion : code {code}"
from jobhunter.stockage import file as queue_io  # noqa: E402

file = queue_io.charger()
assert any(o.get("entreprise") == "Exemple Gestion" for o in file), "offre absente de la file"
etape(f"fusion dans la file ({len(file)} offre(s))")

# 4. The application folder: CV and letter for this offer.
code = jobhunter(["documents", "--url", "analyste-esg"])
assert code in (0, None), f"documents : code {code}"
docs = [p for p in RACINE.rglob("*.docx") if "Exemple" in p.name or "EXEMPLE" in p.name]
assert docs, "aucun CV ni lettre écrit"
etape(f"dossier : {', '.join(sorted(p.parent.name + '/' + p.name for p in docs))}")

# 5. The update of the installed application, simulated network: the next version
#    is the installer that was just built, with its published checksum.
from jobhunter.programmes import mise_a_jour as maj  # noqa: E402

setup = Path(os.environ["ESSAI_SETUP"]).read_bytes()
servis = {
    maj.ASSET_URL.format("99.0.0", maj.SETUP): setup,
    maj.ASSET_URL.format("99.0.0", maj.SETUP + ".sha256"): hashlib.sha256(setup)
    .hexdigest()
    .encode(),
}
lances: list[list[str]] = []
maj.nouvelle_version = lambda **kw: "99.0.0"  # type: ignore[assignment]
maj._get = lambda url, t: servis[url]  # type: ignore[assignment]
maj.subprocess.Popen = lambda args, **kw: lances.append(args)  # type: ignore[assignment,misc,return-value]
assert maj.maj_application(False) == 0
assert len(lances) == 1 and Path(lances[0][0]).read_bytes() == setup
Path(os.environ["ESSAI_SORTIE"]).write_text(lances[0][0], encoding="utf-8")
etape(f"mise à jour : installateur contrôlé, prêt à s'ouvrir ({lances[0][0]})")
