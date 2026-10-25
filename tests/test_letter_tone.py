"""The letter's tone follows `lettre.ton`: a young graduate's path, or experience put to work.

The reference profile has no `ton`: its letters keep the young-graduate wording (the
non-regression bench checks them word for word). An experienced profile no longer
writes "je me suis familiarisé avec" nor "le projet que je construis depuis mes études".
"""

import pytest

from jobhunter.documents import letter

OFFRE = {
    "company": "Société Test",
    "role": "Analyste ESG",
    "offer_text": "Analyste ESG : analyse financière, reporting ESG, SFDR, modélisation.",
    "missions": "",
    "profil": "",
    "domaine": "",
}


@pytest.fixture
def texte_de_la_lettre(monkeypatch, tmp_path):
    textes = []

    def capter(doc, out):
        textes.append("\n".join(p.text for p in doc.paragraphs))

    monkeypatch.setattr(letter._generes, "enregistrer", capter)
    monkeypatch.setattr(letter, "LT_OUT", tmp_path, raising=False)

    def ecrire(langue):
        letter.tailor_letter(dict(OFFRE), nom="essai", langue=langue)
        return textes[-1]

    return ecrire


def test_jeune_diplome_par_defaut(texte_de_la_lettre):
    t = texte_de_la_lettre("fr")
    assert "depuis mes études" in t
    assert "J'apporterai ce savoir-faire" not in t


@pytest.mark.parametrize(
    ("langue", "attendu", "absent"),
    [
        ("fr", "correspond à mon parcours et à la suite", "depuis mes études"),
        ("en", "matches the work I have done so far", "since my studies"),
    ],
)
def test_ton_experimente(monkeypatch, texte_de_la_lettre, langue, attendu, absent):
    monkeypatch.setattr(letter, "_experimente", lambda: True)
    t = texte_de_la_lettre(langue)
    assert attendu in t
    assert absent not in t
    assert "familiaris" not in t and "became familiar" not in t
    # The CV's summary already says "N ans d'expérience": the letter does not repeat it.
    assert "expérience" not in t and "experience" not in t
