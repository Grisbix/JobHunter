"""Application constants: paths, statuses, table columns, steps and maintenance.

Part of jobhunter.app (former JobHunter.pyw, phase 3.7)."""

import functools as _ft
import os
import re
import subprocess
import sys
from typing import Any

import customtkinter as ctk

from jobhunter import chemins as chemins
from jobhunter import gele as _gele
from jobhunter import paresseux as _paresseux
from jobhunter import profil as _profil
from jobhunter import racine as _racine
from jobhunter.app import theme as _theme
from jobhunter.app.langue import t as _t


def ouvrir(chemin: object) -> bool:
    """Opens a file or a folder with the system's application.

    `os.startfile` only exists on Windows: elsewhere, calling it raised
    AttributeError. Returns True, to chain in a Tk lambda
    (`lambda: p and ouvrir(p)`).
    """
    if sys.platform == "win32":
        os.startfile(str(chemin))
    else:
        subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", str(chemin)])
    return True


from jobhunter.app.theme import (
    ACC,
    AMBRE,
    BAD,
    BTN,
    BTN_H,
    CARD,
    MUT,
    OK,
    PURP,
    RAD_BTN,
    TEAL,
    TX,
    TX_ACC,
    TX_AMBRE,
    TX_BAD,
    WORK,
)
from jobhunter.scoring import zones as _zones

_ici = sys.modules[__name__]
# Values taken from the profile: computed on first read, not at import
# (jobhunter.paresseux). In this module, they are read through `_ici.NAME`.
_PARESSEUX: _paresseux.Fabriques = {}


def __getattr__(nom: str) -> Any:
    return _paresseux.lire(_ici, _PARESSEUX, nom)


ROOT = _racine.racine()  # marker or JOBHUNTER_RACINE (jobhunter.racine)


SCRIPTS = ROOT / "Scripts"


# Runs the programs as subprocesses: python.exe under Python, jobhunter-cli.exe
# in the installed application (jobhunter.gele).
PY = _gele.interpreteur()


QUEUE = SCRIPTS / "apply_queue.json"


SUIVI = SCRIPTS / "suivi.json"


COMPTES = SCRIPTS / "comptes_sites.json"


PROFILE = SCRIPTS / "apply_profile.json"


CV_ATS_DIR = chemins.CV_MODELES  # 5 CV variants (source, in the repository)


_PARESSEUX["CV_OFFRE_DIR"] = lambda: chemins.CV_PAR_OFFRE  # CVs tailored per offer


_PARESSEUX["LETTRES_DIR"] = lambda: chemins.LT_PAR_OFFRE  # lettres de motivation (docx+pdf)


_PARESSEUX["_PREFIXE"] = lambda: _profil.prefixe_fichier()


# Displayed country and place, memoised per location string: the table recomputes
# them at each refresh, over 7000 rows and a few hundred places.
_pays_lieu = _ft.lru_cache(maxsize=None)(_zones.pays_lieu)


_ville_affichee = _ft.lru_cache(maxsize=None)(_zones.ville_affichee)


_region_lieu = _ft.lru_cache(maxsize=None)(lambda l: _zones.region_pays(_pays_lieu(l)))


# tracking statuses (readable labels stored in suivi.json + SUIVI Excel sheet)
# "mauvaise" = the offer is worth nothing FOR ME (badly scored, off topic, disguised
# senior). To be told apart from "refus", which is the EMPLOYER's answer after
# applying: mixing the two would distort the response rate of the Stats
# panel, where "refus" counts closed doors, not offers set aside.
#
# "pas intéressé" = neither a verdict on the offer's quality nor an answer:
# the user does not want it, full stop. The offer stays in the queue (the scan that
# finds it again tomorrow lands on the same tracking key, so it stays hidden)
# but disappears from the table. Reversible in one click, unlike
# "Écarter", which removes it from the queue and requires a reason.
PAS_INTERESSE = "pas intéressé"


# "expiré" = the posting is closed (seen too late, or withdrawn by the employer).
# Neither a judgement on the offer ("mauvaise") nor an answer ("refus"): a fact.
# Hidden like "pas intéressé" — nothing to do on a closed offer — and kept
# in the tracking so that the scan that would find it again does not bring it back.
# Added on 2026-10-04: the user wrote "mauvaise" + "trop tard" for lack of anything better.
EXPIRE = "expiré"


MASQUANTS = (PAS_INTERESSE, EXPIRE)


STATUTS = [
    "",
    "à postuler",
    "à vérifier",
    "postulé",
    "relancé",
    "entretien",
    "refus",
    "mauvaise",
    EXPIRE,
    PAS_INTERESSE,
]


# MONOCHROME markers: they inherit the row's colour, where
# a colour emoji imposed its own and broke the reading of the table.
ST_EMOJI = {statut: "" for statut in STATUTS}  # labels only, no decorative pictograms


