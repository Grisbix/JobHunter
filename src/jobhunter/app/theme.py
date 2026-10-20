"""Theme: colours, fonts, spacing and basic widgets (CF, CB, CL, CE, make_btn).

Part of jobhunter.app (former JobHunter.pyw, phase 3.7)."""

import datetime
import tkinter as tk
from typing import Any

import customtkinter as ctk

from jobhunter.app.language import t as _t

ctk.set_appearance_mode("light")


# Recruitment CRM (Outcrowd), adapted: navy navigation, pale blue workspace,
# data on white. Separate colours for the controls on the dark sidebar.
BG = "#E9EFF7"


WORK = "#F4F7FB"


CARD = "#FFFFFF"


LINE = "#D8E2EF"

# Outline of an input field: at least 3:1 on CARD, BG and WORK (WCAG 1.4.11, E3).
LINE_SAISIE = "#74869F"


TX = "#19283F"


MUT = "#52647B"


ROW0 = "#FFFFFF"


ROW1 = "#F5F8FC"


ACC = "#325EDF"

# Keyboard focus ring (E3): the accent, 5.5:1 on CARD, 4.8:1 on BG.
FOCUS = ACC


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


# Naming a MISSING font family makes Tk fall back to an arbitrary font,
# often worse than the starting point. So we resolve at run time, when a
# window exists, taking the first family really installed.
FONT_UI = "Segoe UI Variable Display"


FONT_MONO = "Consolas"


# Spacing. Tk has neither clamp() nor vw: we evaluate once at start-up,
# from the real screen width. No recomputation on resize —
# that would be new behaviour, and the floor covers small windows.
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


_TRANSPARENT = (BG,)  # only the main background is a "container"


def _fgcol(bg: Any) -> Any:
    return "transparent" if bg in _TRANSPARENT else bg


def _session_presentation(session: Any, verification: Any, aujourd_hui: Any = None) -> Any:
    """A historical check is not a proof of current login."""
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
    """plat=True: simple layout container, without border or corners —
    a row of buttons placed INSIDE a card is not one more card."""
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
        # A single border per surface; no frame added to sub-containers.
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
    # Hover "gets slightly brighter": one tint per role, not
    # a generic glow. Without it CustomTkinter applies its own blue.
    _SURVOL = {ACC: ACC_H, BTN: BTN_H, DEL: DEL_H, CARD: BTN_H, SIDE_CARD: BTN_H}
    if activebackground:
        kw["hover_color"] = activebackground
    elif bg in _SURVOL:
        kw["hover_color"] = _SURVOL[bg]
    # Text colour DERIVED from the role when it is not imposed: light
    # text on the light blue ACC would be unreadable, and a caller who forgets
    # fg must not produce a button that cannot be read.
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
    return clavier(ctk.CTkButton(parent, **kw))


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
    # Outline of a field: at least 3:1 on all backgrounds (WCAG 1.4.11, E3); LINE, at
    # 1.3:1, left the field invisible. Focus: the outline switches to FOCUS, 2 px.
    kw = {"corner_radius": RAD_BTN, "border_width": 1, "border_color": LINE_SAISIE}
    if bg is not None:
        kw["fg_color"] = bg
    if fg:
        kw["text_color"] = fg
    if width:
        kw["width"] = int(width) * 7
    if font:
        kw["font"] = ctk.CTkFont(*font) if isinstance(font, tuple) else font
    champ = ctk.CTkEntry(parent, **kw)
    interieur = getattr(champ, "_entry", None)
    if interieur is not None:
        interieur.bind(
            "<FocusIn>", lambda e: champ.configure(border_color=FOCUS, border_width=2), add="+"
        )
        interieur.bind(
            "<FocusOut>",
            lambda e: champ.configure(border_color=LINE_SAISIE, border_width=1),
            add="+",
        )
    return champ


def anneau_focus(fond: Any) -> str:
    """The colour of the focus ring depending on the button's background: visible on each.

    Night blue of the sidebar → light text; accent button (blue) → dark text;
    elsewhere, FOCUS.
    """
    if fond in (SIDE, SIDE_CARD, SIDE_H):
        return SIDE_TX
    if fond in (ACC, ACC_H):
        return TX
    return FOCUS


def clavier(bouton: Any) -> Any:
    """Makes a CTkButton usable from the keyboard (E3); returns it.

    CustomTkinter draws its buttons on a canvas that Tab skips: without a mouse, no
    button of the application could be reached. The canvas takes the focus in
    creation order (the visual order, widgets being laid out top to bottom), shows
    a 2 px FOCUS ring, and Enter or Space trigger the button.
    """
    canevas = getattr(bouton, "_canvas", None)
    if canevas is None:
        return bouton
    canevas.configure(takefocus=1)
    largeur, couleur = bouton.cget("border_width"), bouton.cget("border_color")
    anneau = anneau_focus(bouton.cget("fg_color"))

    def declencher(_e: Any) -> str:
        if str(bouton.cget("state")) != "disabled":
            bouton.invoke()
        return "break"

    for touche in ("<Return>", "<KP_Enter>", "<space>"):
        canevas.bind(touche, declencher, add="+")
    canevas.bind(
        "<FocusIn>", lambda e: bouton.configure(border_width=2, border_color=anneau), add="+"
    )
    canevas.bind(
        "<FocusOut>",
        lambda e: bouton.configure(border_width=largeur, border_color=couleur),
        add="+",
    )
    return bouton


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
