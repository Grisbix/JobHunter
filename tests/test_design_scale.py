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


def test_le_bureau_a_distance_retire_flous_et_animations():
    # The user's session, 2026-10-28 (« je trouve ça lent »): Remote Desktop sends about
    # 30 frames a second; the blurs cost the most GPU work per frame there.
    assert 'appel("session")' in JS and '"leger"' in JS
    leger = re.search(r"body\.leger \*[^{]*\{([^}]*)\}", CSS).group(1)
    assert "backdrop-filter: none" in leger and "animation: none" in leger
    assert "prefers-reduced-motion: reduce" in CSS


def test_un_rafraichissement_garde_la_position_de_defilement():
    corps = JS[JS.index("async function redessinerDonnees") :][:1500]
    assert "scrollTop" in corps


def test_chaque_icone_existe_et_dit_ce_que_fait_son_bouton():
    # The user, 2026-11-05: no star, no lightning — an icon says what its button does
    # (collection, pen, clock, funnel…). An icon name missing from ICONES draws nothing.
    html = (
        Path(__file__).resolve().parent.parent
        / "src"
        / "jobhunter"
        / "web"
        / "static"
        / "index.html"
    ).read_text(encoding="utf-8")
    table = JS[JS.index("const ICONES = {") : JS.index("};", JS.index("const ICONES = {"))]
    connues = set(re.findall(r"^\s+([a-z]+):", table, re.M))
    utilisees = set(re.findall(r'svg\("([a-z]+)"\)', JS))
    utilisees |= set(
        re.findall(r'(?:bouton|action)\((?:"[^"]*"|`[^`]*`|[^,()]+),\s*"([a-z]+)"', JS)
    )
    utilisees |= set(re.findall(r'data-icone="([a-z]+)"', html))
    utilisees |= set(re.findall(r'\["([a-z]+)", (?:"|`)', JS[JS.index("ECRANS.accueil") :][:6000]))
    assert utilisees, "aucune icône trouvée : l'expression a changé"
    assert not utilisees - connues, utilisees - connues
    assert not {"etoile", "eclair"} & (connues | utilisees)
