"""Les ADR et le code se citent mutuellement (phase 8 du plan).

Chaque décision de docs/adr/ est citée par au moins un fichier de code — celui où elle
s'applique —, et toute citation `docs/adr/NNNN-….md` du code désigne un ADR qui existe.
Un ADR que rien ne cite est une décision dont on a perdu la trace dans le code ; une
citation morte envoie le lecteur nulle part.
"""

import re
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
ADR = sorted(p.name for p in (RACINE / "docs" / "adr").glob("[0-9][0-9][0-9][0-9]-*.md"))
CODE = [
    *RACINE.joinpath("src", "jobhunter").rglob("*.py"),
    *RACINE.joinpath("outils").glob("*.py"),
    RACINE / "JobHunter.pyw",
]
CITATIONS = {
    (m.group(1), p.relative_to(RACINE).as_posix())
    for p in CODE
    for m in re.finditer(r"docs/adr/(\d{4}-[\w-]+\.md)", p.read_text(encoding="utf-8"))
}


def test_des_adr_existent():
    assert ADR


def test_chaque_adr_est_cite_par_le_code():
    cites = {adr for adr, _ in CITATIONS}
    assert [a for a in ADR if a not in cites] == []


def test_aucune_citation_morte():
    assert sorted((adr, f) for adr, f in CITATIONS if adr not in ADR) == []
