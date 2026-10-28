"""Nothing is defined after a module's `if __name__ == "__main__":` block.

Run as a program (`python -m jobhunter pipeline`, through runpy), a module executes
that block when it reaches it: a function defined below it does not exist yet. On
2026-10-28 the morning collection stopped one second after it started, on
« NameError: name '_pays_usajobs' is not defined »; importing the module, as the
tests do, defines everything first and hid it.
"""

import ast
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src" / "jobhunter"


def _est_garde(n: ast.stmt) -> bool:
    return (
        isinstance(n, ast.If)
        and isinstance(n.test, ast.Compare)
        and isinstance(n.test.left, ast.Name)
        and n.test.left.id == "__name__"
    )


def test_rien_apres_le_bloc_principal():
    fautes = []
    for f in sorted(SRC.rglob("*.py")):
        corps = ast.parse(f.read_text(encoding="utf-8")).body
        gardes = [i for i, n in enumerate(corps) if _est_garde(n)]
        if gardes and gardes[-1] != len(corps) - 1:
            apres = corps[gardes[-1] + 1]
            fautes.append(f"{f.relative_to(SRC)}:{apres.lineno}")
    assert fautes == []
