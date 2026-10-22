"""tools/signature.py: the private key stays out of the repository, the signature produced is valid."""

import hashlib
import importlib.util

import pytest
from conftest import RACINE
from test_update import V13, zip_de

from jobhunter import signature as sig
from jobhunter.programs import update as maj


@pytest.fixture
def outil(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location(
        "outil_signature", RACINE / "tools" / "signature.py"
    )
    assert spec and spec.loader
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    module = tmp_path / "signature.py"
    module.write_text('X = 1\nCLE_PUBLIQUE = ""\n', encoding="utf-8")
    monkeypatch.setattr(m, "CLE_PRIVEE", tmp_path / "prive" / "cle_signature")
    monkeypatch.setattr(m, "MODULE", module)
    monkeypatch.setattr(m, "RACINE", tmp_path)
    monkeypatch.setattr(m, "REFUSEES", tmp_path / "prive" / "versions_refusees.txt")
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


# ── approuver: the hourly task asks, the author decides ──────────────────────


def rel(version, *assets, draft=False):
    noms = [{"name": n} for n in assets]
    return {
        "tag_name": f"v{version}",
        "published_at": "2026-10-21T14:05:00Z",
        "draft": draft,
        "prerelease": False,
        "assets": noms,
    }


@pytest.fixture
def github(outil, monkeypatch):
    import json
    import subprocess

    etat = {"rels": []}

    def gh(*args, check=True):
        if args[0] == "api" and "/releases" in args[1]:
            sortie = json.dumps(etat["rels"])
        elif args[0] == "api" and "/commits/" in args[1]:
            version = args[1].rsplit("/v", 1)[1]
            sortie = json.dumps({"commit": {"message": f"Release {version}\n\ncorps"}})
        else:
            raise AssertionError(args)
        return subprocess.CompletedProcess(["gh", *args], 0, sortie, "")

    monkeypatch.setattr(outil, "_gh", gh)
    return etat


SETUP_OK = ("JobHunterSetup.exe", "JobHunterSetup.exe.sha256")


def test_en_attente_depuis_la_derniere_signee(outil, github):
    github["rels"] = [
        rel("3.15.0", "JobHunterSetup.exe"),  # installer CI still running: not yet
        rel("3.14.1", *SETUP_OK),
        rel("3.14.0", *SETUP_OK, draft=True),
        rel("3.13.0", *SETUP_OK, "signature.json"),
        rel("3.11.0", *SETUP_OK),  # before the key: never asked
    ]
    att = outil.en_attente()
    assert [r["version"] for r in att] == ["3.14.1"]
    assert att[0]["commit"] == "Release 3.14.1" and att[0]["date"] == "2026-10-21 14:05"


def test_rien_en_attente_aucune_fenetre(outil, github):
    github["rels"] = [rel("3.13.0", *SETUP_OK, "signature.json")]
    assert outil.approuver(demander=lambda *a: pytest.fail("fenêtre ouverte")) == 0


def test_une_seule_fenetre_pour_la_plus_recente(outil, github, monkeypatch):
    github["rels"] = [
        rel("3.15.1", *SETUP_OK),
        rel("3.15.0", *SETUP_OK),
        rel("3.14.1", *SETUP_OK),
        rel("3.14.0", *SETUP_OK, "signature.json"),
    ]
    signees, questions = [], []
    monkeypatch.setattr(outil, "signer", lambda v, publier: signees.append((v, publier)) or 0)

    def demander(titre, question):
        questions.append(question)
        return True

    assert outil.approuver(demander) == 0
    assert signees == [("3.15.1", True)] and len(questions) == 1
    assert "JobHunter 3.15.1" in questions[0]
    assert "remplace 3.14.1, 3.15.0" in questions[0]  # named, not asked for
    assert "piraté" in questions[0]  # says why a surprise must be refused
    # once the newest is signed, the older ones are never asked for
    github["rels"][0] = rel("3.15.1", *SETUP_OK, "signature.json")
    assert outil.approuver(lambda *a: pytest.fail("fenêtre ouverte")) == 0


def test_non_ne_redemande_plus(outil, github, monkeypatch):
    github["rels"] = [rel("3.14.1", *SETUP_OK)]
    monkeypatch.setattr(outil, "signer", lambda v, publier: pytest.fail("signée"))
    assert outil.approuver(lambda *a: False) == 0
    assert outil.approuver(lambda *a: pytest.fail("redemandée")) == 0
