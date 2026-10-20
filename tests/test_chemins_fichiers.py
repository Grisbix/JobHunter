"""Document paths <-> file:/// URLs (jobhunter.links), on Windows AND on macOS/Linux.

The macOS CI job (20/10) found it: `chemin_de("file:///Users/x/cv.pdf")` returned the
relative path `Users/x/cv.pdf`, so a CV linked by a standard URL was "not found" on a
Mac; and `url_de("/Users/x")` wrote four slashes. Pure string logic: these tests run
the same on every system.
"""

from pathlib import Path, PurePosixPath

import pytest

from jobhunter.links import chemin_de, url_de


@pytest.mark.parametrize(
    ("url", "attendu"),
    [
        ("file:///C:/Docs/cv.pdf", "C:/Docs/cv.pdf"),
        ("file://C:/Docs/cv.pdf", "C:/Docs/cv.pdf"),
        ("file:///c:/Docs/Soci%C3%A9t%C3%A9.pdf", "c:/Docs/Société.pdf"),
        ("C:/Docs/cv.pdf", "C:/Docs/cv.pdf"),
    ],
)
def test_windows_inchange(url, attendu):
    assert chemin_de(url) == Path(attendu)


@pytest.mark.parametrize(
    "url",
    [
        "file:///Users/camille/Lettres/Soci%C3%A9t%C3%A9.pdf",
        # what url_de wrote on a Mac before 2.23.1: still read
        "file:////Users/camille/Lettres/Soci%C3%A9t%C3%A9.pdf",
    ],
)
def test_mac_garde_la_racine(url):
    p = chemin_de(url)
    assert p is not None
    assert PurePosixPath(p.as_posix()) == PurePosixPath("/Users/camille/Lettres/Société.pdf")


def test_url_mac_trois_barres():
    assert url_de("/Users/camille/cv é.pdf") == "file:///Users/camille/cv%20%C3%A9.pdf"


def test_url_windows_inchangee():
    assert url_de(r"C:\Docs\cv é.pdf") == "file:///C:/Docs/cv%20%C3%A9.pdf"


@pytest.mark.parametrize("p", ["/Users/camille/cv.pdf", "C:/Docs/Société.pdf"])
def test_aller_retour(p):
    assert chemin_de(url_de(p)) == Path(p)


def test_uri_standard_du_systeme(tmp_path):
    """`Path.as_uri()` (file:///C:/… on Windows, file:///Users/… on a Mac) reads back."""
    f = tmp_path / "cv é.pdf"
    f.write_bytes(b"%PDF")
    assert chemin_de(f.as_uri()) == f
