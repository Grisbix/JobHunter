"""3.62: node.exe (88 MB) leaves the installer; the application fetches it, checked,
the first time a browser starts."""

import hashlib
import io
import json
import sys
import types
import zipfile

import pytest

from jobhunter import playwright_node as pn


def _zip(contenu=b"MZ node"):
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        z.writestr("node.exe", contenu)
    return b.getvalue()


@pytest.fixture
def gele(tmp_path, monkeypatch):
    """A compiled application without node.exe, and a fresh LOCALAPPDATA."""
    interne = tmp_path / "_internal"
    interne.mkdir()
    monkeypatch.setattr(sys, "_MEIPASS", str(interne), raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local"))
    # set then removed: the teardown removes again what the wrapper sets (no leak into
    # the browser tests, which would start the fake node.exe)
    monkeypatch.setenv("PLAYWRIGHT_NODEJS_PATH", "")
    monkeypatch.delenv("PLAYWRIGHT_NODEJS_PATH")
    monkeypatch.delenv("JOBHUNTER_NODE_ZIP", raising=False)
    donnees = _zip()
    m = {
        "url": "https://github.com/Grisbix/JobHunter/releases/download/v9/" + pn.ZIP,
        "sha256": hashlib.sha256(donnees).hexdigest(),
        "node": hashlib.sha256(b"MZ node").hexdigest(),
    }
    (interne / pn.MANIFESTE).write_text(json.dumps(m), encoding="utf-8")
    return interne, donnees, m


def test_sans_manifeste_rien_ne_change(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    assert pn.manifeste() is None and pn.installer() is False


def test_node_livre_rien_a_telecharger(gele):
    interne, _, _ = gele
    d = interne / "playwright" / "driver"
    d.mkdir(parents=True)
    (d / "node.exe").write_bytes(b"MZ")
    assert pn.manifeste() is None


def test_telecharge_verifie_et_reutilise(gele, monkeypatch):
    _, donnees, m = gele
    appels = []
    monkeypatch.setattr(pn, "_telecharger", lambda url: appels.append(url) or donnees)
    exe = pn.assurer(pn.manifeste())
    assert exe.read_bytes() == b"MZ node" and m["node"][:12] in str(exe)
    assert pn.assurer(m) == exe and len(appels) == 1  # second time: from the cache
    assert not list(exe.parent.glob("*.tmp"))


def test_empreinte_differente_refusee(gele, monkeypatch):
    _, _, m = gele
    monkeypatch.setattr(pn, "_telecharger", lambda url: _zip(b"autre chose"))
    with pytest.raises(RuntimeError, match="empreinte"):
        pn.assurer(m)
    assert not pn.cible(m["node"]).exists()


def test_hors_ligne_message_clair(gele, monkeypatch):
    _, _, m = gele

    def coupe(url):
        raise OSError("pas de réseau")

    monkeypatch.setattr(pn, "_telecharger", coupe)
    with pytest.raises(RuntimeError, match="connexion"):
        pn.assurer(m)


def test_zip_local_pour_la_ci(gele, tmp_path, monkeypatch):
    _, donnees, m = gele
    z = tmp_path / pn.ZIP
    z.write_bytes(donnees)
    monkeypatch.setenv("JOBHUNTER_NODE_ZIP", str(z))
    monkeypatch.setattr(pn, "_telecharger", lambda url: pytest.fail("pas de réseau"))
    assert pn.assurer(m).read_bytes() == b"MZ node"


def test_le_crochet_enveloppe_playwright_a_l_import(gele, monkeypatch):
    _, donnees, m = gele
    monkeypatch.setattr(pn, "_telecharger", lambda url: donnees)
    import playwright._impl._transport as originel  # the rest of Playwright keeps it

    monkeypatch.delitem(sys.modules, pn.MODULE)  # restored at teardown
    meta = list(sys.meta_path)
    try:
        assert pn.installer() is True
        assert "PLAYWRIGHT_NODEJS_PATH" not in __import__("os").environ  # nothing yet
        import playwright._impl._transport as t

        node, cli = t.compute_driver_executable()
        assert node == str(pn.cible(m["node"])) and cli.endswith("cli.js")
        assert t is not originel
    finally:
        sys.meta_path[:] = meta


def test_module_deja_importe_enveloppe_directement(gele, monkeypatch):
    _, donnees, m = gele
    monkeypatch.setattr(pn, "_telecharger", lambda url: donnees)
    faux = types.SimpleNamespace(
        compute_driver_executable=lambda: (
            __import__("os").environ["PLAYWRIGHT_NODEJS_PATH"],
            "cli.js",
        )
    )
    monkeypatch.setitem(sys.modules, pn.MODULE, faux)
    assert pn.installer() is True
    assert faux.compute_driver_executable()[0] == str(pn.cible(m["node"]))


def test_la_construction_sort_node(tmp_path, monkeypatch):
    sys.path.insert(
        0, str(__import__("pathlib").Path(__file__).resolve().parent.parent / "tools" / "installer")
    )
    try:
        import build
    finally:
        sys.path.pop(0)
    app = tmp_path / "JobHunter"
    d = app / "_internal" / "playwright" / "driver"
    d.mkdir(parents=True)
    (d / "node.exe").write_bytes(b"MZ node" * 1000)
    monkeypatch.setattr(build, "DIST", tmp_path)
    z = build.sortir_node(app)
    assert z == tmp_path / pn.ZIP and not (d / "node.exe").exists()
    m = json.loads((app / "_internal" / pn.MANIFESTE).read_text(encoding="utf-8"))
    assert m["sha256"] == hashlib.sha256(z.read_bytes()).hexdigest()
    assert m["url"].endswith("/v" + build.version() + "/" + pn.ZIP)
    premier = z.read_bytes()
    (d / "node.exe").write_bytes(b"MZ node" * 1000)
    assert build.sortir_node(app).read_bytes() == premier  # same node, same zip: same cache
