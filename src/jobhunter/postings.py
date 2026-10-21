"""A copy of the posting, kept the day the user applies.

An offer closes, the page goes, and three weeks later the interview invitation
arrives: the text one applied to is nowhere. 2,868 closed offers left the queue in
one week of October 2026. So, for each application, the posting is written once to
`Letters/Postings/` (`Lettres/Annonces/` in the 2.x layout) as a PDF to read and a
.txt to search, with what the queue knew: company, job, link, place, contract,
salary, dates.

Written once and never rewritten: it is the version the user applied to, even if the
posting changes afterwards. The text comes from the queue, so nothing is fetched from
the web; an offer whose description is too short is skipped and tried again the next
day (a better source may have completed it).

Called by the app when the user marks an offer "postulé", and every morning by the
pipeline (`jobhunter postings`) for the ones the app did not catch.
"""

import datetime
import html
import re
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

TEXTE_MIN = 200
ENVOYEES = ("postulé", "relancé", "entretien", "refus", "à postuler")

_RX_NOM = re.compile(r"[^\w]+")

_CHAMPS = (
    ("Entreprise", "entreprise"),
    ("Poste", "poste"),
    ("Lien", "url"),
    ("Lieu", "localisation"),
    ("Contrat", "contrat"),
    ("Salaire", "salaire"),
    ("Publiée le", "date_publication"),
    ("Source", "source"),
)


def dossier() -> Path:
    """`Letters/Postings` of the active root (read at call time: profiles switch roots)."""
    from jobhunter import paths

    return Path(paths.LT_ANNONCES)


def nom_fichier(offre: Mapping[str, Any]) -> str:
    """'Company_Job', safe as a Windows file name, 100 characters at most, without extension."""
    brut = f"{offre.get('entreprise') or ''}_{offre.get('poste') or ''}"
    nom = _RX_NOM.sub("_", brut).strip("_")
    return nom[:100].rstrip("_") or "annonce"


def chemin(offre: Mapping[str, Any], ou: Path | None = None) -> Path:
    """The PDF of an offer's posting (it may not exist yet)."""
    return (ou or dossier()) / f"{nom_fichier(offre)}.pdf"


def _entete(offre: Mapping[str, Any], jour: str) -> list[tuple[str, str]]:
    lignes = [(lib, str(offre.get(k) or "").strip()) for lib, k in _CHAMPS]
    lignes.append(("Copie faite le", jour))
    return [(lib, v) for lib, v in lignes if v]


def texte(offre: Mapping[str, Any], jour: str) -> str:
    """The .txt: the header lines, a blank line, the description."""
    tete = "\n".join(f"{lib} : {v}" for lib, v in _entete(offre, jour))
    return f"{tete}\n\n{str(offre.get('description') or '').strip()}\n"


def _html(offre: Mapping[str, Any], jour: str) -> str:
    e = html.escape
    tete = "".join(
        f"<p class='m'><b>{e(lib)}</b> : {e(v)}</p>"
        for lib, v in _entete(offre, jour)
        if lib not in ("Entreprise", "Poste")
    )
    corps = "".join(
        f"<p>{e(p.strip())}</p>"
        for p in re.split(r"\n\s*\n|\n", str(offre.get("description") or ""))
        if p.strip()
    )
    titre = e(f"{offre.get('entreprise') or ''} — {offre.get('poste') or ''}")
    return (
        "<style>body{font-family:sans-serif;font-size:10pt;line-height:1.35}"
        "h1{font-size:15pt;margin-bottom:4pt}.m{color:#555;margin:0}"
        "p{margin:0 0 5pt 0}</style>"
        f"<h1>{titre}</h1>{tete}<hr/>{corps}"
    )


def _pdf(cible: Path, contenu: str) -> None:
    """HTML to an A4 PDF, with PyMuPDF's Story (it flows the text over the pages)."""
    import io

    import fitz

    story = fitz.Story(html=contenu)
    # In memory, then one write: a DocumentWriter on a path keeps the file open on
    # Windows after close(), and the rename into place then fails.
    tampon = io.BytesIO()
    ecrivain = fitz.DocumentWriter(tampon)
    page = fitz.paper_rect("a4")
    cadre = page + (50, 50, -50, -50)
    plus = True
    while plus:
        dev = ecrivain.begin_page(page)
        plus, _ = story.place(cadre)
        story.draw(dev)
        ecrivain.end_page()
    ecrivain.close()
    tmp = cible.with_name(cible.name + ".tmp")
    tmp.write_bytes(tampon.getvalue())
    tmp.replace(cible)


def archiver(
    offre: Mapping[str, Any], ou: Path | None = None, jour: str | None = None
) -> Path | None:
    """Writes the posting's copy (PDF + .txt) if there is none yet.

    Returns:
        The PDF's path when it exists after the call; None when the description is
        too short to be worth keeping (to try again later).
    """
    cible = chemin(offre, ou)
    if cible.exists():
        return cible
    if len(str(offre.get("description") or "").strip()) < TEXTE_MIN:
        return None
    jour = jour or datetime.date.today().isoformat()
    cible.parent.mkdir(parents=True, exist_ok=True)
    cible.with_suffix(".txt").write_text(texte(offre, jour), encoding="utf-8")
    try:
        _pdf(cible, _html(offre, jour))
    except Exception:  # no PDF (PyMuPDF missing, odd text): the .txt stays
        cible.with_name(cible.name + ".tmp").unlink(missing_ok=True)
        return cible.with_suffix(".txt")
    return cible


def existante(offre: Mapping[str, Any], ou: Path | None = None) -> Path | None:
    """The copy kept for this offer (PDF first, else .txt); None if there is none."""
    p = chemin(offre, ou)
    for f in (p, p.with_suffix(".txt")):
        if f.exists():
            return f
    return None


def a_archiver[O: Mapping[str, Any]](
    offres: Iterable[O], suivi: Mapping[str, Mapping[str, Any]], oid: Any
) -> list[O]:
    """The offers applied to (or about to be) whose posting has no copy yet."""
    return [
        o
        for o in offres
        if str((suivi.get(oid(o)) or {}).get("s") or "") in ENVOYEES and existante(o) is None
    ]
