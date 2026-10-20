"""outils/signature.py: the private key stays out of the repository, the signature produced is valid."""

import hashlib
import importlib.util

import pytest
from conftest import RACINE
from test_mise_a_jour import V13, zip_de

from jobhunter import signature as sig
from jobhunter.programmes import mise_a_jour as maj


@pytest.fixture
def outil(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location(
        "outil_signature", RACINE / "outils" / "signature.py"
    )
    assert spec and spec.loader
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    module = tmp_path / "signature.py"
    module.write_text('X = 1\nCLE_PUBLIQUE = ""\n', encoding="utf-8")
    monkeypatch.setattr(m, "CLE_PRIVEE", tmp_path / "prive" / "cle_signature")
    monkeypatch.setattr(m, "MODULE", module)
    monkeypatch.setattr(m, "RACINE", tmp_path)
    return m


def test_cle_creee_hors_depot_jamais_affichee(outil, tmp_path, capsys):
    assert outil.creer_cle() == 0
    secret = bytes.fromhex(outil.CLE_PRIVEE.read_text(encoding="ascii").strip())
    publique = sig.publique(secret).hex()
    assert f'CLE_PUBLIQUE = "{publique}"' in outil.MODULE.read_text(encoding="utf-8")
    assert secret.hex() not in capsys.readouterr().out
    assert outil.creer_cle() == 1  # never replaced


def test_signer_une_version(outil, tmp_path, monkeypatch):
    outil.creer_cle()
    secret = bytes.fromhex(outil.CLE_PRIVEE.read_text(encoding="ascii").strip())
    monkeypatch.setattr(sig, "CLE_PUBLIQUE", sig.publique(secret).hex())
    exe = b"MZ 1.3.0"
    urls = {
        maj.TAG_URL.format("1.3.0"): zip_de(V13, "JobHunter-1.3.0"),
        maj.ASSET_URL.format("1.3.0", maj.SETUP): exe,
        maj.ASSET_URL.format("1.3.0", maj.SETUP + ".sha256"): hashlib.sha256(exe)
        .hexdigest()
        .encode(),
    }
    monkeypatch.setattr(outil, "_get", lambda url: urls[url])
    assert outil.signer("1.3.0", publier=False) == 0
    m = sig.ouvrir((tmp_path / "dist" / sig.FICHIER).read_bytes(), "1.3.0")
    sig.controler_setup(m, exe)
    assert set(m["fichiers"]) == set(V13)


def test_signer_refuse_un_installateur_qui_ne_correspond_pas(outil, monkeypatch):
    outil.creer_cle()
    secret = bytes.fromhex(outil.CLE_PRIVEE.read_text(encoding="ascii").strip())
    monkeypatch.setattr(sig, "CLE_PUBLIQUE", sig.publique(secret).hex())
    urls = {
        maj.TAG_URL.format("1.3.0"): zip_de(V13, "JobHunter-1.3.0"),
        maj.ASSET_URL.format("1.3.0", maj.SETUP): b"MZ",
        maj.ASSET_URL.format("1.3.0", maj.SETUP + ".sha256"): b"0" * 64,
    }
    monkeypatch.setattr(outil, "_get", lambda url: urls[url])
    assert outil.signer("1.3.0", publier=False) == 1


def test_signer_refuse_une_cle_qui_n_est_pas_celle_du_depot(outil, monkeypatch):
    outil.creer_cle()
    monkeypatch.setattr(sig, "CLE_PUBLIQUE", sig.publique(bytes(32)).hex())
    assert outil.signer("1.3.0", publier=False) == 1
