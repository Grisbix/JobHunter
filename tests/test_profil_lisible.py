"""Profil: no sideways scroll, readable title patterns, a fold link that says what unfolds.

The user, 2026-11-04: the trades' raw re: patterns (one word, 2 900 px, no space) stretched
the grid past the window, so texts ran over each other and the panel scrolled sideways;
« Voir le détail » on the activity panel did not say what it showed.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

from jobhunter.web.texts import TEXTES

STATIQUE = Path(__file__).resolve().parent.parent / "src" / "jobhunter" / "web" / "static"
JS = (STATIQUE / "app.js").read_text(encoding="utf-8")
CSS = (STATIQUE / "style.css").read_text(encoding="utf-8")


def test_les_grilles_ne_s_elargissent_pas_pour_un_long_mot():
    assert "minmax(min(320px, 100%), 1fr)" in CSS
    assert ".grille > *, .grille .pile > * { min-width: 0; }" in CSS
    assert ".metier { min-width: 0; display: grid; grid-template-columns: minmax(0, 1fr);" in CSS


def test_le_profil_ne_defile_pas_de_cote():
    assert '.vue[data-ecran="profil"] { overflow-x: hidden; }' in CSS
    assert "vue.dataset.ecran = nom;" in JS


def test_le_lien_de_l_activite_dit_ce_qu_il_montre():
    assert '"Voir le détail"' not in JS
    for cle in (
        "Masquer ce qu'écrit le programme",
        "Voir ce qu'écrit le programme ({n} dernières lignes)",
        "Masquer l'historique",
        "Voir l'historique ({n} messages)",
    ):
        assert cle in TEXTES


@pytest.mark.skipif(shutil.which("node") is None, reason="node absent")
def test_mot_lisible():
    debut = JS.index("function motLisible(")
    fin = JS.index("\n}\n", debut) + 3
    script = JS[debut:fin] + (
        "console.log(JSON.stringify(["
        r"motLisible('re:\\b(isr|(?<![a-z])csrd(?![a-z])|sri)\\b'),"
        r"motLisible('re:(?:data|data\\ scientist)'),"
        "motLisible('climat'),"
        "]));"
    )
    sortie = subprocess.run(  # noqa: S603, S607
        ["node", "-e", script], capture_output=True, text=True, encoding="utf-8", check=True
    ).stdout
    assert sortie.strip() == '["isr · csrd · sri","data · data scientist","climat"]'
