"""The fit's tunable weights (scoring.weights) and the split of the fit into components.

The split must not move a single fit: `fit_entier(composantes(...))` is the fit of
`fit_detail`, and a change of weights is seen without reading the text again.
"""

import pytest

from jobhunter.programs.fit_components import depuis_ligne, ligne
from jobhunter.scoring import fit as F
from jobhunter.scoring import weights as W

OFFRES = [
    ("Analyste ESG junior", "Analyste ESG junior. SFDR, taxonomie, reporting extra-financier."),
    ("Senior Portfolio Manager", "Gestion d'actifs, valorisation DCF, 10 ans d'expérience."),
    ("Data Analyst", "Python / SQL, machine learning, tableaux de bord. 3 ans d'expérience."),
    ("Stagiaire comptable", "Saisie comptable, rapprochements."),
    ("Chargé de mission RSE", "CSRD, empreinte carbone, analyse financière, Excel."),
]


@pytest.mark.parametrize(("titre", "texte"), OFFRES)
def test_composantes_redonnent_le_fit(titre, texte):
    fit, yrs, _fin = F.fit_detail(f"{titre} {texte}", titre)
    c = F.composantes(f"{titre} {texte}", titre)
    assert F.fit_entier(c) == fit
    assert c.annees == yrs


def test_ligne_json_aller_retour():
    axes = list(F.AXES)
    c = F.composantes("Analyste ESG junior SFDR taxonomie", "Analyste ESG junior")
    assert depuis_ligne(ligne(c, axes), axes) == F.Composantes(
        c.axes, c.plafond, c.junior, c.senior, c.ecarte, c.annees
    )


def test_poids_change_le_fit_sans_relire_le_texte():
    titre, texte = OFFRES[2]
    c = F.composantes(f"{titre} {texte}", titre)
    p = F.ponderation()
    sans_exp = p.avec(malus_experience={})
    assert F.fit_de(c, sans_exp) >= F.fit_de(c, p)
    # same answer through fit_detail with the same weights
    assert F.fit_detail(f"{titre} {texte}", titre, None, sans_exp)[0] == F.fit_entier(c, sans_exp)


def test_expliquer_suit_les_poids():
    titre, texte = OFFRES[0]
    p = F.ponderation()
    lignes = F.expliquer(f"{titre} {texte}", titre, p.avec(bonus_junior=3.0))
    assert any(x.endswith("+3") for x in lignes if x.startswith("intitulé junior"))


PROFIL = {
    "scoring": {"axes": {"esg": {"poids": 3.0, "competences": []}, "ia": {"competences": []}}},
    "niveau": {"malus_experience": {"3": 1, "5": 3}},
}


def test_lire_remplit_les_defauts():
    p = W.lire(PROFIL)
    assert p.axes == {"esg": 3.0, "ia": 1.0}
    assert (p.cible, p.bonus_junior, p.malus_senior) == (3.0, 1.0, 2.0)
    assert p.malus_annees(4) == 1 and p.malus_annees(9) == 3 and p.malus_annees(1) == 0


def test_appliquer_n_ecrit_que_ce_qui_change():
    assert W.appliquer(PROFIL, W.lire(PROFIL)) == PROFIL
    p = W.lire(PROFIL).avec(axes={"esg": 2.5, "ia": 1.0}, bonus_junior=1.5)
    out = W.appliquer(PROFIL, p)
    assert out["scoring"]["axes"]["esg"]["poids"] == 2.5
    assert "poids" not in out["scoring"]["axes"]["ia"]
    assert out["niveau"]["bonus_junior"] == 1.5
    assert out["niveau"]["malus_experience"] == {"3": 1, "5": 3}
    assert PROFIL["scoring"]["axes"]["esg"]["poids"] == 3.0  # the original is untouched


def test_appliquer_paliers_d_experience():
    p = W.lire(PROFIL).avec(malus_experience={3: 0.5, 5: 3.0})
    assert W.appliquer(PROFIL, p)["niveau"]["malus_experience"] == {"3": 0.5, "5": 3}


def test_valider():
    p = W.lire(PROFIL)
    assert W.valider(p) == []
    assert W.valider(p.avec(cible=0))
    assert W.valider(p.avec(axes={"esg": 0.0, "ia": 0.0}))
    assert W.valider(p.avec(malus_senior=-1))


def test_bilan():
    cs = [F.composantes(f"{t} {x}", t) for t, x in OFFRES]
    b = W.bilan(cs, F.ponderation())
    assert b.n == len(OFFRES)
    assert sum(b.repartition.values()) == b.n
    assert b.moyenne == pytest.approx(sum(F.fit_entier(c) for c in cs) / b.n)
    assert W.bilan([], F.ponderation()).moyenne == 0.0
