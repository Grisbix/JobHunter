"""The web interface's JavaScript, as the window loads it: every script of index.html, in order.

app.js was one file of 200 KB until 3.87; it is now several classic scripts sharing one
global scope (the page is opened from file://, where ES modules do not load). A test
that looks for a piece of the interface's code reads it here, wherever it lives.
"""

import re
from functools import cache
from pathlib import Path

STATIQUE = Path(__file__).resolve().parent.parent / "src" / "jobhunter" / "web" / "static"


def scripts() -> list[str]:
    """The local scripts of index.html, in the order the page runs them."""
    html = (STATIQUE / "index.html").read_text(encoding="utf-8")
    return re.findall(r'<script src="([^":/]+\.js)"></script>', html)


@cache
def source() -> str:
    """Their text, joined in that order."""
    return "\n".join((STATIQUE / nom).read_text(encoding="utf-8") for nom in scripts())
