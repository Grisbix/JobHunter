"""Cover letter per offer: salutation, context, body, skills.

Part of jobhunter.documents (formerly Scripts/tailor_application.py, phase 3.5).
"""

import importlib
import re
import sys
from pathlib import Path
from typing import Any

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt

from jobhunter import lazy as _paresseux
from jobhunter import paths as chemins
from jobhunter import profile as _P
from jobhunter.documents import generated as _generes
from jobhunter.documents.common import (
    _de,
    _slug,
    company_value,
    match_skills,
    minuscule_titre,
    titre_poste,
)
from jobhunter.scoring.lexicon import cv_variant_key

_ici = sys.modules[__name__]
# Values taken from the profile: computed on first read, not at import
# (jobhunter.lazy). In this module, they are read through `_ici.NAME`.
_PARESSEUX: _paresseux.Fabriques = {}


def __getattr__(nom: str) -> Any:
    return _paresseux.lire(_ici, _PARESSEUX, nom)


_PARESSEUX["LT_OUT"] = lambda: importlib.import_module("jobhunter.documents.common").LT_OUT


_PARESSEUX["PROFILE"] = lambda: importlib.import_module("jobhunter.documents.common").PROFILE


_PARESSEUX["SKILL_INTERNES"] = lambda: (
    importlib.import_module("jobhunter.documents.common").SKILL_INTERNES
)


_PARESSEUX["_COMP"] = lambda: importlib.import_module("jobhunter.scoring.lexicon")._COMP


_PARESSEUX["_DOMAINES"] = lambda: importlib.import_module("jobhunter.scoring.lexicon")._DOMAINES


_PARESSEUX["SKILL_LEX"] = lambda: importlib.import_module("jobhunter.scoring.lexicon").SKILL_LEX


def _citable(t: str | None, langue: str) -> bool:
    """Can this passage be QUOTED in a letter written in `langue`?

    A quotation in the other language jumps out: the English letter for
    TotalEnergies Congo — whose posting is French but asks "Merci de candidater en
    anglais" — quoted "Bac+5 ecole d'ingenieurs ou de commerce, specialisation
    economie ou finance ; connaissances en economie et finance d'entreprise" right in
    the middle of an English paragraph.

    Better NO QUOTATION than a quotation in the wrong language: the sentence that
    carries it is optional, it disappears cleanly.
    """
    t = (t or "").strip()
    if len(t) <= 15:
        return False
    try:
        from jobhunter.scoring.language import langue_offre

        # langue_offre needs 120 characters to decide; below that it
        # answers "fr" by default, which would silence any short quotation
        # in an English letter. So we only decide on a text that is
        # long enough to be judged.
        if len(t) < 120:
            return True
        return langue_offre("", t) == langue
    except Exception:
        return True


# Background paragraph, per offer domain. Same facts, different order and
# emphasis — the key is the one of cv_variant_key, so the letter tells the
# same story as the attached CV.
# A sentence carries only ONE conjunction. Beyond that, the clauses are glued
# end to end instead of flowing, and the letter reads like a list:
#   "…valorisation par DCF ET analyse de bilan, ET labellisation
#     SFDR…" — three "et" in the same sentence.
# The colon and the comma do the same job without adding to the noise.
# No em dash and no slash either: "risque/performance" is written
# "le risque et la performance".
_PARESSEUX["SOCLE_FR"] = lambda: ({d["cle"]: d.get("parcours_fr") or "" for d in _ici._DOMAINES})


_PARESSEUX["SOCLE_EN"] = lambda: ({d["cle"]: d.get("parcours_en") or "" for d in _ici._DOMAINES})


def _experimente() -> bool:
    """Is the profile's letter tone `lettre.ton` = "experimente"?

    The letter then speaks of experience put to work, not of a path started at
    school. Set by `first_launch` from 3 years on; absent = the young-graduate wording.
    """
    return _P.get("lettre.ton", "") == "experimente"


def socle(cle: str, langue: str = "fr") -> str:
    """Background paragraph of the `cle` domain, or that of the first domain that has one: a letter without a background says nothing about the candidate."""
    table = _ici.SOCLE_EN if langue == "en" else _ici.SOCLE_FR
    if table.get(cle):
        return str(table[cle])
    return next((v for v in table.values() if v), "")