# Row colour by status: the eye finds the applications in
# progress without reading the column. Set AFTER the link state (the last tag wins).
ST_COULEUR = {
    "à postuler": ACC,
    "à vérifier": AMBRE,
    "postulé": OK,
    "relancé": TEAL,
    "entretien": PURP,
    "refus": BAD,
    "mauvaise": MUT,
    EXPIRE: MUT,
    PAS_INTERESSE: MUT,
}


# Coloured labels IN the table: text versions, otherwise unreadable.
# Only PROBLEM links are coloured. "OK" was too, in green: 98%
# of the rows, the whole table turns green and nothing stands out any more.
LS_COLOR = {
    "MORT": TX_BAD,
    "EXPIREE": TX_AMBRE,
    "FERMEE": TX_BAD,
    "HOMEPAGE": TX_ACC,
    "ANTI-BOT": MUT,
}


# ESSENTIALS: visible straight away. The rest (maintenance) under "🔧 Maintenance ▾".
STEPS = [
    (
        "Scan offres",
        "#2563eb",
        [PY, "-m", "jobhunter.sources", "--all"],
        "NOUVELLES offres : APIs ATS (greenhouse/lever/ashby…) + LinkedIn public + WTJ → merge queue (dédup)",
    ),
    (
        "Candidatures en lot",
        "#dc2626",
        [PY, "-m", "jobhunter.programmes.apply_runner", "--canal", "auto", "--auto", "--fast"],
        "Remplit+upload chaque offre, tu tapes juste Entrée = envoyé+suivant (console)",
    ),
    (
        "LinkedIn",
        "#0a66c2",
        [
            PY,
            "-m",
            "jobhunter.programmes.apply_runner",
            "--canal",
            "linkedin",
            "--chrome",
            "--auto",
        ],
        "Easy Apply semi-auto : réutilise ta session (connecte-toi 1 fois), remplit, STOP sur Envoyer (tu cliques)",
    ),
]


# 19 items stacked flat cannot be read. Grouped by INTENT: one
# looks for "where are my offers going", not a script name.
MAINT: list[tuple[str, list[tuple[str, Any]]]] = [
    (
        "Sources & offres",
        [
            ("Scrape les sites", [PY, "-m", "jobhunter.programmes.scrape_jobs", "--headless"]),
            ("Homepages", [PY, "-m", "jobhunter.programmes.enrich_homepages"]),
            # The daily scan only sees 7 days (LinkedIn f_TPR filter). An
            # offer published at the start of the month and missed at the time stays
            # invisible without this wider pass.
            ("Rattrapage 31 j", [PY, "-m", "jobhunter.sources", "--all", "--days", "31"]),
            ("Sonder flux ATS", [PY, "-m", "jobhunter.programmes.probe_ats"]),
            ("Sonder flux Workday", [PY, "-m", "jobhunter.programmes.probe_workday"]),
            (
                "Sonder mots-clés",
                [PY, "-m", "jobhunter.programmes.probe_keywords", "--days", "30", "--min-new", "3"],
            ),
        ],
    ),
    (
        "Documents",
        [
            ("CV/lettres…", None),  # None = command built on the fly
            ("Sync docs+format", [PY, "-m", "jobhunter.programmes.sync_docs", "--format"]),
            ("Export CSV", [PY, "-m", "jobhunter.programmes.export_queue_csv", "--keep", "8"]),
            ("Relire les lettres", [PY, "-m", "jobhunter.programmes.relecture"]),
            ("Contrôler les dossiers", [PY, "-m", "jobhunter.programmes.controle_dossiers"]),
        ],
    ),
    (
        "Hygiène de la file",
        [
            ("URLs mortes", [PY, "-m", "jobhunter.programmes.queue_tools", "mark"]),
            (
                "Recheck 404",
                [PY, "-m", "jobhunter.programmes.recheck_dead", "--status", "OK", "--limit", "120"],
            ),
            ("Re-score", [PY, "-m", "jobhunter.programmes.rescore_ats"]),
        ],
    ),
    (
        "Suivi",
        [
            ("Relances", [PY, "-m", "jobhunter.programmes.relances"]),
            ("Alerte matchs", [PY, "-m", "jobhunter.programmes.notify_matches", "--min-fit", "8"]),
        ],
    ),
    (
        "Accès & diagnostic",
        [
            # Masked entry of the API secret: it goes neither through the chat nor through
            # l'historique shell. Console reelle obligatoire (getpass lit stdin).
            ("Clés France Travail", [PY, "-m", "jobhunter.programmes.setup_francetravail"]),
            ("Fermer Chrome", [PY, "-m", "jobhunter.programmes.acces", "--close"]),
            (
                "Tester accès aux sites",
                [PY, "-m", "jobhunter.programmes.test_acces_sites", "--all", "--limit", "0"],
            ),
            (
                "Tests live (lent, ouvre un navigateur)",
                [PY, "-m", "jobhunter.programmes.test_live_nav"],
            ),
            ("Mettre à jour JobHunter", "maj"),  # "maj" = mise a jour + relance (App.mettre_a_jour)
            ("Collecte chaque matin…", "planifier"),  # Windows task (App._planifier)
            ("Statuts depuis mes courriels…", "courriels"),  # read-only (app.courriels)
            ("Langue / Language…", "langue"),  # chooses the interface language (app.langue)
        ],
    ),
]


