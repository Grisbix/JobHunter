"""Daily triage: the whole description on demand (the user, 2026-11-04: « pouvoir voir la
description en entier »; it was held in a box 40 % of the window high)."""

from pathlib import Path

import js_app

from jobhunter.web.texts import TEXTES

STATIQUE = Path(__file__).resolve().parent.parent / "src" / "jobhunter" / "web" / "static"
JS = js_app.source()
CSS = (STATIQUE / "style.css").read_text(encoding="utf-8")


def test_le_tri_deplie_la_description():
    debut = JS.index("ECRANS.tri = {")
    assert "texteTri(o.description)" in JS[debut : JS.index("ECRANS.relances", debut)]
    assert "function texteTri(" in JS
    assert ".tri-texte.entier { max-height: none; overflow: visible; }" in CSS


def test_le_choix_est_garde_et_traduit():
    assert 'localStorage.setItem("jh-tri-entier"' in JS
    assert "Lire la description en entier" in TEXTES
    assert "Réduire la description" in TEXTES
