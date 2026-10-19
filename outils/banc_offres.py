"""FICTITIOUS, deterministic offers for the non-regression bench.

Each offer combines a title, a description and a location, chosen to go through
the engine's decisions: ESG cap, classic finance, job vetoes, seniority, student,
technical tools, writing language and required language, zones and countries,
contracts. No real data: the companies are made up and the texts written for the
occasion.
"""

import itertools

INTITULES = [
    "Analyste ESG junior",
    "ESG Analyst",
    "Sustainable Finance Analyst",
    "Analyste ISR / extra-financier",
    "Chargé de mission RSE",
    "Climate Risk Analyst",
    "Junior Financial Analyst",
    "Analyste financier H/F",
    "Credit Analyst - Graduate",
    "Analyste crédit junior",
    "M&A Analyst",
    "FP&A Analyst",
    "Contrôleur de gestion junior",
    "Investment Analyst - Impact Fund",
    "Quantitative Analyst",
    "Data Engineer ESG",
    "AI Analyst - Sustainability",
    "Consultant junior Développement Durable",
    "Responsable HSE",
    "Acheteur responsable",
    "Stage - Analyste ESG",
    "V.I.E - ESG Reporting Analyst",
    "Senior Director ESG",
    "Head of Sustainable Investments",
    "Lead Generation Specialist",
    "Business Developer Green Finance",
    "Duurzaamheidsanalist",
    "Nachhaltigkeitsanalyst (m/w/d)",
    "Analista de sostenibilidad",
    "Graduate Programme Finance 2027",
    "Risk Analyst - Climate & ESG",
    "Chargé d'études extra-financières",
]

DESCRIPTIONS = [
    # ESG dense, francais
    "Au sein de l'équipe Investissement Responsable de Gestion Fictive, vous analysez la "
    "performance ESG des émetteurs, suivez les indicateurs climat (empreinte carbone, "
    "trajectoire 1,5 °C), contribuez au reporting SFDR et taxonomie européenne, et "
    "participez au dialogue actionnarial. Maîtrise d'Excel, appétence pour la finance "
    "durable. Première expérience en stage appréciée. Poste en CDI.",
    # ESG, anglais
    "Join the Sustainable Investment team of Fictive Capital. You will assess ESG risks "
    "and opportunities, build climate metrics (scope 1-3 emissions, temperature alignment), "
    "support SFDR and EU Taxonomy reporting and engage with portfolio companies. "
    "Strong analytical skills, fluent English and French. Graduate profile welcome.",
    # finance classique, anglais
    "Fictive Bank is looking for an analyst to join its corporate finance team: financial "
    "modelling, valuation (DCF, multiples), credit analysis, budgeting and reporting to "
    "management. Excel and PowerPoint required, VBA a plus. 0-2 years of experience.",
    # written in Dutch
    "Wij zoeken een analist voor ons team duurzaam beleggen. Je analyseert de ESG-prestaties "
    "van bedrijven en ondersteunt de rapportage. Je hebt een masterdiploma en je spreekt "
    "vloeiend Nederlands en Engels. Wij bieden een uitdagende baan in een groeiend team.",
    # anglais, neerlandais exige
    "We are looking for an ESG analyst to support our responsible investment process. "
    "You will screen companies, prepare ESG reports and work with portfolio managers. "
    "Fluency in Dutch is required. Fluent English. Master's degree in finance.",
    # anglais, neerlandais optionnel
    "ESG analyst role in our Amsterdam office: ESG data, climate scenarios, SFDR disclosures. "
    "Fluent English required; Dutch is a plus. Graduates are encouraged to apply.",
    # experience exigee
    "We are hiring an experienced professional with at least 7 years of experience in "
    "sustainable finance, team management and client relationship. Expert in ESG ratings "
    "and regulation. Senior position reporting to the CIO.",
    # etudiant
    "Internship for a final or penultimate year student in finance or sustainability, "
    "6 months starting in January, to support the ESG research team with data collection "
    "and company analysis.",
    # outils techniques
    "You will build data pipelines with Python, Spark, Airflow, Kubernetes, Terraform and "
    "dbt, deploy services on AWS with Docker, and maintain CI/CD with GitLab for our ESG "
    "data platform.",
    # company presentation only
    "Fictive Group is a global leader in its field, present in 40 countries with 20,000 "
    "employees. We believe in diversity and inclusion. Join us and shape the future.",
    # allemand
    "Für unser Team Nachhaltige Investments suchen wir eine/n Analyst/in. Sie analysieren "
    "ESG-Kriterien, erstellen Berichte und unterstützen das Portfoliomanagement. "
    "Sehr gute Deutsch- und Englischkenntnisse.",
    # V.I.E
    "Volontariat International en Entreprise de 12 mois au sein de la direction financière "
    "d'une filiale de Groupe Fictif : reporting extra-financier, collecte des données CSRD, "
    "analyse des indicateurs environnementaux. Anglais courant.",
]

LIEUX = [
    "Paris, Île-de-France, France",
    "Lyon, Auvergne-Rhône-Alpes, France",
    "Bordeaux, Nouvelle-Aquitaine, France",
    "Genève, Suisse",
    "Luxembourg",
    "Amsterdam, North Holland, Netherlands",
    "London, England, United Kingdom",
    "Berlin, Germany",
    "Singapore",
    "France (Remote)",
    "Marseille (13)",
    "Bruxelles, Belgique",
    "",
]

SOCIETES = [
    "Gestion Fictive",
    "Fictive Capital",
    "Fictive Bank",
    "Groupe Fictif",
    "Banque Imaginaire",
    "Conseil Exemple",
    "Asset Démo",
    "Énergie Témoin",
]


def offres():
    """Deterministic list of offers in the queue format (apply_queue.json)."""
    out = []
    for i, (titre, desc) in enumerate(itertools.product(INTITULES, DESCRIPTIONS)):
        out.append(
            {
                "entreprise": SOCIETES[i % len(SOCIETES)],
                "poste": titre,
                "description": desc,
                "localisation": LIEUX[i % len(LIEUX)],
                "url": f"https://exemple.org/offres/{i}",
                "missions": desc[:200] if i % 3 == 0 else "",
                "profil": "",
                "rh": "Madame Exemple" if i % 17 == 0 else "",
                "statut": "Scan 2026-10-17",
            }
        )
    return out
