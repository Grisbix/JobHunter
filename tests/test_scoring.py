"""The fit, the required experience and the traps of the scoring (ats_match).

`ats_match` decides which offers receive a CV and a letter. Its main
rule ran DEAD: `_ESG_TITLE_RX` started with a backspace, so
"an ESG title lifts the cap to 10" never applied, without error.
Converted from Scripts/test_scoring.py.
"""

import re

import pytest

from jobhunter.programs import util as jutil
from jobhunter.scoring import fit as ats_match
from jobhunter.scoring.fit import (
    _ESG_DENSITE_MIN,
    _ESG_TITLE_RX,
    axis_scores,
    densite_esg,
    experience_years,
    fit_detail,
    fit_score,
)

# A long, hollow text, so that the ESG density is computed on volume.
REMPLISSAGE = "Nous accompagnons nos clients dans leurs projets. " * 60
ESG_PUR = (
    "Analyste ESG. Missions : analyse extra-financière, reporting CSRD, "
    "taxonomie européenne, SFDR articles 8 et 9, notation ESG des émetteurs, "
    "empreinte carbone et trajectoire climat, due diligence ESG."
)
BASE = (
    "Analyse ESG, reporting CSRD, taxonomie, SFDR, empreinte carbone, "
    "notation ESG, due diligence ESG, analyse extra-financière."
)
FIN = (
    "Missions : analyse financière, modélisation Excel, valorisation DCF, "
    "analyse de bilan, comptabilité IFRS, M&A, corporate finance."
)
IA = (
    "Missions : LLM, agents IA, RAG, intelligence artificielle générative, "
    "machine learning, Python, déploiement de modèles."
)


def fit(texte, titre):
    return fit_score(texte, titre)[0]


# ── A. the patterns are not corrupted ────────────────────────────────────────
# A \b becomes \x08 (heredoc) or a literal backslash: the pattern compiles and
# no longer matches anything.
def test_tous_les_motifs_sont_sains():
    assert jutil.verifier_motifs(vars(ats_match), minimum=4) >= 4


MOTIFS = [n for n, v in vars(ats_match).items() if isinstance(v, re.Pattern)]


@pytest.mark.parametrize("nom", MOTIFS)
def test_motif_sans_backspace(nom):
    assert "\x08" not in getattr(ats_match, nom).pattern


# ── B. the ESG title lifts the cap (the rule that was dead) ───────────────
@pytest.mark.parametrize(
    ("titre", "esg"),
    [
        ("Analyste ESG", True),
        ("Sustainability Manager", True),
        ("Chargé de mission RSE", True),
        ("Analyste extra-financier", True),
        ("Climate Risk Analyst", True),
        ("E&S Analyst", True),
        ("Analyste CSRD", True),
        ("Responsable décarbonation", True),
        # that is what the \b boundaries are for: without them, "rse" matches "diveRSE"
        ("Diverse Talent Partner", False),
        ("Sparse Data Engineer", False),
        ("Trading Market Risk Analyst", False),
        ("Client Services Consultant", False),
    ],
)
def test_intitule_esg(titre, esg):
    assert bool(_ESG_TITLE_RX.search(titre.lower())) is esg


# ── C. a clear ESG offer scores high ────────────────────────────────────────
def test_offre_esg_pure_au_maximum():
    # the saturated ESG axis is worth 3.0; the target was 4.0 and the offer capped at 8
    assert fit(ESG_PUR, "Analyste ESG") == 10


def test_esg_et_finance_au_maximum():
    texte = (
        ESG_PUR
        + " Analyse financière, modélisation financière, valorisation DCF, gestion d'actifs."
    )
    assert fit(texte, "Analyste ESG") == 10


def test_sans_esg_le_plafond_tient():
    texte = (
        "Analyse financière, modélisation financière, valorisation DCF, gestion d'actifs, "
        "contrôle de gestion, audit, gestion des risques, conseil et stratégie, Python et SQL."
    )
    assert 1 <= fit(texte, "Financial Analyst") <= 8


