"""The interface's catalogues (jobhunter.locales), read by the web window (jobhunter.web.i18n).

Kept from test_language.py when the desktop window and its language module were removed
(3.77): the catalogues outlive it.
"""

import importlib
import pathlib
import re

import pytest

from jobhunter.locales import en as texts_en

PAQUET = pathlib.Path(texts_en.__file__).parents[1]
AUTRES = ["en", "de", "es"]


@pytest.mark.parametrize("code", AUTRES)
def test_catalogue_sans_doublon_de_cle(code):
    texte = (PAQUET / "locales" / f"{code}.py").read_text(encoding="utf-8")
    cles = re.findall(r'^    "((?:[^"\\]|\\.)*)": ', texte, re.M)
    assert len(cles) == len(set(cles))


@pytest.mark.parametrize("code", [c for c in AUTRES if c != "en"])
@pytest.mark.parametrize("nom", ["TEXTES", "JOURNAL", "SORTIE"])
def test_chaque_langue_couvre_l_anglais(code, nom):
    """English is the reference list: every language translates all of it, nothing more.

    Same `{x}` holes on both sides: a missing hole raises KeyError at display.
    """
    ref = getattr(texts_en, nom)
    cat = getattr(importlib.import_module(f"jobhunter.locales.{code}"), nom)
    assert [k for k in ref if k not in cat] == []
    assert [k for k in cat if k not in ref] == []
    trous = re.compile(r"\{(\w+)\}")
    assert [k for k, v in cat.items() if sorted(trous.findall(k)) != sorted(trous.findall(v))] == []


def test_sortie_modeles_vivent_dans_le_paquet():
    """Each line of SORTIE is still printed somewhere in the package."""
    source = "\n".join(
        p.read_text(encoding="utf-8") for p in PAQUET.rglob("*.py") if p.parent.name != "locales"
    )
    trous = re.compile(r"\{(\w+)\}")
    morts = []
    for fr, en in texts_en.SORTIE.items():
        assert sorted(trous.findall(fr)) == sorted(trous.findall(en)), fr
        # The code often splits these lines into several strings: we look for the start of
        # EACH fixed piece, short enough to fit in a single one.
        for morceau in trous.split(fr)[::2]:
            debut = re.sub(r"^\W+", "", morceau)[:8]
            if len(debut) >= 4 and debut not in source:
                morts.append((fr, debut))
    assert morts == []