# ── PARAGRAPHES DE CONTEXTE ──────────────────────────────────────────────────
# The profile may declare facts that only count for some offers
# (`lettre.contextes`): an experience in a sector, a volunteering commitment.
# Each carries its trigger words. Rules, all learnt on letters
# reelles :
#   - the TITLE is sovereign: one trigger word in the title is enough;
#   - otherwise `occurrences_min` occurrences are needed in the text (a MENTION
#     de passage — « nos clients vont de l'agroalimentaire a l'aeronautique » —
#     is not a SUBJECT);
#   - `ignorer` erases misleading proper nouns before counting ("Credit
#     Agricole » contient « agricol ») ;
#   - `densite_coeur`: the text must also be dense in vocabulary of the core
#     axis, as the scoring requires (anti-boilerplate);
#   - `sauf_domaines`: useless when the chosen background already says the same thing;
#   - ONE SINGLE context per letter, the first of the list that applies:
#     the concrete drives out the generic, two neighbouring paragraphs repeated each other.
_PARESSEUX["_CONTEXTES"] = lambda: _P.get("lettre.contextes", []) or []


def _contexte_applicable(ctx: dict[str, Any], offer: dict[str, Any]) -> bool:
    if cv_variant_key(offer.get("domaine")) in (ctx.get("sauf_domaines") or []):
        return False
    rx = _P.motif(ctx.get("mots"))
    if rx is None:
        return False
    ign = _P.motif(ctx.get("ignorer"))

    def net(t: str | None) -> str:
        return ign.sub(" ", t or "") if ign else (t or "")

    role = net(str(offer.get("role") or ""))
    if rx.search(role):
        return True
    texte = net(
        " ".join(
            str(offer.get(k) or "") for k in ("company", "role", "offer_text", "missions", "profil")
        )
    )
    if len(rx.findall(texte)) < int(ctx.get("occurrences_min") or 1):
        return False
    if ctx.get("densite_coeur"):
        # Deferred import: ats_match imports this module.
        from jobhunter.scoring.fit import _ESG_DENSITE_LONG, _ESG_DENSITE_MIN, densite_esg

        if len(texte) >= _ESG_DENSITE_LONG and densite_esg(texte) < _ESG_DENSITE_MIN:
            return False
    return True


def contexte(
    offer: dict[str, Any], langue: str = "fr", position: str | None = None
) -> tuple[str, str]:
    """(position, text) of the context to add, or ("", "").

    position: "socle" (added to the background) or "paragraphe" (separate paragraph).

    `position` restricts the search to a single position. Without it, the FIRST
    applicable context hid the others: an offer that was both agricultural
    (paragraph) and sustainable (base) lost the sustainable sentence of the message,
    which the original code added independently (Ortec, 15/10).
    """
    for ctx in _ici._CONTEXTES:
        if position and (ctx.get("position") or "paragraphe") != position:
            continue
        if _contexte_applicable(ctx, offer):
            t = ctx.get("en" if langue == "en" else "fr") or ""
            if t:
                return ctx.get("position") or "paragraphe", t
    return "", ""


def contexte_durable(offer: dict[str, Any], langue: str = "fr") -> str:
    """Compatibility: the text of a context placed in the base, or ""."""
    return contexte(offer, langue, "socle")[1]


def contexte_agricole(offer: dict[str, Any], langue: str = "fr") -> str:
    """Compatibility: the text of a context as a separate paragraph, or ""."""
    return contexte(offer, langue, "paragraphe")[1]


# ── WHO THE LETTER IS ADDRESSED TO ───────────────────────────────────────────
# Until now the letter opened with a hard-coded "Madame, Monsieur," and closed with
# "Je vous prie d'agreer, Madame, Monsieur". The message, for its part, already knew
# how to name the recruiter through `message_offre.appel()`. Two documents going
# in the same envelope, one addressed by name and the other not.
#
# A POSTING MAY NAME TWO. Mirova writes "adressez votre CV et votre
# lettre a Louis Mac Arthur et Clement Lebrun" — two recipients, of which
# `appel()` knows nothing: it handles ONE person, and its 26 test cases
# hold for that contract. So we do not change it; we call it once
# per name.
#
# SAFEGUARD: the split is kept ONLY if each piece gives a named
# salutation. A single generic fragment, and we fall back to the whole field,
# hence to the previous behaviour. "Monsieur Jean et Marie Dupont" will
# never produce "Monsieur Jean, Madame Dupont".
_CIV_FEM = {"madame", "mme", "mrs", "ms"}


