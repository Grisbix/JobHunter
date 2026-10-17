#!/usr/bin/env python3
"""JobHunter — application compacte (1 fenêtre : actions + dashboard riche intégré).
Tkinter (stdlib, aucune install). Double-clic JobHunter.pyw.
Onglet Dashboard = table filtrable + fiche détail + ÉDITION statut/note/date
(écrit direct dans Scripts/suivi.json ; bouton 🔄 Sync Excel pousse vers la feuille SUIVI).
LE dashboard de l'app = source unique d'infos (plus de HTML séparé).
"""

import datetime
import json
import os
import queue
import re
import subprocess
import sys
import threading
import tkinter as tk
import webbrowser
from pathlib import Path
from urllib.parse import quote, urlparse

import customtkinter as ctk

ctk.set_appearance_mode("light")
from tkinter import messagebox, scrolledtext, simpledialog, ttk


def _racine():
    """Racine du projet = premier dossier, en remontant, qui contient Scripts/apply_queue.json.

    Ne suppose PAS que ce fichier est a la racine : il peut etre range dans un
    sous-dossier sans que l'app cesse de trouver ses donnees.
    """
    d = Path(__file__).resolve().parent
    for cand in (d, *d.parents):
        if (cand / "Scripts" / "apply_queue.json").exists():
            return cand
    return d  # rien trouve : on garde l'ancien comportement


ROOT = _racine()
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
# Sans profil, rien ne peut tourner : on le DIT, au lieu que le .pyw se ferme
# sans un mot (il n'a pas de console).
import profil as _profil
from jutil import chemin_de, sans_accent
from jutil import existe as _doc_existe

try:
    _profil.charger()
except _profil.ProfilAbsent as _e:
    # PREMIER LANCEMENT GUIDE : choisir son CV ici, sans terminal. Le profil se
    # cree dans une console (premier_lancement pose ses questions au clavier),
    # puis l'application demarre normalement.
    import subprocess
    from tkinter import filedialog

    _r = tk.Tk()
    _r.withdraw()
    _cv = ""
    if messagebox.askyesno(
        "JobHunter — bienvenue",
        "Aucun profil pour l'instant.\n\nChoisis ton CV (.docx de préférence, "
        "ou .pdf) : JobHunter le lit et te pose quelques questions dans une "
        "fenêtre de commande.\n\nChoisir mon CV maintenant ?",
    ):
        _dep = Path(__file__).resolve().parent / "Mon_CV"
        _cv = filedialog.askopenfilename(
            title="Ton CV",
            initialdir=str(_dep if _dep.is_dir() else Path.home()),
            filetypes=[("CV", "*.docx *.pdf"), ("Word", "*.docx"), ("PDF", "*.pdf")],
        )
    if not _cv:
        messagebox.showinfo(
            "JobHunter",
            "Sans CV, pas de profil : relance JobHunter quand tu "
            "l'auras sous la main. (Voir README.md)",
        )
        sys.exit(1)
    # pythonw n'a pas de console : premier_lancement a besoin de python.exe.
    _py = Path(sys.executable)
    _py = _py.with_name("python.exe") if _py.name.lower() == "pythonw.exe" else _py
    _racine = Path(__file__).resolve().parent
    subprocess.run(
        [str(_py), str(_racine / "Scripts" / "premier_lancement.py"), _cv],
        cwd=str(_racine),
        creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0),
    )
    try:
        _profil.charger()
    except _profil.ProfilAbsent:
        messagebox.showerror(
            "JobHunter",
            "Le profil n'a pas été créé. Lance lancer.bat ou voir README.md, section Dépannage.",
        )
        sys.exit(1)
    messagebox.showinfo(
        "JobHunter",
        "Profil créé : profil/profil.json.\n\nPour le compléter "
        "(compétences, recherches, lettres), ouvre Claude Code dans ce "
        "dossier et tape /configurer-profil.",
    )
    _r.destroy()
# Les documents generes peuvent vivre hors de OneDrive (Scripts/chemins.json).
# L'import vient APRES sys.path : c'est un module de Scripts, comme jutil.
import chemins

CV_ATS_DIR = chemins.CV_MODELES  # 5 CV variants (source, dans le depot)
CV_OFFRE_DIR = chemins.CV_PAR_OFFRE  # CV cibles par offre
LETTRES_DIR = chemins.LT_PAR_OFFRE  # lettres de motivation (docx+pdf)
import profil as _profil
import queue_io  # acces unique a la file : verrou, atomicite, descriptions
from zones import libelle_secteur as _libelle_secteur
from zones import sous_zone as _sous_zone

_PREFIXE = _profil.prefixe_fichier()
import functools as _ft

import zones as _zones

# Pays et lieu affiches, memorises par chaine de lieu : le tableau les recalcule
# a chaque rafraichissement, sur 7000 lignes et quelques centaines de lieux.
_pays_lieu = _ft.lru_cache(maxsize=None)(_zones.pays_lieu)
_ville_affichee = _ft.lru_cache(maxsize=None)(_zones.ville_affichee)
_region_lieu = _ft.lru_cache(maxsize=None)(lambda l: _zones.region_pays(_pays_lieu(l)))
import suivi_io  # acces unique aux candidatures : verrou + relecture fraiche

# Recruitment CRM (Outcrowd) adapté : navigation marine, plan de travail bleu pâle,
# données sur blanc. Couleurs séparées pour les contrôles sur sidebar sombre.
BG = "#E9EFF7"
WORK = "#F4F7FB"
CARD = "#FFFFFF"
LINE = "#D8E2EF"
TX = "#19283F"
MUT = "#52647B"
ROW0 = "#FFFFFF"
ROW1 = "#F5F8FC"
ACC = "#325EDF"
OK = "#25704F"
OK2 = "#25704F"
BAD = "#AC3E49"
PURP = "#70549C"
TEAL = "#246B76"
AMBRE = "#8A5B19"
SIDE = "#172B50"
SIDE_CARD = "#223963"
SIDE_TX = "#F5F8FE"
SIDE_MUT = "#C3D3EC"
SIDE_H = "#304C80"
LOGBG = SIDE_CARD
LOGFG = SIDE_TX
TX_OK = OK
TX_BAD = BAD
TX_AMBRE = AMBRE
TX_ACC = ACC
BTN = "#E7EDF7"
BTN_H = "#D4E1F7"
ACC_H = "#234FC7"
DEL = "#FBECEF"
DEL_H = "#F4DADF"
ACC_TX = "#FFFFFF"
DEL_TX = BAD
RAD_BTN = 6
RAD_CARD = 10

# Nommer une famille de police ABSENTE fait basculer Tk sur un repli arbitraire,
# souvent pire que le point de depart. On resout donc a l'execution, quand une
# fenetre existe, en prenant la premiere famille reellement installee.
FONT_UI = "Segoe UI Variable Display"
FONT_MONO = "Consolas"


# Espacements. Tk n'a ni clamp() ni vw : on evalue une fois au demarrage, a
# partir de la largeur d'ecran reelle. Pas de recalcul au redimensionnement —
# ce serait un comportement nouveau, et le plancher couvre les petites fenetres.
PAD_PAGE = 24  # marge exterieure    clamp(24px, 3vw,   56px)
GAP = 16  # entre widgets       clamp(16px, 1.5vw, 28px)


def _resoudre_espacements(fenetre):
    global PAD_PAGE, GAP
    try:
        w = fenetre.winfo_screenwidth()
    except Exception:
        return
    PAD_PAGE = 20
    GAP = 12


def _resoudre_polices():
    global FONT_UI, FONT_MONO
    import tkinter.font as _tkf

    try:
        dispo = set(_tkf.families())
    except Exception:
        return
    for n in ("Segoe UI", "Segoe UI Variable Display", "IBM Plex Sans"):
        if n in dispo:
            FONT_UI = n
            break
    for n in ("IBM Plex Mono", "Cascadia Mono", "Consolas"):
        if n in dispo:
            FONT_MONO = n
            break


_TRANSPARENT = (BG,)  # seul le fond principal est "conteneur"


def _fgcol(bg):
    return "transparent" if bg in _TRANSPARENT else bg


def _session_presentation(session, verification, aujourd_hui=None):
    """Un contrôle historique n'est pas une preuve de connexion actuelle."""
    aujourd_hui = aujourd_hui or datetime.date.today()
    try:
        age = (aujourd_hui - datetime.date.fromisoformat(str(verification)[:10])).days
    except ValueError:
        age = None
    if age is None or age < 0 or age > 7:
        return "À revérifier", "ancien"
    labels = {
        "connecte": "Connecté",
        "deconnecte": "Déconnecté",
        "bloque": "Bloqué",
        "erreur": "Erreur",
        "indetermine": "Indéterminé",
    }
    return labels.get(session, "Indéterminé"), (
        "ok"
        if session == "connecte"
        else "ko"
        if session in ("deconnecte", "bloque", "erreur")
        else ""
    )


def CF(
    parent,
    bg=None,
    width=None,
    height=None,
    corner_radius=None,
    highlightbackground=None,
    highlightthickness=0,
    plat=False,
    **_,
):
    """plat=True : simple conteneur de mise en page, sans liser ni coins —
    une rangee de boutons posee DANS une carte n'est pas une carte de plus."""
    kw = {}
    if bg is not None:
        kw["fg_color"] = _fgcol(bg)
    if width:
        kw["width"] = width
    if height:
        kw["height"] = height
    surface = bool(bg) and bg not in _TRANSPARENT and not plat
    kw["corner_radius"] = (
        corner_radius if corner_radius is not None else (RAD_CARD if surface else 0)
    )
    if highlightthickness and highlightbackground:
        kw["border_width"] = 1
        kw["border_color"] = highlightbackground
    elif surface:
        # Un seul liser par surface ; aucun cadre ajouté aux sous-conteneurs.
        try:
            fond_parent = parent.cget("fg_color")
        except (ValueError, tk.TclError):
            fond_parent = None
        kw["border_width"] = 1 if bg == CARD and fond_parent != CARD else 0
        kw["border_color"] = LINE
    return ctk.CTkFrame(parent, **kw)


def CB(
    parent,
    text="",
    command=None,
    bg=None,
    fg=None,
    activebackground=None,
    width=None,
    pady=None,
    anchor=None,
    font=None,
    corner_radius=None,
    cursor=None,
    **_,
):
    kw = {
        "text": text,
        "command": command,
        "corner_radius": corner_radius if corner_radius is not None else RAD_BTN,
    }
    if bg is not None:
        kw["fg_color"] = bg
    # Le survol « gagne legerement en luminosite » : une teinte par role, pas
    # un eclat generique. Sans cela CustomTkinter applique son propre bleu.
    _SURVOL = {ACC: ACC_H, BTN: BTN_H, DEL: DEL_H, CARD: BTN_H, SIDE_CARD: BTN_H}
    if activebackground:
        kw["hover_color"] = activebackground
    elif bg in _SURVOL:
        kw["hover_color"] = _SURVOL[bg]
    # Couleur de texte DEDUITE du role quand elle n'est pas imposee : du texte
    # clair sur le bleu clair ACC serait illisible, et un appelant qui oublie
    # fg ne doit pas produire un bouton qu'on ne peut pas lire.
    _TEXTE = {
        ACC: ACC_TX,
        ACC_H: ACC_TX,
        DEL: DEL_TX,
        DEL_H: DEL_TX,
        SIDE: SIDE_TX,
        SIDE_CARD: SIDE_TX,
        SIDE_H: SIDE_TX,
    }
    kw["text_color"] = fg or _TEXTE.get(bg, TX)
    if font:
        kw["font"] = ctk.CTkFont(*font) if isinstance(font, tuple) else font
    if anchor:
        kw["anchor"] = anchor
    kw["height"] = (pady * 2 + 16) if pady else 34
    kw["width"] = width if width else max(70, len(str(text)) * 8 + 20)
    return ctk.CTkButton(parent, **kw)


def CL(
    parent,
    text="",
    bg=None,
    fg=None,
    font=None,
    anchor=None,
    justify=None,
    wraplength=None,
    width=None,
    **_,
):
    kw = {"text": text}
    if bg is not None:
        kw["fg_color"] = _fgcol(bg)
    if fg:
        kw["text_color"] = fg
    if font:
        kw["font"] = ctk.CTkFont(*font) if isinstance(font, tuple) else font
    if anchor:
        kw["anchor"] = anchor
    if justify:
        kw["justify"] = justify
    if wraplength:
        kw["wraplength"] = wraplength
    return ctk.CTkLabel(parent, **kw)


def CE(parent, bg=None, fg=None, width=None, font=None, **_):
    # Focus visible : la bordure suffit, pas besoin d'un halo.
    kw = {"corner_radius": RAD_BTN, "border_width": 1, "border_color": LINE}
    if bg is not None:
        kw["fg_color"] = bg
    if fg:
        kw["text_color"] = fg
    if width:
        kw["width"] = int(width) * 7
    if font:
        kw["font"] = ctk.CTkFont(*font) if isinstance(font, tuple) else font
    return ctk.CTkEntry(parent, **kw)


def make_btn(parent, text, bg=BTN, fg=TX, cmd=None, pw=10, ph=4, w=None, side=None):
    """Bouton solide, arrondi, moderne — aucun effet vitre."""
    b = CB(
        parent,
        text=text,
        font=(FONT_UI, 13, "bold"),
        bg=bg,
        fg=fg,
        activebackground=bg,
        activeforeground=fg,
        relief="flat",
        bd=0,
        cursor="hand2",
        highlightthickness=0,
        padx=pw,
        pady=ph,
    )
    if cmd:
        b.configure(command=cmd)
    if w:
        b.configure(width=w)
    if side:
        b.pack(side=side, padx=6, pady=2)
    return b


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
        [PY, "job_sources.py", "--all"],
        "NOUVELLES offres : APIs ATS (greenhouse/lever/ashby…) + LinkedIn public + WTJ → merge queue (dédup)",
    ),
    (
        "Candidatures en lot",
        "#dc2626",
        [PY, "apply_runner.py", "--canal", "auto", "--auto", "--fast"],
        "Remplit+upload chaque offre, tu tapes juste Entrée = envoyé+suivant (console)",
    ),
    (
        "LinkedIn",
        "#0a66c2",
        [PY, "apply_runner.py", "--canal", "linkedin", "--chrome", "--auto"],
        "Easy Apply semi-auto : réutilise ta session (connecte-toi 1 fois), remplit, STOP sur Envoyer (tu cliques)",
    ),
]
# 19 items empiles a plat ne se lisent pas. Regroupes par INTENTION : on
# cherche « ou vont mes offres », pas un nom de script.
MAINT = [
    (
        "Sources & offres",
        [
            ("Scrape les sites", [PY, "scrape_jobs.py", "--headless"]),
            ("Homepages", [PY, "enrich_homepages.py"]),
            # Le scan quotidien ne voit que 7 jours (filtre f_TPR LinkedIn). Une
            # offre publiee en debut de mois et ratee sur le moment reste
            # invisible sans cette passe elargie.
            ("Rattrapage 31 j", [PY, "job_sources.py", "--all", "--days", "31"]),
            ("Sonder flux ATS", [PY, "probe_ats.py"]),
            ("Sonder flux Workday", [PY, "probe_workday.py"]),
            ("Sonder mots-clés", [PY, "probe_keywords.py", "--days", "30", "--min-new", "3"]),
        ],
    ),
    (
        "Documents",
        [
            ("CV/lettres…", None),  # None = commande construite a la volee
            ("Sync docs+format", [PY, "sync_docs.py", "--format"]),
            ("Export CSV", [PY, "export_queue_csv.py", "--keep", "8"]),
        ],
    ),
    (
        "Hygiène de la file",
        [
            ("URLs mortes", [PY, "queue_tools.py", "mark"]),
            ("Recheck 404", [PY, "recheck_dead.py", "--status", "OK", "--limit", "120"]),
            ("Fix WTJ", [PY, "fix_wtj_urls.py"]),
            ("Re-score", [PY, "rescore_ats.py"]),
        ],
    ),
    (
        "Suivi",
        [
            ("Relances", [PY, "relances.py"]),
            ("Alerte matchs", [PY, "notify_matches.py", "--min-fit", "8"]),
        ],
    ),
    (
        "Accès & diagnostic",
        [
            # Saisie masquee du secret API : il ne transite ni par le chat ni par
            # l'historique shell. Console reelle obligatoire (getpass lit stdin).
            ("Clés France Travail", [PY, "setup_francetravail.py"]),
            ("Fermer Chrome", [PY, "acces.py", "--close"]),
            ("Tester accès aux sites", [PY, "test_acces_sites.py", "--all", "--limit", "0"]),
            ("Tests live (lent, ouvre un navigateur)", [PY, "test_web_nav.py"]),
            ("Mettre à jour JobHunter", "maj"),  # "maj" = mise a jour + relance (App.mettre_a_jour)
        ],
    ),
]

# scripts interactifs (input()) -> lancés dans une VRAIE console, pas en subprocess piped
INTERACTIVE = ("apply_runner.py", "setup_francetravail.py", "acces.py")
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
            font=ctk.CTkFont(FONT_UI, 12),
            dropdown_font=ctk.CTkFont(FONT_UI, 12),
        )
        self.set("")

    def get(self):
        v = super().get()
        return "" if v == self.VIDE else v

    def set(self, v):
        super().set(v or self.VIDE)


