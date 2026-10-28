"""3.52: the web window's sizes stay on two scales (type, spacing).

Twenty font sizes (12.5, 13.5, 9.5 px…) and thirty spacing values had crept in, one
screen at a time; the result read as unfinished. A new size goes through a token.
"""

import re
from pathlib import Path

CSS = (
    Path(__file__).resolve().parent.parent / "src" / "jobhunter" / "web" / "static" / "style.css"
).read_text(encoding="utf-8")
JS = (
    Path(__file__).resolve().parent.parent / "src" / "jobhunter" / "web" / "static" / "app.js"
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


def test_les_fenetres_d_accueil_suivent_les_memes_echelles():
    # The welcome windows (customtkinter) draw what style.css draws: same two scales.
    from jobhunter import welcome

    src = Path(welcome.__file__).parent
    for nom in ("welcome.py", "welcome_tour.py"):
        code = (src / nom).read_text(encoding="utf-8")
        for t in re.findall(r"(?:taille=|_police\()(\d+)", code):
            assert int(t) in welcome.TYPO, (nom, t)
        for pad in re.findall(r"\bpad[xy]=(\(\s*\d+\s*,\s*\d+\s*\)|\d+)", code):
            for v in re.findall(r"\d+", pad):
                assert int(v) in ESPACEMENTS, (nom, pad)
    assert set(welcome.TYPO) == {int(v) for v in re.findall(r"--t-\w+:\s*(\d+)px", CSS)}
    assert set(welcome.ESPACEMENTS) <= ESPACEMENTS


def test_une_fenetre_basse_ne_pousse_pas_les_lignes_hors_du_panneau():
    # 900×560 (the window's minimum): the list's own 260 px minimum outgrew its panel,
    # and its rows showed under the panel's edge (2026-10-28). The panel holds the
    # minimum; the list inside may shrink.
    regle = re.search(r"\.vue\.plein \.remplit > \.defile[^{]*\{([^}]*)\}", CSS).group(1)
    assert "min-height: 0" in regle
    panneau = re.search(r"\.vue\.plein \.colonne > \.remplit,[^{]*\{([^}]*)\}", CSS).group(1)
    assert re.search(r"min-height: [1-9]\d+px", panneau)


def test_le_kanban_passe_a_la_ligne_au_lieu_d_ecraser_ses_colonnes():
    assert re.search(r"\.tableau-kanban \{[^}]*flex-wrap: wrap", CSS)
    assert re.search(r"\n\.colonne-k \{[^}]*min-width: [1-9]\d+px", CSS)


def test_rien_ne_defile_vers_la_droite():
    # The user, 2026-10-28: « pas de défilement vers la droite ». Bars and boards wrap;
    # only a table may scroll sideways inside its own panel.
    for regle in re.findall(r"([^{}]+)\{([^}]*overflow-x: (?:auto|scroll)[^}]*)\}", CSS):
        assert "barre-outils" not in regle[0] and "kanban" not in regle[0], regle[0]
    assert not re.search(r"\.barre-outils[^{]*\{[^}]*flex-wrap: nowrap", CSS)


def test_l_accueil_range_des_elements_entiers_pour_tenir_dans_la_fenetre():
    # The user, 2026-10-28: « éviter de couper les widgets quand on ouvre l'app ».
    assert "function ajusterAccueil(vue)" in JS
    assert re.search(r"\.accueil \.range \{[^}]*display: none", CSS)