# interactive scripts (input()) -> run in a REAL console, not a piped subprocess
INTERACTIVE = (
    "jobhunter.programmes.apply_runner",
    "jobhunter.programmes.setup_francetravail",
    "jobhunter.programmes.acces",
)


SCRAPE_TAG = "\U0001f50e"  # magnifier, prefix of the automatic scan's logs


LF = "\n"


# (offer key, header, width). Numeric column (numeric sort): fit.
# widths enlarged for the bigger font (otherwise text truncated / "🆕 nouveau" status clipped)
COLS = [
    ("_chk", "☐", 40),
    ("_st", "Statut", 140),
    ("entreprise", "Entreprise", 190),
    ("poste", "Poste", 330),
    ("domaine", "Domaine", 90),
    ("fit", "Fit", 50),
    ("contrat", "Contrat", 80),
    ("zone", "Zone", 125),
    ("localisation", "Lieu", 170),
    ("pays", "Pays", 100),
    ("region", "Région", 120),
    ("process", "Date offre", 115),
    ("_url", "Lien", 175),
    ("_date", "Suivi", 100),
]


# Zones: the alphabetical sort of the column must follow the PREFERENCE, not
# the alphabet. The leading digit is enough, and reads just as well by eye.
# "prioritaire" groups the profile's priority sectors: the label
# names the offer's sector (sous_zone), otherwise they all carried the first one.
ZONE_ETIQ = {
    "prioritaire": "1 · prioritaire",
    "secondaire": "2 · secondaire",
    "inconnu": "3 · non précisé",
    "ailleurs": "4 · ailleurs",
    "international": "5 · étranger",
}


# Last URL segment that designates a SECTION, hence a list of jobs,
# and never a specific job.
# Same patterns as job_sources: offers ALREADY in the queue often carry
# "CDI" when their title says "Alternance" — LinkedIn gets it wrong.
_RX_ALT = re.compile(r"\b(alternan[ct]|apprenti|apprentissage|contrat\s+pro)", re.I)


_RX_STAGE = re.compile(r"\b(stage|stagiaire|internship|intern)\b", re.I)


_RUBRIQUES = {
    "careers",
    "career",
    "carrieres",
    "carrières",
    "recrutement",
    "recruitment",
    "jobs",
    "job",
    "offres",
    "emplois",
    "emploi",
    "vacancies",
    "opportunities",
    "nous-rejoindre",
    "join-us",
}


# Parameters that designate a SEARCH, not an offer: ?query=…, ?q=…,
# ?keywords=…. An offer link carries an identifier, not keywords.
_RX_RECHERCHE_Q = re.compile(r"(^|&)(query|q|k|keywords?|search|recherche)=", re.I)


DEFAULT_ST = ""  # nothing displayed as long as there is no manual status (no "🆕 nouveau")


# Placeholder of the search field. A constant, not a repeated literal: the text
# ALSO serves as a sentinel ("is the field empty?"), and two copies that
# differ by one space would search for the placeholder itself.
# Placeholders of the two entry fields, in the interface language: the code compares
# the field's content with them, so they are translated once, here.
SEARCH_HINT = _t("rechercher…")
URL_HINT = _t("coller un lien d'offre…")


DOM_SHORT = {
    "ESG / Finance Durable": "ESG",
    "Data / IA / Climate Tech": "Data/IA",
    "Finance / Investissement": "Finance",
    "Conseil / Strategy": "Conseil",
    "Risk / Quant / Assurance": "Risk",
    # current labels of classify_domaine; the previous ones stay for
    # older offers. Without them the column displayed "ESG_Finan".
    "ESG_Finance_Durable": "ESG",
    "Data_IA": "Data/IA",
    "Risk_Quant": "Risk",
}


CONTRAT_COURT = {"non precise": "—", "non précisé": "—", "Non précisé": "—"}


class _ChoixStatut(ctk.CTkOptionMenu):
    """Dark-themed status menu that speaks the old Combobox's language.

    The ttk Combobox stayed white on a night background: clam does not colour the
    "readonly" state. This menu keeps get()/set() with "" for "no status", which
    save_edit and _load_edit use as is.
    """

    VIDE = "—"

    def __init__(self, parent: Any) -> None:
        super().__init__(
            parent,
            values=[self.VIDE] + STATUTS[1:],
            width=170,
            height=30,
            corner_radius=RAD_BTN,
            fg_color=WORK,
            button_color=BTN,
            button_hover_color=BTN_H,
            text_color=TX,
            dropdown_fg_color=CARD,
            dropdown_hover_color=BTN_H,
            dropdown_text_color=TX,
            font=ctk.CTkFont(_theme.FONT_UI, 12),
            dropdown_font=ctk.CTkFont(_theme.FONT_UI, 12),
        )
        self.set("")

    def get(self) -> Any:
        v = super().get()
        return "" if v == self.VIDE else v

    def set(self, v: Any) -> None:
        super().set(v or self.VIDE)