def _reprise(civs: list[str], langue: str) -> str:
    """The title ALONE, for the closing formula.

    "Je vous prie d'agreer, Monsieur Mac Arthur, Monsieur Lebrun" is not said: the
    closing repeats the title, never the surname. For two men it agrees in the
    plural — "Messieurs".
    """
    connus = [c for c in civs if c]
    if not connus or len(connus) != len(civs):
        return "Madame, Monsieur" if langue != "en" else "Sir or Madam"
    fem = [c in _CIV_FEM for c in connus]
    if langue == "en":
        return "Sir or Madam"  # English closes with "Yours sincerely"
    if all(fem):
        return "Madame" if len(connus) == 1 else "Mesdames"
    if not any(fem):
        return "Monsieur" if len(connus) == 1 else "Messieurs"
    return "Madame, Monsieur"


def corps_sur_mesure(offer: dict[str, Any]) -> list[str]:
    """The paragraphs written by hand for this offer, or [] if there are none.

    The file is named `<entreprise>__<poste>.txt`, paragraphs separated by an empty
    line.

    The search is TOLERANT of case and punctuation: the file name comes from a
    posting title, which contains slashes, parentheses and random capitals. Windows
    already ignoring case, an exact search would only give a silent false negative.
    """
    from jobhunter.paths import LT_SUR_MESURE

    if not LT_SUR_MESURE.exists():
        return []
    # The target name goes through _slug AS A WHOLE, like the file's. Assembling
    # two slugs around a literal "__" gave "mirova__analyste…" against
    # a file reduced to "mirova_analyste…": the double separator survives
    # on one side and not on the other, and the tailor-made letter is never found.
    vise = _slug(f"{offer.get('company')}__{offer.get('role')}")
    for f in LT_SUR_MESURE.glob("*.txt"):
        if _slug(f.stem) == vise:
            texte = f.read_text(encoding="utf-8")
            return [p.strip() for p in re.split(r"\n\s*\n", texte) if p.strip()]
    return []


def _sans_societe(role: str, company: str) -> str:
    """Removes the company name from the title when the posting glued it there.

    "Analyste Investissement - Capital Naturel - Mirova" gave a letter subject
    "Candidature au poste d'analyste investissement - capital naturel - mirova": the
    proper noun goes lower case through `minuscule_titre`, which is right to do so
    for a title and wrong for a brand.

    8 offers of the queue out of 5374 are in this case. ONLY the subject is touched:
    the file name still derives from the raw title, otherwise the documents already
    generated would end up orphaned.
    """
    r, c = (role or "").strip(), (company or "").strip()
    if not c:
        return r
    # A short dash is a separator only when SURROUNDED by spaces: "F-Gas" and
    # "LCB-FT" are words. Cutting on it then gluing back with " - " gave
    # l'objet « F - Gas & Sustainability Analyst » (Aggreko, 2026-10-04).
    coupe = re.split(r"\s+-\s+|\s*[–—|@]\s*", r)
    if len(coupe) < 2 or coupe[-1].strip().lower() != c.lower():
        return r
    while len(coupe) > 1 and coupe[-1].strip().lower() == c.lower():
        coupe.pop()
    return " - ".join(coupe).strip() or r


def salutation(offer: dict[str, Any], langue: str = "fr") -> tuple[str, str, bool]:
    """Returns (salutation, closing formula, named?).

    THE TEXT OF THE SALUTATION COMES FROM `message_offre.appel`, which already knows
    how to do it and whose 26 test cases check it — splitting of multiple recipients
    included. What is added here is specific to the LETTER: the closing formula,
    which the message does not have.
    """
    from jobhunter.documents.message import (
        _RX_CIVILITE,
        _RX_SEPARE,
        GENERIQUES,
        appel,
        nom_dans_offre,
    )

    rh = (offer.get("rh") or "").strip()
    # A recipient the posting does not name is not named (2026-10-07).
    if offer.get("offer_text") is not None:
        rh = nom_dans_offre(rh, offer.get("offer_text"))
    texte = appel({"rh": rh}, langue)
    if texte in GENERIQUES:
        return texte, ("Sir or Madam" if langue == "en" else "Madame, Monsieur"), False

    # The titles actually kept, in order, to agree the
    # closing. We re-read the pieces rather than the formula produced: "Madame
    # Moussa" and "Monsieur de Gaulle" stand apart there without having to re-split
    # text already formatted.
    morceaux = [x.strip() for x in _RX_SEPARE.split(rh) if x.strip()] or [rh]
    civs = []
    for x in morceaux:
        if appel({"rh": x}, langue) in GENERIQUES and len(morceaux) > 1:
            continue  # piece discarded by `appel`
        g = _RX_CIVILITE.match(x)
        civs.append(g.group(1).lower() if g else "")
    return texte, _reprise(civs, langue), True


