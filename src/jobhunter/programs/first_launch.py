#!/usr/bin/env python3
"""first_launch.py — creates YOUR profile from your CV.

    python JobHunter.pyw profile path/to/my_cv.pdf      (or .docx)
    python JobHunter.pyw profile my_cv.docx --auto      (no questions)

What the program does:
  1. reads the CV (PDF or Word): name, email, phone, LinkedIn, city, languages,
     recognised skills (catalogue_competences.py);
  2. asks you five questions: target jobs, years of experience, cities,
     agreements (il/elle), company lists;
  3. writes profil/profil.json — everything the engine knows about you —, copies the
     CV into CV/Modeles/, prepares sources_config.json (search keywords).

A .docx CV is PREFERABLE: the CVs generated per offer start from this template and
can insert the job title into it (write "[nom du poste]" in your headline). A .pdf CV
is sent as is.

Nothing is sent anywhere: everything stays in this folder.
Then: review profil/profil.json (the "A COMPLETER" fields above all).
"""

import argparse
import json
import re
import shutil
import sys
import unicodedata
from pathlib import Path

from jobhunter import root as _racine

# No stdout at all when imported by the windowed application (jobhunter.welcome).
if sys.stdout is not None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]  # console : TextIOWrapper
HERE = _racine.scripts()
RACINE = HERE.parent


from jobhunter.programs.skills_catalog import FAMILLES, catalogue  # noqa: E402

A_COMPLETER = "A COMPLETER"


# The questions and messages, in English when the interface is not in French (the
# system's language by default): a user in Ohio reads « First name », not « Prénom ».
_EN = {
    "\n1. Lecture du CV : {}": "\n1. Reading the CV: {}",
    "  ! Presque aucun texte lu. Un CV scanne (image) ne se lit pas : fournis un PDF texte ou un .docx.": "  ! Almost no text read. A scanned CV (image) cannot be read: give a text PDF or a .docx.",
    "  Rien n'est écrit. Relance avec le CV en .docx, ou donne --metiers.": "  Nothing written. Run again with the CV as .docx, or give --metiers.",
    "  nom : {} · email : {} · tel : {} · ville : {}": "  name: {} · email: {} · phone: {} · city: {}",
    "  {} competence(s) reconnue(s) : {}": "  {} skill(s) recognised: {}",
    "\n2. Quelques questions (Entree = valeur proposee)": "\n2. A few questions (Enter = proposed value)",
    "Prénom": "First name",
    "Nom": "Last name",
    "Email": "Email",
    "Téléphone": "Phone",
    "Ville": "City",
    "Métiers visés, séparés par des virgules (ex. : Chargé de communication, Community manager)": "Target jobs, separated by commas (e.g. Communications officer, Community manager)",
    "Années d'expérience professionnelle (stages compris)": "Years of work experience (internships included)",
    "Secteurs PRIORITAIRES (séparés par des virgules)": "PRIORITY places (separated by commas)",
    "Secteurs secondaires (vide = aucun)": "Secondary places (empty = none)",
    "Garder les ~90 entreprises de finance / ESG suivies par défaut ? (o/n)": "Keep the ~90 finance / ESG companies followed by default? (y/n)",
    "\n3. Ecriture": "\n3. Writing",
    "  ! Version Word impossible ({}) : le PDF part tel quel.": "  ! No Word version ({}): the PDF goes out as is.",
    "  CV modele     : {}": "  CV template   : {}",
    "  profil        : {}": "  profile       : {}",
    "  offres        : {} rangée(s) dans les domaines du nouveau profil": "  offers        : {} sorted into the new profile's fields",
    "  faits du CV   : {} (vide)": "  CV facts      : {} (empty)",
    "  recherche     : {} mot(s)-cle(s)": "  search        : {} keyword(s)",
    " · listes d'entreprises finance/ESG videes": " · finance/ESG company lists emptied",
    "\n4. A relire dans {}": "\n4. To read over in {}",
    "identite : champs « A COMPLETER »": "identite: fields « A COMPLETER »",
    "domaines[].parcours_fr : le paragraphe de parcours de tes lettres (3-4 phrases factuelles : formation, experiences, ce que tu apportes) — VIDE pour l'instant": "domaines[].parcours_fr: your letters' background paragraph (3-4 factual sentences: education, experience, what you bring) — EMPTY for now",
    "competences : seulement {} reconnue(s) — ajoute les tiennes (libelle + synonymes que les annonces emploient)": "competences: only {} recognised — add yours (label + the synonyms postings use)",
    "message.{} : une phrase chacun (pas trouvé dans le CV)": "message.{}: one sentence each (not found in the CV)",
    "CV en PDF : il partira tel quel. Fournis un .docx pour des CV adaptes a chaque offre": "CV as PDF: it goes out as is. Give a .docx for a CV adapted to each offer",
    "  rien d'obligatoire : tout ce qu'il faut a été lu dans le CV": "  nothing required: everything needed was read in the CV",
    "\nVerifier : python JobHunter.pyw show-profile   ·   Lancer l'app : python JobHunter.pyw": "\nCheck: python JobHunter.pyw show-profile   ·   Start the app: python JobHunter.pyw",
    "(renseigné)": "(filled in)",
    "(à compléter)": "(to fill in)",
}


def _t(texte: str) -> str:
    """`texte` in the interface's language: French, or English otherwise."""
    from jobhunter.web import i18n

    return texte if i18n.langue() == "fr" else _EN.get(texte, texte)


def _t_comp(libelle: str, v: dict) -> str:
    """A skill's label in the interface's language (the catalogue's `en` outside French)."""
    return libelle if _t("Prénom") == "Prénom" else (v.get("en") or libelle)


def _oui(r: str) -> bool:
    """« o » / « oui » or « y » / « yes »."""
    return r.strip().lower().startswith(("o", "y"))


# ── 1. Reading the CV ────────────────────────────────────────────────────────


def lire_cv(chemin):
    return _titres_serres(_lire_cv(chemin))


def _titres_serres(texte):
    """A Canva heading spaced out letter by letter ("C O M P É T E N C E S") is read as
    the word it spells: the sections were not found, nor the skills under them."""
    return "\n".join(
        l.replace(" ", "") if _RX_ESPACE.fullmatch(l.strip()) else l for l in texte.splitlines()
    )


def _lire_cv(chemin):
    # Text boxes, content controls, nested tables, headers: see jobhunter.cv_text.
    from jobhunter.cv_text import texte_fichier

    try:
        return texte_fichier(chemin)
    except ValueError as e:
        # An unknown format, or a PDF protected by a password: cv_text says which.
        raise SystemExit(str(e)[:1].upper() + str(e)[1:]) from e


_RX_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_RX_TEL = re.compile(
    r"(?:\+\d{2,3}[\s.]?\(?0?\)?[\s.]?[1-9](?:[\s.-]?\d{2}){4}|\b0[1-9](?:[\s.-]?\d{2}){4})\b"
)
_RX_ESPACE = re.compile(r"(?:\w ){3,}\w")
# Any other country: "+44 7700 900123", "+1 (415) 555-0100".
_RX_TEL_INTER = re.compile(r"\+\d{1,3}(?:[\s.-]?\(?\d{2,4}\)?){2,4}\b")
# North America: « (614) 555-0100 », « 614-555-0100 ».
_RX_TEL_NANP = re.compile(r"\(\d{3}\)\s?\d{3}[\s.-]\d{4}\b|\b\d{3}[.-]\d{3}[.-]\d{4}\b")
_RX_LINKEDIN = re.compile(r"(?:https?://)?(?:[a-z]{2,3}\.)?linkedin\.com/in/[\w%-]+/?", re.I)
_RX_TITRE_SECTION = re.compile(
    r"^\s*(?:(?:professional|career|executive|personal)\s+)?"
    r"(profil|profile|r[ée]sum[ée]|summary|about( me)?|[àa] propos|objectif|pr[ée]sentation)\s*:?\s*$",
    re.I,
)
_RX_DIPLOME = re.compile(
    r"\b(master|licence|bachelor|bts|dut|but|mba|doctorat|phd|ing[ée]nieur|bac\s*\+\s*\d)", re.I
)


