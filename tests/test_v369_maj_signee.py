"""3.69: while the latest release waits for its author's signature (up to an hour), the
update check offers the latest signed one instead of only « attend la signature »."""

import json

from jobhunter import frozen
from jobhunter import signature as sig
from jobhunter.programs import update
from jobhunter.web import api


def _releases(*versions_signees):
    rels = []
    for v, signee in versions_signees:
        assets = [{"name": update.SETUP}, {"name": update.SETUP + ".sha256"}]
        if signee:
            assets.append({"name": sig.FICHIER if sig.CLE_PUBLIQUE else ""})
        rels.append({"tag_name": f"v{v}", "assets": assets})
    return json.dumps(rels).encode()


def test_derniere_signee(monkeypatch):
    rels = _releases(("3.68.0", False), ("3.67.0", True), ("3.66.0", True))
    rels = json.loads(rels)
    rels.insert(0, {"tag_name": "v3.70.0", "draft": True, "assets": rels[1]["assets"]})
    monkeypatch.setattr(update, "_get", lambda url, t: json.dumps(rels).encode())
    assert update.derniere_signee() == "3.67.0"


def test_rien_de_signe(monkeypatch):
    monkeypatch.setattr(update, "_get", lambda url, t: _releases(("3.68.0", False)))
    assert update.derniere_signee() == ""


def test_version_proposee(monkeypatch):
    monkeypatch.setattr(update, "_get", lambda url, t: b"3.68.0\n")
    monkeypatch.setattr(update, "prete", lambda v, t=5: False)
    monkeypatch.setattr(update, "derniere_signee", lambda t=10: "3.67.0")
    assert update.version_proposee() == "3.67.0"
    monkeypatch.setattr(update, "prete", lambda v, t=5: True)
    assert update.version_proposee() == "3.68.0"


def _api(monkeypatch, installee, signee):
    monkeypatch.setattr(api, "_version_installee", lambda: installee)
    monkeypatch.setattr(api, "_derniere_version", lambda: "3.68.0")
    monkeypatch.setattr(api, "_signee", lambda v: False)
    monkeypatch.setattr(frozen, "paquet_msix", lambda: False)
    monkeypatch.setattr(update, "derniere_signee", lambda t=10: signee)
    return api.Api.mise_a_jour(None)  # type: ignore[arg-type]


def test_propose_la_derniere_signee(monkeypatch):
    v = _api(monkeypatch, "3.66.0", "3.67.0")
    assert v["nouvelle"] and v["signee"] and v["derniere"] == "3.67.0"
    assert v["attente"] == "3.68.0"


def test_a_jour_en_attendant_la_signature(monkeypatch):
    v = _api(monkeypatch, "3.67.0", "3.67.0")
    assert not v["nouvelle"] and v["attente"] == "3.68.0"