def company_value_en(company: str | None) -> str:
    """Known English hook, or "" (same rule as company_value)."""
    c = (company or "").lower()
    for k, v in _ici.COMPANY_VALUE_EN.items():
        if k in c:
            return str(v)
    return ""


_PARESSEUX["COMPANY_VALUE_EN"] = lambda: dict(_P.get("lettre.valeurs_entreprises_en", {}) or {})


# Skill labels as they are written IN A SENTENCE. On the CV
# they are section tags, where "Trésorerie / financement" and the
# initial capitals are normal. Copied into the letter, they gave:
#
#   "je me suis familiarisé avec Analyse financière, Modélisation financière,
#     Trésorerie / financement, Contrôle de gestion."
#
# Four stray capitals and a slash in the middle of a sentence. It
# reads like a database export, not like a letter. The article
# is included because it depends on the word (le, la, l', les) and no
# simple rule guesses it.
_PARESSEUX["SKILL_PROSE_FR"] = lambda: (
    {lab: v["prose_fr"] for lab, v in _ici._COMP.items() if v.get("prose_fr")}
)


_PARESSEUX["SKILL_PROSE_EN"] = lambda: (
    {lab: v["prose_en"] for lab, v in _ici._COMP.items() if v.get("prose_en")}
)


def _enumere(items: list[str], langue: str = "fr") -> str:
    """“a, b et c”. An enumeration ends with a conjunction, not with a comma: without it, the sentence reads like a bulleted list put end to end.

    An item may CONTAIN the conjunction ("la trésorerie et le financement",
    "Python et SQL"). Placed last, it gave two "et" in a row:
    "…, la trésorerie et le financement et le contrôle de gestion". These items
    therefore go first, where the conjunction does not collide.
    """
    items = [i for i in items if i]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    lien = " and " if langue == "en" else " et "
    # An item carrying a conjunction goes LAST, and its own serves as the
    # final conjunction. Putting it first added a second one:
    #   "la trésorerie et le financement, l'analyse financière ET le contrôle"
    # whereas by placing it at the end, one is enough:
    #   "l'analyse financière, le contrôle de gestion, la trésorerie et le
    #     financement »
    porteurs = [i for i in items if lien in i]
    if porteurs:
        autres = [i for i in items if lien not in i]
        return ", ".join(autres + porteurs[:1])
    return ", ".join(items[:-1]) + lien + items[-1]


def competences_en_prose(skills: list[str], langue: str = "fr", n: int = 4) -> str:
    """The skills kept, written to fit into a sentence.

    Two filters against repetition, both observed on a real output:

    1. No two items ending with the SAME word. "l'analyse financière, la
       modélisation financière" sounds like a stammer, and the second adds almost
       nothing to the first.
    2. ONE SINGLE item carrying "et". "la trésorerie et le financement, l'analyse
       financière et le contrôle de gestion": two conjunctions for three ideas,
       while the enumeration only needs one.
    """
    table = _ici.SKILL_PROSE_EN if langue == "en" else _ici.SKILL_PROSE_FR
    lien = " and " if langue == "en" else " et "
    vus: set[str] = set()
    fins: set[str] = set()
    sortie: list[str] = []
    for s in skills:
        p = table.get(s)
        if not p or p in vus:
            continue
        fin = p.rsplit(" ", 1)[-1].lower()
        if fin in fins:
            continue
        if lien in p and any(lien in q for q in sortie):
            continue
        vus.add(p)
        fins.add(fin)
        sortie.append(p)
        if len(sortie) >= n:
            break
    return _enumere(sortie, langue)


# Skills that are not TECHNICAL terms: quoting them in this
# enumeration gave "forecast, audit, excel, anglais" — and English is
# already announced two lines below, with its TOEIC score.
_PARESSEUX["_NON_TECHNIQUE"] = lambda: (
    {lab for lab, v in _ici._COMP.items() if v.get("technique") is False}
)


# False friends: French words of the lexicon that also exist in English with a
# completely different meaning. "assurance" (the sector) ended up quoted as a
# technical term in an English letter to TotalEnergies, where the posting only
# said "provide assurance". A French word found in an English text
# proves nothing.
_FAUX_AMIS_EN = {
    "assurance",
    "avocat",
    "location",
    "actuel",
    "formation",
    "experience",
    "notice",
    "large",
    "librairie",
    "cave",
}


