"""Country and region names follow the interface language; the data stays French."""

from jobhunter.app import countries as C
from jobhunter.scoring import zones as Z


def test_chaque_pays_du_moteur_a_sa_traduction():
    noms = (
        set(Z._PAYS_CANON)
        | set(Z._ISO_PAYS.values())
        | set(Z._WTJ_PAYS.values())
        | set(Z._REGIONS)
        | {"France", "États-Unis", "Europe"}
    )
    assert sorted(n for n in noms if n not in C.NOMS) == []


def test_langues():
    assert C.nom("Royaume-Uni", "en") == "United Kingdom"
    assert C.nom("Pays-Bas", "de") == "Niederlande"
    assert C.nom("Allemagne", "es") == "Alemania"
    assert C.nom("Royaume-Uni", "fr") == "Royaume-Uni"
    assert C.nom("?", "en") == "?"
