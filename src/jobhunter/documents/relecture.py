"""Proofreading of a letter: a second pass that reports, without ever rewriting.

Part of jobhunter.documents. The generator assembles pieces that are correct one by
one; what is wrong shows when reading the whole, set against the posting. This pass
starts from scratch, without the context of the writing, and returns a list of remarks.
It is the user who corrects (`Lettres/Sur_mesure/`).

What it looks for, in addition to the repetitions of `verifie_redites`:
- the candidate who undersells themselves ("encore court", "malgré", "je suis junior")
  — the rule that comes before all others — and its opposite, the hollow superlative;
- "excellent" for a language level (one writes "courant" / "fluent");
- em dash and slash in the running text;
- a company other than the offer's named in the letter (copy-paste);
- a named recipient that the posting does not name;
- what a booby-trapped posting could have slipped into a letter written by AI:
  instruction to the model, unknown web or email address. The posting is untrusted input.
- an unfilled template.

The patterns are in French and in English. A remark is a clue, not a verdict.
"""

import collections
import html
import re
import unicodedata
import zipfile
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from jobhunter.documents.controle import _RX_GABARIT  # the same pattern as the check


@dataclass(frozen=True)
class Remarque:
    """A point to review in the letter."""

    regle: str  # "dévalorisation", "superlatif", "langue", …
    extrait: str  # the passage concerned, short
    conseil: str


def _plat(texte: str) -> str:
    t = unicodedata.normalize("NFKD", texte.casefold()).encode("ascii", "ignore").decode()
    return " ".join(t.split())


def _extrait(texte: str, debut: int, fin: int, marge: int = 40) -> str:
    a, b = max(0, debut - marge), min(len(texte), fin + marge)
    return ("…" if a else "") + " ".join(texte[a:b].split()) + ("…" if b < len(texte) else "")


# (rule, pattern, advice). Patterns searched on the text as is, case-insensitive.
_MOTIFS: tuple[tuple[str, str, str], ...] = (
    (
        "dévalorisation",
        r"\b(?:court(?:e)? mais|encore (?:court|jeune|limit|peu)|malgr[ée] (?:mon|ma|mes|un|une)"
        r"|je (?:suis|reste) (?:encore )?junior|junior et je l.assume|sans d[ée]tour"
        r"|je ne cherche pas [àa] (?:masquer|cacher)|peu d.exp[ée]rience|manque d.exp[ée]rience"
        r"|m[eê]me si (?:mon|ma|je)|bien que (?:mon|ma|je)"
        r"|although (?:my|i)|limited experience|lack of experience|still (?:junior|new|early)"
        r"|despite my)",
        "On énonce ce qu'on apporte, jamais ce qui manque : supprimer la concessive, "
        "le paragraphe tient sans.",
    ),
    (
        "superlatif",
        r"\b(?:retenu toute mon attention|sp[ée]cialisation rare|se rencontrent rarement"
        r"|constitue ma sp[ée]cialit[ée]|le seul (?:sujet|candidat|profil)|parfaitement adapt"
        r"|profil id[ée]al|candidat id[ée]al|caught my (?:full )?attention|ideal candidate"
        r"|perfect (?:fit|match)|unique (?:profile|combination))",
        "Pas de superlatif ni de jugement sur le marché : prouver par un fait chiffré.",
    ),
    (
        "langue",
        r"\b(?:excellent(?:e)?s? (?:niveau d.)?(?:anglais|allemand|espagnol|italien|fran[çc]ais)"
        r"|(?:anglais|allemand|espagnol|italien) excellent|excellent (?:english|german|spanish"
        r"|french|italian)|(?:english|german|spanish|french) \(excellent\))",
        "Niveau de langue : « courant » (« fluent »), jamais « excellent ».",
    ),
    (
        "injection",
        r"\b(?:ignore (?:all |the )?(?:previous|above|prior)|instructions? (?:pr[ée]c[ée]dentes|"
        r"ci-dessus)|en tant qu.(?:ia|intelligence artificielle|assistant)|as an ai\b"
        r"|language model|mod[èe]le de langage|system prompt|prompt\b)",
        "Texte étranger à une lettre, sans doute venu de l'annonce : à retirer, et vérifier "
        "le reste de la lettre.",
    ),
)
_RX = tuple((r, re.compile(m, re.I), c) for r, m, c in _MOTIFS)
_RX_URL = re.compile(r"\bhttps?://\S+|\bwww\.\S+", re.I)
_RX_MAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
# "Madame Dupont," / "Dear Ms Smith,": a title followed by a proper noun. The
# salutation may name several ("Madame Martin, Madame Dupont,"): each one
# is searched in the posting, not only the first (Codex audit of 19/10).
_CIV = r"(?:Madame|Monsieur|(?:Dear )?(?:Mr|Mrs|Ms|Miss|Dr)\.?)"
_RX_APPEL = re.compile(_CIV + r"\s")
_RX_NOMME = re.compile(
    r"(?:^|(?<=, )|(?<= et )|(?<= and ))"
    + _CIV
    + r"\s+([A-ZÀ-Ý][\w'’-]+(?:\s+[A-ZÀ-Ý][\w'’-]+)*)(?=\s*,|\s+(?:et|and)\s)"
)


