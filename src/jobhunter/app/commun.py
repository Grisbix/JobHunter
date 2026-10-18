"""Constantes de l'application : chemins, statuts, colonnes du tableau, etapes et maintenance.

Partie de jobhunter.app (ancien JobHunter.pyw, phase 3.7)."""

import functools as _ft
import re
import sys
from typing import Any

import customtkinter as ctk

from jobhunter import chemins as chemins
from jobhunter import paresseux as _paresseux
from jobhunter import profil as _profil
from jobhunter import racine as _racine
from jobhunter.app import theme as _theme
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
# Valeurs tirees du profil : calculees a la premiere lecture, pas a l'import
# (jobhunter.paresseux). Dans ce module, on les lit par `_ici.NOM`.
_PARESSEUX: _paresseux.Fabriques = {}


def __getattr__(nom: str) -> Any:
    return _paresseux.lire(_ici, _PARESSEUX, nom)


ROOT = _racine.racine()  # marqueur ou JOBHUNTER_RACINE (jobhunter.racine)


SCRIPTS = ROOT / "Scripts"


PY = sys.executable or "python"


QUEUE = SCRIPTS / "apply_queue.json"


SUIVI = SCRIPTS / "suivi.json"


COMPTES = SCRIPTS / "comptes_sites.json"


PROFILE = SCRIPTS / "apply_profile.json"


# Helpers PARTAGES (chemins file:///, normalisation de texte). Import en tete
# plutot que differe : l'app lit apply_queue.json dans Scripts/ et lance les 48
# programmes qui s'y trouvent — sans ce dossier elle n'a de toute facon rien a
# faire. Mieux vaut echouer ici, clairement, qu'a la 3e ouverture d'un document.
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


CV_ATS_DIR = chemins.CV_MODELES  # 5 CV variants (source, dans le depot)


_PARESSEUX["CV_OFFRE_DIR"] = lambda: chemins.CV_PAR_OFFRE  # CV cibles par offre


_PARESSEUX["LETTRES_DIR"] = lambda: chemins.LT_PAR_OFFRE  # lettres de motivation (docx+pdf)


_PARESSEUX["_PREFIXE"] = lambda: _profil.prefixe_fichier()


# Pays et lieu affiches, memorises par chaine de lieu : le tableau les recalcule
# a chaque rafraichissement, sur 7000 lignes et quelques centaines de lieux.
_pays_lieu = _ft.lru_cache(maxsize=None)(_zones.pays_lieu)


_ville_affichee = _ft.lru_cache(maxsize=None)(_zones.ville_affichee)


_region_lieu = _ft.lru_cache(maxsize=None)(lambda l: _zones.region_pays(_pays_lieu(l)))


# statuts de suivi (libellés lisibles stockés dans suivi.json + feuille Excel SUIVI)
# « mauvaise » = l'offre ne vaut rien POUR MOI (mal notee, hors sujet, senior
# deguise). A distinguer de « refus », qui est la reponse de l'EMPLOYEUR apres
# candidature : confondre les deux fausserait le taux de reponse du panneau
# Stats, ou « refus » compte les portes fermees, pas les offres ecartees.
#
# « pas intéressé » = ni un verdict sur la qualite de l'offre ni une reponse :
# l'utilisateur n'en veut pas, point. L'offre reste dans la file (le scan qui la
# retrouve demain retombe sur la meme cle de suivi, donc elle reste cachee)
# mais disparait du tableau. Reversible en un clic, contrairement a
# « Écarter » qui la retire de la file et exige un motif.
PAS_INTERESSE = "pas intéressé"


# « expiré » = l'annonce est fermee (vue trop tard, ou retiree par l'employeur).
# Ni un jugement sur l'offre (« mauvaise ») ni une reponse (« refus ») : un fait.
# Masque comme « pas intéressé » — rien a faire sur une offre fermee — et garde
# dans le suivi pour que le scan qui la retrouverait ne la refasse pas surgir.
# Ajoute le 2026-10-04 : l'utilisateur notait « mauvaise » + « trop tard » faute de mieux.
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


# Marqueurs MONOCHROMES : ils heritent de la couleur de la ligne, la
# ou un emoji couleur imposait la sienne et cassait la lecture du tableau.
ST_EMOJI = {statut: "" for statut in STATUTS}  # libellés seuls, sans pictogrammes décoratifs


# Couleur de la ligne selon le statut : l'oeil trouve les candidatures en
# cours sans lire la colonne. Posee APRES l'etat du lien (le dernier tag gagne).
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


# Libelles colores DANS le tableau : versions texte, sinon illisibles.
# Seuls les liens A PROBLEME sont colores. « OK » l'etait aussi, en vert : 98 %
# des lignes, tout le tableau vire au vert et plus rien ne se distingue.
LS_COLOR = {
    "MORT": TX_BAD,
    "EXPIREE": TX_AMBRE,
    "FERMEE": TX_BAD,
    "HOMEPAGE": TX_ACC,
    "ANTI-BOT": MUT,
}


# ESSENTIELS : visibles direct. Le reste (maintenance) sous « 🔧 Maintenance ▾ ».
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