# ── D. CSR boilerplate does not make an ESG job ─────────────────────────────
# ExxonMobil "Trading Market Risk Analyst": 3 markers in 7940 characters, fit 10.
NOYE = (
    "Trading Market Risk Analyst. "
    + REMPLISSAGE
    + " Our commitment to sustainability. "
    + REMPLISSAGE
    + " We reduce our carbon footprint. "
    + REMPLISSAGE
    + " environmental stewardship matters. "
    + REMPLISSAGE
)


def test_densite_esg_sous_le_seuil():
    assert densite_esg(NOYE.lower()) < _ESG_DENSITE_MIN


def test_intitule_non_esg_et_rse_de_facade():
    assert 1 <= fit(NOYE, "Trading Market Risk Analyst") <= 8


def test_vraie_annonce_esg_au_dessus_du_seuil():
    dense = (
        "Analyste ESG. "
        + (
            "Analyse ESG, reporting CSRD, taxonomie, SFDR, empreinte carbone, "
            "climat, biodiversité, durabilité. "
        )
        * 12
    )
    assert densite_esg(dense.lower()) >= _ESG_DENSITE_MIN


# ── E, F. the cap holds with the junior bonus; junior is read in the TITLE ─
def test_junior_sans_esg_reste_sous_le_plafond():
    texte = (
        "Auditeur junior. Analyse financière, modélisation financière, valorisation DCF, "
        "audit et comptabilité, contrôle de gestion, gestion des risques, conseil et "
        "stratégie, Python et SQL."
    )
    assert 1 <= fit(texte, "Auditeur junior analyste") <= 8


def test_alternant_dans_le_corps_ne_donne_pas_le_bonus():
    corps = (
        "Analyse financière, modélisation financière, valorisation DCF. "
        "Ce poste est également ouvert aux alternants et aux stagiaires."
    )
    assert fit(f"Directeur financier {corps}", "Directeur financier") < fit(
        f"Analyste financier junior {corps}", "Analyste financier junior"
    )


# ── G, H. seniority and off-target role penalties ─────────────────────────────
def f_titre(titre):
    return fit(f"{titre} {BASE}", titre)


@pytest.mark.parametrize("titre", ["Head of ESG", "Directeur ESG"])
def test_junior_au_dessus_des_seniors(titre):
    assert f_titre("Analyste ESG junior") > f_titre(titre)


def test_titre_finissant_par_lead_prend_le_malus():
    assert f_titre("ESG Disclosure & Compliance Lead") < f_titre("Analyste ESG junior")


def test_lead_generation_n_est_pas_de_la_seniorite():
    assert f_titre("ESG Lead Generation Analyst") > f_titre("ESG Disclosure & Compliance Lead")


def test_role_commercial_penalise():
    assert f_titre("Commercial ESG") < f_titre("Analyste ESG junior")


# ── I. experience requise ──────────────────────────────────────────────────────
@pytest.mark.parametrize(
    ("texte", "ans"),
    [
        ("10 ans d'expérience exigée", 10),
        ("5 years of experience required", 5),
        ("expérience professionnelle antérieure de 3 à 5 ans", 3),  # range: its lower bound
        ("Niveau d'expérience \r\n \r\n \r\n Plus de 10 ans", 10),  # blancs ecrases
        ("Alternance. Société fondée il y a 10 ans.", 0),  # an isolated "10 ans" is noise
        ("40 ans d'expérience de notre société", 0),  # beyond 15: age or seniority
        ("Poste ouvert à tous profils", 0),
    ],
)
def test_experience_years(texte, ans):
    assert experience_years(texte) == ans


