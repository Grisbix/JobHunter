"""3.85: testing the whole application before it is live (the user, 2026-11-06: « une
version test pour pouvoir tester réellement toute l'app sans qu'elle soit live »).

Two ways: `jobhunter sandbox`, the real window on fictitious data cut off from the web,
and test releases (GitHub pre-releases) that only the copies which ticked « Recevoir
les versions de test » receive.
"""

import json
from pathlib import Path

import js_app
import pytest

from jobhunter import scheduling
from jobhunter.programs import sandbox
from jobhunter.programs import update as maj
from jobhunter.web import api

RACINE = Path(__file__).resolve().parent.parent


# ── The sandbox ─────────────────────────────────────────────────────────────


def test_le_profil_d_exemple_embarque_est_celui_du_depot():
    # The package ships its own copy (the compiled app has no profile/ folder).
    assert (
        sandbox.EXEMPLE.read_bytes()
        == (RACINE / "profile" / "example_finance_esg.json").read_bytes()
    )


def test_dossier_fictif(tmp_path):
    sandbox.preparer(tmp_path)
    profil = json.loads((tmp_path / "profile" / "profile.json").read_text("utf-8"))
    file = json.loads((tmp_path / "data" / "apply_queue.json").read_text("utf-8"))
    assert profil["domaines"] and len(file) == len(sandbox.OFFRES)
    assert all(o["url"].startswith("https://jobs.example.com/") for o in file)
    assert json.loads((tmp_path / "data" / "applications.json").read_text("utf-8"))


def test_environnement_sans_les_donnees_ni_le_web(tmp_path, monkeypatch):
    monkeypatch.setenv("JOBHUNTER_PRINCIPALE", "C:/vraies/donnees")
    env = sandbox.environnement(tmp_path)
    assert env["JOBHUNTER_RACINE"] == str(tmp_path) and "JOBHUNTER_PRINCIPALE" not in env
    assert env[sandbox.ENV] == "1" and env["JOBHUNTER_SANS_FOND"] == "1"
    assert env["HTTPS_PROXY"] == env["HTTP_PROXY"] == sandbox.PROXY_MORT
    assert "127.0.0.1" in env["NO_PROXY"]  # the window's own local page
    assert sandbox.environnement(tmp_path, reseau=True).get("HTTPS_PROXY") != sandbox.PROXY_MORT


def test_le_web_ne_repond_pas(tmp_path, monkeypatch):
    import httpx

    for k, v in sandbox.environnement(tmp_path).items():
        if "PROXY" in k.upper():
            monkeypatch.setenv(k, v)
    with pytest.raises(httpx.HTTPError):
        httpx.get("https://example.com", timeout=10)


def test_rien_de_reel_depuis_le_bac_a_sable(monkeypatch):
    from jobhunter import frozen

    monkeypatch.setattr(frozen, "est_gele", lambda: True)
    monkeypatch.setattr(frozen, "famille_msix", lambda: "Grisbix.JobHunter_x")
    assert api._desinstalleur() is not None
    monkeypatch.setenv(sandbox.ENV, "1")
    assert api._desinstalleur() is None  # never uninstalls the real application
    assert not scheduling.disponible()  # never replaces the real morning collection


def test_commande_et_alias():
    from jobhunter import cli

    assert cli.module_de("sandbox") == cli.module_de("bac-a-sable") == "jobhunter.programs.sandbox"


def test_neuf_refuse_un_dossier_qui_n_est_pas_un_bac_a_sable(tmp_path):
    (tmp_path / "a_garder.txt").write_text("x", encoding="utf-8")
    with pytest.raises(SystemExit):
        sandbox.main(["--dossier", str(tmp_path), "--neuf"])
    assert (tmp_path / "a_garder.txt").exists()


# ── Test releases ───────────────────────────────────────────────────────────


def _rel(version, signee=True, test=False):
    noms = ["JobHunterSetup.exe"] + (["signature.json"] if signee else [])
    return {
        "tag_name": f"v{version}",
        "draft": False,
        "prerelease": test,
        "assets": [{"name": n} for n in noms],
    }


@pytest.fixture
def github(tmp_path, monkeypatch):
    from jobhunter import frozen
    from jobhunter import signature as sig

    monkeypatch.setattr(maj, "BETA", tmp_path / ".maj_beta")
    monkeypatch.setattr(maj, "DERNIERE_VERIF", tmp_path / ".maj_derniere_verif")
    monkeypatch.setattr(maj, "version_locale", lambda: "3.84.1")
    monkeypatch.setattr(frozen, "est_gele", lambda: True)
    monkeypatch.setattr(sig, "CLE_PUBLIQUE", "ab")
    etat = {"rels": [_rel("3.85.0", test=True), _rel("3.84.1")], "version": "3.84.1"}

    def get(url, timeout):
        if url == maj.RELEASES_URL:
            return json.dumps(etat["rels"]).encode()
        if url == maj.VERSION_URL:
            return etat["version"].encode()
        if url.endswith("signature.json"):
            return b"{}"
        raise AssertionError(url)

    monkeypatch.setattr(maj, "_get", get)
    return etat


def test_sans_la_case_les_versions_de_test_ne_sont_pas_proposees(github):
    assert maj.derniere_signee() == "3.84.1"
    assert maj.nouvelle_version() is None
    assert maj.version_proposee() == "3.84.1"


def test_avec_la_case_la_version_de_test_est_proposee(github):
    maj.regler_beta(True)
    assert maj.beta()
    assert maj.derniere_signee(avec_beta=True) == "3.85.0"
    assert maj.nouvelle_version() == "3.85.0"
    assert maj.version_proposee() == "3.85.0"


def test_une_version_de_test_non_signee_attend(github):
    github["rels"][0] = _rel("3.85.0", signee=False, test=True)
    maj.regler_beta(True)
    assert maj.nouvelle_version() is None


def test_decocher_oublie_la_derniere_verification(github):
    maj.regler_beta(True)
    assert maj.nouvelle_version() == "3.85.0"
    maj.regler_beta(False)
    assert not maj.beta() and not maj.DERNIERE_VERIF.exists()
    assert maj.nouvelle_version() is None


def test_le_store_n_a_pas_de_versions_de_test(monkeypatch):
    from jobhunter import frozen

    monkeypatch.setattr(frozen, "paquet_msix", lambda: True)
    assert api.Api.regler_beta(None, True)["ok"] is False  # type: ignore[arg-type]


def test_la_case_dans_maintenance():
    js = js_app.source()
    assert '"regler_beta"' in js and "Recevoir les versions de test" in js


def test_une_version_de_test_ne_part_pas_au_store():
    yml = (RACINE / ".github" / "workflows" / "installer.yml").read_text(encoding="utf-8")
    store = yml[yml.index("\n  store:") :]
    assert "!github.event.release.prerelease" in store and "store.yml" in store
    promue = (RACINE / ".github" / "workflows" / "store.yml").read_text(encoding="utf-8")
    assert "types: [released]" in promue  # a test release made the release goes then
