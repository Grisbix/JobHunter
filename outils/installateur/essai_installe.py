"""Essai de l'application installée, sur des données jetables (étape F4, critère de fin).

Lancé PAR l'exécutable compilé, avec son Python embarqué, après l'installation
silencieuse de la CI, sans Python sur le PATH :

    jobhunter-cli.exe -c "exec(open(r'outils/installateur/essai_installe.py', encoding='utf-8').read())"

`JOBHUNTER_RACINE` désigne un dossier de données jetable : jamais celui d'un utilisateur.
Rien ne sort sur le web : le navigateur ouvre une page écrite en mémoire, et la collecte
fusionne un scan fictif. Chaque étape affiche « ok » ; la première qui échoue lève.

Étapes : profil d'exemple → navigateur (Chromium de Playwright, sinon Chrome ou Edge du
système, comme chez l'utilisateur) → fusion d'un scan dans la file → CV et lettre d'une
offre → mise à jour (l'installateur suivant téléchargé, contrôlé, prêt à s'ouvrir).
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


# 1. Un profil configuré : celui d'exemple, comme après « premier lancement ».
profil = RACINE / "profil" / "profil.json"
if not profil.exists():
    shutil.copy2(RACINE / "profil" / "exemple_finance_esg.json", profil)
etape("profil d'exemple en place")

# 2. Le navigateur : Playwright embarqué, navigateur du système si Chromium manque.
from playwright.sync_api import sync_playwright  # noqa: E402

from jobhunter.navigation.navigateur import lancer  # noqa: E402

with sync_playwright() as pw:
    nav = lancer(pw.chromium, headless=True)
    page = nav.new_page()
    page.set_content("<title>JobHunter</title><p>essai</p>")
    assert page.title() == "JobHunter", page.title()
    etape(f"navigateur {nav.version}")
    nav.close()

# 3. La collecte, sans réseau : un scan fictif fusionné dans la file.
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

# 4. Le dossier de candidature : CV et lettre de cette offre.
code = jobhunter(["documents", "--url", "analyste-esg"])
assert code in (0, None), f"documents : code {code}"
docs = [p for p in RACINE.rglob("*.docx") if "Exemple" in p.name or "EXEMPLE" in p.name]
assert docs, "aucun CV ni lettre écrit"
etape(f"dossier : {', '.join(sorted(p.parent.name + '/' + p.name for p in docs))}")

# 5. La mise à jour de l'application installée, réseau simulé : la version suivante
#    est l'installateur qui vient d'être construit, avec son empreinte publiée.
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