# Seven of the twenty offers set aside by October 2026 asked for experience unseen.
@pytest.mark.parametrize(
    ("texte", "titre", "ans"),
    [
        (
            "vous justifiez de 2 années d'expérience minimum (stages et alternance compris)",
            "Analyste ESG Junior",
            2,
        ),
        ("4 à 6 ans d’expérience au total ; encadrement (alternant, stagiaire)", "Gestionnaire", 4),
        (
            "Experience: Minimum of 5 years of experience. INTERNSHIP JOBS",
            "Financial Accountant",
            5,
        ),
        ("Expérience de 3 ans minimum en Business Analysis", "Product Owner", 3),
        ("Requirements: 1-2 years of relevant Finance experience", "Financing Accountant", 1),
        ("At least 2 years of relevant post-undergraduate professional experience", "Analyst", 2),
        ("Expérience confirmée en gestion de projets à impact", "Chargé de projet", 3),
        ("Niveau hiérarchique Confirmé Type d’emploi Temps plein", "Analyste", 3),
        ("Niveau hiérarchique Directeur Type d’emploi", "M&A", 7),
        ("Une première expérience confirmée en ESG", "Analyste", 0),
        ("une équipe apportant en moyenne 10 ans d'expérience ESG", "Analyste", 0),
        ("over 15 years of working together with clients", "Energy Analyst", 0),
        ("across the 3.5 years of the programme", "Finance Grad Programme 2027", 0),
        ("société avec plus de 10 ans d'expertise en IA", "AI Engineer", 0),
        ("10 ans d'expérience de l'équipe", "Stagiaire ESG", 0),  # a junior TITLE: noise
    ],
)
def test_experience_lue_sur_le_texte_offre_junior_sur_l_intitule(texte, titre, ans):
    assert experience_years(texte, titre) == ans


# ── J. the experience penalty crushes the fit ───────────────────────────────────────
def test_dix_ans_detectes():
    assert fit_score(f"Analyste ESG {BASE} 10 ans d'expérience exigée", "Analyste ESG")[1] == 10


def test_dix_ans_font_chuter_le_fit():
    assert (
        fit(f"Analyste ESG {BASE} 10 ans d'expérience exigée", "Analyste ESG")
        <= fit(f"Analyste ESG {BASE}", "Analyste ESG") - 4
    )


def test_trois_ans_coutent_moins_que_dix():
    assert fit(f"Analyste ESG {BASE} 3 ans d'expérience exigée", "Analyste ESG") > fit(
        f"Analyste ESG {BASE} 10 ans d'expérience exigée", "Analyste ESG"
    )


# ── K. bounds and robustness ────────────────────────────────────────────────────
VIDES = [("", ""), (None, None), ("x", "x"), ("   ", "   ")]


@pytest.mark.parametrize(("texte", "titre"), VIDES)
def test_fit_borne(texte, titre):
    assert 1 <= fit_score(texte, titre)[0] <= 10


@pytest.mark.parametrize(("texte", "titre"), VIDES)
def test_experience_nulle(texte, titre):
    assert fit_score(texte, titre)[1] == 0


def test_competences_generiques_insuffisantes():
    assert fit("Excel, Anglais, Communication", "Assistant administratif") <= 3


# ── L. the ESG axis is the only one dampened by density ────────────────────────────
def test_axe_finance_non_attenue():
    texte = (
        "Analyse financière, modélisation financière, valorisation DCF, audit et "
        "comptabilité. " + REMPLISSAGE
    )
    assert axis_scores(texte.lower())["finance"] > 0.5


# ── M. who lifts the cap: ESG-finance yes, HSE and technical no ─────────────
@pytest.mark.parametrize(
    "titre",
    [
        "Chargé de Sécurité, Santé et Environnement H/F",
        "Chargé de Mission HSE F/H",
        "Sustainability (EHS) Engineer",
        "Ingénieur QHSE H/F",
        "Environmental Health & Safety Specialist",
    ],
)
def test_hse_plafonne_a_6(titre):
    assert fit(f"{titre} {ESG_PUR}", titre) <= 6


# THE TEXT IS FIXED, ONLY THE TITLE VARIES: lifting the cap through the title.
MENTION = (
    "Missions : analyse financière, modélisation financière, valorisation DCF, "
    "analyse sectorielle, suivi du bilan carbone du site."
)


@pytest.mark.parametrize("titre", ["Analyste climat", "Sustainability Analyst"])
def test_intitule_esg_leve_le_plafond(titre):
    assert fit(MENTION, titre) > fit(MENTION, "Chargé de mission")