# 19 items empiles a plat ne se lisent pas. Regroupes par INTENTION : on
# cherche « ou vont mes offres », pas un nom de script.
MAINT = [
    (
        "Sources & offres",
        [
            ("Scrape les sites", [PY, "-m", "jobhunter.programmes.scrape_jobs", "--headless"]),
            ("Homepages", [PY, "-m", "jobhunter.programmes.enrich_homepages"]),
            # Le scan quotidien ne voit que 7 jours (filtre f_TPR LinkedIn). Une
            # offre publiee en debut de mois et ratee sur le moment reste
            # invisible sans cette passe elargie.
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
            ("CV/lettres…", None),  # None = commande construite a la volee
            ("Sync docs+format", [PY, "-m", "jobhunter.programmes.sync_docs", "--format"]),
            ("Export CSV", [PY, "-m", "jobhunter.programmes.export_queue_csv", "--keep", "8"]),
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
            ("Fix WTJ", [PY, "-m", "jobhunter.programmes.fix_wtj_urls"]),
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
            # Saisie masquee du secret API : il ne transite ni par le chat ni par
            # l'historique shell. Console reelle obligatoire (getpass lit stdin).
            ("Clés France Travail", [PY, "-m", "jobhunter.programmes.setup_francetravail"]),
            ("Fermer Chrome", [PY, "-m", "jobhunter.programmes.acces", "--close"]),
            (
                "Tester accès aux sites",
                [PY, "-m", "jobhunter.programmes.test_acces_sites", "--all", "--limit", "0"],
            ),
            ("Tests live (lent, ouvre un navigateur)", [PY, "test_web_nav.py"]),
            ("Mettre à jour JobHunter", "maj"),  # "maj" = mise a jour + relance (App.mettre_a_jour)
        ],
    ),
]


# scripts interactifs (input()) -> lancés dans une VRAIE console, pas en subprocess piped
INTERACTIVE = (
    "jobhunter.programmes.apply_runner",
    "jobhunter.programmes.setup_francetravail",
    "jobhunter.programmes.acces",
)


SCRAPE_TAG = "\U0001f50e"  # loupe, prefixe des logs du scan automatique


LF = "\n"


# (clé offre, entête, largeur). Colonne numérique (tri num) : fit.
# largeurs élargies pour la police agrandie (sinon texte tronqué / statut « 🆕 nouveau » clippé)
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


# Zones : le tri alphabetique de la colonne doit suivre la PREFERENCE, pas
# l'alphabet. Le chiffre en tete y suffit, et se lit aussi bien a l'oeil.
# « prioritaire » regroupe les secteurs prioritaires du profil : l'etiquette
# nomme le secteur de l'offre (sous_zone), sinon toutes portaient le premier.
ZONE_ETIQ = {
    "prioritaire": "1 · prioritaire",
    "secondaire": "2 · secondaire",
    "inconnu": "3 · non précisé",
    "ailleurs": "4 · ailleurs",
    "international": "5 · étranger",
}


# Dernier segment d'URL qui designe une RUBRIQUE, donc une liste de postes,
# et jamais un poste precis.
# Memes motifs que job_sources : les offres DEJA en file portent souvent
# « CDI » alors que leur intitule dit « Alternance » — LinkedIn se trompe.
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


# Paramètres qui désignent une RECHERCHE, pas une offre : ?query=…, ?q=…,
# ?keywords=…. Un lien d'offre porte un identifiant, pas des mots-clés.
_RX_RECHERCHE_Q = re.compile(r"(^|&)(query|q|k|keywords?|search|recherche)=", re.I)


DEFAULT_ST = ""  # rien affiché tant qu'aucun statut manuel (pas de « 🆕 nouveau »)


# Invite du champ de recherche. Constante et non litteral repete : le texte
# sert AUSSI de sentinelle (« le champ est-il vide ? »), et deux copies qui
# divergent d'un espace feraient chercher l'invite elle-meme.
SEARCH_HINT = "rechercher…"


DOM_SHORT = {
    "ESG / Finance Durable": "ESG",
    "Data / IA / Climate Tech": "Data/IA",
    "Finance / Investissement": "Finance",
    "Conseil / Strategy": "Conseil",
    "Risk / Quant / Assurance": "Risk",
    # libelles actuels de classify_domaine ; les precedents restent pour
    # les offres anciennes. Sans eux la colonne affichait « ESG_Finan ».
    "ESG_Finance_Durable": "ESG",
    "Data_IA": "Data/IA",
    "Risk_Quant": "Risk",
}


CONTRAT_COURT = {"non precise": "—", "non précisé": "—", "Non précisé": "—"}


class _ChoixStatut(ctk.CTkOptionMenu):
    """Menu de statut au theme sombre, qui parle la langue de l'ancien Combobox.

    Le Combobox ttk restait blanc sur fond de nuit : clam ne colore pas l'etat
    « readonly ». Ce menu garde get()/set() avec "" pour « aucun statut », que
    save_edit et _load_edit utilisent tels quels.
    """

    VIDE = "—"

    def __init__(self, parent):
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

    def get(self):
        v = super().get()
        return "" if v == self.VIDE else v

    def set(self, v):
        super().set(v or self.VIDE)