def _sans_accent(s):
    return "".join(c for c in unicodedata.normalize("NFD", s) if not unicodedata.combining(c))


def _nom_propre(m):
    """ "JEAN-PIERRE" -> "Jean-Pierre"; a name already in mixed case stays as written."""
    return "-".join(x.capitalize() for x in m.split("-")) if m.isupper() else m


def titre_du_cv(lignes, ident):
    """The CV's title: the first short line after the name that is not the name itself,
    a contact or a spaced heading ("C O N T A C T")."""
    nom = {w.lower() for w in f"{ident.get('prenom', '')} {ident.get('nom', '')}".split()}
    for l in lignes[:8]:
        if _RX_SECTION_EXPERIENCE.match(l):
            break  # the title comes before the jobs: past this, a line is a job's detail
        mots = {w.lower() for w in l.split()}
        if (
            4 < len(l) < 60
            # A contact or a date, not a digit: "Commercial B2B" is a title.
            and not re.search(r"@|\d{3}|\d{2}[\s./-]\d{2}", l)
            and not (l.isupper() and len(l.split()) == 1)  # a heading: "PROFIL"
            and not (mots and mots <= nom)
            and not re.fullmatch(r"(?:\w ){3,}\w", l)
            and not _RX_TITRE_SECTION.match(l)  # « PROFESSIONAL SUMMARY »
            and not lieu_du_cv([l])[2]  # « Columbus, Ohio, United States » is a place
        ):
            return l
    return poste_recent(lignes)


_RX_SECTION_EXPERIENCE = re.compile(
    r"^\s*(?:exp[ée]riences?(?: professionnelles?)?|(?:professional |work )?experience"
    r"|employment(?: history)?|parcours professionnel)\s*:?\s*$",
    re.I,
)


def poste_recent(lignes):
    """The first job of the Experience section, without its employer: « Registered Nurse (RN) »."""
    for i, l in enumerate(lignes):
        if _RX_SECTION_EXPERIENCE.match(l) and i + 1 < len(lignes):
            poste = re.split(r"\s+[—–-]\s+|\s+(?:at|chez|@)\s+|\s*\|\s*", lignes[i + 1])[0]
            poste = re.sub(r"\s*\([^)]*\)\s*$", "", poste).strip()
            return poste if 3 < len(poste) < 60 else ""
    return ""


def lieu_du_cv(lignes):
    """(city, region, country ISO code) read in the CV's header; ("", "", "") if none.

    « Columbus, Ohio, United States », « Austin, TX 78701 », « Paris, France ». A line
    with an e-mail or a phone is looked at piece by piece (« · », « | »).
    """
    from jobhunter.scoring import zones

    for l in lignes[:12]:
        for morceau in re.split(r"\s*[|·•]\s*", l):
            m = morceau.strip()
            if "," not in m or "@" in m or len(m) > 70 or re.search(r"\d{6,}|\(\d{3}\)", m):
                continue
            pays = zones.pays_lieu(m)
            if pays in ("?", "étranger (autre)"):
                continue
            iso = zones.code_pays(pays)
            if not iso:
                continue
            parts = [re.sub(r"\s+\d[\d -]*$", "", p).strip() for p in m.split(",")]
            parts = [p for p in parts if p]
            if iso == "fr" and not zones._lieu_sur(m):
                continue  # an unknown word, not a French place
            region = parts[1] if len(parts) > 2 or (len(parts) == 2 and iso != "fr") else ""
            noms_du_pays = {_sans_accent(pays).lower(), *zones._PAYS_CANON.get(pays, ())}
            if _sans_accent(region).lower() in noms_du_pays:
                region = ""
            if iso == "us" and region.lower() in zones.ETATS_US_CODES:
                region = zones.ETATS_US_CODES[region.lower()]
            return parts[0], region, iso
    return "", "", ""


def identite_du_cv(texte):
    lignes = [l.strip() for l in texte.splitlines() if l.strip()]
    email = (_RX_EMAIL.search(texte) or [""])[0]
    tel = (
        _RX_TEL.search(texte) or _RX_TEL_INTER.search(texte) or _RX_TEL_NANP.search(texte) or [""]
    )[0]
    lk = (_RX_LINKEDIN.search(texte) or [""])[0]
    prenom = nom = ""
    # A Canva CV puts the first name and the surname on two lines ("KARIM" / "BENALI").
    if (
        len(lignes) > 1
        and all(re.fullmatch(r"[A-Za-zÀ-ÿ'’-]{2,}", x) for x in lignes[:2])
        and lignes[0].isupper()
        and lignes[1].isupper()
    ):
        lignes = [f"{lignes[0]} {lignes[1]}"] + lignes[2:]
    # The name: one of the first lines, 2 to 4 alphabetic words, without a digit.
    for l in lignes[:8]:
        mots = l.replace("-", " - ").split()
        if (
            2 <= len([m for m in mots if m != "-"]) <= 4
            and not re.search(r"[\d@/:|·•]", l)
            and all(re.fullmatch(r"[A-Za-zÀ-ÿ'’-]+", m) for m in mots)
        ):
            vrais = [m for m in l.split() if m]
            # The word in CAPITALS is the surname, if there is one.
            maj = [m for m in vrais if m.isupper() and len(m) > 1]
            if maj and len(maj) < len(vrais):
                nom = " ".join(m.capitalize() for m in maj)
                prenom = " ".join(m for m in vrais if m not in maj)
            else:  # all in capitals ("JULIE MOREAU"): signed "Julie Moreau"
                prenom = _nom_propre(vrais[0])
                nom = " ".join(_nom_propre(m) for m in vrais[1:])
            break
    # The city: a sector of the zone catalogue named in the header.
    ville = ""
    entete = _sans_accent(" ".join(lignes[:12])).lower()
    from jobhunter.scoring import zones

    for cle, s in zones.CATALOGUE.items():
        for lieu in s.get("lieux", ()):
            if len(lieu) > 3 and re.search(r"(?<![a-z])" + re.escape(lieu) + r"(?![a-z])", entete):
                ville = lieu.title()
                break
        if ville:
            break
    v_cv, region, pays = lieu_du_cv(lignes)
    if pays and pays != "fr":
        ville = v_cv
    elif ville:
        pays = "fr"
    return {
        "prenom": prenom,
        "nom": nom,
        "email": email,
        "telephone": tel,
        "linkedin": lk,
        "ville": ville,
        "region": region,
        "pays": pays,
    }


def resume_du_cv(texte):
    """The paragraph under "Profil / Résumé / Summary", if it exists."""
    lignes = texte.splitlines()
    for i, l in enumerate(lignes):
        if _RX_TITRE_SECTION.match(l):
            bloc = []
            for x in lignes[i + 1 : i + 12]:
                x = x.strip()
                if not x:
                    if bloc:
                        break
                    continue
                if x.isupper() and len(x) < 40:  # title of the next section
                    break
                bloc.append(x)
            txt = re.sub(r"\s+", " ", " ".join(bloc)).strip()
            if len(txt) > 25:  # "Comptable en cabinet, tenue des comptes de PME." is one
                return txt[:700]
    return ""


# A CV summary is written without a subject ("Ingénieure diplômée de…"): in a letter it
# reads as notes. A first word that names the person (a job, a participle) gets "Je suis".
_RX_SANS_SUJET_FR = re.compile(
    r"^[A-ZÀ-Ý][a-zà-ÿ-]*(?:ée?s?|eure?|rice|euse|ien(?:ne)?|[iy]ste|ière|ier|ante?|ente?|ive|if"
    r"|el(?:le)?|[ai]ble|aire)\b"
)
_RX_SANS_SUJET_EN = re.compile(
    r"^(?:(?:junior|senior|experienced|motivated|passionate|certified|qualified)\b"
    r"|(?:[a-z-]+\s){0,2}[a-z-]*(?:er|or|ist|yst|ant|ent)\s+(?:with|in|at|who|special|focus))",
    re.I,
)


