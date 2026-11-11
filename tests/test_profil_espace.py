"""Profil without empty parts (the user, 2026-11-04: « adapte l'espace dans profil pour
éviter qu'il y ait des parties vides »)."""

from pathlib import Path

import js_app

STATIQUE = Path(__file__).resolve().parent.parent / "src" / "jobhunter" / "web" / "static"
JS = js_app.source()
CSS = (STATIQUE / "style.css").read_text(encoding="utf-8")


def test_outils_a_cote_de_l_identite():
    profil = JS[JS.index("ECRANS.profil = {") :]
    profil = profil[: profil.index("\n};\n")]
    assert 'h("div", { class: "pile pile-profil" }' in profil
    assert '{ className: "verre panneau outils-profil" }' in profil
    assert 'carte("Outils", puces(p.outils))));' not in profil
    assert ".grille .pile-profil > .outils-profil { flex: 1 1 0; min-height: 180px;" in CSS


def test_deux_colonnes_au_plus():
    assert 'class: "grille grille-profil"' in JS
    assert "minmax(min(max(320px, calc(50% - 10px)), 100%), 1fr)" in CSS


def test_competences_compactes():
    assert ".ligne-comp > .puces-edit { grid-column: 1 / -1; grid-row: 2; }" in CSS
    assert "minmax(min(520px, 100%), 1fr)" in CSS
