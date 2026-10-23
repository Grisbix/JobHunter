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


class _Horloge:
    def __init__(self) -> None:
        self.t = 1000.0

    def __call__(self) -> float:
        return self.t


def test_plan_annonce_pourcentage_et_temps_restant(capsys):
    R.plan(["ats", "linkedin", "vie"], {"ats": 60.0, "linkedin": 240.0})
    h = _Horloge()
    p = P.Progression(horloge=h)
    assert p.lire(capsys.readouterr().out)
    assert p.prevues == {"ats": 60.0, "linkedin": 240.0, "vie": None}
    p.lire("»» source ats début")
    h.t += 60
    p.lire("»» source ats fin ok 40 60.0")
    p.lire("»» source linkedin début")
    h.t += 120
    # vie, never measured, counts as the mean of the others (150 s): 450 s in all,
    # 60 + 120 done, 120 + 150 left.
    assert p.entete() == "1/3 sources · 40 % · ~4 min restantes · 40 offres trouvées"
    assert p.bande().splitlines()[1] == "ats ✓ 40  ·  linkedin …"


def test_source_plus_longue_que_d_habitude_jamais_finie_a_100():
    h = _Horloge()
    p = P.Progression(horloge=h)
    p.lire("»» plan ats:10.0")
    p.lire("»» source ats début")
    h.t += 500
    assert p.entete().startswith("0/1 sources · 95 % · ~0 s restantes")


def test_lignes_du_pipeline_prefixees_par_les_minutes():
    p = P.Progression()
    assert p.lire("   12.3' »» bilan 5 nouvelles\n")
    assert p.nouvelles == 5
    assert not p.lire("note : »» bilan 5 nouvelles\n")


def test_passes_successives_additionnent_leur_plan():
    p = P.Progression()
    p.lire("»» plan ats:1.0 linkedin:2.0")
    p.lire("»» plan efc:3.0")
    assert list(p.prevues) == ["ats", "linkedin", "efc"]
    p.lire("»» bilan 12 nouvelles")
    assert p.entete().endswith("12 nouvelles ajoutées")


def test_plan_sans_mesure_garde_un_defaut():
    p = P.Progression()
    p.lire("»» plan ats")
    assert "~1 min restantes" in p.entete()


def test_verification_pourcentage_temps_et_fermees():
    h = _Horloge()
    p = P.Progression(horloge=h)
    assert p.lire("»» verif 0 400 0 1800")
    h.t += 100
    p.lire("»» verif 100 400 6 1700")
    # 1 s per offer, 300 left: 5 min, below the 1700 s limit.
    assert p.entete() == "Vérification 100/400 · 25 % · ~5 min restantes · 6 fermée(s)"
    p.lire("»» verif 100 400 6 120")
    assert "~2 min restantes" in p.entete()  # the time limit comes first
    p.lire("»» verif 400 400 9")
    assert p.lire("»» verif retirees 9")
    assert p.bilan() == (
        "Vérification des offres : Vérification 400/400 · 100 % · 9 fermée(s) · "
        "9 retirée(s) de la file."
    )


def test_duree_lisible():
    assert P.duree_lisible(45) == "45 s"
    assert P.duree_lisible(359) == "6 min"
    assert P.duree_lisible(3900) == "1 h 05"


def test_durees_habituelles_mediane_des_dernieres():
    lignes = [{"sources": {"ats": {"duree": d}}} for d in (100, 10, 20, 30, 40, 50)]
    lignes.append({"sources": {"vie": {"duree": "x"}, "wtj": {}}})
    assert R.durees_habituelles(lignes) == {"ats": 30.0}
