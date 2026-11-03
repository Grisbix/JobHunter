"""3.80: an internship said in the posting's text is an internship.

Crédit Agricole writes « Vous recherchez un stage en finance durable ? » and labels the
job CDD: four such internships were first of the queue at fit 10 (2026-11-03), while
the user excludes Stage and Alternance.
"""

import pytest

from jobhunter.scoring import sorting
from jobhunter.sources import common as C

CA = "Vous recherchez un stage en Finance Durable ? Alors postulez ! " + "Missions. " * 10


@pytest.mark.parametrize(
    "texte",
    [
        CA,
        "Profil : vous recherchez un stage de 6 mois à partir de janvier.",
        "La Direction Financière recherche un stagiaire motivé et autonome.",
        "Inclusive business (H/F) Stage de 6 mois à débuter en janvier 2027.",
        "Join us for a 6-month internship in our ESG team.",
        "This internship is based in Paris.",
    ],
)
def test_offre_de_stage(texte):
    assert C.offre_de_stage(texte)


@pytest.mark.parametrize(
    "texte",
    [
        "Ce poste ne s'adresse pas aux personnes recherchant une alternance avec une école.",
        "CDD de 12 mois. Le poste est également ouvert à un stage de 6 mois.",
        "Après un premier stage en banque, vous maîtrisez Excel.",
        "Analyste ESG en CDI, deux ans d'expérience.",
    ],
)
def test_pas_une_offre_de_stage(texte):
    assert not C.offre_de_stage(texte)


def test_le_contrat_lu_dans_le_texte_est_stage():
    assert C.contrat_de_la_description(CA + "Contrat : CDD") == "Stage"


def _offre(**kw):
    return {
        "poste": "Analyste Sustainable Investment Banking H/F",
        "entreprise": "CA",
        "url": "https://x/1",
        **kw,
    }


def test_le_tri_retire_un_stage_exclu(monkeypatch):
    monkeypatch.setattr(sorting, "_CONTRATS_EXCLUS", {"Stage", "Alternance"})
    assert sorting.motif(_offre(description=CA, contrat="CDD"), set()) == "contrat_exclu"
    assert sorting.motif(_offre(contrat="Stage"), set()) == "contrat_exclu"


def test_le_tri_garde_le_stage_si_rien_n_est_exclu(monkeypatch):
    monkeypatch.setattr(sorting, "_CONTRATS_EXCLUS", set())
    assert sorting.motif(_offre(description=CA, contrat="CDD"), set()) is None


def test_une_candidature_n_est_jamais_retiree(monkeypatch):
    from jobhunter.storage.queue import oid

    monkeypatch.setattr(sorting, "_CONTRATS_EXCLUS", {"Stage"})
    o = _offre(description=CA)
    assert sorting.motif(o, {oid(o)}) is None


def test_le_contrat_se_lit_dans_une_description_arrivee_apres():
    o = {"contrat": "non precise", "description": "Poste en CDI basé à Paris. " * 5}
    C.completer_contrat(o)
    assert o["contrat"] == "CDI"
    o = {"contrat": "V.I.E", "description": "Poste en CDI basé à Paris. " * 5}
    C.completer_contrat(o)
    assert o["contrat"] == "V.I.E"  # an announced contract is never overwritten


def test_doublon_meme_ville_ecrite_avec_ou_sans_trait_d_union():
    """3.80: « Le-Relecq-Kerhuon » and « Le Relecq-Kerhuon » are one place."""
    from jobhunter.programs import duplicates

    titre = "Consolideur - reporting extra-financier H/F"
    file = [
        {
            "entreprise": "Crédit Mutuel Arkea",
            "poste": titre,
            "localisation": "Le Relecq-Kerhuon, Bretagne",
            "fit": 7,
            "url": "https://a.fr/1",
        },
        {
            "entreprise": "CREDIT MUTUEL ARKEA",
            "poste": titre.replace("H/F", "F/H"),
            "localisation": "Le-Relecq-Kerhuon",
            "fit": 10,
            "url": "https://a.fr/2",
        },
    ]
    assert len(duplicates.doublons(file)) == 1