def a_la_premiere_personne(txt, langue="fr", titres=()):
    """ "Ingénieure diplômée de…" -> "Je suis ingénieure diplômée de…" (letters say "I").

    `titres`: the target jobs. A summary that starts with one of them ("Chef de rayon en
    grande distribution", "UX designer sur…") names the person, whatever its ending.
    """
    if len(txt) < 2:
        return txt
    bas = txt.lower()
    # The title, or its first word when it is a real word ("Commercial terrain en B2B"
    # for "Commercial B2B").
    formes = {t.lower() for x in titres for t in (x, masculin(x), x.split()[0] if x else "")}
    propre = any(re.match(re.escape(t) + r"\b", bas) for t in formes if len(t) >= 4)
    if not propre and not txt[1].islower():
        return txt
    debut = txt if txt[:2].isupper() else txt[0].lower() + txt[1:]
    if langue == "en" and (propre or _RX_SANS_SUJET_EN.match(txt)):
        return ("I am an " if debut[0].lower() in "aeiou" else "I am a ") + debut
    if langue != "en" and (propre or _RX_SANS_SUJET_FR.match(txt)):
        return "Je suis " + debut
    return txt


_RX_ADRESSE = re.compile(r"\S*(?:@|https?://|www\.|linkedin\.com|\.com/|\.fr/)\S*", re.I)


def competences_du_cv(texte):
    # Without the addresses: "linkedin.com/in/x" in the header is not a social media skill.
    t = " " + _RX_ADRESSE.sub(" ", texte).lower() + " "
    trouvees = {}
    for lab, v in catalogue().items():
        for s in v["synonymes"]:
            s = s.lower()
            ok = (
                re.search(r"\b" + re.escape(s.strip()) + r"\b", t)
                if len(s.strip()) <= 4
                else s in t
            )
            if ok:
                trouvees[lab] = v
                break
    return trouvees


_RX_SECTION_COMP = re.compile(
    r"^\s*(?:comp[ée]tences?(?:\s+techniques)?|skills|technical skills|outils|logiciels"
    r"|savoir[\s-]faire|expertises?|tools)\s*(?::\s*(.*))?$",
    re.I,
)
_RX_AUTRE_SECTION = re.compile(
    r"^\s*(?:langues?|languages?|exp[ée]riences?|formations?|education|dipl[oô]mes?"
    r"|centres? d'int[ée]r[eê]t|int[ée]r[eê]ts|loisirs|hobbies|interests|projets?|r[ée]f[ée]rences?"
    r"|certifications?|publications?|activit[ée]s)\b",
    re.I,
)
_RX_SEPARATEUR = re.compile(r"\s*[,;•·|]\s*|\s+[-–]\s+")


def competences_libres(texte, connues):
    """The skills the CV lists in its Skills section and the catalogue does not know.

    Any profession: "Nastran", "soins palliatifs", "cuisine japonaise" — written as
    the CV writes them, each one its own synonym. `connues` are the catalogue skills
    already found: an item one of them covers ("CATIA V5" when "catia" is known) is
    not added twice. At most 15.
    """
    lignes = texte.splitlines()
    items = []
    for i, l in enumerate(lignes):
        m = _RX_SECTION_COMP.match(l)
        if not m:
            continue
        bloc = [m.group(1)] if m.group(1) else []
        for x in lignes[i + 1 : i + 15]:
            if _RX_AUTRE_SECTION.match(x) or _RX_SECTION_COMP.match(x):
                break
            bloc.append(x)
        for x in bloc:
            items += _RX_SEPARATEUR.split(x.strip(" .:"))
        break
    synonymes = [s.lower() for v in connues.values() for s in v.get("synonymes", ())]
    libres = {}
    for it in items:
        it = re.sub(r"\s*\(.*?\)\s*", " ", it).strip(" .:-")
        bas = it.lower()
        if not (2 <= len(it) <= 35) or len(it.split()) > 4 or not re.search(r"[a-zA-ZÀ-ÿ]", it):
            continue
        # The end of a list cut at its comma: "CACES 1, 3 et 5" gave a skill "3 et 5".
        if it[0].isdigit():
            continue
        if any(s in bas for s in synonymes if len(s) > 2) or bas in synonymes:
            continue
        # Said in a sentence in lower case ("management d'équipe"), an acronym as it is.
        dit = it if it[:2].isupper() else it[0].lower() + it[1:]
        libres.setdefault(
            it[0].upper() + it[1:],
            {"synonymes": [bas], "en": it, "prose_fr": dit, "prose_en": dit, "libre": True},
        )
    return dict(list(libres.items())[:15])


_RX_LIGNE_DIPLOME = re.compile(
    r"^\s*(?:\d{4}(?:\s*[-–]\s*\d{4})?\s*[:,–-]?\s*)?"
    r"((?:dipl[oô]me|master|licence|bachelor|mba|doctorat|phd|bts|dut|but|msc|mastère"
    r"|dcg|dscg|deug|bsc|cap|bep|bac(?:calaur[ée]at)?|caces|fimo|cqp|dn\s+made"
    r"|titre\s+professionnel|certificat)\b.*)$",
    re.I,
)


def diplome_du_cv(texte):
    """The CV's first degree line as a phrase of the messages: "titulaire d'un master
    en finance". Cut at the first comma (the phrase sits between two commas). "" if none.
    """
    for l in texte.splitlines():
        m = _RX_LIGNE_DIPLOME.match(l)
        if not m:
            continue
        d = re.split(r"\s*[,(—–|·•]\s*|\s+-\s+", m.group(1).strip())[0].strip(" .")
        mot = d.split()[0]
        if not mot.isupper():  # "MBA", "BTS" stay as they are
            d = d[0].lower() + d[1:]
        article = "d'une" if mot.lower() == "licence" else "d'un"
        return f"titulaire {article} {d}"
    return ""


_LANGUES_EN = {
    "français": "French",
    "anglais": "English",
    "espagnol": "Spanish",
    "allemand": "German",
    "italien": "Italian",
    "portugais": "Portuguese",
    "arabe": "Arabic",
    "chinois": "Chinese",
    "mandarin": "Mandarin",
    "japonais": "Japanese",
    "russe": "Russian",
    "néerlandais": "Dutch",
    "polonais": "Polish",
}
# An English CV names its languages in English: said in French in the French messages.
_LANGUES_FR = {
    "english": "anglais",
    "spanish": "espagnol",
    "german": "allemand",
    "italian": "italien",
    "portuguese": "portugais",
    "arabic": "arabe",
    "chinese": "chinois",
    "japanese": "japonais",
    "russian": "russe",
    "dutch": "néerlandais",
    "polish": "polonais",
}
_RX_SECTION_LANGUES = re.compile(
    r"^\s*(?:langues?|languages?|sprachen|sprachkenntnisse|idiomas|idiomi|lingue)\s*(?::\s*(.*))?$",
    re.I,
)
# A language's name in English, French, German or Spanish → its ISO code.
_ISO_LANGUE = {
    nom: iso
    for iso, noms in {
        "fr": "french français francais französisch franzosisch francés frances",
        "en": "english anglais englisch inglés ingles",
        "de": "german allemand deutsch alemán aleman",
        "es": "spanish espagnol spanisch español espanol castellano",
        "it": "italian italien italienisch italiano",
        "pt": "portuguese portugais portugiesisch portugués portugues",
        "nl": "dutch néerlandais niederländisch neerlandés",
        "pl": "polish polonais polnisch polaco",
        "ru": "russian russe russisch ruso",
        "ar": "arabic arabe arabisch árabe",
        "zh": "chinese mandarin chinois chinesisch chino",
        "ja": "japanese japonais japanisch japonés japones",
        "ko": "korean coréen koreanisch coreano",
        "hi": "hindi",
    }.items()
    for nom in noms.split()
}
_NOM_FR = {
    "fr": "français", "en": "anglais", "de": "allemand", "es": "espagnol", "it": "italien",
    "pt": "portugais",
    "nl": "néerlandais", "pl": "polonais", "ru": "russe", "ar": "arabe", "zh": "chinois",
    "ja": "japonais", "ko": "coréen", "hi": "hindi",
}  # fmt: skip


def _et(items, et):
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + f" {et} " + items[-1]


def _lignes_de_section(suite):
    """The short lines under a heading, up to the next heading: a Canva or two-column CV
    puts one language per line ("Arabe" / "Anglais (B1)"); only the first was read."""
    out = []
    for x in suite:
        x = x.strip()
        if not x:
            if out:
                break
            continue
        liste = len(x) <= 100 and ("," in x or ";" in x)
        if (
            (len(x) > 40 and not liste)
            or (x.isupper() and len(x) > 3)
            or _RX_AUTRE_SECTION.match(x)
        ):
            break
        out.append(x)
    return out


