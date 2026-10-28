"""3.53: what a new profile collects — its specialty, its country, and the key it lacks.

Three fictional CVs (a mechanical engineer in Lyon, a waiter in Bordeaux, a lawyer in
Paris) collected on 28/10/2026: the engineer's 375 offers held DevOps posts (the filter
passed « ingénieur » alone) and 126 offers from abroad; the waiter found one offer in
Bordeaux, France Travail's key being absent.
"""

from jobhunter import api_keys
from jobhunter import profile as P
from jobhunter.programs import first_launch as fl


def test_les_deux_parties_dans_n_importe_quel_ordre():
    rx = P.motif(["ingénieur / engineer + mécanique / mechanical"])
    assert P.cherche(rx, "Ingénieur conception mécanique H/F")
    assert P.cherche(rx, "Senior Mechanical Engineer")
    assert not P.cherche(rx, "Ingénieur DevOps")
    assert not P.cherche(rx, "Technicien mécanique")
    # "c++" is a word, not two parts.
    assert P.cherche(P.motif(["c++"]), "Développeur C++")


def test_une_tete_large_demande_sa_specialite():
    mots = fl.filtre_metier(
        ["engineer", "ingénieur", "mécanique", "mechanical"], ["méthodes", "technicien"]
    )
    assert mots[0] == "engineer / ingénieur + mécanique / mechanical"
    assert "ingénieur" not in mots and "technicien" not in mots
    assert "mécanique" in mots and "méthodes" in mots
    rx = P.motif(mots)
    assert P.cherche(rx, "Chargé d'études mécanique")
    assert not P.cherche(rx, "Ingénieur DevOps / Ingénieure DevOps")


def test_une_tete_precise_reste_seule():
    assert fl.filtre_metier(["avocat", "lawyer"], ["juridique"]) == [
        "avocat",
        "lawyer",
        "juridique",
    ]
    # A broad head without a specialty is all there is.
    assert fl.filtre_metier(["consultant"], []) == ["consultant"]


def test_la_cle_conseillee(tmp_path):
    assert api_keys.conseillee(tmp_path, "fr") == "francetravail"
    assert api_keys.conseillee(tmp_path, "de") == "adzuna"
    assert api_keys.conseillee(tmp_path, "jp") is None
    api_keys.enregistrer(tmp_path, "francetravail", {"client_id": "x", "client_secret": "y"})
    assert api_keys.conseillee(tmp_path, "fr") is None
