"""`jobhunter sandbox`: the whole application on fictitious data, cut off from the web.

The user, 2026-11-06: « une version test pour pouvoir tester réellement toute l'app sans
qu'elle soit live ». This opens the real window (the installed one, or this checkout's)
on a throwaway folder: the example profile (« Camille Exemple »), eight invented offers
and one application. Nothing of the user's own folder is read or written:
`JOBHUNTER_RACINE` points to the sandbox and the main profile is forgotten.

What stays out of reach, so a click in the sandbox cannot touch the real installation:
- the web: every HTTP client of the programs (httpx, urllib) goes through a proxy that
  answers nothing, the local addresses excepted — a collection finds nothing, a check
  for updates says « injoignable » (`--reseau` lifts it);
- the background loop (`JOBHUNTER_SANS_FOND`), the scheduled morning collection, the
  Start menu shortcut, « Désinstaller JobHunter » and « Effacer mes données ».

    jobhunter sandbox              # opens it; the folder is kept for the next time
    jobhunter sandbox --neuf       # starts again from the fictitious data
    jobhunter sandbox --reseau     # with the web (a real collection, on the example profile)

`tools/screenshots.py` builds its folder from the same data.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess  # nosec B404 : our own programs
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

ENV = "JOBHUNTER_BAC_A_SABLE"
EXEMPLE = Path(__file__).resolve().parent.parent / "assets" / "example_profile.json"
# A port nothing listens on: a request through it fails at once, instead of a timeout.
PROXY_MORT = "http://127.0.0.1:9"


def actif() -> bool:
    """Does this process run in the sandbox (`jobhunter sandbox`)?"""
    return bool(os.environ.get(ENV))


def dossier_defaut() -> Path:
    return Path(tempfile.gettempdir()) / "JobHunter_bac_a_sable"


_DESC = (
    "{poste} at {entreprise}. You will join the sustainability team and work on ESG "
    "analysis of portfolios, CSRD and SFDR reporting, climate risk and carbon footprint "
    "of investments, taxonomy alignment, and engagement with companies. You will build "
    "ESG data dashboards in Excel and Python and present them to investment committees. "
    "Master's degree in finance or sustainability; first experience in responsible "
    "investment appreciated. Fluent English and French."
)

# Offers that match the example profile less and less: a realistic spread of fits.
DESCRIPTIONS = {
    "Climate Risk Analyst": (
        "Climate Risk Analyst. Model physical and transition climate risks for the bank's "
        "credit portfolio, stress tests, scenario analysis, risk reporting to the risk "
        "committee. Python, SQL. Master's degree in finance or engineering."
    ),
    "ESG Data Analyst": (
        "ESG Data Analyst. Collect and clean ESG data from providers, build dashboards in "
        "Power BI, automate data pipelines in Python and SQL, support the sustainability team."
    ),
    "Responsible Investment Associate": (
        "Responsible Investment Associate. Support portfolio managers in asset management: "
        "investment analysis, financial modelling, company meetings, some ESG integration."
    ),
    "Impact Investment Analyst": (
        "Impact Investment Analyst. Due diligence of private equity deals, financial "
        "modelling, impact measurement. 3+ years of experience in investment banking. "
        "You must have the right to work in the UK."
    ),
    "Marketing Assistant": "Marketing assistant for a retail brand: social media and events.",
}

# entreprise, poste, lieu, contrat, salaire
OFFRES = [
    ("Atelier Nova", "ESG Analyst", "Bordeaux", "CDI", "42-48k EUR"),
    ("Studio Lumen", "Sustainable Finance Analyst", "Paris", "CDI", ""),
    ("Fondation Horizon", "Climate Risk Analyst", "Paris", "CDD", ""),
    ("Maison Verte", "CSRD Reporting Officer", "Bordeaux", "CDI", ""),
    ("Groupe Orion", "Responsible Investment Associate", "Lyon", "CDI", "45k EUR"),
    ("Brightside Capital", "Impact Investment Analyst", "London", "CDI", ""),
    ("Kanaal Partners", "ESG Data Analyst", "Amsterdam", "CDI", ""),
    ("Northwind Retail", "Marketing Assistant", "Paris", "CDI", ""),
]

SCORER = """
from jobhunter.scoring.fit import fit_detail
from jobhunter.storage import queue as queue_io
with queue_io.transaction() as q:
    for o in q:
        o["fit"], o["exp_requise"], o["fit_fin"] = fit_detail(
            f"{o['poste']} {o['description']}", o["poste"]
        )
