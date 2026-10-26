"""The candidate's own cover letter, read once at the first launch.

The generated letter is made of the profile's paragraphs; the one about the
candidate's background (`domaines[].parcours_fr`) was drawn from the CV's summary,
rewritten in the first person: correct, but not in the candidate's voice. Most
candidates already have a letter they wrote and like. Its background paragraph is
taken from it, shown in the welcome form to check, and goes into the profile. Nothing
else of it is used: the opening, the company part and the closing are per offer.
"""

import re
from pathlib import Path

from jobhunter import cv_text as _cv_text

# What a background paragraph speaks of, and what a company paragraph speaks of.
_PARCOURS = re.compile(
    r"\b(?:master|dipl[ôo]m|formation|exp[ée]rience|stages?|[ée]cole|universit|parcours"
    r"|j.ai|ann[ée]es|alternance|cursus|degree|experience|graduated|internships?"
    r"|university|years|studied|background|i have)",
    re.I,
)
_ENTREPRISE = re.compile(r"\b(?:votre|vos|your|entreprise|soci[ée]t[ée]|company|groupe)\b", re.I)
# Header, salutation and closing lines: never the background.
_CADRE = re.compile(
    r"^\s*(?:madame|monsieur|dear|objet|subject|re\s*:|je vous prie|veuillez|dans l.attente"
    r"|cordialement|bien [àa] vous|sincerely|i look forward|yours|kind regards)"
    r"|@|\+?\d[\d .]{8,}\d",
    re.I,
)


def paragraphes(chemin: Path | str) -> list[str]:
    """The letter's paragraphs: a PDF's wrapped lines joined back (cv_word)."""
    p = Path(chemin)
    if p.suffix.lower() == ".pdf":
        from jobhunter import cv_word

        return [t for genre, t in cv_word.lire(p) if genre in ("texte", "puce")]
    return [l.strip() for l in _cv_text.texte_fichier(p).splitlines() if l.strip()]


def parcours(textes: list[str]) -> str:
    """The background paragraph among a letter's paragraphs, "" when none reads as one."""
    meilleur, note = "", 0.0
    for t in textes:
        if len(t) < 120 or _CADRE.search(t):
            continue
        n = len(_PARCOURS.findall(t)) - 1.5 * len(_ENTREPRISE.findall(t))
        if n > note:
            meilleur, note = t, n
    return meilleur


def parcours_de_lettre(chemin: Path | str) -> str:
    """The background paragraph of the letter file `chemin` (.pdf or .docx)."""
    return parcours(paragraphes(chemin))
