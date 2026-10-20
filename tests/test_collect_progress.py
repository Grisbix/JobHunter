"""A collection's progress, shown by the application without a console (app.progress)."""

from jobhunter.app import progress as P
from jobhunter.sources import source_yield as R


def test_lignes_du_moteur_lues(capsys):
    R.progres("source linkedin début")
    R.progres(f"source linkedin fin {R.verdict(693, {})} 693 412.0")
    R.progres(f"source apec fin {R.verdict(0, {'apec HTTP 403': 3})} 0 4.6")
    R.progres(f"source efc fin {R.verdict(0, {})} 0 84.4")
    R.progres("bilan 136 nouvelles")
    p = P.Progression()
    lues = [p.lire(ligne + "\n") for ligne in capsys.readouterr().out.splitlines()]
    assert all(lues)
    assert p.sources == {
        "linkedin": ("ok", 693),
        "apec": ("refusé", 0),
        "efc": ("rien à prendre", 0),
    }
    assert p.nouvelles == 136
    assert p.bande() == "linkedin ✓ 693  ·  apec ⛔  ·  efc ∅"


def test_ligne_ordinaire_laissee_au_journal():
    p = P.Progression()
    assert not p.lire("── LinkedIn recherche publique (guest) ──\n")
    assert not p.lire("»» autre chose\n")
    assert p.bilan() == ""


def test_source_en_cours_puis_bilan():
    p = P.Progression()
    p.lire("»» source workday début")
    assert p.bande() == "workday …"
    p.lire("»» source ats fin limité 12 30.0")
    bilan = p.bilan()
    assert "? nouvelle(s)" in bilan  # the merge never said
    assert "1 source(s) sur 2" in bilan
    assert "limitées : ats" in bilan and "interrompues : workday" in bilan


def test_bilans_de_plusieurs_passes_additionnes():
    p = P.Progression()
    p.lire("»» source ats fin ok 3 1.0")
    p.lire("»» bilan 2 nouvelles")
    p.lire("»» bilan 5 nouvelles")
    assert p.nouvelles == 7