"""


def _il_y_a(jours: int) -> str:
    """The date `jours` days ago, as the applications write it (YYYY-MM-DD)."""
    import datetime

    return (datetime.date.today() - datetime.timedelta(days=jours)).isoformat()


def preparer(racine: Path) -> None:
    """The fictitious data folder, in the 3.0 layout."""
    jour = time.strftime("%Y-%m-%d")
    for d in ("data", "profile", "My_CV", "CV", "Letters"):
        (racine / d).mkdir(parents=True, exist_ok=True)
    profil = json.loads(EXEMPLE.read_text("utf-8"))
    for lg in ("fr", "en"):
        if lg not in profil.setdefault("langues_parlees", []):
            profil["langues_parlees"].append(lg)
    (racine / "profile" / "profile.json").write_text(
        json.dumps(profil, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    lignes: list[dict[str, Any]] = []
    for i, (entreprise, poste, lieu, contrat, salaire) in enumerate(OFFRES):
        desc = DESCRIPTIONS.get(poste) or _DESC.format(poste=poste, entreprise=entreprise)
        lignes.append(
            {
                "entreprise": entreprise,
                "poste": poste,
                "domaine": "esg",
                "statut": f"Scan {jour}",
                "url": f"https://jobs.example.com/{i}",
                "contrat": contrat,
                "localisation": lieu,
                "salaire": salaire,
                "source": "greenhouse:example",
                "canal": "auto",
                "site_kind": "entreprise",
                "description": desc,
                "process": jour,
                "vu_le": jour,
                "ls_check": jour,
                "date_publication": "2026-10-08",
            }
        )
    # What 3.3 adds to the card: every search that found the offer, and what its site
    # changed since.
    lignes[0]["vus_sur"] = [
        "greenhouse:example",
        "linkedin-search:esg analyst",
        "welcometothejungle:finance durable",
    ]
    lignes[0]["changements"] = [
        {"date": jour, "champ": "salaire", "avant": "40-45k EUR", "apres": "42-48k EUR"}
    ]
    (racine / "data" / "apply_queue.json").write_text(
        json.dumps(lignes, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    # 3.15: an application with its history, and its posting kept (jobhunter postings).
    suivi = {
        "Atelier Nova|ESG Analyst": {
            "s": "entretien",
            "d": jour,
            "h": [["2026-10-01", "postulé"], [jour, "entretien"]],
        },
        # 3.87: one application per column, so the board, the follow-ups and the
        # statistics show something (one card alone looked like an empty application)
        "Groupe Orion|Responsible Investment Associate": {
            "s": "postulé",
            "d": _il_y_a(12),
            "h": [[_il_y_a(12), "postulé"]],
        },
        "Maison Verte|CSRD Reporting Officer": {
            "s": "relancé",
            "d": _il_y_a(6),
            "h": [[_il_y_a(27), "postulé"], [_il_y_a(6), "relancé"]],
        },
        "Kanaal Partners|ESG Data Analyst": {
            "s": "refus",
            "d": _il_y_a(4),
            "h": [[_il_y_a(18), "postulé"], [_il_y_a(4), "refus"]],
        },
    }
    (racine / "data" / "applications.json").write_text(
        json.dumps(suivi, ensure_ascii=False, indent=1), encoding="utf-8"
    )


def gabarit_cv(racine: Path) -> None:
    """A one-page base CV for the profile's first field (python-docx), fictitious."""
    import docx

    profil = json.loads((racine / "profile" / "profile.json").read_text("utf-8"))
    nom = profil["domaines"][0]["cv"]
    d = docx.Document()
    d.add_heading("Camille Exemple", 0)
    d.add_paragraph("camille.exemple@example.com · +33 6 00 00 00 00 · Bordeaux")
    d.add_heading("Experience", 1)
    d.add_paragraph("Acme Finance — ESG analyst intern (6 months): SFDR classification of funds.")
    d.add_heading("Education", 1)
    d.add_paragraph("Master in Finance, specialisation in sustainable finance.")
    d.add_heading("Skills", 1)
    d.add_paragraph("ESG analysis · CSRD · SFDR · carbon footprint · Excel · Python · SQL")
    (racine / "CV" / "Templates").mkdir(parents=True, exist_ok=True)
    d.save(str(racine / "CV" / "Templates" / nom))


def environnement(racine: Path, reseau: bool = False) -> dict[str, str]:
    """The environment of a program run in the sandbox: its folder, nothing of the user's."""
    env = {**os.environ, "JOBHUNTER_RACINE": str(racine), ENV: "1", "JOBHUNTER_SANS_FOND": "1"}
    env["PYTHONIOENCODING"] = "utf-8"
    env.pop("JOBHUNTER_PRINCIPALE", None)  # else the user's main profile is still read
    if not reseau:
        for nom in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy"):
            env[nom] = PROXY_MORT
        env["NO_PROXY"] = env["no_proxy"] = "localhost,127.0.0.1,::1"
    return env


def _lancer(racine: Path, env: dict[str, str], *args: str, verifier: bool = True) -> int:
    from jobhunter import frozen

    return subprocess.run(  # nosec B603 : our own programs
        [frozen.interpreteur(), *args], env=env, cwd=racine, check=verifier
    ).returncode


def construire(racine: Path) -> None:
    """Writes the fictitious folder, scores its offers, prepares the best one's documents."""
    preparer(racine)
    gabarit_cv(racine)
    env = environnement(racine)
    _lancer(racine, env, "-c", SCORER)
    # The CV and letter of the best offer: their PDF needs LibreOffice, which may be
    # missing; the sandbox opens without them.
    if _lancer(racine, env, "-m", "jobhunter", "documents", "--top", "1", verifier=False):
        print("(CV et lettre de démonstration non préparés : la suite marche sans)")


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    a = argparse.ArgumentParser(
        prog="jobhunter sandbox",
        description="L'application entière sur des données fictives, coupée du web.",
    )
    a.add_argument("--dossier", type=Path, default=None, help="dossier du bac à sable")
    a.add_argument("--neuf", action="store_true", help="repartir des données fictives")
    a.add_argument("--reseau", action="store_true", help="laisser l'accès au web")
    args = a.parse_args(argv)
    racine = (args.dossier or dossier_defaut()).resolve()
    if args.neuf and racine.exists():
        if not (racine / "profile" / "profile.json").exists():
            sys.exit(f"{racine} n'est pas un bac à sable : rien effacé")
        shutil.rmtree(racine)
    if not (racine / "profile" / "profile.json").exists():
        print(f"Bac à sable : préparation de {racine}…", flush=True)
        construire(racine)
    print(
        f"Bac à sable : {racine}\n"
        + ("Web : ouvert (--reseau)." if args.reseau else "Web : coupé.")
        + " Tes données ne sont ni lues ni modifiées. Ferme la fenêtre pour finir.",
        flush=True,
    )
    return _lancer(
        racine, environnement(racine, args.reseau), "-m", "jobhunter", "app", verifier=False
    )


if __name__ == "__main__":
    sys.exit(main())
