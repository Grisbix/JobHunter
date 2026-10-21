"""Knock-out conditions a posting states (scoring.knockouts): flagged, never removed."""

import pytest

from jobhunter.scoring.knockouts import trouver


@pytest.mark.parametrize(
    ("texte", "attendu"),
    [
        ("Profil : bac+5. Permis B indispensable pour les déplacements.", ["permis exigé"]),
        ("Vous êtes titulaire du permis de conduire.", ["permis exigé"]),
        ("A valid driving licence is required for site visits.", ["permis exigé"]),
        ("Führerschein Klasse B zwingend erforderlich.", ["permis exigé"]),
        ("Poste soumis à condition : nationalité française requise.", ["nationalité FR"]),
        (
            "Applicants must be legally authorized to work in the United States.",
            ["droit de travail US"],
        ),
        ("U.S. citizenship required due to access to data.", ["droit de travail US"]),
        ("You have the right to work in the UK.", ["droit de travail UK"]),
        ("We are unable to offer visa sponsorship for this role.", ["pas de visa"]),
        ("Habilitation secret défense obligatoire.", ["habilitation"]),
        ("Active TS/SCI security clearance.", ["habilitation"]),
    ],
)
def test_trouve(texte, attendu):
    assert trouver(texte, {}) == attendu


@pytest.mark.parametrize(
    "texte",
    [
        "Permis B apprécié.",
        "A driving licence is a plus.",
        "A full driving licence may be required.",
        "Führerschein von Vorteil.",
        "Nos équipes à Paris, Londres et New York accompagnent les clients.",
        "",
    ],
)
def test_attenue_ou_absent(texte):
    assert trouver(texte, {}) == []


def test_le_profil_dit_ce_qui_est_rempli():
    texte = (
        "Permis B obligatoire. Must be authorized to work in the EU. Habilitation secret "
        "défense. We do not provide visa sponsorship."
    )
    assert trouver(texte, {}) == [
        "permis exigé",
        "droit de travail EU",
        "pas de visa",
        "habilitation",
    ]
    profil = {"permis": True, "habilitation": True, "droit_de_travail": ["FR"], "ignorer": ["visa"]}
    assert trouver(texte, profil) == []


def test_pas_de_visa_sans_objet_en_europe_pour_un_europeen():
    texte = "Legal authorization to work in Germany (no visa sponsorship provided)."
    assert trouver(texte, {"droit_de_travail": ["FR", "EU"]}, "Allemagne") == []
    assert trouver(texte, {"droit_de_travail": ["FR", "EU"]}, "Royaume-Uni") == ["pas de visa"]
    assert trouver(texte, {}, "Allemagne") == ["pas de visa"]