def _bloc_langues(texte):
    """The items of the CV's Languages section ("Anglais (C1)", "Deutsch (Muttersprache)")."""
    lignes = texte.splitlines()
    for i, l in enumerate(lignes):
        m = _RX_SECTION_LANGUES.match(l)
        if m:
            bloc = m.group(1) or ", ".join(_lignes_de_section(lignes[i + 1 : i + 8]))
            return [x.strip() for x in _RX_SEPARATEUR.split(bloc.strip(" .")) if x.strip()]
    return []


def _nom_langue(item):
    return item.split("(")[0].split(":")[0].strip().lower()


def isos_du_cv(texte):
    """The ISO codes of the languages the CV's Languages section names, in any of four
    languages: « Deutsch, Englisch » → ["de", "en"]."""
    return [_ISO_LANGUE[n] for n in map(_nom_langue, _bloc_langues(texte)) if n in _ISO_LANGUE]


def langues_du_cv(texte):
    """("Je parle anglais (C1) et espagnol (B2).", "I speak English (C1) and Spanish
    (B2).") from the CV's Languages section, the CV's own language left out (a French
    CV's French, a London CV's English); ("", "") if none."""
    propre = langue_du_cv(texte)
    fr, en = [], []
    for it in _bloc_langues(texte):
        nom = _nom_langue(it)
        iso = _ISO_LANGUE.get(nom)
        if not nom or iso == propre:
            continue
        niveau = it[len(it.split("(")[0]) :].strip() if "(" in it else ""
        nom_fr = _NOM_FR.get(iso or "", _LANGUES_FR.get(nom, nom))
        fr.append(f"{nom_fr} {niveau}".strip())
        en.append(f"{_LANGUES_EN.get(nom_fr, nom.capitalize())} {niveau}".strip())
    if fr:
        return f"Je parle {_et(fr, 'et')}.", f"I speak {_et(en, 'and')}."
    return "", ""


def langue_du_cv(texte):
    """The language the CV is written in: "fr", "en", "de" or "es"."""
    t = texte.lower()
    fr = len(re.findall(r"\b(et|les|des|une|pour|avec|exp[ée]rience|comp[ée]tences)\b", t))
    en = len(re.findall(r"\b(and|the|with|for|experience|skills)\b", t))
    de = len(
        re.findall(
            r"\b(und|der|die|das|mit|für|bei|berufserfahrung|kenntnisse|sprachen|heute)\b", t
        )
    )
    es = len(
        re.findall(r"\b(y|los|las|del|con|para|experiencia|competencias|idiomas|actualidad)\b", t)
    )
    autre, n = max((("de", de), ("es", es)), key=lambda x: x[1])
    if n >= 3 and n > max(fr, en) * 1.3:
        return autre
    return "en" if en > fr * 1.3 else "fr"


# ── 2. Questions ─────────────────────────────────────────────────────────────


def demander(question, defaut, auto, impose=None):
    # An answer given as an option (--metiers...) comes before the question: an agent
    # like Claude Code fills in everything without a keyboard.
    if impose is not None:
        print(f"  {question} -> {impose}")
        return impose
    # Without a keyboard (agent, pipe), input() would raise EOFError: we take the proposed value.
    if auto or not sys.stdin.isatty():
        print(f"  {question} -> {defaut}")
        return defaut
    try:
        r = input(f"  {question} [{defaut}] : ").strip()
    except EOFError:  # console without a keyboard: the proposed value
        r = ""
    return r or defaut


def demander_prive(question, defaut, auto, impose=None):
    """demander() for the e-mail and phone: the value is never echoed.

    The first launch's output often goes to a log; only the console prompt shows it.
    """
    if impose is not None:
        print(f"  {question} -> {_t('(renseigné)')}")
        return impose
    if auto or not sys.stdin.isatty():
        print(
            f"  {question} -> "
            + (_t("(à compléter)") if defaut in ("", A_COMPLETER) else _t("(renseigné)"))
        )
        return defaut
    try:
        r = input(f"  {question} [{defaut}] : ").strip()
    except EOFError:
        r = ""
    return r or defaut


_VIDES = {
    "junior",
    "senior",
    "stage",
    "stagiaire",
    "alternance",
    "alternant",
    "cdi",
    "cdd",
    "h/f",
    "f/h",
    "h-f",
    "f-h",
    "(h/f)",
    "de",
    "des",
    "du",
    "en",
    "et",
    "la",
    "le",
    "les",
    "d",
    "l",
    "au",
    "aux",
    "pour",
    "a",
    "à",
    "or",
    "and",
    "of",
    "the",
    "in",
    "vie",
    "v.i.e",
    "freelance",
}


# Feminine endings of a job title -> masculine: postings mostly write the masculine
# ("Ingénieur H/F"), and the sorting families are written in it.
_FEMININS = (
    (re.compile(r"(\w)ée\b"), r"\1é"),  # chargée
    (re.compile(r"(\w{3})eure\b"), r"\1eur"),  # ingénieure
    (re.compile(r"(\w{2})trice\b"), r"\1teur"),  # directrice
    (re.compile(r"(\w{3})euse\b"), r"\1eur"),  # vendeuse
    (re.compile(r"(\w{3})ienne\b"), r"\1ien"),  # technicienne
    (re.compile(r"(\w{3})ère\b"), r"\1er"),  # conseillère
)
_RX_FEMININ = re.compile(r"\b\w+(?:ée|eure|trice|euse|ienne|ère)\b", re.I)


def masculin(titre):
    """The masculine form of a job title: "Ingénieure chargée" -> "Ingénieur chargé"."""
    for rx, rempl in _FEMININS:
        titre = rx.sub(rempl, titre)
    return titre


def _radical(mot):
    """A title word as a word START: masculine, singular ("structures" -> "structure").

    The profile's words find what starts with them: the stem finds both forms.
    """
    mot = masculin(mot)
    return mot[:-1] if len(mot) > 4 and mot[-1] in "sx" and mot[-2] not in "su" else mot


# Words that say little alone: in a title filter, "gestion" lets in every "gestion de
# projet", "état" every title of the public service. Dropped when the title has a more
# specific word ("Contrôleur de gestion" -> contrôleur; "Infirmière diplômée d'État" ->
# infirmier), kept when it has none.
_GENERIQUES = {
    "gestion",
    "projet",
    "chargé",
    "responsable",
    "assistant",
    "état",
    "etat",
    "diplômé",
    "diplome",
    "full",
    "stack",
    "affaire",
    "service",
    "client",
    "structure",
}


def _formes(mot):
    """The word's stems for both genders, when one is not the start of the other.

    "ingénieur" finds "ingénieure", but "infirmier" does not find "infirmière" nor
    "directeur" "directrice": a nurse's own postings fell in the "Autre" domain.
    """
    masc = _radical(mot)
    formes = [masc]
    tel = mot[:-1] if len(mot) > 4 and mot[-1] in "sx" and mot[-2] not in "su" else mot
    if not tel.startswith(masc):
        formes.append(tel)
    elif re.search(r"(?:i|ll)er$", masc):
        formes.append(masc[:-2] + "ère")
    elif masc.endswith("teur") and len(masc) > 6:
        formes.append(masc[:-4] + "trice")
    return formes


# A title word and its other language: an English CV ("Developer") must find the
# French postings ("Développeur"), and the reverse. Stems, as _formes gives them.
_TRADUCTIONS = (
    ("developer", "développeur", "developpeur"),
    ("engineer", "ingénieur", "ingenieur"),
    ("analyst", "analyste"),
    ("accountant", "comptable"),
    ("controller", "contrôleur", "controleur"),
    ("nurse", "infirmier", "infirmière"),
    ("auditor", "auditeur", "auditrice"),
    ("consultant",),
    ("teacher", "enseignant", "professeur"),
    ("technician", "technicien"),
    ("lawyer", "avocat", "juriste"),
    ("buyer", "acheteur", "acheteuse"),
    ("sales", "commercial"),
    ("researcher", "chercheur", "chercheuse"),
)