class App:
    def __init__(self, root):
        _resoudre_polices()  # une fenetre existe : on sait quelles familles sont installees
        _resoudre_espacements(root)
        self.root = root
        self.proc = None
        self.q = queue.Queue()
        # Une exception dans un rappel Tk s'imprime sur stderr. Dans un .pyw il
        # n'y a pas de console : elle part dans le vide, le bouton ne fait rien
        # et rien ne le dit. On la range dans un fichier et on l'affiche.
        root.report_callback_exception = self._panne_tk
        self.offers = []
        self.suivi = {}
        self.rowmap = {}
        self.comptes = {}
        self._search_cache = {}  # oid -> texte cherchable (vide a chaque load_offers)
        self._search_termes_actifs = []  # termes REELLEMENT appliques au tableau
        self._search_job = None  # after() en attente (anti-saccade)
        try:
            self.myemail = _profil.identite()["email"]
        except Exception:
            self.myemail = ""
        root.title("Offres — suivi candidatures")
        # 1320x840 n'est PAS la taille d'ouverture : c'est celle qu'on retrouve en
        # de-maximisant. La fenetre s'ouvre maximisee.
        root.geometry("1320x840")
        root.minsize(1080, 680)
        root.configure(fg_color=BG)

        def _maximiser():
            try:
                root.state("zoomed")
            except Exception:
                try:
                    root.attributes("-zoomed", True)  # repli Linux
                except Exception:
                    pass

        _maximiser()
        # CustomTkinter re-applique SA geometrie apres __init__ (suivi du facteur
        # d'echelle DPI), ce qui de-maximisait la fenetre juste apres l'ouverture.
        # On re-affirme donc une fois la boucle d'evenements demarree. Deux
        # rappels : le premier suffit d'ordinaire, le second couvre un demarrage
        # lent. « zoomed » garde la barre de titre et les controles systeme —
        # c'est bien maximise, pas du plein ecran sans bordure.
        root.after(80, _maximiser)
        root.after(400, _maximiser)

        body = CF(root, bg=BG)
        body.pack(fill="both", expand=True, padx=0, pady=0)
        # Recruitment CRM : navigation permanente, outils secondaires défilants.
        self.sidebar = CF(body, bg=SIDE, width=238, corner_radius=0)
        self.sidebar.pack(side="left", fill="y", padx=0)
        self.sidebar.pack_propagate(False)
        self._sidebar_on = True
        CL(self.sidebar, text="JOBHUNTER", fg=SIDE_TX, bg=SIDE, font=(FONT_UI, 17, "bold")).pack(
            anchor="w", padx=18, pady=(20, 3)
        )
        CL(
            self.sidebar,
            text="RECHERCHE D'EMPLOI",
            fg=SIDE_MUT,
            bg=SIDE,
            font=(FONT_UI, 10, "bold"),
        ).pack(anchor="w", padx=18, pady=(0, 18))
        self._nav = {}
        for cle, texte, fn in (
            ("offres", "Offres", self._show_dash),
            ("cv", "Mes CV", self._cv_viewer),
            ("entreprises", "Entreprises", self._companies_panel),
            ("sites", "Sites d'offres", self._sources_panel),
            ("stats", "Statistiques", self._stats_panel),
            ("acces", "Accès", self._acces_panel),
        ):
            b = CB(
                self.sidebar,
                text=texte,
                command=lambda c=cle, f=fn: (f(), self._nav_actif(c)),
                bg=SIDE,
                fg=SIDE_MUT,
                activebackground=SIDE_H,
                anchor="w",
                font=(FONT_UI, 13),
            )
            b.pack(fill="x", padx=10, pady=2)
            self._nav[cle] = b
        self._nav_actif("offres")
        CL(self.sidebar, text="ACTIONS", fg=SIDE_MUT, bg=SIDE, font=(FONT_UI, 10, "bold")).pack(
            anchor="w", padx=18, pady=(18, 4)
        )
        journal = CF(self.sidebar, bg=SIDE, plat=True)
        journal.pack(side="bottom", fill="x")
        self._build_log(journal)
        outils = ctk.CTkScrollableFrame(
            self.sidebar, fg_color=SIDE, corner_radius=0, scrollbar_button_color=SIDE_H
        )
        outils.pack(fill="both", expand=True)
        CB(
            outils,
            text="Actualiser les offres",
            command=self.run_all,
            font=(FONT_UI, 13, "bold"),
            bg=ACC,
            fg=ACC_TX,
            relief="flat",
            activebackground=ACC_H,
            cursor="hand2",
            pady=8,
        ).pack(fill="x", padx=10, pady=(8, 6))
        for label, color, cmd, tip in STEPS:
            CB(
                outils,
                text=label,
                command=lambda c=cmd, l=label: self.run_step(c, l),
                font=(FONT_UI, 12),
                bg=SIDE,
                fg=SIDE_MUT,
                relief="flat",
                activebackground=SIDE_H,
                cursor="hand2",
                pady=5,
                anchor="w",
            ).pack(fill="x", padx=10, pady=3)
        # section MAINTENANCE pliée : boutons rarement utiles
        self._maint_on = False
        self.b_maint = CB(
            outils,
            text="Maintenance ▸",
            command=self._toggle_maint,
            bg=SIDE,
            fg=SIDE_MUT,
            relief="flat",
            cursor="hand2",
            activebackground=SIDE_H,
            font=(FONT_UI, 12),
            anchor="w",
            pady=4,
        )
        self.b_maint.pack(fill="x", padx=10, pady=(6, 0))
        self.maint = CF(outils, bg=SIDE, plat=True)  # rempli, affiché à la demande
        for groupe, items in MAINT:
            CL(
                self.maint,
                text=groupe,
                bg=SIDE,
                fg=SIDE_MUT,
                font=(FONT_UI, 11, "bold"),
                anchor="w",
            ).pack(fill="x", padx=16, pady=(12, 2))
            for label, cmd in items:
                CB(
                    self.maint,
                    text=label,
                    command=lambda c=cmd, l=label: (
                        self._gen_docs()
                        if c is None
                        else self.mettre_a_jour()
                        if c == "maj"
                        else self.run_step(c, l)
                    ),
                    font=(FONT_UI, 12),
                    bg=SIDE,
                    fg=SIDE_MUT,
                    relief="flat",
                    activebackground=SIDE_H,
                    cursor="hand2",
                    pady=3,
                    anchor="w",
                ).pack(fill="x", padx=16, pady=2)
        CB(
            outils,
            text="Recharger",
            command=self.load_offers,
            bg=SIDE,
            fg=SIDE_MUT,
            activebackground=SIDE_H,
            relief="flat",
            cursor="hand2",
        ).pack(fill="x", padx=10, pady=(6, 2))

        self.main = CF(body, bg=BG)
        self.main.pack(
            side="left", fill="both", expand=True, padx=PAD_PAGE, pady=(GAP // 2, GAP // 2)
        )
        # UNE SEULE REGLE DE NAVIGATION, faute de quoi rien ne dit ou chercher
        # quoi : la barre du haut ne porte que des DESTINATIONS (ou je vais),
        # la barre laterale que des ACTIONS (ce que je fais). « Fermer Chrome »
        # etait une action posee parmi les destinations, et doublonnait deja
        # avec Maintenance > Acces & diagnostic.
        tp = CF(self.main, bg=BG)
        tp.pack(fill="x", pady=(0, GAP))
        CB(
            tp,
            text="Outils",
            command=self._toggle_sidebar,
            bg=BTN,
            fg=TX,
            relief="flat",
            activebackground=BTN_H,
            cursor="hand2",
            font=(FONT_UI, 13),
        ).pack(side="left", padx=(2, 0), pady=2)
        # Retour de disposition : voir _dispo_retour.
        self._dispo_pile = []
        self.b_dispo = CB(
            tp,
            text="↶ Retour",
            command=self._dispo_retour,
            bg=BTN,
            fg=MUT,
            relief="flat",
            activebackground=BTN_H,
            cursor="hand2",
            font=(FONT_UI, 13),
        )
        self.b_dispo.pack(side="left", padx=(8, 0), pady=2)
        # La navigation principale habite la colonne gauche, pas en doublon
        # dans l'en-tête. Cette barre ne garde que le contexte du travail.
        CL(tp, text="Suivi des candidatures", bg=BG, fg=TX, font=(FONT_UI, 17, "bold")).pack(
            side="left", padx=(20, 0)
        )
        self.nav_context = CL(tp, text="Offres", bg=BG, fg=MUT, font=(FONT_UI, 12))
        self.nav_context.pack(side="right", padx=(0, 12))
        # Le journal vit dans la barre laterale, REPLIEE au demarrage : tout le
        # travail de fond (auto-enrichissement, relances dues, taches lancees
        # depuis la barre du haut) s'ecrivait dans un panneau que personne ne
        # voit. Cette ligne rend la derniere information toujours lisible.
        footer = CF(self.main, bg=BG, plat=True)
        footer.pack(side="bottom", fill="x", pady=(8, 0))
        self.status = CL(footer, text="", bg=BG, fg=MUT, font=(FONT_UI, 12), anchor="e")
        self.status.pack(side="left", fill="x", expand=True)
        # dashboard et visionneuse = 2 panneaux DANS la même fenêtre (pas de popup)
        self.dash = CF(self.main, bg=WORK)
        self.dash.pack(fill="both", expand=True)
        self._build_dash(self.dash)
        self.viewer = None  # panneau CV & Lettres, construit au 1er usage
        self._dv = None  # panneau détail offre plein écran
        self._panels = {}  # panneaux Entreprises / Sites d'offres
        # Navigation CRM visible au démarrage ; Outils / Ctrl+B la replie
        # pour les écrans plus étroits. La ligne d'état reste visible.
        self._desc_busy = False
        self.load_offers()
        self.root.after(100, self._drain)
        self._raccourcis()
        # JOBHUNTER_SANS_FOND=1 : aucun travail de fond (scan, descriptions,
        # sync). Pour ouvrir l'app le temps d'une verification visuelle sans
        # declencher un scan au premier retour de focus.
        if os.environ.get("JOBHUNTER_SANS_FOND"):
            act = os.environ.get("JOBHUNTER_ACTION")
            if act:
                self.root.after(1500, lambda: exec(act, {"app": self, "tk": tk}))
            return
        # AUTO : dès qu'il y a des offres sans description, on les récupère en fond (au démarrage
        # + après chaque ajout/rebuild). Aucun bouton — silencieux.
        self.root.after(2500, self._auto_enrich)
        # AUTO : sync docx→pdf + liens (un docx modifié quelque part = pdf/liens réalignés)
        self.root.after(6000, self._auto_sync)
        self.root.after(4000, self._check_relances)  # relances dues → log
        # AUTO : scan des sites entreprises, 2 min apres le lancement puis toutes les 3 h
        self.root.after(120000, self._auto_scrape)
        self.root.bind("<FocusIn>", self._on_focus_scrape, add="+")

    def _raccourcis(self):
        """Couche clavier sur les actions DEJA existantes — aucune nouvelle.

        448 offres a traiter une par une : chaque aller-retour a la souris est
        un cout paye 448 fois. Les liaisons existantes etaient toutes locales a
        un widget (Entree dans un champ, clic sur le tableau) ; il n'y avait
        aucun raccourci global.
        """
        for touches, action in (
            ("<Escape>", self._show_dash),  # revenir au tableau
            ("<Control-r>", self.load_offers),  # recharger
            ("<F5>", self.run_all),  # TOUT FAIRE
            ("<Control-b>", self._toggle_sidebar),  # replier/ouvrir la barre
            ("<Control-l>", lambda: self.e_url.focus_set()),
            ("<Control-w>", self.stop),  # arreter la tache
            ("<Control-f>", self._focus_search),  # rechercher dans les offres
            ("<Alt-Left>", self._dispo_retour),  # annuler agrandir/retrecir
        ):
            self.root.bind_all(touches, lambda e, f=action: (f(), "break")[1])
        # Raccourcis métier réservés au tableau. bind_all() interceptait aussi
        # Ctrl+A et Ctrl+Z dans les champs de recherche, note et URL : la
        # sélection/annulation native du texte déclenchait une action métier.
        for touches, action in (
            ("<Control-Return>", self._apply_checked),
            ("<Control-a>", lambda: self._check_all(True)),
            ("<Control-d>", lambda: self._check_all(False)),
            ("<Control-z>", self._annuler_dernier),
        ):
            self.tree.bind(touches, lambda e, f=action: (f(), "break")[1])
        self._log(
            "Raccourcis : Echap retour · Alt+Gauche annule agrandir/rétrécir · "
            "Ctrl+R recharger · F5 tout faire · "
            "Ctrl+B barre · dans le tableau : Ctrl+Entree postuler, "
            "Ctrl+A/D cocher/decocher, Ctrl+Z annuler · "
            "Ctrl+L coller un lien · Ctrl+W arreter · Suppr pas intéressé" + chr(10)
        )

    def _nav_actif(self, cle):
        contexte = getattr(self, "nav_context", None)
        if contexte is not None:
            contexte.configure(
                text={
                    "offres": "Offres",
                    "cv": "Mes CV",
                    "entreprises": "Entreprises",
                    "sites": "Sites d'offres",
                    "stats": "Statistiques",
                    "acces": "Accès",
                }.get(cle, cle)
            )
        for c, b in getattr(self, "_nav", {}).items():
            if c == cle:
                b.configure(fg_color=ACC, text_color=ACC_TX, hover_color=ACC_H)
            else:
                b.configure(fg_color=SIDE, text_color=SIDE_MUT, hover_color=SIDE_H)

    def _toggle_maint(self):
        if self._maint_on:
            self.maint.pack_forget()
            self.b_maint.configure(text="Maintenance ▸")
        else:
            self.maint.pack(fill="x", after=self.b_maint)
            self.b_maint.configure(text="Maintenance ▾")
        self._maint_on = not self._maint_on

    # ── Retour de disposition ──
    # l'utilisateur, 2026-10-07 : un panneau elargi, une colonne etiree, la fiche
    # agrandie ou la barre Outils repliee n'avaient aucun retour arriere — il
    # fallait refaire le geste a la main, au pixel pres. On memorise donc la
    # disposition AVANT chaque geste ; « ↶ Retour » (Alt+Gauche) la remet, et
    # chaque appui remonte d'un geste. Le contenu (suivi, statuts) n'y est
    # pas : c'est Ctrl+Z, dans le tableau.
    def _dispo_etat(self):
        etat = {
            "dash": self.dash.winfo_manager() == "pack",
            "barre": bool(getattr(self, "_sidebar_on", True)),
        }
        try:
            etat["split"] = self._offer_split.sash_coord(0)[0]
        except Exception:
            pass
        try:
            etat["cols"] = {c: int(self.tree.column(c, "width")) for c in self._visible_cols}
        except Exception:
            pass
        return etat

    def _dispo_memo(self, etat=None):
        """Empile la disposition `etat` (par defaut : l'actuelle)."""
        etat = etat or self._dispo_etat()
        if not self._dispo_pile or self._dispo_pile[-1] != etat:
            self._dispo_pile.append(etat)
            del self._dispo_pile[:-30]
        self._dispo_maj_bouton()

    def _dispo_maj_bouton(self):
        try:
            self.b_dispo.configure(fg=TX if self._dispo_pile else MUT)
        except Exception:
            pass

    def _dispo_retour(self):
        if not self._dispo_pile:
            self._log("Retour : aucune disposition à rétablir.\n")
            return
        e = self._dispo_pile.pop()
        if e.get("dash") and self.dash.winfo_manager() != "pack":
            self._show_dash()
        if e.get("barre") != self._sidebar_on:
            self._toggle_sidebar(memo=False)
        # Le tableau doit etre affiche et mesure avant de replacer le separateur.
        self.root.update_idletasks()
        if "split" in e:
            try:
                self._offer_split.sash_place(0, e["split"], self._offer_split.sash_coord(0)[1])
            except Exception:
                pass
        for c, w in (e.get("cols") or {}).items():
            try:
                self.tree.column(c, width=w)
            except Exception:
                pass
        self._dispo_maj_bouton()

    def _dispo_suivre(self, widget):
        """Memorise la disposition d'avant tout glisser sur `widget`
        (separateur de panneaux, bord d'une colonne)."""

        def _avant(_e):
            self._dispo_avant = self._dispo_etat()

        def _apres(_e):
            avant = getattr(self, "_dispo_avant", None)
            if avant is not None and avant != self._dispo_etat():
                self._dispo_memo(avant)
            self._dispo_avant = None

        widget.bind("<ButtonPress-1>", _avant, add="+")
        widget.bind("<ButtonRelease-1>", _apres, add="+")

    def _toggle_sidebar(self, memo=True):
        if memo and hasattr(self, "_dispo_pile"):
            self._dispo_memo()
        if self._sidebar_on:
            self.sidebar.pack_forget()
        else:
            self.sidebar.pack(side="left", fill="y", padx=0, before=self.main)
        self._sidebar_on = not self._sidebar_on

    # ── dashboard plein écran : filtres Excel (clic entête) + table + détail + édition ──
    def _build_dash(self, parent):
        self.colsel = {}  # key -> ("keep"|"excl", set) | None (None = toutes)
        self._colidx = {k: i for i, (k, _, _) in enumerate(COLS)}
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Treeview",
            background=ROW0,
            foreground=TX,
            fieldbackground=ROW0,
            rowheight=38,
            borderwidth=0,
            font=(FONT_UI, 12),
            bordercolor=WORK,
            lightcolor=WORK,
            darkcolor=WORK,
        )
        # Entete : plan 3 (widgets), texte attenue en capitales de fait — la
        # donnee doit peser plus lourd que son etiquette.
        style.configure(
            "Treeview.Heading",
            background=CARD,
            foreground=MUT,
            font=(FONT_UI, 11, "bold"),
            relief="flat",
            borderwidth=0,
            padding=(6, 7),
        )
        style.map("Treeview.Heading", background=[("active", BTN_H)], foreground=[("active", TX)])
        style.map("Treeview", background=[("selected", BTN_H)], foreground=[("selected", TX)])
        # Barres de defilement : celles de clam sont grises et claires, seules
        # taches blanches de toute l'application.
        for orient in ("Vertical", "Horizontal"):
            style.configure(
                f"{orient}.TScrollbar",
                background=BTN,
                troughcolor=WORK,
                bordercolor=WORK,
                lightcolor=BTN,
                darkcolor=BTN,
                arrowcolor=MUT,
                gripcount=0,
                relief="flat",
            )
            style.map(f"{orient}.TScrollbar", background=[("active", BTN_H)])
        self.checked = set()  # oids des offres cochées (à postuler en lot)
        self._voir_masquees = False
        self._annuler = []  # pile Ctrl+Z : [(oid, entree de suivi AVANT), ...] par geste

        # ── ligne 1 : chercher · voir masquées ········· coller un lien ──
        # Deux lignes au lieu d'une : sur une seule, les cinq boutons de
        # selection repoussaient la recherche et le champ « coller un lien »
        # HORS de la fenetre — ils existaient sans qu'on puisse les voir.
        heading = CF(parent, bg=WORK, plat=True)
        heading.pack(fill="x", padx=18, pady=(4, 12))
        CL(heading, text="Offres", fg=TX, font=(FONT_UI, 26, "bold")).pack(side="left")
        # CRM : trois indicateurs de travail, pas dix cartes décoratives. Ils
        # restent synchronisés avec la file chargée et le suivi manuel.
        kpis = CF(parent, bg=WORK, plat=True)
        kpis.pack(fill="x", padx=18, pady=(0, 6))
        self._offer_kpis = {}
        for index, (key, label) in enumerate(
            (("total", "OFFRES EN FILE"), ("fit", "FIT ≥ 8"), ("post", "CANDIDATURES ENVOYÉES"))
        ):
            kpis.grid_columnconfigure(index, weight=1, uniform="indicateur")
            tile = CF(kpis, bg=CARD)
            tile.grid(row=0, column=index, sticky="ew", padx=(0, 10 if index < 2 else 0))
            CL(tile, text=label, fg=MUT, bg=CARD, font=(FONT_UI, 10, "bold")).pack(
                anchor="w", padx=14, pady=(10, 0)
            )
            value = CL(tile, text="—", fg=TX, bg=CARD, font=(FONT_UI, 22, "bold"))
            value.pack(anchor="w", padx=14, pady=(0, 8))
            self._offer_kpis[key] = value
        bar = CF(parent, bg=WORK, plat=True)
        bar.pack(fill="x", padx=18, pady=(8, 0))
        self.e_search = CE(bar, width=40, bg=CARD, fg=TX, font=(FONT_UI, 13))
        self.e_search.pack(side="left", fill="x", expand=True, ipady=3)
        self.e_search.insert(0, SEARCH_HINT)
        self.e_search.bind("<FocusIn>", self._search_focus)
        self.e_search.bind("<KeyRelease>", self._search_differe)
        self.e_search.bind("<Return>", lambda e: (self._search_now(), "break")[1])
        self.e_search.bind("<Escape>", lambda e: (self._search_clear(), "break")[1])
        self.b_search = CB(bar, text="Chercher", command=self._search_now, bg=BTN, width=80)
        self.b_search.pack(side="left", padx=(6, 2))
        self.b_search_x = CB(bar, text="✕", command=self._search_clear, bg=BTN, fg=MUT, width=40)
        self.b_search_x.pack(side="left", padx=(0, 4))
        self.sw_masq = ctk.CTkSwitch(
            bar,
            text="Voir les masquées",
            command=self._basculer_masquees,
            font=ctk.CTkFont(FONT_UI, 12),
            text_color=MUT,
            progress_color=ACC,
            button_color=TX,
            button_hover_color=ACC_H,
            fg_color=LINE,
        )
        self.sw_masq.pack(side="left", padx=(18, 0))
        # ＋ coller un lien d'offre → analyse (titre/entreprise/description) + queue + CV/lettre
        importbar = CF(parent, bg=WORK, plat=True)
        importbar.pack(fill="x", padx=18, pady=(8, 0))
        self.b_addurl = CB(importbar, text="Ajouter une offre", command=self._add_offer_url, bg=BTN)
        self.b_addurl.pack(side="right", padx=(6, 0))
        self.e_url = CE(importbar, width=40, bg=CARD, fg=TX, font=(FONT_UI, 12))
        self.e_url.pack(side="left", fill="x", expand=True, ipady=3)
        self.e_url.insert(0, "coller un lien d'offre…")
        self.e_url.bind(
            "<FocusIn>",
            lambda e: self.e_url.get().startswith("coller") and self.e_url.delete(0, "end"),
        )
        self.e_url.bind("<Return>", lambda e: self._add_offer_url())

        # ── ligne 2 : compteur ········· actions sur la sélection (si cochées) ──
        bar2 = CF(parent, bg=WORK, plat=True)
        bar2.pack(fill="x", padx=18, pady=(10, 0))
        # Sans compteur, rien ne distingue « 12 offres apres filtre » de « 2879 »,
        # ni un filtre trop strict d'une queue vide : le tableau restait blanc et
        # muet dans les deux cas.
        self.lbl_count = CL(bar2, text="", bg=WORK, fg=MUT, font=(FONT_UI, 12), anchor="w")
        self.lbl_count.pack(side="left")
        CB(
            bar2,
            text="Colonnes",
            command=self._toggle_columns,
            bg=WORK,
            fg=MUT,
            width=80,
            font=(FONT_UI, 12),
        ).pack(side="right", padx=(8, 0))
        # Les actions de lot n'apparaissent QUE s'il y a une selection : quatre
        # boutons « (0) » permanents etaient du bruit, et le plus dangereux
        # (Supprimer) attirait l'oeil en rouge sans rien avoir a faire.
        self.selbar = CF(bar2, bg=WORK, plat=True)
        self.lbl_sel = CL(self.selbar, text="", bg=WORK, fg=TX, font=(FONT_UI, 12, "bold"))
        self.lbl_sel.pack(side="left", padx=(0, 10))
        self.b_apply = CB(
            self.selbar,
            text="Postuler",
            command=self._apply_checked,
            bg=ACC,
            font=(FONT_UI, 12, "bold"),
        )
        self.b_apply.pack(side="left", padx=3)
        self.b_pasint = CB(
            self.selbar,
            text="Pas intéressé",
            command=self._pas_interesse_checked,
            bg=BTN,
            font=(FONT_UI, 12),
        )
        self.b_pasint.pack(side="left", padx=3)
        self.b_ecarter = CB(
            self.selbar, text="Écarter…", command=self._ecarter_checked, bg=BTN, font=(FONT_UI, 12)
        )
        self.b_ecarter.pack(side="left", padx=3)
        self.b_del = CB(
            self.selbar, text="Supprimer", command=self._delete_checked, bg=DEL, font=(FONT_UI, 12)
        )
        self.b_del.pack(side="left", padx=3)
        CB(
            self.selbar,
            text="Décocher",
            command=lambda: self._check_all(False),
            bg=WORK,
            fg=MUT,
            activebackground=BTN,
            font=(FONT_UI, 12),
        ).pack(side="left", padx=(8, 0))
        self.lbl_aide = CL(
            bar2,
            text="En-tête : filtrer  ·  Double-clic : fiche",
            bg=WORK,
            fg=MUT,
            font=(FONT_UI, 11),
            anchor="e",
        )

        # Le bas (detail + suivi) est place AVANT le tableau, cote bas : le
        # packer sert les widgets dans l'ordre, et le tableau extensible,
        # place en premier, prenait toute la hauteur — le suivi etait coupe.
        split = tk.PanedWindow(
            parent,
            orient="horizontal",
            bg=LINE,
            sashwidth=6,
            borderwidth=0,
            sashrelief="flat",
            opaqueresize=True,
        )
        split.pack(fill="both", expand=True, padx=8, pady=(12, 0))
        twrap = CF(split, bg=WORK, plat=True)
        bas = CF(split, bg=CARD)
        scale = self.root._get_window_scaling()
        split.add(twrap, minsize=int(380 * scale), stretch="always", width=int(720 * scale))
        split.add(bas, minsize=int(340 * scale), stretch="never", width=int(390 * scale))
        self._offer_split = split
        cols = [c[0] for c in COLS]
        self.tree = ttk.Treeview(
            twrap, columns=cols, show="headings", selectmode="browse", height=16
        )
        for key, lbl, wdt in COLS:
            anc = "center" if key in ("fit", "_chk") else "w"
            # entête _chk = cocher/décocher tout ; autres = menu filtre
            cmd = (
                (lambda: self._check_all(None))
                if key == "_chk"
                else (lambda k=key: self._col_menu(k))
            )
            self.tree.heading(key, text=lbl, command=cmd, anchor=anc)
            compact = {
                "_chk": 34,
                "entreprise": 135,
                "poste": 235,
                "fit": 45,
                "contrat": 70,
                "localisation": 115,
                "pays": 85,
                "region": 95,
                "_st": 105,
            }
            self.tree.column(
                key,
                width=compact.get(key, wdt),
                minwidth=compact.get(key, wdt),
                anchor=anc,
                stretch=(key == "poste"),
            )
        self._visible_cols = (
            "_chk",
            "entreprise",
            "poste",
            "fit",
            "contrat",
            "localisation",
            "pays",
            "region",
            "_st",
        )
        self.tree.configure(displaycolumns=self._visible_cols)
        _hsb = ttk.Scrollbar(twrap, orient="horizontal", command=self.tree.xview)
        _vsb = ttk.Scrollbar(twrap, orient="vertical", command=self.tree.yview)
        self.tree.configure(xscrollcommand=_hsb.set, yscrollcommand=_vsb.set)
        _hsb.pack(side="bottom", fill="x")
        _vsb.pack(side="right", fill="y")
        self.tree.pack(side="top", fill="both", expand=True)
        self._urlcol = None  # lien disponible dans la fiche et le menu contextuel
        self._chkcol = "#%d" % (1 + [c[0] for c in COLS].index("_chk"))
        self.tree.bind("<Button-1>", self._click_cell, add="+")
        self._dispo_suivre(split)  # separateur tableau | fiche
        self._dispo_suivre(self.tree)  # largeur des colonnes
        self.tree.bind("<Double-1>", self._fiche_popup)  # double-clic = fiche complète
        self.tree.bind("<Return>", self._fiche_popup)
        self.tree.bind("<Button-3>", self._row_menu)  # clic droit = actions (Postuler + statuts)
        self.tree.bind("<<TreeviewSelect>>", self._load_edit)
        # Suppr sur une ligne = pas intéressé, et le curseur passe a la
        # suivante : trier 400 offres devient une suite de touches. Lie au
        # TABLEAU seulement — dans un champ texte, Suppr efface une lettre.
        self.tree.bind("<Delete>", lambda e: (self._pas_interesse(self._cur), "break")[1])
        self.tree.tag_configure("odd", background=ROW1)
        self.tree.tag_configure("even", background=ROW0)
        for ls, col in LS_COLOR.items():
            self.tree.tag_configure("ls_" + ls, foreground=col)
        # Poses APRES les couleurs de lien : sur une meme ligne, le dernier tag
        # configure l'emporte, et le jugement de l'utilisateur prime sur l'etat du lien.
        for st, col in ST_COULEUR.items():
            self.tree.tag_configure("st_" + st, foreground=col)
        self._sort = (None, False)

        # ── bas : détail de l'offre (gauche) + suivi (droite) ──
        dcard = CF(bas, bg=CARD)
        dcard.pack(side="top", fill="both", expand=True)
        dtop = CF(dcard, bg=CARD, plat=True)
        dtop.pack(fill="x", padx=14, pady=(10, 0))
        CL(dtop, text="FICHE DE L’OFFRE", bg=CARD, fg=MUT, font=(FONT_UI, 11, "bold")).pack(
            side="left"
        )
        CB(
            dtop,
            text="Agrandir",
            command=self._detail_full,
            bg=CARD,
            fg=MUT,
            font=(FONT_UI, 11),
            pady=2,
        ).pack(side="right")
        self.detail = self._zone_texte(dcard, height=7, bg=CARD)
        self.detail.master.pack(fill="both", expand=True, padx=(14, 6), pady=(4, 10))
        self.detail.bind("<Double-1>", lambda e: self._detail_full())  # double-clic = plein écran
        self._detail_vide()

        # ── panneau d'édition du suivi (écrit suivi.json) ──
        ed = CF(bas, bg=CARD)
        ed.pack(side="bottom", fill="x", padx=14, pady=14, before=dcard)
        ed.grid_columnconfigure(1, weight=1)
        self.b_suivi = CB(
            ed,
            text="Suivi et note ▸",
            command=self._toggle_suivi,
            bg=CARD,
            fg=MUT,
            anchor="w",
            font=(FONT_UI, 13),
        )
        self.b_suivi.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        fields = CF(ed, bg=CARD, plat=True)
        fields.grid(row=1, column=0, columnspan=2, sticky="ew")
        fields.grid_columnconfigure(1, weight=1)
        self._suivi_fields = fields
        self._suivi_open = False
        fields.grid_remove()
        self.sel = CL(
            ed,
            text="Sélectionne une offre",
            fg=MUT,
            font=(FONT_UI, 12),
            anchor="w",
            wraplength=320,
            justify="left",
        )
        # Le titre figure déjà dans la fiche ; conserver le widget pour les mises à jour.
        CL(fields, text="Statut", fg=MUT).grid(row=2, column=0, sticky="w", padx=(0, 12))
        self.e_st = _ChoixStatut(fields)
        self.e_st.grid(row=2, column=1, sticky="ew", pady=3)
        CL(fields, text="Date", fg=MUT).grid(row=3, column=0, sticky="w")
        self.e_date = CE(fields, width=13, bg=WORK, fg=TX)
        self.e_date.grid(row=3, column=1, sticky="ew", pady=3)
        CL(fields, text="Note", fg=MUT).grid(row=4, column=0, sticky="w")
        self.e_note = CE(fields, width=25, bg=WORK, fg=TX)
        self.e_note.grid(row=4, column=1, sticky="ew", pady=3)
        self.e_note.bind("<Return>", lambda e: self.save_edit())
        acts = CF(ed, bg=CARD, plat=True)
        acts.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        acts.grid_columnconfigure((0, 1), weight=1)
        CB(
            acts,
            text="Ouvrir l'offre",
            command=lambda: self._open_offer(self._cur),
            bg=ACC,
            font=(FONT_UI, 13, "bold"),
        ).grid(row=0, column=0, sticky="ew", padx=(0, 4), pady=4)
        CB(
            acts,
            text="Envoi confirmé",
            command=lambda: self._postuler(self._cur),
            bg=BTN,
            font=(FONT_UI, 13),
        ).grid(row=0, column=1, sticky="ew", padx=(4, 0), pady=4)
        CB(
            acts,
            text="Pas intéressé",
            command=lambda: self._pas_interesse(self._cur),
            bg=BTN,
            font=(FONT_UI, 12),
        ).grid(row=1, column=0, sticky="ew", padx=(0, 4), pady=4)
        CB(acts, text="Enregistrer", command=self.save_edit, bg=BTN, font=(FONT_UI, 12)).grid(
            row=1, column=1, sticky="ew", padx=(4, 0), pady=4
        )
        self.b_acct = CB(
            acts,
            text="Associer un compte",
            command=self._toggle_account,
            bg=CARD,
            fg=MUT,
            font=(FONT_UI, 12),
        )
        self.b_acct.grid(row=2, column=0, columnspan=2, sticky="w", pady=(4, 0))
        self._cur = None

    def _toggle_columns(self):
        """Vue compacte par défaut, toutes les colonnes restent accessibles."""
        all_cols = tuple(c[0] for c in COLS)
        current = tuple(self.tree.cget("displaycolumns"))
        visible = all_cols if current == self._visible_cols else self._visible_cols
        self.tree.configure(displaycolumns=visible)
        self._urlcol = "#%d" % (visible.index("_url") + 1) if "_url" in visible else None

    def _toggle_suivi(self):
        self._suivi_open = not self._suivi_open
        if self._suivi_open:
            self._suivi_fields.grid()
        else:
            self._suivi_fields.grid_remove()
        self.b_suivi.configure(text="Suivi et note " + ("▾" if self._suivi_open else "▸"))

    def _zone_texte(self, parent, height=7, bg=ROW0):
        """Texte en lecture, au theme : tk.Text + barre ttk stylee.

        ScrolledText impose une barre tk que Windows dessine toujours en gris
        clair. Le cadre porteur est `t.master` — c'est lui qu'on place.
        """
        fr = tk.Frame(parent, bg=bg)
        t = tk.Text(
            fr,
            height=height,
            bg=bg,
            fg=TX,
            insertbackground=TX,
            font=(FONT_UI, 12),
            relief="flat",
            wrap="word",
            state="disabled",
            borderwidth=0,
            highlightthickness=0,
            padx=2,
            pady=2,
            spacing1=1,
            spacing3=2,
            selectbackground=BTN_H,
            selectforeground=TX,
        )
        sb = ttk.Scrollbar(fr, orient="vertical", command=t.yview)
        t.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        t.pack(side="left", fill="both", expand=True)
        t.tag_configure("k", foreground=ACC, font=(FONT_UI, 12, "bold"))
        t.tag_configure("h", foreground=TX, font=(FONT_UI, 15, "bold"), spacing3=4)
        t.tag_configure("m", foreground=MUT)
        return t

    def _detail_vide(self):
        d = self.detail
        d.configure(state="normal")
        d.delete("1.0", "end")
        d.insert("end", "Sélectionne une offre dans le tableau.\n", "m")
        d.insert(
            "end",
            "Double-clic ou Entrée : fiche complète  ·  clic droit : actions  ·  "
            "Suppr : pas intéressé",
            "m",
        )
        d.configure(state="disabled")

    def _basculer_masquees(self):
        self._voir_masquees = bool(self.sw_masq.get())
        self.refresh_table()

    def _clear_filters(self):
        self.colsel.clear()
        self.refresh_table()

    def _cell(self, o, key):
        """Valeur affichée d'une colonne (pour liste de valeurs + filtre)."""
        return str(self._row_vals(o)[self._colidx[key]])

    def _col_menu(self, key):
        """Menu type Excel sur l'entête : tri croissant/décroissant + choisir les valeurs."""
        win = tk.Toplevel(self.root)
        win.overrideredirect(True)
        win.configure(bg=LINE)
        x, y = self.root.winfo_pointerxy()
        win.geometry(f"+{x}+{y + 6}")
        fr = CF(win, bg=CARD)
        fr.pack(padx=2, pady=2)

        def sort(asc):
            self._sort = (key, asc)
            win.destroy()
            self.refresh_table()

        CB(
            fr,
            text="▲  Croissant",
            anchor="w",
            command=lambda: sort(True),
            bg=CARD,
            fg=TX,
            relief="flat",
            cursor="hand2",
        ).pack(fill="x")
        CB(
            fr,
            text="▼  Décroissant",
            anchor="w",
            command=lambda: sort(False),
            bg=CARD,
            fg=TX,
            relief="flat",
            cursor="hand2",
        ).pack(fill="x")
        CF(fr, bg=LINE, height=1).pack(fill="x", pady=6)
        vals = sorted({self._cell(o, key) for o in self.offers}, key=lambda s: s.lower())
        srch = CE(fr, bg=ROW0, fg=TX, insertbackground=TX, relief="flat", width=22)
        srch.pack(fill="x", padx=6)
        lbf = CF(fr, bg=CARD)
        lbf.pack()
        lb = tk.Listbox(
            lbf,
            selectmode="multiple",
            height=min(12, len(vals) or 1),
            bg=ROW0,
            fg=TX,
            relief="flat",
            width=24,
            exportselection=False,
        )
        sb = tk.Scrollbar(lbf, command=lb.yview)
        lb.configure(yscrollcommand=sb.set)
        lb.pack(side="left", fill="both")
        sb.pack(side="right", fill="y")
        cur = self.colsel.get(key)  # ("keep"|"excl", set) | None
        cmode, cset = cur if cur else (None, set())
        shown = list(vals)

        def fill(flt=""):
            lb.delete(0, "end")
            shown.clear()
            for v in vals:
                if flt and flt not in v.lower():
                    continue
                shown.append(v)
                i = lb.size()
                lb.insert("end", v if v else "(vide)")
                # coché = valeur retenue à l'affichage (keep→dans set ; excl→hors set)
                keep = (
                    (cur is None)
                    or (cmode == "keep" and v in cset)
                    or (cmode == "excl" and v not in cset)
                )
                if keep:
                    lb.selection_set(i)

        fill()
        srch.bind("<KeyRelease>", lambda e: fill(srch.get().strip().lower()))
        hint = CL(fr, text="double-clic = seulement celle-ci", bg=CARD, fg=MUT, font=(FONT_UI, 12))
        hint.pack(anchor="w", padx=6)
        bt = CF(fr, bg=CARD)
        bt.pack(fill="x", pady=(2, 0))

        def _sel():
            return {shown[i] for i in lb.curselection()}

        def keep():  # garder seulement la sélection
            sel = _sel()
            self.colsel[key] = None if len(sel) >= len(vals) else ("keep", sel)
            win.destroy()
            self.refresh_table()

        def excl():  # exclure la sélection, montrer le reste
            sel = _sel()
            self.colsel[key] = ("excl", sel) if sel else None
            win.destroy()
            self.refresh_table()

        def only(_e):  # double-clic une valeur → seulement celle-ci
            c = lb.curselection()
            if not c:
                return
            self.colsel[key] = ("keep", {shown[c[0]]})
            win.destroy()
            self.refresh_table()

        lb.bind("<Double-Button-1>", only)

        def tout():
            self.colsel.pop(key, None)
            win.destroy()
            self.refresh_table()

        CB(bt, text="Garder", command=keep, bg=ACC, fg=ACC_TX, relief="flat", cursor="hand2").pack(
            side="left", padx=6
        )
        CB(bt, text="Exclure", command=excl, bg=DEL, fg=DEL_TX, relief="flat", cursor="hand2").pack(
            side="left", padx=6
        )
        CB(bt, text="Tout", command=tout, bg=BTN, fg=TX, relief="flat", cursor="hand2").pack(
            side="left", padx=6
        )
        CB(bt, text="✕", command=win.destroy, bg=BTN, fg=TX, relief="flat").pack(
            side="right", padx=6
        )

        def _close_if_out():
            try:
                f = win.focus_get()
            except Exception:
                f = None
            # ne ferme QUE si le focus a quitté le popup (pas un clic sur un enfant)
            if f is None or not str(f).startswith(str(win)):
                win.destroy()

        win.bind("<FocusOut>", lambda e: win.after(120, _close_if_out))
        win.after(50, win.focus_force)

    def _build_log(self, parent):
        qf = CF(parent, bg=SIDE, plat=True)
        qf.pack(fill="x", padx=12, pady=(8, 2))
        CB(
            qf,
            text="Dossier",
            command=lambda: os.startfile(ROOT),
            bg=SIDE_H,
            fg=SIDE_TX,
            activebackground=ACC,
            relief="flat",
        ).pack(side="left")
        CB(qf, text="Arrêter", command=self.stop, bg=DEL, fg=DEL_TX, relief="flat").pack(
            side="right"
        )
        self.log = scrolledtext.ScrolledText(
            parent,
            bg=LOGBG,
            fg=LOGFG,
            insertbackground=LOGFG,
            font=(FONT_MONO, 10),
            relief="flat",
            height=3,
            wrap="word",
        )
        self.log.pack(fill="both", expand=True, padx=12, pady=(6, 12))
        self._log("Prêt. « ▶ TOUT FAIRE » régénère.\n")

    # ── données ──
    def _oid(self, o):
        return f"{(o.get('entreprise') or '').strip()}|{(o.get('poste') or '').strip()}"

    def _host(self, o):
        u = o.get("url") or ""
        return urlparse(u).netloc.replace("www.", "").lower() if u.startswith("http") else ""

    def _acct_of(self, o):
        """Compte connu pour ce site ? Match host (exact ou sous-domaine). Retour info|None."""
        host = self._host(o)
        if not host:
            return None
        if o.get("etat"):
            return {
                "site": o.get("entreprise", ""),
                "login": o.get("url", ""),
                "email": self.myemail,
                "src": "etat",
            }
        for h, info in self.comptes.items():
            if host == h or host.endswith("." + h) or h.endswith("." + host):
                return info
        return None

    def load_offers(self):
        # la queue change (scan, suppressions) : le texte cherchable mis en cache
        # decrirait sinon des offres qui n'existent plus
        self._search_cache.clear()
        try:
            self.offers = queue_io.charger(QUEUE)
        except Exception:
            self.offers = []
        try:
            self.suivi = __import__("suivi_io").charger(SUIVI)
        except Exception:
            self.suivi = {}
        try:
            self.comptes = json.loads(COMPTES.read_text(encoding="utf-8"))
        except Exception:
            self.comptes = {}
        self.refresh_table()

    def _missing_desc(self):
        """Offres avec URL http mais sans description (à enrichir auto)."""
        return [
            o
            for o in self.offers
            if str(o.get("url") or "").startswith("http")
            and not (o.get("description") or "").strip()
        ]

    def _auto_enrich(self):
        """AUTO (pas de bouton) : récupère en fond les descriptions manquantes par lots,
        puis re-score ATS, recharge, et enchaîne tant qu'il en reste. Headless, silencieux.
        VERROU _bg_busy partagé avec _auto_sync : jamais 2 jobs qui écrivent la queue en même temps."""
        if getattr(self, "_desc_busy", False) or getattr(self, "_bg_busy", False):
            return
        # cap par session : évite de scraper 1300 offres d'un coup (rate-limit/ban)
        if getattr(self, "_desc_batches", 0) >= 8:
            return
        todo = self._missing_desc()
        if not todo:
            return
        self._desc_busy = True
        self._bg_busy = True
        self._desc_batches = getattr(self, "_desc_batches", 0) + 1
        n = len(todo)
        self._log(f"ℹ {n} description(s) manquante(s) — récupération auto en fond…\n")

        def work():
            try:
                subprocess.run(
                    [PY, "scrape_desc.py", "--all", "--limit", "40"],
                    cwd=str(SCRIPTS),
                    capture_output=True,
                    text=True,
                    timeout=900,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                subprocess.run(
                    [PY, "rescore_ats.py"],
                    cwd=str(SCRIPTS),
                    capture_output=True,
                    text=True,
                    timeout=300,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
            except Exception as e:
                err = type(e).__name__
                self.root.after(0, lambda n=err: self._log(f"! auto-desc: {n}\n"))
            self.root.after(0, done)

        def done():
            self._desc_busy = False
            self._bg_busy = False
            self.load_offers()  # recharge (descriptions + ATS mis à jour) → table rafraîchie
            rest = len(self._missing_desc())
            got = n - rest
            self._log(
                f"✅ descriptions: +{got} récupérées ({rest} restantes, dont Indeed/anti-bot).\n"
            )
            if rest and got:  # il en reste ET on progresse → lot suivant
                self.root.after(1500, self._auto_enrich)

        threading.Thread(target=work, daemon=True).start()

    def _auto_sync(self):
        """AUTO : sync_docs.py en fond — docx modifiés → pdf régénérés, liens queue réparés.
        Relancé toutes les 10 min tant que l'app tourne."""
        if getattr(self, "_sync_busy", False) or getattr(self, "_bg_busy", False):
            self.root.after(120000, self._auto_sync)
            return  # occupé → réessaie dans 2 min
        self._sync_busy = True
        self._bg_busy = True

        def work():
            try:
                r = subprocess.run(
                    [PY, "sync_docs.py"],
                    cwd=str(SCRIPTS),
                    capture_output=True,
                    text=True,
                    timeout=3000,
                    encoding="utf-8",
                    errors="replace",
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                lines = [l for l in (r.stdout or "").splitlines() if l.strip()]
                msg = " · ".join(lines[-2:])[:110] if lines else ""
            except Exception as e:
                msg = f"! {type(e).__name__}"

            def done():
                self._sync_busy = False
                self._bg_busy = False
                if msg and not msg.startswith("pdf créés: 0 · pdf resynchronisés: 0"):
                    self._log(f"🔁 sync docs : {msg}\n")
                self.root.after(600000, self._auto_sync)  # re-check dans 10 min

            self.root.after(0, done)

        threading.Thread(target=work, daemon=True).start()

    _SCRAPE_COOLDOWN_S = 1800  # 30 min minimum entre deux scans declenches

    def _scrape_cooldown_ok(self):
        last = getattr(self, "_scrape_last", None)
        if last is None:
            return True
        return (datetime.datetime.now() - last).total_seconds() >= self._SCRAPE_COOLDOWN_S

    def _on_focus_scrape(self, e=None):
        """La fenetre reprend le focus : on revient dans l'app, on rafraichit.

        Declenchement par evenement plutot que minuterie : pas de scan pendant
        que l'app est en arriere-plan, et les offres sont fraiches au moment ou
        tu les regardes. Le cooldown evite qu'un alt-tab repete relance un scan.
        """
        if e is not None and getattr(e, "widget", None) is not self.root:
            return
        if self._scrape_cooldown_ok():
            self._auto_scrape()

    def _auto_scrape(self):
        """AUTO : scrape_jobs.py en fond — nouvelles offres des sites entreprises.

        Meme motif que _auto_sync, mais espace de 3 h : un scan trop frequent se
        fait rate-limiter ou bannir. Cap par session comme _auto_enrich.
        VERROU _bg_busy partage : jamais 2 jobs qui ecrivent la file en meme temps.
        """
        if getattr(self, "_scrape_busy", False) or getattr(self, "_bg_busy", False):
            self.root.after(300000, self._auto_scrape)
            return  # occupe -> reessaie dans 5 min
        if self.proc and self.proc.poll() is None:
            self.root.after(300000, self._auto_scrape)
            return  # un bouton tourne -> 5 min
        if getattr(self, "_scrape_runs", 0) >= 4:
            return  # cap : 4 scans par session
        self._scrape_busy = True
        self._bg_busy = True
        self._scrape_last = datetime.datetime.now()
        self._scrape_runs = getattr(self, "_scrape_runs", 0) + 1
        avant = len(getattr(self, "offers", []) or [])

        def work():
            try:
                r = subprocess.run(
                    [PY, "scrape_jobs.py", "--headless"],
                    cwd=str(SCRIPTS),
                    capture_output=True,
                    text=True,
                    timeout=1800,
                    encoding="utf-8",
                    errors="replace",
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                lines = [l for l in (r.stdout or "").splitlines() if l.strip()]
                msg = " - ".join(lines[-2:])[:110] if lines else ""
                if r.returncode != 0:
                    err = [l for l in (r.stderr or "").strip().splitlines() if l.strip()]
                    msg = (
                        ("! code %d - %s" % (r.returncode, err[-1][:80]))
                        if err
                        else ("! code %d" % r.returncode)
                    )
            except Exception as e:
                msg = "! %s" % type(e).__name__

            def done():
                self._scrape_busy = False
                self._bg_busy = False
                self.load_offers()  # table rafraichie
                neuf = len(getattr(self, "offers", []) or []) - avant
                if neuf > 0:
                    self._log(SCRAPE_TAG + " scan auto : +%d offre(s). %s%s" % (neuf, msg, LF))
                elif msg.startswith("!"):
                    self._log(SCRAPE_TAG + " scan auto : %s%s" % (msg, LF))
                # plus de minuterie : le prochain scan viendra du focus fenetre
                if neuf > 0:
                    self.root.after(1500, self._auto_enrich)  # descriptions des nouvelles

            self.root.after(0, done)

        threading.Thread(target=work, daemon=True).start()

    def _check_relances(self):
        """Signale au démarrage les candidatures « postulé » depuis ≥ 10 j sans réponse."""

        def work():
            try:
                import sys as _s

                if str(SCRIPTS) not in _s.path:
                    _s.path.insert(0, str(SCRIPTS))
                import relances

                lst = relances.a_relancer(10)
            except Exception:
                lst = []
            if lst:
                names = ", ".join(o.get("entreprise", "")[:18] for o, *_ in lst[:5])
                self.root.after(
                    0,
                    lambda: self._log(
                        f"🔔 {len(lst)} candidature(s) à relancer : {names}\n"
                        "   (clic droit sur l'offre → 🔔 Relance)\n"
                    ),
                )

        threading.Thread(target=work, daemon=True).start()

    def _relance_draft(self, o):
        """Brouillon de relance (.txt + mailto ouvert) — TU envoies, puis statut → relancé."""
        key = self._oid(o)

        def work():
            try:
                subprocess.run(
                    [PY, "relances.py", "--draft", key],
                    cwd=str(SCRIPTS),
                    capture_output=True,
                    timeout=60,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                self.root.after(
                    0,
                    lambda: self._log(
                        f"📧 brouillon relance ouvert ({o.get('entreprise', '')}) — "
                        "envoie-le puis passe le statut à « relancé ».\n"
                    ),
                )
            except Exception as e:
                err = type(e).__name__
                self.root.after(0, lambda n=err: self._log(f"! relance: {n}\n"))

        threading.Thread(target=work, daemon=True).start()

    def _statut_of(self, o):
        """Statut effectif = suivi MANUEL uniquement (toi). apply_runner_done.json = essais
        machine (form rempli/test), PAS une vraie candidature → jamais affiché comme 'postulé'."""
        sv = self.suivi.get(self._oid(o), {})
        return (sv["s"], "manuel") if sv.get("s") else ("", "")

    def _fitnum(self, o):
        f = str(o.get("fit") or "").strip()
        return int(f) if f.isdigit() else -1

    def _fitfin(self, o):
        """Fit decimal (ats_match.fit_detail, 2026-10-09) : departage les ex aequo
        d'un meme fit entier. Absent sur une offre pas encore rescoree : le fit
        entier tient lieu."""
        f = o.get("fit_fin")
        return float(f) if isinstance(f, (int, float)) else float(self._fitnum(o))

    def _fit_aff(self, o):
        """fit_fin a une decimale, SANS plafond : il va de fit - 0,45 a fit + 0,45,
        donc jusqu'a 10,4 au sommet. Plafonne a 10, tout le haut de la file
        affichait 10.0 et le tri ne se voyait plus."""
        f = o.get("fit_fin")
        return f"{f:.1f}" if isinstance(f, (int, float)) else o.get("fit", "")

    def _sortkey(self, o, key):
        if key == "_st":
            return self._statut_of(o)[0] or "zzz"
        if key == "_url":
            return urlparse(o.get("url") or "").netloc.replace("www.", "")
        if key == "_date":
            return self.suivi.get(self._oid(o), {}).get("d", "")
        if key == "fit":
            return self._fitfin(o)
        if key == "pays":
            return _pays_lieu(o.get("localisation") or "")
        if key == "region":
            return _region_lieu(o.get("localisation") or "")
        if key == "localisation":
            return _ville_affichee(o.get("localisation") or "")
        v = o.get(key)
        return v if v is not None else ""

    # Types d'URL qui ne menent PAS a une offre precise : page d'accueil,
    # portail carrieres, page de resultats. Les ouvrir donne l'impression que
    # l'app se trompe, alors que le lien direct etait mort et a ete remplace
    # a dessein (queue_tools.writeback garde l'original dans url_orig).
    _PAS_DIRECT = {
        "HOMEPAGE": "⌂",
        "CAREERS_PORTAL": "⌂",
        "OTHER": "⌂",
        "RECHERCHE": "≡",
        "BOARD_SEARCH": "≡",
    }

    def _marque_lien(self, o):
        """Glyphe d'avertissement, ou '' si le lien ouvre bien une offre."""
        g = self._PAS_DIRECT.get(str(o.get("url_type") or ""), "")
        if g:
            return g
        # Le type ne suffit pas : jobs.smartrecruiters.com/<Societe> etait classe
        # OFFRE_DIRECTE alors qu'il ouvre le tableau d'offres de la societe, pas
        # une offre. Un lien d'offre porte toujours un identifiant — un segment
        # de chemin supplementaire, un nombre, ou une requete.
        u = str(o.get("url") or "")
        if not u.startswith("http"):
            return ""
        d = urlparse(u)
        seg = [c for c in (d.path or "").split("/") if c]
        # UNE RECHERCHE N'EST PAS UNE OFFRE. Le test `d.query` plus bas prenait
        # toute chaine de requete pour un identifiant d'offre : les 15 liens
        # `welcometothejungle.com/fr/jobs?query=Amundi+Analyste+ESG` passaient
        # donc pour des liens directs, sans le moindre avertissement. Quatre
        # d'entre eux trônaient a fit 10 en tete de liste, et cliquer dessus
        # ouvrait la page de resultats de WTJ — ce que l'utilisateur a vu comme
        # « l'accueil ». Ce sont des cibles notees a la main, pas des annonces.
        if _RX_RECHERCHE_Q.search(d.query or ""):
            return "≡"
        # Un chemin qui SE TERMINE par un mot de rubrique ouvre la liste des
        # postes, jamais un poste : /careers, /recrutement, /companies/<slug>…
        if seg and seg[-1].lower().strip("-_") in _RUBRIQUES:
            return "⌂"
        if d.query or len(seg) >= 2 or any(c.isdigit() for c in "".join(seg)):
            return ""
        return "⌂"

    # ── RECHERCHE LIBRE ─────────────────────────────────────────────────────
    # _sansaccent vivait ici, en 4e copie de la meme normalisation.
    _sansaccent = staticmethod(sans_accent)

    def _texte_offre(self, o):
        """Tout le texte cherchable d'une offre, mis en cache par identifiant.

        Sans cache, chaque frappe reconstruisait la chaine pour 2500 offres dont
        la description fait plusieurs milliers de caracteres — la saisie devenait
        saccadee. Le cache est vide a chaque load_offers().
        """
        oid = self._oid(o)
        t = self._search_cache.get(oid)
        if t is None:
            t = self._sansaccent(
                " ".join(
                    str(o.get(k) or "")
                    for k in (
                        "entreprise",
                        "poste",
                        "domaine",
                        "contrat",
                        "localisation",
                        "process",
                        "url",
                        "description",
                        "missions",
                        "profil",
                        "skills_match",
                    )
                )
            )
            self._search_cache[oid] = t
        return t

    def _focus_search(self, e=None):
        """Ctrl+F : donne le focus au champ et efface l'invite."""
        self.e_search.focus_set()
        self._search_focus()

    def _search_focus(self, e=None):
        if self.e_search.get() == SEARCH_HINT:
            self.e_search.delete(0, "end")

    def _search_termes(self):
        """Termes saisis, ou [] si le champ est vide / affiche l'invite."""
        q = self.e_search.get().strip()
        if not q or q == SEARCH_HINT:
            return []
        return [m for m in self._sansaccent(q).split() if m]

    def _search_differe(self, e=None):
        """Relance la recherche 300 ms apres la DERNIERE frappe.

        Sans ce delai, refresh_table() reconstruit les 2500 lignes du tableau a
        chaque caractere tape : la fenetre se fige entre deux touches.
        """
        if getattr(self, "_search_job", None):
            try:
                self.root.after_cancel(self._search_job)
            except Exception:
                pass
        self._search_job = self.root.after(300, self._search_now)

    def _search_now(self, e=None):
        self._search_job = None
        termes = self._search_termes()
        if termes == self._search_termes_actifs:
            return  # rien de neuf : on ne redessine pas
        self._search_termes_actifs = termes
        self.refresh_table()

    def _search_clear(self, e=None):
        self.e_search.delete(0, "end")
        self.e_search.insert(0, SEARCH_HINT)
        self.root.focus_set()  # sinon l'invite serait effacee par le FocusIn
        self._search_termes_actifs = []
        self.refresh_table()

    def _row_vals(self, o):
        sv = self.suivi.get(self._oid(o), {})
        stt, src = self._statut_of(o)
        u = o.get("url") or ""
        host = urlparse(u).netloc.replace("www.", "") if u.startswith("http") else "chercher"
        marque = self._marque_lien(o)
        poste = o.get("poste", "")
        if marque and u.startswith("http"):
            host = marque + " " + host
            # LE MARQUEUR DOIT ETRE LA OU L'OEIL VA. Il ne vivait que dans la
            # colonne « site », tout a droite : en triant par fit on ne le voit
            # pas. Quatre lignes dont le lien est une RECHERCHE trônaient a
            # fit 10, et cliquer dessus ouvrait la page de resultats du site —
            # « ça m'envoie sur l'accueil ». On le met aussi devant l'intitule.
            poste = f"{marque} {poste}"
        st_txt = f"{ST_EMOJI.get(stt, '')} {stt}".strip() if stt else DEFAULT_ST
        chk = "☑" if self._oid(o) in self.checked else "☐"
        # ZONE. Bordeaux et l'Ile-de-France d'abord, le Sud-Est ensuite : c'est
        # une preference de l'utilisateur, PAS une mesure d'adequation du poste. Elle
        # vit donc dans sa propre colonne, filtrable, et ne touche pas au fit —
        # une offre parfaite a Lille reste une offre parfaite, mal placee.
        zone = o.get("zone") or ""
        zone_txt = ZONE_ETIQ.get(zone, zone)
        if zone == "prioritaire":
            _sz = _sous_zone(o.get("localisation"))
            if _sz:
                zone_txt = "1 · " + _libelle_secteur(_sz)
        contrat = o.get("contrat") or ""
        # LIEU : toute l'Ile-de-France s'affiche « Paris » (l'utilisateur, 2026-10-05).
        # « La Defense - 92 », « Paris, Ile-de-France, France », « Courbevoie »
        # faisaient chacun une case du filtre. Le lieu exact reste dans la fiche.
        # PAYS : sa propre colonne, filtrable — 61 pays dans la file.
        # REGION (2026-10-07) : Europe, Amerique du Nord, Asie... un clic par continent.
        lieu = o.get("localisation") or ""
        return [
            chk,
            st_txt,
            o.get("entreprise", ""),
            poste,
            DOM_SHORT.get(o.get("domaine"), o.get("domaine") or ""),
            self._fit_aff(o),
            CONTRAT_COURT.get(contrat, contrat),
            zone_txt,
            _ville_affichee(lieu),
            _pays_lieu(lieu),
            _region_lieu(lieu),
            o.get("process", ""),
            host,
            sv.get("d", ""),
        ]

    def _contrats_exclus(self):
        """Types de contrat masques, lus dans sources_config.json — le MEME
        fichier que le scan. Le reglage reste donc dans les parametres : il
        suffit de vider la liste pour tout revoir, sans toucher au code.
        Relu a chaque rafraichissement, pour ne pas exiger un redemarrage."""
        try:
            cfg = json.loads((SCRIPTS / "sources_config.json").read_text(encoding="utf-8"))
            return set(cfg.get("contrats_exclus") or [])
        except Exception:
            return set()

    def _exclu(self, o):
        """Le contrat vient du champ, sinon de l'intitule : les offres deja en
        file portent encore « CDI » la ou LinkedIn s'est trompe."""
        ex = self._exclus
        if not ex:
            return False
        c = str(o.get("contrat") or "")
        if c in ex:
            return True
        t = str(o.get("poste") or "")
        if "Alternance" in ex and _RX_ALT.search(t):
            return True
        return "Stage" in ex and _RX_STAGE.search(t)

    def refresh_table(self):
        for r in self.tree.get_children():
            self.tree.delete(r)
        self.rowmap.clear()
        self._exclus = self._contrats_exclus()
        active = {k: v for k, v in self.colsel.items() if v is not None}
        sk, asc = self._sort
        if sk:
            rows = sorted(self.offers, key=lambda o: self._sortkey(o, sk), reverse=not asc)
        else:
            # Departage par entreprise : ats_pct servait de second critere, mais
            # la colonne a ete retiree et le score ne veut plus rien dire ici.
            rows = sorted(
                self.offers, key=lambda o: (-self._fitnum(o), str(o.get("entreprise") or ""))
            )
        n = 0
        masques = 0
        pas_int = 0
        termes = self._search_termes_actifs
        hors_recherche = 0
        for o in rows:
            if self._exclu(o):
                masques += 1
                continue
            stt = self._statut_of(o)[0]
            if stt in MASQUANTS:
                pas_int += 1
                if not self._voir_masquees:
                    continue
            # tous les termes doivent etre presents (ET), dans n'importe quel champ
            if termes:
                txt = self._texte_offre(o)
                if not all(m in txt for m in termes):
                    hors_recherche += 1
                    continue
            vals = [str(v) for v in self._row_vals(o)]
            skip = False
            for k, (mode, sel) in active.items():
                c = vals[self._colidx[k]]
                if (mode == "keep" and c not in sel) or (mode == "excl" and c in sel):
                    skip = True
                    break
            if skip:
                continue
            tags = ["odd" if n % 2 else "even"]
            ls = o.get("link_status", "")
            if ls in LS_COLOR:
                tags.append("ls_" + ls)
            # Une offre jugee mauvaise reste visible — l'utilisateur doit pouvoir
            # revenir sur son verdict — mais grisee, pour que l'oeil la saute.
            # Les autres statuts colorent la ligne (ST_COULEUR).
            if stt in ST_COULEUR:
                tags.append("st_" + stt)
            iid = self.tree.insert("", "end", values=vals, tags=tuple(tags))
            self.rowmap[iid] = o
            n += 1
        for key, lbl, _ in COLS:
            if key == "_chk":
                continue  # entête ☐ garde son libellé (cocher/décocher tout)
            arrow = (" ▲" if asc else " ▼") if sk == key else ""
            filt = " ▾" if self.colsel.get(key) is not None else ""
            self.tree.heading(key, text=lbl + arrow + filt)
        if getattr(self, "lbl_count", None) is not None:
            filtres = sum(1 for v in self.colsel.values() if v is not None)
            if n == 0:
                if termes:
                    msg = "aucune offre ne contient « %s » — Echap ou ✕ pour effacer" % " ".join(
                        termes
                    )
                elif filtres:
                    msg = "aucune offre ne passe les filtres — clique sur ▾ dans une entete pour les lever"
                else:
                    msg = "aucune offre dans la file"
                self.lbl_count.configure(text=msg, text_color=TX_AMBRE)
            else:
                base = len(self.offers) - masques - (0 if self._voir_masquees else pas_int)
                detail = f" sur {base}" if n != base else ""
                cache = (
                    f"   ·   {masques} masquee(s) : {', '.join(sorted(self._exclus))}"
                    if masques
                    else ""
                )
                rech = f"   ·   🔍 « {' '.join(termes)} »" if termes else ""
                self.lbl_count.configure(text=f"{n} offre(s){detail}{rech}{cache}", text_color=MUT)
        if getattr(self, "_offer_kpis", None):
            stats = {
                "total": len(self.offers),
                "fit": sum(1 for o in self.offers if self._fitnum(o) >= 8),
                "post": sum(
                    1
                    for v in self.suivi.values()
                    if str((v or {}).get("s") or "").lower() == "postulé"
                ),
            }
            for key, label in self._offer_kpis.items():
                label.configure(text=str(stats[key]))
        if getattr(self, "sw_masq", None) is not None:
            self.sw_masq.configure(text=f"Voir les masquées ({pas_int})")
        self._upd_apply_btn()

    # ── édition suivi (écrit suivi.json direct) ──
    def _load_edit(self, e=None):
        it = self.tree.focus()
        o = self.rowmap.get(it)
        if not o:
            return
        self._cur = o
        sv = self.suivi.get(self._oid(o), {})
        acc = self._acct_of(o)
        self.sel.configure(text=f"{o.get('entreprise', '')} — {o.get('poste', '')[:70]}")
        self.b_acct.configure(text="Retirer le compte" if acc else "Associer un compte")
        self.e_st.set(sv.get("s", ""))
        self.e_note.delete(0, "end")
        self.e_note.insert(0, sv.get("n", ""))
        self.e_date.delete(0, "end")
        self.e_date.insert(0, sv.get("d", ""))
        self._show_detail(o)

    def _fill_detail(self, d, o):
        """Écrit TOUTES les colonnes Excel de l'offre dans le widget texte d."""
        d.configure(state="normal")
        d.delete("1.0", "end")
        d.insert("end", f"{o.get('entreprise', '')} — {o.get('poste', '')}\n", "h")
        acc = self._acct_of(o)
        d.insert("end", ("● compte  ·  " if acc else "") + f"{self._host(o)}\n", "m")
        meta = []
        for lbl, k in [
            ("Fit", "fit"),
            ("Action", "action"),
            ("Contrat", "contrat"),
            ("Lieu", "localisation"),
            ("Télétravail", "teletravail"),
            ("Domaine", "domaine"),
            ("Compétences", "skills_match"),
            ("Correspondance ATS", "ats_pct"),
            ("Canal", "canal"),
            ("Type", "url_type"),
            ("État lien", "link_status"),
        ]:
            v = o.get(k)
            if v not in (None, "", "Non précisé"):
                meta.append(f"{lbl} : {str(v).replace('_', ' ')}")
        yrs = o.get("exp_requise")
        if yrs:  # années d'expérience exigées (l'utilisateur junior → fit pénalisé si ≥3)
            meta.append(f"⚠️ Exp requise: {yrs} ans" if yrs >= 3 else f"Exp requise: {yrs} ans")
        if meta:
            d.insert("end", "\n".join(meta) + "\n", "m")
        desc = (o.get("description") or "").strip()
        if desc:
            d.insert("end", "\nDescription\n", "k")
            d.insert("end", desc + "\n")
        for lbl, k in [
            ("Salaire / Avantages", "salaire"),
            ("Profil requis", "profil"),
            ("Missions / Compétences", "missions"),
            ("Pourquoi", "pourquoi"),
            ("Recruteur", "rh"),
            ("Source", "source"),
            ("Process", "process"),
            ("CV", "cv"),
            ("Lettre", "lettre"),
            ("URL", "url"),
        ]:
            v = (o.get(k) or "").strip()
            if v and v != "Non précisé":
                d.insert("end", f"\n{lbl} : ", "k")
                d.insert("end", v)
        d.configure(state="disabled")
        d.see("1.0")

    def _show_detail(self, o):
        self._fill_detail(self.detail, o)

    def _fiche_popup(self, e=None):
        o = self.rowmap.get(self.tree.focus())
        if not o:
            return
        w = tk.Toplevel(self.root)
        w.title(f"Fiche — {o.get('entreprise', '')}")
        w.geometry("820x680")
        w.configure(bg=BG)
        carte = CF(w, bg=CARD)
        carte.pack(fill="both", expand=True, padx=20, pady=(20, 12))
        t = self._zone_texte(carte, bg=CARD)
        t.master.pack(fill="both", expand=True, padx=16, pady=14)
        self._fill_detail(t, o)
        btn = CF(w, bg=BG)
        btn.pack(fill="x", padx=20, pady=(0, 16))
        CB(
            btn,
            text="Envoi confirmé",
            command=lambda: (self._postuler(o), self._fill_detail(t, o)),
            bg=ACC,
            fg=ACC_TX,
            activebackground=ACC_H,
            relief="flat",
        ).pack(side="left")
        CB(
            btn, text="Pas intéressé", command=lambda: (self._pas_interesse(o), w.destroy()), bg=BTN
        ).pack(side="left", padx=(12, 0))
        CB(
            btn,
            text="Ouvrir l'offre",
            command=lambda: self._open_offer(o),
            bg=BTN,
            fg=TX,
            activebackground=BTN_H,
            relief="flat",
        ).pack(side="left", padx=12)
        bd = CB(btn, text="Description", bg=BTN, fg=TX, activebackground=BTN_H, relief="flat")
        bd.configure(command=lambda: self._fetch_desc(o, t, bd))
        bd.pack(side="left", padx=12)
        cvp = self._cv_of(o)
        if cvp:
            CB(
                btn,
                text="Voir CV",
                command=lambda: (w.destroy(), self._cv_viewer(str(cvp))),
                bg=BTN,
                fg=TX,
                relief="flat",
            ).pack(side="left", padx=12)
        ltp = self._lettre_of(o)
        if ltp:
            CB(
                btn,
                text="Voir lettre",
                command=lambda: (w.destroy(), self._cv_viewer(str(ltp))),
                bg=BTN,
                fg=TX,
                relief="flat",
            ).pack(side="left", padx=12)
        CB(btn, text="Fermer", command=w.destroy, bg=BTN, fg=TX, relief="flat").pack(side="right")

    def _fetch_desc(self, o, textwidget, btn):
        """Récupère la description de l'offre en ligne (scrape_desc.py, headless) → queue → détail."""
        key = self._oid(o)
        if not (o.get("url") or "").startswith("http"):
            self._log("✗ pas d'URL http pour récupérer la description\n")
            return
        try:
            btn.configure(text="Chargement…", state="disabled")
        except Exception:
            pass

        def work():
            try:
                r = subprocess.run(
                    [PY, "scrape_desc.py", "--key", key],
                    cwd=str(SCRIPTS),
                    capture_output=True,
                    text=True,
                    timeout=100,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                out = (r.stdout or "") + (r.stderr or "")
            except Exception as e:
                out = f"err {type(e).__name__}: {e}"
            self.root.after(0, lambda: done(out))

        def done(out):
            try:
                q = queue_io.charger(QUEUE)
                for x in q:
                    if self._oid(x) == key:
                        o["description"] = x.get("description", "")
                        break
            except Exception:
                pass
            try:
                self._fill_detail(textwidget, o)
            except Exception:
                pass
            try:
                btn.configure(text="Description", state="normal")
            except Exception:
                pass
            self._log(
                "✅ description récupérée\n"
                if o.get("description")
                else "✗ description introuvable (page JS/mur login ?)\n"
            )

        threading.Thread(target=work, daemon=True).start()

    def _toggle_account(self):
        """Marque/retire un compte pour ce site (comptes_sites.json)."""
        o = self._cur
        if not o:
            return
        host = self._host(o)
        if not host:
            self._log("(pas d'URL → pas de host)\n")
            return
        if self._acct_of(o) and not o.get("etat"):
            for h in [
                k
                for k in list(self.comptes)
                if host == k or host.endswith("." + k) or k.endswith("." + host)
            ]:
                self.comptes.pop(h, None)
            self._log(f"－ compte retiré: {host}\n")
        else:
            self.comptes[host] = {
                "site": o.get("entreprise", ""),
                "login": o.get("url", ""),
                "email": self.myemail,
                "src": "manuel",
            }
            self._log(f"Associer un compte ajouté: {host}\n")
        try:
            self._jwrite(COMPTES, self.comptes)
        except Exception as ex:
            self._log(f"! écriture comptes_sites.json KO: {ex}\n")
        self.refresh_table()
        self._load_edit()

    def save_edit(self):
        if not self._cur:
            self._log("Sélectionne d'abord une offre.\n")
            return
        oid = self._oid(self._cur)
        rec = {}
        if self.e_st.get():
            rec["s"] = self.e_st.get()
        if self.e_note.get().strip():
            rec["n"] = self.e_note.get().strip()
        if self.e_date.get().strip():
            rec["d"] = self.e_date.get().strip()
        if not self._ecrire_suivi(oid, rec):
            return
        self._log(f"💾 suivi enregistré: {oid} → {rec or '(vidé)'}\n")
        self.refresh_table()

    def _ecrire_suivi(self, oid, rec):
        """UNE candidature, écrite sous verrou sur l'état frais du disque.

        L'app écrivait `self.suivi`, son instantané mémoire : un clic « postulé »
        réécrivait tout le fichier et effaçait ce que `relances.py` y avait mis
        entre-temps. Reproduit — deux relances perdues sans un mot. On n'écrit
        plus qu'une entrée, et `suivi_io` relit le disque à l'intérieur du
        verrou : le travail des autres est conservé.
        """
        try:
            # Attente COURTE : Tkinter est mono-fil, une attente longue dans un
            # gestionnaire de clic fige la fenetre et l'app parait plantee.
            suivi_io.poser(oid, rec, SUIVI, attente=4)
        except suivi_io.VerrouIndisponible:
            self._log("✗ un autre programme écrit suivi.json — réessaie dans un instant.\n")
            return False
        except Exception as ex:
            self._log(f"! écriture suivi.json KO: {ex}\n")
            return False
        # On recharge depuis le disque plutot que de patcher la memoire : c'est
        # le seul etat qui tienne compte des autres ecrivains.
        self.suivi = suivi_io.charger(SUIVI)
        return True

    def _set_statut(self, o, statut):
        """Écrit un statut dans suivi.json (date auto = aujourd'hui si absente). Manuel > auto."""
        if not o:
            return
        oid = self._oid(o)
        # On repart de l'entree TELLE QU'ELLE EST SUR LE DISQUE, pas de la copie
        # memoire : une note ou une relance ajoutee entre-temps doit survivre.
        avant = dict(suivi_io.charger(SUIVI).get(oid, {}))
        rec = dict(avant)
        if statut:
            rec["s"] = statut
            rec.setdefault("d", datetime.date.today().isoformat())
        else:
            rec = {}
        if not self._ecrire_suivi(oid, rec):
            return
        self._annuler.append([(oid, avant)])
        self._log(f"📌 statut: {o.get('entreprise', '')} → {statut or '(vidé)'}\n")
        self.refresh_table()

    def _pas_interesse(self, o):
        """Suppr / bouton / clic droit : l'offre sort du tableau, reste en file.

        Le curseur passe a la ligne suivante AVANT le rafraichissement : sinon
        il retombe en tete de tableau et chaque offre triee coute un defilement.
        """
        if not o:
            self._log("Sélectionne d'abord une offre.\n")
            return
        suivante = None
        kids = self.tree.get_children()
        cur = self.tree.focus()
        if cur in kids:
            i = kids.index(cur)
            voisin = kids[i + 1] if i + 1 < len(kids) else (kids[i - 1] if i else None)
            suivante = self._oid(self.rowmap[voisin]) if voisin else None
        self._set_statut(o, PAS_INTERESSE)
        self.checked.discard(self._oid(o))
        if suivante:
            self._focus_oid(suivante)

    def _focus_oid(self, oid):
        for iid, x in self.rowmap.items():
            if self._oid(x) == oid:
                self.tree.selection_set(iid)
                self.tree.focus(iid)
                self.tree.see(iid)
                self.tree.focus_set()
                return

    def _pas_interesse_checked(self):
        """Toutes les offres cochees d'un coup. Un seul Ctrl+Z les rend toutes."""
        oids = [k for k in self.checked if self._find_by_oid(k)]
        if not oids:
            self._log("Coche d'abord des offres (colonne ☐).\n")
            return
        geste, jour = [], datetime.date.today().isoformat()

        def _f(s):  # UNE transaction : verrou, relecture, ecriture
            geste.clear()
            for oid in oids:
                avant = dict(s.get(oid, {}))
                rec = dict(avant)
                rec["s"] = PAS_INTERESSE
                rec.setdefault("d", jour)
                s[oid] = rec
                geste.append((oid, avant))

        try:
            suivi_io.modifier(_f, SUIVI, attente=4)
        except suivi_io.VerrouIndisponible:
            self._log("✗ un autre programme écrit suivi.json — réessaie dans un instant.\n")
            return
        except Exception as ex:
            self._log(f"! écriture suivi.json KO: {ex}\n")
            return
        self.suivi = suivi_io.charger(SUIVI)
        self._annuler.append(list(geste))
        self.checked.clear()
        self.refresh_table()
        self._log(f"⊖ {len(geste)} offre(s) « pas intéressé » — masquées, Ctrl+Z pour annuler.\n")

    def _annuler_dernier(self):
        """Ctrl+Z : remet le suivi du dernier geste tel qu'il etait avant."""
        if not self._annuler:
            self._log("Rien à annuler.\n")
            return
        geste = self._annuler.pop()

        def _f(s):
            for oid, avant in geste:
                if avant:
                    s[oid] = avant
                else:
                    s.pop(oid, None)

        try:
            suivi_io.modifier(_f, SUIVI, attente=4)
        except Exception as ex:
            self._annuler.append(geste)
            self._log(f"✗ annulation impossible pour l'instant ({type(ex).__name__}) — réessaie.\n")
            return
        self.suivi = suivi_io.charger(SUIVI)
        self.refresh_table()
        if len(geste) == 1:
            self._focus_oid(geste[0][0])
        self._log(f"↶ annulé ({len(geste)} offre(s)).\n")

    def _postuler(self, o):
        """Enregistre uniquement un envoi explicitement confirmé par l'utilisateur."""
        if not o:
            return
        if messagebox.askyesno(
            "Confirmer l'envoi", "As-tu envoyé cette candidature ?", parent=self.root
        ):
            self._set_statut(o, "postulé")

    def _apply_checked(self):
        """Postule TOUTES les offres cochées : runner semi-auto (remplit + upload, STOP sur
        Envoyer = toi). Écrit la sélection dans apply_selection.json, lance la console."""
        oids = [o for o in [self._find_by_oid(k) for k in self.checked] if o]
        if not oids:
            self._log("Coche d'abord des offres (colonne ☐).\n")
            return
        sel = [{"entreprise": o.get("entreprise", ""), "poste": o.get("poste", "")} for o in oids]
        SEL = SCRIPTS / "apply_selection.json"
        try:
            SEL.write_text(json.dumps(sel, ensure_ascii=False, indent=1), encoding="utf-8")
        except Exception as ex:
            self._log(f"! écriture sélection KO: {ex}\n")
            return
        self._log(
            f"📮 Postuler {len(sel)} offre(s) cochée(s) — console (remplit, STOP sur Envoyer).\n"
        )
        self.run_console(
            [PY, "apply_runner.py", "--selection", str(SEL), "--auto"],
            f"Postuler sélection ({len(sel)})",
        )

    def _find_by_oid(self, oid):
        for o in self.offers:
            if self._oid(o) == oid:
                return o
        return None

    def _row_menu(self, e):
        """Clic droit sur une ligne → actions par offre (Postuler + statuts rapides)."""
        iid = self.tree.identify_row(e.y)
        if not iid:
            return
        self.tree.selection_set(iid)
        self.tree.focus(iid)
        o = self.rowmap.get(iid)
        if not o:
            return
        m = tk.Menu(
            self.root,
            tearoff=0,
            bg=CARD,
            fg=TX,
            activebackground=BTN_H,
            activeforeground=TX,
            relief="flat",
            borderwidth=1,
            font=(FONT_UI, 11),
        )
        m.add_command(label="Confirmer une candidature envoyée…", command=lambda: self._postuler(o))
        m.add_command(label="🌐 Ouvrir l'offre", command=lambda: self._open_offer(o))
        if self._statut_of(o)[0] == PAS_INTERESSE:
            m.add_command(
                label="↶ Finalement intéressé (vider le statut)",
                command=lambda: self._set_statut(o, ""),
            )
        else:
            m.add_command(
                label=f"{ST_EMOJI[PAS_INTERESSE]} Pas intéressé   (Suppr)",
                command=lambda: self._pas_interesse(o),
            )
        if self._statut_of(o)[0] in ("postulé", "relancé"):
            m.add_command(
                label="🔔 Relance (brouillon mail)", command=lambda: self._relance_draft(o)
            )
        m.add_separator()
        for s in ("à postuler", "à vérifier", "postulé", "relancé", "entretien", "refus"):
            m.add_command(
                label=f"{ST_EMOJI.get(s, '')} {s}", command=lambda s=s: self._set_statut(o, s)
            )
        # « mauvaise » a part, apres un separateur : ce n'est pas une etape du
        # parcours de candidature mais un jugement sur l'offre elle-meme.
        m.add_separator()
        m.add_command(
            label=f"{ST_EMOJI['mauvaise']} mauvaise (offre sans intérêt)",
            command=lambda: self._set_statut(o, "mauvaise"),
        )
        m.add_command(
            label=f"{ST_EMOJI[EXPIRE]} expiré (annonce fermée)",
            command=lambda: self._set_statut(o, EXPIRE),
        )
        m.add_separator()
        m.add_command(label="✖ vider le statut", command=lambda: self._set_statut(o, ""))
        try:
            m.tk_popup(e.x_root, e.y_root)
        finally:
            m.grab_release()

    def _open_offer(self, o):
        """Ouvre l'URL de l'offre ; sinon recherche web (entreprise + poste)."""
        if not o:
            return
        u = o.get("url") or ""
        if not u.startswith("http"):
            self._search_web(o)
            return
        webbrowser.open(u)
        marque = self._marque_lien(o)
        if not marque:
            self._log(f"→ {u[:78]}" + chr(10))
            return
        # Sans ce message on croit l'app cassee : elle ouvre une page
        # d'accueil alors qu'on attendait une offre.
        quoi = "page de resultats" if marque == "≡" else "page carrieres / accueil"
        mort = " — le lien direct etait mort" if o.get("url_orig") else ""
        self._log(
            f"→ {u[:78]}"
            + chr(10)
            + f"   ATTENTION : {quoi}, pas l'offre elle-meme{mort}."
            + chr(10)
        )

    def _search_web(self, o):
        if not o:
            return
        qy = quote(f"{o.get('entreprise', '')} {o.get('poste', '')} recrutement")
        webbrowser.open(f"https://www.google.com/search?q={qy}")
        self._log(f"🔍 recherche web: {o.get('entreprise', '')}\n")

    def _click_cell(self, e):
        """Clic colonne ☐ = coche/décoche ; colonne Lien = ouvre l'offre."""
        if self.tree.identify_region(e.x, e.y) != "cell":
            return
        col = self.tree.identify_column(e.x)
        o = self.rowmap.get(self.tree.identify_row(e.y))
        if not o:
            return
        if col == self._chkcol:
            self._toggle_check(o)
            return
        if col == self._urlcol:
            self._open_offer(o)

    def _toggle_check(self, o):
        oid = self._oid(o)
        if oid in self.checked:
            self.checked.discard(oid)
        else:
            self.checked.add(oid)
        self.refresh_table()
        self._upd_apply_btn()

    def _check_all(self, val):
        """val True=coche tout (lignes filtrées visibles), False=décoche tout, None=bascule."""
        vis = [self.rowmap[i] for i in self.tree.get_children()]
        oids = [self._oid(o) for o in vis]
        if val is None:
            val = not all(x in self.checked for x in oids) if oids else False
        if val:
            self.checked.update(oids)
        else:
            if len(self.checked) == len(oids) and set(oids) == self.checked:
                self.checked.clear()
            else:
                self.checked.difference_update(oids)
        self.refresh_table()
        self._upd_apply_btn()

    def _upd_apply_btn(self):
        n = len(self.checked)
        try:
            if n:
                self.lbl_sel.configure(text=f"{n} cochée(s)")
                self.lbl_aide.pack_forget()
                self.selbar.pack(side="right")
            else:
                self.selbar.pack_forget()
                self.lbl_aide.pack(side="right")
        except Exception:
            pass

    def _ecarter_checked(self):
        """Écarte les offres cochées AVEC un motif, et retient le refus.

        Supprimer ne suffit pas : le scan retrouve l'offre à la source et la
        réajoute le lendemain. Ici le refus est mémorisé dans exclusions.json,
        que merge_into_queue consulte avant d'ajouter quoi que ce soit.

        Le motif n'est pas un ornement. Un refus sur une offre à fit élevé est
        un désaccord entre le score et le jugement de l'utilisateur — c'est ce que lit
        `python exclusions.py` pour montrer ce que la notation rate.
        """
        oids = set(self.checked)
        if not oids:
            self._log("Coche d'abord des offres (colonne ☐).\n")
            return
        motif = self._demander_motif(len(oids))
        if not motif:
            return
        try:
            import exclusions
        except Exception as ex:
            self._log(f"! exclusions.py introuvable: {ex}\n")
            return
        if not self._verrou_queue(True):
            self._log("✗ un autre programme modifie la file — réessaie dans un instant.\n")
            return
        try:
            try:
                fresh = queue_io.charger(QUEUE)
            except Exception:
                fresh = list(self.offers)
            vises = [o for o in fresh if self._oid(o) in oids]
            # On enregistre AVANT de retirer : si l'écriture de la file échoue,
            # mieux vaut une exclusion en trop qu'une offre écartée sans motif.
            n_exc = exclusions.ajouter(vises, motif)
            restant = [o for o in fresh if self._oid(o) not in oids]
            retirees = len(fresh) - len(restant)
            try:
                queue_io.sauver(restant, QUEUE)
            except Exception as ex:
                self._log(f"! écriture queue KO: {ex}\n")
                return
        finally:
            self._verrou_queue(False)
        self.checked.clear()
        self.load_offers()
        self._log(
            f"✕ {retirees} offre(s) écartée(s) — « {motif} ». "
            f"{n_exc} nouvelle(s) exclusion(s) ; elles ne reviendront pas au scan.\n"
            f"   Bilan de ce que la notation rate : python Scripts/exclusions.py\n"
        )

    def _demander_motif(self, n):
        """Petite boîte : motifs fréquents en boutons, plus un champ libre.

        Rend le motif choisi, ou None si l'utilisateur annule.

        Parente = self.root. Elle etait `self`, l'objet App, qui n'est pas un
        widget : Toplevel(self) levait a chaque clic et « Écarter » ne
        s'ouvrait jamais — l'exception partait dans le journal de panne.
        """
        try:
            import exclusions

            motifs = list(exclusions.MOTIFS)
        except Exception:
            motifs = [
                "Trop d'expérience demandée",
                "Poste trop senior",
                "Pas le bon métier",
                "Lieu impossible",
            ]
        dlg = ctk.CTkToplevel(self.root)
        dlg.title("Écarter des offres")
        dlg.configure(fg_color=BG)
        dlg.transient(self.root)
        dlg.resizable(False, False)
        choix = {"v": None}
        carte = CF(dlg, bg=CARD)
        carte.pack(fill="both", expand=True, padx=16, pady=16)
        CL(
            carte,
            text=f"Pourquoi écarter ces {n} offre(s) ?",
            bg=CARD,
            fg=TX,
            font=(FONT_UI, 15, "bold"),
            anchor="w",
        ).pack(fill="x", padx=18, pady=(16, 2))
        CL(
            carte,
            text="Retirées de la file et bloquées au prochain scan. Le motif sert à "
            "corriger la notation.",
            bg=CARD,
            fg=MUT,
            font=(FONT_UI, 11),
            anchor="w",
            wraplength=380,
            justify="left",
        ).pack(fill="x", padx=18, pady=(0, 12))

        def prendre(m):
            choix["v"] = m
            dlg.destroy()

        for m in motifs:
            CB(
                carte,
                text=m,
                command=lambda m=m: prendre(m),
                bg=BTN,
                anchor="w",
                font=(FONT_UI, 12),
                width=380,
            ).pack(fill="x", padx=18, pady=3)
        CL(
            carte, text="ou une autre raison :", bg=CARD, fg=MUT, font=(FONT_UI, 11), anchor="w"
        ).pack(fill="x", padx=18, pady=(12, 2))
        e = CE(carte, bg=WORK, fg=TX, width=54)
        e.pack(fill="x", padx=18)
        e.bind("<Return>", lambda ev: prendre(e.get().strip() or None))
        e.bind("<Escape>", lambda ev: dlg.destroy())
        barre = CF(carte, bg=CARD, plat=True)
        barre.pack(fill="x", padx=18, pady=(14, 16))
        CB(barre, text="Annuler", command=dlg.destroy, bg=BTN).pack(side="right")
        CB(barre, text="Écarter", command=lambda: prendre(e.get().strip() or None), bg=DEL).pack(
            side="right", padx=8
        )
        # grab APRES l'affichage : sur Windows, un grab_set sur une fenetre pas
        # encore visible echoue (« grab failed: window not viewable »).
        dlg.after(80, lambda: (dlg.grab_set(), e.focus_set()))
        self.root.wait_window(dlg)
        return choix["v"]

    CORBEILLE = SCRIPTS / "_corbeille"

    def _delete_checked(self):
        """Supprime les offres cochées de apply_queue.json, après copie en corbeille.

        La boîte promettait « récupérable via git ». C'était faux le jour où je
        l'ai vérifié : le dernier commit de la file datait de la veille et
        424 offres du disque n'existaient dans aucun commit — dont les 428
        arrivées ce jour-là. Supprimer l'une d'elles la perdait pour de bon.
        On écrit donc une copie horodatée avant de retirer quoi que ce soit ;
        la promesse porte maintenant sur un fichier qui existe vraiment.
        """
        oids = set(self.checked)
        if not oids:
            self._log("Coche d'abord des offres (colonne ☐).\n")
            return
        if not messagebox.askyesno(
            "Supprimer les offres",
            f"Supprimer {len(oids)} offre(s) cochée(s) de la liste ?\n\n"
            "Une copie est gardée dans Scripts/_corbeille/ — rien n'est perdu.\n"
            "Pour qu'elles ne reviennent pas au prochain scan, préfère\n"
            "« Écarter » : le motif est retenu.",
        ):
            return
        # VERROU. Relire le disque juste avant d'ecrire REDUIT la fenetre de course
        # mais ne la ferme pas : un job de fond qui ecrit entre cette relecture et
        # notre ecriture voit son travail efface. L'app etait le SEUL des 14
        # ecrivains de la queue a ne pas prendre le verrou.
        if not self._verrou_queue(True):
            self._log("✗ un autre programme modifie la file — réessaie dans un instant.\n")
            return
        try:
            # état frais : les jobs de fond ont pu enrichir la queue depuis le
            # dernier chargement — sinon on écraserait leurs modifs
            try:
                fresh = queue_io.charger(QUEUE)
            except Exception:
                fresh = list(self.offers)
            before = len(fresh)
            partantes = [o for o in fresh if self._oid(o) in oids]
            fresh = [o for o in fresh if self._oid(o) not in oids]
            removed = before - len(fresh)
            # LA COPIE D'ABORD. Si l'écriture de la file échoue ensuite, on a une
            # corbeille en trop ; dans l'autre ordre, on aurait des offres
            # supprimées sans copie. `charger()` a réinjecté les descriptions,
            # elles partent donc avec.
            sauvegarde = ""
            try:
                self.CORBEILLE.mkdir(parents=True, exist_ok=True)
                f = self.CORBEILLE / f"supprimees_{datetime.datetime.now():%Y-%m-%d_%H%M%S}.json"
                self._jwrite(f, partantes)
                sauvegarde = f.name
            except Exception as ex:
                self._log(f"! copie de sauvegarde KO ({ex}) — suppression ANNULÉE.\n")
                return
            try:
                # sauver() ressort les descriptions vers descriptions.json ;
                # _jwrite les réécrirait dans la file et annulerait la séparation.
                queue_io.sauver(fresh, QUEUE)
            except Exception as ex:
                self._log(f"! écriture queue KO: {ex}\n")
                return
        finally:
            self._verrou_queue(False)
        self.checked.clear()
        self.load_offers()  # recharge l'état frais
        self._log(
            f"🗑 {removed} offre(s) supprimée(s) — copie dans Scripts/_corbeille/{sauvegarde}\n"
        )

    # ── visionneuse CV & LETTRES : panneau INTÉGRÉ (remplace le dashboard, Retour) ──
    # PDF → PyMuPDF (toutes les pages EMPILÉES, molette = dérouler en entier)
    # DOCX/TXT → texte extrait (python-docx) dans un panneau scrollable
    @staticmethod
    def _verrou_queue(prendre, _attente=20):
        """Prend / rend le verrou inter-processus de la queue. True si obtenu.

        `jutil` vit dans Scripts/ : import differe, pour que l'app demarre meme si
        ce dossier bouge. Attente courte (20 s) : c'est une action interactive,
        mieux vaut dire « reessaie » que figer la fenetre 3 minutes.
        """
        try:
            if str(SCRIPTS) not in sys.path:
                sys.path.insert(0, str(SCRIPTS))
            import jutil
        except Exception:
            return True  # jutil introuvable : on n'empeche pas d'agir
        try:
            if prendre:
                return jutil.prendre_verrou(QUEUE, attente=_attente)
            jutil.rendre_verrou(QUEUE)
            return True
        except Exception:
            # UNE PANNE DU VERROU N'EST PAS UN FEU VERT. Ce cas rendait True et
            # l'action destructive continuait sans protection — l'inverse de ce
            # que le verrou existe pour empecher. Rendre la main est sans
            # risque : l'appelant affiche « reessaie ». Le cas « jutil
            # introuvable » ci-dessus reste permissif, lui : sans Scripts/
            # l'app n'a de toute facon pas de file a proteger.
            return not prendre

    @staticmethod
    def _jwrite(path, obj):
        """Écriture JSON ATOMIQUE (tmp + replace) : un crash mi-écriture ne corrompt jamais le fichier."""
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")
        os.replace(str(tmp), str(path))

    def _hide_all(self):
        """Cache tous les panneaux (dash, visionneuse, détail, listes)."""
        self.dash.pack_forget()
        if self.viewer is not None:
            self.viewer.pack_forget()
        if self._dv is not None:
            self._dv.pack_forget()
        for p in self._panels.values():
            p.pack_forget()

    def _show_dash(self):
        self._hide_all()
        if getattr(self, "_viewer_close", None):
            self._viewer_close()  # déverrouille le pdf affiché
        self.dash.pack(fill="both", expand=True)
        self._nav_actif("offres")

    def _stats_panel(self):
        """📊 STATS : vue synthétique de la queue (les données existent dans
        apply_queue.json + suivi.json mais n'étaient visibles nulle part)."""
        self._hide_all()
        if "stats" in self._panels:
            w = self._panels["stats"]
            w._reload()
            w.pack(fill="both", expand=True)
            return
        w = CF(self.main, bg=WORK)
        self._panels["stats"] = w
        top = CF(w, bg=BG)
        top.pack(fill="x")
        CB(
            top,
            text="Offres",
            command=self._show_dash,
            bg=BTN,
            fg=MUT,
            relief="flat",
            cursor="hand2",
            font=(FONT_UI, 13),
        ).pack(side="left", padx=12, pady=(2, 0))
        CL(top, text="Statistiques", bg=BG, fg=TX, font=(FONT_UI, 16)).pack(side="left", padx=28)
        CB(
            top,
            text="Rafraîchir",
            command=lambda: w._reload(),
            bg=BTN,
            fg=TX,
            activebackground=BTN_H,
            relief="flat",
            cursor="hand2",
        ).pack(side="right", padx=24)

        # Grille a colonnes egales : dix cartes cote a cote en pack() sortaient
        # de la fenetre, et les trois dernieres (Entretien, Refus…) etaient coupees.
        cards = CF(w, bg=WORK, plat=True)
        cards.pack(fill="x", padx=28, pady=(12, 4))
        w._cards = {}
        for i, (k, lbl) in enumerate(
            (
                ("total", "Offres"),
                ("vivantes", "Liens OK"),
                ("desc", "Avec description"),
                ("fit8", "Fit ≥ 8"),
                ("pretes", "Dossiers préparés"),
                ("post", "Postulé"),
                ("rel", "Relancé"),
                ("ent", "Entretien"),
                ("ref", "Refus"),
                ("pasint", "Pas intéressé"),
            )
        ):
            cards.grid_columnconfigure(i % 5, weight=1, uniform="carte")
            c = CF(cards, bg=CARD)
            c.grid(row=i // 5, column=i % 5, sticky="ew", padx=5, pady=5)
            v = CL(c, text="—", bg=CARD, fg=ACC if k == "pretes" else TX, font=(FONT_UI, 26))
            v.pack(padx=8, pady=(10, 0))
            CL(c, text=lbl, bg=CARD, fg=MUT, font=(FONT_UI, 13)).pack(padx=8, pady=(0, 14))
            w._cards[k] = v

        body = CF(w, bg=BG)
        body.pack(fill="both", expand=True, padx=28, pady=18)
        cols = ("cat", "n", "bar")
        tv = ttk.Treeview(body, columns=cols, show="headings", selectmode="none")
        for k, lbl, wd, anc in (
            ("cat", "Catégorie", 300, "w"),
            ("n", "Nb", 70, "center"),
            ("bar", "Répartition", 520, "w"),
        ):
            tv.heading(k, text=lbl)
            tv.column(k, width=wd, anchor=anc, stretch=(k == "bar"))
        tv.pack(fill="both", expand=True)
        tv.tag_configure("h", foreground=ACC, font=(FONT_UI, 13, "bold"))
        w._tv = tv

        def reload_():
            # relit le DISQUE : le pipeline tourne en fond, self.offers peut être périmé
            try:
                q = queue_io.charger(QUEUE)
            except Exception:
                q = list(self.offers)
            try:
                sv = __import__("suivi_io").charger(SUIVI) if SUIVI.exists() else {}
            except Exception:
                sv = {}
            # Cle « s », pas « statut » : c'est ce qu'ecrivent _set_statut et
            # suivi_io. Avec « statut », les cartes Postulé/Relancé/Entretien/
            # Refus affichaient 0 alors que dix candidatures etaient suivies.
            st = [str((v or {}).get("s") or "").lower() for v in sv.values()]
            ok = [
                o for o in q if str(o.get("link_status") or "").upper() not in ("MORT", "EXPIREE")
            ]

            # PRETES A ENVOYER = le seul chiffre qui decide d'une soiree.
            # « fit >= 8 » seul est trompeur : une offre dont le CV ou la lettre
            # n'existe plus SUR LE DISQUE ne peut pas etre envoyee, et la queue
            # peut tres bien garder la reference d'un fichier efface.
            def _fichier(u):
                if not u:
                    return False
                try:
                    return _doc_existe(u)
                except Exception:
                    return False

            _top = [o for o in ok if (o.get("fit") or 0) >= 8]
            _pretes, _sans_doc, _sans_desc, _lien_douteux = [], [], [], []
            for o in _top:
                if not (_fichier(o.get("cv")) and _fichier(o.get("lettre"))):
                    _sans_doc.append(o)
                    continue
                if len(str(o.get("description") or "")) < 200:
                    _sans_desc.append(o)
                    continue
                if not o.get("ls_check"):
                    _lien_douteux.append(o)
                    continue
                _pretes.append(o)
            vals = {
                "total": len(q),
                "vivantes": len(ok),
                "desc": sum(1 for o in q if str(o.get("description") or "").strip()),
                "fit8": sum(1 for o in ok if (o.get("fit") or 0) >= 8),
                "pretes": len(_pretes),
                "post": sum(1 for s in st if s == "postulé"),
                "rel": sum(1 for s in st if s == "relancé"),
                "ent": sum(1 for s in st if s == "entretien"),
                "ref": sum(1 for s in st if s == "refus"),
                "pasint": sum(1 for s in st if s == PAS_INTERESSE),
            }
            for k, lab in w._cards.items():
                lab.configure(text=str(vals[k]))

            tv.delete(*tv.get_children())

            def section(titre, pairs):
                if not pairs:
                    return
                tv.insert("", "end", values=(titre, "", ""), tags=("h",))
                mx = max((n for _, n in pairs), default=0) or 1
                for nom, n in pairs:
                    bar = "█" * max(0, round(38 * n / mx))
                    pct = f"{100 * n / len(q):.0f}%" if q else ""
                    tv.insert("", "end", values=(f"   {nom}", n, f"{bar} {pct}"))

            def count(key, src=None):
                d = {}
                for o in src or q:
                    v = str(o.get(key) or "—").strip() or "—"
                    d[v] = d.get(v, 0) + 1
                return sorted(d.items(), key=lambda x: -x[1])

            # Ce qui separe une offre bien notee d'une offre envoyable. Sans ce
            # detail, « 487 a fit >= 8 » laisse croire que tout est pret.
            section(
                "▶ Sur les offres a fit ≥ 8",
                [
                    ("dossiers préparés (envoi à vérifier)", len(_pretes)),
                    ("bloquees : CV ou lettre absent du disque", len(_sans_doc)),
                    ("bloquees : description trop courte", len(_sans_desc)),
                    ("bloquees : lien jamais verifie", len(_lien_douteux)),
                ],
            )
            section("Domaine", count("domaine")[:8])
            section("Canal", count("canal"))
            section("État des liens", count("link_status"))
            fits = [
                (f"fit {i}", sum(1 for o in ok if (o.get("fit") or 0) == i))
                for i in range(10, 0, -1)
            ]
            section("Fit (offres vivantes)", [p for p in fits if p[1]])
            ats_b = [
                ("100 %", 0),
                ("80-99 %", 0),
                ("60-79 %", 0),
                ("40-59 %", 0),
                ("< 40 %", 0),
                ("non scoré", 0),
            ]
            d = dict(ats_b)
            for o in ok:
                a = o.get("ats_pct")
                if a is None:
                    d["non scoré"] += 1
                elif a >= 100:
                    d["100 %"] += 1
                elif a >= 80:
                    d["80-99 %"] += 1
                elif a >= 60:
                    d["60-79 %"] += 1
                elif a >= 40:
                    d["40-59 %"] += 1
                else:
                    d["< 40 %"] += 1
            section("ATS % (offres vivantes)", [(k, v) for k, v in d.items() if v])
            src = count("source")
            section("Sources (top 10)", [(s[:46], n) for s, n in src[:10]])

        w._reload = reload_
        reload_()
        w.pack(fill="both", expand=True)

    def _acces_panel(self):
        """🔐 ACCÈS : état de connexion par site + clés d'API.
        AUCUN mot de passe n'est stocké ici — ils restent dans le gestionnaire
        de Chrome, qui remplit lui-même les formulaires quand les scripts
        tournent avec --chrome sur le profil Chrome DÉDIÉ (jamais le profil personnel)."""
        self._hide_all()
        if "acces" in self._panels:
            w = self._panels["acces"]
            w._reload()
            w.pack(fill="both", expand=True)
            return
        w = CF(self.main, bg=WORK)
        self._panels["acces"] = w
        top = CF(w, bg=BG)
        top.pack(fill="x")
        CB(
            top,
            text="Offres",
            command=self._show_dash,
            bg=BTN,
            fg=MUT,
            relief="flat",
            cursor="hand2",
            font=(FONT_UI, 13),
        ).pack(side="left", padx=12, pady=(2, 0))
        CL(top, text="Accès aux sites", bg=BG, fg=TX, font=(FONT_UI, 16)).pack(side="left", padx=28)
        CL(
            w,
            text="Ouvre un site pour te connecter, puis vérifie la session. "
            "Les mots de passe restent dans Chrome.",
            bg=BG,
            fg=MUT,
            font=(FONT_UI, 13),
            anchor="w",
            justify="left",
            wraplength=700,
        ).pack(fill="x", padx=28, pady=(2, 4))

        bar = CF(w, bg=BG)
        bar.pack(fill="x", padx=28, pady=(0, 4))
        CB(
            bar,
            text="Ouvrir la connexion",
            command=lambda: self._acces_open(w),
            bg=ACC,
            fg=ACC_TX,
            activebackground=ACC_H,
            relief="flat",
            cursor="hand2",
        ).pack(side="left")
        CB(
            bar,
            text="Vérifier les sessions",
            command=lambda: self.run_step([PY, "acces.py", "--check"], "Vérif sessions"),
            bg=BTN,
            fg=TX,
            activebackground=BTN_H,
            relief="flat",
            cursor="hand2",
        ).pack(side="left", padx=18)
        CB(
            bar,
            text="Saisir une clé d'API",
            command=lambda: self.run_step(
                [PY, "acces.py", "--set-key", "francetravail"], "Clé API"
            ),
            bg=BTN,
            fg=TX,
            activebackground=BTN_H,
            relief="flat",
            cursor="hand2",
        ).pack(side="left")
        CB(
            bar,
            text="Rafraîchir",
            command=lambda: w._reload(),
            bg=BTN,
            fg=TX,
            activebackground=BTN_H,
            relief="flat",
            cursor="hand2",
        ).pack(side="right")

        cols = ("site", "id", "sess", "date")
        tv = ttk.Treeview(w, columns=cols, show="headings", selectmode="browse")
        for k, lbl, wd in (
            ("site", "Site", 300),
            ("id", "Identifiant (email)", 260),
            ("sess", "Dernier contrôle", 160),
            ("date", "Vérifié le", 120),
        ):
            tv.heading(k, text=lbl)
            tv.column(k, width=wd, anchor="w", stretch=(k == "id"))
        tv.pack(fill="both", expand=True, padx=28, pady=12)
        tv.tag_configure("ok", foreground=TX_OK)
        tv.tag_configure("ko", foreground=TX_BAD)
        tv.tag_configure("ancien", foreground=TX_AMBRE)
        w._tv = tv

        keys = CL(w, text="", bg=BG, fg=MUT, font=(FONT_UI, 13), anchor="w", justify="left")
        keys.pack(fill="x", padx=28, pady=(0, 8))

        def reload_():
            import importlib.util as _iu

            spec = _iu.spec_from_file_location("acces", SCRIPTS / "acces.py")
            m = _iu.module_from_spec(spec)
            spec.loader.exec_module(m)
            try:
                comptes = json.loads((SCRIPTS / "comptes.json").read_text(encoding="utf-8"))
            except Exception:
                comptes = {}
            tv.delete(*tv.get_children())
            for host in m.SITES_CONNEXION:
                e = comptes.get(host) or {}
                s = str(e.get("session") or "?")
                label, tag = _session_presentation(s, e.get("session_verif"))
                tv.insert(
                    "",
                    "end",
                    values=(
                        host,
                        e.get("identifiant") or "—",
                        label,
                        e.get("session_verif") or "—",
                    ),
                    tags=(tag,),
                )
            kp = SCRIPTS / "api_keys.json"
            try:
                k = json.loads(kp.read_text(encoding="utf-8")) if kp.exists() else {}
            except Exception:
                k = {}
            ft = "✓ installée" if (SCRIPTS / "francetravail.json").exists() else "✗ absente"
            noms = ", ".join(sorted(k)) if k else "aucune"
            keys.configure(
                text=f"Clés d'API enregistrées : {noms}   ·   France Travail : {ft}"
                "   (les valeurs ne sont jamais affichées)"
            )

        w._reload = reload_
        reload_()
        w.pack(fill="both", expand=True)

    def _acces_open(self, w):
        """Ouvre la page de connexion du site sélectionné dans le navigateur."""
        sel = w._tv.selection()
        if not sel:
            self._log("Selectionne d'abord un site dans la liste.\n")
            return
        host = w._tv.item(sel[0], "values")[0]
        self.run_step([PY, "acces.py", "--open", host], f"Connexion {host}")

    # sites d'OFFRES généraux (boards) — PAS des entreprises
    BOARD_HOSTS = (
        "linkedin",
        "indeed",
        "welcometothejungle",
        "glassdoor",
        "efinancialcareers",
        "wizbii",
        "jobteaser",
        "hellowork",
        "apec.fr",
        "meteojob",
        "monster",
        "jobs.smartrecruiters",
        "engagement-jeunes",
        "wttj",
    )

    def _is_board(self, url):
        return any(b in url.lower() for b in self.BOARD_HOSTS)

    def _domains_file(self):
        F = SCRIPTS / "unique_domains.txt"
        try:
            return F, [
                l.split("|", 1)[-1].strip()
                for l in F.read_text(encoding="utf-8").splitlines()
                if l.strip()
            ]
        except Exception:
            return F, []

    def _companies_panel(self):
        """🏢 ENTREPRISES (boards exclus → panneau Sites) : tableau à colonnes,
        Entreprise | Type | Offres en queue | ATS | 🔗 Lien (dernière, clic = ouvre)."""
        self._hide_all()
        if "companies" in self._panels:
            w = self._panels["companies"]
            w._reload()
            w.pack(fill="both", expand=True)
            return
        w = CF(self.main, bg=WORK)
        self._panels["companies"] = w
        top = CF(w, bg=BG)
        top.pack(fill="x")
        CB(
            top,
            text="Offres",
            command=self._show_dash,
            bg=BTN,
            fg=MUT,
            relief="flat",
            cursor="hand2",
            font=(FONT_UI, 13),
        ).pack(side="left", padx=12, pady=(2, 0))
        CL(top, text="Entreprises à scraper", bg=BG, fg="#b45309", font=(FONT_UI, 16)).pack(
            side="left", padx=28
        )
        w._count = CL(top, text="", bg=BG, fg=MUT)
        w._count.pack(side="right", padx=24)
        CL(
            w,
            text="Sites CARRIÈRE d'entreprises (les sites d'offres généraux type LinkedIn/WTJ/Indeed "
            "sont dans « Sites d'offres »). Clic sur la colonne Lien = ouvre le site.",
            bg=BG,
            fg=MUT,
            font=(FONT_UI, 13),
            anchor="w",
            justify="left",
        ).pack(fill="x", padx=28)
        cols = ("ent", "dom", "type", "offres", "ats", "url")
        tv = ttk.Treeview(w, columns=cols, show="headings", selectmode="browse")
        for k, lbl, wd, anc in (
            ("ent", "Entreprise", 180, "w"),
            ("dom", "Domaine", 95, "w"),
            ("type", "Type", 95, "w"),
            ("offres", "Offres en queue", 95, "center"),
            ("ats", "ATS", 100, "w"),
            ("url", "Lien", 400, "w"),
        ):
            tv.heading(k, text=lbl)
            tv.column(k, width=wd, anchor=anc, stretch=(k == "url"))
        tv.pack(fill="both", expand=True, padx=28, pady=18)
        tv.tag_configure("odd", background=ROW1)
        tv.tag_configure("even", background=ROW0)

        def company_name(u):
            host = urlparse(u).netloc.lower()
            for p in (
                "careers.",
                "jobs.",
                "recrutement.",
                "talents.",
                "career.",
                "www.",
                "rejoindre-",
                "group.",
            ):
                host = host.replace(p, "")
            return host.split(".")[0].replace("-", " ").title()

        def site_type(u):
            h = urlparse(u).netloc.lower()
            return (
                "carrières"
                if any(
                    h.startswith(p)
                    for p in ("careers.", "jobs.", "recrutement.", "talents.", "career.")
                )
                or any(
                    s in u.lower()
                    for s in ("/careers", "/carriere", "/recrutement", "/nous-rejoindre")
                )
                else "corporate"
            )

        def ats_of(u):
            for a in (
                "smartrecruiters",
                "talent-soft",
                "talentsoft",
                "workday",
                "breezy",
                "greenhouse",
                "lever.co",
                "recruitee",
                "ashby",
                "icims",
                "successfactors",
                "teamtailor",
            ):
                if a in u.lower():
                    return a.split(".")[0]
            return "—"

        def offers_stats(u):
            """(nb offres en queue, domaine majoritaire) pour ce site."""
            root_d = urlparse(u).netloc.lower().replace("www.", "")
            core = root_d.split(".")[-2] if "." in root_d else root_d  # axa-im.com -> axa-im
            n = 0
            doms = {}
            for o in self.offers:
                ou = (o.get("url") or "").lower()
                if core and core in ou:
                    n += 1
                    d = DOM_SHORT.get(o.get("domaine"), o.get("domaine") or "")
                    if d:
                        doms[d] = doms.get(d, 0) + 1
            dom = max(doms, key=doms.get) if doms else "—"
            return n, dom

        def reload():
            for r in tv.get_children():
                tv.delete(r)
            _, urls = self._domains_file()
            ents = [u for u in urls if not self._is_board(u)]
            for i, u in enumerate(sorted(ents, key=company_name)):
                n, dom = offers_stats(u)
                tv.insert(
                    "",
                    "end",
                    values=(company_name(u), dom, site_type(u), n, ats_of(u), u),
                    tags=("odd" if i % 2 else "even",),
                )
            w._count.configure(
                text=f"{len(ents)} entreprises · {sum(1 for u in urls if self._is_board(u))} boards (→ Sites d'offres)"
            )

        w._reload = reload

        def click(e):
            if tv.identify_region(e.x, e.y) != "cell":
                return
            if tv.identify_column(e.x) != "#6":
                return
            it = tv.identify_row(e.y)
            if it:
                webbrowser.open(tv.item(it)["values"][5])
                self._log(f"🌐 {tv.item(it)['values'][5][:70]}\n")

        tv.bind("<Button-1>", click)

        bar = CF(w, bg=BG)
        bar.pack(fill="x", padx=28, pady=(0, 10))
        ent = CE(bar, bg=ROW0, fg=TX, insertbackground=TX, relief="flat", width=60)
        ent.pack(side="left", ipady=4, fill="x", expand=True)

        def add():
            v = ent.get().strip()
            if not v.startswith("http"):
                self._log("✗ URL http requise (site carrière de l'entreprise)\n")
                return
            if self._is_board(v):
                self._log("↪ c'est un site d'offres général → ajoute-le dans « Sites d'offres »\n")
                return
            F, urls = self._domains_file()
            if v in urls:
                self._log("déjà présent\n")
                return
            F.write_text(("\n".join(urls + [v])).strip() + "\n", encoding="utf-8")
            self._log(f"＋ entreprise ajoutée : {v}\n")
            reload()

        def dele():
            it = tv.focus()
            if not it:
                return
            v = tv.item(it)["values"][5]
            F, urls = self._domains_file()
            F.write_text("\n".join(u for u in urls if u != v).strip() + "\n", encoding="utf-8")
            self._log(f"－ retiré : {v}\n")
            reload()

        ent.bind("<Return>", lambda e: add())
        CB(
            bar,
            text="Ajouter",
            command=add,
            bg=ACC,
            fg=ACC_TX,
            activebackground=ACC_H,
            relief="flat",
            cursor="hand2",
        ).pack(side="left", padx=18)
        CB(
            bar,
            text="Retirer",
            command=dele,
            bg=DEL,
            fg=DEL_TX,
            activebackground=DEL_H,
            relief="flat",
            cursor="hand2",
        ).pack(side="left", padx=6)
        CB(
            bar,
            text="Scraper ces sites",
            command=lambda: self.run_step(
                [PY, "scrape_jobs.py", "--headless"], "Scrape sites entreprises"
            ),
            bg=ACC,
            fg=ACC_TX,
            relief="flat",
            cursor="hand2",
        ).pack(side="left", padx=28)
        reload()
        w.pack(fill="both", expand=True)

    def _sources_panel(self):
        """Sources du Scan offres (job_sources) : mots-clés + slugs ATS. sources_config.json."""
        CFG = SCRIPTS / "sources_config.json"

        def _cfg():
            try:
                return json.loads(CFG.read_text(encoding="utf-8"))
            except Exception:
                # seed depuis les défauts du module
                sys.path.insert(0, str(SCRIPTS))
                try:
                    import job_sources as js

                    return {"keywords": list(js.KEYWORDS), "ats_slugs": dict(js.ATS_SLUGS)}
                except Exception:
                    return {"keywords": [], "ats_slugs": {}}

        def _save(c):
            CFG.write_text(json.dumps(c, ensure_ascii=False, indent=1), encoding="utf-8")

        def add(v):
            if ":" not in v:
                return (
                    "✗ format « kw: mots clés » (recherche LinkedIn/WTJ), "
                    "« greenhouse|lever|ashby|recruitee|smartrecruiters: slug » (API ATS) "
                    "ou « board: https://… » (site d'offres scanné par le Scrape)"
                )
            kind, val = [s.strip() for s in v.split(":", 1)]
            c = _cfg()
            if kind == "kw":
                if val not in c.setdefault("keywords", []):
                    c["keywords"].append(val)
            elif kind in ("greenhouse", "lever", "ashby", "recruitee", "smartrecruiters"):
                if val not in c.setdefault("ats_slugs", {}).setdefault(kind, []):
                    c["ats_slugs"][kind].append(val)
            elif kind == "board":
                if not val.startswith("http"):
                    return "✗ board: URL http requise"
                F, urls = self._domains_file()
                if val in urls:
                    return "déjà présent"
                F.write_text(("\n".join(urls + [val])).strip() + "\n", encoding="utf-8")
                return f"＋ board ajouté : {val}"
            else:
                return f"✗ type inconnu « {kind} »"
            _save(c)

        def dele(v):
            if ":" not in v:
                return
            kind, val = [s.strip() for s in v.split(":", 1)]
            if kind == "board":
                F, urls = self._domains_file()
                F.write_text(
                    "\n".join(u for u in urls if u != val).strip() + "\n", encoding="utf-8"
                )
                return
            c = _cfg()
            if kind == "kw" and val in c.get("keywords", []):
                c["keywords"].remove(val)
            elif val in c.get("ats_slugs", {}).get(kind, []):
                c["ats_slugs"][kind].remove(val)
            _save(c)

        # ── tableau à colonnes : Type | Source | Offres trouvées | 🔗 Lien ──
        self._hide_all()
        if "sources" in self._panels:
            w = self._panels["sources"]
            w._reload()
            w.pack(fill="both", expand=True)
            return
        w = CF(self.main, bg=WORK)
        self._panels["sources"] = w
        top = CF(w, bg=BG)
        top.pack(fill="x")
        CB(
            top,
            text="Offres",
            command=self._show_dash,
            bg=BTN,
            fg=MUT,
            relief="flat",
            cursor="hand2",
            font=(FONT_UI, 13),
        ).pack(side="left", padx=12, pady=(2, 0))
        CL(top, text="Sites d'offres généraux", bg=BG, fg="#b45309", font=(FONT_UI, 16)).pack(
            side="left", padx=28
        )
        w._count = CL(top, text="", bg=BG, fg=MUT)
        w._count.pack(side="right", padx=24)
        CL(
            w,
            text="Sources du Scan : « kw: … » = recherche LinkedIn public + WTJ ·"
            "« greenhouse|lever|ashby|recruitee|smartrecruiters: slug » = API ATS · "
            "« board: https://… » = site scanné par « Scrape les sites ». Clic sur Lien = ouvre.",
            bg=BG,
            fg=MUT,
            font=(FONT_UI, 13),
            anchor="w",
            justify="left",
        ).pack(fill="x", padx=28)
        tv = ttk.Treeview(
            w, columns=("type", "src", "offres", "url"), show="headings", selectmode="browse"
        )
        for k, lbl, wd, anc in (
            ("type", "Type", 120, "w"),
            ("src", "Source", 260, "w"),
            ("offres", "Offres en queue", 100, "center"),
            ("url", "Lien", 420, "w"),
        ):
            tv.heading(k, text=lbl)
            tv.column(k, width=wd, anchor=anc, stretch=(k == "url"))
        tv.pack(fill="both", expand=True, padx=28, pady=18)
        tv.tag_configure("odd", background=ROW1)
        tv.tag_configure("even", background=ROW0)

        ATS_URL = {
            "greenhouse": "https://boards.greenhouse.io/{s}",
            "lever": "https://jobs.lever.co/{s}",
            "ashby": "https://jobs.ashbyhq.com/{s}",
            "recruitee": "https://{s}.recruitee.com",
            "smartrecruiters": "https://careers.smartrecruiters.com/{s}",
        }

        def n_src(needle):
            return sum(1 for o in self.offers if needle in (o.get("source") or "").lower())

        def rows():
            c = _cfg()
            out = []
            for k in c.get("keywords", []):
                n = n_src(f"linkedin-search:{k}".lower()) + n_src(f"wtj-search:{k}".lower())
                out.append(
                    ("kw", k, n, "https://www.linkedin.com/jobs/search?keywords=" + quote(k))
                )
            for kind, slugs in c.get("ats_slugs", {}).items():
                for s in slugs:
                    out.append(
                        (
                            kind,
                            s,
                            n_src(f"{kind}:{s}".lower()),
                            ATS_URL.get(kind, "{s}").format(s=s),
                        )
                    )
            _, urls = self._domains_file()
            for u in urls:
                if self._is_board(u):
                    host = urlparse(u).netloc.replace("www.", "")
                    n = sum(1 for o in self.offers if host and host in (o.get("url") or ""))
                    out.append(("board", host, n, u))
            return out

        def reload():
            for r in tv.get_children():
                tv.delete(r)
            rs = rows()
            for i, r in enumerate(rs):
                tv.insert("", "end", values=r, tags=("odd" if i % 2 else "even",))
            w._count.configure(text=f"{len(rs)} sources")

        w._reload = reload

        def click(e):
            if tv.identify_region(e.x, e.y) != "cell" or tv.identify_column(e.x) != "#4":
                return
            it = tv.identify_row(e.y)
            if it:
                webbrowser.open(tv.item(it)["values"][3])
                self._log(f"🌐 {str(tv.item(it)['values'][3])[:70]}\n")

        tv.bind("<Button-1>", click)

        bar = CF(w, bg=BG)
        bar.pack(fill="x", padx=28, pady=(0, 10))
        ent = CE(bar, bg=ROW0, fg=TX, insertbackground=TX, relief="flat", width=60)
        ent.pack(side="left", ipady=4, fill="x", expand=True)

        def do_add():
            msg = add(ent.get().strip())
            self._log((msg or f"＋ ajouté : {ent.get().strip()}") + "\n")
            ent.delete(0, "end")
            reload()

        def do_del():
            it = tv.focus()
            if not it:
                return
            t, s, _n, u = tv.item(it)["values"]
            dele(f"{t}: {u if t == 'board' else s}")
            self._log(f"－ retiré : {t}: {s}\n")
            reload()

        ent.bind("<Return>", lambda e: do_add())
        CB(
            bar,
            text="Ajouter",
            command=do_add,
            bg=ACC,
            fg=ACC_TX,
            activebackground=ACC_H,
            relief="flat",
            cursor="hand2",
        ).pack(side="left", padx=18)
        CB(
            bar,
            text="Retirer",
            command=do_del,
            bg=DEL,
            fg=DEL_TX,
            activebackground=DEL_H,
            relief="flat",
            cursor="hand2",
        ).pack(side="left", padx=6)
        CB(
            bar,
            text="Scanner maintenant",
            command=lambda: self.run_step([PY, "job_sources.py", "--all"], "Scan offres"),
            bg=ACC,
            fg=ACC_TX,
            relief="flat",
            cursor="hand2",
        ).pack(side="left", padx=28)
        reload()
        w.pack(fill="both", expand=True)

    def _add_offer_url(self):
        """Analyse le lien collé (add_offer.py) : titre+entreprise+description → queue → CV/lettre."""
        url = self.e_url.get().strip()
        if not url.startswith("http"):
            self._log("✗ colle une URL http d'offre.\n")
            return
        self.b_addurl.configure(text="Analyse…", state="disabled")
        self._log(f"🔎 analyse de l'offre : {url[:70]}…\n")

        def work():
            try:
                r = subprocess.run(
                    [PY, "add_offer.py", "--url", url],
                    cwd=str(SCRIPTS),
                    capture_output=True,
                    text=True,
                    timeout=300,
                    encoding="utf-8",
                    errors="replace",
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                out = (r.stdout or "") + (r.stderr or "")
            except Exception as e:
                out = f"! {type(e).__name__}"
            self.root.after(0, lambda: done(out))

        def done(out):
            for line in out.splitlines():
                if line.strip():
                    self._log("  " + line.strip()[:100] + "\n")
            self.b_addurl.configure(text="Ajouter une offre", state="normal")
            self.e_url.delete(0, "end")
            self.load_offers()

        threading.Thread(target=work, daemon=True).start()

    def _detail_full(self, o=None):
        """Détails PLEIN ÉCRAN, fenêtre COUPÉE EN DEUX : infos offre à GAUCHE,
        CV / lettre liés à DROITE (aperçu PDF ou docx ÉDITABLE + 💾)."""
        o = o or self._cur
        if not o:
            self._log("Sélectionne d'abord une offre.\n")
            return
        self._dispo_memo()  # « ↶ Retour » ramene au tableau tel qu'il etait
        self._hide_all()
        if self._dv is None:
            self._dv = CF(self.main, bg=WORK)
        for c in self._dv.winfo_children():  # reconstruit par offre
            c.destroy()
        w = self._dv
        top = CF(w, bg=BG)
        top.pack(fill="x")
        CB(
            top,
            text="Offres",
            command=self._show_dash,
            bg=BTN,
            fg=MUT,
            relief="flat",
            cursor="hand2",
            font=(FONT_UI, 13),
        ).pack(side="left", padx=12, pady=(2, 0))
        CL(
            top,
            text=f"{o.get('entreprise', '')} — {o.get('poste', '')[:70]}",
            bg=BG,
            fg="#b45309",
            font=(FONT_UI, 16),
        ).pack(side="left", padx=28)

        body = tk.PanedWindow(w, orient="horizontal", bg=LINE, sashwidth=5, bd=0)
        body.pack(fill="both", expand=True, padx=24, pady=(4, 4))

        # ── GAUCHE : infos de l'offre + actions ──
        left = CF(body, bg=BG)
        dtxt = scrolledtext.ScrolledText(
            left,
            bg=ROW0,
            fg=TX,
            insertbackground=TX,
            font=(FONT_UI, 13),
            relief="flat",
            wrap="word",
            padx=14,
            pady=10,
            state="disabled",
        )
        dtxt.tag_configure("k", foreground=ACC, font=(FONT_UI, 13))
        dtxt.tag_configure("h", foreground="#b45309", font=(FONT_UI, 16))
        dtxt.pack(fill="both", expand=True)
        lbt = CF(left, bg=BG)
        lbt.pack(fill="x", pady=(4, 0))
        CB(
            lbt,
            text="Envoi confirmé",
            command=lambda: (self._postuler(o), self._fill_detail(dtxt, o)),
            bg=ACC,
            fg=ACC_TX,
            activebackground=ACC_H,
            relief="flat",
            cursor="hand2",
        ).pack(side="left")
        CB(
            lbt,
            text="Ouvrir l'offre",
            command=lambda: self._open_offer(o),
            bg=BTN,
            fg=TX,
            activebackground=BTN_H,
            relief="flat",
            cursor="hand2",
        ).pack(side="left", padx=12)
        bd = CB(
            lbt,
            text="Description",
            bg=BTN,
            fg=TX,
            activebackground=BTN_H,
            relief="flat",
            cursor="hand2",
        )
        bd.configure(command=lambda: self._fetch_desc(o, dtxt, bd))
        bd.pack(side="left", padx=12)
        self._fill_detail(dtxt, o)
        body.add(left, minsize=320)

        # ── DROITE : CV / lettre liés (PDF aperçu ; lettre docx = ÉDITABLE) ──
        right = CF(body, bg=BG)
        rbar = CF(right, bg=BG)
        rbar.pack(fill="x")
        rinfo = CL(right, text="", bg=BG, fg=MUT, font=(FONT_UI, 12), anchor="w")
        rinfo.pack(fill="x")
        holder = CF(right, bg=BG)
        holder.pack(fill="both", expand=True)
        rcv = tk.Canvas(holder, bg="#f8fafc", highlightthickness=0)
        rsb = tk.Scrollbar(holder, command=rcv.yview)
        rcv.configure(yscrollcommand=rsb.set)
        rtxt = scrolledtext.ScrolledText(
            holder,
            bg="#f8fafc",
            fg=TX,
            insertbackground=TX,
            font=(FONT_UI, 13),
            relief="flat",
            wrap="word",
            padx=14,
            pady=10,
        )
        st = {"path": None, "imgs": []}

        def surface(kind):
            rcv.pack_forget()
            rsb.pack_forget()
            rtxt.pack_forget()
            if kind == "pdf":
                rsb.pack(side="right", fill="y")
                rcv.pack(side="left", fill="both", expand=True)
            else:
                rtxt.pack(fill="both", expand=True)

        def load(path):
            """Charge le doc à droite. Lettre .docx → texte ÉDITABLE ; sinon PDF empilé."""
            # pour l'édition : préfère le .docx jumeau des lettres
            if (
                path.suffix.lower() == ".pdf"
                and LETTRES_DIR in path.parents
                and path.with_suffix(".docx").exists()
            ):
                path = path.with_suffix(".docx")
            st["path"] = path
            if path.suffix.lower() == ".pdf":
                try:
                    import base64

                    import fitz

                    doc = fitz.open(str(path))
                    surface("pdf")
                    rcv.delete("all")
                    st["imgs"].clear()
                    y = 8
                    for i in range(doc.page_count):
                        pix = doc[i].get_pixmap(matrix=fitz.Matrix(1.25, 1.25))
                        img = tk.PhotoImage(data=base64.b64encode(pix.tobytes("png")))
                        st["imgs"].append(img)
                        rcv.create_image(
                            max(rcv.winfo_width() // 2, pix.width // 2 + 8),
                            y,
                            image=img,
                            anchor="n",
                        )
                        y += pix.height + 12
                    rcv.configure(scrollregion=(0, 0, rcv.winfo_width(), y))
                    rinfo.configure(
                        text=f"{path.name} · {doc.page_count} p. · lecture (PDF) — molette pour dérouler"
                    )
                    doc.close()  # libère le fichier (images déjà rendues)
                except Exception as ex:
                    surface("txt")
                    rtxt.delete("1.0", "end")
                    rtxt.insert("end", f"aperçu KO: {type(ex).__name__}")
                return
            surface("txt")
            rtxt.delete("1.0", "end")
            try:
                if path.suffix.lower() == ".docx":
                    from docx import Document

                    rtxt.insert("end", "\n".join(p.text for p in Document(str(path)).paragraphs))
                else:
                    rtxt.insert("end", path.read_text(encoding="utf-8", errors="replace"))
                editable = (path.suffix.lower() == ".txt") or (LETTRES_DIR in path.parents)
                rinfo.configure(
                    text=f"{path.name} · "
                    + (
                        "✏ ÉDITABLE — modifie puis 💾 (PDF resynchronisé)"
                        if editable
                        else "lecture seule (CV : 📂 Ouvrir → Word)"
                    )
                )
            except Exception as ex:
                rtxt.insert("end", f"lecture KO: {type(ex).__name__}")

        def save_doc():
            p = st["path"]
            if not p:
                return
            ext = p.suffix.lower()
            if not ((ext == ".txt") or (ext == ".docx" and LETTRES_DIR in p.parents)):
                self._log("✗ édition réservée aux lettres/.txt — CV : 📂 Ouvrir (Word)\n")
                return
            txt = rtxt.get("1.0", "end").rstrip("\n")
            try:
                if ext == ".txt":
                    p.write_text(txt, encoding="utf-8")
                else:
                    from docx import Document
                    from docx.enum.text import WD_ALIGN_PARAGRAPH
                    from docx.oxml.ns import qn

                    doc = Document(str(p))
                    lines = txt.split("\n")
                    paras = doc.paragraphs
                    if len(lines) == len(paras):
                        for para, line in zip(paras, lines):
                            if para.text != line:
                                for r in para.runs:
                                    r.text = ""
                                (para.runs[0] if para.runs else para.add_run("")).text = line
                    else:
                        for para in list(paras):
                            para._element.getparent().remove(para._element)
                        for line in lines:
                            np = doc.add_paragraph(line)
                            if len(line.strip()) > 90:
                                np.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                    s = doc.settings.element
                    if s.find(qn("w:autoHyphenation")) is None:
                        s.append(s.makeelement(qn("w:autoHyphenation"), {qn("w:val"): "true"}))
                    doc.save(str(p))
                self._log(f"💾 enregistré : {p.name}\n")
            except Exception as ex:
                self._log(f"! sauvegarde KO: {type(ex).__name__}\n")
                return
            tw = p.with_suffix(".pdf")
            if ext == ".docx" and tw.exists():

                def regen():
                    for exe in (
                        r"C:\Program Files\LibreOffice\program\soffice.exe",
                        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
                    ):
                        if Path(exe).exists():
                            try:
                                subprocess.run(
                                    [
                                        exe,
                                        "--headless",
                                        "--convert-to",
                                        "pdf",
                                        "--outdir",
                                        str(p.parent),
                                        str(p),
                                    ],
                                    capture_output=True,
                                    timeout=90,
                                )
                                self.root.after(
                                    0, lambda: self._log(f"📄 PDF resynchronisé : {tw.name}\n")
                                )
                            except Exception:
                                pass
                            return

                threading.Thread(target=regen, daemon=True).start()

        rcv.bind("<MouseWheel>", lambda e: rcv.yview_scroll(-1 if e.delta > 0 else 1, "units"))
        cvp, ltp = self._cv_of(o), self._lettre_of(o)
        if cvp:
            CB(
                rbar,
                text="CV",
                command=lambda: load(cvp),
                bg=BTN,
                fg=TX,
                relief="flat",
                cursor="hand2",
            ).pack(side="left", padx=(0, 2))
        if ltp:
            CB(
                rbar,
                text="Lettre",
                command=lambda: load(ltp),
                bg=BTN,
                fg=TX,
                relief="flat",
                cursor="hand2",
            ).pack(side="left", padx=6)
        CB(
            rbar,
            text="Enregistrer",
            command=save_doc,
            bg=BTN,
            fg=TX,
            activebackground=BTN_H,
            relief="flat",
            cursor="hand2",
        ).pack(side="left", padx=24)
        CB(
            rbar,
            text="Ouvrir",
            command=lambda: st["path"] and os.startfile(str(st["path"])),
            bg=BTN,
            fg=TX,
            relief="flat",
            cursor="hand2",
        ).pack(side="left", padx=6)
        if not (cvp or ltp):
            rinfo.configure(text="aucun CV/lettre lié à cette offre")
        body.add(right, minsize=380)
        # ouvre la LETTRE par défaut (éditable), sinon le CV
        if ltp:
            load(ltp)
        elif cvp:
            load(cvp)
        self._dv.pack(fill="both", expand=True)

    def _cv_viewer(self, preselect=None):
        self._hide_all()
        if self.viewer is not None:  # déjà construit → réaffiche
            self.viewer.pack(fill="both", expand=True)
            if preselect:
                p = Path(preselect)
                if p.exists():
                    self._viewer_show(p)
            return
        self.viewer = w = CF(self.main, bg=WORK)
        w.pack(fill="both", expand=True)
        top = CF(w, bg=BG)
        top.pack(fill="x")
        CB(
            top,
            text="Offres",
            command=self._show_dash,
            bg=BTN,
            fg=MUT,
            relief="flat",
            cursor="hand2",
            font=(FONT_UI, 13),
        ).pack(side="left", padx=12, pady=(2, 0))
        left = CF(w, bg=CARD, width=340)
        left.pack(side="left", fill="y", padx=(8, 4), pady=8)
        left.pack_propagate(False)
        right = CF(w, bg=BG)
        right.pack(side="left", fill="both", expand=True, padx=(4, 8), pady=8)

        CL(left, text="Recherche (CV par offre + lettres)", bg=CARD, fg=MUT).pack(
            anchor="w", padx=24, pady=(8, 0)
        )
        srch = CE(left, bg=ROW0, fg=TX, insertbackground=TX, relief="flat")
        srch.pack(fill="x", padx=24, ipady=3)
        lb = tk.Listbox(
            left,
            bg=ROW0,
            fg=TX,
            relief="flat",
            exportselection=False,
            font=(FONT_UI, 13),
            selectbackground=BTN_H,
        )
        sb = ttk.Scrollbar(left, command=lb.yview)
        lb.configure(yscrollcommand=sb.set)
        lb.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=8)
        sb.pack(side="right", fill="y", pady=24)

        def _letters(flt=""):
            """Lettres : préfère le .DOCX (ÉDITABLE dans le panneau) — le pdf suit via sync."""
            if not LETTRES_DIR.exists():
                return []
            by_stem = {}
            for f in LETTRES_DIR.iterdir():
                if f.suffix.lower() not in (".pdf", ".docx"):
                    continue
                if flt and flt not in f.name.lower():
                    continue
                cur = by_stem.get(f.stem)
                if cur is None or f.suffix.lower() == ".docx":
                    by_stem[f.stem] = f
            return sorted(by_stem.values(), key=lambda f: f.name.lower())

        files = []  # aligné avec lb

        def fill(flt=""):
            lb.delete(0, "end")
            files.clear()
            ats = sorted(CV_ATS_DIR.glob("*.pdf")) if CV_ATS_DIR.exists() else []
            if ats:
                lb.insert("end", "── CV ATS (5 variantes) ──")
                files.append(None)
                for f in ats:
                    lb.insert("end", "  " + f.stem.replace(f"CV_{_PREFIXE}_", "").replace("_", " "))
                    files.append(f)
            per = sorted(CV_OFFRE_DIR.glob("*.pdf")) if CV_OFFRE_DIR.exists() else []
            if flt:
                per = [f for f in per if flt in f.name.lower()]
            lb.insert("end", f"── CV par offre ({len(per)}) ──")
            files.append(None)
            for f in per[:250]:
                lb.insert(
                    "end",
                    "  " + f.stem.replace("CV_", "").replace(f"{_PREFIXE}_", "").replace("_", " "),
                )
                files.append(f)
            lets = _letters(flt)
            lb.insert("end", f"── Lettres ({len(lets)}) ──")
            files.append(None)
            for f in lets[:250]:
                lb.insert(
                    "end",
                    "  "
                    + f.stem.replace("_cover_letter", "")
                    .replace(f"{_PREFIXE}_", "")
                    .replace("_", " "),
                )
                files.append(f)

        fill()
        srch.bind("<KeyRelease>", lambda e: fill(srch.get().strip().lower()))

        # barre titre + infos
        bar = CF(right, bg=BG)
        bar.pack(fill="x")
        title = CL(
            bar,
            text="Sélectionne un CV ou une lettre à gauche",
            bg=BG,
            fg=TX,
            font=(FONT_UI, 13),
            anchor="w",
        )
        title.pack(side="left", padx=12)
        pginfo = CL(bar, text="", bg=BG, fg=MUT)
        pginfo.pack(side="right", padx=12)

        # deux surfaces d'aperçu : canvas (PDF, scrollable) / texte (docx-txt, scrollable)
        state = {"doc": None, "path": None, "imgs": [], "zoom": 1.4}
        holder = CF(right, bg=BG)
        holder.pack(fill="both", expand=True, pady=(4, 4))
        cv_canvas = tk.Canvas(holder, bg="#f8fafc", highlightthickness=0)
        vsb = tk.Scrollbar(holder, command=cv_canvas.yview)
        cv_canvas.configure(yscrollcommand=vsb.set)
        txtv = scrolledtext.ScrolledText(
            holder,
            bg="#f8fafc",
            fg=TX,
            font=(FONT_UI, 13),
            relief="flat",
            wrap="word",
            padx=14,
            pady=10,
        )

        def show_surface(kind):
            cv_canvas.pack_forget()
            vsb.pack_forget()
            txtv.pack_forget()
            if kind == "pdf":
                vsb.pack(side="right", fill="y")
                cv_canvas.pack(side="left", fill="both", expand=True)
            else:
                txtv.pack(fill="both", expand=True)

        def render():
            """Rend TOUTES les pages empilées → molette déroule le document en entier."""
            doc = state["doc"]
            if not doc:
                return
            import base64

            import fitz

            try:
                cv_canvas.delete("all")
                state["imgs"].clear()
                y, wmax = 8, 0
                for i in range(doc.page_count):
                    pix = doc[i].get_pixmap(matrix=fitz.Matrix(state["zoom"], state["zoom"]))
                    img = tk.PhotoImage(data=base64.b64encode(pix.tobytes("png")))
                    state["imgs"].append(img)  # refs anti-GC
                    cw = max(cv_canvas.winfo_width(), pix.width + 16)
                    cv_canvas.create_image(cw // 2, y, image=img, anchor="n")
                    y += pix.height + 12
                    wmax = max(wmax, pix.width)
                cv_canvas.configure(scrollregion=(0, 0, wmax + 16, y))
                pginfo.configure(
                    text=f"{doc.page_count} page(s) · zoom {state['zoom']:.1f} · molette = dérouler"
                )
            except Exception as ex:
                cv_canvas.delete("all")
                cv_canvas.create_text(
                    20, 20, text=f"aperçu KO: {type(ex).__name__}", fill="#dc2626", anchor="nw"
                )

        def show(path):
            # ferme le doc PDF précédent (sinon fichier verrouillé → regen LibreOffice impossible)
            if state.get("doc") is not None:
                try:
                    state["doc"].close()
                except Exception:
                    pass
                state["doc"] = None
            state["path"] = path
            title.configure(text=path.name)
            ext = path.suffix.lower()
            if ext == ".pdf":
                try:
                    import fitz

                    state["doc"] = fitz.open(str(path))
                    show_surface("pdf")
                    render()
                except Exception as ex:
                    show_surface("txt")
                    txtv.delete("1.0", "end")
                    txtv.insert("end", f"lecture KO: {type(ex).__name__}")
                return
            # DOCX / TXT → texte complet scrollable
            state["doc"] = None
            show_surface("txt")
            txtv.delete("1.0", "end")
            try:
                if ext == ".docx":
                    from docx import Document

                    txt = "\n".join(p.text for p in Document(str(path)).paragraphs)
                else:
                    txt = path.read_text(encoding="utf-8", errors="replace")
                txtv.insert("end", txt or "(document vide)")
                editable = (ext == ".txt") or (LETTRES_DIR in path.parents)
                pginfo.configure(
                    text=f"{len(txt)} car. · "
                    + (
                        "✏ ÉDITABLE — modifie puis 💾 Enregistrer"
                        if editable
                        else "lecture seule (CV : 📂 Ouvrir → Word)"
                    )
                )
            except Exception as ex:
                txtv.insert(
                    "end", f"lecture KO: {type(ex).__name__} — clique « Ouvrir » pour Word."
                )

        def on_sel(e=None):
            c = lb.curselection()
            if c and files[c[0]] is not None:
                show(files[c[0]])

        lb.bind("<<ListboxSelect>>", on_sel)

        # ── ÉDITION intégrée : lettres (.docx) + .txt. CV .docx = mise en page complexe → Word.
        def save_doc():
            p = state["path"]
            if not p:
                return
            ext = p.suffix.lower()
            editable = (ext == ".txt") or (ext == ".docx" and LETTRES_DIR in p.parents)
            if not editable:
                self._log(
                    "✗ édition intégrée réservée aux lettres/.txt — CV .docx : bouton 📂 Ouvrir (Word)\n"
                )
                return
            txt = txtv.get("1.0", "end").rstrip("\n")
            try:
                if ext == ".txt":
                    p.write_text(txt, encoding="utf-8")
                else:
                    from docx import Document
                    from docx.enum.text import WD_ALIGN_PARAGRAPH
                    from docx.oxml.ns import qn

                    doc = Document(str(p))
                    lines = txt.split("\n")
                    paras = doc.paragraphs
                    if len(lines) == len(paras):
                        # 1 ligne = 1 paragraphe → in-place (styles conservés)
                        for para, line in zip(paras, lines):
                            if para.text != line:
                                for r in para.runs:
                                    r.text = ""
                                (para.runs[0] if para.runs else para.add_run("")).text = line
                    else:
                        # structure changée → reconstruit (lettre = layout simple)
                        for para in list(paras):
                            para._element.getparent().remove(para._element)
                        for line in lines:
                            np = doc.add_paragraph(line)
                            if len(line.strip()) > 90:
                                np.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                    s = doc.settings.element  # césure auto (justifié sans trous)
                    if s.find(qn("w:autoHyphenation")) is None:
                        s.append(s.makeelement(qn("w:autoHyphenation"), {qn("w:val"): "true"}))
                    doc.save(str(p))
                self._log(f"💾 enregistré : {p.name}\n")
            except Exception as ex:
                self._log(f"! sauvegarde KO: {type(ex).__name__}\n")
                return
            # PDF jumeau régénéré en fond (LibreOffice) pour rester synchro
            tw = p.with_suffix(".pdf")
            if ext == ".docx" and tw.exists():

                def regen():
                    for exe in (
                        r"C:\Program Files\LibreOffice\program\soffice.exe",
                        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
                    ):
                        if Path(exe).exists():
                            try:
                                subprocess.run(
                                    [
                                        exe,
                                        "--headless",
                                        "--convert-to",
                                        "pdf",
                                        "--outdir",
                                        str(p.parent),
                                        str(p),
                                    ],
                                    capture_output=True,
                                    timeout=90,
                                )
                                self.root.after(
                                    0, lambda: self._log(f"📄 PDF resynchronisé : {tw.name}\n")
                                )
                            except Exception:
                                pass
                            return

                threading.Thread(target=regen, daemon=True).start()

        def zoom(d):
            state["zoom"] = max(0.6, min(3.0, state["zoom"] + d))
            render()

        def _wheel(e):
            cv_canvas.yview_scroll(-1 if e.delta > 0 else 1, "units")

        cv_canvas.bind("<MouseWheel>", _wheel)
        cv_canvas.bind("<Enter>", lambda e: cv_canvas.focus_set())

        bt = CF(right, bg=BG)
        bt.pack(fill="x")
        for txt_, cmd in [
            ("↑ Haut", lambda: cv_canvas.yview_moveto(0)),
            ("↓ Bas", lambda: cv_canvas.yview_moveto(1)),
            ("－", lambda: zoom(-0.2)),
            ("＋", lambda: zoom(0.2)),
        ]:
            CB(bt, text=txt_, command=cmd, bg=BTN, fg=TX, relief="flat", cursor="hand2").pack(
                side="left", padx=6
            )
        CB(
            bt,
            text="Enregistrer",
            command=save_doc,
            bg=BTN,
            fg=TX,
            activebackground=BTN_H,
            relief="flat",
            cursor="hand2",
        ).pack(side="left", padx=24)
        CB(
            bt,
            text="Ouvrir",
            command=lambda: state["path"] and os.startfile(str(state["path"])),
            bg=ACC,
            fg=ACC_TX,
            relief="flat",
            cursor="hand2",
        ).pack(side="left", padx=6)
        CB(
            bt,
            text="CV",
            command=lambda: os.startfile(str(CV_ATS_DIR.parent)),
            bg=BTN,
            fg=TX,
            relief="flat",
            cursor="hand2",
        ).pack(side="left", padx=6)
        CB(
            bt,
            text="Lettres",
            command=lambda: LETTRES_DIR.exists() and os.startfile(str(LETTRES_DIR)),
            bg=BTN,
            fg=TX,
            relief="flat",
            cursor="hand2",
        ).pack(side="left", padx=6)

        # outils de masse : MAJ date/ordre/destinataire des lettres · renommage à mon nom
        def _tool(script, label, btn):
            btn.configure(state="disabled", text="En cours : " + label)

            def work():
                try:
                    r = subprocess.run(
                        [PY, script],
                        cwd=str(SCRIPTS),
                        capture_output=True,
                        text=True,
                        timeout=1800,
                        encoding="utf-8",
                        errors="replace",
                        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                    )
                    out = ((r.stdout or "") + (r.stderr or "")).strip().splitlines()
                    msg = out[-1][:90] if out else "fini"
                except Exception as e:
                    msg = f"! {type(e).__name__}"

                def done():
                    btn.configure(state="normal", text=label)
                    self._log(f"✅ {label}: {msg}\n")
                    fill(srch.get().strip().lower())
                    self.load_offers()

                self.root.after(0, done)

            threading.Thread(target=work, daemon=True).start()

        b_maj = CB(
            bt,
            text="MAJ lettres",
            bg=BTN,
            fg=TX,
            activebackground=BTN_H,
            relief="flat",
            cursor="hand2",
        )
        b_maj.configure(command=lambda: _tool("refresh_letters.py", "🗓 MAJ lettres", b_maj))
        b_maj.pack(side="left", padx=(10, 2))
        b_ren = CB(bt, text="Renommer (mon nom)", bg=BTN, fg=TX, relief="flat", cursor="hand2")
        b_ren.configure(command=lambda: _tool("rename_docs.py", "📛 Renommer (mon nom)", b_ren))
        b_ren.pack(side="left", padx=6)
        CB(bt, text="Retour", command=self._show_dash, bg=BTN, fg=TX, relief="flat").pack(
            side="right", padx=6
        )
        cv_canvas.bind("<Prior>", lambda e: cv_canvas.yview_scroll(-1, "pages"))
        cv_canvas.bind("<Next>", lambda e: cv_canvas.yview_scroll(1, "pages"))
        self._viewer_show = show  # réutilisé quand le panneau est réaffiché avec preselect

        def _close_doc():
            if state.get("doc") is not None:
                try:
                    state["doc"].close()
                except Exception:
                    pass
                state["doc"] = None

        self._viewer_close = _close_doc  # appelé par _show_dash (déverrouille le pdf)

        if preselect:
            p = Path(preselect)
            if p.exists():
                show(p)

    def _doc_of(self, o, key):
        """Chemin disque du doc lié à l'offre (cv/lettre, décode file:///…). None si absent."""
        u = o.get(key) or ""
        if not u:
            return None
        p = chemin_de(u)
        return p if p.exists() else None

    def _cv_of(self, o):
        return self._doc_of(o, "cv")

    def _lettre_of(self, o):
        return self._doc_of(o, "lettre")

    # ── UI helpers ──
    def _log(self, txt):
        self.log.insert("end", txt)
        self.log.see("end")
        # Meme repli, le journal doit pouvoir se resumer en un coup d'oeil.
        ligne = next((l.strip() for l in reversed(str(txt).split(chr(10))) if l.strip()), "")
        if ligne and getattr(self, "status", None) is not None:
            self.status.configure(text=ligne[:96])

    # ── exécution ──
    def run_step(self, cmd, label):
        # scripts interactifs OU réutilisant Chrome (--chrome) -> nouvelle console (Chrome visible)
        if any(s in cmd for s in INTERACTIVE) or "--chrome" in cmd:
            self.run_console(cmd, label)
            return
        if self._occupe():
            return
        self._log(f"\n{'=' * 56}\n▶ {label}\n{'=' * 56}\n")
        threading.Thread(target=self._exec, args=(cmd, cmd[-1]), daemon=True).start()

    def _occupe(self):
        """Quelque chose écrit-il déjà la file ? Le dit, et rend True si oui.

        `_bg_busy` couvrait les deux jobs automatiques entre eux, mais PAS les
        boutons : lancer « TOUT FAIRE » pendant que l'auto-enrichissement
        tournait faisait tomber l'un des deux sur le verrou, après avoir
        démarré. Le scan peut durer trente minutes — autant le dire avant.
        """
        if self.proc and self.proc.poll() is None:
            self._log("⏳ tâche en cours.\n")
            return True
        if getattr(self, "_bg_busy", False):
            self._log(
                "⏳ un travail de fond écrit la file (descriptions ou sync docs).\n"
                "   Réessaie dans un instant — il se termine tout seul.\n"
            )
            return True
        return False

    def run_console(self, cmd, label):
        """Lance dans une console dédiée : Chrome visible + prompt clavier (Entrée par offre)."""
        self._log(
            f"\n▶ {label} — fenêtre CONSOLE ouverte. Chrome s'ouvre ; "
            f"tape Entrée après chaque envoi. Ferme la console pour arrêter.\n"
        )
        try:
            subprocess.Popen(
                cmd, cwd=str(SCRIPTS), creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0x10)
            )
        except Exception as e:
            self._log(f"! lancement console KO: {e}\n")

    def run_all(self):
        if self._occupe():
            return
        # Version COURTE du pipeline : six etapes, a la main. La tache planifiee
        # lance pipeline_quotidien.py, qui en fait davantage (collecte en cinq
        # passes fusionnees chacune, sauvegarde, sites carriere, dossiers).
        # L'ancien enchainement s'arretait au re-score : ni descriptions, ni
        # export CSV, ni alerte.
        seq = [
            ("1/6 Scan offres (ATS + LinkedIn + V.I.E)", [PY, "job_sources.py", "--all"]),
            (
                "2/6 Descriptions LinkedIn",
                [PY, "scrape_desc.py", "--all", "--canal", "linkedin", "--limit", "150"],
            ),
            ("3/6 Re-score fit + ATS", [PY, "rescore_ats.py"]),
            ("4/6 Verif liens morts", [PY, "recheck_dead.py", "--status", "OK", "--limit", "120"]),
            ("5/6 Export CSV", [PY, "export_queue_csv.py", "--keep", "8"]),
            ("6/6 Alerte nouveaux matchs", [PY, "notify_matches.py", "--min-fit", "8"]),
        ]
        self._log(f"\n{'=' * 56}\n▶ TOUT FAIRE — pipeline complet (6 etapes)\n{'=' * 56}\n")
        threading.Thread(target=self._exec_seq, args=(seq,), daemon=True).start()

    def mettre_a_jour(self, en_attente=False):
        """mise_a_jour.py dans le journal de l'app, puis propose de relancer
        JobHunter sur la nouvelle version (le code deja charge reste l'ancien).

        Au demarrage, l'annonce arrive souvent pendant un travail de fond (scan
        auto, sync docs) : `_occupe()` refusait alors le « Oui » en silence. On
        attend la fin de ce travail — remplacer les scripts sous un programme qui
        tourne n'est pas une option."""
        if (self.proc and self.proc.poll() is None) or getattr(self, "_bg_busy", False):
            if not en_attente:
                self._log("\n⏳ Mise à jour : elle démarre dès que le travail en cours est fini.\n")
            self.root.after(3000, lambda: self.mettre_a_jour(en_attente=True))
            return
        try:
            import mise_a_jour

            avant = mise_a_jour.version_locale()
        except Exception:
            mise_a_jour, avant = None, "?"
        self._log(f"\n{'=' * 56}\n▶ Mise à jour de JobHunter\n{'=' * 56}\n")

        def tache():
            ok = self._exec([PY, "mise_a_jour.py"], "mise à jour")
            apres = mise_a_jour.version_locale() if mise_a_jour else "?"
            self.q.put(("maj_fin", (ok, avant, apres)))

        threading.Thread(target=tache, daemon=True).start()

    def _apres_mise_a_jour(self, ok, avant, apres):
        if not ok:
            messagebox.showwarning(
                "JobHunter — mise à jour",
                "La mise à jour n'a pas abouti ; le détail est dans "
                "le journal. Tes données n'ont pas été touchées.",
                parent=self.root,
            )
            return
        if apres == avant:
            return  # deja a jour : rien a relancer
        if messagebox.askyesno(
            "JobHunter — mise à jour",
            f"Version {apres} installée. Relancer JobHunter maintenant ?",
            parent=self.root,
        ):
            subprocess.Popen([PY, str(ROOT / "JobHunter.pyw")], cwd=str(ROOT))
            self.root.destroy()

    def _exec_seq(self, seq):
        """seq : liste de (libelle, commande). Le libelle sert au log — cmd[-1]
        affichait le dernier ARGUMENT (« 8 », « linkedin »), pas l'etape."""
        for label, cmd in seq:
            if not self._exec(cmd, label, announce=True):
                break
        self.q.put(("done_all", None))

    def _exec(self, cmd, label, announce=False):
        if announce:
            self.q.put(("line", f"\n--- {label} ---\n"))
        try:
            self.proc = subprocess.Popen(
                cmd,
                cwd=str(SCRIPTS),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except Exception as e:
            self.q.put(("line", f"! lancement KO: {e}\n"))
            return False
        for line in self.proc.stdout:
            self.q.put(("line", line))
        code = self.proc.wait()
        self.q.put(("line", f"[exit {code}]\n"))
        # Code 3 = un autre programme tient le verrou de la queue (jutil.garder).
        # « [exit 3] » seul n'apprend rien : on dit ce qui s'est passe, et surtout
        # que rien n'a ete modifie.
        if code == 3:
            self.q.put(
                (
                    "line",
                    "⚠ Un autre programme ecrit apply_queue.json en ce moment.\n"
                    "  Rien n'a ete touche. Reessaie quand il aura fini.\n",
                )
            )
        self.q.put(("reload", None))
        return code == 0

    # ── journal des pannes ───────────────────────────────────────────────────
    JOURNAL = SCRIPTS / "_logs" / "app_erreurs.log"

    def _journal_panne(self, contexte, exc=None):
        """Range une trace dans _logs/app_erreurs.log et la résume dans l'UI.

        Sans ça, une panne dans un rappel Tk est invisible : `.pyw` n'a pas de
        console, stderr ne va nulle part, et l'app garde l'air vivante.
        """
        import traceback

        trace = traceback.format_exc()
        try:
            self.JOURNAL.parent.mkdir(parents=True, exist_ok=True)
            with open(self.JOURNAL, "a", encoding="utf-8") as f:
                f.write(
                    f"\n{'=' * 60}\n{datetime.datetime.now():%Y-%m-%d %H:%M:%S}  "
                    f"[{contexte}]\n{trace}"
                )
        except Exception:
            pass  # journaliser ne doit jamais devenir la panne suivante
        resume = (
            f"{type(exc).__name__}: {exc}" if exc is not None else trace.strip().split("\n")[-1]
        )
        try:
            self._log(
                f"! panne interne [{contexte}] — {resume[:120]}\n"
                f"  trace complète : Scripts/_logs/app_erreurs.log\n"
            )
        except Exception:
            pass

    def _panne_tk(self, typ, val, tb):
        """Rappel d'exception global de Tk (bouton, menu, binding)."""
        self._journal_panne("rappel Tk", val)

    def _drain(self):
        try:
            while True:
                kind, val = self.q.get_nowait()
                if kind == "line":
                    self._log(val)
                elif kind == "reload":
                    self.load_offers()
                    self.root.after(1500, self._auto_enrich)
                elif kind == "done_all":
                    self._log("\n✅ TOUT FAIRE terminé.\n")
                    self.load_offers()
                    self.root.after(1500, self._auto_enrich)
                elif kind == "maj_fin":
                    self._apres_mise_a_jour(*val)
        except queue.Empty:
            pass
        except Exception as ex:
            # UNE SEULE LIGNE FAUTIVE TUAIT L'APP. Seul queue.Empty etait
            # rattrape : toute autre panne sortait AVANT le `after` de la
            # derniere ligne, et plus rien ne se reprogrammait. Mesure : 1 tour
            # de boucle au lieu de 20, et zero rechargement — la table ne se
            # rafraichissait plus jamais apres un scan, sans le moindre signe.
            self._journal_panne("_drain", ex)
        finally:
            # Le `finally` est le correctif : la boucle se reprogramme QUOI QU'IL
            # ARRIVE. Une ligne perdue vaut mieux qu'une application figee.
            self.root.after(100, self._drain)

    def stop(self):
        """Arrete la tache en cours, ENFANTS COMPRIS.

        proc.terminate() ne tue que le Python lance ; Playwright et Chrome sont
        ses petits-enfants et survivent. On en a retrouve 14 orphelins tenant le
        profil dedie, ce qui empechait ensuite toute relance. taskkill /T coupe
        l'arbre entier."""
        if not (self.proc and self.proc.poll() is None):
            self._log("(aucune tache en cours)\n")
            return
        pid = self.proc.pid
        try:
            subprocess.run(
                ["taskkill", "/T", "/F", "/PID", str(pid)],
                capture_output=True,
                timeout=20,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            self._log(f"⏹ arrete (arbre du PID {pid})." + "\n")
        except Exception as e:
            err = type(e).__name__
            self._log(f"! arret KO ({err}) — repli sur terminate\n")
            try:
                self.proc.terminate()
            except Exception:
                pass

    def _gen_docs(self):
        """Genere CV + lettre pour les N offres les mieux notees qui n'en ont pas.

        Le nombre etait fige a 30 : avec 284 offres sans documents, il fallait
        cliquer dix fois. On le demande, en proposant le compte reel a faire."""
        try:
            q = queue_io.charger(QUEUE)
        except Exception:
            q = list(self.offers)

        def _f(u):
            if not u:
                return False
            try:
                return _doc_existe(u)
            except Exception:
                return False

        reste = sum(
            1
            for o in q
            if (o.get("fit") or 0) >= 8 and not (_f(o.get("cv")) and _f(o.get("lettre")))
        )
        n = simpledialog.askinteger(
            "CV / lettres",
            f"Combien d'offres traiter ?\n\n"
            f"{reste} offre(s) a fit ≥ 8 attendent encore leurs documents.",
            parent=self.root,
            initialvalue=min(reste or 30, 50),
            minvalue=1,
            maxvalue=1000,
        )
        if not n:
            return
        self.run_step([PY, "generate_docs.py", "--top", str(n)], f"CV/lettres — {n} offre(s)")


def _annonce_mise_a_jour(root, app):
    """Au demarrage, en arriere-plan : une version plus recente sur GitHub ?
    Au plus une verification par jour ; hors ligne, rien ne s'affiche."""

    def proposer(v, installee):
        if messagebox.askyesno(
            "JobHunter — mise à jour disponible",
            f"La version {v} est disponible (installée : {installee}).\n\n"
            "L'installer maintenant ? Ton profil, ton CV, tes lettres et ton suivi ne "
            "sont pas touchés, et la version d'avant est sauvegardée.",
            parent=root,
        ):
            app.mettre_a_jour()

    def verifier():
        try:
            import mise_a_jour

            v = mise_a_jour.nouvelle_version()
            installee = mise_a_jour.version_locale()
        except Exception:
            v = None
        if v:
            root.after(0, lambda: proposer(v, installee))

    threading.Thread(target=verifier, daemon=True).start()


if __name__ == "__main__":
    r = ctk.CTk()
    a = App(r)
    _annonce_mise_a_jour(r, a)
    r.mainloop()
