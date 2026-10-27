"""Microsoft Store package (tools/installer/msix.py): its manifest."""

import importlib.util
import xml.etree.ElementTree as ET
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("outil_msix", RACINE / "tools/installer/msix.py")
msix = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(msix)
NS = {"m": "http://schemas.microsoft.com/appx/manifest/foundation/windows10"}


def test_manifeste_lisible_version_a_quatre_nombres(monkeypatch):
    for k in ("MSIX_NOM", "MSIX_EDITEUR", "MSIX_EDITEUR_NOM"):
        monkeypatch.delenv(k, raising=False)
    racine = ET.fromstring(msix.manifeste())
    ident = racine.find("m:Identity", NS)
    version = (RACINE / "VERSION").read_text(encoding="utf-8").strip()
    assert ident.get("Version") == f"{version}.0"
    assert racine.find("m:Applications/m:Application", NS).get("Executable") == "JobHunter.exe"


def test_identite_du_store_echappee(monkeypatch):
    monkeypatch.setenv("MSIX_NOM", "12345Grisbix.JobHunter")
    monkeypatch.setenv("MSIX_EDITEUR", 'CN=A&B, O="X"')
    ident = ET.fromstring(msix.manifeste()).find("m:Identity", NS)
    assert ident.get("Name") == "12345Grisbix.JobHunter"
    assert ident.get("Publisher") == 'CN=A&B, O="X"'


def test_variable_vide_prend_l_identite_d_essai(monkeypatch):
    """CI passes an unset repository variable as an empty string, not as absent."""
    for k in ("MSIX_NOM", "MSIX_EDITEUR", "MSIX_EDITEUR_NOM"):
        monkeypatch.setenv(k, "")
    ident = ET.fromstring(msix.manifeste()).find("m:Identity", NS)
    assert ident.get("Name") == "JobHunter.Essai"
    assert ident.get("Publisher") == "CN=JobHunter Essai"


def test_noms_reserves_du_paquet_ecartes(tmp_path):
    """python-docx's unzipped template holds a [Content_Types].xml and `_rels` folders:
    makeappx refuses both."""
    app = tmp_path / "app"
    (app / "docx" / "word" / "_rels").mkdir(parents=True)
    (app / "docx" / "word" / "_rels" / "document.xml.rels").write_text("x", encoding="utf-8")
    (app / "docx" / "[Content_Types].xml").write_text("x", encoding="utf-8")
    (app / "docx" / "default.docx").write_text("x", encoding="utf-8")
    import shutil

    shutil.copytree(app, tmp_path / "msix", ignore=msix._reserves)
    assert sorted(p.name for p in (tmp_path / "msix" / "docx").iterdir()) == [
        "default.docx",
        "word",
    ]
    assert list((tmp_path / "msix" / "docx" / "word").iterdir()) == []
