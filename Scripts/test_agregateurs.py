#!/usr/bin/env python3
"""test_agregateurs.py — sources Adzuna et Jooble, sans reseau.

Couvre : desactivation sans fichier de cle ; lecture des resultats ; filtres
(titre, stage) ; desc_partielle ; arret au 3e refus d'entree ; pause sur 429 ;
et surtout : LA CLE N'APPARAIT JAMAIS dans la sortie, meme sur une exception
dont le message contient l'URL.

Run : python test_agregateurs.py
"""

import _profil_test  # noqa: F401  — les tests tournent sur le profil d'exemple

import io
import json
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.argv = ["x"]
import job_sources as js

ok = ko = 0


def ck(nom, cond):
    global ok, ko
    if cond:
        ok += 1
        print(f"✅ {nom}")
    else:
        ko += 1
        print(f"❌ {nom}")


CLE = "CLE-SECRETE-123"
dormi = []
js.time.sleep = lambda s: dormi.append(s)


class R:
    def __init__(self, code, data=None):
        self.status_code, self._d = code, data or {}

    def json(self):
        return self._d


def rejouer(reponses):
    """Remplace les deux appels bornes par une file de reponses (ou d'exceptions)."""
    it = iter(reponses)
    vus = []

    def appel(envoi, url, **kw):
        vus.append((url, kw))
        x = next(it, R(200, {}))
        if isinstance(x, Exception):
            raise x
        return x

    js._get_borne = appel
    js._post_borne = appel
    return vus


def capture(f):
    buf = io.StringIO()
    with redirect_stdout(buf):
        res = f()
    return res, buf.getvalue()


tmp = Path(tempfile.mkdtemp())
js.ADZUNA_CFG = tmp / "adzuna.json"
js.JOOBLE_CFG = tmp / "jooble.json"

# ── 1. sans cle : la source se tait et le dit ────────────────────────────────
res, sortie = capture(js.scan_adzuna)
ck("Adzuna sans cle : aucune offre", res == [])
ck("Adzuna sans cle : le dit", "adzuna.json absent" in sortie)
res, sortie = capture(js.scan_jooble)
ck("Jooble sans cle : aucune offre", res == [] and "jooble.json absent" in sortie)

js.ADZUNA_CFG.write_text(json.dumps({"app_id": "ID", "app_key": CLE}), encoding="utf-8")
js.JOOBLE_CFG.write_text(json.dumps({"key": CLE}), encoding="utf-8")

# ── 2. Adzuna : lecture et filtres ───────────────────────────────────────────
page = {
    "results": [
        {
            "title": "ESG Analyst",
            "redirect_url": "https://www.adzuna.fr/land/ad/1",
            "company": {"display_name": "Mirova"},
            "location": {"display_name": "Paris"},
            "created": "2026-10-01T08:00:00Z",
            "description": "<b>SFDR</b> reporting",
            "contract_type": "permanent",
        },
        {
            "title": "Stage analyste ESG",
            "redirect_url": "https://www.adzuna.fr/land/ad/2",
            "company": {"display_name": "X"},
            "location": {},
        },
        {
            "title": "Chauffeur livreur",
            "redirect_url": "https://www.adzuna.fr/land/ad/3",
            "company": {"display_name": "Y"},
            "location": {},
        },
    ]
}
appels = rejouer([R(200, page)])
res, sortie = capture(js.scan_adzuna)
ck("Adzuna : offre ESG lue", len(res) == 1 and res[0]["titre"] == "ESG Analyst")
ck("Adzuna : stage ecarte, hors metier ecarte", len(res) == 1)
ck("Adzuna : contrat permanent -> CDI", res and res[0].get("contrat") == "CDI")
ck(
    "Adzuna : extrait marque partiel, HTML retire",
    res and res[0].get("desc_partielle") and "<b>" not in res[0]["description"],
)
ck("Adzuna : date courte", res and res[0]["date"] == "2026-10-01")
ck(
    "Adzuna : France puis 7 pays",
    len(appels) == len(js.AGREG_MOTS_FR) + len(js.ADZUNA_PAYS) * len(js.AGREG_MOTS_EN),
)
ck("Adzuna : la cle part en parametre, pas dans la sortie", CLE not in sortie)

# ── 3. refus d'entree : arret au 3e ──────────────────────────────────────────
appels = rejouer([R(403)] * 20)
res, sortie = capture(js.scan_adzuna)
ck("Adzuna 403 : arret apres 3 requetes", len(appels) == js.AGREG_ABANDON)
ck("Adzuna 403 : le dit", "refus d'affilee" in sortie)

# ── 4. limite de debit : pause, reprise, puis abandon ────────────────────────
dormi.clear()
appels = rejouer([R(429), R(200, page)] + [R(429)] * 5)
res, sortie = capture(js.scan_adzuna)
ck("Adzuna 429 : pause de 60 s", js.AGREG_REPOS_429 in dormi)
ck("Adzuna 429 : reprise apres la pause", len(res) == 1)
ck("Adzuna 429 persistant : arret de la source", "limite de debit persistante" in sortie)

# ── 5. la cle ne fuit jamais, meme dans une exception ────────────────────────
appels = rejouer([RuntimeError(f"echec sur https://api.adzuna.com/?app_key={CLE}")] * 80)
res, sortie = capture(js.scan_adzuna)
ck("exception contenant l'URL : cle absente de la sortie", CLE not in sortie)
ck(
    "exception : comptee dans INCIDENTS par son type",
    js.INCIDENTS["adzuna"].get("RuntimeError", 0) > 0,
)

# ── 6. Jooble ────────────────────────────────────────────────────────────────
pj = {
    "jobs": [
        {
            "title": "Analyste crédit junior",
            "link": "https://jooble.org/desc/9",
            "company": "BNP",
            "location": "Paris",
            "snippet": "crédit corporate",
            "type": "CDI",
            "updated": "2026-09-30T00:00:00",
        }
    ]
}
appels = rejouer([R(200, pj)])
res, sortie = capture(js.scan_jooble)
ck("Jooble : offre lue", len(res) == 1 and res[0]["entreprise"] == "BNP")
ck("Jooble : type CDI repris", res and res[0].get("contrat") == "CDI")
ck(
    "Jooble : POST avec mots-cles et France",
    appels and appels[0][1].get("json", {}).get("location") == "France",
)
ck("Jooble : cle absente de la sortie", CLE not in sortie)

print(f"\n=== BILAN : {ok} ✅  /  {ko} ❌  ({ok}/{ok + ko}) ===")
sys.exit(1 if ko else 0)
