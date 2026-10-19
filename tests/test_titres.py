"""Cleaning of the job title (tailor_application.titre_poste).

Cases taken from REAL titles found in the queue, not invented. Converted from
Scripts/test_titres.py; sections H and I passed the RESULT as the
condition there (`check(nom, valeur, attendu)`) and succeeded as soon as the title
was not empty: idempotence was not checked. It is here.
"""

import pytest

from jobhunter import documents as T


def objet(role):
    t = T.titre_poste(role)
    return f"Candidature au poste {T._de(t)}" if t else "Candidature spontanee"


MOTIFS = [n for n in dir(T) if n.startswith("RX_") and hasattr(getattr(T, n), "pattern")]


@pytest.mark.parametrize("nom", MOTIFS)
def test_motif_sans_backspace(nom):
    """Un « \\b » mange par un heredoc devient \\x08 : le motif ne matche plus jamais."""
    assert "\x08" not in getattr(T, nom).pattern


@pytest.mark.parametrize(
    "src",
    [
        "Analyste ESG (H/F)",
        "ACTUAIRE (F/H)",
        "Actuaire (h/f)",
        "Junior Analyste ESG Mode - (H/F/X)",
        "Consultant junior H/F",
    ],
)
def test_genre_retire(src):
    assert not T.RX_GENRE.search(T.titre_poste(src))


@pytest.mark.parametrize(
    "src",
    [
        "Analyste Quantitatif ESG (H/F) CDI",
        "Adjoint Risque Clients (F/H) - CDD",
        "CDD - Junior Analyste ESG Mode",
        "Intern Analyst - 6 months - Product Specialist",
    ],
)
def test_contrat_retire(src):
    assert not T.RX_CONTRAT.search(T.titre_poste(src))


def test_trait_union_lcb_ft():
    assert T.titre_poste("Analyste LCB-FT CDD 3 mois H/F") == "Analyste LCB-FT"


def test_trait_union_h2_power():
    assert "H2-Power" in T.titre_poste("Junior Finance Controller - OPmobility H2-Power")


@pytest.mark.parametrize(
    ("mot", "attendu"),
    [("Hollande", "de Hollande"), ("Yves Rocher", "de Yves Rocher")],
    ids=["h aspire", "y"],
)
def test_elision_sans_apostrophe(mot, attendu):
    assert T._de(mot) == attendu


def test_elision_voyelle():
    assert objet("Analyste ESG") == "Candidature au poste d'Analyste ESG"


def test_elision_consonne():
    assert objet("Chargé de mission ESG").startswith("Candidature au poste de Chargé")


@pytest.mark.parametrize("src", ["Mérignac : 2 rue du Golf 33700 MÉRIGNAC", "", "   ", "H/F"])
def test_titre_inutilisable_formule_neutre(src):
    assert objet(src) == "Candidature spontanee"


LONG = (
    "2027 Corporate & Investment Bank - Global Investment Banking Analyst Program "
    "- Off-Cycle Internship - Zurich"
)


def test_longueur_bornee():
    # 80 and not 70: "Consultant, Climate Change and Sustainability Services
    # Financial Services - Geneva" was cut into an inverted department name.
    assert len(T.titre_poste(LONG)) <= 80


def test_coupe_sur_mot_entier():
    r = T.titre_poste(LONG)
    assert LONG.startswith(r) or r in LONG.replace("  ", " ")


def test_pas_de_ponctuation_orpheline():
    assert not T.titre_poste(LONG).endswith((" -", ",", ";", ":", "|", "-"))


@pytest.mark.parametrize(
    "src",
    [
        "Bras droit DAF – Finance & Processus F/H - GAYA",
        "Directeur DAF - Finance",
        "Analyste ESG (H/F)",
        "Analyste - M&A - F/H",
        "Responsable RH - Formation F/H",
    ],
)
def test_idempotence(src):
    """Cleaning again must change nothing: refresh_letters is made to be rerun."""
    une = T.titre_poste(src)
    assert T.titre_poste(une) == une


def test_daf_finance_survit():
    # Real trap: "F - F" seen as a gender mention gave "DA inance".
    attendu = "Bras droit DAF - Finance & Processus - GAYA"
    assert T.titre_poste("Bras droit DAF – Finance & Processus F/H - GAYA") == attendu


@pytest.mark.parametrize(
    ("src", "attendu"),
    [
        ("Market Risk Analyst Counterparty F/W", "Market Risk Analyst Counterparty"),
        ("Analyst F/M/X", "Analyst"),
    ],
)
def test_genre_trois_lettres(src, attendu):
    assert T.titre_poste(src) == attendu


REF = "Administrative Officer (P-2), TA, 364 days, #00137324, Education Cannot Wait"


def test_reference_annonce_retiree():
    assert "#" not in T.titre_poste(REF)


def test_pas_de_virgules_doublees():
    r = T.titre_poste(REF)
    assert ", ," not in r and ",," not in r
