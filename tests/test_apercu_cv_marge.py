"""CV preview: the pages end above the drawer's foot (the user, 2026-11-04: « l'aperçu des
cv coupe les cv en bas, met un petit écart avec la marge »)."""

from pathlib import Path

STATIQUE = Path(__file__).resolve().parent.parent / "src" / "jobhunter" / "web" / "static"
JS = (STATIQUE / "app.js").read_text(encoding="utf-8")
CSS = (STATIQUE / "style.css").read_text(encoding="utf-8")


def test_l_apercu_remplit_le_tiroir_sans_le_depasser():
    assert 'place.classList.toggle("remplit-doc", mode === "apercu");' in JS
    assert (
        ".remplit-doc > .apercu-pages { flex: 1 1 auto; min-height: 0; max-height: none; }" in CSS
    )
    assert "overflow: auto; scrollbar-width: thin; padding-bottom: 16px; }" in CSS


def test_l_apercu_a_cote_du_texte_finit_avant_le_bas():
    assert ".cote-apercu .apercu-pages { max-height: calc(100vh - 252px); }" in CSS
