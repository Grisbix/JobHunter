"""The profile's skills as the Compétences tab edits them (jobhunter.skills_settings)."""

from jobhunter import skills_settings as S

PROFIL = {
    "competences": {
        "SFDR": {"synonymes": ["sfdr", "article 8"], "en": "SFDR", "prose_fr": "la SFDR"},
        "Python / SQL": {"synonymes": ["python", "sql"]},
        "Machine learning": {"synonymes": ["machine learning"]},
        "Excel": {"synonymes": ["excel"]},
    },
    "competences_de_base": ["Excel"],
    "scoring": {
        "axes": {
            "esg": {"poids": 3.0, "competences": ["SFDR"]},
            "data": {"competences": ["Python / SQL", "Machine learning"]},
            "ia": {"competences": ["Machine learning", "Hors profil"]},
        }
    },
}


def test_aller_retour_identique():
    assert S.appliquer(PROFIL, S.lire(PROFIL)) == PROFIL


def test_competence_dans_deux_axes():
    ml = next(c for c in S.lire(PROFIL) if c.nom == "Machine learning")
    assert ml.axes == ["data", "ia"]
    excel = next(c for c in S.lire(PROFIL) if c.nom == "Excel")
    assert excel.axes == []


def test_ajouter_et_changer_d_axe():
    liste = S.lire(PROFIL)
    liste.append(S.Competence("CSRD", ["esg"], ["csrd"], "CSRD"))
    next(c for c in liste if c.nom == "Python / SQL").axes = ["ia"]
    out = S.appliquer(PROFIL, liste)
    assert out["competences"]["CSRD"] == {"synonymes": ["csrd"], "en": "CSRD"}
    assert out["scoring"]["axes"]["esg"]["competences"] == ["SFDR", "CSRD"]
    assert out["scoring"]["axes"]["data"]["competences"] == ["Machine learning"]
    # the unknown name an axis carried stays; the moved skill goes to the end
    assert out["scoring"]["axes"]["ia"]["competences"] == [
        "Machine learning",
        "Hors profil",
        "Python / SQL",
    ]
    assert out["competences"]["SFDR"]["prose_fr"] == "la SFDR"  # other keys kept
    assert PROFIL["scoring"]["axes"]["esg"]["competences"] == ["SFDR"]  # untouched


def test_retirer():
    liste = [c for c in S.lire(PROFIL) if c.nom != "SFDR"]
    out = S.appliquer(PROFIL, liste)
    assert "SFDR" not in out["competences"]
    assert out["scoring"]["axes"]["esg"]["competences"] == []


def test_valider():
    assert S.valider(S.lire(PROFIL), PROFIL) == []
    sans_mot = S.lire(PROFIL) + [S.Competence("Vide", [], [])]
    assert any("aucun mot" in e for e in S.valider(sans_mot, PROFIL))
    double = S.lire(PROFIL) + [S.Competence("SFDR", [], ["x"])]
    assert any("double" in e for e in S.valider(double, PROFIL))
    sans_excel = [c for c in S.lire(PROFIL) if c.nom != "Excel"]
    assert any("compétence de base" in e for e in S.valider(sans_excel, PROFIL))
    axe_inconnu = S.lire(PROFIL) + [S.Competence("X", ["finance"], ["x"])]
    assert any("axe inconnu" in e for e in S.valider(axe_inconnu, PROFIL))


def test_depuis_texte():
    assert S.depuis_texte("sfdr, Article 8\n\n article 8 \nart.  9") == [
        "sfdr",
        "Article 8",
        "art. 9",
    ]
