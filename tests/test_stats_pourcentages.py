"""Statistiques without percentages unless asked for in Réglages (the user, 2026-11-04:
« de base ils ne doivent pas y être, ça fait trop chargé »)."""

from pathlib import Path

from jobhunter.web import api
from jobhunter.web.texts import TEXTES

JS = (
    Path(__file__).resolve().parent.parent / "src" / "jobhunter" / "web" / "static" / "app.js"
).read_text(encoding="utf-8")


def test_masques_par_defaut():
    assert api.reglages(None)["pourcentages"] is False
    assert api.reglages({"pourcentages": "oui"})["pourcentages"] is False


def test_affiches_sur_demande():
    assert api.reglages({"pourcentages": True})["pourcentages"] is True


def test_l_ecran_suit_le_reglage():
    stats = JS[JS.index("ECRANS.stats = {") :]
    stats = stats[: stats.index("\n};\n")]
    assert "reglagesCourants.pourcentages" in stats
    assert "p == null || !avecPc" in stats
    assert 'enregistrer({ pourcentages: v === "oui" })' in JS
    for cle in ("Pourcentages dans Statistiques", "Masqués", "Affichés"):
        assert cle in TEXTES