def _traductions(forme):
    for groupe in _TRADUCTIONS:
        if forme in groupe:
            return (forme, *(g for g in groupe if g != forme))
    return (forme,)


def mots_significatifs(titre):
    mots = re.findall(r"[a-zA-ZÀ-ÿ&+#.]+", titre.lower())
    tous = list(
        dict.fromkeys(
            t
            for m in mots
            if m not in _VIDES and len(m) >= 3
            for f in _formes(m)
            for t in _traductions(f)
        )
    )
    return [m for m in tous if m not in _GENERIQUES] or tous


_NOMBRES = {
    "un": 1,
    "une": 1,
    "deux": 2,
    "trois": 3,
    "quatre": 4,
    "cinq": 5,
    "six": 6,
    "sept": 7,
    "huit": 8,
    "neuf": 9,
    "dix": 10,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
}
_RX_ANNEES = re.compile(
    r"\b(\d{1,2}|" + "|".join(_NOMBRES) + r")\+?\s*(?:ans|années|years?)\s+(?:d'|d’|de\s+|of\s+)"
    r"(?:exp[ée]rience|experience)",
    re.I,
)


def annees_du_cv(texte):
    """The years of experience the CV states ("Trois ans d'expérience"), 0 if none."""
    vues = [
        int(n) if n.isdigit() else _NOMBRES.get(n.lower(), 0) for n in _RX_ANNEES.findall(texte)
    ]
    dit = max((v for v in vues if v < 45), default=0)
    return dit or annees_des_dates(texte)


# "2018-2026", "2019 – aujourd'hui", "2021 - present": a job's span on a CV line.
_RX_PERIODE = re.compile(
    r"\b((?:19|20)\d{2})\s*(?:[-–—à]+|bis|hasta)\s*((?:19|20)\d{2}|aujourd.hui|ce jour|pr[ée]sent|present|now"
    r"|en cours|actuel(?:lement)?|current(?:ly)?|heute|jetzt|aktuell|actualidad|actualmente"
    r"|presente|hoy|oggi|attuale)\b",
    re.I,
)


def annees_des_dates(texte):
    """The years from the experience lines' dates when the CV states no "N ans": a
    seven-year department manager was taken for a junior, and his own job sorted out
    as senior. The degree lines (2016-2019 Licence) do not count."""
    import datetime

    debuts, fins = [], []
    for l in texte.splitlines():
        # A degree line, not a job line that says "Ingénieure qualité".
        if _RX_LIGNE_DIPLOME.search(l):
            continue
        for d, f in _RX_PERIODE.findall(l):
            debuts.append(int(d))
            fins.append(int(f) if f.isdigit() else datetime.date.today().year)
    if not debuts:
        return 0
    return max(0, min(max(fins) - min(debuts), 44))


# The seniority words of scoring.sorting, in a target title.
_RX_TITRE_SENIOR = re.compile(
    r"\b(?:senior|confirm|exp[ée]riment|director|directeur|directrice|head|chief|principal"
    r"|manager|lead|responsable|expert|chef|g[ée]rant|superviseur)",
    re.I,
)


def slug(s):
    s = _sans_accent(s)
    return re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_") or "Domaine"


# ── 3. Building the profile ──────────────────────────────────────────────────

# Roles set aside by default (rarely wanted by mistake), with their family:
# a TARGETED family is never set aside.
_EXCLUS_DEFAUT = [
    ("brand", "marketing"),
    ("re:design(er)?\\b", "design"),
    ("re:\\bux\\b", "design"),
    ("re:\\bui\\b", "design"),
    ("graphi", "design"),
    ("marketing", "marketing"),
    ("growth", "marketing"),
    ("sales", "commercial"),
    ("account executive", "commercial"),
    ("account manager", "commercial"),
    ("business developer", "commercial"),
    ("re:commercial\\b", "commercial"),
    ("talent acquisition", "rh"),
    ("recruiter", "rh"),
    ("recruteur", "rh"),
    ("people ops", "rh"),
    ("office manager", ""),
    ("customer success", "commercial"),
    ("customer care", "commercial"),
    ("customer support", "commercial"),
    ("community manager", "marketing"),
    ("copywriter", "marketing"),
    ("content manager", "marketing"),
    ("content creator", "marketing"),
    ("social media", "marketing"),
    ("juriste", "juridique"),
    ("legal counsel", "juridique"),
    ("avocat", "juridique"),
    ("re:paie\\b", "rh"),
    ("payroll", "rh"),
]


def familles_visees(metiers, comps):
    """Score per family: targeted titles (strong) + CV skills."""
    score = {f: 0 for f in FAMILLES}
    txt = " " + " ".join(metiers).lower() + " "
    for f, (_lib, mots) in FAMILLES.items():
        score[f] += 3 * sum(1 for m in mots if m.lower() in txt)
    for v in comps.values():
        if v.get("famille"):
            score[v["famille"]] += 1
    return sorted((f for f in score if score[f] > 0), key=lambda f: -score[f]), score


def niveau(annees):
    if annees <= 2:
        return {
            "mots_junior": [
                "junior",
                "graduate",
                "débutant",
                "debutant",
                "jeune diplôm",
                "alternance",
                "apprenti",
                "stage",
                "stagiaire",
                "entry level",
                "0 à 2 ans",
                "1 à 2 ans",
            ],
            "mots_senior": [
                "senior",
                "director",
                "directeur",
                "manager",
                "head of",
                "principal",
                "vp ",
                "chef de",
                "expert confirmé",
                "expert ",
                "confirmé",
                "expérimenté",
            ],
            "senior_en_fin": [
                "re:\\b(lead|head|principal|manager|director)\\b(?!\\s+(generation|gen)\\b)"
            ],
            "mots_negatifs": [],
            "malus_experience": {"3": 1, "5": 3, "7": 4, "10": 5},
            "experience_max": 5,
        }, True
    if annees <= 6:
        return {
            "mots_junior": [],
            "bonus_junior": 0,
            "mots_senior": ["director", "directeur", "directrice", "head of", "chief", "vp "],
            "malus_senior": 1,
            "senior_en_fin": [],
            "mots_negatifs": [],
            "malus_experience": {"9": 2, "12": 4},
            "experience_max": 12,
        }, False
    return {
        "mots_junior": [],
        "bonus_junior": 0,
        "mots_senior": [],
        "malus_senior": 0,
        "senior_en_fin": [],
        "mots_negatifs": [],
        "malus_experience": {},
        "experience_max": 99,
    }, False


def en_phrase(titre):
    """A title inside a sentence: lower case, but the State keeps its capital
    ("Je suis infirmière diplômée d'État")."""
    return re.sub(r"\b([dl]')état\b", r"\1État", titre.lower())