# ── Repetitions (formerly verifie_redites, moved in 2.13) ─────────────────────

# Stop words and polite formulas: their repetition says nothing.
_BANALS_BASE = {
    "votre",
    "notre",
    "leurs",
    "comme",
    "depuis",
    "serais",
    "heureux",
    "sein",
    "equipes",
    "équipes",
    "parcours",
    "monsieur",
    "madame",
    "salutations",
    "distinguees",
    "distinguées",
    "expression",
    "disposition",
    "entretien",
    "poste",
    "annonce",
    "vous",
    "avec",
    "dans",
    "pour",
    "mais",
    "plus",
    "cette",
    "sont",
    "suis",
    "elles",
}


def _banals() -> set[str]:
    """The commonplace words, plus the candidate's name (read in the greeting)."""
    try:
        from jobhunter.profil import identite

        nom = {m.lower() for m in identite()["nom"].split()}
    except Exception:  # profile missing: we count without its name
        nom = set()
    return _BANALS_BASE | nom


def texte(chemin: Path | str) -> str:
    """The displayed text of a .docx, paragraphs separated."""
    x = zipfile.ZipFile(chemin).read("word/document.xml").decode("utf-8", "replace")
    x = re.sub(r"</w:p>", "\n", x)
    return html.unescape(re.sub(r"<[^>]+>", "", x)).strip()


# The salutation, whatever it is. This spotting looked for "Madame,"
# or "Dear " at the start of a line, which covered the only two formulas that
# the letter could write. Since it names the recruiter, it opens with
# "Monsieur Mac Arthur," or "Madame Moussa, Madame Girard," — and the header
# was no longer cut at all. The name, the email, the phone and the subject
# then entered the count: the Mirova letter was blamed for
# "2 conjonctions" in a block that started with its own name.
#
# So we recognise a SHORT LINE ending with a comma, which no
# header line does and which every salutation does.
_RX_APPEL = re.compile(r"^(?:Madame|Monsieur|Mesdames|Messieurs|Bonjour|Dear)\b.{0,60},$")


def corps(t: str) -> str:
    """The body, without the header (name, email, phone, date, subject)."""
    lignes = [l for l in t.split("\n") if l.strip()]
    for i, l in enumerate(lignes):
        if _RX_APPEL.match(l.strip()):
            return "\n".join(lignes[i + 1 :])
    return "\n".join(lignes)


def defauts(t: str) -> list[str]:
    """The list of a letter's repetitions. Empty = nothing to report."""
    c = corps(t)
    trouves: list[str] = []
    banals = _banals()

    for ph in re.split(r"(?<=[.!?])\s+", c):
        n = len(re.findall(r"\b(?:et|and)\b", ph, re.I))
        if n >= 2:
            trouves.append(f"{n} conjonctions : {ph[:88]}…")

    # NO SEMICOLON. The user's request, 2026-09-21. It joins two
    # clauses that the full stop separates better: the second reads on its own, and a
    # cover letter gains from being made of short sentences. In a
    # CV enumeration, it does the job of the " · " that these documents
    # already use elsewhere — a single separator is better than two.
    for m in re.finditer(r"[^.!?]*;[^.!?]*", c):
        trouves.append(f"point-virgule : {m.group(0).strip()[:82]}…")

    # Enumeration items: we split on the commas AND on the
    # final conjunction, otherwise "l'analyse financière et la modélisation
    # financière" counts as a single item and the repetition goes through.
    for ph in re.split(r"(?<=[.!?])\s+", c):
        elems = [e.strip() for e in re.split(r",|\bet\b|\band\b", ph) if e.strip()]
        fins = [e.rsplit(" ", 1)[-1].lower().strip(".:;") for e in elems if len(e.split()) >= 2]
        for mot, n in collections.Counter(fins).items():
            if n >= 2 and len(mot) >= 5 and mot not in banals:
                trouves.append(f"« {mot} » finit {n} elements : {ph[:78]}…")

    # LOWER-CASE words only. "Master en Finance", "Acme Finance"
    # and "corporate finance" counted as three repetitions of the same word,
    # while the first two are proper nouns — a degree and a
    # company — that can neither be renamed nor avoided. Only the words
    # that the writing really chooses remain.
    mots = re.findall(r"\b[a-zà-ÿ]{5,}\b", c)
    for mot, n in collections.Counter(mots).items():
        if n >= 3 and mot not in banals:
            trouves.append(f"« {mot} » revient {n} fois dans le corps")

    return trouves


