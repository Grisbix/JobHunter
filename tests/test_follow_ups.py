"""The week's follow-up drafts are ready, nothing is sent (relances).

One draft per follow-up due, the right template (D+7 the first time, D+10 after a
follow-up), no draft retouched by hand is overwritten, and the report says
clearly that nothing is sent. Converted from Scripts/test_follow_ups.py.
"""

import pytest

from jobhunter.programs import follow_ups as R

A = {"entreprise": "Amundi", "poste": "Analyste ESG"}
B = {"entreprise": "Covéa Finance", "poste": "Analyste PAI"}
LISTE = [(A, "postulé", "2026-09-20", 18), (B, "relancé", "2026-09-27", 11)]


@pytest.fixture
def prepares(tmp_path):
    bilan = R.preparer_brouillons(LISTE, dossier=tmp_path)
    return tmp_path, bilan


def test_premiere_relance_modele_j7(prepares):
    assert R.chemin_brouillon(A, 7, prepares[0]).exists()


def test_deja_relancee_modele_j10(prepares):
    assert R.chemin_brouillon(B, 10, prepares[0]).exists()


def test_pas_de_j7_si_deja_relancee(prepares):
    assert not R.chemin_brouillon(B, 7, prepares[0]).exists()


def test_brouillon_nomme_entreprise_et_poste(prepares):
    texte = R.chemin_brouillon(A, 7, prepares[0]).read_text(encoding="utf-8")
    assert "Analyste ESG chez Amundi" in texte


def test_j10_est_la_derniere_relance(prepares):
    assert "dernière relance" in R.chemin_brouillon(B, 10, prepares[0]).read_text(encoding="utf-8")


@pytest.fixture
def retouche(prepares):
    fa = R.chemin_brouillon(A, 7, prepares[0])
    fa.write_text("version retouchée", encoding="utf-8")
    return fa, R.preparer_brouillons(LISTE, dossier=prepares[0])


def test_retouche_conservee(retouche):
    assert retouche[0].read_text(encoding="utf-8") == "version retouchée"


def test_bilan_deja_pret(retouche):
    assert "déjà prêt" in retouche[1]


def test_bilan_dit_que_rien_n_est_envoye(prepares):
    assert "rien n'est envoyé" in prepares[1]


def test_bilan_compte_les_relances(prepares):
    assert "**2 candidature(s)**" in prepares[1]


def test_bilan_donne_la_commande_de_marquage(prepares):
    assert "--mark" in prepares[1]


def test_liste_vide_message_clair(tmp_path):
    assert "Rien à relancer" in R.preparer_brouillons([], dossier=tmp_path)
