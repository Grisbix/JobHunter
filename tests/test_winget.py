"""tools/winget.py: the manifests submitted to microsoft/winget-pkgs."""

import importlib.util
import re

import pytest
from conftest import RACINE


@pytest.fixture(scope="module")
def outil():
    spec = importlib.util.spec_from_file_location("outil_winget", RACINE / "tools" / "winget.py")
    assert spec and spec.loader
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_app_id_celui_de_l_installateur(outil):
    """winget recognises an existing installation by the Inno AppId: they must not drift."""
    iss = (RACINE / "tools" / "installer" / "JobHunter.iss").read_text(encoding="utf-8")
    assert f"AppId={{{outil.APP_ID}" in iss


def test_trois_manifestes(outil):
    version = re.search(
        r"^## (\d+\.\d+\.\d+) ", (RACINE / "CHANGELOG.md").read_text(encoding="utf-8"), re.M
    )[1]
    m = outil.manifestes(version, "ab" * 32)
    assert set(m) == {
        f"{outil.ID}.yaml",
        f"{outil.ID}.installer.yaml",
        f"{outil.ID}.locale.en-US.yaml",
    }
    inst = m[f"{outil.ID}.installer.yaml"]
    assert f"InstallerSha256: {'AB' * 32}" in inst
    assert f"/v{version}/JobHunterSetup.exe" in inst
    assert "InstallerType: inno" in inst and "Scope: user" in inst
    assert f"ProductCode: '{outil.APP_ID}_is1'" in inst
    for texte in m.values():
        assert f"PackageVersion: {version}\n" in texte


def test_version_inconnue_refusee(outil):
    with pytest.raises(SystemExit):
        outil.manifestes("0.0.1", "00" * 32)