@pytest.mark.parametrize(
    "titre",
    [
        "Ingénieur Climatologue F/H",
        "Technicien études génie climatique F/H",
        "Sustainability Engineer",
    ],
)
def test_intitule_technique_n_apporte_rien(titre):
    assert fit(MENTION, titre) <= fit(MENTION, "Chargé de mission")


@pytest.mark.parametrize(
    "titre",
    [
        "Analyste ESG",
        "Responsable RSE et HSE",
        "ESG Data Engineer",
        "Associate, Investment Stewardship",
        "Analyste ISR",
        "Ingénieur financier ESG",
        # N. what MUST stay in the target
        "ESG Research Analyst",
        "Sustainable Procurement ESG Analyst",
        "Research Analyst - Sustainable Investing",
        "ESG Data Scientist",
        "Portfolio Construction Analyst - ESG",
        "Ingénieurs auditeur financier ESG",
    ],
)
def test_garde_son_10(titre):
    assert fit(f"{titre} {ESG_PUR}", titre) == 10


@pytest.mark.parametrize(
    "titre",
    ["Chargé d'Investissements en Venture Santé", "Operational Risk Management IT & Sécurité"],
)
def test_mot_isole_echappe_au_veto_hse(titre):
    assert ats_match._titre_hse(titre.lower()) is False


# ── N. off-target professions: green vocabulary no longer carries them to 10 ─────────
@pytest.mark.parametrize(
    "titre",
    [
        "Research Assistant/Associate (Centre for Sustainable Medicine)",
        "Assistant Professor (Nature-based Climate Solutions)",
        "Doctoral student in energy and environmental systems analysis",
        "Chef(fe) de Projet Batiment Durable",
        "Gestionnaire administratif·ve de l'alliance européenne EU GREEN",
        "Procurement Risk, Sustainability & Programs Specialist",
        "Supply Chain Sustainability and Compliance Analyst",
        "Graduate Environmental Scientist (Dublin)",
        "Athlete Welfare and Sustainability Coordinator",
        "Engineer (m/w/d) Sustainability & Product Compliance",
        "Ingénieur Santé Environnement et Risque Industriel",
    ],
)
def test_hors_cible_plafonne_a_6(titre):
    assert fit(f"{titre} {ESG_PUR}", titre) <= 6


@pytest.mark.parametrize(
    "titre", ["Research Analyst", "Data-Scientist", "Ingénieurs auditeur financier"]
)
def test_pas_hors_cible(titre):
    assert ats_match._titre_hors_cible(titre.lower()) is False


# Classic financial analyst (2026-10-07): above the old cap of 6.
@pytest.mark.parametrize(
    "titre",
    [
        "Analyste financier junior",
        "Financial Analyst",
        "Investment Analyst",
        "Contrôleur de gestion junior",
        "Credit Analyst",
    ],
)
def test_finance_classique_au_dessus_de_6(titre):
    assert fit(f"{titre} {FIN}", titre) >= 7


def test_l_esg_reste_devant_la_finance():
    assert fit(f"Analyste ESG {ESG_PUR}", "Analyste ESG") > fit(
        "Financial Analyst Missions : budget, reporting mensuel.", "Financial Analyst"
    )


def test_data_engineer_ne_profite_pas_de_la_regle_finance():
    assert fit(f"Data Engineer {FIN}", "Data Engineer") <= 7


def test_ai_engineer_garde_le_plafond_ia():
    assert fit(f"AI Engineer {IA}", "AI Engineer") >= 7


# ── fit_fin (2026-10-09): breaks ties without moving any fit ──────
TEXTES = [
    ("Analyste ESG", f"Analyste ESG {ESG_PUR}"),
    ("Financial Analyst", f"Financial Analyst {FIN}"),
    ("AI Engineer", f"AI Engineer {IA}"),
    ("Data Engineer", f"Data Engineer {FIN}"),
    ("Head of ESG", "Head of ESG 10 years of experience required"),
    ("Office Manager", "Office Manager accueil courrier"),
]