def construire(cv_txt, cv_nom, rep):
    ident = rep["identite"]
    comps = rep["competences"]
    metiers = rep["metiers"]
    resume = resume_du_cv(cv_txt)
    # The summary goes in its own language: an English CV wrote English in parcours_fr.
    langue = langue_du_cv(cv_txt)
    resume_fr, resume_en = (
        ("", a_la_premiere_personne(resume, "en", metiers))
        if langue == "en"
        else (a_la_premiere_personne(resume, "fr", metiers), "")
        if langue == "fr"
        else ("", "")  # a German or Spanish CV: the letters are written in French or English
    )
    # A paragraph checked in the welcome form (often taken from the owner's own
    # letter) comes before the one drawn from the CV, in its own language.
    parcours = (rep.get("parcours") or "").strip()
    if parcours:
        if langue_du_cv(parcours) == "en":
            resume_en = parcours
        elif langue_du_cv(parcours) == "fr":
            resume_fr = parcours
    ordre, score = familles_visees(metiers, comps)
    coeur = ordre[0] if ordre else ""
    mots_cibles = sorted({m for t in metiers for m in mots_significatifs(t)})

    # Profile skills = the CV's. The letter quotes skills
    # that the posting asks for AND that the CV carries: never one it does not have.
    competences = {}
    for lab, v in comps.items():
        e = {k: v[k] for k in ("synonymes", "en", "prose_fr", "prose_en") if k in v}
        if v.get("technique") is False or not (v.get("famille") or v.get("libre")):
            e["technique"] = False
        competences[lab] = e

    axes = {}
    for f in ordre:
        labs = [l for l, v in comps.items() if v.get("famille") == f]
        if not labs:
            continue
        axes[f] = {"poids": 1.0, "competences": labs}
    if len(ordre) > 1 and ordre[1] in axes:
        axes[ordre[1]]["poids"] = 2.0
    # The CV's own skills (competences_libres) are the job's core: in the core axis.
    libres = [l for l, v in comps.items() if v.get("libre")]
    if libres:
        if not coeur:
            coeur = "metier"
        axes.setdefault(coeur, {"poids": 3.0, "competences": []})["competences"] += libres
    if coeur in axes:
        axes[coeur]["poids"] = 3.0

    niv, junior = niveau(rep["annees"])
    langues = langues_du_cv(cv_txt)
    visees = {f for f in ordre if score[f] >= 3} | ({coeur} if coeur else set())
    exclus = [
        m
        for m, fam in _EXCLUS_DEFAUT
        if fam not in visees
        and not any((m[3:] if m.startswith("re:") else m) in t.lower() for t in metiers)
    ]

    domaines = []
    for i, t in enumerate(metiers):
        mots_t = mots_significatifs(t) or [t.lower()]
        if i == 0:
            # The job's usual titles too: "Software Engineer" is a developer's posting,
            # it fell in "Autre" with "developer" alone.
            mots_t = list(dict.fromkeys(mots_t + list(FAMILLES.get(coeur, ("", []))[1])))
        domaines.append(
            {
                "cle": slug(t)[:40],
                "libelle": t[:30],
                "mots_titre": mots_t,
                "cv": cv_nom,
                "cv_en": "",
                "parcours_fr": resume_fr,
                "parcours_en": resume_en,
                "accroche_fr": en_phrase(t),
                "accroche_en": en_phrase(t),
                "preuve_fr": "",
                "preuve_en": "",
                "preuve_detente_fr": "",
            }
        )
    domaines.append(
        {
            "cle": "General",
            "libelle": "Autre",
            "mots_titre": [],
            "cv": cv_nom,
            "cv_en": "",
            "parcours_fr": resume_fr,
            "parcours_en": resume_en,
            "accroche_fr": (en_phrase(metiers[0]) if metiers else "candidat"),
            "accroche_en": (en_phrase(metiers[0]) if metiers else "candidate"),
            "preuve_fr": "",
            "preuve_en": "",
            "preuve_detente_fr": "",
        }
    )

    # Masculine form too: postings write "Chargé(e)", "Chargé H/F".
    formes = list(dict.fromkeys(f for t in metiers for f in (t.lower(), masculin(t.lower()))))
    mots_cles = list(
        dict.fromkeys(
            formes + ([f"{t} junior" for t in formes[:2] if "junior" not in t] if junior else [])
        )
    )
    top = sorted(
        (l for l, v in comps.items() if v.get("famille")),
        key=lambda l: -(comps[l].get("famille") == coeur),
    )[:3]

    return {
        "_lisez_moi": (
            "Ton profil. Genere par first_launch.py a partir de ton CV : RELIS-LE. "
            "Les champs vides ou « A COMPLETER » rendent les lettres plus pauvres. "
            "Modele complet et commente : profile/example_finance_esg.json."
        ),
        "identite": {**ident, "genre": rep["genre"]},
        "domaines": domaines,
        "competences": competences,
        # The job's skills the CV does not name: only for the ATS % (score_offer),
        # never quoted in a letter nor counted in the fit.
        "competences_ats": {
            lab: {"synonymes": v["synonymes"]}
            for lab, v in catalogue().items()
            if v.get("famille") in set(ordre[:2]) and lab not in comps
        },
        "competences_de_base": top,
        "termes": {},
        "scoring": {
            "axes": axes,
            "axe_coeur": coeur if coeur in axes else (next(iter(axes), "")),
            "axe_complement": "",
            "cible_score": 3.0,
            "saturation_axe": 3,
            "plafond_sans_coeur": 6.0,
            "plafond_complement": 8.0,
            "densite_coeur_min": 0.0,
            "densite_coeur_longueur": 800,
            "intitules_coeur": mots_cibles,
            "intitules_coeur_forts": formes,
            "intitules_second": [],
            "plafond_second": 8.0,
            "veto_sigles": [],
            "veto_si": [],
            "veto_et": [],
            "plafond_veto": 6.0,
            "intitules_techniques": [],
            "intitules_techniques_sauf": [],
            "intitules_hors_metier": [],
        },
        "niveau": niv,
        "filtre_titre": {
            "metier": list(dict.fromkeys(mots_cibles + list(FAMILLES.get(coeur, ("", []))[1]))),
            "exclus": exclus,
            "exclus_sauf_complement": [],
            "complement": [],
            "lexique_large": [],
        },
        "tri": {
            "retirer_seniors": junior,
            "retirer_etudiants": True,
            "metiers_durs": [],
            "sauvetage": mots_cibles,
            # The person's own job is never sorted out as senior ("Chef de rayon").
            "seniorite_sauf": [
                f
                for t in metiers
                for f in dict.fromkeys((t.lower(), masculin(t.lower())))
                if _RX_TITRE_SENIOR.search(f)
            ],
            "outils_max": 0 if coeur in ("dev", "data") else 4,
        },
        # Languages spoken: those of the CV, and the language it is written in.
        # A posting written or required in another language is capped.
        "langues_parlees": list(
            dict.fromkeys(
                [langue_du_cv(cv_txt)]
                + (["fr"] if ident.get("pays", "fr") in ("fr", "") else [])
                + [
                    c
                    for nom, c in (
                        ("Français", "fr"),
                        ("Anglais", "en"),
                        ("Allemand", "de"),
                        ("Espagnol", "es"),
                        ("Italien", "it"),
                    )
                    if nom in comps
                ]
                + isos_du_cv(cv_txt)
            )
        ),
        **({"pays": ident["pays"]} if ident.get("pays") else {}),
        "zones": {"prioritaires": rep["prioritaires"], "secondaires": rep["secondaires"]},
        "collecte": {"mots_cles": mots_cles},
        "message": {
            # Read from the CV's Education and Languages sections: the messages say
            # them without waiting for the profile to be completed by hand.
            "diplome_fr": diplome_du_cv(cv_txt),
            "diplome_detente_fr": "",
            "diplome_en": "",
            "langues_fr": langues[0],
            "langues_detente_fr": "",
            "langues_en": langues[1],
            "sources": {},
            "faits": {},
            "phrase_contexte_fr": {},
            "phrase_contexte_en": {},
        },
        # The CV is the person's own, sent as is: per offer, its skills line puts the
        # ones the posting names first (documents.cv.ordonner_competences).
        "cv": {"ordonner_competences": True},
        "lettre": {
            "valeurs_entreprises_fr": {},
            "valeurs_entreprises_en": {},
            "phrase_profil_fr": "",
            "phrase_profil_en": "",
            "contextes": [],
            # From 3 years of experience the letter speaks of experience put to work.
            "ton": "experimente" if rep["annees"] >= 3 else "",
            "presentation_llm": f"Profil : {', '.join(metiers)}. {resume[:300]}",
        },
        "formulaire": {
            "pays": "France",
            "langues": ", ".join(
                l for l, v in comps.items() if v.get("technique") is False and not v.get("famille")
            ),
        },
    }


def reclasser_domaines():
    """A rebuilt profile (--force): the queue's offers take its domains.

    The domain is written at collection; the old profile's keys stayed on every offer,
    and the stats showed "Autre" for three developer postings out of four.
    """
    from jobhunter.scoring.domains import classify_domaine
    from jobhunter.storage import queue as _file

    if not (HERE / "apply_queue.json").exists():
        return 0
    n = 0
    try:
        with _file.transaction(HERE / "apply_queue.json", descriptions=False) as q:
            for o in q:
                d = classify_domaine(o.get("poste") or "")
                if o.get("domaine") != d:
                    o["domaine"] = d
                    n += 1
    except Exception as e:  # queue busy: the profile is written all the same
        print(f"  offres        : domaines non recalculés ({type(e).__name__}), relance plus tard")
        return 0
    return n


