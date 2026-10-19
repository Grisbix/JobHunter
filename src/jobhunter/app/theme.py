"""Theme : couleurs, polices, espacements et widgets de base (CF, CB, CL, CE, make_btn).

Partie de jobhunter.app (ancien JobHunter.pyw, phase 3.7)."""

import datetime
import tkinter as tk
from typing import Any

import customtkinter as ctk

from jobhunter.app.langue import t as _t

ctk.set_appearance_mode("light")


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


def _resoudre_espacements(fenetre: Any) -> None:
    global PAD_PAGE, GAP
    try:
        w = fenetre.winfo_screenwidth()
    except Exception:
        return
    PAD_PAGE = 20
    GAP = 12


def _resoudre_polices() -> None:
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


def _fgcol(bg: Any) -> Any:
    return "transparent" if bg in _TRANSPARENT else bg


def _session_presentation(session: Any, verification: Any, aujourd_hui: Any = None) -> Any:
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
    parent: Any,
    bg: Any = None,
    width: Any = None,
    height: Any = None,
    corner_radius: Any = None,
    highlightbackground: Any = None,
    highlightthickness: Any = 0,
    plat: Any = False,
    **_: Any,
) -> Any:
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
    parent: Any,
    text: Any = "",
    command: Any = None,
    bg: Any = None,
    fg: Any = None,
    activebackground: Any = None,
    width: Any = None,
    pady: Any = None,
    anchor: Any = None,
    font: Any = None,
    corner_radius: Any = None,
    cursor: Any = None,
    **_: Any,
) -> Any:
    text = _t(text)
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
    parent: Any,
    text: Any = "",
    bg: Any = None,
    fg: Any = None,
    font: Any = None,
    anchor: Any = None,
    justify: Any = None,
    wraplength: Any = None,
    width: Any = None,
    **_: Any,
) -> Any:
    kw = {"text": _t(text)}
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


def CE(
    parent: Any, bg: Any = None, fg: Any = None, width: Any = None, font: Any = None, **_: Any
) -> Any:
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


def make_btn(
    parent: Any,
    text: Any,
    bg: Any = BTN,
    fg: Any = TX,
    cmd: Any = None,
    pw: Any = 10,
    ph: Any = 4,
    w: Any = None,
    side: Any = None,
) -> Any:
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