def test_arrondi_de_fit_fin_rend_le_fit():
    assert [
        (t, f, ff) for t, x in TEXTES for f, _y, ff in [fit_detail(x, t)] if round(ff) != f
    ] == []


def test_fit_detail_et_fit_score_s_accordent():
    assert all(fit_detail(x, t)[:2] == fit_score(x, t) for t, x in TEXTES)


def test_a_fit_egal_la_densite_esg_passe_devant():
    dense = fit_detail(f"Analyste ESG {ESG_PUR}", "Analyste ESG")
    maigre = fit_detail(
        f"Analyste ESG {ESG_PUR} " + "Le groupe et ses metiers. " * 60, "Analyste ESG"
    )
    assert dense[0] == maigre[0] and dense[2] > maigre[2]


# ── language: unreadable posting or required language not spoken ─────────────────────
# Example profile: French, English, German. An offer in Dutch came out at 10.
def test_annonce_en_neerlandais_plafond_2():
    nl = (
        "Wij zoeken een ESG analist voor ons team. Je bent verantwoordelijk voor de "
        "rapportage van het fonds, de SFDR en de CSRD. Wij bieden een uitdagende functie "
        "bij een duurzame organisatie en jij werkt nauw samen met onze collega's. "
    ) * 4
    assert fit(nl, "ESG Analist") <= 2


def test_neerlandais_exige_plafond_4():
    assert (
        fit(f"ESG Analyst {ESG_PUR} Fluent in English and Dutch is required.", "ESG Analyst") <= 4
    )


def test_neerlandais_a_plus_ne_change_rien():
    texte = f"ESG Analyst {ESG_PUR} Fluent English required; Dutch is a plus."
    assert fit(texte, "ESG Analyst") == 10


@pytest.mark.parametrize(
    ("texte", "attendu"),
    [
        ("Fluency in Dutch and/or French, with a good command of English.", ""),
        ("Fluent in English + French and/or Dutch (speaking all three is an asset)", ""),
        ("communication skills, in English and preferable in Dutch too, and others", ""),
        ("Strong presence in Chinese markets and fluency in English, Chinese markets", ""),
        ("Fluent in German and English, both written and spoken.", ""),
        ("Fluent in English and Swedish or Finnish.", "swedish"),
        ("Maîtrise du néerlandais exigée pour ce poste.", "néerlandais"),
        ("Profil Nederlandstalig met kennis van Engels.", "nederlands"),
    ],
)
def test_langue_exigee(texte, attendu):
    assert ats_match.langue_exigee(texte) == attendu


@pytest.mark.parametrize(
    "texte",
    [
        (
            "Nous recherchons pour notre équipe un analyste. Vous travaillerez avec les gérants sur "
            "le reporting des fonds et la CSRD dans une équipe. "
        )
        * 3,
        (
            "Wir suchen für unser Team eine Analystin. Sie arbeiten mit der Berichterstattung und "
            "das Reporting ist auf eine Stelle zu besetzen. "
        )
        * 3,
    ],
    ids=["fr", "de"],
)
def test_langue_parlee_sans_plafond(texte):
    assert ats_match.plafond_langue(texte)[0] == 10.0


# ── expliquer: the calculation in clear, without changing the calculation (G3) ────────────────


def test_raisons_ne_changent_pas_le_fit():
    for t, x in TEXTES:
        assert fit_detail(x, t, []) == fit_detail(x, t), t


def test_expliquer_cite_ce_qui_compte():
    from jobhunter.scoring.fit import expliquer

    raisons = expliquer(f"Analyste ESG junior {ESG_PUR}", "Analyste ESG junior")
    assert (
        raisons[-1]
        == f"fit {fit_detail(f'Analyste ESG junior {ESG_PUR}', 'Analyste ESG junior')[0]}"
    )
    assert any(r.startswith("esg ") for r in raisons)
    assert any("junior" in r for r in raisons)
    assert any("plafond 10" in r for r in raisons)
