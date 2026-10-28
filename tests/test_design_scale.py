"""3.52: the web window's sizes stay on two scales (type, spacing).

Twenty font sizes (12.5, 13.5, 9.5 px…) and thirty spacing values had crept in, one
screen at a time; the result read as unfinished. A new size goes through a token.
"""

import re
from pathlib import Path

CSS = (
    Path(__file__).resolve().parent.parent / "src" / "jobhunter" / "web" / "static" / "style.css"
).read_text(encoding="utf-8")

ESPACEMENTS = {0, 1, 2, 4, 8, 12, 16, 20, 24, 32, 40, 48}


def test_chaque_taille_de_police_est_un_jeton():
    hors = [v.strip() for v in re.findall(r"font-size:\s*([^;}]+)", CSS)]
    hors = [v for v in hors if not v.startswith("var(--t-") and v not in ("0", "inherit")]
    assert not hors, hors


def test_chaque_espacement_est_sur_l_echelle():
    hors = []
    for prop, valeurs in re.findall(
        r"(?<![\w-])(gap|row-gap|column-gap|padding(?:-\w+)?|margin(?:-\w+)?)\s*:([^;{}]+)", CSS
    ):
        for v in re.findall(r"(?<![\w.-])(\d+(?:\.\d+)?)px", valeurs):
            if float(v) <= 64 and float(v) not in ESPACEMENTS:
                hors.append(f"{prop}: {v}px")
    assert not hors, hors


def test_pas_de_halo_decoratif():
    assert ".sombre::before, .sombre::after { display: none; }" in CSS
