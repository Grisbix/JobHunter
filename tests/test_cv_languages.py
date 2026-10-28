"""3.50: CVs written in German or Spanish, and CVs from London, Berlin, Tokyo, Madrid.

Measured on 2026-10-28 with four fictitious CVs: a German or Spanish CV was taken for
French (« fr » added to the spoken languages, the French gender question asked),
« 2022–heute » was not read as « still in the job », « English (fluent) » gave the
skill « Simulation numérique » (Ansys Fluent), and the secondary zone was the
country's own name (« España ») where postings write « Spain ».
"""

from jobhunter.programs import first_launch as fl

BERLIN = """Lena Muster
Juristin
Berlin, Deutschland · lena.muster@example.com
PROFIL
Volljuristin mit 3 Jahren Erfahrung im Arbeitsrecht und Datenschutz.
BERUFSERFAHRUNG
Syndikusrechtsanwältin — Beispiel AG, Berlin — 2022–heute
Beratung zu Arbeitsverträgen und Compliance für die Geschäftsführung.
Rechtsreferendarin — Kammergericht Berlin — 2020–2022
SPRACHEN
Deutsch (Muttersprache), Englisch (verhandlungssicher)
"""

MADRID = """Sofía Ejemplo
Responsable de Marketing Digital
Madrid, España · sofia.ejemplo@example.com
PERFIL
Especialista en marketing digital con experiencia en SEO y redes sociales.
EXPERIENCIA
Responsable de Marketing — Ejemplo Moda SL, Madrid — 2020–actualidad
Gestión de campañas para los clientes del sector y de los contenidos.
IDIOMAS
Español (nativo), Inglés (C1)
"""

LONDON = """Alex Example
Software Engineer
London, United Kingdom · alex.example@example.com
EXPERIENCE
Software Engineer — Example Payments Ltd, London — 2021–present
Built the payment APIs with the team and worked with the product managers.
LANGUAGES
English (native), French (intermediate)
"""


def test_langue_du_cv_allemand_et_espagnol():
    assert fl.langue_du_cv(BERLIN) == "de"
    assert fl.langue_du_cv(MADRID) == "es"
    assert fl.langue_du_cv(LONDON) == "en"
    assert fl.langue_du_cv("Chargée de communication, avec une expérience des réseaux.") == "fr"


def test_encore_en_poste_dans_quatre_langues():
    import datetime

    an = datetime.date.today().year
    assert fl.annees_des_dates("Juristin — 2022–heute") == an - 2022
    assert fl.annees_des_dates("Marketing — 2020–actualidad") == an - 2020
    assert fl.annees_des_dates("Analyst — 2021 bis heute") == an - 2021


def test_langues_nommees_dans_quatre_langues():
    assert fl.isos_du_cv(BERLIN) == ["de", "en"]
    assert fl.isos_du_cv(MADRID) == ["es", "en"]
    assert fl.isos_du_cv(LONDON) == ["en", "fr"]


def test_message_des_langues_sans_la_langue_du_cv():
    # A London CV says it speaks French; a French CV still leaves French out.
    assert fl.langues_du_cv(LONDON)[1] == "I speak French (intermediate)."
    assert fl.langues_du_cv(BERLIN)[1] == "I speak English (verhandlungssicher)."
    assert fl.langues_du_cv("LANGUES\nFrançais (natif), Anglais (C1)\n")[0] == (
        "Je parle anglais (C1)."
    )


def test_fluent_n_est_pas_une_competence():
    assert "Simulation numérique" not in fl.competences_du_cv("English (fluent)")
    assert "Simulation numérique" in fl.competences_du_cv("CFD avec Ansys Fluent")


def test_le_pays_n_est_pas_une_region():
    lignes = BERLIN.splitlines()
    assert fl.lieu_du_cv(lignes) == ("Berlin", "", "de")
    assert fl.lieu_du_cv(MADRID.splitlines()) == ("Madrid", "", "es")


def test_competences_affichees_en_anglais(monkeypatch):
    from jobhunter.web import i18n

    v = {"en": "negotiation"}
    monkeypatch.setattr(i18n, "langue", lambda: "en")
    assert fl._t_comp("Négociation", v) == "negotiation"
    monkeypatch.setattr(i18n, "langue", lambda: "fr")
    assert fl._t_comp("Négociation", v) == "Négociation"
