"""Application constants: paths, statuses, table columns, steps and maintenance.

Part of jobhunter.app (former JobHunter.pyw, phase 3.7)."""

import functools as _ft
import os
import re
import subprocess
import sys
from typing import Any

import customtkinter as ctk

from jobhunter import frozen as _gele
from jobhunter import lazy as _paresseux
from jobhunter import paths as chemins
from jobhunter import profile as _profil
from jobhunter import root as _racine
from jobhunter import tools_catalog as _outils
from jobhunter.app import theme as _theme
from jobhunter.app.language import t as _t


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
# (jobhunter.lazy). In this module, they are read through `_ici.NAME`.
_PARESSEUX: _paresseux.Fabriques = {}


def __getattr__(nom: str) -> Any:
    return _paresseux.lire(_ici, _PARESSEUX, nom)


ROOT = _racine.racine()  # marker or JOBHUNTER_RACINE (jobhunter.root)


SCRIPTS = _racine.scripts()


# Runs the programs as subprocesses: python.exe under Python, jobhunter-cli.exe
# in the installed application (jobhunter.frozen).
PY = _gele.interpreteur()


QUEUE = SCRIPTS / "apply_queue.json"


SUIVI = _racine.dans(SCRIPTS, "suivi.json")


COMPTES = _racine.dans(SCRIPTS, "comptes_sites.json")


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
        [PY, "-m", "jobhunter.programs.apply_runner", "--canal", "auto", "--auto", "--fast"],
        "Remplit+upload chaque offre, tu tapes juste Entrée = envoyé+suivant (console)",
    ),
    (
        "LinkedIn",
        "#0a66c2",
        [
            PY,
            "-m",
            "jobhunter.programs.apply_runner",
            "--canal",
            "linkedin",
            "--chrome",
            "--auto",
        ],
        "Easy Apply semi-auto : réutilise ta session (connecte-toi 1 fois), remplit, STOP sur Envoyer (tu cliques)",
    ),
]


# The second action of the left menu: checks the offers are still open (LinkedIn guest
# API, 404/410, the page's text), then removes the closed ones — never one applied to,
# and the queue is copied first. Bounded: 30 minutes, one pause on a rate limit.
DISPONIBILITE = [
    PY,
    "-m",
    "jobhunter.programs.availability_audit",
    "--supprime",
    "--pauses",
    "1",
    "--duree",
    "30",
]


# The Outils menu: one list shared with the web interface (jobhunter.tools_catalog).
# A program becomes [PY, "-m", module, args…]; an action stays its name.
MAINT: list[tuple[str, list[tuple[str, Any]]]] = [
    (
        groupe,
        [
            (label, [PY, "-m", *args] if (args := _outils.programme(quoi)) else quoi)
            for label, quoi in items
        ],
    )
    for groupe, items in _outils.OUTILS
]


# interactive scripts (input()) -> run in a REAL console, not a piped subprocess
INTERACTIVE = _outils.INTERACTIVE


SCRAPE_TAG = "\U0001f50e"  # magnifier, prefix of the automatic scan's logs


LF = "\n"


# (offer key, header, width). Numeric column (numeric sort): fit.
# widths enlarged for the bigger font (otherwise text truncated / "🆕 nouveau" status clipped)
COLS = [
    ("_chk", "☐", 40),
    ("_alerte", "⚑", 36),  # ⚠ knock-out · ↻ reposted · ≡ same text (programs/reposts)
    ("_st", "Statut", 140),
    ("entreprise", "Entreprise", 190),
    ("poste", "Poste", 330),
    ("domaine", "Domaine", 90),
    ("fit", "Fit", 50),
    ("contrat", "Contrat", 96),
    ("zone", "Zone", 125),
    ("localisation", "Lieu", 170),
    ("pays", "Pays", 100),
    ("region", "Région", 120),
    # The posting's own date (when the source gives it), the day the engine first
    # found it, and the last time it was seen alive (link checked, or served again).
    ("_pub", "Publiée", 80),
    ("process", "Trouvée", 80),
    ("_verif", "Vérifiée", 92),  # "Checked", "Geprüft": wider than the date
    ("signal", "Signal", 170),
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
# The contract types the collection writes; each is translated where it is shown.
CONTRATS = ("CDI", "CDD", "V.I.E", "Freelance", "Interim", "Bénévolat")


# STATUSES AND CONTRACTS ARE STORED IN FRENCH (applications.json, the queue): the
# engine, the follow-ups and the tracking read those words. They are translated only
# where they are shown, and a status chosen in another language goes back to French.
def statut_affiche(statut: str) -> str:
    """A tracking status in the interface language ("" stays "")."""
    return str(_t(statut)) if statut else ""


def statut_de(affiche: str) -> str:
    """The stored (French) status of a status shown in the interface language."""
    return next((s for s in STATUTS if s and statut_affiche(s) == affiche), affiche)


def contrat_affiche(contrat: str) -> str:
    """A contract type in the interface language (CDI -> Permanent…); "—" if unknown."""
    court = CONTRAT_COURT.get(contrat, contrat)
    return str(_t(court)) if court else ""


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
            values=[self.VIDE] + [statut_affiche(s) for s in STATUTS[1:]],
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
        return "" if v == self.VIDE else statut_de(v)

    def set(self, v: Any) -> None:
        super().set(statut_affiche(v) if v else self.VIDE)
