"""ADRs and code cite each other (phase 8 of the plan).

Each decision in docs/adr/ is cited by at least one code file — the one where it
applies —, and every `docs/adr/NNNN-….md` citation in the code designates an ADR that exists.
An ADR that nothing cites is a decision whose trace has been lost in the code; a
dead citation sends the reader nowhere.
"""

import re
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
ADR = sorted(p.name for p in (RACINE / "docs" / "adr").glob("[0-9][0-9][0-9][0-9]-*.md"))
CODE = [
    *RACINE.joinpath("src", "jobhunter").rglob("*.py"),
    *RACINE.joinpath("tools").glob("*.py"),
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