def relire(
    lettre: str,
    entreprise: str = "",
    annonce: str = "",
    autres_entreprises: Iterable[str] = (),
    connus: Iterable[str] = (),
) -> list[Remarque]:
    """The remarks on a letter; empty = nothing to report.

    Args:
        lettre: the text of the letter (header included: it is set aside here).
        entreprise: the offer's company.
        annonce: the text of the posting (for the recipient's name).
        autres_entreprises: the other companies of the queue; a single one named in
            the letter gives away a copy-paste.
        connus: legitimate web and email addresses (the profile's, the company's).
    """
    le_corps = corps(lettre)
    sortie: list[Remarque] = []
    for regle, rx, conseil in _RX:
        for m in rx.finditer(le_corps):
            sortie.append(Remarque(regle, _extrait(le_corps, m.start(), m.end()), conseil))
    for m in _RX_GABARIT.finditer(lettre):
        sortie.append(
            Remarque("gabarit", _extrait(lettre, m.start(), m.end()), "Champ non rempli.")
        )

    # Punctuation of the mechanical rule: em dash, slash outside addresses.
    sans_liens = _RX_URL.sub(" ", le_corps)
    for m in re.finditer(r"—|(?<![\d\s])/(?![\d\s])", sans_liens):
        sortie.append(
            Remarque(
                "ponctuation",
                _extrait(sans_liens, m.start(), m.end(), 25),
                "Ni tiret cadratin ni barre oblique au fil du texte.",
            )
        )
    for d in defauts(lettre):
        sortie.append(Remarque("redite", d, "Une conjonction par phrase, aucun mot trois fois."))

    # Addresses that nothing explains: the signature and the company are "known".
    connus = [c for c in connus if c]
    for rx in (_RX_URL, _RX_MAIL):
        for m in rx.finditer(le_corps):
            if not _legitime(m.group(0), connus):
                sortie.append(
                    Remarque(
                        "injection",
                        m.group(0),
                        "Adresse inconnue dans le corps : d'où vient-elle ? Une annonce "
                        "piégée peut en glisser une dans une lettre écrite par IA.",
                    )
                )

    # Copy-paste: another company of the queue named in the body.
    mien = _plat(entreprise)
    texte_plat = f" {_plat(le_corps)} "
    for autre in {a for a in autres_entreprises if a}:
        p = _plat(autre)
        if len(p) < 4 or p == mien or (mien and (p in mien or mien in p)):
            continue
        if re.search(r"(?<![a-z0-9])" + re.escape(p) + r"(?![a-z0-9])", texte_plat):
            sortie.append(
                Remarque(
                    "entreprise",
                    autre,
                    f"La lettre nomme « {autre} », pas « {entreprise} » : reste d'une autre "
                    "candidature ?",
                )
            )

    # Named recipient: only if the posting names them.
    if annonce:
        from jobhunter.documents.message import nom_dans_offre

        for ligne in lettre.splitlines():
            if not _RX_APPEL.match(ligne.strip()):
                continue
            for m in _RX_NOMME.finditer(ligne.strip()):
                if not nom_dans_offre(m.group(1), annonce):
                    sortie.append(
                        Remarque(
                            "destinataire",
                            m.group(0) + ",",
                            "Nom absent du texte de l'annonce : « Madame, Monsieur, » / "
                            "« Dear Sir or Madam, ».",
                        )
                    )
    return sortie


def _hote_chemin(adresse: str) -> tuple[str, str]:
    """« https://www.Acme.fr/a/b?x » → (« acme.fr », « /a/b ») ; un courriel → (domaine, « @local »)."""
    from urllib.parse import urlsplit

    a = adresse.strip().rstrip(".,;)").casefold()
    if "@" in a and "://" not in a:
        local, _, domaine = a.rpartition("@")
        return domaine, "@" + local
    p = urlsplit(a if "://" in a else "http://" + a)
    hote = (p.hostname or "").removeprefix("www.")
    return hote, p.path.rstrip("/")


def _legitime(trouve: str, connus: Iterable[str]) -> bool:
    """Is the address found in the letter one of the known ones?

    Hosts are compared whole, on a dot boundary: "jobs.acme.fr" goes with
    "acme.fr", but "acme.fr.evil.test" and "evil.test/acme.fr" do not (Codex audit of
    19/10: the substring comparison let them through). A known entry that carries a
    path (a LinkedIn profile) only admits that path and what extends it; a known
    email only admits itself.
    """
    hote, chemin = _hote_chemin(trouve)
    if not hote or "." not in hote:
        return False
    for c in connus:
        if not c:
            continue
        kh, kc = _hote_chemin(c)
        if not kh:
            continue
        if kc.startswith("@") or chemin.startswith("@"):
            if (kh, kc) == (hote, chemin):
                return True
            # An email at the domain of a known site (rh@acme.fr for acme.fr).
            if chemin.startswith("@") and not kc and (hote == kh or hote.endswith("." + kh)):
                return True
            continue
        meme_site = hote == kh or hote.endswith("." + kh) or kh.endswith("." + hote)
        if meme_site and (not kc or chemin == kc or chemin.startswith(kc + "/")):
            return True
    return False
