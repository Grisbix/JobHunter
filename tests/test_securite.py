"""Garde-fous de sécurité : schémas d'URL, chemins des ZIP de mise à jour."""

import io
import zipfile

import pytest

from jobhunter.network import exiger_http
from jobhunter.programs import update as mise_a_jour


@pytest.mark.parametrize(
    "url", ["https://a.fr/x", "http://localhost:11434/api/tags", "HTTPS://A.FR"]
)
def test_exiger_http_accepte(url):
    assert exiger_http(url) == url


@pytest.mark.parametrize(
    "url",
    ["file:///C:/Windows/win.ini", "ftp://a.fr", "data:text/plain,x", "javascript:x", "", "a.fr"],
)
def test_exiger_http_refuse(url):
    with pytest.raises(ValueError):
        exiger_http(url)


@pytest.mark.parametrize(
    "rel,sur",
    [
        ("src/jobhunter/cli.py", True),
        ("README.md", True),
        ("../evil.py", False),
        ("src/../../evil.py", False),
        ("/etc/passwd", False),
        ("C:/Windows/evil.dll", False),
        (r"src\..\evil.py", False),
        ("", False),
    ],
)
def test_chemin_sur(rel, sur):
    assert mise_a_jour.chemin_sur(rel) is sur


def test_zip_piege_ignore_les_chemins_hors_du_dossier():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("JobHunter-main/VERSION", "9.9.9")
        z.writestr("JobHunter-main/../../evil.py", "x")
        z.writestr("JobHunter-main/a/../../../evil2.py", "x")
    assert mise_a_jour.fichiers_du_zip(buf.getvalue()) == {"VERSION": b"9.9.9"}
