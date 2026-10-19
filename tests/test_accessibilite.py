"""Accessibility of the interface (E3): WCAG contrasts, keyboard buttons, visible focus.

CustomTkinter draws its widgets on canvases: UI Automation sees no name
for them (D1, roadmap), and this test does not claim otherwise. What it guarantees: the text
is readable (4.5:1), a field outline and a focus ring are visible (3:1), and each
button can be operated from the keyboard.
"""

import pytest

from jobhunter.app import theme as t


def _lum(h: str) -> float:
    h = h.lstrip("#")
    c = [int(h[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def contraste(a: str, b: str) -> float:
    la, lb = _lum(a), _lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


# (text, background) actually used together in the app.
TEXTES = [
    ("TX", "BG"), ("TX", "CARD"), ("TX", "WORK"), ("TX", "BTN"), ("TX", "BTN_H"),
    ("MUT", "BG"), ("MUT", "CARD"), ("MUT", "WORK"),
    ("ACC_TX", "ACC"), ("ACC_TX", "ACC_H"), ("DEL_TX", "DEL"), ("DEL_TX", "DEL_H"),
    ("SIDE_TX", "SIDE"), ("SIDE_MUT", "SIDE"), ("SIDE_TX", "SIDE_H"), ("SIDE_MUT", "SIDE_H"),
    ("SIDE_TX", "SIDE_CARD"),
    ("OK", "CARD"), ("BAD", "CARD"), ("AMBRE", "CARD"), ("PURP", "CARD"), ("TEAL", "CARD"),
    ("ACC", "CARD"), ("ACC", "BG"), ("OK", "BG"), ("BAD", "BG"), ("AMBRE", "BG"),
]  # fmt: skip


@pytest.mark.parametrize(("texte", "fond"), TEXTES)
def test_texte_lisible_wcag_aa(texte, fond):
    assert contraste(getattr(t, texte), getattr(t, fond)) >= 4.5


@pytest.mark.parametrize("fond", ["CARD", "BG", "WORK"])
def test_contour_de_champ_visible(fond):
    assert contraste(t.LINE_SAISIE, getattr(t, fond)) >= 3


@pytest.mark.parametrize(
    "fond", ["BG", "CARD", "WORK", "BTN", "DEL", "ACC", "ACC_H", "SIDE", "SIDE_CARD", "SIDE_H"]
)
def test_anneau_de_focus_visible_sur_chaque_fond(fond):
    """The ring stands out on the button it surrounds AND on the page background around it."""
    couleur = getattr(t, fond)
    anneau = t.anneau_focus(couleur)
    autour = t.SIDE if fond.startswith("SIDE") else t.BG
    assert max(contraste(anneau, couleur), contraste(anneau, autour)) >= 3


@pytest.fixture
def racine(racine_tk):
    return racine_tk


def test_bouton_atteint_et_joue_au_clavier(racine):
    appels = []
    b = t.CB(racine, text="Suivre", command=lambda: appels.append(1), bg=t.ACC)
    b.pack()
    racine.update()
    canevas = b._canvas
    assert str(canevas.cget("takefocus")) == "1"
    canevas.focus_force()
    racine.update()
    assert b.cget("border_width") == 2 and b.cget("border_color") == t.TX  # anneau
    canevas.event_generate("<Return>")
    canevas.event_generate("<space>")
    racine.update()
    assert appels == [1, 1]


def test_bouton_desactive_muet(racine):
    appels = []
    b = t.CB(racine, text="Non", command=lambda: appels.append(1))
    b.configure(state="disabled")
    b.pack()
    racine.update()
    b._canvas.focus_force()
    b._canvas.event_generate("<Return>")
    racine.update()
    assert appels == []


def test_tabulation_suit_l_ordre_de_pose(racine):
    """Tk parcourt au Tab les widgets focusables dans leur ordre d'empilement, qui est
    l'ordre de création : chaque bouton y est, dans l'ordre où il est posé."""
    boutons = [t.CB(racine, text=f"B{i}") for i in range(3)]
    for b in boutons:
        b.pack()
    racine.update()
    assert all(str(b._canvas.cget("takefocus")) == "1" for b in boutons)
    empiles = [w for w in racine.winfo_children() if w in boutons]
    assert empiles == boutons


def test_champ_montre_son_focus(racine):
    c = t.CE(racine, bg=t.CARD)
    c.pack()
    racine.update()
    assert c.cget("border_color") == t.LINE_SAISIE
    c._entry.focus_force()
    racine.update()
    assert c.cget("border_color") == t.FOCUS and c.cget("border_width") == 2