# HOW EACH TERM IS WRITTEN IN THE LETTER'S LANGUAGE.
#
# The lexicon's keywords are the ones we SEARCH for in the posting: they are
# therefore in both languages, mixed. Printed as they are, they gave
# "je pratique ce que décrit votre annonce : forecast, Excel" — an English
# word in the middle of a French letter, which does not work.
#
# Each entry gives the FR form and the EN form. `None` = do not write in
# that language. A term missing from the table is not printed: better
# a shorter enumeration than one anglicism too many.
_PARESSEUX["_TERMES"] = lambda: ({k: tuple(v) for k, v in (_P.get("termes", {}) or {}).items()})


def mots_techniques(offer_text: str | None, n: int = 6, langue: str = "fr") -> list[str]:
    """The technical terms that the POSTING uses and that the CV covers.

    The skill labels are our vocabulary; this is THEIRS. An ATS looks for the
    posting's words, and a human reader recognises their own: quoting "clôture
    mensuelle" because they wrote it is better than naming "le contrôle de gestion"
    and hoping they make the connection.

    Only a term already covered by a CV skill is kept: repeating a word of the
    posting that we cannot justify would be padding.

    The term is WRITTEN in the letter's language, through _TERMES. The lexicon's
    keywords are used to SEARCH, so they are in both languages, mixed: printed raw,
    they gave "je pratique ce que décrit votre annonce : forecast, Excel" in the
    middle of a French letter. A term missing from _TERMES is not printed — a
    shorter enumeration is better than one anglicism too many.
    """
    t = (offer_text or "").lower()
    i = 0 if langue != "en" else 1
    trouves = []
    for lab, mots in _ici.SKILL_LEX.items():
        if lab in _ici.SKILL_INTERNES or lab in _ici._NON_TECHNIQUE:
            continue
        for m in mots:
            m = m.lower()
            if langue == "en" and m in _FAUX_AMIS_EN:
                continue
            # Word boundaries: without them "rse" is found in "transverse"
            # and "esg" in any identifier. It is the mistake that
            # comes back most often in this project.
            if len(m) >= 3 and re.search(r"\b" + re.escape(m) + r"\b", t):
                forme = _ici._TERMES.get(m, (None, None))[i]
                if forme and forme not in trouves:
                    trouves.append(forme)
                break
    return trouves[:n]


def _enable_hyphenation(doc: Any) -> None:
    """Turns on Word's automatic hyphenation → a justified text without "gaps" (rivers)."""
    try:
        from docx.oxml.ns import qn

        s = doc.settings.element
        if s.find(qn("w:autoHyphenation")) is None:
            el = s.makeelement(qn("w:autoHyphenation"), {qn("w:val"): "true"})
            s.append(el)
    except Exception:
        pass


