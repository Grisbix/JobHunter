"""The fit explanation in the interface language (language.explication, FIT catalogues)."""

import pytest

from jobhunter.app import language as L
from jobhunter.app import texts_de, texts_en, texts_es
from jobhunter.scoring.fit import expliquer

TEXTE = "Senior ESG Analyst. SFDR, CSRD, carbon footprint, Python. 5 years of experience required."


@pytest.mark.parametrize("m", [texts_en, texts_de, texts_es])
def test_memes_cles_partout(m):
    assert set(m.FIT) == set(texts_en.FIT)


@pytest.mark.parametrize("langue", ["en", "de", "es"])
def test_plus_de_francais_du_moteur(monkeypatch, langue):
    monkeypatch.setattr(L, "LANGUE", langue)
    lignes = [L.explication(r) for r in expliquer(TEXTE, "Senior ESG Analyst")]
    for fr in ("vocabulaire", "intitulé", "plafond", "expérience demandés"):
        assert not any(fr in ligne for ligne in lignes), (fr, lignes)


def test_francais_inchange(monkeypatch):
    monkeypatch.setattr(L, "LANGUE", "fr")
    r = expliquer(TEXTE, "Senior ESG Analyst")
    assert [L.explication(x) for x in r] == r