def familles_tri_a_exclure(metiers):
    """Families of the sorting (tri_file._METIERS) that target NONE of the chosen
    jobs: they are removed from the queue. A targeted family stays."""
    from jobhunter.scoring import sorting as tri_file

    # Each title as written, in the masculine, and with its words singular: the family
    # patterns are masculine and bounded ("ingénieur structure\b"), and an "Ingénieure
    # structures" profile would otherwise remove its own job from the queue.
    formes = [
        f
        for t in metiers
        for f in (t, masculin(t), " ".join(_radical(m) for m in masculin(t).split()))
    ]
    exclure = []
    for fam, rx in tri_file._METIERS_CATALOGUE.items():
        if not any(rx.search(t) for t in formes):
            exclure.append(fam)
    return exclure


# ── 4. Programme ─────────────────────────────────────────────────────────────


def propositions(txt):
    """The answers main() proposes, read from the CV's text.

    The welcome window (jobhunter.welcome) prefills its form with them, then passes the
    answers back as options: the same defaults as in the console, without a keyboard.
    """
    from jobhunter.scoring import zones

    ident = identite_du_cv(txt)
    lignes = [l.strip() for l in txt.splitlines() if l.strip()]
    metiers = titre_du_cv(lignes, ident) or ""
    v = _sans_accent(ident["ville"] or "").lower()
    candidats = [
        (len(s.get("departements", ())), cle)
        for cle, s in zones.CATALOGUE.items()
        if v and v in s.get("lieux", ())
    ]
    comps = competences_du_cv(txt)
    comps.update(competences_libres(txt, comps))
    ordre, _ = familles_visees([m.strip() for m in metiers.split(",") if m.strip()], comps)
    return {
        **{k: ident.get(k) or "" for k in ("prenom", "nom", "email", "telephone", "ville")},
        "metiers": metiers,
        "annees": annees_du_cv(txt),
        "genre": "f" if _RX_FEMININ.search(metiers) else "m",
        "prioritaires": [min(candidats)[1]]
        if candidats
        else ([ident["ville"]] if ident.get("pays") not in ("", "fr") and ident["ville"] else []),
        "secondaires": [ident["region"]]
        if ident.get("pays") not in ("", "fr") and ident.get("region")
        else [],
        "pays": ident.get("pays") or "",
        "entreprises": bool(ordre) and ordre[0] in ("finance", "rse", "conseil"),
        # The letters' background paragraph, as construire() would draw it from the CV.
        "parcours": a_la_premiere_personne(
            resume_du_cv(txt),
            langue_du_cv(txt),
            [m.strip() for m in metiers.split(",") if m.strip()],
        )
        if langue_du_cv(txt) in ("fr", "en")
        else "",
    }