# ---- Letter: docx tailored to the real missions ----
def tailor_letter(offer: dict[str, Any], nom: str | None = None, langue: str = "fr") -> Path:
    """`nom`: imposed stem, same reason as tailor_cv.

    `langue`: 'en' writes the letter in English. The FACTS are the same — same
    thesis, same 3,000 funds, same internship at Acme Finance — only the language
    changes. Polite formulas, however, are not translated word for word: "Je vous
    prie d'agreer…" has no literal equivalent and becomes "Yours faithfully", which
    is the expected form when the recipient is unknown ("Dear Sir or Madam").
    """
    chemins.preparer()  # output folders, at write time
    company = offer["company"]
    role = (offer["role"] or "ce poste").strip()
    skills = match_skills(offer["offer_text"])
    missions = (offer["missions"] or "").strip()
    profil = (offer["profil"] or "").strip()
    # WHO we write to. Returns the generic one when the `rh` field does not carry a
    # person — the case of 4501 offers out of 4917, hence the usual case.
    _appel, _reprise_civ, _nomme = salutation(offer, langue)
    # Body written by hand for THIS offer, if it exists. See corps_sur_mesure().
    _corps = corps_sur_mesure(offer)

    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(11)
    _enable_hyphenation(doc)  # automatic hyphenation: justified WITHOUT gaps (rivers)

    def para(
        txt: str, align: Any = WD_ALIGN_PARAGRAPH.JUSTIFY, space: int = 6, bold: bool = False
    ) -> Any:
        p = doc.add_paragraph()
        p.alignment = align
        r = p.add_run(txt)
        r.bold = bold
        p.paragraph_format.space_after = Pt(space)
        return p

    # sender header
    for line in [
        _ici.PROFILE["nom"],
        _ici.PROFILE["email"],
        _ici.PROFILE["tel"],
    ]:  # no address/city (privacy)
        para(line, WD_ALIGN_PARAGRAPH.LEFT, 0)
    para("")
    # today's date on the right; NO recipient block: recruiter's name unknown
    # -> the company name is not put (user's request 2026-07-12)
    from datetime import date as _d

    _MOIS = [
        "janvier",
        "février",
        "mars",
        "avril",
        "mai",
        "juin",
        "juillet",
        "août",
        "septembre",
        "octobre",
        "novembre",
        "décembre",
    ]
    _MONTHS = [
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ]
    _t = _d.today()
    para(
        f"{_MONTHS[_t.month - 1]} {_t.day}, {_t.year}"
        if langue == "en"
        else f"Le {_t.day} {_MOIS[_t.month - 1]} {_t.year}",
        WD_ALIGN_PARAGRAPH.RIGHT,
        12,
    )
    if langue == "en":
        _titre_en = titre_poste(_sans_societe(role, company))
        para(
            f"Subject: Application for the position of {_titre_en}"
            if _titre_en
            else "Subject: Speculative application",
            space=12,
            bold=True,
        )
        para(_appel)
        # THE HAND-WRITTEN BODY short-circuits the template. What surrounds it
        # stays generated: it is what knows how to name two recipients and
        # agree the closing.
        if _corps:
            for _bloc in _corps:
                para(_bloc)
            para("Yours sincerely," if _nomme else "Yours faithfully,", space=12)
            para(_ici.PROFILE["nom"], WD_ALIGN_PARAGRAPH.LEFT, 0)
            from jobhunter.programs.rename_docs import new_name

            out_sm: Path = _ici.LT_OUT / ((nom or new_name("Lettre", role, company)) + ".docx")
            _generes.enregistrer(doc, out_sm)  # never over a hand retouch
            return out_sm
        # "caught my full attention" is the calque of "a retenu toute mon
        # attention": nobody writes that in English. "I read your
        # advertisement with great interest" is the usual phrase.
        # And as in French, we lend no commitment to a company
        # we do not know: without an identified value, we talk about the job.
        _val_en = company_value_en(company)
        _connue_en = bool(_val_en)
        para(
            "I read your advertisement with great interest: "
            + (_val_en if _connue_en else "this role")
            + (
                " matches the experience I have built and where I want to take it next."
                if _experimente()
                else " matches the career path I have been building since my studies."
            )
        )
        # The background follows the offer's DOMAIN: writing "je me suis
        # specialise en finance durable" to an oil company looking for
        # an economic analyst is talking beside the point.
        _cle = cv_variant_key(offer.get("domaine"))
        socle_en = socle(_cle, "en")
        # Same removal as in French: we glued 220 characters of their
        # posting between parentheses, cut in the middle of a sentence.
        # SEPARATE paragraph, not an extension of the base: that one already has
        # four sentences, and a fifth about Portuguese olive trees would get
        # lost in it. Empty for any non-agricultural offer.
        _agri_en = contexte_agricole(offer, "en")
        # THE CONCRETE DRIVES OUT THE GENERIC. The sustainable sentence says "that work
        # covered sustainable investment: SFDR classification"; the agricultural
        # paragraph says the same thing while naming the funds and the field. The
        # two together gave "SFDR" twice in four lines, and
        # "fund" three times — spotted by verifie_redites.py on the Mirova
        # letter. When the agricultural one goes in, the generic one stays silent.
        _dur_en = "" if _agri_en else contexte_durable(offer, "en")
        if _dur_en:
            socle_en += " " + _dur_en
        if socle_en.strip():
            para(socle_en)
        if _agri_en:
            para(_agri_en)
        if skills:
            # Four skills, not six: beyond that, the enumeration stops being
            # a sentence and becomes a list of keywords.
            prose_en = competences_en_prose(skills, "en", 4)
            if prose_en:
                techs_en = [
                    m
                    for m in mots_techniques(
                        f"{offer.get('missions', '')} {offer.get('profil', '')} "
                        f"{offer.get('offer_text', '')}",
                        12,
                        "en",
                    )
                    if m.lower() not in prose_en.lower()
                ][:4]
                ph = (
                    f"In these roles I have put into practice {prose_en}."
                    if _experimente()
                    else f"Along the way I became familiar with {prose_en}."
                )
                if len(techs_en) >= 2:
                    ph += (
                        " I also work with what your advertisement describes: "
                        + ", ".join(techs_en)
                        + "."
                    )
                para(
                    ph
                    + (
                        " I would bring this experience to your teams."
                        if _experimente()
                        else " These are foundations I would be glad to deepen within your teams."
                    )
                )
        if _citable(profil, "en") and profil.lower() not in ("non précisé", "à compléter", "nan"):
            # The English semicolon was no better than the French one.
            _pp_en = _P.get("lettre.phrase_profil_en", "") or ""
            if _pp_en:
                para(_pp_en)
        # « I would be VERY glad to discuss IN PERSON what I COULD bring […] at
        # your convenience": three softeners in one sentence. We ask
        # for an interview, we do not apologise for asking.
        para(
            "I would welcome the opportunity to discuss this role with you and am "
            "available for an interview at your convenience."
        )
        # "Yours faithfully" is the expected formula when the recipient is
        # unknown; "Yours sincerely" assumes they were named. The letter now knows
        # which of the two cases applies.
        para("Yours sincerely," if _nomme else "Yours faithfully,", space=12)
        para(_ici.PROFILE["nom"], WD_ALIGN_PARAGRAPH.LEFT, 0)
        from jobhunter.programs.rename_docs import new_name

        out_en: Path = _ici.LT_OUT / ((nom or new_name("Lettre", role, company)) + ".docx")
        _generes.enregistrer(doc, out_en)
        return out_en
    # the RAW title of the posting does not go into the letter: see titre_poste()
    # In French a job title is a common noun. Postings
    # capitalise it the English way — "Contrôleur de Gestion Financier" — and we
    # copied it as is into the subject.
    _titre = minuscule_titre(titre_poste(_sans_societe(role, company)))
    para(
        f"Objet : Candidature au poste {_de(_titre)}"
        if _titre
        else "Objet : Candidature spontanée",
        space=12,
        bold=True,
    )
    para(_appel)

    # THE HAND-WRITTEN BODY, same rule as in English.
    if _corps:
        for _bloc in _corps:
            para(_bloc)
        para(
            f"Je vous prie d'agréer, {_reprise_civ}, l'expression de mes salutations distinguées.",
            space=12,
        )
        para(_ici.PROFILE["nom"], WD_ALIGN_PARAGRAPH.LEFT, 0)
        from jobhunter.programs.rename_docs import new_name

        out_sm = _ici.LT_OUT / ((nom or new_name("Lettre", role, company)) + ".docx")
        _generes.enregistrer(doc, out_sm)
        return out_sm

    # INTRO. Three wording fixes, all taken from the proofreading
    # of a real letter (Crédit Mutuel AM):
    #
    # 1. The full title was repeated WORD FOR WORD just after the subject, two
    #    lines above. "Votre annonce" is enough: the reader has just read it.
    # 2. "a retenu TOUTE mon attention": the superlative weakens. We keep
    #    « a retenu mon attention ».
    # 3. company_value() returned its generic sentence — "votre engagement en
    #    faveur de la finance durable" — for 5831 offers out of 5907, i.e. 98%.
    #    Written to Van Cleef & Arpels (jeweller) or to EY, it rings false and
    #    asserts nothing. When the company is unknown, we lend it NO
    #    commitment: we talk about the job, which we know.
    _valeur = company_value(company)
    _connue = bool(_valeur)
    _sujet = _valeur if _connue else "ce poste"
    para(
        f"Votre annonce a retenu mon attention : {_sujet} "
        + (
            "correspond à mon expérience et à la suite que je veux lui donner."
            if _experimente()
            else "rejoint le projet professionnel que je construis depuis mes études."
        )
    )

    # body 1: proof through the background (facts, no superlatives)
    # Same rule as in English: the background follows the offer's domain.
    socle_txt = socle(cv_variant_key(offer.get("domaine")), "fr")
    # THE MISSIONS ARE NO LONGER QUOTED. We glued 220 characters of the posting
    # between parentheses, cut in the middle of a sentence:
    #
    #   "Les missions que vous décrivez (Dans le cadre de son développement en
    #     Inde, notre filiale de Bangalore recherche un(e) VIE – Contrôleur de
    #     Gestion Financier. Rattaché(e) à la Direction Financière…) font écho
    #     à ces expériences."
    #
    # Their own text was sent back to them as is, with the posting's
    # capitals, the inclusive forms "un(e)", the en dash and
    # an ellipsis in place of the end. It is not a
    # quotation, it is a truncated copy-paste.
    #
    # Instead: the technical terms that the posting uses AND that the CV
    # covers. They are THEIR words, which helps ATS filtering, and each is
    # justified by a real skill.
    #
    # And if the employer works in sustainability without the JOB being an
    # ESG job — a corporate finance analyst at a renewable energy
    # producer —, the master's specialisation is said here. Otherwise the letter
    # to a green energy company did not breathe a word of it.
    # The agricultural field, as a stand-alone paragraph. Same reason as in English:
    # the base is already full, and these two facts — the Atlantic Agri fund,
    # Terres Solidaires — deserve to be read, not slipped in at the end of a sentence.
    _agri = contexte_agricole(offer, "fr")
    # THE CONCRETE DRIVES OUT THE GENERIC, see the English branch.
    _dur = "" if _agri else contexte_durable(offer, "fr")
    if _dur:
        socle_txt += " " + _dur
    if socle_txt.strip():  # empty background in the profile: no hollow paragraph
        para(socle_txt)
    if _agri:
        para(_agri)

    # body 2: skills brought with humility (owned junior status, eagerness to learn)
    # The raw labels were copied as they appear on the CV, where they
    # are section TAGS: "Analyse financière, Modélisation
    # financière, Trésorerie / financement, Contrôle de gestion". Four
    # stray capitals and a slash in the middle of a sentence.
    # SKILL_PROSE_FR gives the form that is said. FOUR skills, not six:
    # beyond that, the enumeration stops being a sentence.
    if skills:
        prose = competences_en_prose(skills, "fr", 4)
        if prose:
            # The posting's terms that the CV covers, in APPOSITION after a
            # colon. Without an article, hence without an agreement problem: "forecast,
            # reporting, Excel" works for any word, where "avec le
            # forecast et le reporting" would require guessing the gender of
            # each one. It is also the form an ATS reads, which looks for the words
            # of the posting and not for our in-house labels.
            techs = [
                m
                for m in mots_techniques(
                    f"{offer.get('missions', '')} {offer.get('profil', '')} "
                    f"{offer.get('offer_text', '')}",
                    12,
                    "fr",
                )
                if m.lower() not in prose.lower()
            ][:4]
            if _experimente():
                phrase = f"Dans ces postes, j'ai mis en œuvre {prose}."
            else:
                phrase = f"Au fil de ce parcours, je me suis {_P.accord('familiarisé', 'familiarisée')} avec {prose}."
            if len(techs) >= 2:
                phrase += (
                    " Je pratique aussi ce que décrit votre annonce : " + ", ".join(techs) + "."
                )
            para(
                phrase
                + (
                    " J'apporterai cette expérience à vos équipes."
                    if _experimente()
                    else f" Ce sont des acquis que je serais {_P.accord('heureux', 'heureuse')} "
                    "d'approfondir au sein de vos équipes."
                )
            )
    # The profile is no longer quoted either: same truncated copy-paste, followed
    # by a semicolon that nobody writes in a letter.
    if _citable(profil, "fr") and profil.lower() not in ("non précisé", "à compléter", "nan"):
        _pp = _P.get("lettre.phrase_profil_fr", "") or ""
        if _pp:
            para(_pp)

    # CLOSING. The old version stacked three conditionals and two ready-made
    # phrases: "Je SERAIS TRÈS heureux de vous exposer DE VIVE VOIX ce
    # que je POURRAIS apporter […] à votre convenance". A sentence that
    # apologises for asking for an interview does not make one want to grant it.
    para(
        f"Je serais {_P.accord('heureux', 'heureuse')} d'échanger avec vous sur ce poste et me tiens à "
        "votre disposition pour un entretien."
    )
    # THE CLOSING MUST ANSWER THE SALUTATION. Writing "Monsieur Mac Arthur," at
    # the top and "agréer, Madame, Monsieur" at the bottom is the classic mistake of
    # fill-in-the-blank letters: the closing gives away the template the opening hid.
    para(
        f"Je vous prie d'agréer, {_reprise_civ}, l'expression de mes salutations distinguées.",
        space=12,
    )
    para(_ici.PROFILE["nom"], WD_ALIGN_PARAGRAPH.LEFT, 0)

    from jobhunter.programs.rename_docs import (
        new_name,  # Prenom_Nom_Lettre_<Poste court>_<Entreprise>
    )

    out: Path = _ici.LT_OUT / ((nom or new_name("Lettre", role, company)) + ".docx")
    _generes.enregistrer(doc, out)
    return out
