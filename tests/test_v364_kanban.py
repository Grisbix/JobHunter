"""3.64: the applications board holds in the window when it opens (the user, 2026-10-28).

The six columns stayed on two lines at 1280 px: the board ran out under the window
and over the note below it ("text in the background")."""

import re
from pathlib import Path

STATIC = Path(__file__).resolve().parent.parent / "src" / "jobhunter" / "web" / "static"
CSS = (STATIC / "style.css").read_text(encoding="utf-8")
JS = (STATIC / "app.js").read_text(encoding="utf-8")


def test_six_colonnes_sur_une_ligne_a_1280():
    pleine = int(re.search(r"\.colonne-k \{ flex: 1 1 (\d+)px; min-width: (\d+)px", CSS).group(2))
    vide = int(re.search(r"\.colonne-k\.vide-k \{[^}]*min-width: (\d+)px", CSS).group(1))
    # 1280 px window: 992 px for the board (measured), 16 px between columns
    assert 4 * pleine + 2 * vide + 5 * 16 <= 992
    assert "@media (min-width: 1100px) { .vue.plein .tableau-kanban { flex-wrap: nowrap; } }" in CSS


def test_les_cartes_suivent_la_hauteur_de_la_fenetre():
    assert "CARTES_K" not in JS  # no fixed count any more
    assert "ajusterKanban(vue);" in JS
    assert 'courant === "candidatures") ajusterKanban' in JS  # again when the window changes


def test_marge_du_bas_comme_les_cotes():
    assert (
        ".vue.plein { overflow-y: auto; display: flex; flex-direction: column; padding-bottom: 24px; }"
        in CSS
    )
