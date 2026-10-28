"""3.65: Relances and Statistiques hold in a 1280 × 720 window when they open, like
Candidatures in 3.64 (the user, 2026-10-28). Measured on the demo data: Relances ran
136 px under the window, Statistiques 286 px, the home screen 17 px."""

from pathlib import Path

STATIC = Path(__file__).resolve().parent.parent / "src" / "jobhunter" / "web" / "static"
CSS = (STATIC / "style.css").read_text(encoding="utf-8")
JS = (STATIC / "app.js").read_text(encoding="utf-8")


def test_relances_tient_dans_la_fenetre():
    bloc = JS[JS.index("ECRANS.relances = {") :][:400]
    assert "plein: true" in bloc
    assert ".vue.plein > .relances { flex: 1 1 auto; min-height: 0;" in CSS
    assert ".vue.plein .relances .fil { flex: 1 1 auto; min-height: 0; overflow-y: auto;" in CSS


def test_statistiques_en_quatre_piles():
    assert (
        'h("div", { class: "piles-stats" }, envoyees ? h("div", { class: "pile" }, envoyees)' in JS
    )
    assert "minmax(220px, 1fr)" in CSS
    # a long title wraps instead of widening the page
    assert ".piles-stats h2 { font-size: var(--t-xl); white-space: normal;" in CSS


def test_regles_compactes_plus_specifiques_que_les_regles_de_base():
    # the base rules come after the low-window block: one class would lose
    bas = CSS.index("@media (max-height: 760px)")
    assert CSS.index(".carte-stat { padding:") > bas
    assert ".cartes-stats .carte-stat { padding: 12px 16px; }" in CSS[bas:]
