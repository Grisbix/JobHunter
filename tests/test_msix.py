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


def _app_sans_node(tmp_path, contenu=b"MZ node"):
    import hashlib
    import json
    import zipfile

    interne = tmp_path / "app" / "_internal"
    (interne / "playwright" / "driver" / "package").mkdir(parents=True)
    m = {"url": "u", "sha256": "s", "node": hashlib.sha256(b"MZ node").hexdigest()}
    (interne / "jobhunter_node.json").write_text(json.dumps(m), encoding="utf-8")
    z = tmp_path / "playwright-node-win64.zip"
    with zipfile.ZipFile(z, "w") as f:
        f.writestr("node.exe", contenu)
    return tmp_path / "app", z


def test_le_paquet_du_store_contient_node(tmp_path):
    # 3.63: Store policy 10.2.2, no downloaded code inside the package
    app, z = _app_sans_node(tmp_path)
    assert msix.remettre_node(app, z) is True
    assert (app / "_internal/playwright/driver/node.exe").read_bytes() == b"MZ node"
    assert not (app / "_internal/jobhunter_node.json").exists()  # nothing to download
    assert msix.remettre_node(app, z) is False


def test_node_different_refuse(tmp_path):
    import pytest

    app, z = _app_sans_node(tmp_path, b"autre")
    with pytest.raises(SystemExit):
        msix.remettre_node(app, z)
    z.unlink()
    with pytest.raises(SystemExit):
        msix.remettre_node(app, z)
