"""Sweep: a profile from many fictitious CVs, every job and layout, checked automatically.

Each CV (42 jobs x one of four layouts: Word, Word in two columns, Canva-like PDF,
English Word) goes through `jobhunter profile` in its own throwaway data root, then a
second process loads that profile and checks what a new user would see:

  - identity read (first name, surname, email, phone), job proposed = the CV's title;
  - at least two skills of the job recognised;
  - the title filter keeps the person's own job, the domain is theirs, the sorting
    does not remove it, and a posting of that job scores at least 7;
  - the letter and the message: no "A COMPLETER", no dangling "Au fil de ce parcours",
    no double space, no hidden character; the CV comes out of the template.

Network-free, no LibreOffice (documents are checked as .docx). About 2 s per CV.

Run:
  python tools/sweep_cv.py                 # all, summary + failures
  python tools/sweep_cv.py --garder DIR    # keeps the data roots in DIR
  python tools/sweep_cv.py --seul infirm   # only the jobs whose title contains this
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ICI = Path(__file__).resolve().parent.parent

# title, years, summary (one sentence), skills, degree, languages
METIERS = [
    (
        "Infirmière",
        6,
        "Infirmière en service de médecine depuis six ans, habituée aux soins techniques et à la prise en charge des patients.",
        "Soins infirmiers, pansements, perfusions, transmissions, hygiène",
        "Diplôme d'État d'infirmier — IFSI Rennes",
        "Anglais (B1)",
    ),
    (
        "Aide-soignant",
        3,
        "Aide-soignant en EHPAD, attentif au confort et à l'hygiène des résidents.",
        "Soins d'hygiène, aide aux repas, transmissions, gériatrie",
        "Diplôme d'État d'aide-soignant",
        "Anglais (A2)",
    ),
    (
        "Pharmacienne",
        4,
        "Pharmacienne d'officine, conseil aux patients et gestion des stocks.",
        "Délivrance, conseil, gestion des stocks, pharmacovigilance",
        "Doctorat en pharmacie — Université de Lille",
        "Anglais (B2)",
    ),
    (
        "Kinésithérapeute",
        5,
        "Kinésithérapeute en cabinet libéral, rééducation orthopédique et sportive.",
        "Rééducation, massage, kinésithérapie respiratoire",
        "Diplôme d'État de masseur-kinésithérapeute",
        "Anglais (B1)",
    ),
    (
        "Conducteur de travaux",
        8,
        "Conducteur de travaux en gros œuvre, chantiers de logements collectifs.",
        "Planning de chantier, gestion des sous-traitants, sécurité, AutoCAD",
        "BTS Bâtiment",
        "Anglais (A2)",
    ),
    (
        "Électricienne",
        4,
        "Électricienne du bâtiment, installations neuves et rénovation.",
        "Habilitation électrique, câblage, tableaux électriques, lecture de plans",
        "CAP Électricien",
        "Anglais (A2)",
    ),
    (
        "Technicien de maintenance",
        5,
        "Technicien de maintenance industrielle sur lignes de production automatisées.",
        "Maintenance préventive, automatismes, mécanique, électrotechnique, GMAO",
        "BTS Maintenance des systèmes",
        "Anglais (B1)",
    ),
    (
        "Ingénieure qualité",
        3,
        "Ingénieure qualité dans l'industrie automobile, audits et amélioration continue.",
        "ISO 9001, audits qualité, AMDEC, Lean, 8D",
        "Diplôme d'ingénieur — INSA Lyon",
        "Anglais (C1)",
    ),
    (
        "Vendeuse",
        2,
        "Vendeuse en prêt-à-porter, conseil client et tenue du magasin.",
        "Conseil client, encaissement, merchandising, gestion des stocks",
        "Bac professionnel Commerce",
        "Anglais (B1)",
    ),
    (
        "Commercial B2B",
        6,
        "Commercial terrain en B2B, développement d'un portefeuille de PME.",
        "Prospection, négociation, CRM Salesforce, développement commercial",
        "Licence professionnelle commerce",
        "Anglais (B2)",
    ),
    (
        "Chef de rayon",
        7,
        "Chef de rayon en grande distribution, management d'une équipe de huit personnes.",
        "Management d'équipe, gestion des stocks, merchandising, commandes",
        "BTS MCO",
        "Anglais (A2)",
    ),
    (
        "Cuisinier",
        5,
        "Cuisinier en restauration traditionnelle, du poste chaud à la pâtisserie.",
        "Cuisine traditionnelle, HACCP, gestion des commandes, pâtisserie",
        "CAP Cuisine",
        "Anglais (A2)",
    ),
    (
        "Serveuse",
        2,
        "Serveuse en brasserie, service en salle et en terrasse.",
        "Service en salle, encaissement, accueil client, bar",
        "Bac professionnel",
        "Anglais (B1), Espagnol (A2)",
    ),
    (
        "Réceptionniste",
        3,
        "Réceptionniste d'hôtel quatre étoiles, accueil d'une clientèle internationale.",
        "Accueil, réservations, Opera PMS, encaissement",
        "BTS Tourisme",
        "Anglais (C1), Allemand (B1)",
    ),
    (
        "Cariste",
        4,
        "Cariste en entrepôt logistique, préparation et chargement des commandes.",
        "CACES 1, 3 et 5, préparation de commandes, gestion de stock, WMS",
        "CACES",
        "Anglais (A2)",
    ),
    (
        "Responsable logistique",
        9,
        "Responsable logistique d'une plateforme de 20 000 m², supply chain et transport.",
        "Supply chain, gestion des flux, WMS, management, Excel",
        "Master Logistique — Université du Havre",
        "Anglais (B2)",
    ),
    (
        "Chauffeur poids lourd",
        10,
        "Chauffeur poids lourd en régional, livraisons et tournées.",
        "Permis C et CE, FIMO, chargement, tachygraphe",
        "FIMO",
        "Anglais (A2)",
    ),
    (
        "Assistante de direction",
        6,
        "Assistante de direction auprès d'un comité de direction, organisation et suivi.",
        "Gestion d'agenda, Pack Office, organisation d'événements, rédaction",
        "BTS Support à l'action managériale",
        "Anglais (B2)",
    ),
    (
        "Comptable",
        6,
        "Comptable en cabinet, tenue et révision des comptes de PME.",
        "Comptabilité générale, TVA, bilans, Sage, Excel",
        "DCG — Lycée Thiers",
        "Anglais (B1)",
    ),
    (
        "Gestionnaire de paie",
        4,
        "Gestionnaire de paie sur un portefeuille de 300 salariés.",
        "Paie, DSN, Silae, droit social, charges sociales",
        "Licence professionnelle paie",
        "Anglais (A2)",
    ),
    (
        "Chargée de recrutement",
        3,
        "Chargée de recrutement en cabinet, profils techniques et commerciaux.",
        "Sourcing, entretiens, LinkedIn Recruiter, ATS, marque employeur",
        "Master Ressources humaines — IAE Lille",
        "Anglais (B2)",
    ),
    (
        "Responsable RH",
        10,
        "Responsable ressources humaines d'un site industriel de 400 salariés.",
        "Relations sociales, GPEC, droit du travail, recrutement, paie",
        "Master Ressources humaines",
        "Anglais (B2)",
    ),
    (
        "Développeur web",
        3,
        "Développeur web full stack, applications React et API Node.js.",
        "JavaScript, React, Node.js, SQL, Git",
        "Master Informatique — Université de Bordeaux",
        "Anglais (B2)",
    ),
    (
        "Data scientist",
        4,
        "Data scientist en assurance, modèles de tarification et de churn.",
        "Python, machine learning, SQL, scikit-learn, statistiques",
        "Master Data Science — ENSAE",
        "Anglais (C1)",
    ),
    (
        "Administrateur systèmes",
        7,
        "Administrateur systèmes et réseaux, parc Windows et Linux de 500 postes.",
        "Linux, Windows Server, Active Directory, réseaux, VMware",
        "BTS SIO",
        "Anglais (B2)",
    ),
    (
        "Cheffe de projet informatique",
        8,
        "Cheffe de projet informatique, déploiement d'ERP et conduite du changement.",
        "Gestion de projet, ERP SAP, agile, MOA, recette",
        "Master MIAGE",
        "Anglais (C1)",
    ),
    (
        "Chargée de marketing digital",
        3,
        "Chargée de marketing digital, campagnes d'acquisition et réseaux sociaux.",
        "SEO, Google Ads, réseaux sociaux, emailing, Google Analytics",
        "Master Marketing — Kedge",
        "Anglais (C1)",
    ),
    (
        "Graphiste",
        5,
        "Graphiste en agence, identités visuelles et supports print.",
        "Illustrator, Photoshop, InDesign, identité visuelle",
        "DN MADE Graphisme",
        "Anglais (B1)",
    ),
    (
        "Juriste",
        4,
        "Juriste en droit des affaires, contrats commerciaux et conformité.",
        "Droit des contrats, droit des sociétés, conformité, RGPD",
        "Master 2 Droit des affaires — Paris 1",
        "Anglais (C1)",
    ),
    (
        "Professeur des écoles",
        9,
        "Professeur des écoles en cycle 3, classe de CM1-CM2.",
        "Pédagogie, différenciation, gestion de classe",
        "Master MEEF",
        "Anglais (B2)",
    ),
    (
        "Formatrice",
        6,
        "Formatrice pour adultes en bureautique et compétences de base.",
        "Formation, ingénierie pédagogique, Pack Office",
        "Titre professionnel Formateur",
        "Anglais (B1)",
    ),
    (
        "Éducatrice spécialisée",
        5,
        "Éducatrice spécialisée en foyer de protection de l'enfance.",
        "Accompagnement éducatif, projet personnalisé, travail en équipe pluridisciplinaire",
        "Diplôme d'État d'éducateur spécialisé",
        "Anglais (A2)",
    ),
    (
        "Analyste financier",
        2,
        "Analyste financier junior en banque d'affaires, modélisation et évaluation.",
        "Modélisation financière, évaluation, Excel, analyse financière",
        "Master Finance — Dauphine",
        "Anglais (C1)",
    ),
    (
        "Contrôleuse de gestion",
        5,
        "Contrôleuse de gestion industrielle, budget et analyse des coûts.",
        "Contrôle de gestion, budget, reporting, SAP, Power BI",
        "Master CCA",
        "Anglais (B2)",
    ),
    (
        "Auditeur",
        3,
        "Auditeur financier en cabinet Big Four, missions de commissariat aux comptes.",
        "Audit, commissariat aux comptes, IFRS, Excel",
        "DSCG",
        "Anglais (C1)",
    ),
    (
        "Agent immobilier",
        6,
        "Agent immobilier en agence, transactions de logements anciens.",
        "Prospection, estimation, négociation, transaction immobilière",
        "BTS Professions immobilières",
        "Anglais (B1)",
    ),
    (
        "Agent de sécurité",
        4,
        "Agent de sécurité en centre commercial, rondes et contrôle d'accès.",
        "SSIAP 1, rondes, contrôle d'accès, secourisme",
        "CQP APS",
        "Anglais (A2)",
    ),
    (
        "Chargée RSE",
        3,
        "Chargée RSE, bilan carbone et reporting extra-financier d'un groupe industriel.",
        "Bilan carbone, CSRD, reporting extra-financier, analyse de cycle de vie",
        "Master Développement durable",
        "Anglais (C1)",
    ),
    (
        "Architecte",
        7,
        "Architecte DPLG, logements et équipements publics de la conception au chantier.",
        "Conception architecturale, Revit, AutoCAD, permis de construire",
        "Diplôme d'architecte DE",
        "Anglais (B2)",
    ),
    (
        "UX designer",
        4,
        "UX designer sur des applications mobiles, recherche utilisateur et prototypage.",
        "Figma, recherche utilisateur, prototypage, design system",
        "Master Design d'interaction",
        "Anglais (C1)",
    ),
    (
        "Technicien agricole",
        5,
        "Technicien agricole en coopérative, conseil aux exploitants en grandes cultures.",
        "Agronomie, conseil technique, grandes cultures, phytosanitaire",
        "BTS Agronomie",
        "Anglais (A2)",
    ),
    (
        "Assistant social",
        8,
        "Assistant social de secteur, accompagnement des familles et accès aux droits.",
        "Accompagnement social, accès aux droits, travail en réseau",
        "Diplôme d'État d'assistant de service social",
        "Anglais (A2)",
    ),
]
# English CVs: title, years, summary, skills, degree, languages
METIERS_EN = [
    (
        "Software Engineer",
        5,
        "Software engineer with five years of experience building backend services in Java and Go.",
        "Java, Go, Kubernetes, PostgreSQL, AWS",
        "MSc Computer Science — University of Edinburgh",
        "French (B1)",
    ),
    (
        "Marketing Manager",
        7,
        "Marketing manager with seven years of experience leading brand and digital campaigns.",
        "Brand strategy, Google Ads, SEO, team management",
        "MBA — London Business School",
        "French (B2)",
    ),
    (
        "Registered Nurse",
        6,
        "Registered nurse with six years of experience in emergency departments.",
        "Emergency care, triage, patient care, infection control",
        "BSc Nursing — King's College London",
        "French (A2)",
    ),
]
PRENOMS = ["Claire", "Hugo", "Nadia", "Yanis", "Léa", "Mathis", "Inès", "Bruno", "Sarah", "Omar"]
NOMS = ["Lefèvre", "Garnier", "Haddad", "Nguyen", "Rousseau", "Diallo", "Perrin", "Kowalski"]
VILLES = ["Lyon", "Nantes", "Toulouse", "Lille", "Bordeaux", "Strasbourg", "Rennes", "Marseille"]


def _sans_accent(s):
    import unicodedata

    return "".join(c for c in unicodedata.normalize("NFD", s) if not unicodedata.combining(c))


def _lignes(i, m, en=False):
    titre, ans, resume, comps, diplome, langues = m
    prenom, nom = PRENOMS[i % len(PRENOMS)], NOMS[i % len(NOMS)]
    ville = "London" if en else VILLES[i % len(VILLES)]
    tel = "+44 7700 900%03d" % i if en else "06 %02d %02d %02d %02d" % (10 + i, 20, 30, 40)
    email = _sans_accent(f"{prenom}.{nom}@exemple.fr".lower())
    t = (
        ("SUMMARY", "EXPERIENCE", "EDUCATION", "SKILLS", "LANGUAGES")
        if en
        else ("PROFIL", "EXPÉRIENCE", "FORMATION", "COMPÉTENCES", "LANGUES")
    )
    langues = ("English (native), " if en else "Français, ") + langues
    lignes = {
        "nom": f"{prenom} {nom.upper()}",
        "titre": titre,
        "contact": [email, tel, ville],
        "profil": (t[0], resume),
        "exp": (
            t[1],
            f"{2026 - ans}-2026 {titre} — Entreprise {i}, {ville}",
            resume.split(",")[0] + ".",
        ),
        "formation": (t[2], f"2019 {diplome}"),
        "comps": (t[3], comps),
        "langues": (t[4], langues),
    }
    attendu = {
        "prenom": prenom,
        "nom": nom,
        "email": email,
        "tel": tel,
        "titre": titre,
        "annees": ans,
        "en": en,
    }
    return lignes, attendu


def _docx(l, f, tableau=False):
    from docx import Document

    d = Document()
    if tableau:  # two columns: contact, skills and languages on the left
        g, dr = d.add_table(rows=1, cols=2).rows[0].cells
        g.text = l["nom"]
        for x in [
            l["titre"],
            *l["contact"],
            l["comps"][0],
            *l["comps"][1].split(", "),
            l["langues"][0],
            *l["langues"][1].split(", "),
        ]:
            g.add_paragraph(x)
        dr.text = l["profil"][0]
        for x in [l["profil"][1], *l["exp"], *l["formation"]]:
            dr.add_paragraph(x)
    else:
        for x in [
            l["nom"],
            l["titre"],
            " · ".join(l["contact"]),
            *l["profil"],
            *l["exp"],
            *l["formation"],
            *l["comps"],
            *l["langues"],
        ]:
            d.add_paragraph(x)
    d.save(f)


def _canva(l, f):
    import pymupdf

    def espace(s):
        return " ".join(s)

    doc = pymupdf.open()
    p = doc.new_page()
    prenom, nom = l["nom"].split(" ", 1)
    gauche = [
        prenom.upper(),
        nom.upper(),
        l["titre"],
        "",
        espace("CONTACT"),
        *l["contact"],
        "",
        espace(l["comps"][0]),
        *l["comps"][1].split(", "),
        "",
        espace(l["langues"][0]),
        *l["langues"][1].split(", "),
    ]
    droite = [
        espace(l["profil"][0]),
        *_couper(l["profil"][1]),
        "",
        espace(l["exp"][0]),
        *_couper(l["exp"][1]),
        *_couper(l["exp"][2]),
        "",
        espace(l["formation"][0]),
        *_couper(l["formation"][1]),
    ]
    for k, x in enumerate(gauche):
        p.insert_text((36, 60 + 15 * k), x.replace("—", "-"), fontsize=9)
    for k, x in enumerate(droite):
        p.insert_text((220, 60 + 15 * k), x.replace("—", "-"), fontsize=9)
    doc.save(f)


def _couper(s, n=60):
    mots, out, cur = s.split(), [], ""
    for m in mots:
        if len(cur) + len(m) > n:
            out.append(cur.strip())
            cur = ""
        cur += m + " "
    return [*out, cur.strip()]


def fabriquer(dossier):
    """The CVs, as (file, layout, expected)."""
    dossier.mkdir(parents=True, exist_ok=True)
    cvs = []
    for i, m in enumerate(METIERS):
        l, att = _lignes(i, m)
        mise = ("word", "colonnes", "canva")[i % 3]
        f = dossier / f"cv_{i:02d}_{mise}.{'pdf' if mise == 'canva' else 'docx'}"
        _canva(l, f) if mise == "canva" else _docx(l, f, tableau=mise == "colonnes")
        cvs.append((f, mise, att))
    for j, m in enumerate(METIERS_EN):
        l, att = _lignes(50 + j, m, en=True)
        f = dossier / f"cv_en_{j:02d}.docx"
        _docx(l, f)
        cvs.append((f, "anglais", att))
    return cvs


def _env(racine):
    env = {k: v for k, v in os.environ.items() if k != "PROFIL_JOBHUNTER"}
    env.update(
        JOBHUNTER_RACINE=str(racine), JOBHUNTER_PRINCIPALE=str(racine), PYTHONIOENCODING="utf-8"
    )
    return env


def verifier(racine, attendu):
    """In the profile's own process: the list of problems (empty = all good)."""
    sys.path.insert(0, str(ICI / "src"))
    from jobhunter import profile as _P
    from jobhunter.documents.cv import tailor_cv
    from jobhunter.documents.letter import tailor_letter
    from jobhunter.documents.message import message as message_offre
    from jobhunter.scoring.domains import classify_domaine
    from jobhunter.scoring.fit import fit_detail
    from jobhunter.scoring.sorting import motif
    from jobhunter.sources import title_ok

    pb = []
    ident = _P.get("identite", {}) or {}
    for cle, champ in (("prenom", "prenom"), ("nom", "nom"), ("email", "email")):
        if (ident.get(champ) or "").lower() != attendu[cle].lower():
            pb.append(f"{champ} lu « {ident.get(champ)} » au lieu de « {attendu[cle]} »")
    if "".join(attendu["tel"].split()) not in "".join((ident.get("telephone") or "").split()):
        pb.append(f"téléphone lu « {ident.get('telephone')} »")
    doms = _P.domaines()
    titre = attendu["titre"]
    if not doms[0].get("libelle", "").startswith(titre[:30]):
        pb.append(f"métier proposé « {doms[0].get('libelle')} »")
    experimente = _P.get("lettre.ton") == "experimente"
    if experimente != (attendu["annees"] >= 3):
        pb.append(f"{attendu['annees']} ans lus comme {'expérimenté' if experimente else 'junior'}")
    lg = "en" if attendu["en"] else "fr"
    for cle in (f"langues_{lg}", f"diplome_{lg}" if lg == "fr" else None):
        if cle and not _P.get(f"message.{cle}"):
            pb.append(f"message.{cle} vide")
    parcours = doms[0].get(f"parcours_{lg}") or ""
    debut = ("I am", "I ") if attendu["en"] else ("Je ",)
    if not parcours.startswith(debut):
        pb.append(f"parcours sans sujet : « {parcours[:40]} »")
    comps = _P.get("competences", {}) or {}
    techniques = [c for c, v in comps.items() if v.get("technique") is not False]
    if len(techniques) < 2:
        pb.append(f"{len(techniques)} compétence(s) métier : {', '.join(comps)}")
    for t in {titre, f"{titre} H/F"}:
        if not title_ok(t):
            pb.append(f"le filtre de titre écarte « {t} »")
    if classify_domaine(titre) != doms[0]["cle"]:
        pb.append(f"domaine de « {titre} » : {classify_domaine(titre)}")
    offre = {"entreprise": "Société Test", "poste": f"{titre} H/F", "url": "https://exemple.fr/1"}
    m = motif(offre, set())
    if m:
        pb.append(f"le tri retire « {titre} » ({m})")
    syn = [s for c in techniques[:4] for s in (comps[c].get("synonymes") or [])[:1]]
    texte = (
        f"Nous recherchons un(e) {titre} H/F. Missions : {', '.join(syn)}. "
        "Vous travaillerez au sein d'une équipe dynamique, en CDI."
    )
    fit = fit_detail(texte, f"{titre} H/F")[0]
    if fit < 7:
        pb.append(f"une annonce de son métier a fit {fit}")
    o = {
        "company": "Société Test",
        "role": f"{titre} H/F",
        "offer_text": texte,
        "missions": "",
        "profil": "",
        "domaine": classify_domaine(titre),
    }
    from docx import Document

    lt = Document(str(tailor_letter(dict(o), nom="essai_lettre")))
    lettre = "\n".join(p.text for p in lt.paragraphs)
    cv = tailor_cv(dict(o), nom="essai_cv")
    msg = message_offre(
        {
            "entreprise": "Société Test",
            "poste": f"{titre} H/F",
            "description": texte,
            "domaine": o["domaine"],
        },
        "fr",
    )
    for nom_doc, txt in (("lettre", lettre), ("message", msg)):
        for mauvais, dit in (
            ("A COMPLETER", "A COMPLETER"),
            ("  ", "double espace"),
            ("\x08", "caractère caché"),
            ("\n ", "paragraphe qui commence par un espace"),
        ):
            if mauvais in txt:
                pb.append(f"{nom_doc} : {dit}")
    if "Au fil de ce parcours" in lettre and not _P.domaines()[0].get("parcours_fr"):
        pb.append("lettre : « Au fil de ce parcours » sans parcours")
    if not cv or not Path(cv).exists():
        pb.append("CV non produit")
    return pb


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--garder", help="dossier où garder les CV et les racines de données")
    ap.add_argument("--seul", default="", help="seulement les métiers contenant ce texte")
    ap.add_argument("--verifier", nargs=2, help=argparse.SUPPRESS)  # racine, attendu (JSON)
    a = ap.parse_args()
    if a.verifier:
        print(
            json.dumps(verifier(Path(a.verifier[0]), json.loads(a.verifier[1])), ensure_ascii=False)
        )
        return 0
    base = Path(a.garder) if a.garder else Path(tempfile.mkdtemp(prefix="sweep_cv_"))
    cvs = [c for c in fabriquer(base / "cv") if a.seul.lower() in c[2]["titre"].lower()]
    echecs = 0
    for f, mise, att in cvs:
        racine = base / "racines" / f.stem
        for d in ("data", "profile"):
            (racine / d).mkdir(parents=True, exist_ok=True)
        r = subprocess.run(
            [sys.executable, str(ICI / "JobHunter.pyw"), "profile", str(f)],
            env=_env(racine),
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
            timeout=120,
        )
        if r.returncode:
            pb = [f"profile code {r.returncode} : {(r.stdout + r.stderr).strip()[-300:]}"]
        else:
            v = subprocess.run(
                [
                    sys.executable,
                    __file__,
                    "--verifier",
                    str(racine),
                    json.dumps(att, ensure_ascii=False),
                ],
                env=_env(racine),
                capture_output=True,
                text=True,
                timeout=120,
            )
            try:
                pb = json.loads(v.stdout.strip().splitlines()[-1])
            except (ValueError, IndexError):
                pb = [f"vérification plantée : {(v.stderr or v.stdout).strip()[-400:]}"]
        echecs += bool(pb)
        print(f"{'✓' if not pb else '✗'} {att['titre'][:32]:32} {mise:9} " + " · ".join(pb))
    print(f"\n{len(cvs) - echecs}/{len(cvs)} CV sans problème · données : {base}")
    return 1 if echecs else 0


if __name__ == "__main__":
    sys.exit(main())
