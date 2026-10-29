"""3.67: the home screen holds in 1280 × 720, the web app works with the keyboard and a
screen reader, each offer shows the logo of its source, and the sheet explains the
signals of a ghost offer (republished, same text elsewhere, knock-out condition)."""

from pathlib import Path

from jobhunter.web import api

STATIC = Path(__file__).resolve().parent.parent / "src" / "jobhunter" / "web" / "static"
CSS = (STATIC / "style.css").read_text(encoding="utf-8")
JS = (STATIC / "app.js").read_text(encoding="utf-8")
HTML = (STATIC / "index.html").read_text(encoding="utf-8")


def test_accueil_mesure_le_bas_sans_le_rembourrage():
    assert "parseFloat(getComputedStyle(vue).paddingBottom)" in JS
    assert (
        ".accueil .panneau { padding: 16px 24px; }"
        in CSS[CSS.index("@media (max-height: 760px)") :]
    )


def test_graduations_suivent_la_hauteur_du_tube():
    # 168 px fixed put "125" and "0" under the card when the tube is 98 px
    assert "* 168}px" not in JS
    assert "top:calc(${1 - p / 100} * (100% - 22px))" in JS


def test_tout_element_cliquable_se_joint_au_clavier():
    debut = JS.index("function accessible(")
    corps = JS[debut : debut + 1200]
    assert "tabIndex = 0" in corps
    assert '"Enter"' in corps and '" "' in corps
    assert "accessible(e, attrs || {})" in JS
    assert 'input[type="range"]):focus-visible {' in CSS


def test_icones_muettes_et_boutons_nommes():
    assert 'setAttribute("aria-hidden", "true")' in JS
    assert 'id="fermer-tiroir"' in HTML and 'aria-label="Fermer"' in HTML
    assert 'role="dialog"' in HTML and 'aria-label="Écrans"' in HTML
    assert 'setAttribute("aria-current", "page")' in JS
    assert '"aria-modal"' in JS


def test_tiroir_rend_le_focus():
    debut = JS.index("function suivreTiroir(")
    corps = JS[debut : debut + 900]
    assert "MutationObserver" in corps
    assert '$("fermer-tiroir").focus(' in corps and "avant.focus(" in corps


def test_logo_de_la_source():
    assert "const LOGOS_SOURCES = {" in JS
    for famille in ("linkedin", "welcometothejungle", "greenhouse", "sap", "indeed"):
        assert f'  {famille}: "M' in JS, famille
    assert "logoSource(o.source)" in JS
    assert ".logo-source.initiale" in CSS


def test_carte_des_signaux_fantomes():
    assert "function carteSignaux(o)" in JS
    for indice in ("republi", "même texte", "doublon", "⚠"):
        assert indice in JS[JS.index("function carteSignaux(o)") :][:2500], indice
    assert "Republiée ${m[1]} fois en 90 jours" in JS


def test_l_api_donne_la_source_et_les_republications():
    o = {
        "entreprise": "Acme",
        "poste": "Analyste",
        "url": "https://exemple.org/1",
        "source": "linkedin",
        "republiee": 4,
        "signal": "republiée ×4",
    }
    assert api._ligne(o, {})["source"] == "linkedin"
    f = api.fiche(o, {}, "")
    assert f["republiee"] == 4
    assert api._ligne({"entreprise": "A", "poste": "B"}, {})["source"] == ""