def main():
    ap = argparse.ArgumentParser(description="Creates the profile (profile.json) from your CV.")
    ap.add_argument("cv", help="your CV, .pdf or .docx")
    ap.add_argument("--auto", action="store_true", help="accept every proposed answer")
    ap.add_argument("--force", action="store_true", help="replace an existing profile")
    ap.add_argument("--profil", default=str(_racine.dossier("profil") / _racine.nom("profil.json")))
    # The identity, when the welcome window has asked for it (jobhunter.welcome).
    for champ in ("prenom", "nom", "email", "telephone", "ville"):
        ap.add_argument(f"--{champ}")
    ap.add_argument("--metiers", help="target jobs, separated by commas")
    ap.add_argument("--annees", help="years of experience, internships included")
    ap.add_argument("--genre", choices=["m", "f"], help="agreement of French letters")
    ap.add_argument("--prioritaires", help="priority places, separated by commas")
    ap.add_argument("--secondaires", help="secondary places, separated by commas (empty = none)")
    ap.add_argument(
        "--entreprises",
        choices=["o", "n"],
        help="keep (o) or empty (n) the finance/ESG companies followed by default",
    )
    ap.add_argument(
        "--word",
        choices=["o", "n"],
        default="n",
        help="CV as PDF: rebuild a .docx adapted to each offer (o), or send it as is (n)",
    )
    ap.add_argument("--parcours", help="the letters' background paragraph (else read in the CV)")
    a = ap.parse_args()

    sortie = Path(a.profil)
    if sortie.exists() and not a.force:
        print(
            f"Un profil existe deja : {sortie}\nRelance avec --force pour le remplacer "
            "(l'ancien est garde en .bak)."
        )
        return 1

    cv = Path(a.cv)
    if not cv.exists():
        print(f"CV introuvable : {cv}")
        return 1
    print(_t("\n1. Lecture du CV : {}").format(cv.name))
    txt = lire_cv(cv)
    if len(txt.strip()) < 200:
        print(
            _t(
                "  ! Presque aucun texte lu. Un CV scanne (image) ne se lit pas : fournis un PDF texte ou un .docx."
            )
        )
        # Without text the profile would collect "a completer" postings: nothing written,
        # unless the jobs are given (--metiers).
        if not a.metiers:
            print(_t("  Rien n'est écrit. Relance avec le CV en .docx, ou donne --metiers."))
            return 1
    ident = identite_du_cv(txt)
    comps = competences_du_cv(txt)
    comps.update(competences_libres(txt, comps))
    print(
        _t("  nom : {} · email : {} · tel : {} · ville : {}").format(
            f"{ident['prenom']} {ident['nom']}",
            # Like demander_prive: the e-mail and phone are never echoed, only whether read.
            _t("(renseigné)") if ident["email"] else "?",
            _t("(renseigné)") if ident["telephone"] else "?",
            ident["ville"] or "?",
        )
    )
    print(
        _t("  {} competence(s) reconnue(s) : {}").format(
            len(comps), ", ".join(sorted(_t_comp(c, v) for c, v in comps.items()))[:300]
        )
    )

    print(_t("\n2. Quelques questions (Entree = valeur proposee)"))
    ident["prenom"] = demander(
        _t("Prénom"), ident["prenom"] or A_COMPLETER, a.auto, a.prenom or None
    )
    ident["nom"] = demander(_t("Nom"), ident["nom"] or A_COMPLETER, a.auto, a.nom or None)
    ident["email"] = demander_prive(
        _t("Email"), ident["email"] or A_COMPLETER, a.auto, a.email or None
    )
    ident["telephone"] = demander_prive(_t("Téléphone"), ident["telephone"], a.auto, a.telephone)
    ident["ville"] = demander(_t("Ville"), ident["ville"], a.auto, a.ville)
    # Job: the line under the name is often the CV's title.
    lignes = [l.strip() for l in txt.splitlines() if l.strip()]
    propose = titre_du_cv(lignes, ident)
    metiers = [
        m.strip()
        for m in demander(
            _t(
                "Métiers visés, séparés par des virgules (ex. : Chargé de communication, Community manager)"
            ),
            propose or A_COMPLETER,
            a.auto,
            a.metiers,
        ).split(",")
        if m.strip()
    ]
    try:
        annees = int(
            demander(
                _t("Années d'expérience professionnelle (stages compris)"),
                str(annees_du_cv(txt)),
                a.auto,
                a.annees,
            )
        )
    except ValueError:
        annees = 0
    # A title in the feminine ("Chargée", "Directrice", "Ingénieure") suggests "f".
    # Asked only for a CV in French: no other language agrees « diplômé(e) ».
    fem = bool(_RX_FEMININ.search(" ".join(metiers)))
    genre = (
        demander(
            "Accords dans les lettres : « diplômé » (m) ou « diplômée » (f) ?",
            "f" if fem else "m",
            a.auto,
            a.genre,
        )
        if langue_du_cv(txt) == "fr"
        else (a.genre or "m")
    )
    from jobhunter.scoring import zones

    # The most PRECISE sector that names the city: the metropolis before the region.
    v = _sans_accent(ident["ville"] or "").lower()
    candidats = [
        (len(s.get("departements", ())), cle)
        for cle, s in zones.CATALOGUE.items()
        if v and v in s.get("lieux", ())
    ]
    secteur_ville = min(candidats)[1] if candidats else ""
    a_l_etranger = ident.get("pays") not in ("", "fr")
    from jobhunter.sources import countries as _pays_src

    if a_l_etranger:
        secteur_ville = ident["ville"]
    else:
        print(f"     secteurs connus : {', '.join(zones.CATALOGUE)}")
    prio = [
        x.strip()
        for x in demander(
            _t("Secteurs PRIORITAIRES (séparés par des virgules)"),
            secteur_ville or ("" if a_l_etranger else "idf"),
            a.auto,
            a.prioritaires,
        ).split(",")
        if x.strip()
    ]
    sec = [
        x.strip()
        for x in demander(
            _t("Secteurs secondaires (vide = aucun)"),
            (ident.get("region") or _pays_src.nom(ident.get("pays"))) if a_l_etranger else "",
            a.auto,
            a.secondaires,
        ).split(",")
        if x.strip()
    ]
    # A place outside the catalogue (« Columbus », « Chambéry ») is kept as a free place.
    from jobhunter import search_settings

    def secteur(x):
        if x.lower() in zones.CATALOGUE:
            return x.lower()
        libre = search_settings.lieu_libre(x)
        etat = next((k for k, v in zones.ETATS_US_CODES.items() if v.lower() == x.lower()), "")
        if etat:
            libre["lieux"] = [x, etat.upper()]
        # The home country: also under the names the CV and the postings may use.
        if a_l_etranger and x == _pays_src.nom(ident.get("pays")):
            canon = next((k for k, v in zones._PAYS_CANON.items() if x.lower() in v), "")
            libre["lieux"] = list(dict.fromkeys([x, *zones._PAYS_CANON.get(canon, ())]))
        return libre

    prio = [secteur(x) for x in prio]
    sec = [secteur(x) for x in sec]
    ordre, _ = familles_visees(metiers, comps)
    finance = bool(ordre) and ordre[0] in ("finance", "rse", "conseil")
    # Asked only of a finance profile: the default companies are banks and asset managers.
    garder = (
        _oui(
            demander(
                _t("Garder les ~90 entreprises de finance / ESG suivies par défaut ? (o/n)"),
                "o",
                a.auto,
                a.entreprises,
            )
        )
        if finance
        else _oui(a.entreprises or "n")
    )

    rep = {
        "identite": ident,
        "competences": comps,
        "metiers": metiers,
        "annees": annees,
        "genre": "f" if genre.lower().startswith("f") else "m",
        "prioritaires": prio,
        "secondaires": sec,
        "parcours": a.parcours or "",
    }

    print(_t("\n3. Ecriture"))
    cv_dir = RACINE / "CV" / _racine.nom("Modèles")
    cv_dir.mkdir(parents=True, exist_ok=True)
    prefixe = slug(f"{ident['prenom']} {ident['nom']}")
    cv_nom = f"CV_{prefixe}{cv.suffix.lower()}"
    shutil.copyfile(cv, cv_dir / cv_nom)
    # A PDF goes out as is for every offer; its rebuilt .docx can be adapted (cv_word).
    # The PDF stays next to it: the owner can switch back in profile.json.
    if a.word == "o" and cv.suffix.lower() == ".pdf":
        from jobhunter import cv_word

        try:
            cv_word.pdf_en_docx(cv, cv_dir / f"CV_{prefixe}.docx")
            cv_nom = f"CV_{prefixe}.docx"
        except ValueError as e:
            print(_t("  ! Version Word impossible ({}) : le PDF part tel quel.").format(e))
    print(_t("  CV modele     : {}").format((cv_dir / cv_nom).relative_to(RACINE).as_posix()))

    profil = construire(txt, cv_nom, rep)
    sortie.parent.mkdir(parents=True, exist_ok=True)
    if sortie.exists():
        shutil.copyfile(sortie, sortie.with_suffix(".json.bak"))
    sortie.write_text(json.dumps(profil, ensure_ascii=False, indent=1), encoding="utf-8")
    # The sorting families are computed with the profile in place (tri_file reads it).
    import os

    from jobhunter import profile as _profil

    os.environ["PROFIL_JOBHUNTER"] = str(sortie)
    _profil.recharger(sortie)
    profil["tri"]["metiers_exclus"] = familles_tri_a_exclure(metiers)
    sortie.write_text(json.dumps(profil, ensure_ascii=False, indent=1), encoding="utf-8")
    print(_t("  profil        : {}").format(sortie.relative_to(RACINE).as_posix()))

    # Empty data files: the queue of offers and the application tracking.
    # The app finds its root through Scripts/apply_queue.json.
    for nom, vide in (("apply_queue.json", "[]"), (_racine.nom("suivi.json"), "{}")):
        if not (HERE / nom).exists():
            (HERE / nom).write_text(vide, encoding="utf-8")
    n = reclasser_domaines()
    if n:
        print(_t("  offres        : {} rangée(s) dans les domaines du nouveau profil").format(n))
    faits = RACINE / "CV" / _racine.nom("Faits.json")
    if not faits.exists():
        faits.write_text(
            json.dumps(
                {
                    "_lisez_moi": (
                        "Faits VALIDES ajoutes au CV quand une annonce les appelle. Voir "
                        "profile/example_Facts.json pour le format."
                    ),
                    "faits": [],
                    "allegements": {"fr": [], "en": []},
                },
                ensure_ascii=False,
                indent=1,
            ),
            encoding="utf-8",
        )
        print(_t("  faits du CV   : {} (vide)").format(faits.relative_to(RACINE).as_posix()))

    cfg_p = HERE / "sources_config.json"
    cfg = json.loads(cfg_p.read_text(encoding="utf-8")) if cfg_p.exists() else {}
    cfg["keywords"] = profil["collecte"]["mots_cles"]
    if not garder:
        cfg["ats_slugs"], cfg["workday_flux"], cfg["autres_flux"] = {}, [], []
        # The sector lists (3.32) are ticked in the app: Sources → Entreprises suivies.
        cfg["listes"] = []
    else:
        # A new profile starts from the main one's settings, whose lists may have been
        # emptied (a non-finance main profile): "keep" then gave a finance profile no
        # company at all. An empty list is dropped, so the engine's ~90 apply.
        for cle in ("ats_slugs", "workday_flux", "autres_flux"):
            if cle in cfg and not cfg[cle]:
                del cfg[cle]
        if "listes" in cfg:  # settings with sector lists: "keep" ticks the finance one
            from jobhunter.sources import company_lists

            company_lists.activer(cfg, company_lists.FINANCE)
    cfg_p.write_text(json.dumps(cfg, ensure_ascii=False, indent=1), encoding="utf-8")
    print(
        _t("  recherche     : {} mot(s)-cle(s)").format(len(cfg["keywords"]))
        + ("" if garder or not finance else _t(" · listes d'entreprises finance/ESG videes"))
    )

    print(_t("\n4. A relire dans {}").format(sortie.relative_to(RACINE).as_posix()))
    manque = []
    if A_COMPLETER in json.dumps(profil["identite"], ensure_ascii=False):
        manque.append(_t("identite : champs « A COMPLETER »"))
    # An English CV fills parcours_en: the letters have their paragraph.
    if not (profil["domaines"][0]["parcours_fr"] or profil["domaines"][0].get("parcours_en")):
        manque.append(
            _t(
                "domaines[].parcours_fr : le paragraphe de parcours de tes lettres (3-4 phrases "
                "factuelles : formation, experiences, ce que tu apportes) — VIDE pour l'instant"
            )
        )
    if len(comps) < 5:
        manque.append(
            _t(
                "competences : seulement {} reconnue(s) — ajoute les tiennes "
                "(libelle + synonymes que les annonces emploient)"
            ).format(len(comps))
        )
    vides = [k for k in ("diplome_fr", "langues_fr") if not profil["message"][k]]
    if vides:
        manque.append(
            _t("message.{} : une phrase chacun (pas trouvé dans le CV)").format(" / ".join(vides))
        )
    if cv.suffix.lower() == ".pdf":
        manque.append(
            _t(
                "CV en PDF : il partira tel quel. Fournis un .docx pour des CV adaptes a chaque offre"
            )
        )
    for m in manque:
        print(f"  - {m}")
    if not manque:
        print(_t("  rien d'obligatoire : tout ce qu'il faut a été lu dans le CV"))
    print(
        _t(
            "\nVerifier : python JobHunter.pyw show-profile   ·   Lancer l'app : python JobHunter.pyw"
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
